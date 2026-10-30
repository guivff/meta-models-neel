"""R-A / R-B bank builder (BRIEF_R.md §3): the SAE-probing CSVs (``prompt,target``) -> ``dataset/items_r.json``
(binary facts) and ``dataset/items_rk.json`` (multiclass parents), balanced, seeded, with the spec attached to
every item so the collectors and the analysis never look the spec up by hand.

    python -m projects.g_agreement.r_bench.bank --csv-dir cache/g_agreement/r/cleaned_data --check
        prints, per dataset: rows, target values, how many rows the spec's positive mapping covers, three sample
        prompts and the candidates — read this BEFORE the freeze and fix r_bench/datasets.py where it is wrong
    python -m projects.g_agreement.r_bench.bank --csv-dir cache/g_agreement/r/cleaned_data --build
        writes dataset/items_r.json and dataset/items_rk.json (seed 20261019, test 200, pool 512 per fact)
    python -m projects.g_agreement.r_bench.bank --summary
        writes results/g_agreement/r/bank_summary.md from the built bank: per-dataset sizes, small-test and
        short-pool flags, drops, J-lens single-token coverage under the Qwen3.6 tokenizer (local HF cache), k-way
        parents, the parent round trip; a hand-written block between <!-- notes --> markers is preserved
    python -m projects.g_agreement.r_bench.bank --roundtrip
        joins every binarised child (datasets.BINARISED_FROM) with its parent CSV on the text and checks that
        target 1 <=> parent class == the named class; exits non-zero if any child disagrees

Item schema (INTERFACES §1 compatible; one item is rendered twice at collect time, chat and raw):
  item_id "r-<dataset>-<split>-<k>", dataset, tag, split in {test, pool}, label 1/0 (pos true), raw_target,
  prompt_text (= the text), render "chat", system None,
  primary {name: dataset, question, candidates [pos, neg], answer, template, sided, jlens [pos, neg]}
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from projects.g_agreement.core import config as C
from projects.g_agreement.r_bench import datasets as D

ITEMS_R = C.DATASET_DIR / "items_r.json"
ITEMS_RK = C.DATASET_DIR / "items_rk.json"
SUMMARY_MD = C.RESULTS_DIR / "r" / "bank_summary.md"
DEFAULT_CSV_DIR = C.CACHE_DIR / "r" / "cleaned_data"
SEED = 20261019
N_TEST = 200
N_POOL = 512
MIN_TEST = 100   # the paper's floor; smaller test splits are flagged, not dropped
MAX_CHARS = 2000  # texts longer than this are cut (bigram facts exempt: the phrase sits at the end)

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


# ------------------------------------------------------------------ reading
def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8", errors="replace") as fh:
        rows = list(csv.DictReader(fh))
    if not rows or "prompt" not in rows[0] or "target" not in rows[0]:
        raise ValueError(f"{path}: expected columns prompt,target; got {list(rows[0].keys()) if rows else 'empty'}")
    return rows


def _clean_text(t: str, max_chars: int | None) -> str | None:
    t = (t or "").replace("\r\n", "\n").strip()
    if not t:
        return None
    if max_chars and len(t) > max_chars:
        t = t[:max_chars].rstrip()
    return t


def labelled_rows(spec: D.FactSpec, rows: list[dict[str, str]], max_chars: int | None = MAX_CHARS
                  ) -> tuple[list[tuple[str, int, str]], Counter, int, dict[str, int]]:
    """(text, label, raw_target) for every row the spec maps, one row per distinct text; target counts; number of
    unmapped rows; drops {"duplicate": repeated texts, "conflict": texts that occur with both labels (all copies
    dropped)}. The raw CSVs oversample the minority class with replacement (e.g. 6_hist_fig_isamerican: 2,500
    positive rows, 825 distinct names), so the distinct-text counts are the real sizes."""
    cap = None if spec.tag == "SURFACE" and spec.id.split("_", 1)[1] in BIGRAM_SLUGS else max_chars
    out: list[tuple[str, int, str]] = []
    counts: Counter = Counter(r["target"] for r in rows)
    # two-valued inference: when the column has exactly two values and the spec maps one of them to the positive
    # class, the other one is the negative class (recorded in the item's raw_target either way)
    inferred_neg: str | None = None
    if len(counts) == 2:
        vals = list(counts)
        flags = [spec.is_positive(_coerce(v)) for v in vals]
        if flags.count(True) == 1 and None in flags:
            inferred_neg = vals[flags.index(None)]
    unmapped = 0
    first: dict[str, tuple[str, int, str]] = {}
    labels_of: dict[str, set[int]] = {}
    n_rows: Counter = Counter()
    for r in rows:
        raw = r["target"]
        lab = spec.is_positive(_coerce(raw))
        if lab is None and inferred_neg is not None and raw == inferred_neg:
            lab = False
        text = _clean_text(r["prompt"], cap)
        if lab is None:
            unmapped += 1
            continue
        if text is None:
            continue
        n_rows[text] += 1
        first.setdefault(text, (text, int(lab), raw))
        labels_of.setdefault(text, set()).add(int(lab))
    conflict = {t for t, labs in labels_of.items() if len(labs) > 1}
    for t in conflict:
        del first[t]
    # duplicate = repeated rows of a kept text; conflict = texts seen with both labels (every copy dropped)
    drops = {"duplicate": sum(n - 1 for t, n in n_rows.items() if t not in conflict), "conflict": len(conflict)}
    return list(first.values()), counts, unmapped, drops


def _coerce(raw: str) -> Any:
    """CSV cells are strings; '1', '1.0', 'True' should hit the numeric/bool members of the positive sets too."""
    s = raw.strip()
    for conv in (int, float):
        try:
            v = conv(s)
            if conv is float and not v.is_integer():
                return s
            return int(v)
        except ValueError:
            pass
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    return s


BIGRAM_SLUGS = {s.id.split("_", 1)[1] for s in D.specs() if s.note.startswith("Gurnee-style bigram")}


# ------------------------------------------------------------------ splitting
def balanced_split(labelled: list[tuple[str, int, str]], n_test: int, n_pool: int, seed: int
                   ) -> tuple[list[int], list[int], dict[str, Any]]:
    """Index lists (into ``labelled``) for a balanced test split and a balanced pool, disjoint. Shrinks to the
    minority class when a class is short, keeping balance; the pool takes what is left up to n_pool/2 per class."""
    rng = np.random.default_rng(seed)
    pos = [i for i, (_, y, _) in enumerate(labelled) if y == 1]
    neg = [i for i, (_, y, _) in enumerate(labelled) if y == 0]
    rng.shuffle(pos)
    rng.shuffle(neg)
    avail = min(len(pos), len(neg))
    # short datasets: split the minority class half/half between test and pool so probes still get training data
    per_test = n_test // 2 if avail >= n_test // 2 + 64 else avail // 2
    test = pos[:per_test] + neg[:per_test]
    rest_pos, rest_neg = pos[per_test:], neg[per_test:]
    per_pool = min(n_pool // 2, len(rest_pos), len(rest_neg))
    pool = rest_pos[:per_pool] + rest_neg[:per_pool]
    test_idx = [int(i) for i in rng.permutation(test)]
    pool_idx = [int(i) for i in rng.permutation(pool)]
    info = {"n_pos": len(pos), "n_neg": len(neg), "n_test": len(test_idx), "n_pool": len(pool_idx),
            "small_test": len(test_idx) < MIN_TEST, "pool_short": len(pool_idx) < n_pool}
    return test_idx, pool_idx, info


def make_items(spec: D.FactSpec, labelled: list[tuple[str, int, str]], test_idx: list[int], pool_idx: list[int]
               ) -> list[dict[str, Any]]:
    items = []
    for split, idx in (("test", test_idx), ("pool", pool_idx)):
        for k, i in enumerate(idx):
            text, y, raw = labelled[i]
            items.append({
                "item_id": f"r-{spec.id}-{split}-{k:04d}",
                "dataset": spec.id, "tag": spec.tag, "split": split, "label": y, "raw_target": raw,
                "prompt_text": text, "render": "chat", "system": None,
                "primary": {"name": spec.id, "question": spec.question, "candidates": [spec.pos, spec.neg],
                            "answer": spec.pos if y == 1 else spec.neg, "template": spec.template,
                            "sided": spec.sided, "jlens": [spec.jlens_pos, spec.jlens_neg]},
            })
    return items


# ------------------------------------------------------------------ multiclass (R-B)
def multiclass_items(m: D.MulticlassSpec, rows: list[dict[str, str]], n_per_class_test: int = 25,
                     n_per_class_pool: int = 64, seed: int = SEED, max_chars: int | None = MAX_CHARS
                     ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rng = np.random.default_rng(seed + m.num)
    by_class: dict[str, list[str]] = {}
    seen: set[str] = set()
    for r in rows:
        text = _clean_text(r["prompt"], max_chars)
        if text is None or text in seen:
            continue
        seen.add(text)
        by_class.setdefault(str(r["target"]).strip(), []).append(text)
    classes = [c for c, _ in Counter({c: len(v) for c, v in by_class.items()}).most_common(m.k_max)]
    classes = [c for c in classes if len(by_class[c]) >= n_per_class_test + 8]
    cands = [m.candidate(c) for c in classes]
    items = []
    for ci, c in enumerate(classes):
        texts = list(by_class[c])
        rng.shuffle(texts)
        for split, chunk in (("test", texts[:n_per_class_test]),
                             ("pool", texts[n_per_class_test:n_per_class_test + n_per_class_pool])):
            for k, text in enumerate(chunk):
                items.append({
                    "item_id": f"rk-{m.id}-{split}-{ci}-{k:04d}",
                    "dataset": m.id, "tag": m.tag, "split": split, "label": ci, "raw_target": c,
                    "prompt_text": text, "render": "chat", "system": None,
                    "primary": {"name": m.id, "question": m.question, "candidates": cands, "answer": cands[ci],
                                "template": m.template, "sided": "kway", "k": len(cands)},
                })
    info = {"k": len(cands), "classes": dict(zip(classes, cands)),
            "n_per_class": {c: len(by_class[c]) for c in classes}, "dropped_classes": [c for c in by_class if c not in classes]}
    return items, info


# ------------------------------------------------------------------ parent round trip
def parent_roundtrip(csv_dir: Path) -> dict[str, dict[str, Any]]:
    """For every child in ``datasets.BINARISED_FROM``: P(target == 1 | parent class == named class) and
    P(target == 1 | parent class != named class), joined on the stripped prompt text. Both must be 1.00 / 0.00."""
    parents: dict[str, dict[str, set[str]]] = {}
    out: dict[str, dict[str, Any]] = {}
    for child, (parent, cls) in D.BINARISED_FROM.items():
        if parent not in parents:
            pp = find_csv(csv_dir, parent + ".csv")
            pm: dict[str, set[str]] = {}
            if pp is not None:
                for r in read_csv_rows(pp):
                    pm.setdefault(r["prompt"].strip(), set()).add(r["target"].strip())
            parents[parent] = pm
        pm = parents[parent]
        cp = find_csv(csv_dir, child + ".csv")
        if cp is None or not pm:
            out[child] = {"status": "missing", "parent": parent}
            continue
        hit = Counter(); miss = Counter(); joined = 0
        for r in read_csv_rows(cp):
            pc = pm.get(r["prompt"].strip())
            if pc is None or len(pc) != 1:
                continue
            joined += 1
            (hit if next(iter(pc)) == cls else miss)[r["target"].strip()] += 1
        p1 = hit["1"] / max(1, sum(hit.values()))
        p0 = miss["1"] / max(1, sum(miss.values()))
        out[child] = {"status": "ok" if (p1 == 1.0 and p0 == 0.0 and joined) else "MISMATCH", "parent": parent,
                      "class": cls, "joined": joined, "p1_given_class": round(p1, 3), "p1_given_other": round(p0, 3),
                      "n_class": sum(hit.values()), "n_other": sum(miss.values())}
    return out


# ------------------------------------------------------------------ --check / --build
def find_csv(csv_dir: Path, file: str) -> Path | None:
    p = csv_dir / file
    if p.exists():
        return p
    hits = list(csv_dir.rglob(file))
    return hits[0] if hits else None


def check(csv_dir: Path, ids: list[str] | None = None, samples: int = 3) -> dict[str, Any]:
    report: dict[str, Any] = {"csv_dir": str(csv_dir), "missing": [], "unmapped": {}, "datasets": {}}
    for spec in D.specs(ids=ids):
        p = find_csv(csv_dir, spec.file)
        if p is None:
            report["missing"].append(spec.id)
            print(f"[{spec.id}] MISSING {spec.file}")
            continue
        rows = read_csv_rows(p)
        labelled, counts, unmapped, drops = labelled_rows(spec, rows)
        n_pos = sum(y for _, y, _ in labelled)
        line = (f"[{spec.id}] {spec.tag:9s} rows {len(rows):5d}  targets {dict(counts.most_common(6))}  "
                f"distinct mapped {len(labelled)} (pos {n_pos}, neg {len(labelled) - n_pos}), unmapped {unmapped}, "
                f"dropped dup {drops['duplicate']} conflict {drops['conflict']}"
                f"{'  VERIFY' if spec.verify else ''}")
        print(line)
        print(f"    Q: {spec.question}   pos: {spec.pos!r}   neg: {spec.neg!r}   template: {spec.template!r}   "
              f"jlens: {spec.jlens_pos!r} / {spec.jlens_neg!r}   sided: {spec.sided}")
        # ``samples`` examples of each class, in file order, so the mapping can be read off both sides
        for cls in (1, 0):
            shown = 0
            for text, y, raw in labelled:
                if y != cls or shown >= samples:
                    continue
                print(f"    [{raw} -> {'pos' if y else 'neg'}] {text[:110]!r}")
                shown += 1
        if unmapped:
            report["unmapped"][spec.id] = {"unmapped": unmapped, "targets": dict(counts)}
        report["datasets"][spec.id] = {"rows": len(rows), "mapped": len(labelled), "pos": n_pos, "unmapped": unmapped,
                                       **drops}
    for m in D.MULTICLASS.values():
        p = find_csv(csv_dir, m.file)
        if p is None:
            report["missing"].append(m.id)
            print(f"[{m.id}] MISSING {m.file}")
            continue
        rows = read_csv_rows(p)
        counts = Counter(str(r["target"]).strip() for r in rows)
        print(f"[{m.id}] k-way {m.tag:9s} rows {len(rows):5d}  classes {len(counts)}  top {dict(counts.most_common(m.k_max))}")
        print(f"    candidates: {[m.candidate(c) for c, _ in counts.most_common(m.k_max)]}")
    print(f"\nmissing: {len(report['missing'])}   datasets with unmapped targets: {len(report['unmapped'])}")
    return report


def build(csv_dir: Path, out_r: Path = ITEMS_R, out_rk: Path = ITEMS_RK, n_test: int = N_TEST, n_pool: int = N_POOL,
          seed: int = SEED, ids: list[str] | None = None, max_chars: int | None = MAX_CHARS) -> tuple[Path, Path]:
    items: list[dict[str, Any]] = []
    per: dict[str, Any] = {}
    missing: list[str] = []
    for spec in D.specs(ids=ids):
        p = find_csv(csv_dir, spec.file)
        if p is None:
            missing.append(spec.id)
            continue
        labelled, counts, unmapped, drops = labelled_rows(spec, read_csv_rows(p), max_chars)
        if unmapped and unmapped > 0.05 * (len(labelled) + unmapped):
            raise SystemExit(f"{spec.id}: {unmapped} rows have targets the spec does not map {dict(counts)}; fix datasets.py")
        test_idx, pool_idx, info = balanced_split(labelled, n_test, n_pool, seed + spec.num)
        if not test_idx:
            missing.append(spec.id)
            continue
        items += make_items(spec, labelled, test_idx, pool_idx)
        per[spec.id] = {**info, **{f"dropped_{k}": v for k, v in drops.items()}, "n_rows_csv": len(labelled) + unmapped
                        + sum(drops.values()), "tag": spec.tag, "sided": spec.sided, "verify": spec.verify,
                        "csv": str(p), "csv_sha256": C.sha256_file(p)}
    meta = {"created": datetime.now(UTC).isoformat(), "seed": seed, "n_test": n_test, "n_pool": n_pool,
            "max_chars": max_chars, "n_datasets": len(per), "n_items": len(items), "missing": missing,
            "taxonomy": Counter(v["tag"] for v in per.values()), "datasets": per,
            "spec": {s.id: s.to_json() for s in D.specs(ids=list(per))},
            "prompt_only_fc_template": D.PROMPT_ONLY_FC_TEMPLATE, "frozen": False}
    meta["sha256_items"] = hashlib.sha256(json.dumps(items, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    out_r.parent.mkdir(parents=True, exist_ok=True)
    out_r.write_text(json.dumps({"meta": meta, "items": items}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    kitems: list[dict[str, Any]] = []
    kper: dict[str, Any] = {}
    for m in D.MULTICLASS.values():
        p = find_csv(csv_dir, m.file)
        if p is None:
            missing.append(m.id)
            continue
        its, info = multiclass_items(m, read_csv_rows(p), seed=seed, max_chars=max_chars)
        kitems += its
        kper[m.id] = {**info, "tag": m.tag, "csv": str(p)}
    kmeta = {"created": meta["created"], "seed": seed, "n_datasets": len(kper), "n_items": len(kitems),
             "datasets": kper, "prompt_only_kway_template": D.PROMPT_ONLY_KWAY_TEMPLATE, "frozen": False}
    out_rk.write_text(json.dumps({"meta": kmeta, "items": kitems}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {out_r} ({len(items)} items, {len(per)} facts; missing {missing}) and {out_rk} ({len(kitems)} items)")
    return out_r, out_rk


# ------------------------------------------------------------------ --summary
def _jlens_variants(tok: Any, word: str) -> list[str]:
    """Mirror of core.scoring_lo.token_variants (kept out of that import so this stays torch-free): the forms
    X, " X", capitalised, lower (bare and with a leading space) that encode to exactly one token."""
    forms: list[str] = []
    for w in (word, word.capitalize(), word.lower(), word.upper() if len(word) == 1 else word):
        for f in (w, " " + w):
            if f not in forms:
                forms.append(f)
    return [f for f in forms if len(tok.encode(f, add_special_tokens=False)) == 1]


def _load_tokenizer() -> Any | None:
    try:
        from transformers import AutoTokenizer  # heavy import; local cache only, never downloads
        return AutoTokenizer.from_pretrained(C.TARGET_MODEL_ID, local_files_only=True)
    except Exception as e:  # noqa: BLE001
        print(f"tokenizer unavailable ({type(e).__name__}: {e}); J-lens coverage column left blank")
        return None


def write_summary(items_r: Path = ITEMS_R, items_rk: Path = ITEMS_RK, out: Path = SUMMARY_MD,
                  csv_dir: Path | None = DEFAULT_CSV_DIR) -> Path:
    d = json.loads(Path(items_r).read_text(encoding="utf-8"))
    k = json.loads(Path(items_rk).read_text(encoding="utf-8"))
    meta, kmeta = d["meta"], k["meta"]
    tok = _load_tokenizer()
    notes = ""
    if out.exists():
        old = out.read_text(encoding="utf-8")
        if "<!-- notes -->" in old and "<!-- /notes -->" in old:
            notes = old.split("<!-- notes -->", 1)[1].split("<!-- /notes -->", 1)[0]
    L: list[str] = []
    L.append("# Phase R bank summary (R-A binary facts, R-B k-way parents)\n")
    L.append(f"Generated by `python -m projects.g_agreement.r_bench.bank --summary` from `{Path(items_r).name}` "
             f"(created {meta['created'][:19]}Z, seed {meta['seed']}, items sha256 `{meta['sha256_items']}`, "
             f"frozen={meta['frozen']}) and `{Path(items_rk).name}`. Tokenizer: "
             f"{C.TARGET_MODEL_ID if tok is not None else 'not loaded'}.\n")
    L.append("<!-- notes -->" + (notes or "\n(hand-written notes go here; preserved across regeneration)\n") + "<!-- /notes -->\n")
    per = meta["datasets"]
    spec = {sid: D.SPECS[sid] for sid in per}
    n_small = sum(v["small_test"] for v in per.values())
    n_pool_short = sum(v["pool_short"] for v in per.values())
    n_items_test = sum(v["n_test"] for v in per.values())
    n_items_pool = sum(v["n_pool"] for v in per.values())
    cov_pos = cov_neg = cov_both = 0
    cov_rows: dict[str, tuple[list[str], list[str]]] = {}
    if tok is not None:
        for sid, s in spec.items():
            vp, vn = _jlens_variants(tok, s.jlens_pos), _jlens_variants(tok, s.jlens_neg)
            cov_rows[sid] = (vp, vn)
            cov_pos += bool(vp)
            cov_neg += bool(vn)
            cov_both += bool(vp and vn)
    L.append("## Totals\n")
    L.append("| quantity | value |\n|---|---|")
    L.append(f"| binary facts | {len(per)} |")
    L.append(f"| items (test + pool) | {meta['n_items']} ({n_items_test} + {n_items_pool}) |")
    L.append(f"| facts with the full {meta['n_test']}-item test split | {sum(v['n_test'] == meta['n_test'] for v in per.values())} |")
    L.append(f"| facts with a small test split (< {MIN_TEST}) | {n_small} |")
    L.append(f"| facts with a short pool (< {meta['n_pool']}) | {n_pool_short} |")
    L.append(f"| one-sided / two-sided | {sum(v['sided'] == 'one' for v in per.values())} / {sum(v['sided'] == 'two' for v in per.values())} |")
    L.append(f"| rows dropped as duplicate texts (all facts) | {sum(v['dropped_duplicate'] for v in per.values())} |")
    L.append(f"| texts dropped for conflicting labels | {sum(v['dropped_conflict'] for v in per.values())} |")
    if tok is not None:
        L.append(f"| J-lens: facts whose pos form is one token | {cov_pos} / {len(per)} |")
        L.append(f"| J-lens: facts whose neg form is one token | {cov_neg} / {len(per)} |")
        L.append(f"| J-lens: facts scorable (both forms one token) | {cov_both} / {len(per)} |")
    L.append(f"| k-way parents / items | {kmeta['n_datasets']} / {kmeta['n_items']} |")
    L.append("")
    L.append("| tag | facts | items | small test | short pool |\n|---|---|---|---|---|")
    for tag in D.TAGS:
        vs = [v for v in per.values() if v["tag"] == tag]
        if vs:
            L.append(f"| {tag} | {len(vs)} | {sum(v['n_test'] + v['n_pool'] for v in vs)} | "
                     f"{sum(v['small_test'] for v in vs)} | {sum(v['pool_short'] for v in vs)} |")
    L.append("")
    L.append("## Per-dataset sizes\n")
    L.append("Distinct = distinct texts after dropping duplicates and conflicting-label texts (the raw CSVs oversample "
             "the minority class with replacement). Flags: S = small test split, P = short pool. J-lens column: number "
             "of single-token variants found for the pos / neg short form (`-` = none, the pair is unscorable).\n")
    L.append("| id | tag | sided | distinct pos / neg | test | pool | flags | dup / conflict | candidates (pos / neg) | J-lens forms |\n|---|---|---|---|---|---|---|---|---|---|")
    for sid, v in sorted(per.items(), key=lambda kv: D.SPECS[kv[0]].num):
        s = spec[sid]
        flags = ("S" if v["small_test"] else "") + ("P" if v["pool_short"] else "")
        if tok is not None:
            vp, vn = cov_rows[sid]
            jl = f"`{s.jlens_pos}` {len(vp) or '-'} / `{s.jlens_neg}` {len(vn) or '-'}"
        else:
            jl = f"`{s.jlens_pos}` / `{s.jlens_neg}`"
        L.append(f"| {sid} | {v['tag']} | {v['sided']} | {v['n_pos']} / {v['n_neg']} | {v['n_test']} | {v['n_pool']} | "
                 f"{flags or '·'} | {v['dropped_duplicate']} / {v['dropped_conflict']} | {s.pos} / {s.neg} | {jl} |")
    L.append("")
    if tok is not None:
        bad = [(sid, s.jlens_pos, s.jlens_neg) for sid, s in spec.items() if not (cov_rows[sid][0] and cov_rows[sid][1])]
        L.append("## J-lens single-token coverage\n")
        if bad:
            L.append("Facts whose declared short form has no single-token variant (unscorable for the J-lens):\n")
            L += [f"- {sid}: `{p}` / `{n}`" for sid, p, n in bad]
        else:
            L.append(f"Every one of the {len(per)} facts has a single-token variant for both declared short forms, so the "
                     "J-lens scores every fact. The variants tried are the four spellings of `core.scoring_lo.token_variants` "
                     "(bare / leading space x as written / capitalised / lower).")
        L.append("")
    L.append("## k-way parents (R-B)\n")
    L.append("| id | tag | k | classes -> candidates | test items | pool items |\n|---|---|---|---|---|---|")
    kitems = k["items"]
    for kid, v in sorted(kmeta["datasets"].items(), key=lambda kv: D.MULTICLASS[kv[0]].num):
        its = [it for it in kitems if it["dataset"] == kid]
        nt = sum(it["split"] == "test" for it in its)
        cls = "; ".join(f"{a} -> {b}" if a != b else a for a, b in v["classes"].items())
        L.append(f"| {kid} | {v['tag']} | {v['k']} | {cls} | {nt} | {len(its) - nt} |")
    L.append("")
    if csv_dir is not None and Path(csv_dir).exists():
        rt = parent_roundtrip(Path(csv_dir))
        ok = sum(v["status"] == "ok" for v in rt.values())
        L.append("## Parent round trip (binarised children 114-156 and 129)\n")
        L.append(f"{ok} / {len(rt)} children agree with their parent on every joined text "
                 f"(P(target 1 | parent class = named class) = 1.00 and P(target 1 | other class) = 0.00).")
        L += [f"- {kk}: {vv}" for kk, vv in rt.items() if vv["status"] != "ok"]
        L.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {out}")
    return out


def load_items(path: Path = ITEMS_R, split: str = "all", datasets: list[str] | None = None) -> list[dict[str, Any]]:
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    items = d["items"]
    if split != "all":
        items = [it for it in items if it["split"] == split]
    if datasets:
        items = [it for it in items if it["dataset"] in datasets]
    return items


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv-dir", type=Path, default=DEFAULT_CSV_DIR)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--roundtrip", action="store_true", help="verify the binarised children against their parents")
    ap.add_argument("--summary", action="store_true", help="write results/g_agreement/r/bank_summary.md from the built bank")
    ap.add_argument("--ids", nargs="*", default=None, help="restrict to these dataset ids")
    ap.add_argument("--n-test", type=int, default=N_TEST)
    ap.add_argument("--n-pool", type=int, default=N_POOL)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", type=Path, default=ITEMS_R)
    ap.add_argument("--out-k", type=Path, default=ITEMS_RK)
    a = ap.parse_args(argv)
    problems = D.spec_check()
    if problems:
        raise SystemExit("spec problems: " + "; ".join(problems))
    if a.check:
        check(a.csv_dir, a.ids)
    if a.roundtrip:
        rt = parent_roundtrip(a.csv_dir)
        for k, v in rt.items():
            print(f"[{k}] {v}")
        bad = [k for k, v in rt.items() if v["status"] != "ok"]
        print(f"round trip: {len(rt) - len(bad)} ok, {len(bad)} not ok {bad}")
        if bad:
            raise SystemExit(1)
    if a.build:
        build(a.csv_dir, a.out, a.out_k, a.n_test, a.n_pool, a.seed, a.ids)
    if a.summary:
        write_summary(a.out, a.out_k, csv_dir=a.csv_dir)
    if not (a.check or a.build or a.roundtrip or a.summary):
        print(json.dumps({"n_binary": len(D.SPECS), "n_multiclass": len(D.MULTICLASS), "taxonomy": D.taxonomy_counts()}, indent=1))


if __name__ == "__main__":
    main()
