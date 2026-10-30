"""Synthetic-only CPU checks for frozen E35 probe plumbing, 2026-10-25."""
import importlib.util
from pathlib import Path

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('e35_decomp_probes_under_test', HERE / 'decomp_probes.py')
P = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(P)


def metadata():
    return [{'id': f'{row}/{split}/{i}', 'row': row, 'split': split,
             'label': i % 2, 'cluster': f'{split}/template-{i // 14}'}
            for row in P.ROWS for split in ('dev', 'test') for i in range(84)]


def test_complete_metadata_and_frozen_population():
    P.validate_production_metadata(metadata())
    assert len(P.ROWS) == 25
    assert P.ROOT / P.SOURCE_DIR == HERE.parents[3] / P.SOURCE_DIR


@pytest.mark.parametrize('change', ['duplicate_id', 'cluster_leak', 'balance', 'row', 'split', 'label', 'size'])
def test_invalid_production_population_rejected(change):
    records = metadata()
    if change == 'duplicate_id':
        records[-1]['id'] = records[0]['id']
    elif change == 'cluster_leak':
        records[84]['cluster'] = records[0]['cluster']
    elif change == 'balance':
        records[0]['label'] = 1
    elif change == 'row':
        records[0]['row'] = 'unregistered_row'
    elif change == 'split':
        records[0]['split'] = 'train'
    elif change == 'label':
        records[0]['label'] = True
    elif change == 'size':
        records.pop()
    with pytest.raises(ValueError):
        P.validate_production_metadata(records)


def test_row_densification_preserves_selection_and_zero_codes():
    indices = np.array([[1, 3], [0, 2], [3, 0]])
    values = np.array([[2, 7], [0, 0], [5, 1]], dtype=float)
    result = P.densify_row(indices, values, [2, 1], 4)
    np.testing.assert_array_equal(result, [[1, 0, 0, 5], [0, 0, 0, 0]])
    assert result.dtype == np.float32


@pytest.mark.parametrize('indices,values,selected,n_latents', [
    ([[0, 0]], [[1, 2]], [0], 3),
    ([[0, 3]], [[1, 2]], [0], 3),
    ([[0, -1]], [[1, 2]], [0], 3),
    ([[0, 1]], [[1, -2]], [0], 3),
    ([[0, 1]], [[1, float('nan')]], [0], 3),
    ([[0, 1]], [[1, 2]], [0, 0], 3),
    ([[0, 1]], [[1, 2]], [1], 3),
    ([[0.0, 1.0]], [[1, 2]], [0], 3),
])
def test_corrupt_sparse_codes_rejected(indices, values, selected, n_latents):
    with pytest.raises(ValueError):
        P.densify_row(indices, values, selected, n_latents)


def test_fitting_requires_explicit_verified_runtime_authorization(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('pinned library must not load before authorization')
    monkeypatch.setattr(P, 'load_pinned_library', forbidden)
    with pytest.raises(PermissionError):
        P.fit_row_probe(None, None, None, None)
    with pytest.raises(PermissionError):
        P.run_per_row_probes(None, None, None)


@pytest.mark.parametrize('filename', ['probes.py', 'metrics.py'])
def test_source_mutation_rejected_before_import(tmp_path, filename):
    folder = tmp_path / P.SOURCE_DIR
    folder.mkdir(parents=True)
    for name in P.SOURCE_SHA256:
        (folder / name).write_bytes((P.ROOT / P.SOURCE_DIR / name).read_bytes())
    with (folder / filename).open('a') as stream:
        stream.write('\n# synthetic corruption\n')
    with pytest.raises(ValueError, match='source hash mismatch'):
        P.load_pinned_library(tmp_path)


def test_actual_pinned_recipe_with_zero_variance_and_test_labels_not_used_for_fit():
    import torch
    threads = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        dev_x = np.array([[0, 2, 0], [1, 2, 0], [3, 2, 0], [4, 2, 0]], dtype=float)
        test_x = np.array([[0.5, 100, 0], [3.5, 100, 0]], dtype=float)
        report = P.fit_row_probe(dev_x, [0, 0, 1, 1], test_x, [0, 1], authorized=True)
        reverse = P.fit_row_probe(dev_x, [0, 0, 1, 1], test_x, [1, 0], authorized=True)
        assert report['auroc'] == 1.0
        assert reverse['auroc'] == 0.0
        assert report['lam'] == 1e-3 and report['iters'] == 200
        assert report['fit_split'] == 'dev' and report['descriptive_only'] is True
        assert 'ci95' not in report and 'held' not in report
        probes, _ = P.load_pinned_library()
        model = probes.fit_logreg(torch.as_tensor(dev_x), torch.tensor([0, 0, 1, 1]), lam=1e-3, iters=200)
        np.testing.assert_array_equal(model.mu.numpy(), [2, 2, 0])
        assert float(model.sd[1]) == pytest.approx(1e-4)
    finally:
        torch.set_num_threads(threads)


def test_production_driver_handles_rows_and_terms_without_other_rows_dense(monkeypatch):
    records = metadata()
    indices = np.tile([[0, 1]], (len(records), 1))
    values = np.ones_like(indices, dtype=float)
    calls = []
    def synthetic_fit(dev_x, dev_y, test_x, test_y, *, authorized, root):
        assert authorized is True
        assert dev_x.shape == test_x.shape == (84, 3)
        assert sum(dev_y) == sum(test_y) == 42
        calls.append(1)
        return {'auroc': 0.5, 'descriptive_only': True}
    monkeypatch.setattr(P, 'fit_row_probe', synthetic_fit)
    reports = P.run_per_row_probes(records, {term: (indices, values) for term in P.TERMS},
                                   3, authorized=True)
    assert len(calls) == len(reports) == 75
    assert {(r['row'], r['term']) for r in reports} == {(r, t) for r in P.ROWS for t in P.TERMS}
