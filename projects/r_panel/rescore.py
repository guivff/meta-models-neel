"""BRIEF_RP §15: fresh-pool re-score of the surprise-list cells (BRIEF_R §4.9 (c)), one fresh pod, ≤ 2 GPU-h.

Cells (``CELLS``, fixed in §15 before any compute): the AO / AO-yn exceedances over prompt-only of Q8B and Q32 (onset and
training-native offset 7) and of Q27 (onset), and the 27 Q27 C-A cells where the AO and the Oracle lens disagree. Fresh items:
per fact, the first 100 positive and 100 negative pool items outside the 64 pool-eval items, in bank order (``native.py
--fresh``'s rule; ``fresh_items``). Same scoring as the original cells; prompt-only rows for pool items already exist.

Pod stages (one process per pair; ``--smoke N`` uses the first N/2 per class and its own cache root):
    python -m projects.r_panel.rescore capture Q8  --root R --layers 21 22 23 24 25 --datasets …   # Q8B's five blocks
    python -m projects.r_panel.rescore ao      Q8B --root R --offsets 0 7 --readers ao ao_yn --datasets …
    python -m projects.r_panel.rescore noact   Q27 --root R --datasets …                            # AO text arm (ao_noact @32)
    python -m projects.r_panel.rescore olens   --root R --datasets …                                # Oracle lens @44 + olens_txtq
Mac:
    python -m projects.r_panel.rescore analyze --root <pulled root>   → results/g_agreement/rp/rescore/
Every stage prints one ``RSC_TIMING {json}`` line (load and work seconds, items) for the smoke's projection.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

CA_FACTS = ["106_hate_hate", "113_movie_sent", "123_world_country_United_Kingdom", "125_world_country_Italy", "127_art_type_song",
            "128_art_type_movie", "134_context_type_Belief_states", "136_glue_mnli_entailment", "138_glue_mnli_contradiction",
            "143_cancer_cat_Lung_Cancer", "154_athlete_sport_football", "155_athlete_sport_basketball", "156_athlete_sport_baseball",
            "158_code_C", "159_code_Python", "26_headline_isfrontpage", "36_sciq_tf", "41_truthqa_tf", "42_temp_sense", "44_phys_tf",
            "47_reasoning_tf", "51_just_is", "54_cs_tf", "89_glue_mrpc", "90_glue_qnli", "91_glue_qqp", "96_spam_is"]
ADMIN = "153_it_tick_Administrative rights"
# (pair, reader, offset, dataset): H2 exceedances over prompt-only (BH-passing at the primary site, rp/<pair>[/native_k7]/ceiling_bh.csv)
H2_CELLS = [("Q8B", "ao", 0, ADMIN), ("Q8B", "ao_yn", 0, ADMIN), ("Q8B", "ao", 0, "94_ai_gen"),
            ("Q8B", "ao", 7, "127_art_type_song"), ("Q8B", "ao", 7, "128_art_type_movie"), ("Q8B", "ao", 7, "138_glue_mnli_contradiction"),
            ("Q8B", "ao", 7, "42_temp_sense"), ("Q8B", "ao", 7, "52_virtue_is"), ("Q8B", "ao", 7, "94_ai_gen"),
            ("Q32", "ao", 0, ADMIN), ("Q32", "ao_yn", 0, ADMIN),
            ("Q32", "ao", 7, ADMIN), ("Q32", "ao", 7, "26_headline_isfrontpage"), ("Q32", "ao", 7, "56_wikidatasex_or_gender"),
            ("Q32", "ao", 7, "94_ai_gen"),
            ("Q27", "ao", 0, "142_cancer_cat_Thyroid_Cancer"), ("Q27", "ao", 0, ADMIN), ("Q27", "ao_yn", 0, "131_temp_cat_Typical Time"),
            ("Q27", "ao_yn", 0, ADMIN)]
N_FRESH = 200
OLENS_LAYER = 44


def facts(pair: str) -> list[str]:
    fs = {d for p, _, _, d in H2_CELLS if p == pair}
    return sorted(fs | (set(CA_FACTS) if pair == "Q27" else set()))


def fresh_items(its: list[dict[str, Any]], n: int, pool_eval: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """native.py --fresh: pool items outside the pool-eval set, first n/2 per class in bank order."""
    used = {it["item_id"] for it in pool_eval}
    rest = [it for it in its if it["split"] == "pool" and it["item_id"] not in used]
    return [it for it in rest if it["label"] == 1][: n // 2] + [it for it in rest if it["label"] == 0][: n // 2]


def timing(stage: str, load_s: float, work_s: float, n_items: int, **kw: Any) -> None:
    print("RSC_TIMING " + json.dumps({"stage": stage, "load_s": round(load_s, 1), "work_s": round(work_s, 1), "n_items": n_items, **kw}), flush=True)


def _pair_env(pair: str, root: Path):
    from projects.r_panel import setup as S

    S.activate(pair)
    from projects.g_agreement.r_bench import bank as B
    from projects.g_agreement.r_bench import collect as RC
    from projects.r_gemma import collect as RGC

    RGC.set_cache_dir(root / pair)
    items = B.load_items(B.ITEMS_R, "all")
    return S, B, RC, RGC, items


def _fresh_by_ds(RC, RGC, items, datasets, n):
    out = {}
    for ds, its in RC.items_by_dataset([it for it in items if it["dataset"] in datasets]).items():
        out[ds] = fresh_items(its, n, RGC.pool_eval_items(its))
    return out


def capture(a) -> int:
    S, B, RC, RGC, items = _pair_env(a.pair, a.root)
    t0 = time.time()
    target = RGC.load_target_timed()
    load = time.time() - t0
    fr = _fresh_by_ds(RC, RGC, items, a.datasets, a.n)
    t1 = time.time()
    try:
        for ds, its in fr.items():
            RGC.capture_positions(target, ds, its, tuple(a.layers), a.capture_batch)
    finally:
        RGC.flush_ledgers()
    timing(f"capture_{a.pair}", load, time.time() - t1, sum(map(len, fr.values())), facts=len(fr))
    return 0


def ao(a) -> int:
    """native.py's fresh scoring with a reader list: rows ``<reader>|L<L>|chat|k<k>|fresh|<item>`` in reader_lo_fresh.jsonl."""
    import numpy as np
    import torch

    S, B, RC, RGC, items = _pair_env(a.pair, a.root)
    spec = S.ACTIVE["spec"]
    L, multi = spec["primary"], spec.get("multi")
    pos_dir = (RGC.RG_DIR.parent / spec["states_from"] if spec.get("states_from") else RGC.RG_DIR) / "states_pos"
    out = RGC.RG_DIR / "reader_lo_fresh.jsonl"
    t0 = time.time()
    target = RGC.load_target_timed()
    readers = RGC.bind_readers(target, list(a.readers))
    load = time.time() - t0
    shas = RGC.rg_shas(B.ITEMS_R)
    fr = _fresh_by_ds(RC, RGC, items, a.datasets, a.n)
    t1, n = time.time(), 0
    try:
        for ds, its in fr.items():
            idx = json.loads((pos_dir / ds / "index.json").read_text())
            at = {iid: i for i, iid in enumerate(idx["item_ids"])}
            rows_idx = [at[it["item_id"]] for it in its]
            pairs = [(it["primary"]["candidates"][0], it["primary"]["candidates"][1]) for it in its]
            for k in a.offsets:
                if multi:
                    X = np.stack([np.load(pos_dir / ds / f"chat_L{b}_k{k}.npy").astype(np.float32)[rows_idx] for b in multi], axis=1)
                else:
                    X = np.load(pos_dir / ds / f"chat_L{L}_k{k}.npy").astype(np.float32)[rows_idx]
                for rd in readers:
                    keys = [f"{rd.name}|L{L}|chat|k{k}|fresh|{it['item_id']}" for it in its]
                    if all(kk in RGC.done_keys(out) for kk in keys):
                        continue
                    rows = rd.score(torch.from_numpy(X), pairs, its[0]["primary"], L, a.batch)
                    for it, key, r in zip(its, keys, rows):
                        RGC.append_row(out, {"key": key, "module": RGC.MODULE, "reader": rd.name, "layer": L, "render": "chat", "offset": k,
                                             "condition": "natural", "split": "pool", "subset": "fresh", "dataset": ds, "tag": it.get("tag"),
                                             "sided": its[0]["primary"].get("sided"), "item_id": it["item_id"], "label": it["label"],
                                             "lp_A": r["lp_A"], "lp_B": r["lp_B"], "lo": r["lo"], "unscorable": r["unscorable"],
                                             "run_id": a.run_id, "run_kind": a.run_kind, "created_at": RGC.now_iso(), **shas})
                        n += 1
    finally:
        RGC.flush_ledgers()
    timing(f"ao_{a.pair}", load, time.time() - t1, sum(map(len, fr.values())) * len(a.offsets) * len(readers), rows=n)
    return 0


