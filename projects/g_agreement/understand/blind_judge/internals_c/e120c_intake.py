"""Complete targeted/sham native800 to original judge205; no yes/no rescorer."""
import argparse
from pathlib import Path
from .runner import CACHE
from .transport import ROOT, HERE
from .banks import opaque
from ..privacy79 import redact
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require


def make_units(records, items, contexts):
    public = {x['id']: (i, x) for i, x in enumerate(items)}
    require(len(public) == len(items) == 400 and set(public) == set(contexts), 'exact400 original TEST items and source contexts')
    require(len(records) == 800 and len({r['id'] for _, r in records}) == 800, 'all800 unique native outputs')
    seen, units, joins = set(), [], []
    for source_ref, r in records:
        key = r['item_id'], r['condition']
        require(key not in seen and key[0] in public and key[1] in ('targeted', 'sham') and
                r['reader'] == 'oracle' and r['source_layer'] == 44 and type(r['text']) is str,
                'one exact original Oracle44 readout per item/arm')
        seen.add(key); ident = opaque('E120', 'part_c', r['id'])
        text, context_ref = contexts[r['item_id']]
        units.append(dict(id=ident, kind='eval85', rubric=None,
            data=dict(id=ident, source_text=text, readout=r['text'])))
        joins.append(dict(id=ident, item_id=r['item_id'], arm=r['condition'], native_id=r['id'],
            input_index=public[r['item_id']][0], source_ref=source_ref, context_ref=context_ref))
    require(seen == {(i, a) for i in public for a in ('targeted', 'sham')}, 'complete two-arm census, no partial stitching')
    by = {u['id']: u for u in units}
    return [by[k] for k in sorted(by)], sorted(joins, key=lambda x: x['id'])


def prepare():
    for name, digest in read(HERE/'E120c_INTAKE_SOURCE_SEAL.json')['files'].items():
        require(sha(ROOT/name) == digest, 'published E120c intake/source')
    report = ROOT/'projects/g_agreement/e120c_analysis/SOURCE_RECEIPT.json'
    for name, digest in read(report)['files'].items(): require(sha(ROOT/name) == digest, 'owner tested source precedes opening')
    native = ROOT.parent/'wt-wmech/cache/g_agreement/understand/analysis402_verified/E120/c/out/OUTPUT_SEAL.json'
    ns = verify(native, '813f2ae98281dcaa5181943caaaf871dc2c91009c4e96d1592152382e17fe130')
    require(ns['experiment'] == 'E120' and ns['status'] == 'COMPLETE' and
            ns['input_sha256'] == '8f295cd6003616ae2b64d923dc44d35a7186dfd20e2220d22df2345e0c1dcf8a', 'complete original E120c only')
    inputs = ROOT.parent/'outputs/e120c-inputs-v1/inputs/INPUT_SEAL.json'; verify(inputs, ns['input_sha256'])
    source = CACHE/'E85/native_eval_units/UNIT_SEAL.json'
    verify(source, '0fbabe81a4fcb0c37226cbe83017e91528966577376da81e00dcf261d245e484')
    old = read(source.parent/'UNITS.json'); by = {x['id']: (i, x) for i, x in enumerate(old) if x['kind'] == 'eval85'}
    contexts = {}
    for j in read(source.parent/'SOURCE_POINTERS.PRIVATE.json'):
        i, unit = by[j['id']]
        if j['reader'] == 'oracle':
            require(j['unit_id'] not in contexts, 'one original Oracle context per item')
            contexts[j['unit_id']] = (unit['data']['source_text'], dict(seal=str(source), sha256=sha(source), member='UNITS.json', keys=[i, 'data', 'source_text']))
    records = []
    for member in ns['files']:
        if not member.startswith('jobs/') or not member.endswith('.json'): continue
        for i, r in enumerate(read(native.parent/member)):
            records.append((dict(seal=str(native), sha256=sha(native), member=member, keys=[i, 'text']), r))
    units, joins = make_units(records, read(inputs.parent/'items.json'), contexts)
    raw = [dict(id=u['id'], readout=u['data']['readout']) for u in units]
    copied, audit = redact(raw, 'E120', addresses=True); copied = {x['id']: x['readout'] for x in copied}
    affected = {x['id'] for x in audit['affected']}; evidence = {x['id']: x['readout'] for x in raw if x['id'] in affected}
    units = [dict(u, data=dict(u['data'], readout=copied[u['id']])) for u in units]
    dest = CACHE/'E120/targeted_sham_units'; dest.mkdir(parents=True, exist_ok=True); dest.chmod(0o700)
    if (dest/'UNIT_SEAL.json').exists():
        verify(dest/'UNIT_SEAL.json', sha(dest/'UNIT_SEAL.json')); require(read(dest/'UNITS.json') == units, 'immutable full800 E120c source'); return dest
    for n, v in [('UNITS.json', units), ('SOURCE_POINTERS.PRIVATE.json', joins), ('PATH_REDACTION_AUDIT.json', audit), ('ORIGINAL_EVIDENCE.PRIVATE.json', evidence)]: write(dest/n, v)
    write(dest/'CUSTODY.json', dict(experiment='E120', part='c', issuer='W-internals-C', original_source_owner='Track Q', verified=True,
        complete_eligible_native_grid=True, labels_cpu_only=True, full_original_source_text=True, native_oracle44_only=True,
        original_E85_rejudged=False, sham_scoring='owner a77885ae1 yes-response rate; no C analysis or guessed no',
        source_seals=[dict(seal=str(native), sha256=sha(native)), dict(seal=str(inputs), sha256=sha(inputs)), dict(seal=str(source), sha256=sha(source))]))
    write(dest/'UNIT_SEAL.json', dict(experiment='E120', part='c', n=800,
        files={n: sha(dest/n) for n in ('UNITS.json', 'SOURCE_POINTERS.PRIVATE.json', 'CUSTODY.json', 'PATH_REDACTION_AUDIT.json', 'ORIGINAL_EVIDENCE.PRIVATE.json')}))
    write(dest/'PREPARE_SPEC.json', dict(bank='E120', unit_seal=str(dest/'UNIT_SEAL.json'), unit_sha256=sha(dest/'UNIT_SEAL.json'), phase_name='targeted_sham'))
    return dest


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print('E120c full800 units '+sha(prepare()/'UNIT_SEAL.json'))
