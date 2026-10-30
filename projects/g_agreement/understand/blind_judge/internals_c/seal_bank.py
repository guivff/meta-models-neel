"""Close a fully sealed C bank and release only its evidenced unused allocation.

CPU-only, under the existing bank dispatch lock. No request, settlement, retry,
scientific analysis, or modification of the original allocation receipt.
"""
import argparse
from decimal import Decimal
from datetime import datetime, timezone

from .transport import HERE, SHARED
from .runner import CACHE
from .accounting import bank_actual
from ..dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require


def disposition(cap, actual, unknown):
    cap, actual, unknown = map(lambda x: Decimal(str(x)), (cap, actual, unknown))
    require(all(x.is_finite() and x >= 0 for x in (cap, actual, unknown)), 'finite nonnegative physical accounting')
    require(unknown == 0, 'no release with an unresolved physical reservation')
    require(actual <= cap, 'combined lifetime cap preserved')
    return dict(cap_usd=str(cap), actual_usd=str(actual), unresolved_reserve_usd='0',
                unused_allocation_released_usd=str(cap-actual), allocation_reset=False)


def complete(bank):
    source = HERE/'BANK_CLOSE_SOURCE_SEAL.json'
    for name, digest in read(source)['files'].items():
        from .transport import ROOT
        require(sha(ROOT/name) == digest, 'published bank-close source pin')
    require(bank in ('E109', 'E108'), 'explicit complete-bank source contracts only')
    if bank == 'E109':
        cap = 6
        expected = [('oracle_arrival_copy_judging', 1008), ('oracle_arrival_copy_original', 252)]
        binding = CACHE/bank/'oracle_code_binding/BINDING_SEAL.json'
    else:
        cap = 8
        expected = [('generation', 1008), ('native_choice_extraction', 1008), ('chosen_member_hit_judging', 1190)]
        binding = CACHE/bank/'normalized/JUDGMENT_SEAL.json'
    with dispatch_lock(SHARED/bank/'DISPATCH.lock'):
        bound = verify(binding, sha(binding))
        require(bound['experiment'] == bank and bound['status'] == ('COMPLETE_CPU_BINDING' if bank == 'E109' else 'COMPLETE'),
                'complete exact CPU binding before bank closure')
        phases = []
        for phase, count in expected:
            out = CACHE/bank/phase/'outputs'
            path = out/('GENERATION_SEAL.json' if phase == 'generation' else 'JUDGMENT_SEAL.json')
            seal = verify(path, sha(path))
            require(seal['experiment'] == bank and seal['status'] == 'COMPLETE' and seal['route_verified'] is True,
                    'every required original phase complete on approved route')
            name = 'RESPONSES.json' if phase == 'generation' else 'JUDGMENTS.json'
            records = read(out/name)
            require(len(records) == count and len({x['id'] for x in records}) == count,
                    'full exact per-phase terminal census')
            phases.append(dict(phase=phase, n=count, seal=str(path), sha256=sha(path)))
        actual, unknown = bank_actual(SHARED/bank/'ledger')
        cost = disposition(cap, actual, unknown)
        allocation_path = SHARED/bank/'ALLOCATION_C.json'
        allocation = read(allocation_path)
        require(allocation['bank'] == bank and allocation['operator'] == 'W-internals-C' and
                Decimal(str(allocation['allocation_usd'])) == cap and allocation['reservation_included'] is True,
                'original canonical combined bank allocation')
        dest = CACHE/bank/'complete'
        dest.mkdir(exist_ok=True)
        dest.chmod(0o700)
        final = dest/'JUDGMENT_SEAL.json'
        if final.exists():
            prior = verify(final, sha(final))
            require(prior['binding_sha256'] == sha(binding) and read(dest/'BANK_COST.json') == cost,
                    'immutable completed bank; no later cost or source change')
        else:
            require(allocation['status'] == 'OPEN', 'only close an actual open allocation')
            write(dest/'ORIGINAL_ALLOCATION.PRIVATE.json', allocation)
            write(dest/'BANK_COST.json', cost)
            write(dest/'PHASES.json', phases)
            write(final, dict(experiment=bank, status='COMPLETE', final_bank=True,
                completed_utc=datetime.now(timezone.utc).isoformat(), route_verified=True, labels_cpu_only=True,
                binding_seal=str(binding), binding_sha256=sha(binding), source_manifest_sha256=sha(source),
                source_seals=phases, scientific_analysis_run=False,
                files={n: sha(dest/n) for n in ('ORIGINAL_ALLOCATION.PRIVATE.json', 'BANK_COST.json', 'PHASES.json')}))
        if allocation['status'] == 'RELEASED':
            require(allocation['completion_seal_sha256'] == sha(final), 'same once-only release')
        else:
            require(allocation['status'] == 'OPEN', 'known allocation status')
            write(allocation_path, dict(allocation, status='RELEASED', completion_seal=str(final),
                completion_seal_sha256=sha(final), final_actual_usd=str(actual),
                unused_allocation_released_usd=cost['unused_allocation_released_usd']))
        write(SHARED/bank/'BANK_COMPLETE_C.json', dict(bank=bank, status='COMPLETE',
            seal=str(final), sha256=sha(final), **cost))
        return final


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bank', choices=('E109', 'E108'), required=True)
    args = p.parse_args()
    final = complete(args.bank)
    print('Completed canonical bank '+args.bank+' '+sha(final))
