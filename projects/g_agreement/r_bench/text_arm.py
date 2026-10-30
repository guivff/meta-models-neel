"""The Oracle lens given the TEXT instead of the activation (BRIEF_R §12; the Li control of BRIEF_RG §10 on Qwen3.6-27B).

    python -m projects.g_agreement.r_bench.text_arm --check-shas                        # CPU: the banks against the R freeze
    python -m projects.g_agreement.r_bench.text_arm --smoke 4 --datasets 92_glue_sst2   # pod: 4 test items, unfrozen cache
    python -m projects.g_agreement.r_bench.text_arm --pod TXT                           # pod: every R-A + ReaderBench test item
    python -m projects.g_agreement.r_bench.text_arm --analyze                           # Mac: activation − text per fact, by tag

Arm ``olens_txt``: the frozen Oracle-lens reader (``collect.bind_readers(target, ["olens"])``, LoRA active), NO injection;
the carrier prompt ``C.OLENS_PROMPT`` at layer 44 with the item's text between the activation tags where the frozen run
puts the marker character; candidates ``collect.item_pair``, ``lp("- {cand}")`` teacher-forced by
``collect.teacher_forced_lp`` (per-row heads, both candidates of an item in one forward). collect.py is imported, never
edited (the pods run the frozen file). Rows go to ``cache/g_agreement/r/text_arm/text_arm_lo.jsonl`` with
``condition = "text_arm"`` — outside the ``reader_lo*.jsonl`` glob, so ``analyze.py`` never merges them into the main
cells; the TXT suffix (``collect.set_shard(None, "TXT")``) sends the log to ``results/g_agreement/r/log.TXT.md`` and the
ledger to ``results/g_agreement/compute.TXT.jsonl``. Every row carries ``pod``, ``git_sha`` and ``text_arm_code_sha256``.
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
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import now_iso, timed_call
from projects.g_agreement.r_bench import bank as B
from projects.g_agreement.r_bench import collect as RC

NAME = "olens_txt"
LAYER = 44                      # the Oracle's primary site (collect.PRIMARY_LAYER["olens"]); "layer 44" in the prompt
RENDER = "text"
SUFFIX = "TXT"
CONDITION = "text_arm"
OUT_DIR = "text_arm"           # under the R cache: cache/g_agreement/r/text_arm/
OUT_NAME = "text_arm_lo.jsonl"
ITEMS_FILES = ("items_r.json", "items_rb.json")
EXCLUDED = ("139_news_class_Politics", "140_news_class_Technology", "141_news_class_Entertainment", "97_news_class")
# Sensitivity only (BRIEF_R §12 Deviations 2026-10-19): WS3 found 101_disease_class's class names permuted after the §12 freeze;
# the pre-registered table keeps them, ``--exclude-label-defects-ws3`` writes a second table without them.
EXCLUDED_WS3 = ("145_disease_class_digestive system diseases", "146_disease_class_cardiovascular diseases", "101_disease_class")
ACT_LAYERS = (42, 44, 48, 52, 56)   # activation arm: 44 inferential (chat primary, raw secondary), the rest descriptive
INFERENTIAL = (("chat", 44), ("raw", 44))
N_BOOT = 2000
BH_Q = 0.10
ROLE = {"system": "System", "user": "User", "assistant": "Assistant"}


def code_sha() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


# ------------------------------------------------------------------ the prompt
def item_text(tokenizer: Any, item: dict[str, Any], max_tokens: int = RC.MAX_TOKENS) -> str:
    """What the state saw, as text: ``prompt_text`` cut like the capture (``collect.truncate_text``); after a system turn
    or earlier turns, the whole conversation one turn per line (``System: …`` / ``User: …`` / ``Assistant: …``)."""
    last = RC.truncate_text(tokenizer, item["prompt_text"], max_tokens)
    msgs = item.get("capture_messages")
    if msgs:
        if msgs[-1]["role"] != "user" or msgs[-1]["content"] != item["prompt_text"]:
            raise ValueError(f"{item['item_id']}: capture_messages must end with prompt_text as the user turn")
        turns = [(m["role"], m["content"]) for m in msgs[:-1]] + [("user", last)]
    elif item.get("system"):
        turns = [("system", item["system"]), ("user", last)]
    else:
        return last
    return "\n".join(f"{ROLE[r]}: {c}" for r, c in turns)


def text_carrier_ids(tokenizer: Any, text: str, layer: int = LAYER, prompt: str = C.OLENS_PROMPT) -> list[int]:
    """The Oracle's carrier render (``core.readers.olens_carrier``: one user turn, thinking off) with ``text`` in the
    marker's place. With ``text`` = the marker character this is exactly the frozen carrier."""
    return M.chat_ids(tokenizer, [{"role": "user", "content": prompt.format(layer=layer, char=text)}])


