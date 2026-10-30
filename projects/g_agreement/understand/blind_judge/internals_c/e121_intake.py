"""Literal complete E121 NLA source + frozen original E104 candidates; no scores."""
import argparse
from pathlib import Path
from .runner import CACHE
from .transport import ROOT, HERE
from .banks import opaque
from .e121_channel import RUBRIC_SHA
from ..privacy79 import redact
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require


def make_units(records, original, items, rubric):
    candidates = {(x['item_id'], x['condition']): (i, x) for i, x in enumerate(original)
        if x['arm'] == 'U' and x['row'] == 'fact_recall' and x['reader'] == 'oracle'}
    cohort = {x['item_id'] for x in original if x['arm'] == 'U' and x['row'] == 'fact_recall'
        and x['reader'] == 'oracle' and x['condition'] == 'steered' and x['flipped'] is True}
    require(len(cohort) == 84 and len(candidates) == 168, 'exact original84 flipped fact cohort/two conditions')
    public = {x['id']: x for x in items}
    require(len(public) == len(items) == len(records) == 168 and
            len({x['id'] for _, x in records}) == 168 and {x['item_id'] for _, x in records} == set(public),
            'complete168 native readout IDs and explicit source item_id/input identities')
    require({(x['base_id'], x['condition']) for x in items} == {(i, a) for i in cohort for a in ('steered', 'random')}, 'no new cohort or condition selection')
    units, joins = [], []
    for native_ref, x in records:
        item = public[x['item_id']]
        key = (item['base_id'], item['condition'])
        original_index, o = candidates[key]
        require(x['base_id'] == item['base_id'] and x['condition'] == item['condition'] and
                x['reader'] == 'nla' and x['source_layer'] == 42 and item['alpha'] == o['alpha'] == 8 and
                item['row'] == o['row'] == 'fact_recall', 'same original hook/cohort and actual native NLA42')
        require(type(x['text']) is str and set(o['values']) == {'A', 'B'}, 'literal native string and unchanged candidates')
        ident = opaque('E121', 'nla', x['id'])
        units.append(dict(id=ident, kind='original104', rubric=rubric,
            data=dict(id=ident, property=o['property'], values=o['values'], readout=x['text'])))
        joins.append(dict(id=ident, item_id=item['base_id'], condition=item['condition'], native_id=x['id'],
            source_input_id=x['item_id'], reader='nla', row='fact_recall', original_E104_id=o['id'], original_E104_judgment_id=o['opaque_id'],
            original_private_index=original_index, source_ref=native_ref, steered_letter=o['target'],
            original_values=o['values'], malformed=x.get('malformed'), truncated=x.get('truncated')))
    require(len({x['id'] for x in units}) == 168, 'unique complete units')
    order = {x['id']: x for x in units}
    return [order[k] for k in sorted(order)], sorted(joins, key=lambda x: x['id'])


