"""E58b CPU-only mean-damage rules after the sealed label join."""
import numpy as np
from common58 import ARMS, CONTROLS, SHALLOW, require
from projection58 import check_basis, random_basis, projection_hook, PCAMoments


def aggregate(rows, records):
    """Each pair equally weighted within item, then items within each row."""
    expected = {(row['key'], item['id'], j, arm)
                for row in rows for item in row['test'] for j in range(len(item['pairs'])) for arm in ARMS}
    keyed = {(r['row'], r['id'], r['pair_index'], r['arm']): r for r in records}
    require(len(keyed) == len(records) and set(keyed) == expected, 'Incomplete/duplicate E58b score grid')
    require(all(np.isfinite(r['logodds_A_minus_B']) for r in records), 'Nonfinite E58b score')
    result = []
    for row in rows:
        item_scores = {arm: [] for arm in ARMS}
        for item in row['test']:
            sign = 1 if item['label'] == 1 else -1
            require(item['label'] in (0, 1), 'Binary frozen orientation required')
            for arm in ARMS:
                item_scores[arm].append(sign * np.mean([
                    keyed[row['key'], item['id'], j, arm]['logodds_A_minus_B']
                    for j in range(len(item['pairs']))]))
        means = {arm: float(np.mean(values)) for arm, values in item_scores.items()}
        damage = {arm: means['none'] - means[arm] for arm in ARMS if arm != 'none'}
        random = float(np.mean([damage['random' + str(i)] for i in range(5)]))
        result.append({'row': row['key'], 'feature': row['feature'], 'category': row['category'],
            'control': row['control'], 'n_test': len(row['test']),
            'mean_correct_minus_wrong': means, 'damage': damage, 'random_damage_mean5': random,
            'J_over_random_damage': damage['J'] / random if random != 0 else None,
            'ratio_status': 'DEFINED_SIGNED_RATIO' if random != 0 else 'UNDEFINED_ZERO_RANDOM_DAMAGE',
            'shallow_content_descriptive': row['feature'] in SHALLOW,
            'PCA_damage_below_random': damage['PCA'] < random,
            'J_at_least_twice_random': damage['J'] >= 2 * random,
            'J_at_most_1p25_random': damage['J'] <= 1.25 * random})
        if row.get('bank') == 'E57':
            lookup = {x['id']: x for x in row['test']}
            swap_means = {}
            for arm in ARMS:
                values = []
                for item in row['test']:
                    donor = lookup[item['swap_donor_id']]
                    require(donor['label'] == 1 - item['label'], 'Swap is not opposite-state')
                    require([(p['A_ids'], p['B_ids']) for p in donor['pairs']]
                            == [(p['A_ids'], p['B_ids']) for p in item['pairs']], 'Swap pair mismatch')
                    sign = 1 if item['label'] == 1 else -1
                    values.append(sign * np.mean([keyed[row['key'], donor['id'], j, arm]['logodds_A_minus_B']
                                                  for j in range(len(item['pairs']))]))
                swap_means[arm] = float(np.mean(values))
            result[-1]['paired_prompt_swap_control'] = {'status': 'COMPLETE_DESCRIPTIVE',
                'n': len(row['test']), 'mean_correct_minus_wrong': swap_means,
                'score_reuse': 'Exact frozen opposite-state prompt, same candidate pair and shared arm basis',
                'extra_model_calls': 0, 'used_in_R_b1_or_R_b2': False}
    controls = [r for r in result if r['control']]
    require(len(controls) == 3 and {r['feature'] for r in controls} == set(CONTROLS),
            'Exact clarified three-row sanity population required')
    sanity_n = sum(r['J_at_least_twice_random'] for r in controls)
    sanity = sanity_n >= 2
    main = [r for r in result if r['category'] in ('bookkeeping', 'delimiter', 'syntactic') and not r['control']]
    require(main, 'Empty R-b2 row population')
    n = sum(r['J_at_most_1p25_random'] for r in main)
    return {'rows': result, 'R_b1': {'met': sanity, 'passing': sanity_n, 'denominator': 3},
        'R_b2': {'met': bool(10 * n >= 7 * len(main)) if sanity else None,
            'status': 'EVALUABLE' if sanity else 'NOT EVALUABLE', 'passing': n, 'denominator': len(main),
            'rows': [r['row'] for r in main]},
        'signed_random_damage_policy': 'Arithmetic mean of five seeds; no clipping or absolute values; rules use direct inequalities, ratios descriptive only',
        'shallow_content_group_descriptive': [r for r in result if r['feature'] in SHALLOW],
        'PCA_rows_reported_without_exclusion': [r['row'] for r in result if r['PCA_damage_below_random']]}
