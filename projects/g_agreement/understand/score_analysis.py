"""CPU reporting of frozen E6 proxies/E8 gains; no new inference or tuning.

E5 already has its frozen analyser. E6/E8 froze their scoring functions before
capture; this adapter applies them, adds the requested base-rate reporting, and
uses the project's fixed 2,000 cluster resamples. No decision threshold is added.
"""
import argparse
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
import numpy as np
from . import core as K, e6, e8
from projects.g_agreement.blindspot import protocol as P


def verified(experiment, bank, outputs, out):
    bank, outputs, out = map(Path, (bank, outputs, out))
    if out.exists():
        raise ValueError('analysis exists; no repeated analysis')
    P.verify(bank, 'INPUT_SEAL.json')
    P.verify(outputs, 'SCORE_SEAL.json')
    plan = json.loads((bank/'plan.json').read_text())
    provenance = json.loads((outputs/'provenance.json').read_text())
    if plan['experiment'] != experiment or provenance['experiment'] != experiment:
        raise ValueError('experiment mismatch')
    if provenance['input_seal_sha256'] != P.sha(bank/'INPUT_SEAL.json') or provenance['source_files'] != plan['source_files']:
        raise ValueError('source/input lineage mismatch')
    for name, digest in plan['source_files'].items():
        if P.sha(P.ROOT/name) != digest:
            raise ValueError('frozen source mismatch: '+name)
    items = P.rows(bank/'items.input.jsonl')
    raw = P.rows(outputs/'scores.jsonl')
    readers = K.READERS[:2] if experiment == 'E6' else K.READERS
    doses = plan.get('alphas', [0])
    expected = {(x['id'], r, s, a) for x in items for r, s in readers for a in doses}
    keys = [(r['id'], r['reader'], r['layer'], r['alpha']) for r in raw]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError('incomplete/duplicate grid')
    ids = {x['id']: x for x in items}
    for r in raw:
        if r['feature'] != ids[r['id']]['feature']:
            raise ValueError('feature mismatch')
        if r['status'] == 'COMPLETE':
            if experiment == 'E6':
                if not isinstance(r['text'], str) or r['format_status'] != e6.format_status(r['text']):
                    raise ValueError('invalid generation/format marker')
            elif len(r['scores']) != 2 or not np.isfinite(r['scores']).all():
                raise ValueError('invalid phrasing scores')
    # Everything above is checked before labels are joined.
    label_path = Path(plan['labels_local'])
    if P.sha(label_path) != plan['labels_sha256']:
        raise ValueError('label hash mismatch')
    records = P.rows(label_path)
    labels = {x['id']: x for x in records}
    if len(labels) != len(records) or set(labels) != set(ids):
        raise ValueError('label grid mismatch')
    lock = out.with_name(out.name+'.lock.json')
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('x') as stream:
        json.dump({'experiment': experiment, 'status': 'STARTED', 'score_seal_sha256': P.sha(outputs/'SCORE_SEAL.json')}, stream)
    return bank, outputs, out, plan, items, raw, labels


def event_rate(scores):
    """Rate of the frozen score-1 event, retaining neutral/score-0 outputs."""
    from common.stats import wilson
    values = np.asarray(scores)
    k, n = int((values == 1).sum()), len(values)
    p, lo, hi = wilson(k, n)
    return {'k': k, 'n': n, 'rate': p, 'ci95_wilson': [lo, hi],
            'neutral_n': int((values == .5).sum()), 'zero_n': int((values == 0).sum()),
            'mean_proxy': float(values.mean()), 'other_fractional_n': int(((values != 0)&(values != .5)&(values != 1)).sum())}


def finish(out, data, outputs):
    out.mkdir(parents=True, exist_ok=False)
    data.update(score_seal_sha256=P.sha(outputs/'SCORE_SEAL.json'),
                analysis_adapter_sha256=P.sha(Path(__file__)))
    P.dump(out/'metrics.json', data)


