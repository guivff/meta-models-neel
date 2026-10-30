import json
import numpy as np
import pytest
from projects.g_agreement.e96.reconstructor_check import inputs, write, digest, check_prediction, remaining_budget


def make_inputs(tmp_path):
    write(tmp_path / 'item.json', {'id': 'sealed-id', 'oracle_text': 'saved oracle',
          'nla_text': 'saved nla', 'source_seals': ['a' * 64]})
    for n in ('h44.npy', 'h42.npy'):
        np.save(tmp_path / n, np.ones((1, 5120), dtype='float32'))
    reseal(tmp_path)
    return tmp_path


def reseal(root):
    write(root / 'INPUT_SEAL.json', {'files': {n: digest(root / n)
          for n in ('item.json', 'h44.npy', 'h42.npy')}})


def test_valid_one_item_and_no_gpu(tmp_path):
    item, acts = inputs(make_inputs(tmp_path))
    assert item['id'] == 'sealed-id'
    assert acts['oracle'].shape == (1, 5120)


def test_rejects_tampered_text(tmp_path):
    root = make_inputs(tmp_path)
    (root / 'item.json').write_text('{}')
    with pytest.raises(ValueError, match='hash mismatch'):
        inputs(root)


def test_rejects_labels_even_when_sealed(tmp_path):
    root = make_inputs(tmp_path)
    item = json.loads((root / 'item.json').read_text())
    item['answer'] = 'private'
    write(root / 'item.json', item)
    reseal(root)
    with pytest.raises(ValueError, match='schema'):
        inputs(root)


@pytest.mark.parametrize('value', [np.zeros((1, 5120)), np.ones((2, 5120)), np.full((1, 5120), np.nan)])
def test_rejects_bad_activation(tmp_path, value):
    root = make_inputs(tmp_path)
    np.save(root / 'h42.npy', value)
    reseal(root)
    with pytest.raises(ValueError, match='invalid one-item'):
        inputs(root)


def test_prediction_checks_shape_and_finiteness():
    import torch
    gold = np.ones((1, 5120), dtype='float32')
    _, metrics = check_prediction(torch.ones((1, 5120)), gold)
    assert metrics['raw_mse'] == 0
    assert metrics['unit_scaled_mse'] == 0
    with pytest.raises(ValueError):
        check_prediction(torch.full((1, 5120), float('inf')), gold)


def test_staging_consumes_allocation_cap():
    assert remaining_budget(1000, 2800, 2200) == 600
    with pytest.raises(ValueError):
        remaining_budget(1000, 4000, 2200)
    with pytest.raises(ValueError):
        remaining_budget(1000, 2800, 2800)
