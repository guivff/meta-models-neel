"""CPU checks of E18's actual token, injection, donor and likelihood paths."""
from contextlib import nullcontext
import numpy as np
import pytest

from projects.g_agreement.understand import e18 as E, e18_worker as W


class TinyTokenizer:
    pad_token_id = 0
    eos_token_id = 2
    vocabulary = {'- ': [7, 8], '\n': [9], 'A': [10, 11], 'B': [12],
                  'C': [13], 'D': [14, 15, 16]}

    def encode(self, text, add_special_tokens=False):
        assert add_special_tokens is False
        return self.vocabulary.get(text, [24 + ord(c) % 24 for c in text])

    def decode(self, ids, skip_special_tokens=False, clean_up_tokenization_spaces=True):
        assert clean_up_tokenization_spaces is False
        return ' '.join('t' + str(t) for t in ids if not skip_special_tokens or t not in (0, 2))

    def apply_chat_template(self, turns, **kwargs):
        assert kwargs == {'tokenize': True, 'add_generation_prompt': True,
                          'enable_thinking': False}
        assert len(turns) == 1 and turns[0]['role'] == 'user'
        self.last_turns = turns
        return [1, 20] + self.encode(turns[0]['content']) + [21, 22]


@pytest.fixture
def reader():
    import common
    import torch
    from transformers import LlamaConfig, LlamaForCausalLM
    from peft import LoraConfig, get_peft_model
    from mats.readers.olens import OracleLens

    torch.manual_seed(18)
    model = LlamaForCausalLM(LlamaConfig(
        vocab_size=64, hidden_size=16, intermediate_size=32, num_hidden_layers=2,
        num_attention_heads=2, num_key_value_heads=2, pad_token_id=0, eos_token_id=2,
        bos_token_id=1)).eval()
    model = get_peft_model(model, LoraConfig(
        r=2, lora_alpha=2, target_modules=['q_proj', 'v_proj'], task_type='CAUSAL_LM')).eval()
    # A nonzero adapter makes accidentally using it for arm d detectable.
    with torch.no_grad():
        for name, parameter in model.named_parameters():
            if 'lora_B' in name:
                parameter.normal_(0, .5)
    result = OracleLens(model, TinyTokenizer(), alpha=3., device='cpu')
    result._slots[44] = ([1, 4, 5, 6], 2)
    return result


def fixture_items():
    items = [{'id': 'recipient-a', 'feature': 'f'}, {'id': 'recipient-b', 'feature': 'f'}]
    h = np.arange(32, dtype=np.float32).reshape(2, 16) - 13
    templates = {'f': {'olens': [['A', 'B'], ['C', 'D']]}}
    continuation = {
        'recipient-a': {'continuation_ids': [17, 18], 'raw': 't17 t18'},
        'recipient-b': {'continuation_ids': [19, 23, 24, 2], 'raw': 't19 t23 t24'}}
    donors = {'recipient-a': 'recipient-b', 'recipient-b': 'recipient-a'}
    return items, h, templates, continuation, donors


def manual_scores(reader, heads, h, pairs, base=False):
    """Independent full-forward next-token CE, with only candidate positions credited."""
    import torch
    import torch.nn.functional as F
    result = np.empty((len(heads), len(pairs)))
    with (reader.base() if base else nullcontext()), torch.inference_mode():
        for i, head in enumerate(heads):
            for j, pair in enumerate(pairs):
                values = []
                for candidate in pair:
                    tail = reader.tok.encode(candidate)
                    ids = torch.tensor([head + tail])
                    if base:
                        logits = reader.model(input_ids=ids, attention_mask=torch.ones_like(ids),
                                              use_cache=False).logits
                    else:
                        # Build the embedding replacement independently of reader._embed().
                        embeds = reader.model.get_input_embeddings()(ids).clone()
                        vector = torch.tensor(h[i])
                        embeds[0, 2] = reader.alpha * vector / vector.norm()
                        logits = reader.model(inputs_embeds=embeds,
                                              attention_mask=torch.ones_like(ids), use_cache=False).logits
                    token_loss = F.cross_entropy(logits[0, :-1].float(), ids[0, 1:], reduction='none')
                    values.append(-float(token_loss[len(head)-1:].sum()))
                result[i, j] = values[0] - values[1]
    return result


