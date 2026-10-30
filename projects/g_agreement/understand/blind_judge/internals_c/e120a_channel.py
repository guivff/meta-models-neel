"""Separate E120 channel: exact frozen E85 judge205 for Oracle52/60 readouts.

All changes to registered globals are scoped to this new worker process. No
executing source file, other process, original bank code or label is modified.
"""
import argparse
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from . import registered, transport
from .banks import eval85
from .accounting_e79b import snapshot
from .. import parallel_funded
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require

CAP = Decimal('2')


def check_continuation(value):
    require(value['bank'] == 'E120' and value['part'] == 'a' and
            Decimal(value['lifetime_cap_usd']) == CAP and
            Decimal(value['prior_part_c_actual_usd']) + Decimal(value['remaining_allowance_usd']) == CAP and
            value['prior_allocation_status'] == 'RELEASED' and value['same_original_allowance'] is True,
            'only unused original E120 lifetime2, no new allowance')


def source_gate():
    source = transport.HERE/'E120a_SOURCE_SEAL.json'
    for name, digest in read(source)['files'].items():
        require(sha(transport.ROOT/name) == digest, 'prospective E120a source pin')
    require(read(source).get('report_adapter_identity_custody_fixed') is True, 'owner tested original code/row identity binding before calls')
    return source


def original205_call(unit, protocol):
    require(set(unit) == {'id', 'kind', 'data', 'rubric'} and unit['kind'] == 'eval85' and unit['rubric'] is None,
            'exact original judge205 descriptor, no comparison arm')
    return eval85(unit['data'])


def check_scope(bank, units, custody):
    require(bank == 'E120' and custody.get('experiment') == bank and custody.get('verified') is True and
            custody.get('complete_eligible_native_grid') is True and custody.get('labels_cpu_only') is True,
            'complete E120a owner source/custody')
    require(len(units) == len({u['id'] for u in units}) == 800 and all(u['kind'] == 'eval85' for u in units),
            'all400original TEST items x Oracle52/60 only')
    require(custody['part'] == 'a' and custody['native_oracle52_60_only'] is True and
            custody['full_original_source_text'] is True, 'registered E120a scope and original judge205 context')


class E120Transport(transport.Transport):
    def __init__(self, input_seal, input_sha256, admission, key):
        source = source_gate()
        require(admission['bank'] == 'E120' and Decimal(str(admission['allocation_usd'])) == CAP and
                admission['E120a_source_seal_sha256'] == sha(source), 'separate registered E1202/source-bound admission')
        continuation = transport.SHARED/'E120/CONTINUATION_E120A_C.json'
        require(admission['continuation_sha256'] == sha(continuation), 'published same lifetime continuation')
        check_continuation(read(continuation))
        super().__init__(input_seal, input_sha256, admission, key)

    def __enter__(self):
        result = super().__enter__()
        self.original_post = self.api.requests.post
        def checked_post(url, *args, **kwargs):
            transport.unpaused()  # physical POST after pacing, not only before waiting
            return self.original_post(url, *args, **kwargs)
        self.api.requests.post = checked_post
        return result

    def __exit__(self, *args):
        self.api.requests.post = self.original_post
        return super().__exit__(*args)


@contextmanager
def worker(dest=None):
    source_gate()
    require(transport.CAPS.get('E120', CAP) == CAP, 'no E120 cap override')
    prior_cap = transport.CAPS.get('E120')
    old_expiry, old_retries = transport.EXPIRY, parallel_funded.MAX_429_RETRIES
    transport.EXPIRY = 1793372400
    parallel_funded.MAX_429_RETRIES = 0  # unknown-cost 429 stops this bank without resend
    transport.CAPS['E120'] = CAP
    saved = {name: getattr(registered, name) for name in
             ('unit_call', 'check_scope', 'normalized_code', 'Transport', 'snapshot', 'HERE', 'write')}
    try:
        registered.HERE = transport.HERE/'E120a'
        registered.unit_call = original205_call
        registered.check_scope = check_scope
        registered.Transport = E120Transport
        registered.snapshot = snapshot
        if dest is not None:
            sealed = verify(dest/'INPUT_SEAL.json', sha(dest/'INPUT_SEAL.json'))
            ref = sealed['source_seals'][0]
            verify(ref['seal'], ref['sha256'])
            origin = Path(ref['seal']).parent
            audit = read(origin/'PATH_REDACTION_AUDIT.json')
            original = read(origin/'ORIGINAL_EVIDENCE.PRIVATE.json')
            def guarded(unit, protocol):
                call, validate = original205_call(unit, protocol)
                def check(value):
                    validate(value)
                    if unit['id'] in original:
                        spans = [value[k] for k in ('a_evidence', 'b_evidence', 'c_evidence')] + value['c_genres']
                        require(all(s in original[unit['id']] for s in spans), 'kept evidence also verbatim in original native readout')
                return call, check
            registered.unit_call = guarded
            def audited(path, value):
                path = Path(path)
                if path.name == 'JUDGMENT_SEAL.json':
                    ap = path.parent/'PATH_REDACTION_AUDIT.json'; saved['write'](ap, audit)
                    value = dict(value, redacted_records=audit['redacted_records'], redacted_opaque_ids=sorted(original),
                        files=dict(value['files'], **{'PATH_REDACTION_AUDIT.json': sha(ap)}))
                saved['write'](path, value)
            registered.write = audited
        registered.normalized_code = lambda kind, terminal: (terminal['result']
            if terminal['status'] == 'KEPT' else None)
        yield
    finally:
        transport.EXPIRY, parallel_funded.MAX_429_RETRIES = old_expiry, old_retries
        for name, value in saved.items():
            setattr(registered, name, value)
        if prior_cap is None:
            transport.CAPS.pop('E120', None)
        else:
            transport.CAPS['E120'] = prior_cap


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'run'))
    p.add_argument('--spec', type=Path)
    p.add_argument('--phase-directory', type=Path)
    args = p.parse_args()
    with worker(args.phase_directory if args.action == 'run' else None):
        if args.action == 'prepare':
            registered.prepare(args.spec)
        else:
            registered.run(args.phase_directory)
