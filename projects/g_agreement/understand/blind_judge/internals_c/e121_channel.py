"""Separate E121 channel: exact original E104/E56 rubric and frozen value renderer.

All changes to registered globals are scoped to this new worker process. No
executing source file, other process, original bank code or label is modified.
"""
import argparse
import hashlib
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from . import registered, transport
from .banks import value_call
from .accounting234 import snapshot
from projects.g_agreement.readerbench.io import read, write, sha, verify
from .e109_privacy import raw_evidence_guard
from projects.g_agreement.readerbench.scoring import require

CAP = Decimal('1')
RUBRIC_SHA = '03d9377b1ba3c2923cef0c3dd812cc3cc3bb6b8108a68bfe4f8e12b49e253613'


def source_gate():
    source = transport.HERE/'E121_SOURCE_SEAL.json'
    for name, digest in read(source)['files'].items():
        require(sha(transport.ROOT/name) == digest, 'prospective E121 source pin')
    return source


def original104_call(unit, protocol):
    require(set(unit) == {'id', 'kind', 'data', 'rubric'} and unit['kind'] == 'original104',
            'original E104 unit descriptor only')
    data = unit['data']
    require(set(data) == {'id', 'property', 'values', 'readout'} and data['id'] == unit['id'],
            'only original blinded id/property/candidates/readout')
    require(hashlib.sha256(unit['rubric'].encode()).hexdigest() == RUBRIC_SHA,
            'exact original E104 shared E56 rubric, no amended rubric')
    return value_call([data], protocol, 'judging', unit['rubric'])


def check_scope(bank, units, custody):
    require(bank == 'E121' and custody.get('experiment') == bank and custody.get('issuer') in
            ('I-2', 'W-internals-C') and custody.get('verified') is True and
            custody.get('complete_eligible_native_grid') is True and custody.get('labels_cpu_only') is True,
            'complete eligible E121 owner source/custody')
    require(len(units) == 168 and len({u['id'] for u in units}) == 168 and
            all(u['kind'] == 'original104' for u in units), 'exact168 new NLA readouts; no original Oracle rejudging')
    require(custody.get('original_E104_rubric_sha256') == RUBRIC_SHA and
            custody.get('original_candidates_unchanged') is True and custody.get('native_nla42_only') is True,
            'original E104 scorer/CPU gold and native NLA42 only')


class E121Transport(transport.Transport):
    def __init__(self, input_seal, input_sha256, admission, key):
        source = source_gate()
        require(admission['bank'] == 'E121' and Decimal(str(admission['allocation_usd'])) == CAP and
                admission['E121_source_seal_sha256'] == sha(source), 'separate registered E1211/source-bound admission')
        super().__init__(input_seal, input_sha256, admission, key)


@contextmanager
def worker(dest=None):
    source_gate()
    require(transport.CAPS.get('E121', CAP) == CAP, 'no E121 cap override')
    prior_cap = transport.CAPS.get('E121')
    transport.CAPS['E121'] = CAP
    saved = {name: getattr(registered, name) for name in
             ('unit_call', 'check_scope', 'normalized_code', 'Transport', 'snapshot', 'HERE', 'write')}
    try:
        registered.HERE = transport.HERE/'E121'
        registered.unit_call = original104_call
        registered.check_scope = check_scope
        registered.Transport = E121Transport
        registered.snapshot = snapshot
        if dest is not None:
            sealed = verify(dest/'INPUT_SEAL.json', sha(dest/'INPUT_SEAL.json'))
            ref = sealed['source_seals'][0]
            verify(ref['seal'], ref['sha256'])
            origin = Path(ref['seal']).parent
            audit = read(origin/'PATH_REDACTION_AUDIT.json')
            original = read(origin/'ORIGINAL_EVIDENCE.PRIVATE.json')
            registered.unit_call = lambda unit, protocol: raw_evidence_guard(lambda u: original104_call(u, protocol), unit, original)
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
        for name, value in saved.items():
            setattr(registered, name, value)
        if prior_cap is None:
            transport.CAPS.pop('E121', None)
        else:
            transport.CAPS['E121'] = prior_cap


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
