"""Separate E117 main/c channel: literal original E56/E57 descriptors and renderer.

Both phases use one cumulative operational cap of USD4, below the registered
combined ceiling6; c also has its phase ceiling2. The extra2 remains unallocated.

All changes to registered globals are scoped to this new worker process. No
executing source file, other process, original bank code or label is modified.
"""
import argparse
import hashlib
from contextlib import contextmanager
from decimal import Decimal
from .. import parallel_funded
from pathlib import Path

from . import registered, transport
from .banks import value_call
from .accounting_e79b import snapshot
from projects.g_agreement.readerbench.io import read, write, sha, verify
from .e109_privacy import raw_evidence_guard
from projects.g_agreement.readerbench.scoring import require

CAP = Decimal('4')
PHASE_LIMITS = {'c': Decimal('2'), 'main': Decimal('4')}
RUBRIC_SHA = '03d9377b1ba3c2923cef0c3dd812cc3cc3bb6b8108a68bfe4f8e12b49e253613'


def source_gate():
    source = transport.HERE/'E117_SOURCE_SEAL.json'
    for name, digest in read(source)['files'].items():
        require(sha(transport.ROOT/name) == digest, 'prospective E117 source pin')
    return source


def original57_call(unit, protocol):
    require(set(unit) == {'id', 'kind', 'data', 'rubric'} and unit['kind'] == 'original57',
            'original E104 unit descriptor only')
    data = unit['data']
    require(set(data) == {'id', 'property', 'values', 'readout'} and data['id'] == unit['id'],
            'only original blinded id/property/candidates/readout')
    require(hashlib.sha256(unit['rubric'].encode()).hexdigest() == RUBRIC_SHA,
            'exact original shared E56/E57 rubric, no amended rubric')
    return value_call([data], protocol, 'judging', unit['rubric'])


def check_scope(part, bank, units, custody):
    require(bank == 'E117' and custody.get('experiment') == bank and custody.get('issuer') in
            ('I-2', 'W-internals-C') and custody.get('verified') is True and
            custody.get('complete_eligible_native_grid') is True and custody.get('labels_cpu_only') is True,
            'complete eligible E117 owner source/custody')
    require(custody.get('part') == part and part in PHASE_LIMITS, 'original phase identity')
    n = 672 if part == 'c' else 3024
    require(len(units) == len({u['id'] for u in units}) == n and
            all(u['kind'] == 'original57' for u in units), 'whole registered source grid; no original rejudging')
    require(custody.get('original_E56_E57_rubric_sha256') == RUBRIC_SHA and
            custody.get('original_E56_E57_descriptors_copied') is True and
            custody.get('all_degenerate_native_texts_retained') is True,
            'literal original E56/E57 descriptors and all native texts')


class E117Transport(transport.Transport):
    def __init__(self, input_seal, input_sha256, admission, key):
        source = source_gate()
        require(admission['bank'] == 'E117' and Decimal(str(admission['allocation_usd'])) == CAP and
                admission['E117_source_seal_sha256'] == sha(source), 'shared E117 lifetime4 operational allocation/source-bound admission')
        require(admission['part'] in PHASE_LIMITS and Decimal(admission['phase_ceiling_usd']) == PHASE_LIMITS[admission['part']], 'registered phase ceiling')
        super().__init__(input_seal, input_sha256, admission, key)

    def __enter__(self):
        value=super().__enter__()
        require(Decimal(self.summary()['actual_usd']) == Decimal(self.admission['phase_start_booked_usd']), 'exact phase-start cumulative cost; no resets')
        self.api.CAP = min(CAP, Decimal(self.admission['phase_start_booked_usd']) + PHASE_LIMITS[self.admission['part']])
        self.original_post=self.api.requests.post
        def checked_post(*a,**k):
            transport.unpaused()
            return self.original_post(*a,**k)
        self.api.requests.post=checked_post
        return value

    def __exit__(self,*args):
        self.api.requests.post=self.original_post
        return super().__exit__(*args)


@contextmanager
def worker(part, dest=None):
    require(part in PHASE_LIMITS, 'registered part')
    source_gate()
    require(transport.CAPS.get('E117', CAP) == CAP, 'no E117 cap override')
    prior_cap = transport.CAPS.get('E117')
    prior_expiry=transport.EXPIRY
    prior_rate_retries=parallel_funded.MAX_429_RETRIES
    parallel_funded.MAX_429_RETRIES=0  # unpriced refusal stops this bank, no guessed charge
    transport.EXPIRY=1793372400  # direct Guiv236 amendment4 / Fri16CET
    transport.CAPS['E117'] = CAP
    saved = {name: getattr(registered, name) for name in
             ('unit_call', 'check_scope', 'normalized_code', 'Transport', 'snapshot', 'HERE', 'write')}
    try:
        registered.HERE = transport.HERE/'E117'
        registered.unit_call = original57_call
        registered.check_scope = lambda bank, units, custody: check_scope(part, bank, units, custody)
        registered.Transport = E117Transport
        registered.snapshot = snapshot
        if dest is not None:
            sealed = verify(dest/'INPUT_SEAL.json', sha(dest/'INPUT_SEAL.json'))
            ref = sealed['source_seals'][0]
            verify(ref['seal'], ref['sha256'])
            origin = Path(ref['seal']).parent
            audit = read(origin/'PATH_REDACTION_AUDIT.json')
            original = read(origin/'ORIGINAL_EVIDENCE.PRIVATE.json')
            registered.unit_call = lambda unit, protocol: raw_evidence_guard(lambda u: original57_call(u, protocol), unit, original)
            def audited(path, value):
                path = Path(path)
                if path.name == 'JUDGMENT_SEAL.json':
                    ap = path.parent/'PATH_REDACTION_AUDIT.json'; saved['write'](ap, audit)
                    value = dict(value, redacted_records=audit['redacted_records'], redacted_opaque_ids=sorted(original),
                        files=dict(value['files'], **{'PATH_REDACTION_AUDIT.json': sha(ap)}))
                saved['write'](path, value)
            registered.write = audited
        registered.normalized_code = lambda kind, terminal: (terminal['result']['records'][0]
            if terminal['status'] == 'KEPT' else None)
        yield
    finally:
        transport.EXPIRY=prior_expiry
        parallel_funded.MAX_429_RETRIES=prior_rate_retries
        for name, value in saved.items():
            setattr(registered, name, value)
        if prior_cap is None:
            transport.CAPS.pop('E117', None)
        else:
            transport.CAPS['E117'] = prior_cap


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'run'))
    p.add_argument('--part', choices=('main','c'), required=True)
    p.add_argument('--spec', type=Path)
    p.add_argument('--phase-directory', type=Path)
    args = p.parse_args()
    with worker(args.part, args.phase_directory if args.action == 'run' else None):
        if args.action == 'prepare':
            registered.prepare(args.spec)
        else:
            registered.run(args.phase_directory)