def _derived_items(B, items, fr: dict[str, list[dict[str, Any]]], path: Path) -> Path:
    """The fresh items relabelled ``split = test`` (``orig_split = pool``), for the code paths that score test items only."""
    keep = {it["item_id"] for its in fr.values() for it in its}
    rows = [{**it, "split": "test", "orig_split": it["split"]} for it in items if it["item_id"] in keep]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows))
    return path


def noact(a) -> int:
    S, B, RC, RGC, items = _pair_env(a.pair, a.root)
    L = S.ACTIVE["spec"]["primary"]
    fr = _fresh_by_ds(RC, RGC, items, a.datasets, a.n)
    p = _derived_items(B, items, fr, a.root / a.pair / "items_fresh.json")
    der = {ds: [{**it, "split": "test"} for it in its] for ds, its in fr.items()}
    t0 = time.time()
    target = RGC.load_target_timed()
    (rd,) = RGC.bind_readers(target, ["ao"])
    load = time.time() - t0
    t1, n = time.time(), 0
    try:
        for ds, its in der.items():
            n += RGC.collect_reader_noact(rd, ds, its, L, a.batch, items_path=p)
    finally:
        RGC.flush_ledgers()
    timing(f"noact_{a.pair}", load, time.time() - t1, sum(map(len, der.values())), rows=n)
    return 0