# ------------------------------------------------------------------ scoring
def score_text_items(reader: Any, items: list[dict[str, Any]], layer: int = LAYER, batch: int = 32) -> list[dict[str, Any]]:
    """One row per item: ``lp_A`` = lp("- pos"), ``lp_B`` = lp("- neg") after the text carrier, ``lo`` = difference.
    ``batch`` rows per forward (``batch // 2`` items), items of similar length together; the adapter stays as bound."""
    t = reader.target
    tok = t.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    dev = next(t.model.parameters()).device
    heads = [text_carrier_ids(tok, item_text(tok, it), layer) for it in items]
    order = sorted(range(len(items)), key=lambda i: len(heads[i]))
    per = max(1, batch // 2)
    out: list[dict[str, Any] | None] = [None] * len(items)
    for s in range(0, len(order), per):
        chunk = order[s: s + per]
        rows, head_lens, cands = [], [], []
        for i in chunk:
            pos, neg = RC.item_pair("olens", items[i]["primary"])
            cands.append((pos, neg))
            for c in (pos, neg):
                rows.append(heads[i] + LO.encode(tok, LO.OLENS_BULLET.format(X=c)))
                head_lens.append(len(heads[i]))
        with timed_call() as st:
            lps = RC.teacher_forced_lp(t.model, rows, head_lens, pad, dev)
        for q, i in enumerate(chunk):
            lp_a, lp_b = lps[2 * q], lps[2 * q + 1]
            out[i] = {"cand_A": cands[q][0], "cand_B": cands[q][1], "lp_A": lp_a, "lp_B": lp_b, "lo": lp_a - lp_b,
                      "n_head_tokens": len(heads[i]), "n_tokens_A": len(rows[2 * q]) - len(heads[i]),
                      "n_tokens_B": len(rows[2 * q + 1]) - len(heads[i]), "wall_s_chunk": st.wall_s, "chunk_size": len(chunk),
                      "peak_mem_gb": st.peak_mem_gb}
    return [r for r in out if r is not None]


def out_path(cache: Path | None = None) -> Path:
    """``<R cache>/text_arm/text_arm_lo.jsonl`` (never a ``reader_lo*.jsonl`` name: analyze.py globs those)."""
    return Path(cache or RC.R_DIR) / OUT_DIR / OUT_NAME


def lo_key(item_id: str, layer: int = LAYER) -> str:
    return f"{NAME}|L{layer}|{RENDER}|{item_id}"


def collect_text_arm(reader: Any, dataset: str, items: list[dict[str, Any]], items_path: Path, layer: int = LAYER,
                     batch: int = 32) -> int:
    """Rows for the TEST items of one dataset not yet in ``text_arm/text_arm_lo.jsonl`` (resumable by key)."""
    test = [it for it in items if it["split"] == "test" and lo_key(it["item_id"], layer) not in RC.done_keys(out_path())]
    if not test:
        return 0
    base = {"module": RC.MODULE, "reader": NAME, "reader_family": "olens", "layer": layer, "layer_in_prompt": layer,
            "render": RENDER, "position": "last", "condition": CONDITION, "dataset": dataset, "tag": test[0].get("tag"),
            "alpha": getattr(reader, "alpha", None), "injection": "none", "format": "bullet_text",
            "templates": [LO.OLENS_BULLET], "text_arm_code_sha256": code_sha(), **RC.r_shas(items_path)}
    led = RC.ledger(f"lo_{NAME}_L{layer}", batch=batch)
    tok = reader.target.tokenizer
    with timed_call() as st:
        rows = score_text_items(reader, test, layer, batch)
    for it, r in zip(test, rows):
        n_text = len(LO.encode(tok, it["prompt_text"]))
        RC.append_row(out_path(), {"key": lo_key(it["item_id"], layer), **base, "split": it["split"], "item_id": it["item_id"],
                                   "state_item_id": None, "label": it["label"], "sided": it["primary"].get("sided", "two"),
                                   "family": RC.family_for(it["primary"]), "system": bool(it.get("system")),
                                   "multi_turn": bool(it.get("capture_messages")), "text_truncated": n_text > RC.MAX_TOKENS,
                                   "unscorable": False, **{k: v for k, v in r.items() if k != "peak_mem_gb"},
                                   "created_at": now_iso()})
    led.add(sum(r["n_head_tokens"] + r["n_tokens_A"] + r["n_head_tokens"] + r["n_tokens_B"] for r in rows), 0, st.wall_s, st.peak_mem_gb)
    print(f"[r/{NAME}/L{layer}] {dataset}: {len(rows)} rows, {st.wall_s:.0f}s", flush=True)
    return len(rows)


# ------------------------------------------------------------------ freeze check
def check_shas(names: tuple[str, ...] = ITEMS_FILES) -> dict[str, str]:
    """sha256 of every bank against ``manifest/frozen_config_r.json`` ``items_sha256``; SystemExit on any mismatch."""
    if not RC.FROZEN_R.exists():
        raise SystemExit(f"{RC.FROZEN_R} missing")
    fz = json.loads(RC.FROZEN_R.read_text())
    if not fz.get("frozen"):
        raise SystemExit("frozen_config_r.json has frozen=false")
    out = {}
    for name in names:
        p = C.DATASET_DIR / name
        want = (fz.get("items_sha256") or {}).get(name)
        got = C.sha256_file(p)
        if want is None or got != want:
            raise SystemExit(f"refusing to run: {name} sha {got} != frozen {want}")
        out[name] = got
    return out


# ------------------------------------------------------------------ analysis (Mac, CPU)
def _iter_rows(path: Path, needle: str):
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if needle not in line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:   # a half-written last line of a live shard
                continue


def activation_scores(cache: Path, layers: tuple[int, ...] = ACT_LAYERS) -> dict[tuple[str, int], dict[str, dict[str, Any]]]:
    """{(render, layer): {item_id: row}} for the frozen Oracle's natural test rows at the last position, every
    ``reader_lo*.jsonl`` (last occurrence of a key wins, as ``analyze.read_jsonl_shards``)."""
    out: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
    for p in sorted(cache.glob("reader_lo*.jsonl")):
        for r in _iter_rows(p, '"reader": "olens"'):
            if (r.get("reader") != "olens" or r.get("condition") != "natural" or r.get("split") != "test"
                    or r.get("position", "last") != "last" or r.get("layer") not in layers or r.get("unscorable")):
                continue
            out.setdefault((r["render"], r["layer"]), {})[r["item_id"]] = r
    return out


def model_labels(cache: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    for p in sorted(cache.glob("model_labels*.jsonl")):
        for r in _iter_rows(p, '"key"'):
            if r.get("model_label") is not None:
                out[r["item_id"]] = int(r["model_label"])
    return out


def primary(r: dict[str, Any]) -> float:
    """s_diff two-sided, s_pos one-sided (BRIEF_R §2.1, ``analyze.primary_score``)."""
    return float(r["lo"] if r.get("sided", "two") == "two" else r["lp_A"])


def bh(p: list[float]) -> list[float]:
    """Benjamini–Hochberg adjusted p-values (step-up, monotone)."""
    p_arr = np.asarray(p, dtype=float)
    n = len(p_arr)
    if n == 0:
        return []
    order = np.argsort(p_arr)
    adj = p_arr[order] * n / np.arange(1, n + 1)
    adj = np.minimum.accumulate(adj[::-1])[::-1]
    out = np.empty(n)
    out[order] = np.minimum(adj, 1.0)
    return out.tolist()


def auroc_rows(y: np.ndarray, s: np.ndarray) -> np.ndarray:
    """AUROC per row of [B, n] labels / scores (Mann–Whitney on mid-ranks, ties count 1/2); NaN for one-class rows."""
    from scipy.stats import rankdata

    y = np.atleast_2d(y).astype(bool)
    r = rankdata(np.atleast_2d(s), axis=1)
    n1 = y.sum(1)
    n0 = y.shape[1] - n1
    with np.errstate(invalid="ignore", divide="ignore"):
        return ((r * y).sum(1) - n1 * (n1 + 1) / 2) / (n1 * n0)


def paired_delta(y: np.ndarray, s_act: np.ndarray, s_txt: np.ndarray, n_boot: int = N_BOOT, seed: int = 0) -> dict[str, float]:
    """Δ = AUROC(act) − AUROC(text), item-paired bootstrap (``common.stats.auc_diff_bootstrap``'s resampling: items
    drawn with replacement, one-class draws skipped), 95% percentile CI and the two-sided bootstrap p."""
    y, s_act, s_txt = np.asarray(y), np.asarray(s_act, float), np.asarray(s_txt, float)
    a0, t0 = float(auroc_rows(y, s_act)[0]), float(auroc_rows(y, s_txt)[0])
    i = np.random.default_rng(seed).integers(0, len(y), (n_boot, len(y)))
    v = auroc_rows(y[i], s_act[i]) - auroc_rows(y[i], s_txt[i])
    v = v[~np.isnan(v)]
    p = min(1.0, 2 * min(float((v <= 0).mean()), float((v >= 0).mean())))
    return {"auc_act": float(a0), "auc_txt": float(t0), "delta": float(a0 - t0), "lo": float(np.quantile(v, 0.025)),
            "hi": float(np.quantile(v, 0.975)), "p": p}


def verdict(d: float, lo: float, hi: float, q: float) -> str:
    if d > 0 and lo > 0 and q <= BH_Q:
        return "READ_FROM_STATE"
    if d < 0 and hi < 0 and q <= BH_Q:
        return "TEXT_SUFFICES"
    return "NOT_DISTINGUISHED"


def analyze(cache: Path, out_csv: Path, n_boot: int = N_BOOT, extra_excluded: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    """The per-fact table (BRIEF_R §12) for every (render, layer) with activation rows; BH within tag on the two
    inferential sites only, ``verdict`` empty on the descriptive ones."""
    import csv

    txt = {r["item_id"]: r for r in _iter_rows(out_path(cache), f'"reader": "{NAME}"')
           if r.get("condition") == CONDITION}
    act = activation_scores(cache)
    ml = model_labels(cache)
    by_ds: dict[str, list[dict[str, Any]]] = {}
    for r in txt.values():
        if r["dataset"] not in EXCLUDED and r["dataset"] not in extra_excluded:
            by_ds.setdefault(r["dataset"], []).append(r)
    rows: list[dict[str, Any]] = []
    for (render, layer), arows in sorted(act.items()):
        for ds, trs in sorted(by_ds.items()):
            pairs = [(t, arows[t["item_id"]]) for t in trs if t["item_id"] in arows]
            if not pairs:
                continue
            y = np.array([ml.get(t["item_id"], t["label"]) for t, _ in pairs])
            if len(set(y)) < 2:
                continue
            s_t = np.array([primary(t) for t, _ in pairs])
            s_a = np.array([primary(a) for _, a in pairs])
            rows.append({"dataset": ds, "tag": trs[0]["tag"], "bank": trs[0]["items_file"], "render": render, "layer": layer,
                         "n": len(pairs), "n_text_rows": len(trs), **paired_delta(y, s_a, s_t, n_boot)})
    for render, layer in INFERENTIAL:
        site = [r for r in rows if r["render"] == render and r["layer"] == layer]
        for tag in sorted({r["tag"] for r in site}):
            fam = [r for r in site if r["tag"] == tag]
            for r, q in zip(fam, bh([r["p"] for r in fam])):
                r["q_bh_tag"] = q
                r["verdict"] = verdict(r["delta"], r["lo"], r["hi"], q)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    cols = ["dataset", "tag", "bank", "render", "layer", "n", "n_text_rows", "auc_act", "auc_txt", "delta", "lo", "hi", "p", "q_bh_tag", "verdict"]
    with out_csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    return rows


def tag_table(rows: list[dict[str, Any]], render: str, layer: int) -> str:
    """Markdown: per tag at one site, n facts, medians and verdict counts."""
    site = [r for r in rows if r["render"] == render and r["layer"] == layer]
    lines = [f"| tag | facts | AUROC act | AUROC text | median Δ | Δ > 0 | state | text suffices | n.d. |", "|---|---|---|---|---|---|---|---|---|"]
    for tag in sorted({r["tag"] for r in site}) + ["ALL"]:
        fam = site if tag == "ALL" else [r for r in site if r["tag"] == tag]
        v = [r.get("verdict") for r in fam]
        lines.append(f"| {tag} | {len(fam)} | {np.median([r['auc_act'] for r in fam]):.3f} | {np.median([r['auc_txt'] for r in fam]):.3f} | "
                     f"{np.median([r['delta'] for r in fam]):+.3f} | {sum(r['delta'] > 0 for r in fam)} | {v.count('READ_FROM_STATE')} | "
                     f"{v.count('TEXT_SUFFICES')} | {v.count('NOT_DISTINGUISHED')} |")
    return "\n".join(lines)


# ------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items-files", nargs="*", default=list(ITEMS_FILES))
    ap.add_argument("--datasets", nargs="*", default=None)
    ap.add_argument("--layer", type=int, default=LAYER)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--pod", default=None)
    ap.add_argument("--smoke", type=int, default=None, help="only the first N test items per dataset; writes under r_unfrozen")
    ap.add_argument("--cache-dir", default=None)
    ap.add_argument("--check-shas", action="store_true", help="verify the banks against the R freeze and exit")
    ap.add_argument("--analyze", action="store_true", help="CPU: activation − text per fact (results/g_agreement/r/text_arm.csv)")
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--exclude-label-defects-ws3", action="store_true",
                    help="sensitivity: also drop EXCLUDED_WS3 (results/g_agreement/r/text_arm_ex_ws3_defects.csv)")
    a = ap.parse_args(argv)
    if a.analyze:
        cache = Path(a.cache_dir) if a.cache_dir else RC.R_DIR
        extra = EXCLUDED_WS3 if a.exclude_label_defects_ws3 else ()
        name = "text_arm_ex_ws3_defects.csv" if extra else "text_arm.csv"
        rows = analyze(cache, RC.RESULTS / name, a.n_boot, extra)
        for render, layer in INFERENTIAL:
            print(f"\n### activation (Oracle, block {layer}, {render}) − text (olens_txt)\n\n{tag_table(rows, render, layer)}")
        return 0
    shas = check_shas(tuple(a.items_files))
    print(f"[text_arm] banks match the R freeze: {shas}", flush=True)
    if a.check_shas:
        return 0
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
        its = [it for it in B.load_items(p, "all") if it["split"] == "test" and (not a.datasets or it["dataset"] in a.datasets)]
        banks.append((p, RC.items_by_dataset(its)))
    if a.smoke:
        banks = [(p, {ds: its[: a.smoke] for ds, its in g.items()}) for p, g in banks]
    n_items = sum(len(its) for _, g in banks for its in g.values())
    RC.rlog(f"text arm ({NAME}, prompt layer {a.layer}): run={RC.RUN_META} code_sha={code_sha()} banks={shas} "
            f"{n_items} test items, cache={RC.R_DIR}, smoke={a.smoke}")
    try:
        target = load_target_timed(RC.MODULE, RC.LEDGER_PATH)
        (reader,) = RC.bind_readers(target, ["olens"])
        with timed_call() as st_all:
            n = 0
            for p, groups in banks:
                for ds, its in groups.items():
                    n += collect_text_arm(reader, ds, its, p, a.layer, a.batch)
        RC.rlog(f"text arm: {n} new rows in {st_all.wall_s / 60:.1f} min -> {out_path()}")
        M.unload(target)
    finally:
        rows = RC.flush_ledgers()
        RC.rlog("text arm ledger: " + "; ".join(f"{r['step']} {r['wall_s']:.0f}s×{r['n_calls']}" for r in rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
