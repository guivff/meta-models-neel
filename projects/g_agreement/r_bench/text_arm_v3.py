"""Text arm v3: control arms for text arm v2's arm (b) (BRIEF_R §13 note "text arm v3").

    python -m projects.g_agreement.r_bench.text_arm_v3 --smoke 2 --datasets <2 R-A> <2 ReaderBench>   # pod: asserts every arm
    python -m projects.g_agreement.r_bench.text_arm_v3 --pod TXT3                                     # pod: every test item
    python -m projects.g_agreement.r_bench.text_arm_v3 --analyze                                      # Mac: Δ_R, Δ_D, Δ_RM, Δ_M

Arms (arm (b) of ``text_arm_v2`` exactly, only the injected vector changes):
  ``olens_txtq_shuf``  item i gets the state of item π(i), π = the frozen shuffled control's per-fact derangement
                       (``collect.derangement(n, default_rng(SHUFFLE_SEED + stable_offset(dataset)))`` over the test items in bank order)
  ``olens_txtq_mean``  every item gets the mean of its fact's test-item states (same render, block 44)
States: ``text_arm/states_v2/`` (v2's re-capture). Rows: ``text_arm/text_arm_v3_lo.jsonl`` (``condition = "text_arm_v3"``);
log ``log.TXT3.md``, ledger ``compute.TXT3.jsonl``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core.accounting import now_iso, timed_call
from projects.g_agreement.r_bench import bank as B
from projects.g_agreement.r_bench import collect as RC
from projects.g_agreement.r_bench import text_arm as T
from projects.g_agreement.r_bench import text_arm_v2 as V

NAME_SHUF = "olens_txtq_shuf"
NAME_MEAN = "olens_txtq_mean"
ARMS = (NAME_SHUF, NAME_MEAN)          # the pre-registered order: every fact for the deranged arm, then the mean arm
SUFFIX = "TXT3"
CONDITION = "text_arm_v3"
OUT_NAME = "text_arm_v3_lo.jsonl"
BATCH = 96
STATES_ROOT = RC.R_DIR      # the R cache at import (cache/g_agreement/r): v2's states_v2/ live here, also for the smoke


def load_states_v2(dataset: str, ids: list[str], root: Path | None = None) -> dict[str, Any]:
    """{render: fp32 [N, d]} from v2's ``states_v2/`` under the REAL R cache (never a smoke cache's partial copy);
    the stored item order must equal ``ids``."""
    import torch

    d = V.states_dir(root or STATES_ROOT) / dataset
    if json.loads((d / "index.json").read_text())["item_ids"] != ids:
        raise RuntimeError(f"{d}: states_v2 item order differs from the fact's test items")
    return {rd: torch.as_tensor(np.load(d / f"{rd}_L{V.LAYER}.npy").astype(np.float32)) for rd in V.RENDERS}


def code_sha() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def out_path(cache: Path | None = None) -> Path:
    return Path(cache or RC.R_DIR) / T.OUT_DIR / OUT_NAME


def key(arm: str, item_id: str, render: str, layer: int = V.LAYER) -> str:
    return f"{arm}|L{layer}|{render}|{item_id}"


def frozen_derangement(dataset: str, test_bank_order: list[dict[str, Any]]) -> dict[str, str]:
    """{item_id: state_item_id} of the frozen shuffled control (``collect.collect_reader_lo``) for one fact."""
    perm = RC.derangement(len(test_bank_order), np.random.default_rng(RC.SHUFFLE_SEED + RC.stable_offset(dataset)))
    return {it["item_id"]: test_bank_order[j]["item_id"] for it, j in zip(test_bank_order, perm)}


def control_states(arm: str, H: Any, ordered_ids: list[str], pi: dict[str, str]) -> tuple[Any, list[str | None]]:
    """The injected vectors in ``ordered_ids`` order: the deranged states, or the fact's mean state repeated."""
    import torch

    if arm == NAME_SHUF:
        pos = {iid: k for k, iid in enumerate(ordered_ids)}
        sids = [pi[iid] for iid in ordered_ids]
        return H[torch.as_tensor([pos[s] for s in sids])], sids
    if arm == NAME_MEAN:
        return H.float().mean(0, keepdim=True).repeat(H.shape[0], 1), [None] * len(ordered_ids)
    raise ValueError(arm)


