"""Integrator runtime driver for the authorized W7 optimized-kernel retry (mechanism/w7/RETRY_REQUEST.json).

The science is w7_steering's, unchanged: frozen inputs and recipe, text_nll / token_logp, choose_doses, the dose seal
before outcomes, the score rows and the final seal. This driver replaces only what the retry receipt supersedes:
  * clock: setup (model load + unscored warm-up through every kernel path and production batch shape) runs first, inside
    the 900 s setup allowance and outside science; science then starts with its own clock, allocated science
    <= the remaining cumulative science (575.2 s), deadline = science_started + allocated, 180 s retrieval reserve kept;
  * gate: instead of the calibration-average token forecast, the median seconds-per-token of the next 3 real units of a
    path after warm-up (never the first call) times the remaining work on that path, x1.5, must fit before
    deadline - 180 s; otherwise NO_FIT. Gate 1 runs after 3 steered calibration units and forecasts all remaining
    calibration and outcome work at that rate (text_nll scores every position, so it is the heavier per-token path);
    gate 2 re-checks the outcome path on its own first 3 steered units.
The warm-up uses unrelated text only (tiled to each production batch length), so no W7 target item is read before the
dose seal; its outputs are discarded and it never enters the timing sample.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time

import numpy as np

from . import protocol as P
from . import w7_steering as W

DRIVER = Path(__file__).resolve()
SETUP_ALLOWANCE = 900.0
RESERVE = 180.0
MARGIN = 1.5
N_GATE = 3
ENVIRONMENT = "/weights/venv-kernels"
DRIVER_REL = "projects/g_agreement/blindspot/w7_retry_driver.py"


def _sync():
    import torch
    torch.cuda.synchronize()


def _batch_lengths(seqs, batch):
    """Max sequence length of each production batch, in production order."""
    return [max(len(s) for s in seqs[i:i+batch]) for i in range(0, len(seqs), batch)]


def _filler(unrelated, length, n):
    """n unrelated-text token sequences of exactly `length`, tiled from the frozen unrelated texts."""
    flat = [t for s in unrelated for t in s]
    out = []
    for k in range(n):
        start = (k * 64) % len(flat)
        seq = (flat[start:] + flat[:start]) * (length // len(flat) + 2)
        out.append(seq[:length])
    return out


def admit(a, now):
    """Exact-pod/source/brief binding (as w7_steering.compute) plus the retry's setup/science clock."""
    if (a.get("issuer") != "integrator" or not os.environ.get("RUNPOD_POD_ID")
            or a.get("pod_id") != os.environ["RUNPOD_POD_ID"]
            or a.get("experiment") != "W7" or a.get("mechanism_budget") != "w7" or a.get("gpu_count") != 1):
        raise ValueError("W7 retry requires an exact-pod one-GPU integrator assignment")
    if (a.get("brief_registered") is not True or a.get("brief_pushed") is not True
            or a.get("external_hardstop_verified") is not True
            or a.get("brief_sha256") != P.sha(P.ROOT / P.BRIEF)
            or a.get("source_files") != W.source_hashes()
            or a.get("runtime_driver", {}).get("sha256") != P.sha(DRIVER)
            or a.get("executed_source_files") != {**W.source_hashes(), DRIVER_REL: P.sha(DRIVER)}):
        raise ValueError("W7 retry brief/source/driver/hardstop binding mismatch")
    for field in ("source_commit", "brief_commit"):
        value = a.get(field, "")
        if len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("missing pinned " + field)
    if a.get("environment") != ENVIRONMENT or not sys.executable.startswith(ENVIRONMENT):
        raise ValueError("W7 retry must run in " + ENVIRONMENT)
    created = float(a["provider_created_epoch"]); allocated = float(a["allocated_gpu_seconds"])
    previous = float(a["previous_gpu_seconds"]); hardstop = float(a["provider_hardstop_epoch"])
    remaining = float(a["remaining_science_gpu_seconds"])
    if (not all(math.isfinite(v) for v in (created, allocated, previous, hardstop, remaining))
            or previous < 504.8 or allocated <= 0 or allocated > remaining + 1e-9
            or previous + allocated > W.CAP_SECONDS + 1e-9
            or float(a.get("setup_allowance_seconds", -1)) != SETUP_ALLOWANCE
            or hardstop > created + SETUP_ALLOWANCE + allocated + 1e-6
            or not created <= now < created + SETUP_ALLOWANCE):
        raise ValueError("W7 retry cumulative science / setup allowance / hardstop clock violated")
    ledger = P.ROOT / "results/g_agreement/compute.jsonl"
    used = sum(float(r["gpu_hours"]) * 3600 for r in P.rows(ledger)
               if r.get("extra", {}).get("mechanism_budget") == "w7") if ledger.exists() else 0
    if max(used, previous) + allocated > W.CAP_SECONDS + 1e-9:
        raise ValueError("W7 retry allocation exceeds remaining cumulative budget")
    return created, allocated


