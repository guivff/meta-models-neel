"""Synthetic CPU tests for the E35 registered gate (2026-10-25)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest


_spec = importlib.util.spec_from_file_location(
    "e35_gate_math", Path(__file__).with_name("gate_math.py"))
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
GateAccumulator = _module.GateAccumulator
N = _module.HELDOUT_TOKENS


def alternating():
    return np.tile(np.array([[-1.0], [1.0]]), (N // 2, 1))


def test_fvu_boundary_is_inclusive_and_dead_boundary_exclusive():
    x = alternating()
    mask = np.ones(10, dtype=bool)
    at_limit = GateAccumulator(1, 10).update(x, 0.5 * x, active_latents=mask).result()
    assert at_limit["fvu"] == 0.25
    assert at_limit["passed"] is True
    above = GateAccumulator(1, 10).update(x, 0.499999999 * x,
                                        active_latents=mask).result()
    assert above["fvu"] > 0.25
    assert above["fvu_pass"] is False
    assert above["passed"] is False
    mask[-1] = False
    dead_limit = GateAccumulator(1, 10).update(x, x, active_latents=mask).result()
    assert dead_limit["dead_fraction"] == 0.10
    assert dead_limit["dead_pass"] is False
    assert dead_limit["passed"] is False


def test_global_mean_includes_variance_between_constant_batches():
    a = GateAccumulator(1, 11)
    mask = np.ones(11, dtype=bool)
    for value in (-1.0, 1.0):
        x = np.full((N // 2, 1), value)
        a.update(x, 0.5 * x, active_latents=mask)
    r = a.result()
    assert r["total_variance"] == N
    assert r["squared_error"] == N / 4
    assert r["passed"] is True


def test_dense_codes_count_positive_ever_not_absolute_or_last_batch():
    x = alternating()
    z1 = np.zeros((N // 2, 11))
    z2 = np.zeros_like(z1)
    z1[0, :5] = 1
    z2[0, 5:10] = 1
    z1[:, 10] = -2  # Negative-only latent is dead under >0 activity.
    a = GateAccumulator(1, 11)
    a.update(x[:N // 2], x[:N // 2], z1)
    a.update(x[N // 2:], x[N // 2:], z2)
    r = a.result()
    assert r["dead_latents"] == 1
    assert r["dead_fraction"] == 1 / 11
    assert r["passed"] is True


def test_large_offset_streaming_and_merge_agree_with_centered_reference():
    rng = np.random.default_rng(273)
    x = 1e8 + rng.normal(size=(N, 3))
    xr = x + rng.normal(scale=0.1, size=x.shape)
    mask = np.ones(3, dtype=bool)
    whole = GateAccumulator(3, 3).update(x, xr, active_latents=mask).result()
    stream = GateAccumulator(3, 3)
    for ids in np.array_split(np.arange(N), 97):
        stream.update(x[ids], xr[ids], active_latents=mask)
    left = GateAccumulator(3, 3).update(x[:12345], xr[:12345], active_latents=mask)
    right = GateAccumulator(3, 3).update(x[12345:], xr[12345:], active_latents=mask)
    right_count = right.n_tokens
    merged = left.merge(right).result()
    assert right.n_tokens == right_count
    for r in (stream.result(), merged):
        assert r["fvu"] == pytest.approx(whole["fvu"], rel=1e-8)
        assert r["total_variance"] == pytest.approx(whole["total_variance"], rel=1e-8)
        assert r["squared_error"] == pytest.approx(whole["squared_error"], rel=1e-12)
        assert r["passed"] is True


def test_missing_extra_empty_tokens_fail_closed_without_mutation():
    a = GateAccumulator(1, 1)
    with pytest.raises(ValueError, match="exactly 50,000"):
        a.result()
    with pytest.raises(ValueError, match="nonempty"):
        a.update(np.empty((0, 1)), np.empty((0, 1)), np.empty((0, 1)))
    x = alternating()
    a.update(x[:-1], x[:-1], active_latents=np.ones(1, dtype=bool))
    with pytest.raises(ValueError, match="exactly 50,000"):
        a.result()
    with pytest.raises(ValueError, match="more than 50,000"):
        a.update(x[:2], x[:2], active_latents=np.ones(1, dtype=bool))
    assert a.n_tokens == N - 1
    a.update(x[-1:], x[-1:], active_latents=np.ones(1, dtype=bool))
    before = a.result()
    with pytest.raises(ValueError, match="more than 50,000"):
        a.update(x[:1], x[:1], active_latents=np.ones(1, dtype=bool))
    assert a.result() == before


@pytest.mark.parametrize("where", ["activations", "reconstruction", "codes"])
@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_nonfinite_inputs_rejected_atomically(where, value):
    values = {name: np.ones((2, 1)) for name in ("activations", "reconstruction", "codes")}
    values[where][0, 0] = value
    a = GateAccumulator(1, 1)
    with pytest.raises(ValueError, match="finite real"):
        a.update(**values)
    assert a.n_tokens == 0


@pytest.mark.parametrize("kwargs", [
    {},
    {"codes": np.ones((2, 1)), "active_latents": np.ones(1, dtype=bool)},
    {"active_latents": np.ones(1)},
    {"active_latents": np.ones((1, 1), dtype=bool)},
    {"active_latents": np.ones(2, dtype=bool)},
    {"codes": np.ones((1, 1))},
    {"codes": np.ones((2, 2))},
])
def test_bad_activity_inputs_rejected(kwargs):
    a = GateAccumulator(1, 1)
    with pytest.raises(ValueError):
        a.update(np.ones((2, 1)), np.ones((2, 1)), **kwargs)
    assert a.n_tokens == 0


@pytest.mark.parametrize("x,xr", [
    (np.ones(2), np.ones((2, 1))),
    (np.ones((2, 2)), np.ones((2, 1))),
    (np.ones((2, 1)), np.ones((1, 1))),
    (np.ones((2, 1), dtype=complex), np.ones((2, 1))),
    (np.array([["1"], ["2"]]), np.ones((2, 1))),
])
def test_bad_activation_shapes_and_types_rejected(x, xr):
    a = GateAccumulator(1, 1)
    with pytest.raises(ValueError):
        a.update(x, xr, active_latents=np.ones(1, dtype=bool))
    assert a.n_tokens == 0


def test_zero_variance_and_numeric_overflow_are_invalid_not_gate_passes():
    a = GateAccumulator(1, 1)
    x = np.ones((N, 1))
    a.update(x, x, active_latents=np.ones(1, dtype=bool))
    with pytest.raises(ValueError, match="zero pooled"):
        a.result()
    b = GateAccumulator(1, 1)
    with pytest.raises(ValueError, match="pooled moments"):
        b.update(np.array([[-1e308], [1e308]]), np.zeros((2, 1)),
                 active_latents=np.ones(1, dtype=bool))
    assert b.n_tokens == 0


def test_merge_rejects_invalid_identity_dimensions_and_token_total():
    a = GateAccumulator(1, 1)
    with pytest.raises(ValueError, match="itself"):
        a.merge(a)
    with pytest.raises(ValueError, match="dimensions"):
        a.merge(GateAccumulator(1, 2))
    with pytest.raises(TypeError):
        a.merge(None)
    a.merge(GateAccumulator(1, 1))
    assert a.n_tokens == 0
    x = alternating()
    a.update(x, x, active_latents=np.ones(1, dtype=bool))
    b = GateAccumulator(1, 1).update(x[:1], x[:1], active_latents=np.ones(1, dtype=bool))
    before = a.result()
    with pytest.raises(ValueError, match="more than 50,000"):
        a.merge(b)
    assert a.result() == before


@pytest.mark.parametrize("dims", [(0, 1), (1, -1), (True, 1), (1, 1.5)])
def test_dimensions_require_positive_integers(dims):
    with pytest.raises(ValueError, match="positive integer"):
        GateAccumulator(*dims)