def olens(a) -> int:
    """WS3's text arm v2 path on the fresh items: arm (a) ``olens_txtq`` and the frozen bullet-form Oracle on the re-captured
    block-44 states (``olens_repro``, K2's reader) for EVERY fresh item; arm (b) comes along unused."""
    from projects.g_agreement.r_bench import bank as B
    from projects.g_agreement.r_bench import collect as RC
    from projects.g_agreement.r_bench import text_arm_v2 as T2
    from projects.r_panel import setup as S

    S.activate("Q27")
    from projects.r_gemma import collect as RGC

    items = B.load_items(B.ITEMS_R, "all")
    fr = _fresh_by_ds(RC, RGC, items, a.datasets, a.n)
    p = _derived_items(B, items, fr, a.root / "olens" / "items_fresh.json")
    RC.set_shard(None, T2.SUFFIX)
    RC.set_run_meta(a.pod, None, run_kind=a.run_kind)
    RC.set_cache_dir(a.root / "olens")
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    t0 = time.time()
    target = load_target_timed(RC.MODULE, RC.LEDGER_PATH)
    (reader,) = RC.bind_readers(target, ["olens"])
    load = time.time() - t0
    t1, n = time.time(), 0
    try:
        for ds, its in fr.items():
            der = [{**it, "split": "test"} for it in its]
            n += T2.collect_v2(reader, ds, der, p, OLENS_LAYER, a.batch, repro=len(der))
    finally:
        RC.flush_ledgers()
    timing("olens_Q27", load, time.time() - t1, sum(map(len, fr.values())), rows=n)
    return 0


