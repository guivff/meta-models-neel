"""§76 W7: guarded block-44 target behaviour, separate from frozen ar_tests.py.

Prepare a label-free bundle locally, then run on an integrator-assigned pod.
Doses are calibrated only on unrelated text before any W7 target score is read.
Operational choices are fixed in mechanism/ASAP_HANDOFF.md before model work.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import time

import numpy as np

from . import protocol as P

CAP_SECONDS = 3600
FEATURES = {"prose_paren": {"token": ")", "positive_value": "inside", "negative_value": "outside", "predicted_sign": 1},
            "table_column": {"token": "|", "positive_value": "first", "negative_value": "later", "predicted_sign": -1}}
MULTIPLIERS = [2. ** k for k in range(-5, 4)]
RECIPE = {"block": 44, "position": "last real prefix token", "n_items_per_row": 60,
          "n_random": 5, "seed": P.SEED, "signed_doses": [-1, 1],
          "candidate_multipliers": MULTIPLIERS, "ppl_max_ratio": 1.1,
          "unrelated_n": 16, "unrelated_tokens": 64,
          "dose_scale": "positive dev class-mean projection gap along raw unit probe",
          "edit": "plain additive; no renormalization",
          "primary": "mean across three doses of predicted-sign half (+ minus -), probe minus mean five randoms",
          "features": FEATURES}


def read(path):
    return json.loads(Path(path).read_text())


def source_hashes():
    return {**P.code_hashes(), "projects/g_agreement/blindspot/w7_steering.py": P.sha(__file__)}


@contextmanager
def compute(assignment):
    """Exact-pod/source/brief binding and smoke-sized science, setup separate."""
    a = read(assignment)
    if (a.get("issuer") != "integrator" or not os.environ.get("RUNPOD_POD_ID")
        or a.get("pod_id") != os.environ["RUNPOD_POD_ID"]
        or a.get("experiment") != "W7" or a.get("mechanism_budget") != "w7"
        or a.get("gpu_count") != 1):
        raise ValueError("W7 requires an exact-pod one-GPU integrator assignment")
    if (a.get("brief_registered") is not True or a.get("brief_pushed") is not True
        or a.get("external_hardstop_verified") is not True
        or a.get("brief_sha256") != P.sha(P.ROOT / P.BRIEF)
        or a.get("source_files") != source_hashes()):
        raise ValueError("W7 brief/source/hardstop binding mismatch")
    for field in ("source_commit", "brief_commit"):
        value = a.get(field, "")
        if len(value) != 40 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("missing pinned " + field)
    created, deadline, budget, previous = (float(a[k]) for k in
        ("provider_created_epoch", "deadline_epoch", "allocated_gpu_seconds", "previous_gpu_seconds"))
    setup = float(a.get("setup_allowance_seconds", 0))
    forecast = float(a.get("smoke_forecast_seconds", float("nan")))
    if (not math.isfinite(forecast) or not 0 < forecast <= CAP_SECONDS):
        raise ValueError("W7 smoke forecast exceeds cap or is invalid; report before launch")
    cap = min(CAP_SECONDS, 1.5 * forecast)
    if (not all(math.isfinite(v) for v in (created, deadline, budget, previous, setup))
        or not 0 <= setup <= 900
        or previous < 0 or budget <= 0 or previous + budget > cap
        or not 0 < deadline - created <= setup + budget or not created <= time.time() < deadline - 180):
        raise ValueError("W7 cumulative cap/deadline/retrieval reserve exceeded")
    budget_round = a.get("budget_round", "legacy")
    if budget_round not in ("legacy", "2026-10-23-1245"):
        raise ValueError("unregistered W7 budget round")
    ledger = P.ROOT / "results/g_agreement/compute.jsonl"
    used = sum(float(r["gpu_hours"]) * 3600 for r in P.rows(ledger)
               if r.get("extra", {}).get("mechanism_budget") == "w7"
               and r.get("extra", {}).get("budget_round", "legacy") == budget_round) if ledger.exists() else 0
    if max(used, previous) + budget > cap + 1e-9:
        raise ValueError("W7 allocation exceeds remaining cumulative budget")
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", WANDB_MODE="disabled")
    with P.logged("mechanism_w7", gpu=True, extra={"mechanism_budget": "w7", "budget_round": budget_round, "pod_id": a["pod_id"]}), P.compute_window(a):
        yield a


def random_vectors(probe, seed=P.SEED):
    """Five fixed isotropic directions, each with exactly the probe's raw norm."""
    probe = np.asarray(probe, dtype=np.float32)
    if probe.ndim != 1 or not np.isfinite(probe).all() or np.linalg.norm(probe) <= 0:
        raise ValueError("invalid raw probe direction")
    x = np.random.default_rng(seed).normal(size=(5, len(probe)))
    return (x / np.linalg.norm(x, axis=1, keepdims=True) * np.linalg.norm(probe)).astype(np.float32)


