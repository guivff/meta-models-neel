"""Administrative E120a+c combined lifetime closure; direct code/null pointers, no analysis."""
import argparse
from .runner import CACHE
from .transport import ROOT, HERE, SHARED
from .accounting import bank_actual
from .seal_bank import disposition
from ..dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require


def pointers(rows, phase, digest, n=800):
    require(len(rows) == len({x['id'] for x in rows}) == n, 'complete unique registered bank before closure')
    out = []
    for i, row in enumerate(rows):
        require(row['kind'] == 'eval85' and row['status'] in ('KEPT', 'UNPARSEABLE', 'REFUSED'), 'registered terminal kind/status')
        require((row['code'] is None) == (row['status'] != 'KEPT'), 'original terminal missingness unchanged')
        out.append(dict(id=row['id'], kind=row['kind'], status=row['status'],
            original_code=dict(seal=str(phase), sha256=digest, member='JUDGMENTS.json', keys=[i, 'code'])))
    return out


def close():
    for name, digest in read(HERE/'E120a_CLOSE_SOURCE_SEAL.json')['files'].items():
        require(sha(ROOT/name) == digest, 'published administrative close source')
    phase = CACHE/'E120/late_layers_judging/outputs/JUDGMENT_SEAL.json'
    s = verify(phase, sha(phase))
    require(s['status'] == 'COMPLETE' and s['experiment'] == 'E120' and s['route_verified'] is True, 'complete original E120 bank')
    rows = read(phase.parent/'JUDGMENTS.json')
    refs = pointers(rows, phase, sha(phase))
    prior = CACHE/'E120/complete/JUDGMENT_SEAL.json'
    old = verify(prior, sha(prior))
    require(old['part'] == 'c' and old['n'] == 800, 'immutable prior c completion')
    cont = SHARED/'E120/CONTINUATION_E120A_C.json'
    continuation = read(cont)
    require(continuation['prior_part_c_complete_sha256'] == sha(prior), 'source-bound original c seal')
    from .e120a_channel import check_continuation
    check_continuation(continuation)
    with dispatch_lock(SHARED/'E120/DISPATCH.lock'):
        actual, unknown = bank_actual(SHARED/'E120/ledger'); cost = disposition(2, actual, unknown)
        ap = SHARED/'E120/ALLOCATION_C.json'; a = read(ap)
        require(a['bank'] == 'E120' and str(a['allocation_usd']) == '2', 'original separate lifetime2 allocation')
        dest = CACHE/'E120/combined_a_c_complete'; dest.mkdir(exist_ok=True)
        final = dest/'JUDGMENT_SEAL.json'
        if final.exists():
            verify(final, sha(final)); require(read(dest/'BANK_COST.json') == cost, 'no later costs after once-only close')
        else:
            require(a['status'] == 'OPEN', 'only original open allowance can close')
            write(dest/'TERMINAL_BINDINGS.PRIVATE.json', refs)
            write(dest/'BANK_COST.json', cost); write(dest/'ORIGINAL_ALLOCATION.PRIVATE.json', a)
            write(dest/'CONTINUATION_E120A_C.json', continuation)
            write(final, dict(experiment='E120', status='COMPLETE_JUDGING_BANK', n=1600, new_phase_judgments=800, prior_part_c_sha256=sha(prior), route_verified=True,
                labels_cpu_only=True, part="a+c", original_E85_rejudged=False, phase_seal=str(phase), phase_sha256=sha(phase),
                files={n: sha(dest/n) for n in ('TERMINAL_BINDINGS.PRIVATE.json', 'BANK_COST.json', 'ORIGINAL_ALLOCATION.PRIVATE.json', 'CONTINUATION_E120A_C.json')}))
        if a['status'] == 'RELEASED': require(a['completion_seal_sha256'] == sha(final), 'same once-only unused release')
        else: write(ap, dict(a, status='RELEASED', completion_seal=str(final), completion_seal_sha256=sha(final),
            final_actual_usd=str(actual), unused_allocation_released_usd=cost['unused_allocation_released_usd']))
        write(SHARED/'E120/BANK_COMBINED_A_C_COMPLETE_C.json', dict(bank='E120', status='COMPLETE', seal=str(final), sha256=sha(final), **cost))
        return final


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print('E120 administrative complete '+sha(close()))
