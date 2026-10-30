"""R-5 pre-output E138 independent reproduction; owner schema bound prospectively.

Normalized synthetic interface only: one record per recipient and arm, with
code=None for terminal missing, otherwise a set-valued list drawn from R/D/O
(recipient-old, donor-old, other). Empty list is the judge's none category.
These role letters are reviewer-internal, never a substitute for frozen labels.
Committed owner source/tests bind the original rubric and raw pointer schema.
Real CLI requires a verified final COMPLETE_ONCE seal. No owner entrypoint/guard/model calls.
"""
from collections import Counter
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from common.stats import wilson

ARMS = ('clean', 'donor', 'random')


def rate(k, n, planned):
    p, lo, hi = wilson(k, n) if n else (None, None, None)
    return dict(k=k, n=n, planned=planned, missing=planned-n, rate=p,
                ci95=None if not n else [lo, hi],
                completion_bounds=[k/planned, (k+planned-n)/planned])


def reproduce(records, planned=84):
    by = {arm: {} for arm in ARMS}
    for record in records:
        arm = record['arm']
        if arm not in by or record['item_id'] in by[arm]:
            raise ValueError('invalid arm or duplicate recipient')
        code = record['code']
        if code is not None and (type(code) is not list or
                                any(v not in ('R', 'D', 'O') for v in code) or
                                len(set(code)) != len(code)):
            raise ValueError('invalid normalized original value code')
        by[arm][record['item_id']] = code
    ids = set(by['clean'])
    if len(ids) != planned or any(set(by[a]) != ids for a in ARMS):
        raise ValueError('exact same planned recipient cohort required')
    tables = {}
    for arm in ARMS:
        codes = list(by[arm].values())
        observed = [c for c in codes if c is not None]
        counts = Counter('missing' if c is None else 'none' if not c else
                         'dual_or_multiple' if len(c) > 1 else
                         {'R': 'recipient_old', 'D': 'donor_old', 'O': 'other'}[c[0]]
                         for c in codes)
        tables[arm] = {name: rate(counts[name], len(observed), planned)
                       for name in ('recipient_old', 'donor_old', 'other', 'none', 'dual_or_multiple')}
        tables[arm]['missing_n'] = counts['missing']
        # Mention supplements preserve multi-value reports without crediting them
        # as exclusive recipient/donor reports (E127 original convention).
        tables[arm]['recipient_mentioned'] = rate(sum('R' in c for c in observed), len(observed), planned)
        tables[arm]['donor_mentioned'] = rate(sum('D' in c for c in observed), len(observed), planned)
    donor = tables['donor']
    recipient, target = donor['recipient_old'], donor['donor_old']
    primary = (None if recipient['rate'] is None else
               recipient['rate'] <= .05 and target['rate'] >= .40)
    random_rate = tables['random']['recipient_old']['rate']
    against = None if random_rate is None else random_rate >= .20
    return dict(arms=tables,
                donor_primary_observed='NOT EVALUABLE' if primary is None else 'MET' if primary else 'NOT MET',
                random_counts_against_observed='NOT EVALUABLE' if against is None else 'WITHDRAW WORDING' if against else 'NOT MET',
                donor_primary_robust_to_missing=(recipient['completion_bounds'][1] <= .05 and target['completion_bounds'][0] >= .40),
                random_against_robust_to_missing=tables['random']['recipient_old']['completion_bounds'][0] >= .20,
                interpretation='Activation specificity only; donor question re-solving remains possible. Low random recipient-old never supports the primary reading.',
                status='PREPARED CORE; original source/identity custody verified separately')


