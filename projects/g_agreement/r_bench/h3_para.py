"""H3 secondary result (BRIEF_R §14): the §4.9 (f) MODEL key from paraphrased prompt-only forced choice, plus the two cheap
pre-freeze collector items that missed the freeze (BD-7 ``--no-activation``, CI-10 ``--candidates-from/--states-from``).

    python -m projects.g_agreement.r_bench.h3_para --write-paraphrases      # CPU: dataset/h3_paraphrases.json (commit + sha BEFORE scoring)
    python -m projects.g_agreement.r_bench.h3_para --check                  # CPU: banks vs the R freeze, paraphrase file vs its pinned sha
    python -m projects.g_agreement.r_bench.h3_para --para --pod PARA-<id>   # pod: p1, p2, p3 on every R-A test item, then every pool item
    python -m projects.g_agreement.r_bench.h3_para --ci10 --pod PARA-<id>   # pod: CI-10 transplanted-label rows (Oracle + J-lens + prompt-only)
    python -m projects.g_agreement.r_bench.h3_para --no-activation ...      # BD-7: the §12 text arm (``text_arm.py``), already run; resumable no-op
    python -m projects.g_agreement.r_bench.h3_para --key                    # CPU: per-item paraphrase-majority MODEL key

Paraphrases are three FIXED templates applied to every R-A question, written programmatically and blind to every result:
the question string and the candidates are inserted verbatim, only the instruction wording and (p2, p3) the order in which
the two candidates are offered change. The pre-registered §4.9 (f) key is the majority of {frozen, p1, p2} (p2 = the swapped
order); p3 (a second swapped wording) is descriptive only (phrasing stability, ICC). Scoring mirrors
``collect.collect_prompt_only`` exactly (adapter off, ``collect.teacher_forced_lp``, both candidates of an item in one
forward, LO = lp(pos) − lp(neg) whatever order the prompt offers them in); collect.py is imported, never edited. Rows go to
``cache/g_agreement/r/h3_para/`` (outside every ``reader_lo*`` / ``prompt_only*`` glob); the PARA suffix sends the log to
``results/g_agreement/r/log.PARA.md`` and the ledger to ``results/g_agreement/compute.PARA.jsonl``.
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
from projects.g_agreement.r_bench import datasets as D
from projects.g_agreement.r_bench import text_arm as T

SUFFIX = "PARA"
OUT_DIR = "h3_para"
PARA_FILE = C.DATASET_DIR / "h3_paraphrases.json"
# sha256 of dataset/h3_paraphrases.json, pinned after --write-paraphrases and committed before any scoring (BRIEF_R §14).
PARA_SHA256 = "1c0d2705917e220357bc79c005f9b550dd5825d6b5c36d7cb442f0f2794a10f8"
KEY_PARAS = ("p1", "p2")        # §4.9 (f): the frozen question + these two; p2 swaps the candidate order
DESCRIPTIVE_PARAS = ("p3",)
# Fixed templates. {text}, {question}, {first}, {second} are filled per item; "swap" says which candidate comes first.
TEMPLATES: dict[str, dict[str, Any]] = {
    "p1": {"swap": False, "user": ("Read the passage below, then answer the question.\n\n"
                                   "Passage:\n{text}\n\n"
                                   "{question}\n"
                                   "Reply with only \"{first}\" or \"{second}\".")},
    "p2": {"swap": True, "user": ("Here is a text.\n\n{text}\n\n"
                                  "Based on this text: {question}\n"
                                  "Respond with one option only, either \"{first}\" or \"{second}\".")},
    "p3": {"swap": True, "user": ("Text:\n{text}\n\n"
                                  "I have a question about the text above. {question} "
                                  "Pick one of the two answers, \"{first}\" or \"{second}\", and write nothing else.")},
}
# CI-10 (ideation causal_inference.md): fact f's candidates (and question) on fact g's states (and text), f and g of different
# tags. The four named in CI-10 first, then 16 drawn by ``ci10_pairs`` (seeded, from the spec list only, blind to results).
CI10_NAMED = (("92_glue_sst2", "21_headline_istrump"), ("95_toxic_is", "87_glue_cola"), ("96_spam_is", "94_ai_gen"),
              ("120_us_timezone_Chicago", "36_sciq_tf"))
CI10_N = 20
CI10_SEED = 10
LABEL_DEFECT = ("139_news_class_Politics", "140_news_class_Technology", "141_news_class_Entertainment",
                "145_disease_class_digestive system diseases", "146_disease_class_cardiovascular diseases")


def out_dir(cache: Path | None = None) -> Path:
    return Path(cache or RC.R_DIR) / OUT_DIR


def para_path(cache: Path | None = None) -> Path:
    return out_dir(cache) / f"prompt_only.{SUFFIX}.jsonl"


def code_sha() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


# ------------------------------------------------------------------ the paraphrase file
def paraphrase_table() -> dict[str, Any]:
    """Per R-A dataset: the frozen question / candidates and the three templates (text left as {text}). Built from
    ``datasets.SPECS`` only."""
    out = {}
    for name, spec in sorted(D.SPECS.items()):
        out[name] = {"question": spec.question, "pos": spec.pos, "neg": spec.neg,
                     "frozen": D.PROMPT_ONLY_FC_TEMPLATE.replace("{question}", spec.question)
                     .replace("{pos}", spec.pos).replace("{neg}", spec.neg),
                     **{k: _fill(t, spec.question, spec.pos, spec.neg) for k, t in TEMPLATES.items()}}
    # "§13": the section number when the file was written and pinned; the section is §14 since the merge renumbering (file unchanged)
    return {"meta": {"purpose": "BRIEF_R §13 / §4.9 (f) paraphrases", "written": now_iso(), "templates": TEMPLATES,
                     "key_paraphrases": list(KEY_PARAS), "descriptive": list(DESCRIPTIVE_PARAS),
                     "frozen_template": D.PROMPT_ONLY_FC_TEMPLATE, "n_datasets": len(out)}, "datasets": out}


def _fill(t: dict[str, Any], question: str, pos: str, neg: str) -> str:
    first, second = (neg, pos) if t["swap"] else (pos, neg)
    # sequential replace (not str.format) so braces inside a question can never break the template
    return t["user"].replace("{question}", question).replace("{first}", first).replace("{second}", second)


def write_paraphrases(path: Path = PARA_FILE) -> str:
    d = paraphrase_table()
    path.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
    sha = C.sha256_file(path)
    print(f"wrote {path}: {d['meta']['n_datasets']} datasets × {len(TEMPLATES)} templates, sha256 {sha}")
    return sha


def load_paraphrases(path: Path = PARA_FILE, pinned: str | None = None) -> dict[str, Any]:
    """The committed file; refuses if it differs from the pinned sha (``PARA_SHA256``) or from the templates in this module."""
    pinned = PARA_SHA256 if pinned is None else pinned
    sha = C.sha256_file(path)
    if pinned is not None and sha != pinned:
        raise SystemExit(f"refusing: {path.name} sha {sha} != pinned {pinned}")
    d = json.loads(path.read_text())
    if d["meta"]["templates"] != TEMPLATES:
        raise SystemExit(f"refusing: {path.name} templates differ from h3_para.TEMPLATES")
    return d


def para_user(item: dict[str, Any], k: str, table: dict[str, Any], tokenizer: Any) -> str:
    """The forced-choice user turn of paraphrase ``k`` for one item: the dataset's filled template with the item's text cut
    exactly as the frozen prompt-only render (``collect.truncate_text``)."""
    text = RC.truncate_text(tokenizer, item["prompt_text"], RC.MAX_TOKENS)
    return table["datasets"][item["dataset"]][k].replace("{text}", text)


def para_ids(tokenizer: Any, item: dict[str, Any], k: str, table: dict[str, Any]) -> list[int]:
    if item.get("capture_messages"):
        raise ValueError("R-A items carry no earlier turns")
    return M.render_item(tokenizer, para_user(item, k, table, tokenizer), item.get("system"))


def para_key(dataset: str, item_id: str, k: str) -> str:
    return f"po|{dataset}|{item_id}|{k}"


# ------------------------------------------------------------------ scoring (mirrors collect.collect_prompt_only)
def collect_para(target: M.Target, dataset: str, items: list[dict[str, Any]], k: str, table: dict[str, Any],
                 batch: int = 32, cache: Path | None = None) -> int:
    path = para_path(cache)
    todo = [it for it in items if para_key(dataset, it["item_id"], k) not in RC.done_keys(path)]
    if not todo:
        return 0
    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    dev = next(target.model.parameters()).device
    led = RC.ledger(f"prompt_only_{k}", batch=batch)
    shas = {**RC.r_shas(B.ITEMS_R), "paraphrase_file_sha256": C.sha256_file(PARA_FILE), "h3_para_code_sha256": code_sha()}
    n = 0
    per = max(1, batch // 2)
    for s in range(0, len(todo), per):
        chunk = todo[s: s + per]
        heads = [para_ids(tok, it, k, table) for it in chunk]
        rows, head_lens = [], []
        for it, head in zip(chunk, heads):
            for c in it["primary"]["candidates"][:2]:          # always (pos, neg): LO keeps its sign whatever the offer order
                rows.append(head + LO.encode(tok, c))
                head_lens.append(len(head))
        with timed_call() as st:
            with M.disable_adapter_ctx(target.model):
                lps = RC.teacher_forced_lp(target.model, rows, head_lens, pad, dev)
        for q, (it, head) in enumerate(zip(chunk, heads)):
            lp_pos, lp_neg = lps[2 * q], lps[2 * q + 1]
            RC.append_row(path, {"key": para_key(dataset, it["item_id"], k), "module": RC.MODULE, "dataset": dataset,
                                 "tag": it.get("tag"), "item_id": it["item_id"], "split": it["split"], "label": it["label"],
                                 "paraphrase": k, "swap": TEMPLATES[k]["swap"], "candidates": it["primary"]["candidates"][:2],
                                 "lp": [lp_pos, lp_neg], "lp_pos": lp_pos, "lp_neg": lp_neg, "lo": lp_pos - lp_neg,
                                 "greedy": int(lp_neg > lp_pos), "model_says_pos": bool(lp_pos > lp_neg),
                                 "n_head_tokens": len(head), "adapter": "none", "system": bool(it.get("system")),
                                 "template": f"fc_{k}", "condition": "paraphrase", **shas, "created_at": now_iso()})
            n += 1
        led.add(sum(len(r) for r in rows), 0, st.wall_s, st.peak_mem_gb)
    print(f"[r/h3_para/{k}] {dataset}: {n} items", flush=True)
    return n


# ------------------------------------------------------------------ CI-10 (--candidates-from f --states-from g)
def ci10_pairs(n: int = CI10_N, seed: int = CI10_SEED) -> list[tuple[str, str]]:
    """The 4 named CI-10 pairs, then seeded draws: f two-sided (so both candidates are concepts), g of a different tag,
    no label-defect fact, every f used once. Uses the spec list only (no data, no results)."""
    pairs = list(CI10_NAMED)
    used_f = {f for f, _ in pairs}
    names = sorted(k for k in D.SPECS if k not in LABEL_DEFECT)
    two = [k for k in names if D.SPECS[k].sided == "two" and k not in used_f]
    rng = np.random.default_rng(seed)
    for f in rng.permutation(two):
        if len(pairs) >= n:
            break
        gs = [g for g in names if D.SPECS[g].tag != D.SPECS[f].tag and g not in {x for _, x in pairs}]
        pairs.append((str(f), str(gs[int(rng.integers(len(gs)))])))
    return pairs


def transplant(items_g: list[dict[str, Any]], f: str) -> list[dict[str, Any]]:
    """g's items with f's primary (question, candidates, template, sidedness); g's label kept as ``label``."""
    sf = D.SPECS[f]
    prim = {"name": f, "question": sf.question, "candidates": [sf.pos, sf.neg], "template": sf.template, "sided": sf.sided,
            "jlens": [sf.jlens_pos, sf.jlens_neg]}   # exactly as bank.py builds an item's primary
    return [{**it, "primary": prim, "g_dataset": it["dataset"], "f_dataset": f} for it in items_g]