def test_prompt_assembly_preserves_native_tokens_then_continuation_then_candidates(reader):
    emitted = [17, 18, 2]
    head, slot = E.lens_head(reader, emitted)
    assert head == [1, 4, 5, 6, 7, 8, 17, 18, 2, 9]
    assert slot == 2 and head[slot] == 5
    assert head + reader.tok.encode('A') == [1, 4, 5, 6, 7, 8, 17, 18, 2, 9, 10, 11]
    assert E.lens_head(reader) == ([1, 4, 5, 6], 2)
    base = E.base_head(reader.tok, 't17 t18')
    assert reader.tok.last_turns == [{'role': 'user', 'content': '- t17 t18'}]
    assert base == [1, 20] + reader.tok.encode('- t17 t18') + [21, 22]
    assert '<activation>' not in reader.tok.last_turns[0]['content']


def test_donors_are_exact_seeded_canonical_opposite_value_same_row_and_split():
    items = [{'id': f'{f}-{value}-{i}', 'feature': f, 'value': value, 'split': 'test'}
             for f in ['f', 'g'] for value in ['A', 'B'] for i in range(4)]
    result = E.pair_donors(items)
    assert E.SEED == 20261025
    assert result == E.pair_donors(list(reversed(items)), seed=20261025)
    lookup = {r['id']: r for r in items}
    rng = np.random.default_rng(20261025)
    for r in sorted(items, key=lambda x: (x['feature'], x['id'])):
        eligible = sorted(x['id'] for x in items
                          if x['feature'] == r['feature'] and x['value'] != r['value'])
        assert result[r['id']] == eligible[int(rng.integers(len(eligible)))]
        donor = lookup[result[r['id']]]
        assert donor['feature'] == r['feature'] and donor['value'] != r['value']
        assert donor['split'] == r['split'] and donor['id'] != r['id']
    assert result != E.pair_donors(items, seed=20261026)
    with pytest.raises(ValueError, match='cross splits'):
        E.pair_donors(items + [{'id': 'dev', 'feature': 'f', 'value': 'A', 'split': 'dev'}])
    with pytest.raises(ValueError, match='unique'):
        E.pair_donors(items + items[:1])
    with pytest.raises(ValueError, match='two truth'):
        E.pair_donors([r for r in items if r['value'] == 'A'])


def test_b_and_c_keep_recipient_injection_and_score_variable_heads_against_manual(reader, monkeypatch):
    import torch
    items, h, templates, cont, donors = fixture_items()
    original = reader._embed
    embedded, masks = [], []
    def embed(ids, slot, acts):
        result = original(ids, slot, acts)
        embedded.append((ids.clone(), slot, acts.clone(), result[:, slot].clone()))
        return result
    monkeypatch.setattr(reader, '_embed', embed)
    hook = reader.model.register_forward_pre_hook(
        lambda _m, _a, kwargs: masks.append(kwargs['attention_mask'].clone()), with_kwargs=True)
    try:
        for arm in ('b', 'c'):
            embedded.clear(); masks.clear()
            result = W.score_arm(reader, arm, items, h, templates, cont, donors)
            assert len(embedded) == len(masks) == 2
            for pair_index, (ids, slot, acts, at_slot) in enumerate(embedded):
                assert ids.shape[0] == 4  # Both candidates share each item forward.
                assert slot == 2
                expected_h = torch.tensor(h).repeat_interleave(2, 0)
                assert torch.equal(acts, expected_h)
                assert torch.allclose(at_slot, 3 * expected_h / expected_h.norm(dim=-1, keepdim=True))
                for i, item in enumerate(items):
                    chosen = cont[donors[item['id']] if arm == 'c' else item['id']]
                    head, _ = E.lens_head(reader, chosen['continuation_ids'])
                    for c, candidate in enumerate(templates['f']['olens'][pair_index]):
                        seq = head + reader.tok.encode(candidate)
                        assert ids[2*i+c, :len(seq)].tolist() == seq
                        assert masks[pair_index][2*i+c, :len(seq)].tolist() == [1]*len(seq)
                        assert not masks[pair_index][2*i+c, len(seq):].any()
            heads = [E.lens_head(reader, cont[donors[r['id']] if arm == 'c' else r['id']]['continuation_ids'])[0]
                     for r in items]
            hook.remove()
            expected = manual_scores(reader, heads, h, templates['f']['olens'])
            assert np.allclose([r['scores'] for r in result], expected, atol=2e-6)
            hook = reader.model.register_forward_pre_hook(
                lambda _m, _a, kwargs: masks.append(kwargs['attention_mask'].clone()), with_kwargs=True)
    finally:
        hook.remove()