def reproduce_owner_rows(rows):
    """Independent bound-schema kernel, never imports E138 owner analysis.

    Original row IDs determine paired bootstrap order, as E100. Common.stats
    supplies the actual 2000-draw/20261027 bootstrap; missing masks stay separate.
    Returns all numerical arm/bootstrap/contrast fields and both readings.
    """
    import numpy as np
    from common.stats import bootstrap_ci
    if len(rows) != 84 or len({r['item_id'] for r in rows}) != 84:
        raise ValueError('exact84 original recipients')
    ids = {r['item_id'] for r in rows}
    mapping = {'recipient-old': 'R', 'donor-old': 'D', 'other': 'O'}
    normalized = []
    for row in rows:
        if row['row'] != 'fact_recall' or row['block'] != 44 or row['donor_id'] not in ids or row['donor_id'] == row['item_id']:
            raise ValueError('original row/block/donor identity')
        if not all(type(row[k]) is str and row[k] for k in ('recipient_old', 'donor_old')) or row['recipient_old'] == row['donor_old']:
            raise ValueError('distinct original value roles')
        if set(row['arms']) != set(ARMS):
            raise ValueError('full arm grid')
        for arm, code in row['arms'].items():
            if isinstance(code, str):
                code = [] if code == 'none' else [code]
            value = None if code is None else [mapping[c] for c in code]
            normalized.append(dict(item_id=row['item_id'], arm=arm, code=value))
    core = reproduce(normalized)
    sorted_ids = sorted(ids)
    by = {(r['item_id'], r['arm']): r['code'] for r in normalized}
    categories = ('recipient-old', 'donor-old', 'other', 'none', 'dual_or_multiple', 'recipient_mentioned', 'donor_mentioned')
    cells = {}
    for arm in ARMS:
        for category in categories:
            vector = []
            for ident in sorted_ids:
                code = by[ident, arm]
                if code is None:
                    value = np.nan
                elif category == 'dual_or_multiple':
                    value = len(code) > 1
                elif category == 'recipient_mentioned':
                    value = 'R' in code
                elif category == 'donor_mentioned':
                    value = 'D' in code
                else:
                    value = code == ([] if category == 'none' else [mapping[category]])
                vector.append(float(value))
            cells[arm, category] = np.array(vector)

    def stat(key, other=None):
        a = cells[key]
        kept = int(np.isfinite(a).sum())
        undefined = [False]
        def mean(v):
            finite = v[np.isfinite(v)]
            if not len(finite):
                undefined[0] = True
                return np.nan
            return float(np.mean(finite))
        def statistic(ix):
            index = ix.astype(int)
            point = mean(a[index])
            return point if other is None else point-mean(cells[other][index])
        point, lo, hi = bootstrap_ci(np.arange(84), fn=statistic, n_boot=2000, seed=20261027)
        interval = None if undefined[0] or not np.isfinite([lo, hi]).all() else [lo, hi]
        out = dict(total=84, kept=kept, missing=84-kept, over_5_percent=(84-kept)*20 > 84,
                   estimate=None if not math_isfinite(point) else point, CI95=interval)
        if other is not None:
            out['other_kept'] = int(np.isfinite(cells[other]).sum())
        return out

    arms = {}
    key_map = {'recipient-old': 'recipient_old', 'donor-old': 'donor_old'}
    for arm in ARMS:
        arms[arm] = {}
        for category in categories:
            v = core['arms'][arm][key_map.get(category, category)]
            arms[arm][category] = dict(k=v['k'], n=v['n'], planned_n=84, missing_n=v['missing'],
                estimate=v['rate'], Wilson95=v['ci95'], missing_over5percent=v['missing']/84 > .05,
                full84_missing_bounds=v['completion_bounds'], paired_item_bootstrap=stat((arm, category)))
    return dict(arms=arms, donor_primary=core['donor_primary_observed'],
                random_withdrawal='MET' if core['random_counts_against_observed'] == 'WITHDRAW WORDING' else core['random_counts_against_observed'],
                donor_positive_robust_to_missing=core['donor_primary_robust_to_missing'],
                random_withdrawal_robust_to_missing=core['random_against_robust_to_missing'],
                contrasts={arm: stat((arm, 'recipient-old'), ('clean', 'recipient-old')) for arm in ('donor', 'random')},
                bootstrap=dict(draws=2000, seed=20261027, unit='original paired recipient item'))


def math_isfinite(value):
    import math
    return math.isfinite(value)



def original_roles(code, status, judgment_id, value_roles):
    """Lossless categorical transport; no text/evidence classification."""
    def require(ok):
        if not ok:
            raise ValueError('invalid original categorical role binding')
    require(type(judgment_id) is str and bool(judgment_id))
    require(type(value_roles) is dict and set(value_roles) in ({'A', 'B'}, {'A', 'B', 'OTHER'}))
    order = ('recipient-old', 'donor-old', 'other')
    require(all(role in order for role in value_roles.values()))
    require('OTHER' not in value_roles or value_roles['OTHER'] == 'other')
    require(status in ('KEPT', 'UNPARSEABLE'))
    if status == 'UNPARSEABLE':
        require(code is None or (type(code) is dict and code.get('id') == judgment_id and
                                code.get('category') == 'UNPARSEABLE' and not code.get('values')))
        return None
    require(type(code) is dict and code.get('id') == judgment_id)
    category, values = code.get('category'), code.get('values')
    require(category in ('states_value', 'names_property_without_value', 'exhibits', 'silent'))
    require(type(values) is list and all(type(v) is str and v in value_roles for v in values))
    require(len(values) == len(set(values)) and bool(values) == (category == 'states_value'))
    result = [value_roles[letter] for letter in values]
    require(len(set(result)) == len(result))
    return sorted(result, key=order.index)


