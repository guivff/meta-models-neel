"""CPU proof that the two warning tensors cannot affect native NLA reconstruction."""
from types import SimpleNamespace
from unittest.mock import patch

import common
import pytest
import torch
from safetensors.torch import save_file
from mats.readers.nla import NLA, _load_ar, rescale, logprob_of_strings_batch


class Poison(torch.nn.Module):
    def __init__(self, value):
        super().__init__()
        self.weight = torch.nn.Parameter(torch.full((4,), value))

    def forward(self, *args, **kwargs):
        raise AssertionError('newly initialized tensor reached a score')


class Inner(torch.nn.Module):
    def __init__(self, value):
        super().__init__()
        self.norm = Poison(value)

    def forward(self, input_ids, attention_mask):
        h = input_ids.float()[..., None] + torch.arange(1, 5).float()
        return SimpleNamespace(last_hidden_state=self.norm(h))


class Full(torch.nn.Module):
    def __init__(self, value):
        super().__init__()
        self.model = Inner(value)
        self.lm_head = Poison(value)

    def forward(self, *args, **kwargs):
        return self.lm_head(self.model(*args, **kwargs).last_hidden_state)


class Tokenizer:
    pad_token_id = 0

    def encode(self, text, add_special_tokens=False):
        return [1 + ord(c) % 8 for c in text]


def fixture(tmp_path, value, info=None):
    ar = tmp_path / 'ar_reconstructor'; ar.mkdir(exist_ok=True)
    weight = torch.arange(16, dtype=torch.float32).reshape(4, 4) / 7
    save_file({'value_head.weight': weight}, ar / 'value_head.safetensors')
    full = Full(value)
    info = info if info is not None else {
        'missing_keys': ['model.norm.weight', 'lm_head.weight'], 'unexpected_keys': []}
    with patch('transformers.AutoModelForCausalLM.from_pretrained', return_value=(full, info)) as load:
        inner, head = _load_ar(tmp_path, 'cpu')
    assert load.call_args.kwargs['output_loading_info'] is True
    assert inner is full.model and isinstance(inner.norm, torch.nn.Identity)
    assert isinstance(full.lm_head, torch.nn.Identity)
    assert torch.equal(head.weight, weight)
    assert not any(n.startswith('norm.') for n, _ in inner.named_parameters())
    return NLA(av=Poison(value), tok=Tokenizer(), ar=inner, value_head=head,
               meta={'prompt_templates': {'critic': '{explanation}'}},
               prompt_ids=[], marker=0, device='cpu'), weight


def test_discarded_lm_head_and_norm_never_reach_reconstruction(tmp_path):
    outputs = []
    for value in (-999., 999.):
        nla, weight = fixture(tmp_path, value)
        texts = ['a', 'bcdef']
        pred = nla.reconstruct(texts, batch=2)
        last = torch.tensor([[nla.tok.encode(t)[-1] + k for k in range(1, 5)] for t in texts])
        assert torch.equal(pred, rescale(last) @ weight.T)
        outputs.append(pred)
    assert torch.equal(*outputs)


@pytest.mark.parametrize('info', [
    {'missing_keys': ['model.norm.weight', 'lm_head.weight', 'model.layers.0.weight'], 'unexpected_keys': []},
    {'missing_keys': ['model.norm.weight', 'lm_head.weight'], 'unexpected_keys': ['extra.weight']},
])
def test_nonallowlisted_checkpoint_mismatch_fails(tmp_path, info):
    with pytest.raises(RuntimeError, match='AR weights mismatch'):
        fixture(tmp_path, 1., info)


def test_missing_trained_value_head_fails(tmp_path):
    (tmp_path / 'ar_reconstructor').mkdir()
    info = {'missing_keys': ['model.norm.weight', 'lm_head.weight'], 'unexpected_keys': []}
    with patch('transformers.AutoModelForCausalLM.from_pretrained', return_value=(Full(1.), info)):
        with pytest.raises(FileNotFoundError):
            _load_ar(tmp_path, 'cpu')


def test_asked_score_uses_separate_av_not_decoder_heads():
    class AV(torch.nn.Module):
        def forward(self, input_ids, attention_mask, logits_to_keep):
            logits = torch.arange(16).float().expand(len(input_ids), logits_to_keep, 16)
            return SimpleNamespace(logits=logits)
    nla = NLA(av=AV(), tok=Tokenizer(), ar=Poison(1.), value_head=Poison(1.),
              meta={}, prompt_ids=[2], marker=0, device='cpu')
    out = logprob_of_strings_batch(nla, torch.ones(2, 4), ['a', 'b'], prefix='p', batch=4)
    assert out.shape == (2, 2) and torch.isfinite(out).all()
