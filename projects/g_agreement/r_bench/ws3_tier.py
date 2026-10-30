"""checkpoint_tier, scoped to WS3's own tables (Integrator, 2026-10-19: ``checkpoint_tier --apply`` over every tracked
table rewrote other streams' files, e.g. TH-2's i2/th2_event_orders.csv). checkpoint_tier.py is not WS3's file, so it is
left unchanged; this wrapper restricts its table list to the CSVs directly under results/g_agreement/r/ whose adding
commit is a WS3 commit (subject starting "WS3"), plus WS3 CSVs not yet committed when named with --also.

    python -m projects.g_agreement.r_bench.ws3_tier --apply [--also results/g_agreement/r/new.csv ...]
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from projects.g_agreement.r_bench import checkpoint_tier as CT

R_DIR = "results/g_agreement/r"


def ws3_tables(root: Path = CT.ROOT) -> list[Path]:
    files = subprocess.check_output(["git", "ls-files", f"{R_DIR}/*.csv"], cwd=root, text=True).split()
    out = []
    for f in files:
        if "/" in f[len(R_DIR) + 1:] or f.endswith(".tiers.csv"):
            continue  # subdirectories (i2/, planted_facts/, …) belong to other streams
        subj = subprocess.check_output(["git", "log", "--diff-filter=A", "--format=%s", "--", f], cwd=root, text=True).strip().splitlines()
        if subj and subj[-1].startswith("WS3"):
            out.append(root / f)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--apply", action="store_true")
    g.add_argument("--check", action="store_true")
    g.add_argument("--list", action="store_true")
    ap.add_argument("--also", nargs="*", default=[])
    a = ap.parse_args(argv)
    mine = ws3_tables() + [CT.ROOT / p for p in a.also if (CT.ROOT / p).exists()]
    if a.list:
        print("\n".join(str(p.relative_to(CT.ROOT)) for p in mine))
        return 0
    CT.tables = lambda: mine  # scope the shared tool to WS3's tables only
    for line in CT.apply(check_only=a.check):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
