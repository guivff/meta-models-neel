"""Synthetic E35 clarification-1 checks; no experiment data or model inference."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest

SPEC = importlib.util.spec_from_file_location('e35_decomp_math_tested', Path(__file__).with_name('decomp_math.py'))
dm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dm)


def test_registered_constants():
    assert dm.BOOTSTRAP_RESAMPLES == 10000
    assert dm.CONTROL_DRAWS == 100
    assert dm.SEED == 20261025


def test_additive_norm_share_not_norm_of_decoder_sum():
    decoder_columns = np.array([[1., -1.]])
    norms = np.linalg.norm(decoder_columns, axis=0)
    code = np.array([[1., 1.]])
    assert np.linalg.norm(code @ decoder_columns.T) == 0
    # Opposite decoder vectors cancel in vector space, but both carry mass here.
    np.testing.assert_allclose(dm.latent_share(code, norms, np.array([True, False])), [.5])
    # b_dec is neither accepted nor used by the registered formula.
    with pytest.raises(TypeError):
        dm.latent_share(code, norms, np.array([True, False]), b_dec=np.array([1e9]))


def test_weighted_share_zero_codes_and_empty_structure_set():
    z = np.array([[1., 3.], [2., 2.], [0., 0.]])
    actual = dm.latent_share(z, [2., 1.], np.array([True, False]))
    np.testing.assert_allclose(actual[:2], [2 / 5, 4 / 6])
    assert np.isnan(actual[2])
    empty = dm.latent_share(z, [2., 1.], np.array([False, False]))
    np.testing.assert_array_equal(empty[:2], [0., 0.])
    assert np.isnan(empty[2])


def test_all_structure_is_one_and_sparse_matches_dense_across_batches():
    rng = np.random.default_rng(7)
    n, width, k = 301, 17, 4
    index = np.stack([rng.choice(width, k, replace=False) for _ in range(n)])
    values = rng.uniform(.1, 2, (n, k)).astype(np.float32)
    values[5] = 0
    norms = rng.uniform(.1, 3, width)
    mask = rng.integers(0, 2, width).astype(bool)
    dense = np.zeros((n, width), dtype=np.float32)
    dense[np.arange(n)[:, None], index] = values
    np.testing.assert_allclose(dm.latent_share_sparse(index, values, norms, mask),
                               dm.latent_share(dense, norms, mask), equal_nan=True)
    result = dm.latent_share(dense, norms, np.ones(width, dtype=bool))
    np.testing.assert_allclose(result[np.isfinite(result)], 1)
    assert np.isnan(result[5])


@pytest.mark.parametrize('bad', [-.1, np.nan, np.inf])
def test_invalid_dense_codes_rejected(bad):
    with pytest.raises(ValueError):
        dm.latent_share([[1, bad]], [1, 1], np.array([True, False]))


@pytest.mark.parametrize('norms', [[1, -.1], [1, np.inf], [1, np.nan], [1], []])
def test_invalid_decoder_norms_rejected(norms):
    with pytest.raises(ValueError):
        dm.latent_share([[1, 2]], norms, np.array([True, False]))


def test_nonzero_codes_on_zero_decoder_columns_fail_instead_of_silent_exclusion():
    with pytest.raises(ValueError, match='nonzero code has zero'):
        dm.latent_share([[1, 0]], [0, 1], np.array([True, False]))
    with pytest.raises(ValueError, match='nonzero code has zero'):
        dm.latent_share_sparse([[0]], [[1]], [0, 1], np.array([True, False]))


@pytest.mark.parametrize('indices,values', [
    ([[0, 0]], [[1, 2]]), ([[0, 2]], [[1, 2]]), ([[-1, 1]], [[1, 2]]),
    ([[0., 1.]], [[1, 2]]), ([[0, 1]], [[1, -2]]), ([[0, 1]], [[1, np.nan]]),
])
def test_invalid_sparse_codes_rejected(indices, values):
    with pytest.raises(ValueError):
        dm.latent_share_sparse(indices, values, [1, 1], np.array([True, False]))


def test_pairing_excludes_union_before_both_item_means():
    report = dm.paired_ratio([.4, np.nan, .2, .6], [.2, .9, np.nan, .3])
    assert report['paired_items'] == 2
    assert report['excluded_items'] == 2
    assert report['term_zero_code_items'] == report['baseline_zero_code_items'] == 1
    assert report['mean_term_share'] == .5
    assert report['mean_baseline_share'] == .25
    assert report['ratio'] == 2
    assert report['exclusion_limit_exceeded']


def test_ratio_of_means_is_not_mean_of_item_ratios():
    report = dm.paired_ratio([.9, .1], [.9, .01])
    assert report['ratio'] == pytest.approx(1 / .91)
    assert report['ratio'] != pytest.approx(np.mean([1, 10]))


def test_exact_ten_percent_exclusion_is_interpretable_but_above_is_not():
    a = dm.row_cluster_analysis([.6] * 9 + [np.nan], [.3] * 10, ['r'] * 10)
    assert a['excluded_fraction'] == .1
    assert a['interpretable'] and a['rule_met']
    b = dm.row_cluster_analysis([.6] * 8 + [np.nan] * 2, [.3] * 10, ['r'] * 10)
    assert b['ratio'] == 2
    assert not b['interpretable'] and b['rule_met'] is None
    assert b['uninterpretable_reasons'] == ['more_than_10_percent_paired_items_excluded']


@pytest.mark.parametrize('ratio,lower,met', [
    (1.5, 1.000000001, True), (1.5, 1., False), (1.499999999, 1.1, False),
    (2., .999999999, False), (2., 1.5, True),
])
def test_frozen_decision_boundaries(ratio, lower, met):
    report = dm.rule_decision(ratio, [lower, 3.], 0, 10)
    assert report['interpretable']
    assert report['rule_met'] is met


def test_row_cluster_resampling_preserves_item_weights_and_whole_rows():
    # Row A has two items, row B one. Equal-weight row-ratio means would be1.5.
    report = dm.row_cluster_analysis([1., 1., .1], [.5, .5, .1], ['A', 'A', 'B'])
    assert report['ratio'] == pytest.approx(2.1 / 1.1)
    assert report['ratio'] != pytest.approx(1.5)
    # Whole-cluster draws: AA->2, AB/BA->2.1/1.1, BB->1. Both tails have25% mass.
    np.testing.assert_allclose(report['ci95'], [1, 2])
    assert report['bootstrap_resamples_performed'] == 10000
    assert report['bootstrap_seed'] == 20261025
    assert not report['rule_met']
    again = dm.row_cluster_analysis([.1, 1., 1.], [.1, .5, .5], ['B', 'A', 'A'])
    assert again['ci95'] == report['ci95']
    assert again['ratio'] == pytest.approx(report['ratio'])


def test_constant_paired_ratio_bootstrap_is_degenerate_without_random_jitter():
    report = dm.row_cluster_analysis([.6, .3, .9], [.2, .1, .3], ['A', 'B', 'C'])
    np.testing.assert_allclose(report['ci95'], [3, 3])
    assert report['undefined_bootstrap_draws'] == 0
    assert report['rule_met']


def test_undefined_bootstrap_draws_are_counted_not_dropped_from_ci():
    report = dm.row_cluster_analysis([.5, 1.], [0, .5], ['A', 'B'])
    assert report['ratio'] == 3
    assert report['bootstrap_resamples_performed'] == 10000
    assert 2000 < report['undefined_bootstrap_draws'] < 3000
    assert report['ci95'] is None and report['rule_met'] is None
    assert 'undefined_bootstrap_draws_not_discarded' in report['uninterpretable_reasons']


@pytest.mark.parametrize('term,baseline', [([.1, .2], [0, 0]), ([np.nan, np.nan], [.1, .2])])
def test_undefined_baseline_or_no_valid_items_remains_uninterpretable(term, baseline):
    report = dm.row_cluster_analysis(term, baseline, ['A', 'B'])
    assert report['ratio'] is None
    assert report['bootstrap_resamples_performed'] == 0
    assert report['ci95'] is None and report['rule_met'] is None


@pytest.mark.parametrize('term,base', [([1.1], [.1]), ([-.1], [.1]), ([np.inf], [.1]), ([.1], [.2, .3]), ([], [])])
def test_invalid_share_arrays_rejected(term, base):
    with pytest.raises(ValueError):
        dm.paired_ratio(term, base)


def test_arithmetic_overflow_is_rejected_not_returned_in_json_report():
    with pytest.raises(ValueError, match='nonfinite ratio'):
        dm.paired_ratio([1.], [1e-320])


@pytest.mark.parametrize('rows', [[''], [b''], [1], ['A', 'B']])
def test_invalid_row_ids_rejected(rows):
    with pytest.raises(ValueError, match='row ID'):
        dm.row_cluster_analysis([.2], [.1], rows)


def test_frequency_controls_match_every_exact_count_and_preserve_cardinality():
    counts = np.array([0, 0, 1, 1, 1, 2])
    observed = np.array([True, False, True, False, False, True])
    masks = dm.frequency_matched_masks(counts, observed)
    assert masks.shape == (100, 6) and masks.dtype == bool
    assert np.all(masks.sum(axis=1) == 3)
    for frequency in np.unique(counts):
        group = counts == frequency
        assert np.all(masks[:, group].sum(axis=1) == observed[group].sum())
    assert np.all(masks[:, -1])  # Singleton stays selected; no matching relaxation.
    assert 1 < len(np.unique(masks, axis=0)) <= 6
    np.testing.assert_array_equal(masks, dm.frequency_matched_masks(counts, observed))


@pytest.mark.parametrize('draws,seed', [(99, dm.SEED), (101, dm.SEED), (100, 1), (True, dm.SEED)])
def test_control_draw_count_and_seed_are_fixed(draws, seed):
    with pytest.raises(ValueError):
        dm.frequency_matched_masks([1, 1], np.array([True, False]), draws=draws, seed=seed)


def test_degenerate_frequency_control_masks_are_reported_without_resampling():
    observed = np.array([True, False, True])
    masks = dm.frequency_matched_masks([1, 2, 3], observed)
    term = np.tile([.4, .2], (100, 1))
    base = np.tile([.2, .1], (100, 1))
    report = dm.control_summary(term, base, masks=masks, structure_mask=observed)
    assert report['unique_masks'] == 1 and report['draws_equal_observed'] == 100
    assert report['ratios'] == [2.] * 100
    assert not report['null_CI_computed'] and not report['rule_applied_to_controls']


def test_control_summary_keeps_undefined_ratios_in_all_100_draws():
    term = np.tile([.4, .2], (100, 1))
    baseline = np.tile([.2, .1], (100, 1))
    baseline[7] = 0
    report = dm.control_summary(term, baseline)
    assert len(report['ratios']) == 100
    assert report['ratios'][7] is None
    assert report['undefined_ratios'] == 1
    assert report['null_percentiles_2_5_50_97_5'] is None
    assert report['paired_items_per_draw'] == [2] * 100


def test_control_exclusions_cannot_change_with_label_draw():
    term = np.tile([.4, .2], (100, 1))
    baseline = np.tile([.2, .1], (100, 1))
    term[1, 0] = np.nan
    with pytest.raises(ValueError, match='invariant'):
        dm.control_summary(term, baseline)
