"""CPU-only E22 native parity, cache-indexing and exact patch-location tests."""
from types import SimpleNamespace

import pytest
import torch

from projects.g_agreement.understand.e22.runtime import E22Runtime, layer_grid
from projects.g_agreement.understand.reader_runtime import ReaderRuntime
from projects.g_agreement.understand.tests.test_reader_runtime import oracle, vectors, PAIRS, TinyModel
from mats.readers.olens import OracleLens


def runtime(candidate_batch=32):
    return E22Runtime(ReaderRuntime("olens", oracle()), candidate_batch=candidate_batch)


def test_layer_grid_and_one_baseline_forward_per_pair():
    assert layer_grid(64) == list(range(0, 64, 4))+[63]
    assert layer_grid(1) == [0]
    rt = runtime()
    before = rt.oracle.model.forward_count
    baseline = rt.capture(vectors(), PAIRS)
    assert rt.oracle.model.forward_count-before == len(PAIRS)
    assert baseline["residuals"].shape == (3, 2, 2, 2, 2, 6)
    assert baseline["residuals"].device.type == "cpu"
    assert not baseline["residuals"].requires_grad
    assert baseline["layer_ids"] == [0, 3]
    assert baseline["metadata"]["layer_convention"] == "decoder_block_input"
    assert torch.equal(baseline["scores"], rt.oracle.asked(vectors(), PAIRS).detach())
    assert all(not block._forward_pre_hooks for block in rt.oracle.model.layers)


@pytest.mark.parametrize("prefix", ["", "- "])
def test_layer_zero_injection_exactly_matches_full_activation_swap(prefix):
    rt = runtime()
    recipient = vectors()
    donor = vectors().roll(1, 1)+0.4
    capture = rt.capture(donor, PAIRS, prefix=prefix)
    mapping = [2, 0, 1]
    before = rt.oracle.model.forward_count
    patched = rt.score_patch(recipient, PAIRS, capture, 0, "injection", prefix=prefix, donor_indices=mapping)
    assert rt.oracle.model.forward_count-before == len(PAIRS)  # No extra donor forwards.
    full_swap = rt.capture(donor[mapping], PAIRS, prefix=prefix)
    assert torch.equal(patched["scores"], full_swap["scores"])
    assert torch.equal(patched["per_pair_scores"], full_swap["per_pair_scores"])
    native = rt.oracle.reader.paired_logodds_templates(donor[mapping], 44, PAIRS, prefix=prefix).mean(0)
    assert torch.equal(full_swap["scores"], native)
    assert patched["metadata"]["donor_forwards"] == 0
    assert patched["metadata"]["donor_indices"] == mapping


@pytest.mark.parametrize("position", ["injection", "preanswer"])
def test_exact_one_position_and_layer_is_replaced_with_correct_item_pair_candidate(position):
    rt = runtime()
    h = vectors()
    capture = rt.capture(h.flip(0), PAIRS, prefix="- ")
    axis = rt.positions.index(position)
    # Distinct synthetic cached vectors make every item/pair/candidate index
    # independently observable, even at causal positions whose true vectors tie.
    for i in range(3):
        for pair in range(2):
            for candidate in range(2):
                capture["residuals"][i, pair, candidate, 1, axis] += 100*i+10*pair+candidate+1
    block = rt.oracle.model.layers[3]
    old_forward = block.forward
    before, after = [], []
    handle = block.register_forward_pre_hook(lambda _m, args: before.append(args[0].detach().clone()))
    def recording(*args, **kwargs):
        after.append(args[0].detach().clone())
        return old_forward(*args, **kwargs)
    block.forward = recording
    try:
        out = rt.score_patch(h, PAIRS, capture, 3, position, prefix="- ", donor_indices=[1, 2, 0])
    finally:
        block.forward = old_forward
        handle.remove()
    token_position = capture["metadata"]["position_indices"][axis]
    for pair in range(2):
        expected = before[pair].clone()
        expected[:, token_position] = capture["residuals"][[1, 2, 0], pair, :, 1, axis].reshape(6, 6)
        assert torch.equal(after[pair], expected)
        untouched = [i for i in range(expected.shape[1]) if i != token_position]
        assert torch.equal(after[pair][:, untouched], before[pair][:, untouched])
    assert out["metadata"]["patch_token_index"] == token_position
    assert all(not b._forward_pre_hooks for b in rt.oracle.model.layers)


