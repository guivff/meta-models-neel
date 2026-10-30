"""E118b §231: all positions, item-level original classifications and uncertainty."""
from collections import defaultdict, Counter
from common.stats import bootstrap_ci, wilson
from projects.g_agreement.readerbench.scoring import require

CATEGORIES = ('YES', 'NO', 'OFF-TOPIC')


def summarize(terminals, joins, bootstrap=bootstrap_ci):
    by = {r['id']: r for r in terminals}
    require(len(by) == len(terminals) == len(joins) and set(by) == {r['id'] for r in joins}, 'exact census')
    groups = defaultdict(list)
    seen = set()
    for j in joins:
        key = (j['family'], j['item_id'])
        unit = key + (j['position'],)
        require(unit not in seen, 'unique original position')
        seen.add(unit)
        require(all(j[k] is None or type(j[k]) is bool for k in ('belief', 'truth')), 'original nullable item classifications')
        require(type(j['has_truth']) is bool, 'original truth target availability')
        t = by[j['id']]
        require(t['status'] in ('KEPT', 'UNPARSEABLE', 'REFUSED'), 'original terminal status')
        if t['status'] == 'KEPT':
            require(isinstance(t['result'], dict) and set(t['result']) == {'verdict'} and t['result']['verdict'] in CATEGORIES, 'three-way rubric')
            v = t['result']['verdict']
        else:
            require(t['result'] is None, 'missing stays null')
            v = None
        groups[key].append((j, v, t['status']))
    items = []
    for key, positions in groups.items():
        j = positions[0][0]
        require(all(all(p[0][k] == j[k] for k in ('belief', 'truth', 'has_truth')) for p in positions), 'one original group classification across positions')
        cells = [p[1] for p in positions]
        items.append(dict(family=key[0], belief=j['belief'], truth=j['truth'], has_truth=j['has_truth'], cells=cells,
                          complete=all(v is not None for v in cells)))

    def describe(selected):
        complete = [x for x in selected if x['complete']]
        cells = [v for x in selected for v in x['cells']]
        kept = [v for v in cells if v is not None]
        rates = {}
        for category in CATEGORIES:
            values = [x['cells'].count(category)/len(x['cells']) for x in complete]
            estimate, lo, hi = bootstrap(values) if values else (None, None, None)
            k = kept.count(category)
            wp, wl, wh = wilson(k, len(kept)) if kept else (None, None, None)
            rates[category] = dict(item_rate=estimate, item_ci95=[lo, hi] if values else None,
                                   readout_count=k, readout_rate=wp, readout_wilson95=[wl, wh] if kept else None)
        return dict(n_items=len(selected), n_complete_items=len(complete), n_incomplete_items=len(selected)-len(complete),
                    n_positions=len(cells), n_missing_positions=len(cells)-len(kept), categories=rates)

    def section(selected):
        known = [x for x in selected if x['has_truth']]
        belief = describe([x for x in known if x['belief'] is True])
        truth = describe([x for x in known if x['truth'] is True])
        unknown = sum(x['belief'] is None or x['truth'] is None for x in known)
        evaluable = bool(belief['n_complete_items'] and truth['n_complete_items']) and not unknown and all(x['complete'] for x in known)
        b, t = belief['categories']['YES']['item_rate'], truth['categories']['YES']['item_rate']
        reading = 'NOT EVALUABLE' if not evaluable else ('MET' if b <= t-.20 else 'NOT MET')
        return dict(all_items=describe(selected), belief_stating=belief, truth_stating=truth,
                    both_stating_items=sum(x['belief'] is True and x['truth'] is True for x in known),
                    unknown_classification_items=unknown, no_canonical_truth=describe([x for x in selected if not x['has_truth']]),
                    belief_minus_truth=None if b is None or t is None else b-t, descriptive_reading=reading)

    return dict(experiment='E118', part='b', descriptive=True, pooled=section(items),
                rows={f: section([x for x in items if x['family'] == f]) for f in sorted({x['family'] for x in items})},
                terminal_counts=dict(Counter(t['status'] for t in terminals)),
                unit='All original positions; within-item fractions, equal item weights; common.stats bootstrap5000 seed0. Readout Wilson intervals are descriptive supplements.',
                missingness='Unknown original classifications remain unknown; incomplete items excluded from descriptive item estimates and make the affected reading NOT EVALUABLE. No-truth items reported separately, excluded from belief-versus-truth reading. Both-stating items retained in both groups.')
