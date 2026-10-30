"""A synthetic Phase R cache so ``analyze.py`` can be exercised end to end without a GPU (``analyze --mock``).

The mock world (d = 48, not 5120) is built to contain every behaviour the regimes test for, so that the analysis code
can be checked against known answers:
  - each fact has a PROBE direction (the label is linearly present along it) and a CLASS-MEAN direction that is only
    partly aligned with it; readers score along the class-mean direction with tag-dependent noise
    (SURFACE/TOPIC clean, KNOWLEDGE medium, COMPUTED/FORM/META noisy), so n* and the blind-spot map have structure;
  - the prompt-only model is strong on text-derivable tags and weaker on COMPUTED, and its errors define conflicts;
  - at layers below 40 the probe direction carries less signal and the reader signal appears later (a lag);
  - the raw render adds noise to the readers (render shift);
  - a shuffled control is written for every reader, and state-free rows carry a constant candidate bias;
  - R5 rows: steering along the class-mean direction moves readers but not the model, the probe direction moves
    the model but not the readers (spoof + evade by construction), random directions move nothing.
Everything is written in the real file formats under a separate cache root (default: a scratch directory).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from projects.g_agreement.r_bench import datasets as D

D_MOCK = 48
LAYERS = (24, 28, 32, 36, 40, 42, 44, 48, 52, 56, 60)
READERS = {"jlens": (42, 44, 48, 52, 56), "olens": (42, 44, 48, 52, 56), "skip_a": (42,), "nla": (42,)}
RENDERS = ("chat", "raw")
MOCK_FACTS = ["21_headline_istrump", "66_living-room", "92_glue_sst2", "96_spam_is", "139_news_class_Politics", "158_code_C",
              "5_hist_fig_ismale", "117_us_state_FL", "154_athlete_sport_football", "123_world_country_United_Kingdom",
              "41_truthqa_tf", "87_glue_cola", "90_glue_qnli", "48_cm_correct", "110_aimade_humangpt3", "100_news_fake",
              "130_temp_cat_Frequency", "133_context_type_Causality", "36_sciq_tf", "54_cs_tf", "94_ai_gen", "26_headline_isfrontpage",
              "7_hist_fig_ispolitician", "95_toxic_is"]
TAG_READER_NOISE = {"SURFACE": 0.6, "TOPIC": 0.8, "KNOWLEDGE": 1.4, "FORM": 2.5, "COMPUTED": 3.0, "META": 2.0}
TAG_MODEL_ACC = {"SURFACE": 0.97, "TOPIC": 0.93, "KNOWLEDGE": 0.9, "FORM": 0.8, "COMPUTED": 0.72, "META": 0.85}
READER_QUALITY = {"jlens": 1.3, "olens": 1.0, "skip_a": 1.1, "nla": 1.6}  # multiplies the noise


def _unit(v: np.ndarray) -> np.ndarray:
    return v / (np.linalg.norm(v) + 1e-9)


def _append(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")


def build_mock(root: Path, n_test: int = 120, n_pool: int = 256, seed: int = 0, facts: list[str] | None = None,
               with_r5: bool = True) -> dict[str, Path]:
    """Write items_r.json, states, logit_lens, prompt_only, reader_lo, state_free, kway (one parent) and r5 rows."""
    rng = np.random.default_rng(seed)
    root = Path(root)
    cache = root / "cache" / "g_agreement" / "r"
    dataset_dir = root / "dataset"
    results = root / "results" / "g_agreement" / "r"
    for p in (cache / "states", dataset_dir, results):
        p.mkdir(parents=True, exist_ok=True)
    facts = facts or MOCK_FACTS
    items: list[dict[str, Any]] = []
    per: dict[str, Any] = {}
    truth: dict[str, Any] = {}
    for fid in facts:
        spec = D.SPECS[fid]
        n = n_test + n_pool
        y = np.array([1] * (n // 2) + [0] * (n - n // 2))
        rng.shuffle(y)
        d_probe = _unit(rng.standard_normal(D_MOCK))
        d_cm = _unit(0.55 * d_probe + 0.85 * _unit(rng.standard_normal(D_MOCK)))   # cos ≈ 0.55 with the probe direction
        d_cm = _unit(d_cm - 0.0 * d_probe)
        base = rng.standard_normal((n, D_MOCK)) * 1.0
        ids = [f"r-{fid}-{'test' if i < n_test else 'pool'}-{(i if i < n_test else i - n_test):04d}" for i in range(n)]
        splits = ["test" if i < n_test else "pool" for i in range(n)]
        for i in range(n):
            items.append({"item_id": ids[i], "dataset": fid, "tag": spec.tag, "split": splits[i], "label": int(y[i]), "raw_target": str(y[i]),
                          "prompt_text": f"mock text {fid} {i}", "render": "chat", "system": None,
                          "primary": {"name": fid, "question": spec.question, "candidates": [spec.pos, spec.neg],
                                      "answer": spec.pos if y[i] else spec.neg, "template": spec.template, "sided": spec.sided,
                                      "jlens": [spec.jlens_pos, spec.jlens_neg]}})
        per[fid] = {"n_pos": int(y.sum()), "n_neg": int((1 - y).sum()), "n_test": n_test, "n_pool": n_pool, "small_test": False,
                    "pool_short": False, "tag": spec.tag, "sided": spec.sided, "verify": spec.verify}
        truth[fid] = {"d_probe": d_probe, "d_cm": d_cm}
        sd = cache / "states" / fid
        sd.mkdir(parents=True, exist_ok=True)
        (sd / "index.json").write_text(json.dumps({"dataset": fid, "item_ids": ids, "splits": splits, "labels": [int(v) for v in y],
                                                   "layers": list(LAYERS), "renders": list(RENDERS), "max_tokens": 256}))
        sgn = 2 * y - 1
        ll_rows, lo_rows, sf_rows = [], [], []
        states: dict[tuple[str, int], np.ndarray] = {}
        for render in RENDERS:
            for L in LAYERS:
                # signal grows with the layer up to 40 (probe), the class-mean component appears from 44 on noisy tags
                g_probe = min(1.0, max(0.15, (L - 20) / 20))
                lag_tags = ("COMPUTED", "FORM", "META")
                g_cm = min(1.0, max(0.0, (L - (40 if spec.tag in lag_tags else 24)) / 12))
                X = base + 1.6 * g_probe * sgn[:, None] * d_probe[None, :] + 1.4 * g_cm * sgn[:, None] * d_cm[None, :]
                if render == "raw":
                    X = X + 0.6 * rng.standard_normal(X.shape)
                states[(render, L)] = X.astype(np.float32)
                np.save(sd / f"{render}_L{L}.npy", X.astype(np.float16))
            # logit lens: a weak late reader of the class-mean component
            for i in range(n):
                ll_rows.append({"key": f"ll|{fid}|{render}|{ids[i]}", "dataset": fid, "render": render, "item_id": ids[i], "split": splits[i],
                                "label": int(y[i]), "per_layer": {str(L): {"margin": float(0.4 * max(0.0, (L - 44) / 16) * (states[(render, L)][i] @ truth[fid]["d_cm"]) + 0.8 * rng.standard_normal())} for L in LAYERS}})
            # readers: projection on d_cm at the read layer + tag/reader/render noise; shuffled control; state-free row
            for rname, layers in READERS.items():
                noise = TAG_READER_NOISE[spec.tag] * READER_QUALITY[rname] * (1.5 if render == "raw" else 1.0)
                bias = {"jlens": 0.0, "olens": 1.2, "skip_a": -0.4, "nla": 0.7}[rname]
                for L in layers:
                    X = states[(render, L)]
                    proj = X @ truth[fid]["d_cm"]
                    perm = rng.permutation(n_test)
                    primary_site = (L == {"jlens": 42, "olens": 44, "skip_a": 42, "nla": 42}[rname]) and render == "chat"
                    if primary_site:  # the quiver's validation pool: the first 64 pool items at the primary site
                        for i in range(n_test, min(n, n_test + 64)):
                            s_pos = float(0.8 * proj[i] + bias + noise * rng.standard_normal())
                            s_neg = float(-0.8 * proj[i] + noise * rng.standard_normal())
                            lo_rows.append({"key": f"{rname}|L{L}|{render}|{ids[i]}", "reader": rname, "layer": L, "render": render, "condition": "natural",
                                            "dataset": fid, "item_id": ids[i], "label": int(y[i]), "lp_A": s_pos, "lp_B": s_neg, "lo": s_pos - s_neg,
                                            "unscorable": False})
                    for i in range(n_test):  # readers are scored on the TEST split (and the pool-eval subset above)
                        s_pos = float(0.8 * proj[i] + bias + noise * rng.standard_normal())
                        s_neg = float(-0.8 * proj[i] + noise * rng.standard_normal())
                        lo_rows.append({"key": f"{rname}|L{L}|{render}|{ids[i]}", "reader": rname, "layer": L, "render": render, "condition": "natural",
                                        "dataset": fid, "item_id": ids[i], "label": int(y[i]), "lp_A": s_pos, "lp_B": s_neg, "lo": s_pos - s_neg,
                                        "unscorable": False})
                        j = perm[i]
                        sp = float(0.8 * proj[j] + bias + noise * rng.standard_normal())
                        sn = float(-0.8 * proj[j] + noise * rng.standard_normal())
                        lo_rows.append({"key": f"{rname}|L{L}|{render}|shuf|{ids[i]}", "reader": rname, "layer": L, "render": render, "condition": "shuf",
                                        "dataset": fid, "item_id": ids[i], "label": int(y[i]), "lp_A": sp, "lp_B": sn, "lo": sp - sn, "unscorable": False})
                    sf_rows.append({"key": f"{rname}|L{L}|{render}|{fid}", "reader": rname, "layer": L, "render": render, "condition": "state_free", "dataset": fid,
                                    "lp_A": bias, "lp_B": 0.0, "lo": bias, "unscorable": False})
        _append(cache / "logit_lens.jsonl", ll_rows)
        _append(cache / "reader_lo.jsonl", lo_rows)
        _append(cache / "state_free.jsonl", sf_rows)
        # prompt-only: the model's own report; accuracy by tag, confidence correlated with the probe projection
        po_rows = []
        acc = TAG_MODEL_ACC[spec.tag]
        for i in range(n):
            correct = rng.random() < acc
            says_pos = bool(y[i]) if correct else not bool(y[i])
            conf = abs(float(states[("chat", 42)][i] @ truth[fid]["d_probe"])) * 2 + 0.5
            lo = conf if says_pos else -conf
            po_rows.append({"key": f"po|{fid}|{ids[i]}", "dataset": fid, "item_id": ids[i], "split": splits[i], "label": int(y[i]),
                            "candidates": [spec.pos, spec.neg], "lp": [lo / 2, -lo / 2], "greedy": 0 if says_pos else 1,
                            "lp_pos": lo / 2, "lp_neg": -lo / 2, "lo": lo, "model_says_pos": says_pos})
        _append(cache / "prompt_only.jsonl", po_rows)
    meta = {"created": "mock", "seed": seed, "n_test": n_test, "n_pool": n_pool, "n_datasets": len(per), "n_items": len(items),
            "missing": [], "datasets": per, "spec": {f: D.SPECS[f].to_json() for f in facts}, "frozen": False, "mock": True}
    (dataset_dir / "items_r.json").write_text(json.dumps({"meta": meta, "items": items}))

    # one k-way parent: 5 classes, reader argmax weak, probe strong, model strong
    k = 5
    kid = "10_nyc_borough"
    m = D.MULTICLASS[kid]
    cands = ["Manhattan", "Brooklyn", "Queens", "the Bronx", "Staten Island"]
    nk = 25 * k
    yk = np.repeat(np.arange(k), 25)
    kids = [f"rk-{kid}-test-{c}-{i:04d}" for c in range(k) for i in range(25)]
    kitems = [{"item_id": kids[i], "dataset": kid, "tag": m.tag, "split": "test", "label": int(yk[i]), "raw_target": cands[yk[i]],
               "prompt_text": f"mock place {i}", "render": "chat", "system": None,
               "primary": {"name": kid, "question": m.question, "candidates": cands, "answer": cands[yk[i]], "template": m.template,
                           "sided": "kway", "k": k}} for i in range(nk)]
    kpool = [{**it, "item_id": it["item_id"].replace("-test-", "-pool-"), "split": "pool"} for it in kitems]
    (dataset_dir / "items_rk.json").write_text(json.dumps({"meta": {"mock": True, "datasets": {kid: {"k": k}}}, "items": kitems + kpool}))
    sd = cache / "states" / kid
    sd.mkdir(parents=True, exist_ok=True)
    allk = kitems + kpool
    protos = rng.standard_normal((k, D_MOCK))
    yall = np.array([it["label"] for it in allk])
    Xk = rng.standard_normal((len(allk), D_MOCK)) + 1.5 * protos[yall]
    (sd / "index.json").write_text(json.dumps({"dataset": kid, "item_ids": [it["item_id"] for it in allk], "splits": [it["split"] for it in allk],
                                               "labels": [int(v) for v in yall], "layers": list(LAYERS), "renders": list(RENDERS)}))
    for render in RENDERS:
        for L in LAYERS:
            np.save(sd / f"{render}_L{L}.npy", Xk.astype(np.float16))
    krows, kpo = [], []
    for rname, layers in READERS.items():
        for L in layers:
            for render in RENDERS:
                for i, it in enumerate(kitems):
                    for c in range(k):
                        s = 0.5 * float(Xk[i] @ _unit(protos[c])) + 1.5 * rng.standard_normal()
                        krows.append({"key": f"{rname}|L{L}|{render}|{it['item_id']}|c{c}", "reader": rname, "layer": L, "render": render,
                                      "dataset": kid, "item_id": it["item_id"], "label": int(yk[i]), "cand_index": c, "candidate": cands[c],
                                      "lp": s, "unscorable": False, "k": k})
    for i, it in enumerate(allk):
        lp = [float(Xk[i] @ _unit(protos[c])) + 0.3 * rng.standard_normal() for c in range(k)]
        kpo.append({"key": f"po|{kid}|{it['item_id']}", "dataset": kid, "item_id": it["item_id"], "split": it["split"], "label": int(yall[i]),
                    "candidates": cands, "lp": lp, "greedy": int(np.argmax(lp))})
    _append(cache / "kway_lo.jsonl", krows)
    _append(cache / "prompt_only.jsonl", kpo)

    if with_r5:
        write_mock_r5(cache, results, items, truth, facts[:4], rng)
    return {"root": root, "cache": cache, "dataset_dir": dataset_dir, "results": results}


def write_mock_r5(cache: Path, results: Path, items: list[dict[str, Any]], truth: dict[str, Any], facts: list[str], rng: np.random.Generator) -> None:
    """Steering rows with the construction: d_cm moves readers (not the model), d_probe moves the model (not readers)."""
    r5 = cache / "r5"
    (r5 / "directions").mkdir(parents=True, exist_ok=True)
    sel: dict[str, Any] = {"datasets": {}, "mock": True}
    steer_rows, reader_rows = [], []
    for fid in facts:
        its = [it for it in items if it["dataset"] == fid and it["split"] == "test"][:32]
        d_probe, d_cm = truth[fid]["d_probe"], truth[fid]["d_cm"]
        dirs = {"d_cm_L38": d_cm, "d_probe_L38": d_probe, "d_cm_L42": d_cm, "d_probe_L42": d_probe,
                "d_olens_L38": _unit(0.9 * d_cm + 0.3 * rng.standard_normal(D_MOCK)), "d_jlens_L38": _unit(0.85 * d_cm + 0.4 * rng.standard_normal(D_MOCK)),
                "d_rand0_L38": _unit(rng.standard_normal(D_MOCK)), "d_rand1_L38": _unit(rng.standard_normal(D_MOCK))}
        np.savez(r5 / "directions" / f"{fid}.npz", **dirs)
        sel["datasets"][fid] = {"item_ids": [it["item_id"] for it in its], "scale": 3.0, "probe_auroc": 0.95, "prompt_only_auroc": 0.95}
        rb = r5 / "readback" / fid
        rb.mkdir(parents=True, exist_ok=True)
        (rb / "index.json").write_text(json.dumps({"item_ids": [it["item_id"] for it in its], "directions": ["natural"] + [k for k in dirs if k.endswith("_L38")],
                                                   "alphas": [0.5, 1.0, 2.0], "scale": 3.0, "edit_layer": 38, "read_layer": 42}))
        for dname in ["natural"] + [k for k in dirs if k.endswith("_L38")]:
            for alpha in ([0.0] if dname == "natural" else [0.5, 1.0, 2.0]):
                for it in its:
                    y = it["label"]
                    sgn = -1.0 if y == 1 else 1.0
                    nat_model = 6.0 * (1 if y else -1) + rng.standard_normal()
                    nat_reader = 2.0 * (1 if y else -1)
                    model_move = 0.0
                    reader_move = 0.0
                    if dname.startswith("d_probe"):
                        model_move = 9.0 * alpha
                        reader_move = 0.3 * alpha
                    elif dname.startswith("d_cm") or dname.startswith("d_olens") or dname.startswith("d_jlens"):
                        model_move = 1.0 * alpha
                        reader_move = 2.5 * alpha
                    lo_model = nat_model + sgn * model_move
                    steer_rows.append({"key": f"{fid}|{it['item_id']}|{dname}|{alpha}", "dataset": fid, "item_id": it["item_id"], "label": y,
                                       "direction": dname, "alpha": alpha, "sign": sgn, "scale": 3.0, "edit_layer": 38, "read_layer": 42,
                                       "candidates": it["primary"]["candidates"], "lp_pos": lo_model / 2, "lp_neg": -lo_model / 2, "lo": lo_model})
                    for rname in ("olens", "jlens", "skip_a", "nla"):
                        s = nat_reader + sgn * reader_move + 0.5 * rng.standard_normal()
                        reader_rows.append({"key": f"{rname}|{fid}|{it['item_id']}|{dname}|{alpha}", "reader": rname, "dataset": fid,
                                            "item_id": it["item_id"], "label": y, "direction": dname, "alpha": alpha, "lp_A": s / 2, "lp_B": -s / 2,
                                            "lo": s, "unscorable": False})
    _append(r5 / "steer.jsonl", steer_rows)
    _append(r5 / "readers.jsonl", reader_rows)
    results.mkdir(parents=True, exist_ok=True)
    (results / "r5_selection.json").write_text(json.dumps(sel, indent=1))


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--n-test", type=int, default=120)
    ap.add_argument("--n-pool", type=int, default=256)
    a = ap.parse_args()
    print(build_mock(a.root, a.n_test, a.n_pool))