class RoutedBlock(torch.nn.Module):
    def __init__(self, block, sentinel):
        super().__init__()
        self.block, self.sentinel = block, sentinel
        self.seen = []
    def forward(self, hidden_states, attention_mask, sentinel):
        assert sentinel is self.sentinel
        self.seen.append((attention_mask, sentinel))
        return self.block(hidden_states)


class RoutedModel(TinyModel):
    def __init__(self, keyword):
        super().__init__()
        self.sentinel = object()
        self.keyword = keyword
        self.layers = torch.nn.ModuleList([RoutedBlock(block, self.sentinel) for block in self.layers])
    def forward(self, input_ids=None, inputs_embeds=None, attention_mask=None, logits_to_keep=0, use_cache=False):
        self.forward_count += 1
        hidden = self.embed(input_ids) if inputs_embeds is None else inputs_embeds
        for block in self.layers:
            if self.keyword:
                hidden = block(hidden_states=hidden, attention_mask=attention_mask, sentinel=self.sentinel)
            else:
                hidden = block(hidden, attention_mask, self.sentinel)
        return SimpleNamespace(logits=self.lm_head(hidden[:, -logits_to_keep:] if logits_to_keep else hidden))


@pytest.mark.parametrize("keyword", [False, True])
def test_pre_hook_preserves_extra_positional_and_keyword_arguments(keyword):
    wrapped = oracle()
    wrapped.model = RoutedModel(keyword)
    rt = E22Runtime(ReaderRuntime("olens", wrapped))
    donor = vectors().flip(0)
    capture = rt.capture(donor, PAIRS)
    patch = rt.score_patch(vectors(), PAIRS, capture, 0, "injection")
    assert torch.equal(patch["scores"], capture["scores"])
    for call in range(rt.oracle.model.forward_count):
        masks = [block.seen[call][0] for block in rt.oracle.model.layers]
        assert all(mask is masks[0] for mask in masks)


@pytest.mark.parametrize("mapping", [[0, 1], [0, 1, 3], [-1, 1, 2], [0.0, 1.0, 2.0], [True, False, True]])
def test_donor_index_validation(mapping):
    rt = runtime()
    captured = rt.capture(vectors(), PAIRS)
    with pytest.raises(ValueError, match="donor"):
        rt.score_patch(vectors(), PAIRS, captured, 0, "injection", donor_indices=mapping)


def test_prefix_candidate_and_batch_contract_rejects_cross_use():
    rt = runtime()
    capture = rt.capture(vectors(), PAIRS)
    with pytest.raises(ValueError, match="metadata mismatch"):
        rt.score_patch(vectors(), PAIRS, capture, 0, "injection", prefix="- ")
    with pytest.raises(ValueError, match="metadata mismatch"):
        rt.score_patch(vectors(), PAIRS[::-1], capture, 0, "injection")
    with pytest.raises(ValueError, match="metadata mismatch"):
        runtime(candidate_batch=4).score_patch(vectors(), PAIRS, capture, 0, "injection")
    with pytest.raises(ValueError, match="identical donor"):
        rt.score_patch(vectors()[:1], PAIRS, capture, 0, "injection")


def test_multibatch_layout_and_cleanup_after_errors():
    rt = runtime(candidate_batch=4)
    h = vectors()
    captured = rt.capture(h, PAIRS)
    assert rt.oracle.model.forward_count == 4
    patched = rt.score_patch(h.flip(0), PAIRS, captured, 0, "injection")
    assert torch.equal(patched["scores"], captured["scores"])
    original = rt.oracle.model.forward
    def broken(**kwargs):
        raise RuntimeError("deliberate forward failure")
    rt.oracle.model.forward = broken
    try:
        with pytest.raises(RuntimeError, match="deliberate"):
            rt.capture(h, PAIRS)
        assert all(not block._forward_pre_hooks for block in rt.oracle.model.layers)
        with pytest.raises(RuntimeError, match="deliberate"):
            rt.score_patch(h, PAIRS, captured, 3, "preanswer")
        assert all(not block._forward_pre_hooks for block in rt.oracle.model.layers)
    finally:
        rt.oracle.model.forward = original
