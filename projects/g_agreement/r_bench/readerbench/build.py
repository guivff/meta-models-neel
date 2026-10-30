"""ReaderBench builder (PLAN_R §7, WS12): every ``readerbench/<tag>.py`` module -> ``dataset/items_rb.json`` (binary
facts, the ``items_r.json`` schema) and ``dataset/items_rbk.json`` (k-way facts, the ``items_rk.json`` schema), plus
``results/g_agreement/r/readerbench_bank.md`` (sizes, small-test flags, factor balance, optional J-lens coverage).

    python -m projects.g_agreement.r_bench.readerbench.build --check [--tags KHOP SYNTAX] [--samples 3]
    python -m projects.g_agreement.r_bench.readerbench.build --build [--seed 20261019]
    python -m projects.g_agreement.r_bench.readerbench.build --build --jlens-coverage   # needs the Qwen3.6 tokenizer in the HF cache

Collection: ``collect.py --items-file dataset/items_rb.json`` (binary) and ``--items-file dataset/items_rbk.json --kway``;
see results/g_agreement/r/HANDOFF.md for what the collector must honour (per-item candidates, system turns,
``capture_messages``, label_source "model").
"""

from __future__ import annotations

import argparse
import collections
import importlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.r_bench.readerbench import common as CM
from projects.g_agreement.r_bench.readerbench import tables as T

MODULES = ["khop", "syntax", "count", "knowledge", "computed", "surface", "topic", "form", "meta", "internal", "context"]
SUMMARY_MD = C.RESULTS_DIR / "r" / "readerbench_bank.md"


def load_modules(names: list[str] | None = None) -> list[Any]:
    mods = []
    for n in names or MODULES:
        try:
            mods.append(importlib.import_module(f"projects.g_agreement.r_bench.readerbench.{n}"))
        except ModuleNotFoundError as e:
            if e.name and e.name.endswith(n):
                continue   # module not written yet
            raise
    return mods


def all_facts(mods: list[Any] | None = None) -> list[CM.Fact]:
    facts = [f for m in (mods or load_modules()) for f in m.FACTS]
    ids = [f.id for f in facts]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate fact ids: " + ", ".join(i for i, c in collections.Counter(ids).items() if c > 1))
    return facts