def continuation(bank, outputs, out):
    from mats import metrics
    bank, outputs, out, plan, items, raw, labels = verified('E6', bank, outputs, out)
    specs = json.loads((bank/'templates.json').read_text())
    rows = []
    for feature in plan['features']:
        for reader, site in K.READERS[:2]:
            cells = [r for r in raw if r['feature'] == feature and r['reader'] == reader]
            row = {'feature': feature, 'reader': reader, 'layer': site, 'n': len(cells),
                   'values': specs[feature]['values'], 'script': e6.SCRIPTS[feature],
                   'format_markers': dict(Counter(r.get('format_status', r['status']) for r in cells))}
            if any(r['status'] != 'COMPLETE' for r in cells):
                row['status'] = 'NOT EVALUABLE: FORMAT_UNSUPPORTED'
            else:
                y = np.array([labels[r['id']]['value'] == row['values'][0] for r in cells])
                scores = np.array([e6.behaviour(feature, r['text']) for r in cells])
                groups = np.array([labels[r['id']]['cluster'] for r in cells])
                row.update(status='EXPLORATORY', auroc=asdict(metrics.auroc_ci(scores, y, groups, n_boot=2000, seed=P.SEED)),
                           on_A=event_rate(scores[y]), off_B=event_rate(scores[~y]))
            rows.append(row)
    finish(out, {'experiment': 'E6', 'status': 'EXPLORATORY', 'prediction': plan['prediction'],
                 'rows': rows, 'base_rate_definition': 'score==1 event / all outputs per value; neutral outputs retained. A=first frozen value, B=second. B is not necessarily absence.',
                 'limitations': plan['limitations']}, outputs)
    return rows


def gain_curves(bank, outputs, out):
    from mats import metrics
    bank, outputs, out, plan, items, raw, labels = verified('E8', bank, outputs, out)
    specs = json.loads((bank/'templates.json').read_text())
    mapping = {(r['id'], r['reader'], r['alpha']): r for r in raw}
    rows = []
    for feature in plan['features']:
        ids = [x['id'] for x in items if x['feature'] == feature]
        if len(ids) != 40 or any(labels[i]['value'] != specs[feature]['values'][1] for i in ids):
            raise ValueError('wrong recipient population')
        groups = np.array([labels[i]['cluster'] for i in ids])
        for reader, site in K.READERS:
            matrix = np.array([[np.mean(mapping[i, reader, a]['scores']) for a in e8.ALPHAS] for i in ids])
            means = matrix.mean(axis=0)
            reference = plan['A_reference_medians'][feature+'__'+reader]['A_median']
            row = {'feature': feature, 'reader': reader, 'layer': site, 'class': specs[feature]['class'],
                   'n': len(ids), 'n_clusters': len(set(groups)), 'alphas': e8.ALPHAS, 'dose_means': means.tolist(),
                   'A_reference_median': reference, **e8.gains(means, reference)}
            # OLS slope is linear in dose means; bootstrap whole recipient clusters.
            low_weights = np.array([-1., 0., 1., 0., 0., 0.])
            x = np.array(e8.ALPHAS); all_weights = (x-x.mean())/np.sum((x-x.mean())**2)
            for key, weights in [('low_dose_gain', low_weights), ('all_dose_gain', all_weights)]:
                per_item = matrix @ weights
                row[key+'_ci95'] = list(metrics.cluster_bootstrap(lambda j: float(per_item[j].mean()), groups, n_boot=2000, seed=P.SEED))
            rows.append(row)
    summaries = []
    for reader, _ in K.READERS:
        for cls in sorted({r['class'] for r in rows}):
            subset = [r for r in rows if r['reader'] == reader and r['class'] == cls]
            summaries.append({'reader': reader, 'class': cls, 'n_rows': len(subset),
                              'mean_low_dose_gain': float(np.mean([r['low_dose_gain'] for r in subset])),
                              'median_low_dose_gain': float(np.median([r['low_dose_gain'] for r in subset]))})
    finish(out, {'experiment': 'E8', 'status': 'EXPLORATORY', 'prediction': plan['prediction'],
                 'rows': rows, 'descriptive_class_summaries': summaries,
                 'gain_definition': plan['gain_definition'], 'crossing_definition': plan['crossing_definition']}, outputs)
    return rows


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment', choices=['E6', 'E8'])
    for name in ('bank', 'outputs', 'out'):
        parser.add_argument('--'+name, type=Path, required=True)
    a = parser.parse_args()
    rows = (continuation if a.experiment == 'E6' else gain_curves)(a.bank, a.outputs, a.out)
    print(json.dumps(rows, indent=2))