def choose_doses(candidates, ratios):
    """Largest tested safe maximum whose half and quarter also pass, both signs/all arms."""
    candidates, ratios = np.asarray(candidates, float), np.asarray(ratios, float)
    if (len(candidates) != len(MULTIPLIERS) or ratios.shape != (len(candidates), 6, 2)
        or not np.isfinite(candidates).all() or not np.isfinite(ratios).all()
        or np.any(candidates <= 0) or np.any(ratios <= 0)
        or not np.allclose(candidates[1:], 2 * candidates[:-1])):
        raise ValueError("invalid PPL calibration grid")
    safe = (ratios <= 1.1).all(axis=(1, 2))
    for i in range(len(candidates) - 1, 1, -1):
        if safe[i-2:i+1].all():
            return candidates[i-2:i+1].tolist()
    raise ValueError("no three doses meet the unrelated-text PPL constraint")


def priority_vectors(priority, seal_name, bank_sha, label_sha):
    """Read W-core's actual training export without changing its files or fits."""
    seal = P.verify(priority, seal_name)
    if not {"probe_directions.json", "probe_directions.npz"} <= set(seal["files"]):
        raise ValueError("priority directions are not covered by their seal")
    meta = read(priority / "probe_directions.json")
    training = meta.get("schema") == "blindspot-priority-training-export-v1"
    if training:
        if (seal.get("status") != "SEALED_TRAINING_ONLY_EXPORT"
            or meta.get("status") != "TRAINING_ONLY_EARLY_EXPORT"
            or meta.get("source_labels_sha256") != label_sha):
            raise ValueError("priority training export status/label lineage mismatch")
        provenance = meta
    else:
        if "provenance.json" not in seal["files"]:
            raise ValueError("legacy priority export lacks sealed provenance")
        provenance = read(priority / "provenance.json")
        if provenance.get("direction_space") != "raw_block44":
            raise ValueError("priority directions must use raw block44 space")
    if provenance.get("input_seal_sha256") != bank_sha or meta.get("fit_split") != "dev":
        raise ValueError("priority directions need the same bank and dev-only fitting")
    vectors, audit = {}, {}
    with np.load(priority / "probe_directions.npz", allow_pickle=False) as z:
        for feature, spec in FEATURES.items():
            matches = [r for r in meta["rows"] if r["feature"] == feature and r["layer"] == 44]
            if len(matches) != 1:
                raise ValueError("missing/duplicate priority direction: " + feature)
            row = matches[0]
            if (row.get("fit_split") != "dev" or row.get("positive_value") != spec["positive_value"]
                or row.get("orientation_flipped") is not False or "test_class_mean_projection_gap" in row):
                raise ValueError("priority export must be A-positive and dev-only, without test means")
            prefix = row["array_prefix"]
            unit = np.asarray(z[prefix + "__unit"], np.float32)
            gap = float(row["dev_class_mean_projection_gap"])
            if (not np.isfinite(gap) or gap <= 0 or unit.ndim != 1 or not np.isfinite(unit).all()
                or not np.isclose(np.linalg.norm(unit), 1, atol=1e-5)):
                raise ValueError("invalid raw unit direction/dev gap")
            if training:
                expected_keys = {"unit_direction": prefix + "__unit", "raw_coefficient": prefix + "__coef",
                                 "raw_mean_A": prefix + "__mean_A", "raw_mean_B": prefix + "__mean_B"}
                if row.get("arrays") != expected_keys or row.get("negative_value") != spec["negative_value"]:
                    raise ValueError("training array/value mapping mismatch")
                coef, mean_a, mean_b = [np.asarray(z[expected_keys[k]], float) for k in
                                       ("raw_coefficient", "raw_mean_A", "raw_mean_B")]
                if (any(x.shape != unit.shape or not np.isfinite(x).all() for x in (coef, mean_a, mean_b))
                    or not math.isfinite(float(row["raw_intercept"])) or np.linalg.norm(coef) <= 0
                    or not np.allclose(coef / np.linalg.norm(coef), unit, rtol=1e-5, atol=1e-6)
                    or not np.isclose((mean_a - mean_b) @ unit, gap, rtol=1e-5, atol=1e-5)
                    or row["n_A"] <= 0 or row["n_B"] <= 0 or row["n_A"] + row["n_B"] != row["dev_n"]):
                    raise ValueError("raw coefficient/class means disagree with training direction/gap")
            probe = unit * gap
            vectors[feature] = np.vstack([probe, random_vectors(probe)])
            audit[feature] = {"array_prefix": prefix, "fit_split": "dev", "layer": 44,
                "positive_value": spec["positive_value"], "negative_value": spec["negative_value"],
                "dev_class_mean_projection_gap": gap, "n_dev": row.get("dev_n"),
                "raw_means_coefficient_verified": training}
    return vectors, audit


