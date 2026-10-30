"""STATUS.md / STATUS.json writer and the pod-budget guard for the Phase W pod session.

    python -m projects.g_agreement.w_pod.status --stage S1 --started <iso> [--finished <iso>] --decodes 120/860 [--errors "..."]
    python -m projects.g_agreement.w_pod.status --check-budget [--limit 150]      # exit 0 = continue, exit 3 = skip to S5
    python -m projects.g_agreement.w_pod.status --mark-pod-start                   # writes POD_STARTED_AT (epoch seconds) once
    python -m projects.g_agreement.w_pod.status --append-error <stage> <file>      # traceback file -> STATUS.md errors section

``write_status`` OVERWRITES results/g_agreement/w/STATUS.md (and STATUS.json) with: stage, started/finished, decodes done/total,
pod minutes used (from POD_STARTED_AT), errors. ``budget_decision`` is the pure function run_w.sh calls before every stage."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from projects.g_agreement.core.accounting import now_iso

from . import common as W

STATUS_MD = W.W_RESULTS / "STATUS.md"
STATUS_JSON = W.W_RESULTS / "STATUS.json"
BUDGET_LIMIT_MIN = 150  # 2.5 h: skip to S5 when reached (brief: budget 3 h, stop at 2.5 h)
EXIT_SKIP_TO_S5 = 3


def budget_decision(minutes: float, limit: float = BUDGET_LIMIT_MIN) -> dict[str, Any]:
    """{'skip_to_s5': bool, 'minutes': m, 'limit': limit, 'remaining': limit − m}. Skip iff minutes >= limit."""
    m = float(minutes)
    return {"skip_to_s5": m >= float(limit), "minutes": round(m, 2), "limit": float(limit), "remaining": round(float(limit) - m, 2)}


def mark_pod_start(path: Path | None = None, force: bool = False, now: float | None = None) -> Path:
    p = path or W.POD_STARTED_AT
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists() or force:
        p.write_text(f"{time.time() if now is None else float(now):.3f}\n")
    return p


def write_status(stage: str, started: str | None, finished: str | None, decodes_done: int | None, decodes_total: int | None,
                 pod_minutes: float | None = None, errors: str | list[str] | None = None, *, notes: str | None = None,
                 md_path: Path | None = None, json_path: Path | None = None, started_at: Path | None = None) -> dict[str, Any]:
    md_path = md_path or STATUS_MD
    json_path = json_path or STATUS_JSON
    pm = W.pod_minutes(started_at) if pod_minutes is None else float(pod_minutes)
    errs = errors if isinstance(errors, list) else ([errors] if errors else [])
    rec = {"updated": now_iso(), "stage": stage, "started": started, "finished": finished, "decodes_done": decodes_done, "decodes_total": decodes_total,
           "pod_minutes": round(pm, 1), "budget": budget_decision(pm), "errors": errs, "notes": notes}
    md_path.parent.mkdir(parents=True, exist_ok=True)
    dec = "-" if decodes_done is None and decodes_total is None else f"{decodes_done if decodes_done is not None else '?'}/{decodes_total if decodes_total is not None else '?'}"
    lines = ["# STATUS (w)", "", f"updated: {rec['updated']}", f"stage: {stage}", f"started: {started or '-'}", f"finished: {finished or '-'}",
             f"decodes: {dec}", f"pod_minutes: {rec['pod_minutes']} (limit {BUDGET_LIMIT_MIN}; skip_to_s5={rec['budget']['skip_to_s5']})",
             "errors: " + ("none" if not errs else f"{len(errs)}")]
    if notes:
        lines.append(f"notes: {notes}")
    if errs:
        lines += ["", "## errors", ""]
        for e in errs:
            lines += ["```", str(e).rstrip(), "```", ""]
    md_path.write_text("\n".join(lines).rstrip() + "\n")
    json_path.write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def progress(stage: str, decodes_done: int, decodes_total: int, *, every: int = 1, notes: str | None = None) -> None:
    """Stage-internal counter: rewrite STATUS with the running decode count (the stage's started time, errors and notes are kept).
    Called by S1 / S2 / S4 after every ``every`` units of work; never raises."""
    try:
        if every > 1 and decodes_done % every and decodes_done != decodes_total:
            return
        prev = read_status()
        same = (prev.get("stage") or "").split(" (")[0] == stage.split(" (")[0]
        write_status(stage, prev.get("started") if same else now_iso(), None, int(decodes_done), int(decodes_total), errors=list(prev.get("errors") or []),
                     notes=notes if notes is not None else prev.get("notes"))
    except Exception as exc:  # pragma: no cover - a status write must never stop a stage
        print(f"[w/status] progress write failed: {exc}", flush=True)


def read_status(json_path: Path | None = None) -> dict[str, Any]:
    p = json_path or STATUS_JSON
    return json.loads(p.read_text()) if p.exists() else {}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage")
    ap.add_argument("--started")
    ap.add_argument("--finished")
    ap.add_argument("--decodes", help="done/total")
    ap.add_argument("--errors", default=None)
    ap.add_argument("--notes", default=None)
    ap.add_argument("--keep-errors", action="store_true", help="carry the previous STATUS.json errors over")
    ap.add_argument("--check-budget", action="store_true")
    ap.add_argument("--limit", type=float, default=BUDGET_LIMIT_MIN)
    ap.add_argument("--mark-pod-start", action="store_true")
    ap.add_argument("--append-error", nargs=2, metavar=("STAGE", "FILE"))
    ap.add_argument("--print-minutes", action="store_true")
    a = ap.parse_args(argv)
    if a.mark_pod_start:
        print(mark_pod_start())
        return 0
    if a.print_minutes:
        print(f"{W.pod_minutes():.1f}")
        return 0
    if a.check_budget:
        d = budget_decision(W.pod_minutes(), a.limit)
        print(json.dumps(d))
        return EXIT_SKIP_TO_S5 if d["skip_to_s5"] else 0
    prev = read_status()
    if a.append_error:
        stage, f = a.append_error
        tb = Path(f).read_text() if Path(f).exists() else f"(traceback file {f} missing)"
        errs = list(prev.get("errors") or []) + [f"[{stage}] {tb}"]
        write_status(stage, prev.get("started"), now_iso(), prev.get("decodes_done"), prev.get("decodes_total"), errors=errs, notes=prev.get("notes"))
        return 0
    if not a.stage:
        ap.error("--stage is required")
    done = total = None
    if a.decodes:
        d, t = a.decodes.split("/")
        done, total = (int(d) if d.strip() not in ("", "?") else None), (int(t) if t.strip() not in ("", "?") else None)
    errs = list(prev.get("errors") or []) if a.keep_errors else []
    if a.errors:
        errs.append(a.errors)
    write_status(a.stage, a.started, a.finished, done, total, errors=errs, notes=a.notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