def collect_v3(reader: Any, arm: str, dataset: str, test_bank_order: list[dict[str, Any]], items_path: Path,
               batch: int = BATCH) -> int:
    """One arm, both renders, the test items of one fact (resumable by key)."""
    if not test_bank_order:
        return 0
    test = RC.ordered_items(test_bank_order)            # the states_v2 row order
    ids = [it["item_id"] for it in test]
    pi = frozen_derangement(dataset, test_bank_order)
    need = {rd: [i for i, iid in enumerate(ids) if key(arm, iid, rd) not in RC.done_keys(out_path())] for rd in V.RENDERS}
    if not any(need.values()):
        return 0
    H = load_states_v2(dataset, ids)
    base = {**V._base(reader, dataset, test[0].get("tag"), items_path, V.LAYER), "condition": CONDITION,
            "text_arm_v3_code_sha256": code_sha()}
    n = 0
    for rd in V.RENDERS:
        if not need[rd]:
            continue
        Hc, sids = control_states(arm, H[rd], ids, pi)
        sub = [test[i] for i in need[rd]]
        led = RC.ledger(f"lo_{arm}_{rd}_L{V.LAYER}", batch=batch)
        with timed_call() as st:
            rows = V.score_arm_b(reader, sub, Hc[need[rd]], V.LAYER, batch)
        for i, it, r in zip(need[rd], sub, rows):
            V._write(out_path(), base, key(arm, it["item_id"], rd), it, r,
                     {"reader": arm, "render": rd, "injection": C.OLENS_INJECTION, "state_item_id": sids[i],
                      "state": f"{V.STATES_SUBDIR}/{rd}_L{V.LAYER}" + ("|deranged" if arm == NAME_SHUF else "|fact_mean")})
        led.add(V._tokens(rows), 0, st.wall_s, st.peak_mem_gb)
        n += len(rows)
    print(f"[r/text_arm_v3] {arm} {dataset}: {n} rows", flush=True)
    return n


def smoke_missing(path: Path, banks: list[str]) -> list[str]:
    """Every arm × render × bank must have ≥ 1 row (PODS.md rule 5)."""
    got = set()
    if path.exists():
        for r in T._iter_rows(path, '"text_arm_v3"'):
            got.add((r["reader"], r["render"], r["items_file"]))
    return [f"{a}/{rd}/{b}" for a in ARMS for rd in V.RENDERS for b in banks if (a, rd, b) not in got]


# ------------------------------------------------------------------ analysis (Mac)
def load_v3(cache: Path) -> dict[tuple[str, str], dict[str, dict[str, Any]]]:
    out: dict[tuple[str, str], dict[str, dict[str, Any]]] = {}
    for r in T._iter_rows(out_path(cache), '"text_arm_v3"'):
        if r.get("condition") == CONDITION:
            out.setdefault((r["reader"], r["render"]), {})[r["item_id"]] = r
    return out


CONTRASTS = {   # name: (first arm, second arm) → Δ = AUROC(first) − AUROC(second); "a" = v2 arm (a), "b" = v2 arm (b)
    "R": ("b", NAME_SHUF), "D": (NAME_SHUF, "a"), "RM": ("b", NAME_MEAN), "M": (NAME_MEAN, "a"), "B": ("b", "a")}
VERDICTS = {"R": ("ADDS_INFORMATION", "DERANGED_BETTER"), "RM": ("REAL_GT_MEAN", "MEAN_GT_REAL")}