def plan(a_args, items, unrelated):
    """Warm-up coverage plan: every production path and batch length; unrelated filler only."""
    paths = [{"path": "text_nll_unsteered", "lengths": sorted(set(_batch_lengths(unrelated, a_args.batch)))},
             {"path": "text_nll_steered", "lengths": sorted(set(_batch_lengths(unrelated, a_args.batch)))}]
    lens = set()
    for f in W.FEATURES:
        lens |= set(_batch_lengths([r["ids"] for r in items if r["feature"] == f], a_args.batch))
    paths += [{"path": "token_logp_unsteered", "lengths": sorted(lens)},
              {"path": "token_logp_steered", "lengths": sorted(lens)}]
    return paths


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--assets", type=Path, required=True)
    p.add_argument("--assignment", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--batch", type=int, default=4)
    p.add_argument("--dry-admission", action="store_true", help="Mac rehearsal: checks, admission and warm-up plan only")
    a = p.parse_args(argv)
    from .run import _assets
    # Input checks: identical to w7_steering.run.
    seal = P.verify(a.bundle, "INPUT_SEAL.json")
    expected = {"items.input.jsonl", "unrelated.input.jsonl", "directions.npz", "recipe.json", "provenance.json"}
    if set(seal["files"]) != expected or W.read(a.bundle / "recipe.json") != W.RECIPE:
        raise ValueError("W7 input/recipe differs from frozen operational plan")
    if any(a.bundle.rglob("*.DO_NOT_STAGE.*")):
        raise ValueError("labels must stay off the W7 worker")
    assignment = W.read(a.assignment)
    if assignment.get("input_seal_sha256") != P.sha(a.bundle / "INPUT_SEAL.json") or assignment.get("manifest_committed") is not True:
        raise ValueError("W7 assignment must bind the committed input seal")
    items = P.rows(a.bundle / "items.input.jsonl")
    unrelated = [r["ids"] for r in P.rows(a.bundle / "unrelated.input.jsonl")]
    if (len({r["id"] for r in items}) != 120 or any(sum(r["feature"] == f for r in items) != 60 for f in W.FEATURES)
            or len(unrelated) != 16 or any(len(s) != 64 for s in unrelated)):
        raise ValueError("W7 frozen population incomplete")
    with np.load(a.bundle / "directions.npz", allow_pickle=False) as z:
        vectors = {f: z[f] for f in W.FEATURES}
    for x in vectors.values():
        if (x.ndim != 2 or x.shape[0] != 6 or not np.isfinite(x).all() or np.linalg.norm(x[0]) <= 0
                or not np.allclose(np.linalg.norm(x, axis=1), np.linalg.norm(x[0]), rtol=1e-5)):
            raise ValueError("W7 needs probe plus five same-norm controls")
    warm_plan = plan(a, items, unrelated)
    cal_tokens_unit = sum(map(len, unrelated))
    n_cal_steered = len(W.FEATURES) * len(W.MULTIPLIERS) * 6 * 2
    out_tokens = {f: sum(len(r["ids"]) for r in items if r["feature"] == f) for f in W.FEATURES}
    work = {"calibration_tokens_per_unit": cal_tokens_unit, "calibration_steered_units": n_cal_steered,
            "outcome_tokens_per_unit": out_tokens, "outcome_steered_units_per_feature": 3 * 6 * 2}
    if a.dry_admission:
        now = float(assignment["provider_created_epoch"]) + 1
        os.environ.setdefault("RUNPOD_POD_ID", assignment["pod_id"])
        try:
            admit(assignment, now)
            admitted = "ADMITTED"
        except ValueError as e:
            admitted = "REFUSED: " + str(e)
        print(json.dumps({"dry_admission": admitted, "warm_plan": warm_plan, "work": work,
                          "driver_sha256": P.sha(DRIVER)}, indent=1))
        return 0
    created, allocated = admit(assignment, time.time())
    assets = _assets(a.assets, ("model",))
    a.out.mkdir(parents=True, exist_ok=False)
    runtime = {"schema": "w7-retry-runtime-v1", "driver_sha256": P.sha(DRIVER), "python": sys.executable,
               "provider_created_epoch": created, "setup_allowance_seconds": SETUP_ALLOWANCE,
               "allocated_science_seconds": allocated, "work": work, "warm_plan": warm_plan}
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", WANDB_MODE="disabled")
    # ---- setup: load + unscored warm-up (outside science) ----
    setup_started = time.time(); runtime["setup_started_epoch"] = setup_started
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    model = AutoModelForCausalLM.from_pretrained(assets["model"], dtype=torch.bfloat16, device_map="cuda", local_files_only=True).eval()
    tokenizer = AutoTokenizer.from_pretrained(assets["model"], local_files_only=True)
    tokens = {}
    for f, spec in W.FEATURES.items():
        ids = tokenizer.encode(spec["token"], add_special_tokens=False)
        if len(ids) != 1:
            raise ValueError("registered W7 outcome must be a single native token")
        tokens[f] = ids[0]
    runtime["model_loaded_epoch"] = time.time()
    probe = vectors[next(iter(W.FEATURES))][0]
    warm_log = []
    t = time.time()
    W.text_nll(model, unrelated[:a.batch], batch=a.batch)
    W.text_nll(model, unrelated[:a.batch], probe, W.MULTIPLIERS[0], a.batch)
    W.text_nll(model, unrelated[:a.batch], probe, -W.MULTIPLIERS[0], a.batch)
    _sync(); warm_log.append({"path": "text_nll_unsteered+steered", "length": 64, "seconds": round(time.time() - t, 3)})
    some_token = next(iter(tokens.values()))
    for length in warm_plan[2]["lengths"]:
        seqs = _filler(unrelated, length, a.batch)
        t = time.time()
        W.token_logp(model, seqs, some_token, batch=a.batch)
        W.token_logp(model, seqs, some_token, probe, W.MULTIPLIERS[0], a.batch)
        _sync(); warm_log.append({"path": "token_logp_unsteered+steered", "length": length, "seconds": round(time.time() - t, 3)})
    setup_done = time.time()
    runtime.update(warmup=warm_log, setup_completed_epoch=setup_done, setup_seconds=setup_done - created,
                   warmup_scored=False, warmup_in_timing_sample=False)
    if setup_done >= created + SETUP_ALLOWANCE:
        runtime["status"] = "SETUP_OVERRUN_STOP"
        P.dump(a.out / "retry_runtime.json", runtime)
        raise SystemExit("W7 retry setup exceeded the 900 s allowance")
    # ---- science: own clock ----
    science_started = time.time(); deadline = science_started + allocated
    runtime.update(science_started_epoch=science_started, science_deadline_epoch=deadline,
                   compute_window_end_epoch=deadline - RESERVE)
    P.dump(a.out / "retry_runtime.json", runtime)

    def remaining_s():
        return deadline - RESERVE - time.time()

    def nofit(gate):
        runtime["status"] = "NO_FIT_STOP_" + gate["gate"]
        P.dump(a.out / "forecast.json", {"gates": runtime.get("gates", [])})
        P.dump(a.out / "retry_runtime.json", runtime)
        raise SystemExit("W7 retry NO_FIT at " + gate["gate"])

    runtime["gates"] = []
    with P.logged("mechanism_w7_retry", gpu=True, extra={"mechanism_budget": "w7", "pod_id": assignment["pod_id"],
                                                          "accounting": "science only; setup outside"}), \
            P.compute_window({"deadline_epoch": deadline}):
        t = time.time(); baseline_nll = W.text_nll(model, unrelated, batch=a.batch); _sync()
        runtime["calibration_baseline_seconds"] = time.time() - t
        calibration, cal_units = {}, []
        gate1_done = False
        for f, x in vectors.items():
            ratios = np.zeros((len(W.MULTIPLIERS), 6, 2))
            for i, dose in enumerate(W.MULTIPLIERS):
                for j, vector in enumerate(x):
                    for k, sign in enumerate((-1, 1)):
                        t = time.time()
                        nll = W.text_nll(model, unrelated, vector, sign*dose, a.batch); _sync()
                        cal_units.append({"feature": f, "dose": dose, "arm": j, "sign": sign,
                                          "tokens": cal_tokens_unit, "seconds": time.time() - t})
                        ratios[i, j, k] = math.exp(min(700, nll - baseline_nll))
                        if not gate1_done and len(cal_units) == N_GATE:
                            per_tok = statistics.median(u["seconds"] / u["tokens"] for u in cal_units)
                            rem_cal = (n_cal_steered - N_GATE) * cal_tokens_unit
                            rem_out = sum(out_tokens.values()) * (1 + 3 * 6 * 2)
                            forecast = MARGIN * per_tok * (rem_cal + rem_out)
                            gate = {"gate": "gate1_calibration_path", "path": "text_nll_steered (bs=%d, len 64)" % a.batch,
                                    "raw_units": cal_units[:N_GATE], "median_seconds_per_token": per_tok,
                                    "remaining_tokens": {"calibration": rem_cal, "outcomes_at_calibration_rate": rem_out},
                                    "forecast_seconds_x1_5": forecast, "remaining_science_seconds_before_reserve": remaining_s(),
                                    "science_deadline_epoch": deadline}
                            runtime["gates"].append(gate); gate1_done = True
                            P.dump(a.out / "retry_runtime.json", runtime)
                            if forecast > remaining_s():
                                nofit(gate)
                P.dump(a.out / f"calibration.partial.{f}.json", {"completed": i+1, "ratios": ratios[:i+1].tolist()})
            calibration[f] = {"multipliers": W.MULTIPLIERS, "ppl_ratios": ratios.tolist(),
                              "doses": W.choose_doses(W.MULTIPLIERS, ratios)}
        P.dump(a.out / "calibration.json", {"baseline_nll": baseline_nll, "rows": calibration})
        P.seal(a.out, ["calibration.json"], "INPUTS_FROZEN_W7_DOSES_BEFORE_OUTCOMES")
        runtime["calibration_units"] = cal_units
        scores, out_units, base_rate = [], [], None
        gate2_done = False
        feats = list(W.FEATURES)
        for fi, (f, spec) in enumerate(W.FEATURES.items()):
            selected = [r for r in items if r["feature"] == f]
            seqs = [r["ids"] for r in selected]
            t = time.time(); baseline = W.token_logp(model, seqs, tokens[f], batch=a.batch); _sync()
            if base_rate is None:
                base_rate = (time.time() - t) / out_tokens[f]
            scores.extend({"id": r["id"], "feature": f, "cluster": r["cluster"], "arm": "baseline", "dose": 0., "sign": 0,
                           "logp": float(lp)} for r, lp in zip(selected, baseline))
            for dose in calibration[f]["doses"]:
                for j, vector in enumerate(vectors[f]):
                    for sign in (-1, 1):
                        t = time.time()
                        lp = W.token_logp(model, seqs, tokens[f], vector, sign*dose, a.batch); _sync()
                        out_units.append({"feature": f, "dose": dose, "arm": j, "sign": sign, "tokens": out_tokens[f],
                                          "seconds": time.time() - t})
                        chunk = [{"id": r["id"], "feature": f, "cluster": r["cluster"], "arm": "probe" if j == 0 else f"random:{j}",
                                  "dose": dose, "sign": sign, "logp": float(v)} for r, v in zip(selected, lp)]
                        scores.extend(chunk)
                        with (a.out / "scores.partial.jsonl").open("a") as partial:
                            for row in chunk:
                                partial.write(json.dumps(row, allow_nan=False) + "\n")
                        if not gate2_done and len(out_units) == N_GATE:
                            per_tok = statistics.median(u["seconds"] / u["tokens"] for u in out_units)
                            rem_steered = (3 * 6 * 2 - N_GATE) * out_tokens[f] + sum(3 * 6 * 2 * out_tokens[g] for g in feats[fi+1:])
                            rem_base = sum(out_tokens[g] for g in feats[fi+1:])
                            forecast = MARGIN * (per_tok * rem_steered + base_rate * rem_base)
                            gate = {"gate": "gate2_outcome_path", "path": "token_logp_steered (bs=%d)" % a.batch,
                                    "raw_units": out_units[:N_GATE], "median_seconds_per_token": per_tok,
                                    "baseline_seconds_per_token": base_rate,
                                    "remaining_tokens": {"steered": rem_steered, "baseline": rem_base},
                                    "forecast_seconds_x1_5": forecast, "remaining_science_seconds_before_reserve": remaining_s(),
                                    "science_deadline_epoch": deadline}
                            runtime["gates"].append(gate); gate2_done = True
                            P.dump(a.out / "retry_runtime.json", runtime)
                            if forecast > remaining_s():
                                nofit(gate)
        runtime["outcome_units"] = out_units
        P.jsonl(a.out / "scores.w7.jsonl", scores)
        P.dump(a.out / "forecast.json", {"gates": runtime["gates"]})
        P.dump(a.out / "provenance.json", {"input_seal_sha256": P.sha(a.bundle / "INPUT_SEAL.json"),
               "dose_seal_sha256": P.sha(a.out / "INPUT_SEAL.json"), "assignment_sha256": P.sha(a.assignment),
               "construction_block": 44, "target": "Qwen3.6-27B", "science_cap_seconds": W.CAP_SECONDS,
               "runtime_driver_sha256": P.sha(DRIVER), "environment": ENVIRONMENT})
        runtime["status"] = "SCORES_SEALED"; runtime["science_seconds"] = time.time() - science_started
        P.dump(a.out / "retry_runtime.json", runtime)
        P.seal(a.out, ["scores.w7.jsonl", "calibration.json", "forecast.json", "provenance.json", "retry_runtime.json"],
               "SCORES_SEALED_W7")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
