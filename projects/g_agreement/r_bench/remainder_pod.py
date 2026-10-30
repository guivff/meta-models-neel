"""Offline preparation helpers and pull/queue gates for remainder pod jobs.

No API calls, pod allocation, judge calls, or implicit authorization. Run bootstrap
only after the user's experiment-specific go and the relayed rule-6 booking.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shlex
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CAPS = {'r2': 1200, 'r3': 1200, 'r4': 3600, 'r5': 1800, 'r6': 1200}

def queue_ready(text: str) -> list[str]:
    rows = []
    for line in text.splitlines():
        cells = [c.strip() for c in line.split('|')]
        if len(cells) >= 5 and cells[2] == 'READY':
            rows.append(cells[3])
    return rows

def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def manifest(root: Path) -> dict[str, str]:
    paths = sorted(root.rglob('*'))
    if any(p.is_symlink() for p in paths):
        raise ValueError('deliverables must contain copied files, not symlinks')
    return {str(p.relative_to(root)): digest(p) for p in paths if p.is_file()}

def verify_pull(root: Path, receipt: dict) -> None:
    """Compare the Mac-created receipt with every remote deliverable byte."""
    if not receipt.get('mac_verified') or not receipt.get('files'):
        raise ValueError('Mac pull has not been verified or has no files')
    if manifest(root) != receipt['files']:
        raise ValueError('Mac pull receipt differs from remote deliverables')

def bootstrap(experiment: str, pod: str, run_id: str, seconds: int | None = None, idle_ceiling: int = 45) -> str:
    for name, value in [('pod', pod), ('run_id', run_id)]:
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value):
            raise ValueError(f'invalid {name}')
    if idle_ceiling not in (45, 90):
        raise ValueError('idle ceiling must follow PODS: 45 ordinarily, 90 for active rule 7c')
    cap = CAPS[experiment]
    seconds = cap if seconds is None else seconds
    if not 1 <= seconds <= cap:
        raise ValueError(f'guard duration must be in 1..{cap}; subtract already billed setup time')
    d = f'/workspace/remainder/{experiment}/{run_id}'
    guards = REPO / 'results/g_agreement/r/pod_tools'
    parts = ['#!/usr/bin/env bash', 'set -euo pipefail', f'POD={shlex.quote(pod)}', f'RUN={shlex.quote(d)}',
             'OWN=$(tr "\\0" "\\n" < /proc/1/environ | sed -n "s/^RUNPOD_POD_ID=//p")',
             '[ "$OWN" = "$POD" ] || { echo "POD ID MISMATCH"; exit 2; }',
             '[ ! -e "$RUN" ] || { echo "REFUSE reused run directory"; exit 2; }',
             'mkdir -p "$RUN/guards"',
             'GUARD_STARTED=$(date +%s)',
             f'GUARD_DEADLINE=$((GUARD_STARTED + {seconds}))',
             f'''printf '{{"pod":"{pod}","experiment":"{experiment}","started_epoch":%s,"deadline_epoch":%s}}\n' "$GUARD_STARTED" "$GUARD_DEADLINE" > "$RUN/guard.json"''']
    for script in ('ws2_watchdog.sh', 'ws2_hardstop.sh', 'ws2_selfstop.sh'):
        parts += [f"cat > \"$RUN/guards/{script}\" <<'REMAINDER_GUARD_EOF'", (guards/script).read_text(), 'REMAINDER_GUARD_EOF']
    parts += [
        'export WD_RESERVE_FILE="$RUN/reservation"',
        f'export WD_CEIL={idle_ceiling}',
        'nohup setsid bash "$RUN/guards/ws2_watchdog.sh" "$POD" "$RUN/job.pid" "$RUN/job.log" > "$RUN/watchdog.log" 2>&1 < /dev/null &',
        'echo $! > "$RUN/watchdog.pid"',
        f'nohup setsid bash "$RUN/guards/ws2_hardstop.sh" "$POD" {seconds} > "$RUN/hardstop.log" 2>&1 < /dev/null &',
        'echo $! > "$RUN/hardstop.pid"',
        'for try in $(seq 1 10); do',
        '  if grep -q "armed:" "$RUN/watchdog.log" && grep -q "armed:" "$RUN/hardstop.log"; then',
        '    kill -0 "$(cat "$RUN/watchdog.pid")" && kill -0 "$(cat "$RUN/hardstop.pid")"',
        '    touch "$RUN/ARMED"',
        '    echo "ARMED $RUN; sync isolated code and launch detached job only now"',
        '    exit 0',
        '  fi',
        '  sleep 1',
        'done',
        'echo "GUARDS NOT ARMED: no job may start"; exit 3',
    ]
    return '\n'.join(parts) + '\n'

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    b = sub.add_parser('bootstrap')
    b.add_argument('--experiment', choices=CAPS, required=True)
    b.add_argument('--pod', required=True)
    b.add_argument('--run-id', required=True)
    b.add_argument('--remaining-seconds', type=int)
    b.add_argument('--idle-ceiling-minutes', type=int, choices=(45, 90), default=45)
    m = sub.add_parser('pull-receipt')
    m.add_argument('--local-deliverables', type=Path, required=True)
    v = sub.add_parser('verify-pull')
    v.add_argument('--remote-deliverables', type=Path, required=True)
    v.add_argument('--receipt', type=Path, required=True)
    q = sub.add_parser('queue')
    q.add_argument('--fresh-integration', type=Path, required=True)
    a = p.parse_args(argv)
    if a.action == 'bootstrap':
        print(bootstrap(a.experiment, a.pod, a.run_id, a.remaining_seconds, a.idle_ceiling_minutes), end='')
    elif a.action == 'pull-receipt':
        files = manifest(a.local_deliverables)
        if not files: p.error('no local deliverables')
        print(json.dumps({'mac_verified': True, 'files': files}, sort_keys=True))
    elif a.action == 'verify-pull':
        verify_pull(a.remote_deliverables, json.loads(a.receipt.read_text()))
        print('MAC PULL VERIFIED')
    else:
        print(json.dumps({'ready_jobs': queue_ready(a.fresh_integration.read_text()), 'stop_authorized': False, 'note': 'Read all queued jobs and current PODS 7b/7c through the integrator; READY-only parsing never authorizes stop.'}))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