def build_all(seed: int = CM.SEED, tags: list[str] | None = None, n_test: int = CM.N_TEST, n_pool: int = CM.N_POOL,
              mods: list[Any] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """(binary items, k-way items, per-fact info). Every module's facts are built, validated and split."""
    mods = mods or load_modules()
    problems = T.check_tables()
    if problems:
        raise SystemExit("table problems: " + "; ".join(problems))
    facts = {f.id: f for f in all_facts(mods)}
    items_b: list[dict[str, Any]] = []
    items_k: list[dict[str, Any]] = []
    info: dict[str, Any] = {}
    for m in mods:
        drafts_by = m.build(seed)
        for fid, drafts in drafts_by.items():
            fact = facts[fid]
            if fid not in facts:
                raise ValueError(f"{m.__name__} built {fid} which is not in FACTS")
            if tags and fact.tag not in tags:
                continue
            items, rep = CM.make_items(fact, drafts, seed, n_test, n_pool)
            (items_k if fact.sided == "kway" else items_b).append(items)
            info[fid] = {"tag": fact.tag, "sided": fact.sided, "per_item_candidates": fact.per_item_candidates,
                         "label_source": fact.label_source, **rep}
        built = set(drafts_by)
        missing = [f.id for f in m.FACTS if f.id not in built]
        if missing:
            raise ValueError(f"{m.__name__}: FACTS without drafts: {missing}")
    flat_b = [it for its in items_b for it in its]
    flat_k = [it for its in items_k for it in its]
    cross_checks(flat_b + flat_k, facts)
    # independent ground-truth round trip (solvers.py): every label re-derived from the item alone
    from projects.g_agreement.r_bench.readerbench import solvers as S
    rt = S.roundtrip(flat_b + flat_k)
    bad = {ds: r for ds, r in rt.items() if not r["ok"]}
    if bad:
        raise SystemExit("ground-truth round trip failed: " + json.dumps(bad, ensure_ascii=False)[:2000])
    for ds, r in rt.items():
        info[ds]["roundtrip"] = {"n": r["n"], "n_solved": r["n_solved"], "ok": r["ok"]}
    return flat_b, flat_k, info


def cross_checks(items: list[dict[str, Any]], facts: dict[str, CM.Fact]) -> None:
    """Bank-wide invariants: unique ids; a prompt shared by two facts only when they declare it; candidates of KHOP /
    KNOWLEDGE / per-item facts never in the text; k-way and binary files disjoint in prompts unless declared."""
    ids = [it["item_id"] for it in items]
    assert len(set(ids)) == len(ids), "duplicate item ids"
    by_prompt: dict[tuple, set[str]] = collections.defaultdict(set)
    for it in items:
        by_prompt[CM.prompt_key(it)].add(it["dataset"])
    for (text, _sys, _msgs), ds in by_prompt.items():
        if len(ds) > 1:
            for d in ds:
                others = ds - {d}
                assert others <= set(facts[d].shares_text_with), (f"prompt shared by {sorted(ds)} without shares_text_with", text[:80])
    for it in items:
        f = facts[it["dataset"]]
        if f.tag in ("KHOP", "KNOWLEDGE") or f.per_item_candidates and f.tag not in ("SYNTAX", "INTERNAL", "CONTEXT"):
            for c in it["primary"]["candidates"]:
                assert not CM.contains_word(it["prompt_text"], c), (it["item_id"], "candidate in text", c)


def write_bank(items_b: list[dict[str, Any]], items_k: list[dict[str, Any]], info: dict[str, Any], seed: int,
               out_b: Path = CM.ITEMS_RB, out_k: Path = CM.ITEMS_RBK, facts: list[CM.Fact] | None = None) -> None:
    facts = facts or all_facts()
    created = datetime.now(UTC).isoformat()
    for out, items, kind in ((out_b, items_b, "binary"), (out_k, items_k, "kway")):
        if out.exists():
            old = json.loads(out.read_text(encoding="utf-8"))
            if old.get("meta", {}).get("frozen"):
                raise SystemExit(f"refusing to overwrite frozen bank {out}")
        fids = sorted({it["dataset"] for it in items})
        meta = {"created": created, "bank": "readerbench", "kind": kind, "seed": seed, "n_test": CM.N_TEST, "n_pool": CM.N_POOL,
                "n_datasets": len(fids), "n_items": len(items), "taxonomy": dict(collections.Counter(info[f]["tag"] for f in fids)),
                "datasets": {f: info[f] for f in fids}, "spec": {f.id: f.to_json() for f in facts if f.id in fids},
                "per_item_candidate_datasets": [f for f in fids if info[f]["per_item_candidates"]],
                "model_labelled_datasets": [f for f in fids if info[f]["label_source"] == "model"],
                "sha256_items": CM.sha256_items(items), "frozen": False}
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"meta": meta, "items": items}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {out} ({len(items)} items, {len(fids)} facts, sha {meta['sha256_items'][:16]}...)")