def test_a_is_unchanged_e16_asked_baseline(reader):
    from projects.g_agreement.understand.e16_worker import asked
    items, h, templates, cont, donors = fixture_items()
    actual = W.score_arm(reader, 'a', items, h, templates, cont, donors)
    expected = asked(reader, 'olens', {'feature': 'f', 'indices': [0, 1]}, items, h, templates)
    assert actual == expected
    assert all(len(row['scores']) == 2 for row in actual)


def test_base_d_has_no_injection_and_disables_nonzero_adapter_for_every_pair(reader, monkeypatch):
    items, h, templates, cont, donors = fixture_items()
    heads = [E.base_head(reader.tok, cont[r['id']]['raw']) for r in items]
    expected = manual_scores(reader, heads, None, templates['f']['olens'], base=True)
    monkeypatch.setattr(reader, '_embed', lambda *args: pytest.fail('base arm must never inject'))
    calls = []
    def observe(_model, _args, kwargs):
        assert 'input_ids' in kwargs and 'inputs_embeds' not in kwargs
        assert kwargs['input_ids'].shape[0] == 4
        adapters = [m for m in reader.model.modules() if hasattr(m, 'lora_A')]
        assert adapters and all(m.disable_adapters for m in adapters)
        calls.append(kwargs)
    hook = reader.model.register_forward_pre_hook(observe, with_kwargs=True)
    try:
        result = W.score_arm(reader, 'd', items, h, templates, cont, donors)
    finally:
        hook.remove()
    assert len(calls) == 2
    assert np.allclose([r['scores'] for r in result], expected, atol=2e-6)
    assert all(not m.disable_adapters for m in reader.model.modules() if hasattr(m, 'lora_A'))
    assert all(r['reader'] == 'base' for r in result)
    with pytest.raises(ValueError, match='no activation'):
        W.score_heads(reader, heads, 2, h, templates['f']['olens'], base=True)


def test_generation_uses_native_prefix_greedy16_and_keeps_early_eos_context(reader, monkeypatch):
    import torch
    items, h, _, _, _ = fixture_items()
    native = [1, 4, 5, 6, 7, 8]
    expected = reader._embed(torch.tensor([native]*2), 2, torch.tensor(h))
    def generate(**kwargs):
        assert kwargs['do_sample'] is False and kwargs['num_beams'] == 1
        assert kwargs['max_new_tokens'] == 16
        assert torch.equal(kwargs['attention_mask'], torch.ones((2, len(native)), dtype=torch.long))
        assert torch.equal(kwargs['inputs_embeds'], expected)
        # Production follows its native `pad_token_id or eos_token_id` convention.
        assert kwargs['pad_token_id'] == 2
        return torch.tensor([[17, 18, 2, 2], [19, 23, 24, 2]])
    monkeypatch.setattr(reader.model, 'generate', generate)
    result = W.generate(reader, h, items)
    assert result[0]['generated_ids'] == [17, 18, 2, 2]
    assert result[0]['continuation_ids'] == [17, 18, 2]
    assert result[0]['raw'] == 't17 t18'
    assert result[1]['continuation_ids'] == [19, 23, 24, 2]
    assert E.continuation_tokens([4, 5, 6], {2}, 0) == [4, 5, 6]
    with pytest.raises(ValueError, match='non-padding'):
        E.continuation_tokens([4, 2, 9], {2}, 0)


def test_actual_tiny_cpu_generation_roundtrips_to_injected_scoring(reader):
    items, h, templates, _, donors = fixture_items()
    generated = W.generate(reader, h, items)
    assert len(generated) == 2 and all(0 < len(r['continuation_ids']) <= 16 for r in generated)
    cache = {r['id']: r for r in generated}
    for arm in E.ARMS:
        values = W.score_arm(reader, arm, items, h, templates, cache, donors)
        assert np.asarray([r['scores'] for r in values]).shape == (2, 2)
        assert np.isfinite([r['scores'] for r in values]).all()
