"""Separate E120 channel: exact frozen E85 judge205 for targeted/sham Oracle readouts.

All changes to registered globals are scoped to this new worker process. No
executing source file, other process, original bank code or label is modified.
"""
import argparse
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from . import registered, transport
from .banks import eval85
from .accounting234 import snapshot
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require

CAP = Decimal('2')


def source_gate():
    source = transport.HERE/'E120c_SOURCE_SEAL.json'
    for name, digest in read(source)['files'].items():
        require(sha(transport.ROOT/name) == digest, 'prospective E120 source pin')
    return source


def original205_call(unit, protocol):
    require(set(unit) == {'id', 'kind', 'data', 'rubric'} and unit['kind'] == 'eval85' and unit['rubric'] is None,
            'exact original judge205 descriptor, no comparison arm')
    return eval85(unit['data'])


def check_scope(bank, units, custody):
    require(bank == 'E120' and custody.get('experiment') == bank and custody.get('verified') is True and
            custody.get('complete_eligible_native_grid') is True and custody.get('labels_cpu_only') is True,
            'complete E120c owner source/custody')
    require(len(units) == len({u['id'] for u in units}) == 800 and all(u['kind'] == 'eval85' for u in units),
            'all400original test items x targeted/sham only')
    require(custody['part'] == 'c' and custody['native_oracle44_only'] is True and
            custody['full_original_source_text'] is True, 'registered E120c scope and original judge205 context')


class E120Transport(transport.Transport):
    def __init__(self, input_seal, input_sha256, admission, key):
        source = source_gate()
        require(admission['bank'] == 'E120' and Decimal(str(admission['allocation_usd'])) == CAP and
                admission['E120c_source_seal_sha256'] == sha(source), 'separate registered E1202/source-bound admission')
        super().__init__(input_seal, input_sha256, admission, key)


@contextmanager
def worker(dest=None):
    source_gate()
    require(transport.CAPS.get('E120', CAP) == CAP, 'no E120 cap override')
    prior_cap = transport.CAPS.get('E120')
    transport.CAPS['E120'] = CAP
    saved = {name: getattr(registered, name) for name in
             ('unit_call', 'check_scope', 'normalized_code', 'Transport', 'snapshot', 'HERE', 'write')}
    try:
        registered.HERE = transport.HERE/'E120'
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