def prepare(a):
    """Consume W-core's sealed dev-only raw probe export; select 30 opposite-value test pairs."""
    from . import ar_tests as AR
    bank_seal = P.verify(a.bank, "INPUT_SEAL.json")
    for name in ("items.input.jsonl", "provenance.json"):
        if name not in bank_seal["files"]:
            raise ValueError("bank is not sealed")
    vectors, direction_audit = priority_vectors(a.priority, a.priority_seal,
        P.sha(a.bank / "INPUT_SEAL.json"), read(a.bank / "provenance.json")["labels_sha256"])
    items = P.rows(a.bank / "items.input.jsonl")
    labels = AR._labels(a.bank, a.labels, items)
    by_id = {r["id"]: r for r in items}
    selected = []
    for f in FEATURES:
        pairs = set()
        for it in items:
            donor = it.get("donor_id")
            if it["feature"] == f and labels[it["id"]]["split"] == "test" and donor in by_id:
                other = by_id[donor]
                if (other["feature"] != f or labels[donor]["split"] != "test"
                    or labels[donor]["value"] == labels[it["id"]]["value"]
                    or labels[donor]["cluster"] != labels[it["id"]]["cluster"]
                    or len(other["ids"]) != len(it["ids"])):
                    raise ValueError("invalid matched W7 test pair")
                pairs.add(tuple(sorted((it["id"], donor))))
        ranked = sorted(pairs, key=lambda p: hashlib.sha256(f"{P.SEED}:{p}".encode()).hexdigest())
        if len(ranked) < 30:
            raise ValueError("W7 needs 30 opposite-value test pairs per row")
        for pair in ranked[:30]:
            for iid in pair:
                it = by_id[iid]
                selected.append({"id": iid, "feature": f, "ids": it["ids"], "cluster": labels[iid]["cluster"]})
    unrelated = P.rows(a.unrelated)
    if (len(unrelated) < 16 or len({r["id"] for r in unrelated}) != len(unrelated)
        or any(len(r["ids"]) < 64 for r in unrelated)
        or {r["id"] for r in unrelated} & {r["id"] for r in items}):
        raise ValueError("need >=16 distinct unrelated texts of >=64 tokens, disjoint from W1")
    unrelated = sorted(unrelated, key=lambda r: hashlib.sha256(f"{P.SEED}:{r['id']}".encode()).hexdigest())[:16]
    a.out.mkdir(parents=True, exist_ok=False)
    P.jsonl(a.out / "items.input.jsonl", selected)
    P.jsonl(a.out / "unrelated.input.jsonl", [{"id": r["id"], "ids": r["ids"][:64]} for r in unrelated])
    np.savez(a.out / "directions.npz", **vectors)
    P.dump(a.out / "recipe.json", RECIPE)
    P.dump(a.out / "provenance.json", {"input_seal_sha256": P.sha(a.bank / "INPUT_SEAL.json"),
           "priority_seal_sha256": P.sha(a.priority / a.priority_seal), "unrelated_source_sha256": P.sha(a.unrelated),
           "direction_space": "raw_block44", "direction_fit_split": "dev", "directions": direction_audit})
    P.seal(a.out, ["items.input.jsonl", "unrelated.input.jsonl", "directions.npz", "recipe.json", "provenance.json"], "INPUTS_FROZEN_W7")