# ------------------------------------------------------------------ J-lens single-token coverage (local tokenizer, optional)
def jlens_coverage(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per dataset: fraction of distinct J-lens forms that are a single token in the bare or leading-space spelling."""
    from transformers import AutoTokenizer  # local only

    tok = AutoTokenizer.from_pretrained(C.TARGET_MODEL_ID if hasattr(C, "TARGET_MODEL_ID") else "Qwen/Qwen3.6-27B")
    out: dict[str, dict[str, Any]] = {}
    forms: dict[str, set[str]] = collections.defaultdict(set)
    for it in items:
        for f in it["primary"]["jlens"]:
            if f:
                forms[it["dataset"]].add(f)
    for ds, fs in sorted(forms.items()):
        single = [f for f in fs if any(len(tok(v, add_special_tokens=False)["input_ids"]) == 1 for v in (f, " " + f))]
        out[ds] = {"n_forms": len(fs), "n_single": len(single), "multi": sorted(fs - set(single))[:6]}
    return out


def summary_md(info: dict[str, Any], cov: dict[str, dict[str, Any]] | None, seed: int) -> str:
    L = [f"# ReaderBench bank summary (seed {seed}, {datetime.now(UTC).date().isoformat()})", "",
         "Generated by `python -m projects.g_agreement.r_bench.readerbench.build --build`. Ground-truth rules per fact: "
         "`projects/g_agreement/r_bench/readerbench/README.md`.", "",
         "H-rules = test split >= 100 items (BRIEF_R §3 floor); facts below it are descriptive-only (reported with CIs, excluded from the H1-H7 verdicts).", "",
         "| fact | tag | sided | per-item cands | label | generated | test | pool | H-rules | balanced factors | J-lens single-token |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for fid, r in sorted(info.items(), key=lambda kv: (kv[1]["tag"], kv[0])):
        fac = "; ".join(f"{k}: {'/'.join(str(v) for v in sorted(c.values()))}" for k, c in r["factors_full"].items()) or "-"
        jl = f"{cov[fid]['n_single']}/{cov[fid]['n_forms']}" if cov and fid in cov else "n/a"
        L.append(f"| {fid} | {r['tag']} | {r['sided']} | {'yes' if r['per_item_candidates'] else ''} | {r['label_source']} | "
                 f"{r['n_generated']} | {r['n_test']} | {r['n_pool']} | {'descriptive-only' if r['small_test'] else 'yes'} | {fac} | {jl} |")
    tags = collections.Counter(r["tag"] for r in info.values())
    small = sorted(f for f, r in info.items() if r["small_test"])
    L += ["", "Descriptive-only facts (test < 100): " + (", ".join(small) if small else "none")]
    L += ["", "Facts per tag: " + ", ".join(f"{t} {n}" for t, n in sorted(tags.items())),
          f"Total: {len(info)} facts, {sum(r['n_items'] for r in info.values())} items "
          f"(test {sum(r['n_test'] for r in info.values())}, pool {sum(r['n_pool'] for r in info.values())}).", ""]
    if cov:
        multi = {d: c["multi"] for d, c in cov.items() if c["multi"]}
        L += ["Multi-token J-lens forms (first 6 per fact): " + json.dumps(multi, ensure_ascii=False), ""]
    return "\n".join(L)


def check(seed: int, tags: list[str] | None, samples: int) -> None:
    mods = load_modules()
    items_b, items_k, info = build_all(seed, tags, mods=mods)
    by_ds: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for it in items_b + items_k:
        by_ds[it["dataset"]].append(it)
    for fid, r in sorted(info.items(), key=lambda kv: (kv[1]["tag"], kv[0])):
        its = by_ds[fid]
        print(f"[{fid}] {r['tag']:9s} {r['sided']:4s} gen {r['n_generated']:4d} test {r['n_test']:3d} pool {r['n_pool']:3d}"
              f"{'  SMALL' if r['small_test'] else ''}{'  PER-ITEM' if r['per_item_candidates'] else ''}"
              f"{'  MODEL-LABELLED' if r['label_source'] == 'model' else ''}  factors {r['factors_full']}")
        p = its[0]["primary"]
        print(f"    Q: {p['question']}   template: {p['template']!r}" + ("" if r["per_item_candidates"] else f"   cands: {p['candidates']}"))
        rng = CM.rng_for(seed, fid + ":samples")
        for it in rng.sample([x for x in its if x["split"] == "test"], min(samples, len(its))):
            sys_ = f"  [system: {it['system'][:70]!r}]" if it.get("system") else ""
            print(f"    [{it['label']} -> {it['primary']['answer']!r} of {it['primary']['candidates'] if r['per_item_candidates'] else ''}]"
                  f" {it['prompt_text'][:120]!r}{sys_}")
    tags_c = collections.Counter(r["tag"] for r in info.values())
    print(f"\n{len(info)} facts ({dict(sorted(tags_c.items()))}); {len(items_b)} binary items, {len(items_k)} k-way items")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--tags", nargs="*", default=None)
    ap.add_argument("--samples", type=int, default=3)
    ap.add_argument("--seed", type=int, default=CM.SEED)
    ap.add_argument("--out", type=Path, default=CM.ITEMS_RB)
    ap.add_argument("--out-k", type=Path, default=CM.ITEMS_RBK)
    ap.add_argument("--jlens-coverage", action="store_true", help="tokenise the J-lens forms with the local Qwen3.6 tokenizer")
    a = ap.parse_args(argv)
    if a.check:
        check(a.seed, a.tags, a.samples)
    if a.build:
        items_b, items_k, info = build_all(a.seed, a.tags)
        write_bank(items_b, items_k, info, a.seed, a.out, a.out_k)
        cov = jlens_coverage(items_b + items_k) if a.jlens_coverage else None
        SUMMARY_MD.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY_MD.write_text(summary_md(info, cov, a.seed), encoding="utf-8")
        print(f"wrote {SUMMARY_MD}")
    if not (a.check or a.build):
        facts = all_facts()
        print(json.dumps({"n_facts": len(facts), "taxonomy": dict(collections.Counter(f.tag for f in facts))}, indent=1))


if __name__ == "__main__":
    main()
