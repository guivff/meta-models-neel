"""E112 exact E80 family worker; regex stays CPU, no original-arm rejudging."""
import argparse
from contextlib import contextmanager
from pathlib import Path
from . import registered, transport
from .e112_channel import E112Transport, register_process_cap, family_call
from .accounting226 import snapshot
from ..e80_channel import load_renderers
from projects.g_agreement.readerbench.io import read, sha
from projects.g_agreement.readerbench.scoring import require


def source_gate():
    for name, digest in read(transport.HERE/'E112_DRIVER_SOURCE_SEAL.json')['files'].items():
        require(sha(transport.ROOT/name) == digest, 'E112 family-driver source pin')


def unit_call(unit, protocol, renderer):
    require(set(unit) == {'id', 'kind', 'data', 'rubric'} and unit['kind'] == 'family80' and
            unit['rubric'] is None, 'original E80 family unit')
    data = unit['data']
    require(set(data) == {'id', 'packet', 'readout'} and data['id'] == unit['id'], 'CPU-only family validator descriptor')
    return family_call(unit['id'], data['packet'], data['readout'], protocol, renderer)


def check_scope(bank, units, custody):
    require(bank == 'E112' and custody.get('experiment') == bank and custody.get('verified') is True and
            custody.get('complete_eligible_native_grid') is True and custody.get('labels_cpu_only') is True,
            'complete original E112 owner custody')
    require(len(units) == custody['paid_family_units'] and len(units)+custody['cpu_regex_units'] == 1036 and
            len({x['id'] for x in units}) == len(units) and all(x['kind'] == 'family80' for x in units),
            'full1036 census with exact original regex/API split')
    require(custody['original_arms_rejudged'] is False and custody['original_E80_families_unchanged'] is True,
            'new PCA1 readouts only; no generic comparison')


@contextmanager
def worker():
    source_gate()
    prior = transport.CAPS.get('E112')
    register_process_cap()
    route = read(transport.ROOT/'results/g_agreement/understand/blind_judge/e80_channel/ROUTE_SEAL.json')
    renderer, _ = load_renderers(route)
    saved = {n: getattr(registered, n) for n in ('unit_call', 'check_scope', 'normalized_code', 'Transport', 'snapshot', 'HERE')}
    registered.HERE = transport.HERE/'E112'
    registered.unit_call = lambda unit, protocol: unit_call(unit, protocol, renderer)
    registered.check_scope = check_scope
    registered.normalized_code = lambda kind, terminal: terminal['result'] if terminal['status'] == 'KEPT' else None
    registered.Transport = E112Transport
    registered.snapshot = snapshot
    try:
        yield
    finally:
        for name, value in saved.items():setattr(registered, name, value)
        if prior is None:transport.CAPS.pop('E112', None)
        else:transport.CAPS['E112'] = prior


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('prepare', 'run'))
    p.add_argument('--spec', type=Path)
    p.add_argument('--phase-directory', type=Path)
    args = p.parse_args()
    with worker():
        if args.action == 'prepare':registered.prepare(args.spec)
        else:registered.run(args.phase_directory)
