"""Checkpoint tier of every reader in the Phase R tables (BRIEF_RP §0, §9).

standard  = released by the authors of a paper that introduces or evaluates that checkpoint on that exact target model,
            pinned by commit hash (Karvonen et al.'s AOs, Bauer et al.'s Qwen3-8B AO, Gemma Scope SAEs).
community = any other trained reader checkpoint (third-party ports, our own training).
none      = no trained reader checkpoint (probes, logit lens and its rotation control, prompt-only, target fine-tunes).

Assigned by rule before any panel result; never re-assigned after a result is seen.

    python -m projects.g_agreement.r_bench.checkpoint_tier --apply   # add the column to every committed Phase R CSV
    python -m projects.g_agreement.r_bench.checkpoint_tier --check   # list tables that lack it or have 'unknown'
                                                                     # (exit 1 only with --strict)

For table owners, one line before writing a Phase R CSV (adds the column; a no-op for tables it cannot classify):
    df = checkpoint_tier.annotate(df, out_path)
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

COL = "checkpoint_tier"
ROOT = Path(__file__).resolve().parents[3]
TABLE_DIRS = ("results/g_agreement/r", "results/g_agreement/rg", "results/g_agreement/rp")

# Reader key prefixes (after normalisation) → tier. Longest match wins.
TIERS: dict[str, str] = {
    # Qwen3.6-27B community readers (BRIEF_R §2.1)
    "jlens": "community", "olens": "community", "nla": "community", "skip": "community",
    # author-released activation oracles: Gemma-2-9B-it (BRIEF_RG), Qwen3-8B / Qwen3-32B / Bauer (BRIEF_RP)
    "ao": "standard", "q8_ao": "standard", "q32_ao": "standard", "q8b_ao": "standard", "q27_ao": "standard",
    # Gemma Scope SAE probes
    "sae": "standard",
    # no reader checkpoint
    "probe": "none", "lr": "none", "mm": "none", "mass_mean": "none", "logit_lens": "none", "llens": "none",
    "rotation_readout": "none", "rot": "none", "prompt_only": "none", "model_ft": "none",
}
# Rows that aggregate several readers ('all' quiver lines, hypothesis ids) take the tier of the trained readers of the
# table's directory: Phase R on Qwen3.6-27B is community, WS9 Gemma and the BRIEF_RP panel are standard.
AGGREGATE = re.compile(r"^(all|h\d.*|hp\d.*|bd_?8.*)$")
DIR_TIER = {"results/g_agreement/r": "community", "results/g_agreement/rg": "standard",
            "results/g_agreement/rp": "standard"}
# Tables with no reader column that concern one reader (or none) throughout: path suffix → reader key.
FILE_READER = {
    "r/text_arm.csv": "olens", "r/text_arm_ex_ws3_defects.csv": "olens",
    "r/label_audit.csv": "prompt_only", "r/planted_facts/prompt_only.csv": "prompt_only",
    "rg/followup_b.csv": "ao", "rg/followup_b_summary.csv": "ao", "rg/check_c_passage_truncation.csv": "ao",
    "rg/sae_fve.csv": "sae", "rg/with_label_defect/sae_fve.csv": "sae",
}
# Checkpoints behind the non-'none' keys (for the report header).
CHECKPOINTS: dict[str, str] = {
    "jlens": "neuronpedia/jacobian-lens (Qwen3.6-27B)",
    "olens": "agu18dec/olens_and_ar olens_s3d_rl600 (Qwen3.6-27B)",
    "nla": "ceselder/qwen3.6-27b-nla-rl iter 400 (Qwen3.6-27B)",
    "skip": "agreelens skip lenses (Qwen3.6-27B)",
    "ao": "adamkarvonen/checkpoints_latentqa_cls_past_lens_addition_gemma-2-9b-it @ 44b50560",
    "q8_ao": "adamkarvonen/checkpoints_latentqa_cls_past_lens_addition_Qwen3-8B @ 6e3c7e9d",
    "q32_ao": "adamkarvonen/checkpoints_cls_latentqa_past_lens_Qwen3-32B @ 08c733f3",
    "q8b_ao": "ceselder/qwen3-8b-ao-v3-best @ a7344ac8",
    "q27_ao": "adamkarvonen/checkpoints_latentqa_cls_past_lens_addition_Qwen3.6-27B @ 891bef83",
    "sae": "google/gemma-scope-9b-{pt,it}-res",
}
# Columns whose row values name a reader, in priority order.
READER_COLS = ("reader", "method", "probe", "form", "line", "column", "readers", "hypothesis")


def _norm(name: str) -> str:
    s = str(name).strip().lower()
    s = re.sub(r"[@\[].*$", "", s)            # 'olens@44', 'AO@21 chat' → site dropped
    s = re.sub(r"[\s\-:]+", "_", s).strip("_")  # 'AO-yn', 'logit lens', 'sae:sae16:k16'
    return s


def combine(tiers: set[str]) -> str:
    """Tier of a set of readers: the trained readers' tier; 'none' if there are none; 'mixed' if they differ."""
    trained = tiers - {"none"}
    if "unknown" in trained:
        return "unknown"
    return "none" if not trained else trained.pop() if len(trained) == 1 else "mixed"


