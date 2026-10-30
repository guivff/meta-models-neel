#!/usr/bin/env python3
"""R-5 independent E118b reproduction. Real inputs require COMPLETE_ONCE seal.

From repository root:
  python results/g_agreement/reviews/R-5/reproduce_e118b.py --self-test
  python results/g_agreement/reviews/R-5/reproduce_e118b.py \
    --analysis-seal /absolute/ANALYSIS_SEAL.json --seal-sha256 HASH

Read-only: no owner adapter imports, guards, writes, paid calls or launches.
Prints aggregate comparison and provenance only; never item IDs/text/labels.
Filesystem/commit/first-output custody and financial receipts still need review.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from common.stats import bootstrap_ci, wilson

UNIT_SHA = 'eacf843a30acec062587209452823546b6ffad48d3683f5fe6e75f3aebab352e'
CATEGORIES = ('YES', 'NO', 'OFF-TOPIC')


def check(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def sealed(path, expected):
    path = Path(path).resolve()
    check(sha(path) == expected, 'seal digest mismatch')
    obj = read(path)
    check(bool(obj.get('files')), 'empty seal')
    for member, digest in obj['files'].items():
        p = (path.parent / member).resolve()
        check(p.is_relative_to(path.parent), 'member escapes seal directory')
        check(sha(p) == digest, 'member digest mismatch')
    return obj


def reproduce(terminals, joins, bootstrap=bootstrap_ci):
    """Independent grouping; caller provides original ordered all-position joins."""
    records = {r['id']: r for r in terminals}
    check(len(records) == len(terminals) == len(joins), 'duplicate/count mismatch')
    check(set(records) == {j['id'] for j in joins}, 'census mismatch')
    items = {}
    positions = set()
    for j in joins:
        key = (j['family'], j['item_id'])
        pos = key + (j['position'],)
        check(pos not in positions, 'duplicate position')
        positions.add(pos)
        check(all(j[k] is None or type(j[k]) is bool for k in ('belief', 'truth')), 'invalid classification')
        check(type(j['has_truth']) is bool, 'invalid truth availability')
        labels = (j['belief'], j['truth'], j['has_truth'])
        if key not in items:
            items[key] = {'labels': labels, 'cells': []}
        check(items[key]['labels'] == labels, 'classification changes within item')
        r = records[j['id']]
        check(r['status'] in ('KEPT', 'UNPARSEABLE', 'REFUSED'), 'invalid status')
        value = None
        if r['status'] == 'KEPT':
            check(isinstance(r['result'], dict) and set(r['result']) == {'verdict'}, 'invalid result schema')
            value = r['result']['verdict']
            check(value in CATEGORIES, 'invalid category')
        else:
            check(r['result'] is None, 'non-null missing result')
        items[key]['cells'].append(value)

    def describe(selected):
        complete = [i for i in selected if None not in i['cells']]
        cells = [v for i in selected for v in i['cells']]
        observed = [v for v in cells if v is not None]
        categories = {}
        for name in CATEGORIES:
            fractions = [sum(v == name for v in i['cells']) / len(i['cells']) for i in complete]
            point, lo, hi = bootstrap(fractions) if fractions else (None, None, None)
            count = sum(v == name for v in observed)
            rate, wl, wh = wilson(count, len(observed)) if observed else (None, None, None)
            categories[name] = dict(item_rate=point, item_ci95=[lo, hi] if fractions else None,
                                    readout_count=count, readout_rate=rate,
                                    readout_wilson95=[wl, wh] if observed else None)
        return dict(n_items=len(selected), n_complete_items=len(complete),
                    n_incomplete_items=len(selected)-len(complete), n_positions=len(cells),
                    n_missing_positions=len(cells)-len(observed), categories=categories)

    def section(selected):
        known = [i for i in selected if i['labels'][2]]
        b = describe([i for i in known if i['labels'][0] is True])
        t = describe([i for i in known if i['labels'][1] is True])
        unknown = sum(None in i['labels'][:2] for i in known)
        br, tr = b['categories']['YES']['item_rate'], t['categories']['YES']['item_rate']
        evaluable = (not unknown and all(None not in i['cells'] for i in known)
                     and b['n_complete_items'] > 0 and t['n_complete_items'] > 0)
        return dict(all_items=describe(selected), belief_stating=b, truth_stating=t,
                    both_stating_items=sum(i['labels'][:2] == (True, True) for i in known),
                    unknown_classification_items=unknown,
                    no_canonical_truth=describe([i for i in selected if not i['labels'][2]]),
                    belief_minus_truth=None if br is None or tr is None else br-tr,
                    descriptive_reading=('MET' if br <= tr-.20 else 'NOT MET') if evaluable else 'NOT EVALUABLE')

    return dict(experiment='E118', part='b', descriptive=True,
                pooled=section(list(items.values())),
                rows={family: section([v for k, v in items.items() if k[0] == family])
                      for family in sorted({k[0] for k in items})},
                terminal_counts=dict(Counter(r['status'] for r in terminals)))


def load_sealed(analysis_path, digest):
    """Gate before any real judgment opening; resolve original label refs independently."""
    pins = read(Path(__file__).with_name('E118B_REPRODUCTION_SOURCE.json'))
    check(all(sha(ROOT/name) == digest for name, digest in pins['files'].items()), 'prepared source changed; review before real opening')
    path = Path(analysis_path).resolve()
    final = sealed(path, digest)
    check((final.get('experiment'), final.get('part'), final.get('status')) ==
          ('E118', 'b', 'COMPLETE_ONCE'), 'not a final E118b scientific seal')
    check({'RESULTS.json', 'BINDING.json'} <= set(final['files']), 'missing final bindings')
    spec = read(path.parent/'BINDING.json')
    unit_path = Path(spec['unit_seal'])
    unit = sealed(unit_path, UNIT_SHA)
    check(unit['n'] == 6790 and unit['n_items'] == 209 and
          unit['unit_definition_frozen'] is True and unit['frozen_before_judging'] is True,
          'original all-position census required')
    source_seals = {(s['seal'], s['sha256']): sealed(s['seal'], s['sha256']) for s in unit['source_seals']}
    custody = read(unit_path.parent/'CUSTODY.PRIVATE.json')
    public = read(unit_path.parent/'UNITS.json')
    public_by = {p['id']: p for p in public}
    check(len(public_by) == len(public) == len(custody['units']) == 6790, 'original unit count')
    files = {s['path']: s['sha256'] for s in custody['original_source_files']}
    check(all(sha(p) == h for p, h in files.items()), 'original source digest')
    objects = {}

    def resolve(ref):
        if 'seal' in ref:
            s = source_seals.get((ref['seal'], ref['sha256']))
            check(s is not None and ref['member'] in s['files'], 'unsealed source ref')
            p = str(Path(ref['seal']).parent/ref['member'])
        else:
            p = ref['path']
            check(files.get(p) == ref['sha256'], 'unbound source ref')
        if p not in objects:
            objects[p] = read(p)
        v = objects[p]
        for key in ref['keys']:
            v = v[key]
        return v

    joins = []
    for u in custody['units']:
        p = public_by[u['id']]
        check(p['context'] == resolve(u['context_ref']) and p['readout'] == resolve(u['readout_ref']), 'literal source mismatch')
        labels = u['original_label_refs']
        check('belief' in labels and set(labels) <= {'belief', 'truth'}, 'label ref schema')
        states = {}
        for name, ref in labels.items():
            if ref is not None:
                code = resolve(ref)
                states[name] = None if code is None else code['category'] == 'states_value' and ref['target_letter'] in code['values']
        joins.append(dict(id=u['id'], family=u['family'], item_id=u['item_id'], position=u['position'],
                          belief=states['belief'], truth=states.get('truth'), has_truth=labels.get('truth') is not None))
    check(len({(j['family'], j['item_id']) for j in joins}) == 209, 'original item count')
    for kind in ('input', 'report_source', 'judgment', 'cap'):
        # Original closure may be a hash-only source receipt rather than a member seal.
        if kind == 'report_source':
            check(sha(spec[kind+'_seal']) == spec[kind+'_sha256'], 'report closure hash')
        else:
            sealed(spec[kind+'_seal'], spec[kind+'_sha256'])
    judge = read(spec['judgment_seal'])
    check(judge['status'] == 'COMPLETE' and judge['experiment'] == 'E118' and
          judge['phase'] == 'belief_wrong_consistency_judging', 'terminal part-b bank required')
    check(judge['input_seal_sha256'] == spec['input_sha256'] and
          judge['E118b_source_seal_sha256'] == spec['report_source_sha256'], 'input/source binding')
    check(all(judge[k] is True for k in ('route_verified', 'labels_cpu_only', 'redaction_audit_complete'))
          and judge['redacted_records'] == 0, 'route/privacy receipt')
    check(read(Path(spec['input_seal']).parent/'PROVENANCE.json')['owner_seal_sha256'] == UNIT_SHA, 'roster provenance')
    return read(Path(spec['judgment_seal']).parent/'RESPONSES.json'), joins, read(path.parent/'RESULTS.json'), spec


def compare(actual, expected, where='result'):
    if isinstance(actual, dict):
        check(isinstance(expected, dict) and set(actual) <= set(expected), where+' keys')
        return sum(compare(v, expected[k], where+'.'+k) for k, v in actual.items())
    if isinstance(actual, list):
        check(isinstance(expected, list) and len(actual) == len(expected), where+' shape')
        return sum(compare(a, b, where+'[]') for a, b in zip(actual, expected))
    if isinstance(actual, float):
        check(isinstance(expected, (float, int)) and math.isfinite(expected) and
              math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), where+' numeric mismatch')
    else:
        check(type(actual) is type(expected) and actual == expected, where+' mismatch')
    return 1


def self_test():
    # Only synthetic packets from the committed tests; owner transport/entrypoint never imported.
    from projects.g_agreement.e118b_analysis.test_analysis import packet, boot
    from projects.g_agreement.e118b_analysis.analysis import summarize
    fixtures = [
        [(['YES']*9, True, False, True), (['NO'], True, False, True), (['YES'], False, True, True)],
        [(['NO'], None, False, True), (['YES'], False, True, True)],
        [(['NO', None], True, False, True), (['YES'], False, True, True)],
        [(['YES'], True, True, True)],
        [(['YES'], True, None, False), (['NO'], True, False, True), (['YES'], False, True, True)],
        [(['YES', 'NO', 'OFF-TOPIC'], True, False, True)],
    ]
    for fixture in fixtures:
        ts, js = packet(fixture)
        compare(reproduce(ts, js, boot), summarize(ts, js, bootstrap=boot))
    ts, js = packet(fixtures[0])
    r = reproduce(ts, js, boot)['pooled']
    check(r['belief_stating']['categories']['YES']['item_rate'] == .5, 'equal item weights')
    check(r['belief_stating']['categories']['YES']['readout_rate'] == .9, 'position supplement')
    check(r['descriptive_reading'] == 'MET', 'registered threshold')
    # Real default common.stats bootstrap on a non-degenerate synthetic example.
    compare(reproduce(ts, js), summarize(ts, js))
    # Multiple families preserve source insertion order within each bootstrap group.
    js[-1]['family'] = 'second'
    compare(reproduce(ts, js, boot), summarize(ts, js, bootstrap=boot))
    for ts, js in [packet([(['MAYBE'], True, False, True)]), packet([(['YES'], True, False, True)])]:
        if ts[0]['result']['verdict'] == 'YES':
            ts += ts
            js += js
        try:
            reproduce(ts, js, boot)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid packet accepted')
    print('PASS: 8 synthetic comparisons, weighting/threshold assertions, invalid packets; no real inputs opened')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--self-test', action='store_true')
    p.add_argument('--analysis-seal', type=Path)
    p.add_argument('--seal-sha256')
    a = p.parse_args()
    if a.self_test:
        check(a.analysis_seal is None and a.seal_sha256 is None, 'synthetic mode only')
        self_test()
        return
    check(a.analysis_seal is not None and a.seal_sha256 is not None, 'final seal path and pinned digest required')
    ts, js, expected, spec = load_sealed(a.analysis_seal, a.seal_sha256)
    computed = reproduce(ts, js)
    count = compare(computed, expected)
    print(json.dumps(dict(status='VERIFIED', compared_leaves=count, analysis_sha256=a.seal_sha256,
                          judgment_sha256=spec['judgment_sha256'], result_sha256=sha(a.analysis_seal.parent/'RESULTS.json'),
                          pooled_reading=computed['pooled']['descriptive_reading'],
                          row_readings={k: v['descriptive_reading'] for k, v in computed['rows'].items()},
                          terminals=len(ts), items=209, bootstrap_draws=5000, seed=0), indent=2))


if __name__ == '__main__':
    main()
