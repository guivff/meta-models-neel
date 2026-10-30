"""Separate E116 channel: exact original E108 chosen-member hit judge.

All changes to registered globals are scoped to this new worker process. No
executing source file, other process, original bank code or label is modified.
"""
import argparse
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from . import registered, transport
from .banks import choice108
from .accounting234 import snapshot
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require

CAP = Decimal('2')


def source_gate():
    source = transport.HERE/'E116_SOURCE_SEAL.json'
    for name, digest in read(source)['files'].items():
        require(sha(transport.ROOT/name) == digest, 'prospective E116 source pin')
    return source


def original108_call(unit, protocol):
    require(set(unit) == {'id', 'kind', 'data', 'rubric'} and unit['kind'] == 'choice_hit' and unit['rubric'] is None,
            'exact original E108 chosen-member hit descriptor')
    return choice108([unit['data']], 'judging')


def check_scope(bank, units, custody):
    require(bank == 'E116' and custody.get('experiment') == bank and custody.get('verified') is True and
            custody.get('complete_eligible_native_grid') is True and custody.get('labels_cpu_only') is True,
            'complete E116 owner source/custody')
    require(len(units) == len({u['id'] for u in units}) == 752 and all(u['kind'] == 'choice_hit' for u in units),
            'all376 original ONE items x two registered late blocks')
    require(custody['native_oracle52_60_only'] is True and custody['original_E108_choices_unchanged'] is True, 'registered E116 scope and original judge205 context')


class E116Transport(transport.Transport):
    def __init__(self, input_seal, input_sha256, admission, key):
        source = source_gate()
        require(admission['bank'] == 'E116' and Decimal(str(admission['allocation_usd'])) == CAP and
                admission['E116_source_seal_sha256'] == sha(source), 'separate registered E1162/source-bound admission')
        super().__init__(input_seal, input_sha256, admission, key)


@contextmanager
def worker(dest=None):
    source_gate()
    require(transport.CAPS.get('E116', CAP) == CAP, 'no E116 cap override')
    prior_cap = transport.CAPS.get('E116')
    transport.CAPS['E116'] = CAP
    saved = {name: getattr(registered, name) for name in
             ('unit_call', 'check_scope', 'normalized_code', 'Transport', 'snapshot', 'HERE', 'write')}
    try:
        registered.HERE = transport.HERE/'E116'
        registered.unit_call = original108_call
        registered.check_scope = check_scope
        registered.Transport = E116Transport
        registered.snapshot = snapshot
        if dest is not None:
            sealed = verify(dest/'INPUT_SEAL.json', sha(dest/'INPUT_SEAL.json'))
            ref = sealed['source_seals'][0]
            verify(ref['seal'], ref['sha256'])
            origin = Path(ref['seal']).parent
            audit = read(origin/'PATH_REDACTION_AUDIT.json')
            original = read(origin/'ORIGINAL_EVIDENCE.PRIVATE.json')
            def guarded(unit, protocol):
                call, validate = original108_call(unit, protocol)
                def check(value):
                    validate(value)
                    if unit['id'] in original:
                        spans = [value['records'][0]['evidence']]
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
        registered.normalized_code = lambda kind, terminal: (terminal['result']['records'][0]['hit']
            if terminal['status'] == 'KEPT' else None)
        yield
    finally:
        for name, value in saved.items():
            setattr(registered, name, value)
        if prior_cap is None:
            transport.CAPS.pop('E116', None)
        else:
            transport.CAPS['E116'] = prior_cap


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
