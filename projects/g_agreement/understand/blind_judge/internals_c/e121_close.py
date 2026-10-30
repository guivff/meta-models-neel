"""Administrative E121 full-bank closure; direct code/null pointers, no analysis."""
import argparse
from .runner import CACHE
from .transport import ROOT, HERE, SHARED
from .accounting import bank_actual
from .seal_bank import disposition
from ..dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require


def pointers(rows, phase, digest, n=168):
    require(len(rows) == len({x['id'] for x in rows}) == n, 'complete unique registered bank before closure')
    out = []
    for i, row in enumerate(rows):
        require(row['kind'] == 'original104' and row['status'] in ('KEPT', 'UNPARSEABLE', 'REFUSED'), 'registered terminal kind/status')
        require((row['code'] is None) == (row['status'] != 'KEPT'), 'original terminal missingness unchanged')
        out.append(dict(id=row['id'], kind=row['kind'], status=row['status'],
            original_code=dict(seal=str(phase), sha256=digest, member='JUDGMENTS.json', keys=[i, 'code'])))
    return out


def close():
    for name, digest in read(HERE/'E121_CLOSE_SOURCE_SEAL.json')['files'].items():
        require(sha(ROOT/name) == digest, 'published administrative close source')
    phase = CACHE/'E121/original104_judging/outputs/JUDGMENT_SEAL.json'
    s = verify(phase, sha(phase))
    require(s['status'] == 'COMPLETE' and s['experiment'] == 'E121' and s['route_verified'] is True, 'complete original E121 bank')
    rows = read(phase.parent/'JUDGMENTS.json')
    refs = pointers(rows, phase, sha(phase))
    with dispatch_lock(SHARED/'E121/DISPATCH.lock'):
        actual, unknown = bank_actual(SHARED/'E121/ledger'); cost = disposition(1, actual, unknown)
        ap = SHARED/'E121/ALLOCATION_C.json'; a = read(ap)
        require(a['bank'] == 'E121' and str(a['allocation_usd']) == '1', 'original separate lifetime1 allocation')
        dest = CACHE/'E121/complete'; dest.mkdir(exist_ok=True)
        final = dest/'JUDGMENT_SEAL.json'
        if final.exists():
            verify(final, sha(final)); require(read(dest/'BANK_COST.json') == cost, 'no later costs after once-only close')
        else:
            require(a['status'] == 'OPEN', 'only original open allowance can close')
            write(dest/'TERMINAL_BINDINGS.PRIVATE.json', refs)
            write(dest/'BANK_COST.json', cost); write(dest/'ORIGINAL_ALLOCATION.PRIVATE.json', a)
            write(final, dict(experiment='E121', status='COMPLETE_JUDGING_BANK', n=168, route_verified=True,
                labels_cpu_only=True, original_oracle_rejudged=False, phase_seal=str(phase), phase_sha256=sha(phase),
                files={n: sha(dest/n) for n in ('TERMINAL_BINDINGS.PRIVATE.json', 'BANK_COST.json', 'ORIGINAL_ALLOCATION.PRIVATE.json')}))
        if a['status'] == 'RELEASED': require(a['completion_seal_sha256'] == sha(final), 'same once-only unused release')
        else: write(ap, dict(a, status='RELEASED', completion_seal=str(final), completion_seal_sha256=sha(final),
            final_actual_usd=str(actual), unused_allocation_released_usd=cost['unused_allocation_released_usd']))
        write(SHARED/'E121/BANK_COMPLETE_C.json', dict(bank='E121', status='COMPLETE', seal=str(final), sha256=sha(final), **cost))
        return final


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print('E121 administrative complete '+sha(close()))
