"""Remainder R2: CPU-only availability audit; no GPU/API imports or inference on missing taps."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import subprocess

BANKS = {"R-A": "items_r.json", "R-E": "items_re.json", "ReaderBench": "items_rb.json"}
READERS = ("olens", "nla")
TAPS = (20, 32, 40)
TAP_DIRS = {"reader_states", "oracle_states", "nla_states"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def defects_from_source(path: Path) -> set[str]:
    """Read the authoritative exclusion constant without importing analysis code."""
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "LABEL_DEFECT" for t in node.targets):
            return set(ast.literal_eval(node.value))
    raise ValueError("LABEL_DEFECT constant missing")


def bank_inventory(bank_root: Path, defects: set[str]) -> dict:
    out = {}
    for name, filename in BANKS.items():
        path = bank_root / filename
        if not path.exists():
            raise FileNotFoundError(f"missing bank; absence cannot establish absent taps: {path}")
        blob = json.loads(path.read_text())
        items = blob["items"] if isinstance(blob, dict) else blob
        kept = [r for r in items if r["dataset"] not in defects]
        out[name] = {"file": str(path), "sha256": sha(path),
                     "facts": sorted({r["dataset"] for r in kept}),
                     "excluded": sorted({r["dataset"] for r in items} & defects),
                     "ids": {r["item_id"]: {"dataset": r["dataset"], "split": r["split"], "tag": r.get("tag")} for r in kept}}
    return out


def discover_tap_roots(cache: Path) -> list[Path]:
    """Traverse real directories once; never follow symlinks or enter this experiment's output."""
    roots = []
    for parent, dirs, _files in os.walk(cache, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not Path(parent, d).is_symlink())
        for d in dirs[:]:
            if d in TAP_DIRS:
                roots.append(Path(parent, d))
                dirs.remove(d)
    return sorted(roots)


def inspect_taps(tap_roots: list[Path], banks: dict) -> list[dict]:
    all_ids = {iid: (bn, meta) for bn, bank in banks.items() for iid, meta in bank["ids"].items()}
    records = []
    for tap_root in tap_roots:
        for path in sorted(tap_root.rglob("*index.json")):
            meta = json.loads(path.read_text())
            dataset = meta.get("dataset", path.parent.name)
            reader = meta.get("reader") or ("olens" if tap_root.name == "oracle_states" else "nla" if tap_root.name == "nla_states" else path.relative_to(tap_root).parts[0])
            ids = meta.get("item_ids") or sorted({r[0] for r in meta.get("rows", [])})
            fine_tuned = dataset.startswith("rf_") or "@" in dataset or "planted_facts" in path.parts
            matches = [all_ids[i] for i in ids if i in all_ids]
            splits = Counter(m[1]["split"] for m in matches)
            arrays = sorted(path.parent.glob("*.npy"))
            present = sorted(set(int(m.group(1)) for p in arrays for m in [re.search(r"(?:rL|tap)(\d+)", p.name)] if m))
            records.append({"path": str(path), "reader": reader, "dataset": dataset,
                            "source_kind": "fine_tuned_test_model" if fine_tuned else "main_bank" if matches else "unmatched",
                            "banks": sorted({m[0] for m in matches}), "matched_pool": splits["pool"], "matched_test": splits["test"],
                            "index_item_count": len(ids), "tap_blocks": present,
                            "array_count_in_directory": len(arrays), "source_index_sha256": sha(path),
                            "eligible_for_pool_probe": bool(not fine_tuned and matches and splits["pool"] and splits["test"] and set(TAPS).issubset(present))})
    return records


def assert_arm_coverage(rows: list[dict], expected: set[tuple], dimensions: tuple[str, ...]) -> None:
    seen = {tuple(r.get(k) for k in dimensions) for r in rows if r.get("n_rows", 0) > 0}
    missing = sorted(expected - seen)
    if missing:
        raise RuntimeError("SMOKE FAILED: missing " + "; ".join("/".join(map(str, cell)) for cell in missing))


def capture_smoke_contract() -> dict:
    dims = ("reader", "bank", "split", "condition", "tap_block")
    cells = set(itertools.product(READERS, BANKS, ("pool", "test"), ("natural", "shuf"), TAPS))
    return {"dimensions": dims, "expected_cells": sorted(cells), "cell_count": len(cells),
            "additional_assertions": ["finite fp16 pre_answer states only", "one state per native score item ID", "pool/test IDs disjoint", "pod/git_sha/code_sha present", "no LABEL_DEFECT", "target-state reference available"]}