# ------------------------------------------------------------------ Mac: the pre-registered verdicts (§15)
def analyze(root: Path, out: Path, n_boot: int = 2000) -> Any:
    import numpy as np
    import pandas as pd

    from projects.g_agreement.r_bench import text_arm as TA
    from projects.r_panel import panel as P

    def rows(path: Path) -> pd.DataFrame:
        if not path.exists():   # the pulled copy carries WS2's output suffix
            path = path.with_name(path.name.replace(".jsonl", ".RSC.jsonl"))
        if not path.exists():
            return pd.DataFrame()
        df = pd.DataFrame([json.loads(l) for l in open(path) if l.strip()]).drop_duplicates("key", keep="last")
        df["score"] = np.where(df.get("sided", pd.Series("two", index=df.index)).fillna("two") == "two", df["lo"], df["lp_A"]).astype(float)
        return df

    def delta(y, a, b) -> dict[str, float]:
        i = np.random.default_rng(0).integers(0, len(y), (n_boot, len(y)))
        v = TA.auroc_rows(y[i], a[i]) - TA.auroc_rows(y[i], b[i])
        v = v[~np.isnan(v)]
        return {"n": len(y), "auroc_1": float(TA.auroc_rows(y, a)[0]), "auroc_2": float(TA.auroc_rows(y, b)[0]),
                "delta": float(TA.auroc_rows(y, a)[0] - TA.auroc_rows(y, b)[0]), "lo95": float(np.quantile(v, 0.025)),
                "hi95": float(np.quantile(v, 0.975))}

    def confirmed(orig: float, d: dict[str, float]) -> bool:
        return bool(np.sign(d["delta"]) == np.sign(orig) and (d["lo95"] > 0 or d["hi95"] < 0))

    res = []
    for pair, reader, k, ds in H2_CELLS:
        fr = rows(root / pair / "reader_lo_fresh.jsonl")
        po = P.read_rows("Q8" if pair == "Q8B" else pair, "prompt_only")
        cb = pd.read_csv(P.RES / pair / ("native_k7" if k else "") / "ceiling_bh.csv")
        orig = float(cb[(cb.dataset == ds) & (cb.reader == reader)]["diff"].iloc[0])
        g = fr[(fr.reader == reader) & (fr.offset == k) & (fr.dataset == ds)] if len(fr) else fr
        m = P._pair_scores(g, po[po.dataset == ds]) if len(g) else g
        d = delta(m["label"].to_numpy(), m["score_1"].to_numpy(), m["score_2"].to_numpy()) if len(m) else {}
        res.append({"cell": "H2 exceedance", "pair": pair, "reader": reader, "offset": k, "dataset": ds, "contrast": "reader − prompt-only",
                    "orig_delta": orig, **d, "confirmed": confirmed(orig, d) if d else None})
    ca = pd.read_csv(P.RES / "Q27" / "ca.csv")
    ca = ca[(ca.form == "ao") & (ca.render == "chat")].set_index("dataset")
    ol = pd.read_csv(P.RES.parent / "r" / "text_arm_v2_gemma108.csv")
    ol = ol[(ol.contrast == "A") & (ol.render == "chat") & (ol.layer == OLENS_LAYER)].set_index("dataset")
    fr = rows(root / "Q27" / "reader_lo_fresh.jsonl")
    na = rows(root / "Q27" / "reader_lo.jsonl")
    tv = rows(root / "olens" / "text_arm" / "text_arm_v2_lo.jsonl")
    rp = rows(root / "olens" / "text_arm" / "text_arm_v2_repro_lo.jsonl")
    for ds in CA_FACTS:
        out_ds = []
        for who, a_rows, b_rows, orig in (
                ("AO@32 state − AO text arm", fr[(fr.reader == "ao") & (fr.offset == 0) & (fr.dataset == ds)] if len(fr) else fr,
                 na[(na.reader == "ao_noact") & (na.dataset == ds)] if len(na) else na, float(ca.loc[ds, "delta"])),
                ("Oracle lens@44 state − olens_txtq", rp[(rp.render == "chat") & (rp.dataset == ds)] if len(rp) else rp,
                 tv[(tv.reader == "olens_txtq") & (tv.dataset == ds)] if len(tv) else tv, float(ol.loc[ds, "delta"]))):
            m = P._pair_scores(a_rows, b_rows) if len(a_rows) and len(b_rows) else pd.DataFrame()
            d = delta(m["label"].to_numpy(), m["score_1"].to_numpy(), m["score_2"].to_numpy()) if len(m) else {}
            c = confirmed(orig, d) if d else None
            out_ds.append(c)
            res.append({"cell": "C-A disagreement", "pair": "Q27", "reader": "ao" if who.startswith("AO") else "olens", "offset": 0, "dataset": ds, "contrast": who,
                        "orig_delta": orig, **d, "confirmed": c})
        res.append({"cell": "C-A disagreement (both readers)", "pair": "Q27", "reader": "['ao', 'olens']", "offset": 0, "dataset": ds,
                    "contrast": "AO TEXT SUFFICES and Oracle READ FROM THE STATE (or the reverse) both re-found",
                    "confirmed": (all(out_ds) if None not in out_ds else None)})
    df = pd.DataFrame(res)
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "rescore.csv", index=False)
    return df


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0]
    ap = argparse.ArgumentParser()
    if cmd != "olens" and cmd != "analyze":
        ap.add_argument("pair")
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--datasets", nargs="*", default=None)
    ap.add_argument("--layers", nargs="*", type=int, default=None)
    ap.add_argument("--offsets", nargs="*", type=int, default=[0])
    ap.add_argument("--readers", nargs="*", default=["ao"])
    ap.add_argument("--n", type=int, default=N_FRESH, help="fresh items per fact (balanced); the smoke uses 8")
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--capture-batch", type=int, default=32)
    ap.add_argument("--pod", default=None)
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--run-kind", default="real", choices=["real", "smoke"])
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args(argv[1:])
    if cmd == "analyze":
        from projects.g_agreement.core import config as C

        df = analyze(a.root, a.out or C.RESULTS_DIR / "rp" / "rescore")
        print(df.drop(columns=[c for c in ("auroc_1", "auroc_2") if c in df]).round(3).to_string())
        return 0
    if a.datasets is None:
        a.datasets = list(CA_FACTS) if cmd in ("olens", "noact") else facts(a.pair)
    return {"capture": capture, "ao": ao, "noact": noact, "olens": olens}[cmd](a)


if __name__ == "__main__":
    sys.exit(main())
