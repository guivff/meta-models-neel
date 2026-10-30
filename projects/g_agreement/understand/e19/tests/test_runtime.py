"""Offline E19 intervention placement, native parity and control-norm checks."""
import pytest
import torch

from projects.g_agreement.understand.e19.runtime import E19Runtime
from projects.g_agreement.understand.reader_runtime import ReaderRuntime
from projects.g_agreement.understand.tests.test_reader_runtime import oracle, vectors, PAIRS


def runtime(batch=32):
    return E19Runtime(ReaderRuntime("olens", oracle()), candidate_batch=batch)


def unit(index=0):
    result = torch.zeros(6)
    result[index] = 1
    return result


def observers(model, layer):
    before, after, next_layer = [], [], []
    handles = [
        model.layers[layer].register_forward_hook(lambda _m, _i, out: before.append(out.detach().clone())),
        model.layers[layer+1].register_forward_pre_hook(lambda _m, inp: after.append(inp[0].detach().clone())),
        model.layers[layer+1].register_forward_hook(lambda _m, _i, out: next_layer.append(out.detach().clone())),
    ]
    return before, after, next_layer, handles


def test_alpha_zero_exact_w1_parity_and_no_autograd():
    rt = runtime()
    h = vectors().requires_grad_(True)
    expected = rt.oracle.asked(h, PAIRS).detach()
    out = rt.score(h, PAIRS, layer=1, direction=unit(), sigma=2, alpha=0)
    assert torch.equal(out["scores"], expected)
    assert out["per_pair_scores"].shape == (3, 2)
    assert out["projection_preanswer"].shape == (3, 2, 2)
    assert out["projection_answer_mean"].shape == (3, 2, 2)
    assert not out["scores"].requires_grad and h.grad is None
    assert all(p.grad is None for p in rt.oracle.model.parameters())
    assert all(not block._forward_hooks for block in rt.oracle.model.layers)
    assert out["metadata"]["requested_edit_norm"] == 0


def test_e15_prefix_native_parity_and_preanswer_hook_boundary():
    rt = runtime()
    h = vectors()[:1]
    prefix = "- "
    expected = rt.oracle.reader.paired_logodds_templates(h, 44, PAIRS, prefix=prefix).mean(0)
    baseline = rt.score(h, PAIRS, layer=1, direction=unit(), sigma=1, alpha=0, prefix=prefix)
    assert torch.equal(baseline["scores"], expected)
    assert baseline["metadata"]["prefix_ids"] == rt.oracle.reader.tok.encode(prefix)
    assert baseline["metadata"]["preanswer_position"] == 5
    before, after, _, handles = observers(rt.oracle.model, 1)
    try:
        result = rt.score(h, [("a", "bbb")], layer=1, direction=unit(), sigma=1, alpha=2, prefix=prefix)
    finally:
        for handle in handles:
            handle.remove()
    expected_hidden = before[0].clone()
    expected_hidden[0, 5:7] += 2*unit()
    expected_hidden[1, 5:9] += 2*unit()
    assert torch.equal(after[0], expected_hidden)
    # All carrier positions and all prefix tokens before the final prefix token
    # are untouched. Short-candidate right padding is also untouched.
    assert torch.equal(after[0][:, :5], before[0][:, :5])
    assert torch.equal(after[0][0, 7:], before[0][0, 7:])
    assert [record["positions"] for record in result["projections"]] == [[5, 6], [5, 6, 7, 8]]