def token_logp(model, seqs, token, vector=None, dose=0, batch=4):
    import torch
    from contextlib import nullcontext
    from mats.capture import logits_at, steer
    positions = [[-1] for _ in seqs]
    context = nullcontext() if vector is None else steer(model, 44, torch.as_tensor(vector), positions, dose=dose, preserve_norm=False)
    with context:
        logits = logits_at(model, seqs, positions, batch_size=batch)[:, 0]
    return torch.log_softmax(logits, -1)[:, token].numpy()


def text_nll(model, seqs, vector=None, dose=0, batch=4):
    """Teacher-forced unrelated-text NLL, all positions edited, right padded by mats."""
    import torch
    from contextlib import nullcontext
    from mats.capture import logits_at, steer
    total, count = 0., 0
    for start in range(0, len(seqs), batch):
        part = seqs[start:start+batch]
        if len({len(s) for s in part}) != 1 or min(map(len, part)) < 2:
            raise ValueError("PPL texts must share frozen length >=2")
        positions = [list(range(len(s)-1)) for s in part]
        context = nullcontext() if vector is None else steer(model, 44, torch.as_tensor(vector), None, dose=dose, preserve_norm=False)
        with context:
            logits = logits_at(model, part, positions, batch_size=batch)
        targets = torch.tensor([s[1:] for s in part])
        losses = -torch.log_softmax(logits, -1).gather(-1, targets[..., None])[..., 0]
        total += float(losses.sum()); count += losses.numel()
    return total / count


