"""Per-call accounting (wall-clock, tokens, peak CUDA memory) and the shared compute ledger
``results/g_agreement/compute.jsonl`` (INTERFACES §7), plus the small JSONL helpers every
collector uses for resumability. Pure Python apart from an optional torch import."""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from . import config as C

GPU_NAME_FALLBACK = "H100 80GB"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def peak_mem_gb(reset: bool = False) -> float | None:
    try:
        import torch

        if not torch.cuda.is_available():
            return None
        v = torch.cuda.max_memory_allocated() / 1e9
        if reset:
            torch.cuda.reset_peak_memory_stats()
        return round(v, 3)
    except Exception:
        return None


def gpu_name() -> str:
    try:
        import torch

        if torch.cuda.is_available():
            return torch.cuda.get_device_name(0)
    except Exception:
        pass
    return "cpu"


@dataclass
class CallStats:
    wall_s: float = 0.0
    peak_mem_gb: float | None = None
    started: str = ""
    ended: str = ""


@contextmanager
def timed_call() -> Iterator[CallStats]:
    """``with timed_call() as st: ...`` then ``st.wall_s``, ``st.peak_mem_gb``."""
    st = CallStats(started=now_iso())
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.synchronize()
            torch.cuda.reset_peak_memory_stats()
    except Exception:
        pass
    t0 = time.perf_counter()
    try:
        yield st
    finally:
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.synchronize()
        except Exception:
            pass
        st.wall_s = round(time.perf_counter() - t0, 3)
        st.peak_mem_gb = peak_mem_gb()
        st.ended = now_iso()


@dataclass
class StepLedger:
    """Accumulates one ledger row per (step, module); ``flush`` appends it to compute.jsonl."""

    step: str
    module: str
    n_calls: int = 0
    prompt_tokens: int = 0
    new_tokens: int = 0
    wall_s: float = 0.0
    peak_mem_gb: float = 0.0
    started: str = field(default_factory=now_iso)
    extra: dict[str, Any] = field(default_factory=dict)

    def add(self, n_prompt: int = 0, n_new: int = 0, wall_s: float = 0.0, peak: float | None = None) -> None:
        self.n_calls += 1
        self.prompt_tokens += int(n_prompt)
        self.new_tokens += int(n_new)
        self.wall_s += float(wall_s)
        if peak is not None:
            self.peak_mem_gb = max(self.peak_mem_gb, float(peak))

    def row(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "module": self.module,
            "n_calls": self.n_calls,
            "prompt_tokens": self.prompt_tokens,
            "new_tokens": self.new_tokens,
            "wall_s": round(self.wall_s, 3),
            "peak_mem_gb": round(self.peak_mem_gb, 3),
            "gpu": gpu_name(),
            "started": self.started,
            "ended": now_iso(),
            **({"extra": self.extra} if self.extra else {}),
        }

    def flush(self, path: Path | None = None) -> dict[str, Any] | None:
        if self.n_calls == 0:
            return None
        row = self.row()
        append_jsonl(path or C.COMPUTE_LEDGER, row)
        return row


# ------------------------------------------------------------------ JSONL helpers
def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        fh.flush()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def done_ids(path: Path, key: str = "gen_id") -> set[str]:
    """The ids already present in a JSONL (for resumable collectors)."""
    return {r[key] for r in read_jsonl(path) if key in r}


def log_line(path: Path, text: str) -> None:
    """Append a timestamped line to a module's log.md."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"- {now_iso()} {text}\n")
