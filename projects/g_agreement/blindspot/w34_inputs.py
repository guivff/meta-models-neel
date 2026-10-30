"""Freeze W3/W4 populations from W1 rule (i), regardless of W1's overall verdict.

Metadata/pair preparation only. All residual maths, pairing and NLA scoring remain
in the immutable P3-reviewed ar_tests.py. No model calls in this module.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
from . import ar_tests as AR, protocol as P

BLINDSPOT_ROWS = tuple('json_type latex_environment latex_section list_depth list_index prose_paren prose_quote prose_sentence python_argument python_comment python_depth python_indent python_string table_column table_role table_row'.split())
AUTHORITY = 'Guiv: use the 16 W1 rule-(i) rows as registered despite W1 overall NOT MET; NLA donor-following remains an open test.'


def population(rule_i, metrics):
    features = rule_i['features']
    if (len(features) != 16 or set(features) != set(BLINDSPOT_ROWS)
        or set(metrics['w1']['blindspot_features']) != set(BLINDSPOT_ROWS)
        or rule_i['w1_verdict'] != metrics['w1']['status']):
        raise ValueError('W1 rule-(i) export differs from the registered 16-row population')
    oracle = {r['feature']: r for r in metrics['rows'] if r['reader'] == 'olens' and r['layer'] == 44}
    if any(oracle[f]['status'] != 'EVALUABLE' or oracle[f]['class'] not in ('count-like', 'state-like') for f in features):
        raise ValueError('registered blind-spot row lacks Oracle evaluability')
    semantic = sorted(f for f, r in oracle.items() if r['class'] == 'semantic' and r['status'] == 'EVALUABLE')
    if not semantic:
        raise ValueError('no evaluable semantic controls')
    excluded = [{'feature': f, 'reason': r['status']} for f, r in sorted(oracle.items())
                if r['class'] == 'semantic' and r['status'] != 'EVALUABLE']
    return sorted(features), semantic, excluded


def prepare(a):
    items, h = AR._target(a.bank, a.target)
    seal = P.verify(a.w1, 'ANALYSIS_SEAL.json')
    required = {'metrics.json', 'probe_directions.json', 'probe_directions.npz', 'rule_i_rows.json', 'activations.json'}
    if not required <= set(seal['files']):
        raise ValueError('W1 analysis seal must cover the final rule-(i) and activation exports')
    metrics, rule_i = AR._read(a.w1/'metrics.json'), AR._read(a.w1/'rule_i_rows.json')
    if (metrics['input_seal_sha256'] != P.sha(a.bank/'INPUT_SEAL.json')
        or P.sha(a.target/'SCORE_SEAL.json') not in metrics['reader_seals']
        or rule_i['metrics_sha256'] != P.sha(a.w1/'metrics.json')):
        raise ValueError('W1 bank/target/metrics lineage mismatch')
    blind, semantic, excluded = population(rule_i, metrics)
    selected = blind + semantic
    all_definitions = AR.definitions_from_bank(a.bank)
    definitions = {f: all_definitions[f] for f in selected}
    cells = {(r['feature'], r['reader'], r['layer']): r for r in metrics['rows']}
    meta = AR._read(a.w1/'probe_directions.json')
    if meta['fit_split'] != 'dev':
        raise ValueError('directions must be dev-only')
    rows, directions = [], {}
    with np.load(a.w1/'probe_directions.npz', allow_pickle=False) as arrays:
        for f in selected:
            o, n = cells[f, 'olens', 44], cells[f, 'nla', 42]
            matches = [r for r in meta['rows'] if r['feature'] == f and r['layer'] == 44]
            if len(matches) != 1:
                raise ValueError('missing/duplicate block44 direction')
            dm = matches[0]
            if (dm['fit_split'] != 'dev' or dm['orientation_flipped'] is not False
                or dm['positive_value'] != definitions[f]['values'][0]):
                raise ValueError('direction provenance mismatch')
            directions[f] = arrays[dm['array_prefix']+'__unit']
            rows.append({'feature': f, 'row_class': definitions[f]['row_class'], 'evaluable': True,
                'blindspot': f in blind, 'probe_auroc': o['probe_auroc'], 'oracle_auroc': o['true']['auroc'],
                'nla_evaluable': n['status'] == 'EVALUABLE', 'oracle_mismatched_auroc': o['mismatched']['auroc']})
    labels = AR._labels(a.bank, a.labels, items)
    for item in items:
        row = labels[item['id']]
        row['template_family'] = row['cluster']; row['length_bin'] = len(item['ids'])//8
    # Use the reviewed pairing function on the complete original item/random pool.
    # No NLA-success filter and no W1-overall two-pilot fallback.
    pairs = AR.prepare_swap_pairs(items, labels, selected)
    templates = AR._read(a.bank/'templates.json')
    if any(len(templates[f]['nla']) < 2 for f in selected):
        raise ValueError('missing original W1 asked phrasings')
    a.out.mkdir(parents=True, exist_ok=False)
    reference = a.out/'reference'; reference.mkdir()
    P.dump(reference/'definitions.json', definitions); P.dump(reference/'rows.json', rows)
    np.savez(reference/'directions.npz', **directions)
    lineage = {'input_seal_sha256': P.sha(a.bank/'INPUT_SEAL.json'),
        'target_score_seal_sha256': P.sha(a.target/'SCORE_SEAL.json'),
        'w1_analysis_seal_sha256': P.sha(a.w1/'ANALYSIS_SEAL.json'),
        'direction_space': 'raw_block44', 'w1_status': metrics['w1']['status'],
        'inference_scope': 'REGISTERED_RULES_W1_I_ROWS', 'authority': AUTHORITY}
    P.dump(reference/'provenance.json', lineage)
    P.seal(reference, ['definitions.json', 'rows.json', 'directions.npz', 'provenance.json'], 'INPUTS_FROZEN_MECHANISM_REFERENCE')
    AR._reference(reference, a.bank, a.target)
    plan = a.out/'pair_plan'; plan.mkdir()
    P.jsonl(plan/'pairs.input.jsonl', pairs)
    P.dump(plan/'templates.json', {f: templates[f] for f in selected})
    P.dump(plan/'definitions.json', definitions)
    P.dump(plan/'provenance.json', {**lineage, 'reference_seal_sha256': P.sha(reference/'INPUT_SEAL.json'),
        'length_bin_width': 8, 'seed': P.SEED, 'pairing': '40 directed opposite-value test pairs per row; same domain/template/length bin',
        'random_control': 'complete original same-domain item pool excluding i/j; value ignored', **AR.SITE})
    P.seal(plan, ['pairs.input.jsonl', 'templates.json', 'definitions.json', 'provenance.json'], 'INPUTS_FROZEN_W4_PAIR_PLAN_PENDING_RESIDUAL_SEAL')
    P.dump(a.out/'POPULATION.json', {'blindspot_features': blind, 'semantic_features': semantic,
        'excluded_semantic': excluded, 'n_pairs': len(pairs), 'pairs_per_row': 40,
        'w1_status': metrics['w1']['status'], 'nla_donor_following': 'OPEN_TEST',
        'inference_scope': 'REGISTERED_RULES_W1_I_ROWS', 'authority': AUTHORITY,
        'reference_seal_sha256': P.sha(reference/'INPUT_SEAL.json'), 'pair_plan_seal_sha256': P.sha(plan/'INPUT_SEAL.json')})


def bind_swaps(a):
    """Bind pre-frozen pair bytes to real W3 residuals; never regenerate pairs."""
    items, h = AR._target(a.bank, a.target)
    AR._residuals(a.residuals, a.bank, a.target, items, h)
    seal = P.verify(a.plan, 'INPUT_SEAL.json')
    if set(seal['files']) != {'pairs.input.jsonl', 'templates.json', 'definitions.json', 'provenance.json'}:
        raise ValueError('pair plan seal incomplete')
    p = AR._read(a.plan/'provenance.json')
    if (p['input_seal_sha256'] != P.sha(a.bank/'INPUT_SEAL.json')
        or p['target_score_seal_sha256'] != P.sha(a.target/'SCORE_SEAL.json')):
        raise ValueError('pair plan source mismatch')
    a.out.mkdir(parents=True, exist_ok=False)
    for name in ('pairs.input.jsonl', 'templates.json', 'definitions.json'):
        (a.out/name).write_bytes((a.plan/name).read_bytes())
    P.dump(a.out/'provenance.json', {**p, 'residual_score_seal_sha256': P.sha(a.residuals/'SCORE_SEAL.json'),
        'pair_plan_seal_sha256': P.sha(a.plan/'INPUT_SEAL.json')})
    P.seal(a.out, ['pairs.input.jsonl', 'templates.json', 'definitions.json', 'provenance.json'], 'INPUTS_FROZEN_CAUSAL_SWAP')
    from types import SimpleNamespace
    AR._swap_inputs(SimpleNamespace(bank=a.bank,target=a.target,pairs=a.out,residuals=a.residuals), items, h)



def compact_indices(items, labels, rows, pairs):
    """All registered test items plus the already-frozen random-donor support."""
    features = {r['feature'] for r in rows}
    test = {i for i,it in enumerate(items) if it['feature'] in features and labels[it['id']]['split']=='test'}
    used = test | {p[k] for p in pairs for k in ('recipient','donor','random')}
    order = sorted(used); remap = {old:new for new,old in enumerate(order)}
    mapped = [{**p,**{k:remap[p[k]] for k in ('recipient','donor','random')}} for p in pairs]
    return order, mapped, test


def compact(a):
    """Derive label-free collection inputs without dropping a test ID or re-drawing donors."""
    items,h = AR._target(a.bank,a.target)
    definitions,rows,_ = AR._reference(a.prepared/'reference',a.bank,a.target)
    plan = a.prepared/'pair_plan'; P.verify(plan,'INPUT_SEAL.json')
    p = AR._read(plan/'provenance.json')
    if p['input_seal_sha256'] != P.sha(a.bank/'INPUT_SEAL.json') or p['target_score_seal_sha256'] != P.sha(a.target/'SCORE_SEAL.json'):
        raise ValueError('parent plan/bank/target mismatch')
    pairs = P.rows(plan/'pairs.input.jsonl')
    labels = AR._labels(a.bank,a.labels,items)
    order,mapped,test = compact_indices(items,labels,rows,pairs)
    a.out.mkdir(parents=True,exist_ok=False)
    label_file=a.out/'labels.DO_NOT_STAGE.jsonl';P.jsonl(label_file,[labels[items[i]['id']] for i in order])
    bank,target,reference,newplan = [a.out/n for n in ('bank','target','reference','pair_plan')]
    for directory in (bank,target,reference,newplan): directory.mkdir()
    P.jsonl(bank/'items.input.jsonl',[items[i] for i in order])
    (bank/'templates.json').write_bytes((a.bank/'templates.json').read_bytes())
    P.dump(bank/'provenance.json',{'labels_sha256':P.sha(label_file),'parent_input_seal_sha256':P.sha(a.bank/'INPUT_SEAL.json'),
        'selection':'all25registered rows test IDs plus fixed full-pool W4 donor support;no donor redraw or test subsampling'})
    P.seal(bank,['items.input.jsonl','templates.json','provenance.json'],'INPUTS_FROZEN_W34_COLLECTION')
    np.save(target/'acts44.npy',h[order].numpy(),allow_pickle=False)
    P.dump(target/'items.order.json',[items[i]['id'] for i in order])
    P.dump(target/'provenance.target.json',{'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),
        'parent_score_seal_sha256':P.sha(a.target/'SCORE_SEAL.json'),'parent_acts44_sha256':P.sha(a.target/'acts44.npy'),
        'parent_indices':order,'space':'raw_block44','transform':'row selection only;no centring,whitening or rescaling'})
    P.seal(target,['acts44.npy','items.order.json','provenance.target.json'],'SCORES_SEALED_DERIVED_W1_ACTIVATIONS')
    for name in ('definitions.json','rows.json','directions.npz'):
        (reference/name).write_bytes((a.prepared/'reference'/name).read_bytes())
    provenance=AR._read(a.prepared/'reference/provenance.json')
    lineage={'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),'target_score_seal_sha256':P.sha(target/'SCORE_SEAL.json')}
    P.dump(reference/'provenance.json',{**provenance,**lineage,'parent_reference_seal_sha256':P.sha(a.prepared/'reference/INPUT_SEAL.json')})
    P.seal(reference,['definitions.json','rows.json','directions.npz','provenance.json'],'INPUTS_FROZEN_MECHANISM_REFERENCE')
    P.jsonl(newplan/'pairs.input.jsonl',mapped)
    for name in ('templates.json','definitions.json'):(newplan/name).write_bytes((plan/name).read_bytes())
    P.dump(newplan/'provenance.json',{**p,**lineage,'reference_seal_sha256':P.sha(reference/'INPUT_SEAL.json'),
        'parent_pair_plan_seal_sha256':P.sha(plan/'INPUT_SEAL.json'),'index_remap':'original sorted row subset;recipient/donor/random IDs unchanged'})
    P.seal(newplan,['pairs.input.jsonl','templates.json','definitions.json','provenance.json'],'INPUTS_FROZEN_W4_PAIR_PLAN_PENDING_RESIDUAL_SEAL')
    AR._target(bank,target);AR._reference(reference,bank,target)
    for old,new in zip(pairs,mapped):
        assert old['id']==new['id'] and all(items[old[k]]['id']==items[order[new[k]]]['id'] for k in ('recipient','donor','random'))
    P.dump(a.out/'COLLECTION.json',{'n_collection_items':len(order),'n_registered_test_items':len(test),
        'n_support_items':len(set(order)-test),'n_pairs':len(pairs),'n_rows':len(rows),
        'parent_indices':order,'test_indices':[order.index(i) for i in sorted(test)],
        'source_bank_seal_sha256':P.sha(a.bank/'INPUT_SEAL.json'),'source_target_seal_sha256':P.sha(a.target/'SCORE_SEAL.json'),
        'private_labels_local':str(label_file.resolve()),'private_labels_sha256':P.sha(label_file),
        'label_staging':'DO_NOT_STAGE;integrator runs W3 probes and W4 labels joins locally after upstream score sealing',
        'collection_bank_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),'collection_target_seal_sha256':P.sha(target/'SCORE_SEAL.json'),
        'reference_seal_sha256':P.sha(reference/'INPUT_SEAL.json'),'pair_plan_seal_sha256':P.sha(newplan/'INPUT_SEAL.json')})

def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='action',required=True)
    for name, fields in [('prepare',('bank','target','w1','labels','out')),('bind-swaps',('bank','target','residuals','plan','out')),('compact',('bank','target','prepared','labels','out'))]:
        command = sub.add_parser(name)
        for field in fields: command.add_argument('--'+field,type=Path,required=True)
    a=p.parse_args(); {'prepare':prepare,'bind-swaps':bind_swaps,'compact':compact}[a.action](a)


if __name__ == '__main__': main()
