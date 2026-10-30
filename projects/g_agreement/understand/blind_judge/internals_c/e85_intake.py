"""All800 sealed E85 native readouts, original source text and seeded200 S6."""
import argparse
import json
import tarfile
from pathlib import Path
from .runner import CACHE
from .transport import ROOT, HERE
from .banks import opaque
from ..privacy79 import redact
from ..rubric202 import original_ids
from ..later_runner import S6_RUBRIC_SHA
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require


def make_units(public, records, rubric):
    by = {x['id']: x for x in public if x['reader_allowed'] is True}
    require(len(by) == 400 and all(x['split'] == 'test' for x in by.values()), 'original released400 TEST inputs')
    seen = set()
    raw, joins = [], []
    for ref, record in records:
        key = (record['unit_id'], record['reader'])
        require(key not in seen and key[0] in by and key[1] in ('oracle', 'nla') and
                record['repeat'] == 0 and type(record['text']) is str, 'one original greedy readout per TEST item/reader')
        seen.add(key)
        ident = opaque('E85', 'native', record['id'])
        raw.append(dict(id=ident, readout=record['text']))
        joins.append(dict(id=ident, unit_id=record['unit_id'], reader=record['reader'], source_id=record['id'], source_ref=ref))
    require(seen == {(i, r) for i in by for r in ('oracle', 'nla')} and len(raw) == 800, 'all800 full native grid')
    copies, audit = redact(raw, 'E85', addresses=True)
    raw_by = {x['id']: x['readout'] for x in raw}
    original = {x['id']: raw_by[x['id']] for x in audit['affected']}
    copies = {x['id']: x['readout'] for x in copies}
    units = [dict(id=x['id'], kind='eval85', rubric=None,
        data=dict(id=x['id'], source_text=by[x['unit_id']]['prompt'], readout=copies[x['id']])) for x in joins]
    selected = set(original_ids([x['id'] for x in units], 'E85'))
    units += [dict(id=x['id'], kind='s6', rubric=rubric, data=dict(id=x['id'], readout=copies[x['id']]))
              for x in joins if x['id'] in selected]
    return units, joins, audit, original


def prepare(root, expected):
    for name, digest in read(HERE/'E85_RUNTIME_SOURCE_SEAL.json')['files'].items():
        require(sha(ROOT/name) == digest, 'published E85 intake/source pin')
    root = Path(root).resolve();native = root/'OUTPUT_SEAL.json';seal = verify(native, expected)
    require(seal['experiment'] == 'E85' and seal['status'] == 'COMPLETE' and seal['synthetic'] is False,
            'complete original E85 production only')
    owner = ROOT.parent/'wt-wtext/results/g_agreement/understand/e85'
    verify(owner/'BANK_SEAL.json', sha(owner/'BANK_SEAL.json'))
    launch = read(owner/'LAUNCH_REQUEST.json');archive = Path(launch['public_archive'])
    require(sha(archive) == launch['public_archive_sha256'], 'exact frozen public source texts including system')
    with tarfile.open(archive) as tar:
        require(tar.getnames() == ['PUBLIC_INPUTS.json'], 'original single public member')
        public = json.load(tar.extractfile('PUBLIC_INPUTS.json'))
    rubric = HERE/'E85_ORIGINAL_S6_RUBRIC.md'
    require(sha(rubric) == S6_RUBRIC_SHA, 'exact original S6 comparison bytes')
    records = []
    for name in sorted(seal['files']):
        if name.startswith(('oracle/', 'nla/')) and name.endswith('.json') and not name.endswith('STAGE_SEAL.json'):
            rows = read(root/name);require(type(rows) is list, 'original batch')
            records.extend((dict(member=name, keys=[i, 'text']), x) for i, x in enumerate(rows))
    units, joins, audit, original = make_units(public, records, rubric.read_text())
    dest = CACHE/'E85/native_eval_units';dest.mkdir(parents=True, exist_ok=True);dest.chmod(0o700)
    if (dest/'UNIT_SEAL.json').exists():
        verify(dest/'UNIT_SEAL.json', sha(dest/'UNIT_SEAL.json'));require(read(dest/'UNITS.json') == units, 'immutable full E85 units');return dest
    for name, value in [('UNITS.json', units), ('SOURCE_POINTERS.PRIVATE.json', joins), ('PATH_REDACTION_AUDIT.json', audit), ('ORIGINAL_EVIDENCE.PRIVATE.json', original)]:write(dest/name, value)
    write(dest/'CUSTODY.json', dict(issuer='W-internals-C', original_source_owner='I-2', experiment='E85', verified=True,
        complete_eligible_native_grid=True, labels_cpu_only=True, original_S6_rubric_sha256=sha(rubric),
        full_source_text_including_system=True, source_seals=[dict(seal=str(native), sha256=expected),
            dict(seal=str(owner/'BANK_SEAL.json'), sha256=sha(owner/'BANK_SEAL.json'))]))
    write(dest/'UNIT_SEAL.json', dict(experiment='E85', n_primary=800, n_original=200,
        files={p.name:sha(p) for p in dest.iterdir() if p.is_file()}))
    write(dest/'PREPARE_SPEC.json', dict(bank='E85', unit_seal=str(dest/'UNIT_SEAL.json'), unit_sha256=sha(dest/'UNIT_SEAL.json'), phase_name='native_eval'))
    return dest


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--native-root',type=Path,required=True);p.add_argument('--native-sha256',required=True)
    a=p.parse_args();dest=prepare(a.native_root,a.native_sha256);print('E85 full800+200 units '+sha(dest/'UNIT_SEAL.json'))
