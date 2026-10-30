"""CPU checks; synthetic check receipts never claim real Qwen CUDA parity."""
from types import SimpleNamespace
import json

import numpy as np
import pytest
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand.attention_check import (
    check_equivalence, equivalence_items, forecast_lower_bound,
    retain_calibrations, sealed_calibrations,
)
from projects.g_agreement.understand.reader_runtime import ReaderRuntime
from projects.g_agreement.understand.tests.test_reader_runtime import oracle, vectors


def prior(tmp_path):
    directory = tmp_path/'previous'
    (directory/'calibration').mkdir(parents=True)
    seals = {'primary': 'e4', 'e9': 'e9'}
    P.dump(directory/'provenance.json', {'experiment': 'E4', 'input_seals': seals})
    P.dump(directory/'RUN_STATUS.json', {'status': 'STOPPED_PARTIAL'})
    names = ['provenance.json', 'RUN_STATUS.json']
    for phase in ('olens', 'nla', 'jlens'):
        name = f'calibration/{phase}.json'
        P.dump(directory/name, {'warmups': 1, 'batch': 1, 'units': 2100,
            'timings_seconds': [1., 2., 3.], 'forecast_seconds': 4200.})
        names.append(name)
    P.seal(directory, names, 'SCORES_SEALED_EXPLORATORY_E4')
    return directory, seals


def test_sealed_reuse_bytes_and_no_fit_lower_bound(tmp_path):
    directory, seals = prior(tmp_path)
    target = tmp_path/'retained'
    receipts = retain_calibrations(directory, target, seals)
    for file in directory.rglob('*.json'):
        assert file.read_bytes() == (target/file.relative_to(directory)).read_bytes()
    result = forecast_lower_bound(receipts)
    assert result['status'] == 'NO_FIT_DO_NOT_LAUNCH'
    assert result['reader_forecast_seconds'] == 12600.
    assert result['excess_seconds_at_least'] == 10440.
    with pytest.raises(FileExistsError):
        retain_calibrations(directory, target, seals)
    with pytest.raises(ValueError, match='population mismatch'):
        sealed_calibrations(directory, {'primary': 'other', 'e9': 'e9'})
    (directory/'calibration/nla.json').write_text('{}')
    with pytest.raises(ValueError, match='seal mismatch'):
        sealed_calibrations(directory, seals)


def data():
    return {'items': [{'id': key, 'feature': 'row', 'split': split}
                      for key, split in [('z', 'dev'), ('d', 'test'), ('c', 'test'),
                                         ('b', 'test'), ('a', 'test'), ('e', 'test')]],
            'activations': {44: np.ones((6, 6), dtype=np.float32)},
            'templates': {'row': {'olens': [('a', 'b'), ('c', 'd')]}}}


class SyntheticOracle:
    name = 'olens'
    device = torch.device('cuda')  # Metadata only. All tensors remain on CPU.

    def __init__(self, delta):
        self.delta = delta
        self.calls = 0
        self.model = torch.nn.Linear(1, 1)
        self.model.config = SimpleNamespace(_attn_implementation='sdpa')

    def asked(self, acts, pairs, batch):
        assert not torch.is_grad_enabled() and batch == 2 and acts.shape == (1, 6)
        self.calls += 1
        flash = torch.backends.cuda.flash_sdp_enabled()
        assert flash != torch.backends.cuda.math_sdp_enabled()
        return torch.tensor([0. if flash else self.delta], dtype=torch.float64)


@pytest.mark.parametrize('delta,passed', [(0.01, True), (0.010001, False)])
def test_equivalence_absolute_boundary_and_receipt(tmp_path, delta, passed):
    model = SyntheticOracle(delta)
    path = tmp_path/'equivalence.json'
    before = (torch.backends.cuda.flash_sdp_enabled(), torch.backends.cuda.math_sdp_enabled())
    if passed:
        check_equivalence(model, data(), path)
    else:
        with pytest.raises(ValueError, match='INCOMPLETE'):
            check_equivalence(model, data(), path)
    result = json.loads(path.read_text())
    assert result['status'] == ('PASS' if passed else 'FAIL')
    assert [i['id'] for i in result['items']] == ['a', 'b', 'c', 'd']
    assert model.calls == 8
    assert before == (torch.backends.cuda.flash_sdp_enabled(), torch.backends.cuda.math_sdp_enabled())
    with pytest.raises(ValueError, match='already exists'):
        check_equivalence(model, data(), path)
    assert model.calls == 8


@pytest.mark.parametrize('failure', ['cpu', 'dispatch', 'nonfinite', 'kernel'])
def test_check_errors_are_recorded_and_do_not_retry(tmp_path, failure):
    model = SyntheticOracle(0.)
    if failure == 'cpu':
        model.device = torch.device('cpu')
    elif failure == 'dispatch':
        model.model.config._attn_implementation = 'eager'
    elif failure == 'nonfinite':
        model.delta = float('nan')
    else:
        def unavailable(*a, **kw):
            raise RuntimeError('unsupported flash kernel')
        model.asked = unavailable
    path = tmp_path/'error.json'
    before = (torch.backends.cuda.flash_sdp_enabled(), torch.backends.cuda.math_sdp_enabled())
    with pytest.raises((ValueError, RuntimeError)):
        check_equivalence(model, data(), path)
    result = json.loads(path.read_text())
    assert result['status'] == 'ERROR' and result['error']
    assert before == (torch.backends.cuda.flash_sdp_enabled(), torch.backends.cuda.math_sdp_enabled())


def test_selection_uses_only_test_ids():
    sample = data()
    assert [sample['items'][i]['id'] for i in equivalence_items(sample)] == ['a', 'b', 'c', 'd']
    sample['items'] = sample['items'][:4]
    with pytest.raises(ValueError, match='four distinct'):
        equivalence_items(sample)


class AttentionBlock(torch.nn.Module):
    def forward(self, hidden):
        assert torch.backends.cuda.math_sdp_enabled()
        assert not torch.backends.cuda.flash_sdp_enabled()
        assert not torch.backends.cuda.mem_efficient_sdp_enabled()
        x = hidden[:, None]
        return hidden + torch.nn.functional.scaled_dot_product_attention(x, x, x, is_causal=True)[:, 0]


def test_target_math_sdpa_second_derivative_matches_finite_difference():
    reader = oracle()
    reader.model.layers[2] = AttentionBlock()
    runtime = ReaderRuntime('target', reader)
    h = vectors()[:1]
    u = torch.randn_like(h)
    seq = [[3, 5, 8, 2]]
    before = (torch.backends.cuda.flash_sdp_enabled(), torch.backends.cuda.math_sdp_enabled())
    exact = runtime.target_directional(h, seq, u, layer=1)['derivatives']
    assert before == (torch.backends.cuda.flash_sdp_enabled(), torch.backends.cuda.math_sdp_enabled())

    def direct(x):
        def inject(_module, _inputs, hidden):
            hidden = hidden.clone()
            hidden[:, -1] = x
            return hidden
        handle = reader.model.layers[1].register_forward_hook(inject)
        try:
            with sdpa_kernel(SDPBackend.MATH):
                return reader.model(input_ids=torch.tensor(seq), logits_to_keep=1).logits[:, -1]
        finally:
            handle.remove()

    eps = 1e-3
    finite = (direct(h+eps*u)-direct(h-eps*u))/(2*eps)
    assert torch.allclose(exact, finite, atol=2e-3, rtol=0.01)
