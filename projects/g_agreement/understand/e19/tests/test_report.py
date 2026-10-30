"""Offline statistical/provenance regressions for the E19 report."""
import json

import numpy as np
import pytest

from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand.e19 import report as R


def fixture(n=4):
    items, records = [], []
    slopes = {'own': 2., 'donor': 3., 'content': .5,
              **dict(zip(R.RANDOM, (.1, .2, .3)))}
    for row in R.ROWS:
        for i in range(n):
            item = {'row': row, 'item_id': row+'_'+str(i),
                    'cluster': 'template_'+str(i//(14 if n == 84 else 2))}
            items.append(item)
            for arm in R.arms(row):
                for alpha in R.ALPHAS:
                    baseline = 10+i+(50 if arm == 'donor' else 0)
                    records.append({**item, 'arm': arm, 'alpha': alpha,
                        'asked_score': baseline+slopes[arm]*alpha,
                        'continuation_score': None if row == 'prose_sentiment' else baseline+4*alpha,
                        'projection_preanswer': baseline+5*alpha,
                        'projection_answer_mean': baseline+3*alpha})
    return items, records


def analyse(items, records, **kwargs):
    return R.analyse_scores(records, items, expected_n=4, n_bootstrap=200, **kwargs)


def test_primary_empirical_three_direction_quantile_and_all_doses():
    items, records = fixture()
    summary, paired = analyse(items, records)
    assert summary['prediction']['pathway_underweighted_observed'] is True
    assert summary['prediction']['state_rows_observed'] == 4
    for row in summary['rows']:
        assert row['random_slope_q95'] == pytest.approx(.29)
        assert row['asked_own_slope']['mean'] == pytest.approx(2)
        assert row['registered_pattern_observed'] is True
    assert summary['positive_control']['asked_positive_direction'] is True
    assert len(summary['cells']) == 29*7*4
    assert len(paired) == len(records) == 29*7*4
    assert 'not a calibrated 95%' in summary['method']['random_percentile_limitation']
    assert summary['method']['bootstrap_replicates'] == 200
    assert summary['method']['seed'] == 20261025


def test_positive_slope_alone_does_not_pass_nonmonotonic_seven_dose_curve():
    items, records = fixture()
    for record in records:
        if record['row'] == 'prose_paren' and record['arm'] == 'own' and record['alpha'] == 2:
            record['asked_score'] -= 5
    summary, _ = analyse(items, records)
    row = summary['rows'][0]
    assert row['asked_own_slope']['mean'] > row['random_slope_q95']
    assert row['asked_monotonic_nondecreasing'] is False
    assert row['registered_pattern_observed'] is False
    assert summary['prediction']['state_rows_observed'] == 3
    assert summary['prediction']['pathway_underweighted_observed'] is True


def test_no_posthoc_sign_flip_and_content_not_counted_as_state():
    items, records = fixture()
    for record in records:
        if record['row'] in R.STRUCTURE and record['arm'] == 'own':
            record['asked_score'] -= 4*record['alpha']
    summary, _ = analyse(items, records)
    assert summary['prediction']['pathway_underweighted_observed'] is False
    assert summary['prediction']['state_rows_observed'] == 0
    assert summary['positive_control']['registered_pattern_observed'] is True
    assert all(r['asked_own_slope']['mean'] == pytest.approx(-2) for r in summary['rows'][:4])


def test_donor_steering_uses_donor_zero_and_replacement_is_separate():
    items, records = fixture()
    summary, paired = analyse(items, records)
    record = next(r for r in paired if r['row'] == 'prose_paren' and r['arm'] == 'donor' and r['alpha'] == 1)
    assert record['baseline_arm'] == 'donor'
    assert record['asked_score_change'] == pytest.approx(3)
    assert record['asked_score_donor_zero_minus_own_zero'] == pytest.approx(50)
    offset = next(r for r in summary['donor_baseline_offsets'] if r['row'] == 'prose_paren' and r['metric'] == 'asked_score')
    assert offset['mean'] == pytest.approx(50)
    assert offset['ci95'] == pytest.approx([50, 50])
    random = next(r for r in paired if r['row'] == 'prose_paren' and r['arm'] == R.RANDOM[0] and r['alpha'] == 2)
    assert random['baseline_arm'] == 'own' and random['asked_score_change'] == pytest.approx(.2)


def test_projection_changes_and_missing_sentiment_continuation_are_explicit():
    items, records = fixture()
    summary, _ = analyse(items, records)
    cell = next(c for c in summary['cells'] if c['row'] == 'python_string' and c['arm'] == 'own'
                and c['alpha'] == 2 and c['metric'] == 'projection_preanswer')
    assert cell['mean_paired_change'] == pytest.approx(10)
    missing = [c for c in summary['cells'] if c['row'] == 'prose_sentiment' and c['metric'] == 'continuation_score']
    assert len(missing) == 5*7
    assert all(c['status'] == 'UNAVAILABLE' and c['n_paired'] == 0 and c['mean_paired_change'] is None for c in missing)
    assert all(r['disconnected_classification'] == 'DESCRIPTIVE_ONLY_NO_ADDITIONAL_THRESHOLD' for r in summary['rows'])


def test_partial_grid_cannot_silently_pass_row_rule():
    items, records = fixture()
    records = [r for r in records if not (r['row'] in R.STRUCTURE[:2] and r['arm'] == 'own'
                                         and r['alpha'] == 4 and r['item_id'].endswith('_0'))]
    summary, paired = analyse(items, records)
    assert summary['n_missing_score_records'] == 2
    assert summary['population_status'] == 'PARTIAL'
    assert summary['prediction']['state_rows_not_evaluable'] == 2
    assert summary['prediction']['pathway_underweighted_observed'] is None
    assert sum(not r['score_record_present'] for r in paired) == 2
    assert all(r['registered_pattern_observed'] is None for r in summary['rows'][:2])


def test_cluster_bootstrap_preserves_template_blocks_and_is_deterministic():
    groups = ['a', 'a', 'b', 'b']
    weights = R._weights(groups, 20261025, 2000)
    np.testing.assert_array_equal(weights[:, 0], weights[:, 1])
    np.testing.assert_array_equal(weights[:, 2], weights[:, 3])
    np.testing.assert_array_equal(weights, R._weights(groups, 20261025, 2000))
    stats, _ = R._stats(np.array([0., 0., 10., 10.]), weights)
    assert stats[0]['mean'] == 5
    assert stats[0]['ci95'] == [0, 10]


@pytest.mark.parametrize('change', ['duplicate', 'cluster', 'alpha', 'nonfinite'])
def test_bad_score_records_fail_closed(change):
    items, records = fixture()
    if change == 'duplicate':
        records.append(dict(records[0]))
    elif change == 'cluster':
        records[0]['cluster'] = 'wrong'
    elif change == 'alpha':
        records[0]['alpha'] = 3
    else:
        records[0]['asked_score'] = float('nan')
    with pytest.raises(ValueError):
        analyse(items, records)


def sealed_fixture(tmp_path, monkeypatch):
    from projects.g_agreement.understand.e19 import freeze as F
    inputs, frozen, scores = [tmp_path/name for name in ('inputs', 'freeze', 'scores')]
    for directory in (inputs, frozen, scores):
        directory.mkdir()
    items, records = fixture()
    P.jsonl(inputs/'items.input.jsonl', [{'id': r['item_id'], 'feature': r['row'], 'cluster': r['cluster']} for r in items])
    P.dump(inputs/'continuation_pairs.json', {'rows': {r: {'primary_status': 'EVALUABLE'} for r in R.ROWS}})
    P.dump(inputs/'provenance.json', {'source_e3_input_seal_sha256': 'e'*64})
    P.seal(inputs, ['items.input.jsonl', 'continuation_pairs.json', 'provenance.json'], 'INPUTS_FROZEN_E19')
    P.dump(frozen/'FREEZE_SEAL.json', {'files': {}})
    monkeypatch.setattr(F, 'load_freeze', lambda _: ({'source': {'e3_input_seal_sha256': 'e'*64}}, {}))
    P.jsonl(scores/'scores.jsonl', records)
    P.dump(scores/'manifest.json', {'expected_items': items})
    provenance = {'experiment': 'E19', 'input_seal_sha256': P.sha(inputs/'INPUT_SEAL.json'),
                  'freeze_seal_sha256': P.sha(frozen/'FREEZE_SEAL.json'), 'freeze_commit': 'a'*40,
                  'source_files': {'source.py': 'b'*64}}
    P.dump(scores/'provenance.json', provenance)
    P.dump(scores/'RUN_STATUS.json', {'status': 'COMPLETE'})
    P.seal(scores, ['scores.jsonl', 'manifest.json', 'provenance.json', 'RUN_STATUS.json'], 'SCORES_SEALED_EXPLORATORY_E19')
    return inputs, frozen, scores


def test_verifies_score_seal_before_parsing_scores(tmp_path, monkeypatch):
    inputs, frozen, scores = sealed_fixture(tmp_path, monkeypatch)
    R.verify(scores, inputs, frozen)
    (scores/'scores.jsonl').write_text('malformed changed data')
    with pytest.raises(ValueError, match='seal mismatch'):
        R.verify(scores, inputs, frozen)


def test_resealed_wrong_freeze_binding_is_rejected(tmp_path, monkeypatch):
    inputs, frozen, scores = sealed_fixture(tmp_path, monkeypatch)
    provenance = json.loads((scores/'provenance.json').read_text())
    provenance['freeze_seal_sha256'] = 'c'*64
    P.dump(scores/'provenance.json', provenance)
    P.seal(scores, ['scores.jsonl', 'manifest.json', 'provenance.json', 'RUN_STATUS.json'], 'SCORES_SEALED_EXPLORATORY_E19')
    with pytest.raises(ValueError, match='provenance mismatch'):
        R.verify(scores, inputs, frozen)


def test_manifest_cannot_change_bootstrap_clusters(tmp_path, monkeypatch):
    inputs, frozen, scores = sealed_fixture(tmp_path, monkeypatch)
    manifest = json.loads((scores/'manifest.json').read_text())
    manifest['expected_items'][0]['cluster'] = 'changed-after-capture'
    P.dump(scores/'manifest.json', manifest)
    P.seal(scores, ['scores.jsonl', 'manifest.json', 'provenance.json', 'RUN_STATUS.json'], 'SCORES_SEALED_EXPLORATORY_E19')
    with pytest.raises(ValueError, match='template clusters'):
        R.verify(scores, inputs, frozen)


def test_no_invented_sentiment_continuation():
    items, records = fixture()
    next(r for r in records if r['row'] == 'prose_sentiment')['continuation_score'] = 1.
    with pytest.raises(ValueError, match='no frozen E15'):
        analyse(items, records)


def test_complete_report_writer_uses_2000_bootstraps_and_preserves_primary_seal(tmp_path, monkeypatch):
    from projects.g_agreement.understand.e19 import freeze as F
    inputs, frozen, scores = sealed_fixture(tmp_path, monkeypatch)
    items, records = fixture(84)
    for record in records:
        record.update(layer=21, sigma=2.)
    (inputs/'items.input.jsonl').unlink()
    P.jsonl(inputs/'items.input.jsonl', [{'id': r['item_id'], 'feature': r['row'], 'cluster': r['cluster']} for r in items])
    P.seal(inputs, ['items.input.jsonl', 'continuation_pairs.json', 'provenance.json'], 'INPUTS_FROZEN_E19')
    (scores/'scores.jsonl').unlink(); P.jsonl(scores/'scores.jsonl', records)
    P.dump(scores/'manifest.json', {'expected_items': items})
    provenance = json.loads((scores/'provenance.json').read_text())
    provenance['input_seal_sha256'] = P.sha(inputs/'INPUT_SEAL.json')
    P.dump(scores/'provenance.json', provenance)
    P.seal(scores, ['scores.jsonl', 'manifest.json', 'provenance.json', 'RUN_STATUS.json'], 'SCORES_SEALED_EXPLORATORY_E19')
    monkeypatch.setattr(F, 'load_freeze', lambda _: (
        {'source': {'e3_input_seal_sha256': 'e'*64}}, {r: {'layer': 21, 'sigma': 2.} for r in R.ROWS}))
    original_seal = (scores/'SCORE_SEAL.json').read_bytes()
    P.dump(scores/'budget.json', {'science_seconds': 2500., 'science_cap_seconds': 2400., 'cap_overrun_seconds': 100.})
    out, cache = tmp_path/'report', tmp_path/'paired'
    summary = R.generate(scores, inputs, frozen, out, cache)
    assert summary['method']['bootstrap_replicates'] == 2000
    assert summary['n_score_records'] == 17052
    assert summary['population_status'] == 'COMPLETE'
    assert summary['provenance']['selected_layers'] == {r: 21 for r in R.ROWS}
    assert summary['custody_telemetry']['status'] == 'CAP_OVERRUN_REPORTED'
    assert summary['custody_telemetry']['covered_by_primary_score_seal'] is False
    assert summary['custody_telemetry']['compliance_claim'] is False
    assert summary['custody_telemetry']['sha256'] == P.sha(scores/'budget.json')
    assert summary['prediction']['pathway_underweighted_observed'] is True  # Scientific rule unchanged by custody.
    assert 'no claim that the run stayed within budget' in (out/'RESULTS.md').read_text()
    assert (out/'RESULTS.md').read_text().startswith('Prediction:')
    assert (scores/'SCORE_SEAL.json').read_bytes() == original_seal
    P.verify(out, 'ANALYSIS_SEAL.json')
    assert summary['paired_items']['sha256'] == P.sha(cache/'paired_items.jsonl')
    with pytest.raises(FileExistsError):
        R.generate(scores, inputs, frozen, out, cache)