def run(a):
    from .run import _assets
    seal = P.verify(a.bundle, "INPUT_SEAL.json")
    expected = {"items.input.jsonl", "unrelated.input.jsonl", "directions.npz", "recipe.json", "provenance.json"}
    if set(seal["files"]) != expected or read(a.bundle / "recipe.json") != RECIPE:
        raise ValueError("W7 input/recipe differs from frozen operational plan")
    if any(a.bundle.rglob("*.DO_NOT_STAGE.*")):
        raise ValueError("labels must stay off the W7 worker")
    assignment = read(a.assignment)
    if assignment.get("input_seal_sha256") != P.sha(a.bundle / "INPUT_SEAL.json") or assignment.get("manifest_committed") is not True:
        raise ValueError("W7 assignment must bind the committed input seal")
    items = P.rows(a.bundle / "items.input.jsonl")
    unrelated = [r["ids"] for r in P.rows(a.bundle / "unrelated.input.jsonl")]
    if (len({r["id"] for r in items}) != 120 or any(sum(r["feature"] == f for r in items) != 60 for f in FEATURES)
        or len(unrelated) != 16 or any(len(s) != 64 for s in unrelated)):
        raise ValueError("W7 frozen population incomplete")
    with np.load(a.bundle / "directions.npz", allow_pickle=False) as z:
        vectors = {f: z[f] for f in FEATURES}
    for x in vectors.values():
        if x.ndim != 2 or x.shape[0] != 6 or not np.isfinite(x).all() or np.linalg.norm(x[0]) <= 0 or not np.allclose(np.linalg.norm(x, axis=1), np.linalg.norm(x[0]), rtol=1e-5):
            raise ValueError("W7 needs probe plus five same-norm controls")
    assets = _assets(a.assets, ("model",))
    a.out.mkdir(parents=True, exist_ok=False)
    with compute(a.assignment) as admitted:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        model = AutoModelForCausalLM.from_pretrained(assets["model"], dtype=torch.bfloat16, device_map="cuda", local_files_only=True).eval()
        tokenizer = AutoTokenizer.from_pretrained(assets["model"], local_files_only=True)
        tokens = {}
        for f, spec in FEATURES.items():
            ids = tokenizer.encode(spec["token"], add_special_tokens=False)
            if len(ids) != 1:
                raise ValueError("registered W7 outcome must be a single native token")
            tokens[f] = ids[0]
        calibration_started = time.perf_counter()
        baseline_nll = text_nll(model, unrelated, batch=a.batch)
        calibration = {}
        for f, x in vectors.items():
            ratios = np.zeros((len(MULTIPLIERS), 6, 2))
            for i, dose in enumerate(MULTIPLIERS):
                for j, vector in enumerate(x):
                    for k, sign in enumerate((-1, 1)):
                        nll = text_nll(model, unrelated, vector, sign*dose, a.batch)
                        ratios[i, j, k] = math.exp(min(700, nll-baseline_nll))
                # Save completed calibration even if the process is stopped later.
                P.dump(a.out / f"calibration.partial.{f}.json", {"completed": i+1, "ratios": ratios[:i+1].tolist()})
            calibration[f] = {"multipliers": MULTIPLIERS, "ppl_ratios": ratios.tolist(), "doses": choose_doses(MULTIPLIERS, ratios)}
        P.dump(a.out / "calibration.json", {"baseline_nll": baseline_nll, "rows": calibration})
        P.seal(a.out, ["calibration.json"], "INPUTS_FROZEN_W7_DOSES_BEFORE_OUTCOMES")
        calibration_seconds = time.perf_counter() - calibration_started
        calibration_tokens = sum(map(len, unrelated)) * (1 + len(FEATURES)*len(MULTIPLIERS)*6*2)
        outcome_tokens = sum(len(r["ids"]) for r in items) * 37
        forecast = 1.5 * calibration_seconds * outcome_tokens / calibration_tokens
        remaining = float(admitted["deadline_epoch"]) - 180 - time.time()
        P.dump(a.out / "forecast.json", {"calibration_seconds": calibration_seconds,
               "outcome_seconds_with_1_5_margin": forecast, "remaining_seconds": remaining})
        if forecast > remaining:
            raise ValueError("W7 measured forecast does not fit remaining allocation")
        scores = []
        for f, spec in FEATURES.items():
            selected = [r for r in items if r["feature"] == f]
            seqs = [r["ids"] for r in selected]
            baseline = token_logp(model, seqs, tokens[f], batch=a.batch)
            scores.extend({"id": r["id"], "feature": f, "cluster": r["cluster"], "arm": "baseline", "dose": 0., "sign": 0, "logp": float(lp)} for r, lp in zip(selected, baseline))
            for dose in calibration[f]["doses"]:
                for j, vector in enumerate(vectors[f]):
                    for sign in (-1, 1):
                        lp = token_logp(model, seqs, tokens[f], vector, sign*dose, a.batch)
                        chunk = [{"id": r["id"], "feature": f, "cluster": r["cluster"], "arm": "probe" if j == 0 else f"random:{j}", "dose": dose, "sign": sign, "logp": float(v)} for r, v in zip(selected, lp)]
                        scores.extend(chunk)
                        with (a.out / "scores.partial.jsonl").open("a") as partial:
                            for row in chunk:
                                partial.write(json.dumps(row, allow_nan=False) + "\n")
        P.jsonl(a.out / "scores.w7.jsonl", scores)
        P.dump(a.out / "provenance.json", {"input_seal_sha256": P.sha(a.bundle / "INPUT_SEAL.json"),
               "dose_seal_sha256": P.sha(a.out / "INPUT_SEAL.json"), "assignment_sha256": P.sha(a.assignment),
               "construction_block": 44, "target": "Qwen3.6-27B", "science_cap_seconds": CAP_SECONDS})
        P.seal(a.out, ["scores.w7.jsonl", "calibration.json", "forecast.json", "provenance.json"], "SCORES_SEALED_W7")


