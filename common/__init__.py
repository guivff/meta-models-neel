"""Shared helpers and the pinned, local-only Suraj library."""
from pathlib import Path
import sys

_src = Path(__file__).resolve().parents[1] / "external/mats-nla-workspace/src"
if _src.is_dir() and str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