def collect_ci10(target: M.Target, readers: list[Any], pairs: list[tuple[str, str]], batch: int = 32, cache: Path | None = None) -> int:
    """Per pair: each reader at its primary layer, chat render, on g's TEST states (from the main R cache) with f's
    candidates; prompt-only with f's question on g's text (frozen FC template). Rows: ``ci10_lo.PARA.jsonl``,
    ``ci10_po.PARA.jsonl``."""
    import torch

    lo_path, po_path = out_dir(cache) / f"ci10_lo.{SUFFIX}.jsonl", out_dir(cache) / f"ci10_po.{SUFFIX}.jsonl"
    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    dev = next(target.model.parameters()).device
    allitems = B.load_items(B.ITEMS_R, "all")
    n = 0
    for f, g in pairs:
        test_g = [it for it in allitems if it["dataset"] == g and it["split"] == "test"]
        its = transplant(test_g, f)
        meta = {"module": RC.MODULE, "f_dataset": f, "g_dataset": g, "f_tag": D.SPECS[f].tag, "g_tag": D.SPECS[g].tag,
                "condition": "ci10", "render": "chat", "h3_para_code_sha256": code_sha(), **RC.r_shas(B.ITEMS_R)}
        for rd in readers:
            L = RC.PRIMARY_LAYER[RC.base_name(rd)]
            keys = [f"ci10|{rd.name}|L{L}|chat|{f}|{it['item_id']}" for it in its]
            if all(k in RC.done_keys(lo_path) for k in keys):
                continue
            X, idx = RC.load_states(g, "chat", L)
            pos_of = {iid: i for i, iid in enumerate(idx)}
            H = torch.from_numpy(X[[pos_of[it["item_id"]] for it in its]])
            led = RC.ledger(f"ci10_{rd.name}_L{L}", batch=batch)
            with timed_call() as st:
                rows = RC.score_items(rd, H, its, L, batch)
            for it, key, r in zip(its, keys, rows):
                RC.append_row(lo_path, {"key": key, **meta, "reader": rd.name, "layer": L, "item_id": it["item_id"],
                                        "label_g": it["label"], "sided_f": it["primary"]["sided"], "cand_A": r["cand_A"],
                                        "cand_B": r["cand_B"], "lp_A": r["lp_A"], "lp_B": r["lp_B"], "lo": r["lo"],
                                        "unscorable": r["unscorable"], "family": r["family"], "created_at": now_iso()})
                n += 1
            led.add(0, 0, st.wall_s, st.peak_mem_gb)
        todo = [it for it in its if f"ci10|po|{f}|{it['item_id']}" not in RC.done_keys(po_path)]
        led = RC.ledger("ci10_prompt_only", batch=batch)
        for s in range(0, len(todo), max(1, batch // 2)):
            chunk = todo[s: s + max(1, batch // 2)]
            heads = [RC.prompt_only_ids(tok, it) for it in chunk]
            rows, hl = [], []
            for it, h in zip(chunk, heads):
                for c in it["primary"]["candidates"]:
                    rows.append(h + LO.encode(tok, c))
                    hl.append(len(h))
            with timed_call() as st:
                with M.disable_adapter_ctx(target.model):
                    lps = RC.teacher_forced_lp(target.model, rows, hl, pad, dev)
            for q, it in enumerate(chunk):
                RC.append_row(po_path, {"key": f"ci10|po|{f}|{it['item_id']}", **meta, "reader": "prompt_only", "item_id": it["item_id"],
                                        "label_g": it["label"], "lp_pos": lps[2 * q], "lp_neg": lps[2 * q + 1],
                                        "lo": lps[2 * q] - lps[2 * q + 1], "created_at": now_iso()})
                n += 1
            led.add(sum(len(r) for r in rows), 0, st.wall_s, st.peak_mem_gb)
        print(f"[r/h3_para/ci10] {f} on {g}: done", flush=True)
    return n


# ------------------------------------------------------------------ the MODEL key (CPU)
def model_key(frozen: dict[str, dict[str, Any]], para: dict[tuple[str, str], dict[str, Any]], item_ids: list[str]) -> list[dict[str, Any]]:
    """Per item: the §4.9 (f) key = majority of model_says_pos over {frozen, p1, p2}; ``stable`` iff all three agree;
    ``stable4`` adds p3 (descriptive). Items missing any key phrasing get ``key = None``."""
    out = []
    for iid in item_ids:
        f = frozen.get(iid)
        votes = [f["model_says_pos"]] if f is not None else []
        votes += [para[(iid, k)]["model_says_pos"] for k in KEY_PARAS if (iid, k) in para]
        row = {"item_id": iid, "n_votes": len(votes)}
        if len(votes) == 1 + len(KEY_PARAS):
            row.update(key_model_pos=sum(votes) * 2 > len(votes), stable=len(set(votes)) == 1,
                       frozen_model_pos=votes[0], flips_vs_frozen=(sum(votes) * 2 > len(votes)) != votes[0])
            extra = [para[(iid, k)]["model_says_pos"] for k in DESCRIPTIVE_PARAS if (iid, k) in para]
            if extra:
                row["stable4"] = len(set(votes + extra)) == 1
        else:
            row["key_model_pos"] = None
        out.append(row)
    return out


# ------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write-paraphrases", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--para", action="store_true", help="paraphrase prompt-only rows (p1 p2 p3), test then pool")
    ap.add_argument("--paraphrases", nargs="*", default=list(TEMPLATES))
    ap.add_argument("--splits", nargs="*", default=["test", "pool"])
    ap.add_argument("--ci10", action="store_true", help="CI-10: --candidates-from f --states-from g on the pre-registered pairs")
    ap.add_argument("--ci10-readers", nargs="*", default=["jlens", "olens"])
    ap.add_argument("--no-activation", action="store_true", help="BD-7: delegate to text_arm.py (the §12 run; resumable)")
    ap.add_argument("--key", action="store_true", help="CPU: write the per-item MODEL key")
    ap.add_argument("--datasets", nargs="*", default=None)
    ap.add_argument("--smoke", type=int, default=None, help="first N items per dataset and split; writes under r_unfrozen")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--pod", default=None)
    ap.add_argument("--cache-dir", default=None)
    a = ap.parse_args(argv)
    if a.write_paraphrases:
        write_paraphrases()
        return 0
    if a.no_activation:
        return T.main(["--pod", a.pod or "PARA"] + (["--datasets", *a.datasets] if a.datasets else []))
    table = load_paraphrases()
    shas = T.check_shas(("items_r.json",))
    print(f"[h3_para] items_r.json matches the R freeze; paraphrase file sha {C.sha256_file(PARA_FILE)}", flush=True)
    if a.check:
        return 0
    cache = Path(a.cache_dir) if a.cache_dir else (C.CACHE_DIR / "r_unfrozen" if a.smoke else None)
    if a.key:
        return write_key(cache)
    RC.set_shard(None, SUFFIX)
    RC.set_run_meta(a.pod, None)
    items = [it for it in B.load_items(B.ITEMS_R, "all") if not a.datasets or it["dataset"] in a.datasets]
    groups = RC.items_by_dataset(items)
    RC.rlog(f"h3_para: run={RC.RUN_META} code_sha={code_sha()} banks={shas} paraphrases={a.paraphrases} splits={a.splits} "
            f"ci10={a.ci10} smoke={a.smoke} out={out_dir(cache)}")
    try:
        target = load_target_timed(RC.MODULE, RC.LEDGER_PATH)
        with timed_call() as st_all:
            n = 0
            if a.para:
                for split in a.splits:            # all test items first (R3), then pool (the MODEL-answer probe reference)
                    for k in a.paraphrases:
                        for ds, its in groups.items():
                            sel = [it for it in its if it["split"] == split][: a.smoke or None]
                            n += collect_para(target, ds, sel, k, table, a.batch, cache)
                        RC.rlog(f"h3_para {split} {k}: done, {n} new rows so far")
                        RC.flush_ledgers()
            if a.ci10:
                readers = RC.bind_readers(target, a.ci10_readers)
                pairs = ci10_pairs()
                n += collect_ci10(target, readers, pairs if not a.smoke else pairs[:2], a.batch, cache)
                RC.rlog(f"h3_para ci10: {len(pairs)} pairs done")
        RC.rlog(f"h3_para: {n} new rows in {st_all.wall_s / 60:.1f} min -> {out_dir(cache)}")
        M.unload(target)
    finally:
        rows = RC.flush_ledgers()
        RC.rlog("h3_para ledger: " + "; ".join(f"{r['step']} {r['wall_s']:.0f}s×{r['n_calls']}" for r in rows))
    return 0


def write_key(cache: Path | None) -> int:
    """``h3_para/model_key.PARA.jsonl``: one row per R-A item (test + pool) from the frozen prompt-only rows (every
    ``prompt_only*.jsonl`` of the main R cache) and the paraphrase rows."""
    root = Path(cache or RC.R_DIR)
    frozen: dict[str, dict[str, Any]] = {}
    for p in sorted(root.glob("prompt_only*.jsonl")):
        if p.name.split(".")[-2] in ("D",) or "planted" in p.name:
            continue
        for r in T._iter_rows(p, '"key": "po|'):
            if r.get("template") == "fc":
                frozen[r["item_id"]] = r
    para = {(r["item_id"], r["paraphrase"]): r for r in T._iter_rows(para_path(root), '"paraphrase"')}
    items = B.load_items(B.ITEMS_R, "all")
    rows = model_key(frozen, para, [it["item_id"] for it in items])
    meta = {it["item_id"]: it for it in items}
    path = out_dir(root) / f"model_key.{SUFFIX}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for r in rows:
            it = meta[r["item_id"]]
            fh.write(json.dumps({**r, "dataset": it["dataset"], "tag": it["tag"], "split": it["split"], "label": it["label"]}) + "\n")
    done = [r for r in rows if r["key_model_pos"] is not None]
    print(f"wrote {path}: {len(done)}/{len(rows)} items keyed; unstable {sum(not r['stable'] for r in done)}; "
          f"key ≠ frozen {sum(r['flips_vs_frozen'] for r in done)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