def analyse_scores(scores, calibration):
    from mats.metrics import cluster_bootstrap
    results = []
    for f, spec in FEATURES.items():
        rows = [r for r in scores if r["feature"] == f]
        ids = sorted({r["id"] for r in rows})
        if len(ids) != 60:
            raise ValueError("W7 requires 60 scored test items per row")
        doses = calibration[f]["doses"]
        if len(doses) != 3 or any(d <= 0 for d in doses) or len(set(doses)) != 3:
            raise ValueError("W7 needs three distinct frozen doses")
        if choose_doses(calibration[f]["multipliers"], calibration[f]["ppl_ratios"]) != doses:
            raise ValueError("W7 doses do not match the sealed PPL calibration")
        keys = [(r["id"], r["arm"], r["dose"], r["sign"]) for r in rows]
        expected = {(i, arm, d, s) for i in ids for arm in ("probe", *[f"random:{j}" for j in range(1, 6)]) for d in doses for s in (-1, 1)} | {(i, "baseline", 0., 0) for i in ids}
        if len(set(keys)) != len(keys) or set(keys) != expected or any(not math.isfinite(r["logp"]) or r["logp"] > 0 for r in rows):
            raise ValueError("incomplete/duplicate/nonfinite W7 score grid")
        lookup = dict(zip(keys, rows))
        if any(len({r["cluster"] for r in rows if r["id"] == i}) != 1 for i in ids):
            raise ValueError("item cluster changed across W7 arms")
        def contrast(i, arm, d):
            return spec["predicted_sign"] * (lookup[i, arm, d, 1]["logp"] - lookup[i, arm, d, -1]["logp"]) / 2
        per_dose = np.array([[contrast(i, "probe", d) - np.mean([contrast(i, f"random:{j}", d) for j in range(1, 6)]) for d in doses] for i in ids])
        values = per_dose.mean(1)
        clusters = np.array([lookup[i, "baseline", 0., 0]["cluster"] for i in ids])
        if len(set(clusters.tolist())) < 2:
            raise ValueError("W7 needs multiple template clusters")
        ci = cluster_bootstrap(lambda idx: float(values[idx].mean()), clusters, n_boot=2000, seed=P.SEED)
        effect = float(values.mean())
        results.append({"feature": f, "n": len(ids), "effect": effect, "ci95": list(ci),
                        "per_dose_mean": per_dose.mean(0).tolist(), "doses": doses,
                        "rule_met": bool(effect > 0 and ci[0] > 0)})
    if any(r["feature"] not in FEATURES for r in scores):
        raise ValueError("unexpected W7 feature")
    return {"status": "CONFIRMED" if all(r["rule_met"] for r in results) else "NOT MET",
            "rows": results, "construction_block": 44, "outcome_tokens": FEATURES,
            "primary": RECIPE["primary"], "W1_three_way_dissociation": "requires separately confirmed W1 reader results"}


def analyse(a):
    seal = P.verify(a.scores, "SCORE_SEAL.json")
    if not {"scores.w7.jsonl", "calibration.json", "provenance.json"} <= set(seal["files"]):
        raise ValueError("W7 score seal is incomplete")
    result = analyse_scores(P.rows(a.scores / "scores.w7.jsonl"), read(a.scores / "calibration.json")["rows"])
    a.out.mkdir(parents=True, exist_ok=False)
    P.dump(a.out / "metrics.w7.json", {**result, "score_seal_sha256": P.sha(a.scores / "SCORE_SEAL.json")})
    P.seal(a.out, ["metrics.w7.json"], "SCORES_SEALED_W7_ANALYSIS")
    print("HANDOFF W7: " + result["status"] + "; block44; " + str(a.out / "metrics.w7.json"))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("prepare")
    for name in ("bank", "labels", "priority", "unrelated", "out"):
        prep.add_argument("--" + name, required=True, type=Path)
    prep.add_argument("--priority-seal", default="INPUT_SEAL.json")
    worker = sub.add_parser("run")
    for name in ("bundle", "assets", "assignment", "out"):
        worker.add_argument("--" + name, required=True, type=Path)
    worker.add_argument("--batch", type=int, default=4)
    analysis = sub.add_parser("analyse")
    for name in ("scores", "out"):
        analysis.add_argument("--" + name, required=True, type=Path)
    sub.add_parser("plan")
    a = p.parse_args(argv)
    if a.action == "plan":
        print(json.dumps({"recipe": RECIPE, "cap_seconds": CAP_SECONDS, "source_files": source_hashes()}, indent=2))
    elif a.action == "run": run(a)
    else:
        with P.logged("w7_" + a.action):
            {"prepare": prepare, "analyse": analyse}[a.action](a)


if __name__ == "__main__":
    main()