def tier(name: str, dir_tier: str | None = None) -> str:
    """Tier of one reader key; 'unknown' if no prefix matches."""
    raw = str(name).strip()
    if raw.startswith("["):                       # agreement.csv 'readers' lists
        return combine({tier(p) for p in re.findall(r"'([^']+)'", raw)})
    s = _norm(raw)
    if AGGREGATE.match(s):
        return dir_tier or "unknown"
    for key in sorted(TIERS, key=len, reverse=True):
        if s == key or s.startswith(key + "_") or s.startswith(key):
            return TIERS[key]
    return "unknown"


def reader_col(df: pd.DataFrame) -> str | None:
    return next((c for c in READER_COLS if c in df.columns), None)


def dir_tier_of(path: Path | str) -> str | None:
    rel = str(Path(path).resolve().relative_to(ROOT)) if Path(path).is_absolute() else str(path)
    return next((t for d, t in DIR_TIER.items() if rel.startswith(d + "/")), None)


def file_reader(path: Path | str) -> str | None:
    rel = str(path).replace("\\", "/")
    return next((k for suf, k in FILE_READER.items() if rel.endswith("results/g_agreement/" + suf)), None)


def annotate(df: pd.DataFrame, path: Path | str | None = None) -> pd.DataFrame:
    """Return df with a checkpoint_tier column: from its reader column, else from the file's single reader
    (FILE_READER); unchanged if neither applies. `path` gives aggregate rows their directory's tier."""
    dt = dir_tier_of(path) if path is not None else None
    out = df.drop(columns=[COL], errors="ignore").copy()
    c = reader_col(out)
    if c is not None:
        out[COL] = out[c].map(lambda v: tier(v, dt))
        return out
    k = file_reader(path) if path is not None else None
    if k is None:
        if path is not None and "results/g_agreement/rp/" in str(path).replace("\\", "/"):
            out[COL] = dt   # BRIEF_RP tables without a reader column concern the pair's standard oracle throughout
            return out
        return df
    out[COL] = tier(k, dt)
    return out


WIDE_FIRST_COL = "dataset"


def is_wide(df: pd.DataFrame) -> bool:
    """Readers as columns: no reader column, first column 'dataset', and ≥ 2 reader-named columns."""
    if reader_col(df) is not None or df.columns[0] != WIDE_FIRST_COL:
        return False
    return sum(tier(c) != "unknown" for c in df.columns[1:]) >= 2


def wide_tiers(df: pd.DataFrame) -> pd.DataFrame:
    rows = [(c, tier(c)) for c in df.columns[1:] if c not in ("tag", "gap")]
    return pd.DataFrame(rows, columns=["column", COL])


def write_with_column(path: Path, values: list[str]) -> None:
    """Append (or replace) the checkpoint_tier column textually, so every existing field keeps its exact text."""
    rows = list(csv.reader(io.StringIO(path.read_text())))
    head, body = rows[0], [r for r in rows[1:] if r]
    if COL in head:
        i = head.index(COL)
        head = head[:i] + head[i + 1:]
        body = [r[:i] + r[i + 1:] for r in body]
    assert len(body) == len(values), (path, len(body), len(values))
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(head + [COL])
    w.writerows(r + [v] for r, v in zip(body, values))
    path.write_text(buf.getvalue())


def tables(paths: tuple[str, ...] = TABLE_DIRS) -> list[Path]:
    """Committed CSVs under ``paths`` plus untracked ones under them (a stream's fresh outputs), never another stream's dir
    unless named."""
    out = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", *paths], cwd=ROOT, text=True).split()
    return [ROOT / f for f in out if f.endswith(".csv") and not f.endswith(".tiers.csv")]


def apply(check_only: bool = False, paths: tuple[str, ...] = TABLE_DIRS) -> list[str]:
    problems: list[str] = []
    for p in tables(paths):
        if p.stat().st_size <= 1 or "/pod_" in str(p):   # empty placeholders; pods' raw pulls (pod_<id>/) are not tables
            continue
        df = pd.read_csv(p)
        rel = p.relative_to(ROOT)
        own_rp = "results/g_agreement/rp/" in str(p).replace("\\", "/")
        if reader_col(df) is not None or file_reader(p) is not None or own_rp:
            new = annotate(df, p)
            c = reader_col(df) or COL
            bad = sorted(set(new.loc[new[COL] == "unknown", c].astype(str)))
            if bad:
                problems.append(f"{rel}: unknown reader keys {bad}")
            if check_only:
                if COL not in df.columns or not df[COL].equals(new[COL]):
                    problems.append(f"{rel}: {COL} missing or stale")
            else:
                write_with_column(p, new[COL].tolist())
        elif is_wide(df):
            side = p.with_suffix(".tiers.csv")
            t = wide_tiers(df)
            bad = sorted(t.loc[t[COL] == "unknown", "column"])
            if bad:
                problems.append(f"{rel}: unknown reader columns {bad}")
            if check_only:
                if not side.exists() or not pd.read_csv(side).equals(t):
                    problems.append(f"{side.relative_to(ROOT)}: missing or stale")
            else:
                t.to_csv(side, index=False)
        else:
            problems.append(f"{rel}: no reader column, not wide, not in FILE_READER")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--apply", action="store_true")
    g.add_argument("--check", action="store_true")
    ap.add_argument("--strict", action="store_true", help="with --check: exit 1 if any table needs attention")
    ap.add_argument("--paths", nargs="*", default=list(TABLE_DIRS), help="limit to these results dirs (a stream applies to its own only)")
    a = ap.parse_args(argv)
    problems = apply(check_only=a.check, paths=tuple(a.paths))
    for line in problems:
        print(line)
    return 1 if a.strict and problems else 0


if __name__ == "__main__":
    sys.exit(main())