def expand_roles(value, resolve):
    """Resolve only explicitly sealed refs; all four transport fields are bound."""
    if type(value) is dict:
        if set(value) == {'ref'}:
            return resolve(value['ref'])
        if set(value) == {'e104_role_code'}:
            fields = value['e104_role_code']
            if (type(fields) is not dict or set(fields) != {'code', 'status', 'judgment_id', 'value_roles'} or
                    any(type(v) is not dict or set(v) != {'ref'} for v in fields.values())):
                raise ValueError('every original role field requires a sealed ref')
            return original_roles(**{k: resolve(v['ref']) for k, v in fields.items()})
        return {k: expand_roles(v, resolve) for k, v in value.items()}
    return [expand_roles(v, resolve) for v in value] if type(value) is list else value


def main():
    import argparse
    import json
    from reproduce_e118b import read, sealed, sha, check, compare
    parser = argparse.ArgumentParser(description='Independent sealed E138 reviewer reproduction; no author entrypoint or writes')
    parser.add_argument('--analysis-seal', type=Path, required=True)
    parser.add_argument('--seal-sha256', required=True)
    args = parser.parse_args()
    pins = read(Path(__file__).with_name('E138_REPRODUCTION_SOURCE.json'))
    check(all(sha(ROOT/name) == digest for name, digest in pins['files'].items()), 'prepared source changed')
    final = sealed(args.analysis_seal, args.seal_sha256)
    check(final.get('experiment') == 'E138' and final.get('status') == 'COMPLETE_ONCE', 'final E138 scientific seal required')
    check({'RESULTS.json', 'BINDING.PRIVATE.json'} <= set(final['files']), 'original private binding required')
    spec = read(args.analysis_seal.parent/'BINDING.PRIVATE.json')
    packet = sealed(spec['binding_seal'], spec['binding_sha256'])
    check(packet.get('experiment') == 'E138' and packet.get('status') == 'COMPLETE', 'complete source binding')
    flags = ('original84_verified', 'donor_pairing_E100_verified', 'random_E76_verified', 'clean_E127_no_prefix_verified',
             'literal_value_code_mapping_verified', 'route_verified', 'privacy_verified', 'terminal_dispositions_verified')
    check(all(packet.get(k) is True for k in flags), 'bound custody flags')
    check(packet['unknown_cost_requests'] == 0 and 0 <= packet['booked_usd'] <= packet['cap_usd'] == 1, 'original bank1 terminal receipt')
    check('RECORD_POINTERS.json' in packet['files'], 'sealed original pointer table')
    for name in ('E104_inventory', 'E127_clean', 'E100_pairing', 'E76_random'):
        source = packet['original_sources'][name]
        sealed(source['seal'], source['sha256'])
    sources = packet['source_seals']
    seals = [sealed(s['seal'], s['sha256']) for s in sources]
    cache = {}
    def resolve(ref):
        index = ref['seal_index']
        check(type(index) is int and 0 <= index < len(seals), 'original seal index')
        check(ref['member'] in seals[index]['files'], 'original member binding')
        key = (index, ref['member'])
        if key not in cache:
            cache[key] = read(Path(sources[index]['seal']).parent/ref['member'])
        result = cache[key]
        for field in ref['keys']:
            result = result[field]
        return result
    rows = expand_roles(read(Path(spec['binding_seal']).parent/'RECORD_POINTERS.json'), resolve)
    actual = reproduce_owner_rows(rows)
    leaves = compare(actual, read(args.analysis_seal.parent/'RESULTS.json'))
    print(json.dumps(dict(status='VERIFIED', compared_leaves=leaves, analysis_sha256=args.seal_sha256,
                         donor_primary=actual['donor_primary'], random_withdrawal=actual['random_withdrawal'],
                         bootstrap=actual['bootstrap'], source_and_physical_custody='separate review still required'), indent=2))


if __name__ == '__main__':
    main()
