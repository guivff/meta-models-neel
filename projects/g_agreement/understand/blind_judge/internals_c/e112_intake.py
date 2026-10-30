"""Full sealed E112 PCA1 native grid to original E80 family/regex units."""
import argparse
import re
from pathlib import Path
from .runner import CACHE
from .transport import ROOT, HERE
from .banks import opaque
from .e112_channel import validate_grid
from ..e80_channel import load_renderers
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require


def native_members(files):
    jobs = [name for name in files if name.startswith('jobs/') and name.endswith('.json')]
    batches = [name for name in jobs if re.fullmatch(r'jobs/(oracle|nla)_PCA1_ablated_\d{4}\.json', name)]
    metadata = {'jobs/STAGE_SEAL.json', 'jobs/oracle_STAGE_SEAL.json', 'jobs/nla_STAGE_SEAL.json'}
    require(len(batches) == 130 and all(name in batches or name in metadata for name in jobs),
            'exact65 original batches per reader and stage metadata only')
    return sorted(batches)


def make_units(records, packets, regex):
    validate_grid([dict(id=x['id'], item_id=x['unit_id'], reader=x['reader'], layer=x['layer'], readout=x['text'])
                   for ref, x in records], packets)
    units, resolved, joins = [], [], []
    for ref, record in records:
        require(record['condition'] == 'PCA1_ablated' and record['repeat'] == 0, 'only new greedy PCA1 readout')
        packet = packets[record['unit_id']]
        ident = opaque('E112', 'native', record['id'])
        if packet['headline_scorer'] == 'regex':
            resolved.append(dict(id=ident, kind='family80_regex', status='CPU_REGEX',
                                 code=regex.score_sample(packet['regex_units'], record['text'])))
        else:
            units.append(dict(id=ident, kind='family80', rubric=None,
                data=dict(id=ident, packet=packet, readout=record['text'])))
        joins.append(dict(id=ident, original_item_id=record['unit_id'], source_id=record['id'],
                          reader=record['reader'], layer=record['layer'], source_ref=ref))
    require(len(units)+len(resolved) == len(joins) == 1036 and len({x['id'] for x in joins}) == 1036,
            'all1036 original new readouts retained once')
    return units, resolved, joins


def prepare(root, expected):
    for name, digest in read(HERE/'E112_DRIVER_SOURCE_SEAL.json')['files'].items():
        require(sha(ROOT/name) == digest, 'published E112 intake/driver source')
    root = Path(root).resolve()
    seal = verify(root/'OUTPUT_SEAL.json', expected)
    require(seal['experiment'] == 'E112' and seal['status'] == 'COMPLETE' and seal['synthetic'] is False and
            seal['vector_seal_sha256'] == 'a356cc5a0a96dac3a12c6fbcfa9a8feafc690420ccf6ef5c7f17e684b37e559d',
            'complete original PCA1 source and pre-GPU vector lineage')
    route_path = ROOT/'results/g_agreement/understand/blind_judge/e80_channel/ROUTE_SEAL.json'
    require(sha(route_path) == read(HERE/'E112_INTAKE.json')['expected_original_route_seal_sha256'], 'original E80 family route')
    route = read(route_path)
    packet_path = Path(route['wtext_source'])/'cache/export_2026-10-28_v3/JUDGES.PRIVATE.json'
    require(sha(packet_path) == route['judge_packets_sha256'], 'exact original518 E80 judge packets')
    packets = {x['id']: x for x in read(packet_path)}
    _, regex = load_renderers(route)
    records = []
    for member in native_members(seal['files']):
        rows = read(root/member)
        require(type(rows) is list, 'original native batch')
        records.extend((dict(member=member, keys=[i, 'text']), x) for i, x in enumerate(rows))
    units, resolved, joins = make_units(records, packets, regex)
    dest = CACHE/'E112/pca1_family_units'
    dest.mkdir(parents=True, exist_ok=True)
    dest.chmod(0o700)
    if (dest/'UNIT_SEAL.json').exists():
        verify(dest/'UNIT_SEAL.json', sha(dest/'UNIT_SEAL.json'))
        require(read(dest/'UNITS.json') == units and read(dest/'CPU_REGEX_CODES.PRIVATE.json') == resolved, 'immutable original E112 units')
        return dest
    write(dest/'UNITS.json', units)
    write(dest/'CPU_REGEX_CODES.PRIVATE.json', resolved)
    write(dest/'SOURCE_POINTERS.PRIVATE.json', joins)
    write(dest/'CUSTODY.json', dict(issuer='W-internals-C', original_source_owner='Track Q', experiment='E112',
        verified=True, complete_eligible_native_grid=True, labels_cpu_only=True, original_arms_rejudged=False,
        original_E80_families_unchanged=True, paid_family_units=len(units), cpu_regex_units=len(resolved),
        original_packet_sha256=sha(packet_path), original_route_sha256=sha(route_path),
        source_seals=[dict(seal=str(root/'OUTPUT_SEAL.json'), sha256=expected)]))
    write(dest/'UNIT_SEAL.json', dict(experiment='E112', n=1036,
        files={n: sha(dest/n) for n in ('UNITS.json', 'CPU_REGEX_CODES.PRIVATE.json', 'SOURCE_POINTERS.PRIVATE.json', 'CUSTODY.json')}))
    write(dest/'PREPARE_SPEC.json', dict(bank='E112', unit_seal=str(dest/'UNIT_SEAL.json'),
        unit_sha256=sha(dest/'UNIT_SEAL.json'), phase_name='pca1_family'))
    return dest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native-root', type=Path, required=True)
    p.add_argument('--native-sha256', required=True)
    args = p.parse_args();dest = prepare(args.native_root, args.native_sha256)
    print('E112 full family unit seal '+sha(dest/'UNIT_SEAL.json'))
