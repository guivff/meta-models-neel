"""Complete E114 original504 Oracle readouts to exact original E57 blind units."""
import argparse
from pathlib import Path
from .runner import CACHE
from .transport import ROOT, HERE
from .banks import opaque
from .e114_channel import RUBRIC_SHA
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require


def make_units(records, values, rubric):
    by = {x['id']: x for x in values}
    require(len(by) == len(values) == len(records) == 504 and
            {x['id'] for _, x in records} == set(by), 'exact504 original native/value identities')
    units, joins = [], []
    for ref, record in records:
        source = by[record['id']]
        require(type(record['output']['text']) is str and type(source['property']) is str and
                set(source['values']) == {'A', 'B'}, 'exact original native text and E57 candidate mapping')
        ident = opaque('E114', 'native', record['id'])
        units.append(dict(id=ident, kind='original57', rubric=rubric,
            data=dict(id=ident, property=source['property'], values=source['values'], readout=record['output']['text'])))
        joins.append(dict(id=ident, original_public_id=record['id'], source_ref=ref))
    require(len({x['id'] for x in units}) == 504, 'no duplicate native record')
    return units, joins


def prepare(root, expected):
    manifest = HERE/'E114_INTAKE_SOURCE_SEAL.json'
    for name, digest in read(manifest)['files'].items():
        require(sha(ROOT/name) == digest, 'published E114 intake source')
    root = Path(root).resolve()
    seal = verify(root/'OUTPUT_SEAL.json', expected)
    require(seal['experiment'] == 'E114' and seal['status'] == 'COMPLETE', 'complete original E114 source')
    source = ROOT/'results/g_agreement/understand/e114/JUDGE_SOURCE_SEAL.json'
    verify(source, sha(source))
    receipt = read(source.parent/'JUDGE_SOURCE_RECEIPT.json')
    values = Path(receipt['private_judge_values']['path'])
    require(sha(values) == receipt['private_judge_values']['sha256'], 'original504 E57 values/CPU gold source unchanged')
    rubric = source.parent/'JUDGE_RUBRIC_COPY.md'
    require(sha(rubric) == receipt['rubric_sha256'] == RUBRIC_SHA, 'exact original E57 rubric')
    records = []
    for member in sorted(seal['files']):
        if member.startswith('oracle/') and member.endswith('.json') and not member.endswith('STAGE_SEAL.json'):
            rows = read(root/member)
            require(type(rows) is list, 'original greedy batch records')
            records.extend((dict(member=member, keys=[i, 'output', 'text']), x) for i, x in enumerate(rows))
    units, joins = make_units(records, read(values), rubric.read_text())
    dest = CACHE/'E114/original57_units'
    dest.mkdir(parents=True, exist_ok=True)
    dest.chmod(0o700)
    if (dest/'UNIT_SEAL.json').exists():
        verify(dest/'UNIT_SEAL.json', sha(dest/'UNIT_SEAL.json'))
        require(read(dest/'UNITS.json') == units, 'immutable full E114 units')
        return dest
    write(dest/'UNITS.json', units)
    write(dest/'SOURCE_POINTERS.PRIVATE.json', joins)
    write(dest/'CUSTODY.json', dict(issuer='W-internals-C', original_source_owner='I-2', experiment='E114',
        verified=True, complete_eligible_native_grid=True, labels_cpu_only=True, original_gold_unchanged=True,
        native_oracle44_only=True, original_E57_rubric_sha256=RUBRIC_SHA, original_private_values_sha256=sha(values),
        intake_source_manifest_sha256=sha(manifest), source_seals=[dict(seal=str(root/'OUTPUT_SEAL.json'), sha256=expected),
            dict(seal=str(source), sha256=sha(source))]))
    write(dest/'UNIT_SEAL.json', dict(experiment='E114', n=504,
        files={n: sha(dest/n) for n in ('UNITS.json', 'SOURCE_POINTERS.PRIVATE.json', 'CUSTODY.json')}))
    write(dest/'PREPARE_SPEC.json', dict(bank='E114', unit_seal=str(dest/'UNIT_SEAL.json'),
        unit_sha256=sha(dest/'UNIT_SEAL.json'), phase_name='original57'))
    return dest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native-root', type=Path, required=True)
    p.add_argument('--native-sha256', required=True)
    args = p.parse_args()
    dest = prepare(args.native_root, args.native_sha256)
    print('E114 full original57 unit seal '+sha(dest/'UNIT_SEAL.json'))