def run_audit(repo: Path, cache: Path, out: Path, cache_out: Path, pod: str) -> dict:
    defs = defects_from_source(repo / "projects/g_agreement/r_bench/interim.py")
    banks = bank_inventory(repo / "projects/g_agreement/dataset", defs)
    roots = discover_tap_roots(cache)
    taps = inspect_taps(roots, banks)
    try:
        git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    except subprocess.CalledProcessError:
        git_sha = "unknown"
    prov = {"created_at": datetime.now(timezone.utc).isoformat(), "pod": pod, "git_sha": git_sha, "code_sha": sha(Path(__file__)),
            "collect_code_sha": sha(repo / "projects/g_agreement/r_bench/collect.py")}
    rows = []
    for bn, bank in banks.items():
        for reader in READERS:
            matching = [r for r in taps if r["source_kind"] == "main_bank" and bn in r["banks"] and r["reader"] == reader]
            rows.append({"bank": bn, "reader": reader, "eligible_facts": len(bank["facts"]),
                         "tap_indices": len(matching), "facts_with_any_tap": len({r["dataset"] for r in matching}),
                         "facts_with_pool_and_test_taps": len({r["dataset"] for r in matching if r["eligible_for_pool_probe"]}),
                         "excluded": bank["excluded"], "bank_sha256": bank["sha256"], "n_rows": 1, **prov})
    assert_arm_coverage(rows, set(itertools.product(BANKS, READERS)), ("bank", "reader"))
    status = "MISSING_MAIN_BANK_TAPS" if not any(r["tap_indices"] for r in rows) else "TAPS_FOUND_REQUIRES_FULL_PROVENANCE_AND_CONTROL_VALIDATION"
    summary = {"status": status, "cache_root": str(cache.resolve()), "tap_roots": [str(p) for p in roots],
               "tap_index_count": len(taps), "source_kind_counts": dict(Counter(r["source_kind"] for r in taps)),
               "source_array_count": len({p for root in roots for p in root.rglob("*.npy")}),
               "audited_arms": len(rows), "analysis": "not run", "classification_shares": None, "confidence_intervals": None,
               "inference_reason": "Main-bank pool/test internal states and matched shuffled controls must exist before inference.",
               "banks": {k: {kk: vv for kk, vv in v.items() if kk != "ids"} for k, v in banks.items()},
               "capture_smoke": capture_smoke_contract(), **prov}
    out.mkdir(parents=True, exist_ok=True); cache_out.mkdir(parents=True, exist_ok=True)
    (out / "audit.json").write_text(json.dumps(summary, indent=2) + "\n")
    (out / "audit_rows.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (cache_out / "tap_inventory.jsonl").write_text("".join(json.dumps({**r, **prov}) + "\n" for r in taps))
    lines = ["# R2 main-bank reader-internal-state audit", "", f"Status: **{status}**. CPU only; 0 pod-hours; 0 judge calls.", "",
             "No main-bank mechanism class, class share or confidence interval is estimated from missing taps. The fine-tuned test model is not substituted.", "",
             "| Bank | Reader | Eligible facts | Facts with any tap | Facts with pool+test taps |", "|---|---|---:|---:|---:|"]
    lines += [f"| {r['bank']} | {r['reader']} | {r['eligible_facts']} | {r['facts_with_any_tap']} | {r['facts_with_pool_and_test_taps']} |" for r in rows]
    lines += ["", f"Searched `{cache.resolve()}` recursively for reader_states, oracle_states and nla_states directories without following symlinks. Found {len(roots)} tap root(s), {len(taps)} index files and {summary['source_array_count']} arrays. Source classes: {summary['source_kind_counts']}.",
              "", "Every eligible bank/reader audit arm produced a row (6/6). This passes the CPU inventory smoke only; it does not pass the future capture smoke, which requires 72 reader×bank×split×condition×block cells.",
              "", "The existing `collect --reader-states` hook is restricted to natural test scoring. It omits pool taps and shuffled tap controls, so simply rerunning that command would not supply the registered pool-trained analysis. Required capture changes and guard sequence are in CAPTURE.md.",
              "", "Provenance: `audit_rows.jsonl` stamps the CPU host, Git SHA and code SHA. `audit.json` records bank and collection-code hashes. The full source-file inventory lives in cache/g_agreement/r/remainder/r2/tap_inventory.jsonl. Excluded LABEL_DEFECT facts are explicit per bank in the audit.",
              "", "Decision thresholds remain internal ≥0.85 / native ≤0.65 with disjoint CIs for unverbalised; internal and native ≤0.65 with target probe ≥0.90 for never transmitted. Neither condition can be evaluated here. Absence is an unavailable result, not evidence that no information reached the reader."]
    (out / "REPORT.md").write_text("\n".join(lines) + "\n")
    print(json.dumps({"status": status, "tap_roots": len(roots), "indices": len(taps), "source_kind_counts": summary["source_kind_counts"], "audit_arm_coverage": "6/6", "pod_hours": 0}))
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--phase", choices=("audit",), default="audit")
    ap.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[3])
    ap.add_argument("--pod", default="mac-cpu")
    args = ap.parse_args(argv)
    run_audit(args.repo, args.repo / "cache/g_agreement", args.repo / "results/g_agreement/r/remainder/r2", args.repo / "cache/g_agreement/r/remainder/r2", args.pod)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
