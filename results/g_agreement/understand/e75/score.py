"""E75 §193 pure scorer. No outcome I/O, claim, or computation on import."""
import math
from pathlib import Path
import sys

R3B = Path(__file__).resolve().parents[1] / 'e52' / 'r3b'
sys.path.insert(0, str(R3B))
from category_comparison import compare
from stratified_comparison import within_category

SEED = 20261027
BOOTSTRAPS = 2000


def identity(row):
    return tuple(row[k] for k in ('model', 'reader', 'bank', 'row'))


def score(rows):
    """Pool all bound forecast units separately by model AND reader.

    Truth/category/prospective eligibility are supplied by a separately sealed
    binding, never inferred or selected in response to scores here.
    """
    if not rows:
        raise ValueError('no forecast units')
    keys = [identity(r) for r in rows]
    if any(not isinstance(x, str) or not x for k in keys for x in k):
        raise ValueError('nonempty model/reader/bank/row identities required')
    if len(keys) != len(set(keys)):
        raise ValueError('duplicate model/reader/bank/unit')
    for r in rows:
        if r['j_label'] not in ('IN-J', 'DIFFUSE', 'OUT-J'):
            raise ValueError('unknown J label')
        if r['j_prediction'] != ('REPORTED' if r['j_label'] == 'IN-J' else 'MISSED'):
            raise ValueError('forecast must be REPORTED iff IN-J')
        for field in ('j_fraction', 'j_null_median', 'j_null_percentile975'):
            v = r[field]
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
                raise ValueError('finite nonnegative J fraction and null summaries required')
        if r['j_null_median'] > r['j_null_percentile975']:
            raise ValueError('null median exceeds 97.5th percentile')
    outputs = []
    for model, reader in sorted({k[:2] for k in keys}):
        rr = sorted([r for r in rows if (r['model'], r['reader']) == (model, reader)], key=identity)
        pooled = compare(rr, draws=BOOTSTRAPS, seed=SEED)
        within = within_category(rr)
        ci = pooled['bootstrap']['percentile95']
        eligible = pooled['n'] >= 60 and pooled['reported'] >= 15 and pooled['missed'] >= 15 and ci is not None
        jb = pooled['J_balanced_accuracy']
        delta = pooled['J_minus_category_balanced_accuracy']
        components = {
            'pooled': bool(jb >= .70 and ci['J_balanced_accuracy'][0] > .55) if eligible else None,
            'category_increment': bool(delta >= .05 and ci['J_minus_category_balanced_accuracy'][0] > 0) if eligible else None,
            'within_category': within['criterion_met'],
        }
        confirmatory = eligible and within['status'] == 'CONFIRMATORY'
        constant = .5 if jb is not None else None
        constant_ci = [x - .5 for x in ci['J_balanced_accuracy']] if ci else None
        outputs.append({
            'model': model, 'reader': reader, 'n': pooled['n'],
            'reported': pooled['reported'], 'missed': pooled['missed'],
            'pooled_sample_eligible': eligible,
            'R_P1_status': 'EVALUABLE' if confirmatory else 'NOT EVALUABLE',
            'R_P1_met': all(components.values()) if confirmatory else None,
            'R_P1_components': components,
            'eligibility_reason': None if confirmatory else (
                'requires >=60 units and >=15 of each truth class' if not eligible
                else 'within-category test requires >=3 qualifying strata for confirmation'),
            'falsifier': bool(jb <= .55) if eligible else None,
            'J_balanced_accuracy': jb,
            'category_balanced_accuracy': pooled['category_balanced_accuracy'],
            'J_minus_category_balanced_accuracy': delta,
            'constant_REPORTED_balanced_accuracy': constant,
            'constant_MISSED_balanced_accuracy': constant,
            'J_minus_constant_balanced_accuracy': jb - .5 if jb is not None else None,
            'J_minus_constant_percentile95': constant_ci,
            'J_accuracy': pooled['J_accuracy'],
            'better_constant_accuracy': pooled['better_constant_accuracy'],
            'bootstrap': pooled['bootstrap'], 'within_category': within,
            'rows': pooled['rows'],
        })
    return {'registration': '§193 / a68a228d / 4cde021d',
            'pooling': 'all bound units, separately by model and reader',
            'results': outputs}
