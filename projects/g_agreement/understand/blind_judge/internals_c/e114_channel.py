"""Separate E114 channel: exact original E57/E56 rubric and frozen value renderer.

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
from .accounting226 import snapshot
from projects.g_agreement.readerbench.io import read, sha
from projects.g_agreement.readerbench.scoring import require

CAP = Decimal('2')
RUBRIC_SHA = '03d9377b1ba3c2923cef0c3dd812cc3cc3bb6b8108a68bfe4f8e12b49e253613'


def source_gate():
    source = transport.HERE/'E114_SOURCE_SEAL.json'
    for name, digest in read(source)['files'].items():
        require(sha(transport.ROOT/name) == digest, 'prospective E114 source pin')
    return source


def original57_call(unit, protocol):
    require(set(unit) == {'id', 'kind', 'data', 'rubric'} and unit['kind'] == 'original57',
            'original E57 unit descriptor only')
    data = unit['data']
    require(set(data) == {'id', 'property', 'values', 'readout'} and data['id'] == unit['id'],
            'only original blinded id/property/candidates/readout')
    require(hashlib.sha256(unit['rubric'].encode()).hexdigest() == RUBRIC_SHA,
            'exact original E57 shared E56 rubric, no amended rubric')
    return value_call([data], protocol, 'judging', unit['rubric'])


def check_scope(bank, units, custody):
    require(bank == 'E114' and custody.get('experiment') == bank and custody.get('issuer') in
            ('I-2', 'W-internals-C') and custody.get('verified') is True and
            custody.get('complete_eligible_native_grid') is True and custody.get('labels_cpu_only') is True,
            'complete eligible E114 owner source/custody')
    require(len(units) == 504 and len({u['id'] for u in units}) == 504 and
            all(u['kind'] == 'original57' for u in units), 'exact504 original stated/opposite readouts')
    require(custody.get('original_E57_rubric_sha256') == RUBRIC_SHA and
            custody.get('original_gold_unchanged') is True and custody.get('native_oracle44_only') is True,
            'original E57 scorer/CPU gold and native Oracle44 only')


class E114Transport(transport.Transport):
    def __init__(self, input_seal, input_sha256, admission, key):
        source = source_gate()
        require(admission['bank'] == 'E114' and Decimal(str(admission['allocation_usd'])) == CAP and
                admission['E114_source_seal_sha256'] == sha(source), 'separate registered E1142/source-bound admission')
        super().__init__(input_seal, input_sha256, admission, key)


@contextmanager
def worker():
    source_gate()
    require(transport.CAPS.get('E114', CAP) == CAP, 'no E114 cap override')
    prior_cap = transport.CAPS.get('E114')
    transport.CAPS['E114'] = CAP
    saved = {name: getattr(registered, name) for name in
             ('unit_call', 'check_scope', 'normalized_code', 'Transport', 'snapshot', 'HERE')}
    registered.HERE = transport.HERE/'E114'
    registered.unit_call = original57_call
    registered.check_scope = check_scope
    registered.Transport = E114Transport
    registered.snapshot = snapshot
    registered.normalized_code = lambda kind, terminal: (terminal['result']['records'][0]
        if terminal['status'] == 'KEPT' else None)
    try:
        yield
    finally:
        for name, value in saved.items():
            setattr(registered, name, value)
        if prior_cap is None:
            transport.CAPS.pop('E114', None)
        else:
            transport.CAPS['E114'] = prior_cap


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'run'))
    p.add_argument('--spec', type=Path)
    p.add_argument('--phase-directory', type=Path)
    args = p.parse_args()
    with worker():
        if args.action == 'prepare':
            registered.prepare(args.spec)
        else:
            registered.run(args.phase_directory)