def prepare():
    for name, digest in read(HERE/'E121_INTAKE_SOURCE_SEAL.json')['files'].items():
        require(sha(ROOT/name) == digest, 'published E121 intake source')
    # Owner scientific adapter was committed before this complete native bank.
    report = ROOT/'projects/g_agreement/e121_analysis/SOURCE_RECEIPT.json'
    for name, digest in read(report)['files'].items(): require(sha(ROOT/name) == digest, 'published owner E121 adapter closure')
    native = ROOT.parent/'wt-i2/cache/g_agreement/i2/parallel_gpu230/e121-measured-r1/terminal_pull/outputs/OUTPUT_SEAL.json'
    ns = verify(native, '660cb2a8d24be49a4a4629202f56707e953f6d6cc08776143856606eda61cfb3')
    require(ns['experiment'] == 'E121' and ns['status'] == 'COMPLETE' and
            ns['input_sha256'] == '755154672e006d2ded2b6f0479d22a6fe9a8c511421daf2c8aeb3e5ec2bbc038', 'only final complete measured E121 attempt')
    inputs = ROOT.parent/'outputs/e121-inputs-v1/inputs/INPUT_SEAL.json'
    verify(inputs, ns['input_sha256'])
    old = ROOT.parent/'wt-internals-b/cache/g_agreement/understand/funded_queue/E104'
    ps = verify(old/'PRIVATE_SEAL.json', '0f42d78d151a85b858f2b02a13307e62e74f987ad0bba009cab875b6792aa3c6')
    require(sha(old/'PRIVATE.json') == '495bbb19179f507869779d611c737ac82181f8c404054fcffd6963b7615fd0e4', 'original E104 private source unchanged')
    blind = old/'blind/BLIND_SEAL.json'; verify(blind, '1e0df9accd2f19fd042387701c385a1a6d4b2d2e0e700e27421fc4bc9de64b0d')
    rubric = old/'blind/RUBRIC.md'; require(sha(rubric) == RUBRIC_SHA, 'exact original E104 rubric03d9377b, not amended E82')
    records = []
    for member in ns['files']:
        if not member.startswith('jobs/') or not member.endswith('.json'): continue
        for i, x in enumerate(read(native.parent/member)):
            if x.get('reader') == 'nla': records.append((dict(seal=str(native), sha256=sha(native), member=member, keys=[i, 'text']), x))
    units, joins = make_units(records, read(old/'PRIVATE.json'), read(inputs.parent/'items.json'), rubric.read_text())
    original_targets_cfg = read(ROOT/'results/g_agreement/understand/blind_judge/e101_bank/INPUTS.json')
    target_seal = Path(original_targets_cfg['targets'])
    verify(target_seal, original_targets_cfg['targets_sha256'])
    original_labels = read(target_seal.parent/'ORIGINAL_IDS.json')
    for j in joins:
        label = original_labels[j['item_id']]['label']
        require(label in (0, 1), 'original binary candidate orientation')
        j['old_letter'] = 'A' if label == 1 else 'B'
        require(j['old_letter'] != j['steered_letter'], 'same original old/opposite target encoding')
        j['old_label_ref'] = dict(seal=str(target_seal), sha256=sha(target_seal), member='ORIGINAL_IDS.json', keys=[j['item_id'], 'label'])
    primary = [x['data'] for x in units]
    copies, audit = redact(primary, 'E121', addresses=True)
    by = {x['id']: x for x in copies}
    affected = {x['id'] for x in audit['affected']}
    evidence = {x['id']: x['readout'] for x in primary if x['id'] in affected}
    units = [dict(u, data=by[u['id']]) for u in units]
    dest = CACHE/'E121/original104_units'; dest.mkdir(parents=True, exist_ok=True); dest.chmod(0o700)
    if (dest/'UNIT_SEAL.json').exists():
        verify(dest/'UNIT_SEAL.json', sha(dest/'UNIT_SEAL.json'))
        require(read(dest/'UNITS.json') == units, 'immutable exact168 E121 source')
        return dest
    write(dest/'UNITS.json', units); write(dest/'SOURCE_POINTERS.PRIVATE.json', joins)
    write(dest/'PATH_REDACTION_AUDIT.json', audit); write(dest/'ORIGINAL_EVIDENCE.PRIVATE.json', evidence)
    write(dest/'CUSTODY.json', dict(issuer='W-internals-C', original_source_owner='I-2', experiment='E121', verified=True,
        complete_eligible_native_grid=True, labels_cpu_only=True, original_candidates_unchanged=True,
        original_E104_rubric_sha256=RUBRIC_SHA, native_nla42_only=True, original_oracle_rejudged=False,
        source_seals=[dict(seal=str(native), sha256=sha(native)), dict(seal=str(inputs), sha256=sha(inputs)),
            dict(seal=str(old/'PRIVATE_SEAL.json'), sha256=sha(old/'PRIVATE_SEAL.json')), dict(seal=str(blind), sha256=sha(blind)),
            dict(seal=str(target_seal), sha256=sha(target_seal))],
        old_letter_encoding='original e101 frozen candidate A is label1; old letter A iff original label1 else B; steered target remains opposite'))
    write(dest/'UNIT_SEAL.json', dict(experiment='E121', n=168,
        files={n: sha(dest/n) for n in ('UNITS.json', 'SOURCE_POINTERS.PRIVATE.json', 'CUSTODY.json', 'PATH_REDACTION_AUDIT.json', 'ORIGINAL_EVIDENCE.PRIVATE.json')}))
    write(dest/'PREPARE_SPEC.json', dict(bank='E121', unit_seal=str(dest/'UNIT_SEAL.json'), unit_sha256=sha(dest/'UNIT_SEAL.json'), phase_name='original104'))
    return dest


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print('E121 complete original104 units '+sha(prepare()/'UNIT_SEAL.json'))