def analyze(cache: Path, out_csv: Path | None, n_boot: int = T.N_BOOT, extra_excluded: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    """Per fact × site × contrast. Only facts complete in BOTH renders for an arm enter that arm's contrasts (§13 note)."""
    a, b = V.load_v2(cache)
    v3 = load_v3(cache)
    ml = T.model_labels(cache)
    arms_by_ds: dict[str, list[dict[str, Any]]] = {}
    for r in a.values():
        if r["dataset"] not in T.EXCLUDED and r["dataset"] not in extra_excluded:
            arms_by_ds.setdefault(r["dataset"], []).append(r)

    def scores(arm: str, render: str) -> dict[str, dict[str, Any]]:
        return a if arm == "a" else (b[render] if arm == "b" else v3.get((arm, render), {}))

    def complete(arm: str, ds_ids: set[str]) -> bool:
        return arm in ("a", "b") or all(ds_ids <= set(v3.get((arm, rd), {})) for rd in V.RENDERS)

    rows: list[dict[str, Any]] = []
    for ds, trs in sorted(arms_by_ds.items()):
        ids = {t["item_id"] for t in trs}
        for render in V.RENDERS:
            for cname, (x, y) in CONTRASTS.items():
                if not (complete(x, ids) and complete(y, ids)):
                    continue
                sx, sy = scores(x, render), scores(y, render)
                its = [t for t in trs if t["item_id"] in sx and t["item_id"] in sy]
                yv = np.array([ml.get(t["item_id"], t["label"]) for t in its])
                if not its or len(set(yv)) < 2:
                    continue
                d = T.paired_delta(yv, np.array([T.primary(sx[t["item_id"]]) for t in its]),
                                   np.array([T.primary(sy[t["item_id"]]) for t in its]), n_boot)
                rows.append({"contrast": cname, "dataset": ds, "tag": trs[0]["tag"], "bank": trs[0]["items_file"], "render": render,
                             "layer": V.LAYER, "n": len(its), "auc_1": d["auc_act"], "auc_2": d["auc_txt"], "delta": d["delta"],
                             "lo": d["lo"], "hi": d["hi"], "p": d["p"]})
    for cname, (pos, neg) in VERDICTS.items():
        for render in V.RENDERS:
            site = [r for r in rows if r["contrast"] == cname and r["render"] == render]
            for tag in sorted({r["tag"] for r in site}):
                fam = [r for r in site if r["tag"] == tag]
                for r, q in zip(fam, T.bh([r["p"] for r in fam])):
                    v = T.verdict(r["delta"], r["lo"], r["hi"], q)
                    r["q_bh_tag"] = q
                    r["verdict"] = {"READ_FROM_STATE": pos, "TEXT_SUFFICES": neg}.get(v, v)
    if out_csv is not None:
        V.write_csv(rows, out_csv)
    return rows


def _mean_ci(d: np.ndarray, rng: np.random.Generator) -> tuple[float, float, float]:
    bs = d[rng.integers(0, len(d), (2000, len(d)))].mean(1)
    return float(d.mean()), float(np.quantile(bs, 0.025)), float(np.quantile(bs, 0.975))


def tag_summary(rows: list[dict[str, Any]], render: str, real: str = "R", ctrl: str = "D") -> list[dict[str, Any]]:
    """Per tag (and ALL) at one site: mean Δ_B, Δ_ctrl, Δ_real with fact-bootstrap CIs, the tag-level rules, verdict counts.
    ``real`` / ``ctrl`` = ("R", "D") for the deranged control, ("RM", "M") for the mean control."""
    rng = np.random.default_rng(0)
    by = {(r["contrast"], r["dataset"]): r for r in rows if r["render"] == render}
    dss = sorted({d for (c, d) in by if c == real and (ctrl, d) in by and ("B", d) in by})
    out = []
    for tag in sorted({by[(real, d)]["tag"] for d in dss}) + ["ALL"]:
        sel = [d for d in dss if tag == "ALL" or by[(real, d)]["tag"] == tag]
        if not sel:
            continue
        mb, mr, mc = (_mean_ci(np.array([by[(c, d)]["delta"] for d in sel]), rng) for c in ("B", real, ctrl))
        adds = mr[1] > 0
        c_ex = mc[1] > 0 or mc[2] < 0
        c_same = c_ex and np.sign(mc[0]) == np.sign(mb[0])
        r_ex = mr[1] > 0 or mr[2] < 0
        fmt = ("FORMAT_EFFECT" if c_same and not r_ex else "PART_FORMAT_PART_CONTENT" if c_same and r_ex and np.sign(mr[0]) == np.sign(mc[0])
               else "NO_FORMAT_EFFECT" if not c_ex else "CONTROL_OPPOSITE")
        v = [by[(real, d)].get("verdict") for d in sel]
        out.append({"tag": tag, "render": render, "facts": len(sel), "B": mb, real: mr, ctrl: mc, "adds": adds, "format": fmt,
                    "pos": sum(x in ("ADDS_INFORMATION", "REAL_GT_MEAN") for x in v),
                    "neg": sum(x in ("DERANGED_BETTER", "MEAN_GT_REAL") for x in v), "nd": v.count("NOT_DISTINGUISHED")})
    return out


def summary_table(rows: list[dict[str, Any]], real: str = "R", ctrl: str = "D") -> str:
    lab = {"R": ("real − deranged", "deranged − text"), "RM": ("real − mean", "mean − text")}[real]
    f = lambda m: f"{m[0]:+.3f} [{m[1]:+.3f}, {m[2]:+.3f}]"   # noqa: E731
    lines = [f"| tag | site | facts | v2 gain (real − text) | {lab[1]} | {lab[0]} | adds info (tag) | format reading | facts + / − / n.d. |",
             "|---|---|---|---|---|---|---|---|---|"]
    for render in V.RENDERS:
        for s in tag_summary(rows, render, real, ctrl):
            lines.append(f"| {s['tag']} | {render} | {s['facts']} | {f(s['B'])} | {f(s[ctrl])} | {f(s[real])} | "
                         f"{'yes' if s['adds'] else 'no'} | {s['format']} | {s['pos']} / {s['neg']} / {s['nd']} |")
    return "\n".join(lines)


# ------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items-files", nargs="*", default=list(T.ITEMS_FILES))
    ap.add_argument("--datasets", nargs="*", default=None)
    ap.add_argument("--batch", type=int, default=BATCH)
    ap.add_argument("--pod", default=None)
    ap.add_argument("--smoke", type=int, default=None, help="first N test items (bank order) per fact; r_unfrozen cache; asserts every arm")
    ap.add_argument("--cache-dir", default=None)
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--n-boot", type=int, default=T.N_BOOT)
    ap.add_argument("--exclude-label-defects-ws3", action="store_true")
    ap.add_argument("--gemma-facts", action="store_true")
    a = ap.parse_args(argv)
    cache = Path(a.cache_dir) if a.cache_dir else RC.R_DIR
    if a.analyze:
        if a.gemma_facts:
            rows = V.gemma_rows(analyze(cache, None, a.n_boot), C.RESULTS_DIR / "rg")
            V.write_csv(rows, RC.RESULTS / "text_arm_v3_gemma108.csv")
        else:
            extra, name = ((T.EXCLUDED_WS3, "text_arm_v3_ex_ws3_defects.csv") if a.exclude_label_defects_ws3 else ((), "text_arm_v3.csv"))
            rows = analyze(cache, RC.RESULTS / name, a.n_boot, extra)
        print("### deranged control\n\n" + summary_table(rows, "R", "D") + "\n\n### mean control\n\n" + summary_table(rows, "RM", "M"))
        return 0
    shas = T.check_shas(tuple(a.items_files))
    print(f"[text_arm_v3] banks match the R freeze: {shas}", flush=True)
    RC.set_shard(None, SUFFIX)
    RC.set_run_meta(a.pod, None)
    if a.cache_dir:
        RC.set_cache_dir(Path(a.cache_dir))
    elif a.smoke:
        RC.set_cache_dir(C.CACHE_DIR / "r_unfrozen")
    RC.R_DIR.mkdir(parents=True, exist_ok=True)
    banks = []
    for name in a.items_files:
        p = C.DATASET_DIR / name
        g = RC.items_by_dataset([it for it in B.load_items(p, "all") if not a.datasets or it["dataset"] in a.datasets])
        banks.append((p, {ds: [it for it in its if it["split"] == "test"] for ds, its in g.items()}))
    n_items = sum(len(its) for _, g in banks for its in g.values())
    RC.rlog(f"text arm v3 ({', '.join(ARMS)}, chat/raw, L{V.LAYER}): run={RC.RUN_META} code_sha={code_sha()} banks={shas} "
            f"{n_items} test items, cache={RC.R_DIR}, smoke={a.smoke}, batch={a.batch}")
    try:
        target = load_target_timed(RC.MODULE, RC.LEDGER_PATH)
        (reader,) = RC.bind_readers(target, ["olens"])
        with timed_call() as st_all:
            n = 0
            for arm in ARMS:
                for p, groups in banks:
                    for ds, test in groups.items():
                        if a.smoke:   # the derangement is over the WHOLE fact; the smoke scores its first N items
                            n += _smoke_fact(reader, arm, ds, test, p, a.smoke, a.batch)
                        else:
                            n += collect_v3(reader, arm, ds, test, p, a.batch)
        RC.rlog(f"text arm v3: {n} new rows in {st_all.wall_s / 60:.1f} min -> {out_path()}")
        M.unload(target)
    finally:
        rows = RC.flush_ledgers()
        RC.rlog("text arm v3 ledger: " + "; ".join(f"{r['step']} {r['wall_s']:.0f}s×{r['n_calls']}" for r in rows))
    if a.smoke:
        missing = smoke_missing(out_path(), [p.name for p, _ in banks])
        if missing:
            for m in missing:
                print(f"SMOKE FAILED: missing {m}", flush=True)
            return 3
        print("SMOKE OK: every arm × render × bank has rows", flush=True)
    return 0


def _smoke_fact(reader: Any, arm: str, ds: str, test: list[dict[str, Any]], p: Path, n: int, batch: int) -> int:
    """Smoke: the whole fact's states and derangement, scored on its first ``n`` items (bank order) only."""
    return _collect_subset(reader, arm, ds, test, {it["item_id"] for it in test[:n]}, p, batch)


def _collect_subset(reader: Any, arm: str, dataset: str, test_bank_order: list[dict[str, Any]], keep: set[str], items_path: Path,
                    batch: int) -> int:
    test = RC.ordered_items(test_bank_order)
    ids = [it["item_id"] for it in test]
    pi = frozen_derangement(dataset, test_bank_order)
    H = load_states_v2(dataset, ids)
    base = {**V._base(reader, dataset, test[0].get("tag"), items_path, V.LAYER), "condition": CONDITION,
            "text_arm_v3_code_sha256": code_sha(), "smoke": True}
    n = 0
    for rd in V.RENDERS:
        Hc, sids = control_states(arm, H[rd], ids, pi)
        sel = [i for i, iid in enumerate(ids) if iid in keep and key(arm, iid, rd) not in RC.done_keys(out_path())]
        if not sel:
            continue
        rows = V.score_arm_b(reader, [test[i] for i in sel], Hc[sel], V.LAYER, batch)
        for i, r in zip(sel, rows):
            V._write(out_path(), base, key(arm, ids[i], rd), test[i], r,
                     {"reader": arm, "render": rd, "injection": C.OLENS_INJECTION, "state_item_id": sids[i]})
        n += len(rows)
    return n


if __name__ == "__main__":
    sys.exit(main())
