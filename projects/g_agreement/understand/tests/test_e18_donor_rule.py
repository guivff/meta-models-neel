"""CPU-only checks for §109's pre-output donor clarification (99518d4e)."""
import copy

import numpy as np
import pytest

from projects.g_agreement.understand import e18_analyse as A


def test_movement_is_strict_and_signed_to_each_recipients_truth():
    positive = np.array([True, False, True, False, True, False])
    b = np.array([2., -2., 2., -2., 2., -2.])
    c = np.array([1., -1., 3., -3., 2., -2.])
    result = A.donor_movement(b, c, positive, ['a', 'b', 'c', 'd', 'e', 'f'])
    # A truth: a smaller raw A-minus-B score moves toward the B donor.
    # B truth: a larger raw score moves toward the A donor. Exact ties do not move.
    assert result['moving_items'] == 2
    assert result['n_items'] == 6
    assert result['fraction'] == 2/6
    assert result['row_moves'] is False
    assert result['bootstrap'] == {'samples': 2000, 'seed': 20261025, 'unit': 'item'}


def test_ci_matches_independent_seeded_recipient_item_bootstrap():
    n = 84
    ids = np.asarray([f'item-{i:02d}' for i in range(n)])[::-1]
    positive = np.arange(n) % 2 == 0
    moved = np.asarray([(i % 7) < 5 for i in range(n)])
    b = np.where(positive, 2., -2.)
    c = b + np.where(positive, -1., 1.) * np.where(moved, 1., -1.)
    result = A.donor_movement(b, c, positive, ids)
    # The shared cluster helper sorts cluster IDs; each recipient is one cluster.
    # This reference samples indices directly and never calls that helper.
    canonical = moved[np.argsort(ids)]
    rng = np.random.default_rng(20261025)
    samples = [canonical[rng.integers(0, n, n)].mean() for _ in range(2000)]
    expected = np.quantile(samples, [.025, .975]).tolist()
    assert result['moving_items'] == 60
    assert result['fraction'] == 60/84
    assert result['ci95'] == expected
    assert result['row_moves'] is True
    # Frozen-seed output is reproducible without any generated model text.
    assert A.donor_movement(b, c, positive, ids) == result


@pytest.mark.parametrize('moving,lower,expected', [
    (6, .51, True),       # The fraction threshold is inclusive.
    (6, .50, False),      # The CI must lie strictly above 0.50.
    (5, .51, False),      # Passing the CI alone is insufficient.
    (10, .49, False),     # Even an extreme point estimate cannot bypass the CI.
])
def test_exact_point_and_ci_boundaries(monkeypatch, moving, lower, expected):
    import common
    from mats import metrics
    calls = []

    def fixed_interval(stat, clusters, n_boot=2000, seed=0, **kwargs):
        calls.append((list(clusters), n_boot, seed, stat(np.arange(10))))
        return lower, 1.

    monkeypatch.setattr(metrics, 'cluster_bootstrap', fixed_interval)
    b = np.ones(10)
    c = np.r_[np.zeros(moving), np.ones(10-moving)]
    ids = [f'unit-{i}' for i in range(10)]
    result = A.donor_movement(b, c, np.ones(10, bool), ids)
    assert result['row_moves'] is expected
    assert result['fraction'] == moving/10
    assert calls == [(ids, 2000, 20261025, moving/10)]


def compute_fixture():
    records, labels = [], {}
    for i in range(24):
        positive = i % 2 == 0
        key = f'item-{i:02d}'
        labels[key] = {'feature': 'f', 'value': 'A' if positive else 'B',
                       'cluster': f'template-{i//12}'}
        b = [-3., 5.] if positive else [3., -5.]
        # The first phrasing alone would give the opposite movement conclusion.
        c = [100., -100.] if positive else [-100., 100.]
        if i >= 12:
            c = list(b)  # Ties are non-movements, not half-credit.
        records.append({'id': key, 'feature': 'f', 'arms': {
            'a': [1000., 1000.], 'b': b, 'c': c, 'd': [1., 1.]}})
    return records, labels, {'f': {'class': 'state-like', 'values': ['A', 'B']}}


def test_compute_uses_pair_mean_compares_b_and_clusters_by_recipient_item():
    records, labels, templates = compute_fixture()
    result = A.compute(records, labels, templates, n_boot=40)[0]['donor_movement']
    assert result['moving_items'] == 12
    assert result['fraction'] == .5
    # The same 12 outcomes sit wholly within one template. A template bootstrap
    # would have CI[0,1]; the registered donor CI resamples 24 recipient items.
    assert result['ci95'][0] > 0 and result['ci95'][1] < 1
    assert result['bootstrap']['seed'] == 20261025
    assert result['bootstrap']['unit'] == 'item'
    changed = copy.deepcopy(records)
    for record in changed:
        record['arms']['a'] = [-1000., -1000.]
    relabelled_clusters = copy.deepcopy(labels)
    for i, key in enumerate(relabelled_clusters):
        relabelled_clusters[key]['cluster'] = f'other-{i//4}'
    # Neither ask-only scores nor the primary metric's template grouping enters
    # the donor comparison. The donor itself is not a resampling cluster.
    same = A.compute(changed, relabelled_clusters, templates, n_boot=40)[0]['donor_movement']
    assert same == result


def prediction_rows():
    return [{'feature': feature,
             'b_minus_a': {'difference': .07, 'ci95': [-.1, .2]},
             'donor_movement': {'row_moves': False},
             'arms': {'d': {'auroc': .6}}}
            for feature in A.FEATURES]


def test_format_limit_requires_same_four_structure_rows():
    rows = prediction_rows()
    for row in rows[:4]:
        row['b_minus_a'] = {'difference': .10, 'ci95': [.001, .2]}
        row['donor_movement']['row_moves'] = True
    result = A.assess(rows)
    assert result['assessment'] == 'format limit'
    assert set(result['format_limit_rows']) == set(A.STRUCTURE[:4])
    # Donor movement on another row cannot replace movement on a qualifying row.
    rows[3]['donor_movement']['row_moves'] = False
    rows[4]['donor_movement']['row_moves'] = True
    assert A.assess(rows)['assessment'] == 'mixed'
    # Content controls never count toward the four required structure rows.
    for row in rows[7:]:
        row['b_minus_a'] = {'difference': .2, 'ci95': [.1, .3]}
        row['donor_movement']['row_moves'] = True
    assert A.assess(rows)['assessment'] == 'mixed'


def test_format_limit_ci_above_zero_is_strict():
    rows = prediction_rows()
    for row in rows[:4]:
        row['b_minus_a'] = {'difference': .1, 'ci95': [.01, .2]}
        row['donor_movement']['row_moves'] = True
    rows[3]['b_minus_a']['ci95'][0] = 0.
    assert A.assess(rows)['assessment'] == 'mixed'


def test_real_suppression_uses_same_five_rows_with_exact_boundaries():
    rows = prediction_rows()
    for row in rows[:5]:
        row['b_minus_a']['difference'] = .049
        row['arms']['d']['auroc'] = .70
    result = A.assess(rows)
    assert result['assessment'] == 'real suppression'
    assert set(result['real_suppression_rows']) == set(A.STRUCTURE[:5])
    rows[4]['b_minus_a']['difference'] = .05
    assert A.assess(rows)['assessment'] == 'mixed'
    rows[4]['b_minus_a']['difference'] = .049
    rows[4]['arms']['d']['auroc'] = .6999
    rows[5]['arms']['d']['auroc'] = .90
    assert A.assess(rows)['assessment'] == 'mixed'
