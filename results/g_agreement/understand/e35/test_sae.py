"""Tiny synthetic E35 SAE contract tests, dated 2026-10-25; no model data."""

import importlib.util
from pathlib import Path

import pytest
import torch


_SPEC = importlib.util.spec_from_file_location("e35_sae_under_test", Path(__file__).with_name("sae.py"))
sae_module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(sae_module)
QwenScopeSAE = sae_module.QwenScopeSAE


def parameters():
    return {
        "W_enc": torch.tensor([[1.0, 0.0], [-1.0, 0.0], [0.0, 1.0]]),
        "W_dec": torch.tensor([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]),
        "b_enc": torch.zeros(3),
        "b_dec": torch.tensor([10.0, 20.0]),
    }


def test_relu_zero_selected_by_topk_is_dead():
    sae = QwenScopeSAE(parameters(), k=2)
    x = torch.tensor([[-2.0, -3.0]])
    torch.testing.assert_close(sae.encode(x), torch.tensor([[0.0, 2.0, 0.0]]))
    reconstructed, fired = sae.reconstruct_and_fired(x)
    assert fired.dtype == torch.bool
    assert fired.tolist() == [False, True, False]
    torch.testing.assert_close(reconstructed, torch.tensor([[14.0, 30.0]]))


def test_encoder_does_not_subtract_decoder_bias_or_normalize_input():
    params = parameters()
    params["b_enc"] = torch.tensor([0.5, 0.25, 1.0])
    sae = QwenScopeSAE(params, k=2)
    x = torch.tensor([[2.0, 3.0]], dtype=torch.float64)
    expected = torch.tensor([[2.5, 0.0, 4.0]])
    torch.testing.assert_close(sae.encode(x), expected)
    altered = {**params, "b_dec": torch.tensor([-100.0, 50.0])}
    torch.testing.assert_close(QwenScopeSAE(altered, k=2).encode(x), expected)
    assert sae.encode(x).dtype == torch.float32


def test_decoder_orientation_bias_and_batch_dimensions():
    sae = QwenScopeSAE(parameters(), k=2)
    code = torch.tensor([[[1.0, 2.0, 3.0], [0.0, 0.0, 0.0]]])
    expected = torch.tensor([[[24.0, 52.0], [10.0, 20.0]]])
    torch.testing.assert_close(sae.decode(code), expected)
    x = torch.tensor([[[2.0, -3.0]], [[-2.0, 3.0]]])
    reconstructed, fired = sae.reconstruct_and_fired(x)
    assert reconstructed.shape == (2, 1, 2)
    assert fired.shape == (3,)
    assert fired.tolist() == [True, True, True]


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_nonfinite_inputs_parameters_and_codes_fail_closed(bad):
    sae = QwenScopeSAE(parameters(), k=2)
    with pytest.raises(ValueError, match="non-finite"):
        sae.reconstruct_and_fired(torch.tensor([[bad, 0.0]]))
    with pytest.raises(ValueError, match="non-finite"):
        sae.decode(torch.tensor([[0.0, bad, 0.0]]))
    params = parameters()
    params["W_enc"][0, 0] = bad
    with pytest.raises(ValueError, match="non-finite"):
        QwenScopeSAE(params, k=2)


def test_finite_inputs_with_overflowing_preactivations_fail_closed():
    params = parameters()
    params["W_enc"][0, 0] = torch.finfo(torch.float32).max
    sae = QwenScopeSAE(params, k=2)
    with pytest.raises(ValueError, match="preactivations"):
        sae.reconstruct_and_fired(torch.tensor([[2.0, 0.0]]))


def test_fired_reduction_rechecks_nonfinite_code(monkeypatch):
    sae = QwenScopeSAE(parameters(), k=2)
    monkeypatch.setattr(sae, "encode", lambda _: torch.tensor([[0.0, float("nan"), 0.0]]))
    with pytest.raises(ValueError, match="before fired reduction"):
        sae.reconstruct_and_fired(torch.ones(1, 2))


@pytest.mark.parametrize("shape", [(3,), (1, 3), (0, 2)])
def test_input_shape_validation(shape):
    sae = QwenScopeSAE(parameters(), k=2)
    with pytest.raises(ValueError, match="last dimension"):
        sae.encode(torch.zeros(shape))


def test_parameter_shape_keys_and_k_validation():
    params = parameters()
    with pytest.raises(ValueError, match="shapes disagree"):
        QwenScopeSAE({**params, "W_dec": params["W_dec"].T}, k=2)
    with pytest.raises(ValueError, match="exactly"):
        QwenScopeSAE({**params, "unexpected": torch.zeros(1)}, k=2)
    for k in (0, 4, True, 1.5):
        with pytest.raises(ValueError, match="k must"):
            QwenScopeSAE(params, k=k)
    with pytest.raises(ValueError, match="negative"):
        QwenScopeSAE(params, k=2).decode(torch.tensor([[-1.0, 0.0, 0.0]]))


def test_fp32_even_under_cpu_autocast():
    sae = QwenScopeSAE(parameters(), k=2)
    x = torch.tensor([[2.0, 3.0]])
    reference, _ = sae.reconstruct_and_fired(x)
    with torch.autocast(device_type="cpu", dtype=torch.bfloat16):
        actual, _ = sae.reconstruct_and_fired(x)
    assert actual.dtype == torch.float32
    torch.testing.assert_close(actual, reference, rtol=0, atol=0)


def test_streaming_hash_and_digest_rejection_before_torch_load(tmp_path, monkeypatch):
    path = tmp_path / "synthetic.pt"
    path.write_bytes(b"abc")
    assert sae_module.sha256_file(path) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    monkeypatch.setattr(sae_module.torch, "load", lambda *a, **kw: pytest.fail("Unverified checkpoint was loaded"))
    with pytest.raises(ValueError, match="SHA-256"):
        QwenScopeSAE.from_checkpoint(path)


def test_production_loader_uses_weights_only_and_rejects_tiny_dimensions(tmp_path, monkeypatch):
    path = tmp_path / "synthetic.pt"
    path.write_bytes(b"abc")
    monkeypatch.setattr(sae_module, "sha256_file", lambda _: sae_module.PINNED_SHA256)
    monkeypatch.setattr(sae_module, "PINNED_BYTES", 3)
    calls = []

    def fake_load(*args, **kwargs):
        calls.append((args, kwargs))
        return parameters()

    monkeypatch.setattr(sae_module.torch, "load", fake_load)
    with pytest.raises(ValueError, match="d_model=5120 and d_sae=81920"):
        QwenScopeSAE.from_checkpoint(path)
    assert calls == [((path,), {"map_location": "cpu", "weights_only": True})]
