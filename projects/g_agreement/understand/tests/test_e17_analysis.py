from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from projects.g_agreement.understand import e17_analysis as A


def test_rank_auc_and_bootstrap_preserve_twins_and_shared_cell_draws():
    y = np.tile([True, False], 4)
    perfect = np.tile([1., -1.], 4)
    draws = A.paired_resamples(4, n_boot=200)
    assert np.array_equal(draws[:, ::2] + 1, draws[:, 1::2])
    assert np.all(draws[:, ::2] % 2 == 0)
    tied, tied_boot = A.estimate(np.zeros(8), y, draws)
    high, high_boot = A.estimate(perfect, y, draws)
    assert tied == {'auroc': .5, 'ci95': [.5, .5]}
    assert high == {'auroc': 1., 'ci95': [1., 1.]}
    assert np.array_equal(A.paired_resamples(4, 200), draws)
    difference = A.contrast(high['auroc'], tied['auroc'], high_boot, tied_boot)
    assert difference['difference'] == .5 and difference['ci95'] == [.5, .5]
    assert difference['p_one_sided_bootstrap'] == 1/201
    assert A.auroc(-perfect, y) == 0  # no silent orientation rescue


def test_holm_keeps_three_rows_and_stepdown_order():
    assert A.holm([.04, .001, .02]) == pytest.approx([.04, .003, .04])
    assert A.holm([.5, .6, .7]) == [1., 1., 1.]
    with pytest.raises(ValueError, match='three'):
        A.holm([.01, .02])


def test_probe_only_fits_dev_and_predicts_test_without_refit():
    items = [{'id': str(i), 'feature': 'prose_paren', 'split': 'dev' if i < 2 else 'test',
              'cluster': 'dev_family' if i < 2 else 'test_family'} for i in range(4)]
    labels = {str(i): {'value': 'inside' if i % 2 == 0 else 'outside'} for i in range(4)}
    h = np.array([[2., 3.], [-2., -3.], [100000., 4.], [-100000., -4.]])
    calls = []
    def fit(x, y, lam):
        calls.append((x.clone(), y.clone(), lam))
        return SimpleNamespace(decision=lambda x: x[:, 0])
    scores, receipt, _ = A.fit_dev_scores(h, items, labels, 'prose_paren', fit_fn=fit)
    assert len(calls) == 1 and torch.equal(calls[0][0], torch.tensor(h[:2], dtype=torch.float32))
    assert calls[0][1].tolist() == [1, 0] and calls[0][2] == 1e-3
    assert scores['2'] == 100000 and receipt['n_dev'] == receipt['n_test'] == 2
    assert receipt['dev_ids'] == ['0', '1'] and receipt['test_ids'] == ['2', '3']
    items[3]['cluster'] = 'dev_family'
    with pytest.raises(ValueError, match='leakage'):
        A.fit_dev_scores(h, items, labels, 'prose_paren', fit_fn=fit)


def synthetic_row(feature, deltas, p=.0005, source=.01, window=.2, asked=True):
    contrasts = []
    for value in deltas:
        contrasts.append({'channels': {
            'continuation': {'difference': value, 'ci95': [value-.02, value+.02], 'p_one_sided_bootstrap': p},
            'source_probe': {'difference': source}, 'window_probe': {'difference': window}}})
    return {'feature': feature, 'contrasts': contrasts, 'p_row_one_sided': p,
            'asked_all_cells_at_most_060': asked}


def test_both_late_cells_required_and_thresholds_never_rescued():
    rows = [synthetic_row('prose_paren', [.2, .099]), synthetic_row('python_string', [.2, .2]),
            synthetic_row('list_depth', [.2])]
    summary = A.decision(rows)
    assert not rows[0]['direction_holds'] and rows[1]['direction_holds']
    assert summary['horizon_direction_outcome'] == 'PARTIAL'
    assert not summary['full_prediction_held']
    rows = [synthetic_row('prose_paren', [.10, .10]), synthetic_row('python_string', [.2, .2]),
            synthetic_row('list_depth', [.2], source=.0500001)]
    summary = A.decision(rows)
    assert rows[0]['direction_holds'] and not rows[2]['source_flat']
    assert summary['horizon_direction_outcome'] == 'PARTIAL'


def test_window_and_asked_failures_remain_visible_after_direction_pass():
    rows = [synthetic_row('prose_paren', [.2, .2]), synthetic_row('python_string', [.2, .2], asked=False),
            synthetic_row('list_depth', [.2], window=-.001)]
    summary = A.decision(rows)
    assert summary['horizon_direction_outcome'] == 'SUPPORTED'
    assert not summary['full_prediction_held']
    assert summary['plain_assessment'] == 'The directional prediction held, but the full prediction did not hold.'