def test_exact_layer_position_mask_excludes_carrier_marker_and_padding():
    rt = runtime()
    before, after, next_layer, handles = observers(rt.oracle.model, 1)
    try:
        out = rt.score(vectors()[:2], [("a", "bbb")], layer=1, direction=unit(0),
                       projection_direction=unit(1), sigma=2, alpha=-2)
    finally:
        for handle in handles:
            handle.remove()
    assert len(before) == len(after) == len(next_layer) == 1
    expected = before[0].clone()
    for row, answer_len in enumerate([1, 3, 1, 3]):
        expected[row, 3:4+answer_len] += -4*unit(0)
    assert torch.equal(after[0], expected)
    assert torch.equal(after[0][:, :3], before[0][:, :3])
    assert torch.equal(after[0][0, 5:], before[0][0, 5:])
    assert torch.equal(after[0][2, 5:], before[0][2, 5:])
    # Measurement uses the row's supplied projection direction, even though the
    # edit uses a different control direction.
    for record in out["projections"]:
        row = record["item_index"]*2 + record["candidate_index"]
        expected_values = next_layer[0][row, record["positions"]] @ unit(1)
        assert torch.equal(torch.tensor(record["values"]), expected_values)
        assert record["roles"][0] == "preanswer"
        assert record["roles"][1:] == ["answer"]*(1 if record["candidate_index"] == 0 else 3)
        assert 1 not in record["positions"]  # Never the activation marker.
    assert out["metadata"]["steering_layer"] == 1
    assert out["metadata"]["projection_layer"] == 2


def test_random_control_unit_has_same_edit_norm_without_residual_renormalisation():
    rt = runtime()
    controls = [unit(), (unit(1)+unit(2))/2**0.5]
    measured = []
    for direction in controls:
        before, after, _, handles = observers(rt.oracle.model, 1)
        try:
            out = rt.score(vectors()[:1], [("a", "b")], 1, direction, sigma=1.5, alpha=2)
        finally:
            for handle in handles:
                handle.remove()
        differences = after[0][:, 3:] - before[0][:, 3:]
        measured.append(differences.norm(dim=-1))
        assert torch.allclose(differences, (3*direction).expand_as(differences), atol=2e-7)
        assert not torch.allclose(after[0][:, 3:].norm(dim=-1), before[0][:, 3:].norm(dim=-1))
        assert out["metadata"]["requested_edit_norm"] == 3
    assert torch.allclose(measured[0], measured[1], atol=3e-7)


def test_continuation_truncation_is_on_token_ids_and_masks_short_candidate_padding():
    rt = runtime()
    before, after, _, handles = observers(rt.oracle.model, 1)
    try:
        result = rt.score(vectors()[:1], [("abcdefghijklmnopqrst", "xy")], 1, unit(),
                          sigma=1, alpha=1, max_candidate_tokens=16)
    finally:
        for handle in handles:
            handle.remove()
    metadata = result["metadata"]
    assert metadata["candidate_lengths"] == [[16, 2]]
    assert metadata["original_candidate_lengths"] == [[20, 2]]
    assert [len(record["values"]) for record in result["projections"]] == [17, 3]
    assert result["projections"][0]["token_ids"][1:] == rt.oracle.reader.tok.encode("abcdefghijklmnop")
    assert torch.equal(after[0][1, 6:], before[0][1, 6:])
    # On this character-tokenizer the explicitly truncated strings are exactly
    # the same continuation; verifies truncation does not alter score alignment.
    explicit = rt.score(vectors()[:1], [("abcdefghijklmnop", "xy")], 1, unit(), sigma=1, alpha=1)
    assert torch.equal(result["scores"], explicit["scores"])


def test_cleanup_when_model_forward_raises():
    rt = runtime()
    original = rt.oracle.model.forward
    def broken(**kwargs):
        raise RuntimeError("deliberate failure")
    rt.oracle.model.forward = broken
    with pytest.raises(RuntimeError, match="deliberate failure"):
        rt.score(vectors(), PAIRS, 1, unit(), sigma=1, alpha=1)
    rt.oracle.model.forward = original
    assert all(not block._forward_hooks for block in rt.oracle.model.layers)
    assert rt.score(vectors(), PAIRS, 1, unit(), sigma=1, alpha=1)["status"] == "COMPLETE"


def test_rejects_nonunit_control_invalid_layer_and_invalid_sigma():
    rt = runtime()
    with pytest.raises(ValueError, match="unit-normalized"):
        rt.score(vectors(), PAIRS, 1, 2*unit(), sigma=1, alpha=1)
    with pytest.raises(ValueError, match="following decoder layer"):
        rt.score(vectors(), PAIRS, 3, unit(), sigma=1, alpha=1)
    with pytest.raises(ValueError, match="sigma"):
        rt.score(vectors(), PAIRS, 1, unit(), sigma=0, alpha=1)
