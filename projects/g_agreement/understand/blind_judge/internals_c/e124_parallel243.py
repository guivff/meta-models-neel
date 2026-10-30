"""434061b36 E124 continuation: original saved wires, bank3, e340 rate booking.

Process-local composition of tested saved-state continuation and e340 transport.
No executing/original source edit, cached success resend or scientific guard.
"""
import argparse
from decimal import Decimal
from pathlib import Path
from . import e124_continuation236 as original
from . import resume_e340 as bounds
from . import transport
from projects.g_agreement.readerbench.io import read, write, sha
from projects.g_agreement.readerbench.scoring import require

ACTIVE = None


def bound_events(rows):
    return [r for r in rows if r.get('event') == 'settle' and r.get('authority') == 'e34073059']


def union_raw(original_rows, physical):
    result = {r['path']: r for r in original_rows}
    for r in physical:
        if r['path'] in result:
            require(result[r['path']]['sha256'] == r['sha256'], 'same saved response hash')
        result[r['path']] = r
    return list(result.values())


def source_gate():
    p = transport.HERE/'E124_PARALLEL243_SOURCE_SEAL.json'
    for name, digest in read(p)['files'].items():
        require(sha(transport.ROOT/name) == digest, 'published E124 e340 continuation source')
    return p


class ParallelTransport(bounds.ResumeTransport):
    def __enter__(self):
        global ACTIVE
        require(self.bank == 'E124', 'E124 only')
        result = super().__enter__(); ACTIVE = self
        return result


def execute(dest):
    source_gate(); original.source_gate()
    saved = original.ContinuationTransport, original.source_gate, original.write
    previous_cap = bounds.CAPS.get('E124'); bounds.CAPS['E124'] = Decimal(3)

    def audited_write(path, value):
        path = Path(path)
        if path.name == 'RAW_RESPONSE_BINDINGS.json':
            require(ACTIVE is not None, 'active original E124 channel')
            value = union_raw(value, ACTIVE.physical)
            import json
            rows = [json.loads(line) for line in (ACTIVE.root/'ledger/ledger.jsonl').read_text().splitlines() if line.strip()]
            events = bound_events(rows)
            saved[2](path.parent/'BOOKED_429_BOUNDS.json',dict(authority='e34073059 extended by actual Guiv434061b36',
                events=events, total_booked_upper_bound_usd=str(sum((Decimal(e['usd']) for e in events),Decimal(0))),
                provider_actual_cost_known=False))
        if path.name == 'COUNTS.json':
            value = dict(value, booked_429_upper_bounds_included=True,
                cost_basis='Provider-reported charges plus explicitly booked reservation bounds; bounds are not provider costs')
        saved[2](path, value)

    original.ContinuationTransport = ParallelTransport
    original.source_gate = source_gate
    original.write = audited_write
    try:
        original.execute(dest)
    finally:
        original.ContinuationTransport, original.source_gate, original.write = saved
        if previous_cap is None: bounds.CAPS.pop('E124', None)
        else: bounds.CAPS['E124'] = previous_cap


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase-directory',type=Path,required=True)
    execute(p.parse_args().phase_directory)