def test_incomplete_capture_fails_before_labels_or_lock(monkeypatch, tmp_path):
    monkeypatch.setattr(A.R, 'inputs', lambda _bank: ([], {}, {}))
    opened = []
    monkeypatch.setattr(A, 'label_join', lambda *args: opened.append('labels'))
    def fail(*args):
        raise ValueError('missing complete output seal')
    monkeypatch.setattr(A.P, 'verify', fail)
    with pytest.raises(ValueError, match='missing complete'):
        A.analyse(tmp_path/'bank', tmp_path/'outputs', tmp_path/'labels', tmp_path/'analysis')
    assert opened == [] and not (tmp_path/'analysis.lock.json').exists()


def test_lock_is_create_exclusive_and_never_replaced(tmp_path):
    outputs = tmp_path/'outputs'
    outputs.mkdir()
    (outputs/'SCORE_SEAL.json').write_text('{}')
    path = A.acquire_lock(tmp_path/'analysis', outputs)
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        A.acquire_lock(tmp_path/'analysis', outputs)
    assert path.read_bytes() == original


def test_analysis_spec_freezes_no_new_pair_selection_and_item_bootstrap():
    assert A.METRIC_SPEC['seed'] == 20261025 and A.METRIC_SPEC['bootstrap_samples'] == 2000
    assert 'no E17 validity selection' in A.METRIC_SPEC['continuation']
    assert 'preserving A/B' in A.METRIC_SPEC['bootstrap']
    assert 'no equivalence claim' in A.METRIC_SPEC['source_flat']


def test_synthetic_end_to_end_report_seals_all_outputs(monkeypatch, tmp_path):
    """Synthetic numbers only: exercise report, serialization and once-only closure."""
    items, labels, scores = [], {}, {}
    for feature, cells in A.CELLS.items():
        for cell in cells:
            for index in range(96):
                for side in range(2):
                    key = f'{feature}:{cell}:{index}:{side}'
                    split = 'dev' if index < 32 else 'test'
                    item = {'id': key, 'feature': feature, 'cell': cell, 'split': split,
                            'cluster': split, 'pair_id': f'{feature}:{cell}:{index}'}
                    items.append(item)
                    labels[key] = {**item, 'lexical_id': str(index), 'value': A.VALUES[feature][side]}
                    revealing = cell in ('short_late', 'long_late', 'line_end')
                    for channel in A.R.CHANNELS:
                        for arm in A.R.ARMS:
                            value = (1. if side == 0 else -1.) if channel == 'continuation' and revealing else 0.
                            if arm == 'random_donor':
                                value = 0.
                            if arm == 'opposite_swap':
                                value = -value
                            scores[key, channel, arm] = {'scores': [value, value]}
    def fit(_h, _items, _labels, feature):
        values = {}
        for item in items:
            if item['feature'] != feature:
                continue
            sign = 1. if labels[item['id']]['value'] == A.VALUES[feature][0] else -1.
            values[item['id']] = sign
        model = SimpleNamespace(w=torch.ones(2), mu=torch.zeros(2), sd=torch.ones(2), b=0.)
        return values, {'feature': feature, 'fit_split': 'dev'}, model
    monkeypatch.setattr(A, 'fit_dev_scores', fit)
    monkeypatch.setattr(A, 'verify_prelabel', lambda *_: (items, {'source_probe': None, 'window_probe': None}, scores))
    monkeypatch.setattr(A, 'label_join', lambda *_: labels)
    original_draws = A.paired_resamples
    monkeypatch.setattr(A, 'paired_resamples', lambda n: original_draws(n, 200))
    bank, outputs, out = tmp_path/'bank', tmp_path/'outputs', tmp_path/'analysis'
    bank.mkdir(); outputs.mkdir()
    (bank/'INPUT_SEAL.json').write_text('{}')
    (outputs/'SCORE_SEAL.json').write_text('{}')
    label_file = tmp_path/'labels.jsonl'; label_file.write_text('{}')
    summary = A.analyse(bank, outputs, label_file, out)
    assert summary['horizon_direction_outcome'] == 'SUPPORTED'
    assert not summary['full_prediction_held']  # synthetic window probe is flat across cells
    seal = A.P.verify(out, 'ANALYSIS_SEAL.json')
    assert seal['status'] == 'E17_ANALYSIS_COMPLETE'
    assert (out/'CELL_CORRELATIONS.svg').is_file()
    assert (out/'RESULTS.md').read_text().startswith('**Prediction (§110):**')
    assert len(A.P.rows(out/'predictions.jsonl')) == 1280
    with pytest.raises(ValueError, match='never repeat'):
        A.analyse(bank, outputs, label_file, out)
