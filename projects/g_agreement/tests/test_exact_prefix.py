"""CPU mechanics for the tournament sidecar; no model downloads or scientific data."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest

torch = pytest.importorskip("torch")
from projects.g_agreement.r_bench import exact_prefix as E


# Record only writes from this test process; concurrent pod output is unrelated.
from projects.g_agreement.tests import _write_guard as WG

REPO = Path(__file__).resolve().parents[3]
_GUARD = WG.ModuleWriteGuard([
    REPO / "results" / "g_agreement",
    REPO / "cache" / "g_agreement",
    REPO / "projects" / "g_agreement" / "dataset",
    REPO / "projects" / "g_agreement" / "manifest",
])
_write_guard = _GUARD.fixture()


class ToyTokenizer:
    pad_token_id = 0
    eos_token_id = 1
    all_special_ids = [0, 1]

    def __init__(self):
        self.forms = {i: chr(i) for i in range(2, 256)}
        self.forms.update({300: "㈀", 400: "Oslo", 401: " Oslo", 402: "\nOslo", 403: "Lima", 404: " Lima", 405: "Oslo!"})
        self.inverse = {s: i for i, s in self.forms.items()}
        self.thinking = []

    def get_vocab(self):
        return {**self.inverse, "<pad>": 0, "<eos>": 1}

    def __call__(self, text, **kwargs):
        if text in self.inverse:
            return {"input_ids": [self.inverse[text]]}
        return {"input_ids": [self.inverse[c] for c in text]}

    def decode(self, ids, **kwargs):
        return "".join(self.forms.get(int(i), "<special>") for i in ids)

    def apply_chat_template(self, messages, *, enable_thinking, **kwargs):
        self.thinking.append(enable_thinking)
        return self("USER:" + messages[0]["content"] + "\nASSISTANT:")["input_ids"]


class ToyBlock(torch.nn.Module):
    def __init__(self, increment, as_tuple=False):
        super().__init__()
        self.increment, self.as_tuple = increment, as_tuple

    def forward(self, x):
        y = x + self.increment
        return (y,) if self.as_tuple else y


class ToyModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        with torch.random.fork_rng():
            torch.manual_seed(19)
            self.embedding = torch.nn.Embedding(512, 8)
            self.head = torch.nn.Linear(8, 512, bias=False)
        self.model = torch.nn.Module()
        self.model.layers = torch.nn.ModuleList([ToyBlock(0.2), ToyBlock(0.4, True)])
        self.peft_config = {"default": {}, "planted_sft": {}}
        self.active_adapters = ["default"]
        self.disable_adapters = False
        self.calls = []
        self.fail = False
        self.requires_grad_(False)

    def set_adapter(self, names):
        self.active_adapters = [names] if isinstance(names, str) else list(names)

    @contextmanager
    def disable_adapter(self):
        previous = self.disable_adapters
        self.disable_adapters = True
        try:
            yield
        finally:
            self.disable_adapters = previous

    def get_input_embeddings(self):
        return self.embedding

    def forward(self, input_ids=None, inputs_embeds=None, attention_mask=None, position_ids=None,
                use_cache=False, logits_to_keep=None):
        if self.fail:
            raise RuntimeError("intentional toy failure")
        x = self.embedding(input_ids) if inputs_embeds is None else inputs_embeds
        self.calls.append({"adapter": tuple(self.active_adapters), "disabled": self.disable_adapters,
                           "embeddings": x.detach().clone(), "mask": attention_mask.detach().clone()})
        # Causal sum with masking and real position ids makes padding mistakes observable.
        x = (x * attention_mask[:, :, None]).cumsum(1) + 0.01 * position_ids[:, :, None]
        if not self.disable_adapters and self.active_adapters == ["planted_sft"]:
            x = x + 3
        for block in self.model.layers:
            x = block(x)
            x = x[0] if isinstance(x, tuple) else x
        logits = self.head(x)
        if logits_to_keep:
            logits = logits[:, -logits_to_keep:]
        return SimpleNamespace(logits=logits)


def capture(model, rows, **kwargs):
    return E.capture_exact_prefix(model, rows, layers=(0, 1), pad_token_id=0,
                                  adapter_name=kwargs.pop("adapter_name", "planted_sft"), **kwargs)


@pytest.mark.parametrize("side", ["left", "right"])
def test_capture_matches_single_for_padding_and_both_block_output_types(side):
    model = ToyModel()
    rows = [[10, 12, 14, 16], [20], [30, 31]]
    got = capture(model, rows, padding_side=side, return_sequences=True, max_tokens=4)
    assert got["last_indices"].tolist() == ([3, 3, 3] if side == "left" else [3, 0, 1])
    for i, row in enumerate(rows):
        one = capture(model, [row], return_sequences=True)
        torch.testing.assert_close(got["logits"][i], one["logits"][0])
        for L in (0, 1):
            torch.testing.assert_close(got["states"][L][i], one["states"][L][0])
            torch.testing.assert_close(got["sequences"][L][i], one["sequences"][L][0])
            assert got["sequences"][L][i].shape == (len(row), 8)
    assert model.active_adapters == ["default"]
    assert all(c["adapter"] == ("planted_sft",) and not c["disabled"] for c in model.calls)
    # Source logits and state are taken from one forward, not a rewritten question.
    assert len(model.calls) == 1 + len(rows)


def test_named_adapter_is_active_and_base_is_explicit():
    model = ToyModel()
    planted = capture(model, [[3, 4]])["logits"]
    base = E.capture_exact_prefix(model, [[3, 4]], layers=(0,), pad_token_id=0, adapter_name=None)["logits"]
    assert not torch.allclose(planted, base)
    assert model.calls[-1]["disabled"]
    assert not model.disable_adapters
    with pytest.raises(RuntimeError, match="not mounted"):
        capture(model, [[3]], adapter_name="missing")


def test_adapter_restore_and_hook_cleanup_on_failure():
    model = ToyModel()
    model.fail = True
    with pytest.raises(RuntimeError, match="intentional"):
        capture(model, [[3]])
    assert model.active_adapters == ["default"]
    assert all(not block._forward_hooks for block in model.model.layers)
    with model.disable_adapter():
        with pytest.raises(RuntimeError, match="disabled"):
            capture(model, [[3]])
    assert model.active_adapters == ["default"]


def test_misleading_adapter_selection_rejected():
    model = ToyModel()
    model.set_adapter = lambda names: None
    with pytest.raises(RuntimeError, match="active adapters"):
        capture(model, [[3]])


@pytest.mark.parametrize("rows,kw", [([], {}), ([[]], {}), ([[1, 2]], {"max_tokens": 1}), ([[1]], {"padding_side": "middle"})])
def test_capture_fails_instead_of_truncating_or_guessing(rows, kw):
    with pytest.raises(ValueError):
        capture(ToyModel(), rows, **kw)


def test_complete_candidate_vocab_and_unconditional_mass_global_argmax():
    tok = ToyTokenizer()
    vocab = E.build_candidate_vocab(tok, ["Oslo", "Lima"])
    assert vocab.token_ids == ((400, 401, 402), (403, 404))
    assert vocab.as_dict()["canonicalization"].startswith("strip")
    logits = torch.full((2, 512), -100.0)
    logits[0, [400, 401, 402, 403, 404]] = torch.log(torch.tensor([0.1, 0.2, 0.3, 0.1, 0.1]))
    logits[0, 405] = torch.log(torch.tensor(0.4))  # Oslo! is out-of-set even though candidate union favors Oslo.
    logits[1, 401] = 0  # Leading space canonicalizes to Oslo.
    result = E.summarize_logits(logits, vocab, tok)
    assert result[0]["out_of_set"] and result[0]["global_argmax_candidate"] is None
    assert result[0]["global_argmax_text"] == "Oslo!"
    assert result[0]["pair_argmax"] == "Oslo"
    assert result[0]["candidate_mass"] == pytest.approx(2 / 3)
    assert result[0]["candidate_probs"] == pytest.approx([0.5, 1 / 6])
    assert result[0]["pair_conditional_probs"] == pytest.approx([0.75, 0.25])
    assert not result[1]["out_of_set"] and result[1]["global_argmax_candidate"] == "Oslo"
    assert sum(len(x) for x in result[0]["candidate_token_logprobs"]) == 5


@pytest.mark.parametrize("words", [["violin", "Lima"], ["Oslo", " Oslo"], ["Oslo", "Oslo"]])
def test_multitoken_or_ambiguous_candidate_rejected(words):
    with pytest.raises(ValueError):
        E.build_candidate_vocab(ToyTokenizer(), words)


def test_full_source_text_preserves_history():
    item = {"prompt_text": "Last question", "capture_messages": [
        {"role": "system", "content": "System fact"}, {"role": "user", "content": "Earlier"},
        {"role": "assistant", "content": "Earlier answer"}, {"role": "user", "content": "Last question"}]}
    assert E.full_source_text(item) == "System: System fact\nUser: Earlier\nAssistant: Earlier answer\nUser: Last question"
    assert E.full_source_text({"prompt_text": "Q", "system": "S"}) == "System: S\nUser: Q"
    assert E.full_source_text({"prompt_text": "Q"}) == "Q"


def test_carrier_literal_thinking_off_and_frozen_marker():
    tok = ToyTokenizer()
    marker = E.OracleMarker("㈀", 300)
    c = E.questioned_oracle_carrier(tok, 44, "Which value?", ["Oslo", "Lima"], marker)
    assert c.text == ("An activation vector from layer 44 of a language model is enclosed in activation tags: <activation>㈀</activation>.\n"
                      "Source text: [not supplied]\nWhich value?\nChoose exactly one: Oslo | Lima. Return only that value.")
    assert c.ids[c.marker_index] == 300 and tok.thinking == [False]
    with pytest.raises(ValueError, match="exactly once"):
        E.questioned_oracle_carrier(tok, 44, "Which?", ["Oslo", "Lima"], marker, "㈀")
    with pytest.raises(ValueError, match="token ID"):
        E.questioned_oracle_carrier(tok, 44, "Which?", ["Oslo", "Lima"], E.OracleMarker("㈀", 301))
    with pytest.raises(ValueError, match="ceiling"):
        E.questioned_oracle_carrier(tok, 44, "Which?", ["Oslo", "Lima"], marker, max_tokens=1)


def reader_fixture():
    tok, model = ToyTokenizer(), ToyModel()
    reader = SimpleNamespace(target=SimpleNamespace(model=model, tokenizer=tok), alpha=3.0)
    reader.carrier = lambda layer: ([300], 0, "㈀", 300)
    return reader


def test_questioned_scorer_variable_heads_complete_bare_candidates_and_zero_state():
    reader = reader_fixture()
    H = torch.tensor([[1., 2, 3, 4, 5, 6, 7, 8], [0.] * 8])
    pairs = [("Oslo", "Lima"), ("Lima", "not Oslo")]
    questions = ["Actual hometown?", "Which value is the target instructed to output next?"]
    sources = [None, "User: complete earlier prompt\nAssistant: answer\nUser: final prompt"]
    marker = E.freeze_oracle_marker(reader)
    got = E.score_questioned_oracle(reader, H, pairs, questions, source_texts=sources,
                                    marker=marker, max_tokens=1000, batch=4)
    model, tok = reader.target.model, reader.target.tokenizer
    assert len(model.calls) == 1
    assert got[0]["n_tokens_A"] == got[0]["n_tokens_B"] == 1
    assert got[1]["n_tokens_B"] == len("not Oslo")
    assert model.calls[0]["adapter"] == ("default",)
    assert model.calls[0]["embeddings"][2, got[1]["marker_index"]].count_nonzero() == 0
    for i in range(2):
        one = E.score_questioned_oracle(reader, H[i:i + 1], pairs[i:i + 1], questions[i:i + 1],
                                        source_texts=sources[i:i + 1], marker=marker, max_tokens=1000, batch=2)[0]
        assert got[i]["lo"] == pytest.approx(one["lo"], abs=1e-3)
        # Independent full-position calculation of complete candidate likelihood.
        c = E.questioned_oracle_carrier(tok, 44, questions[i], pairs[i], marker, sources[i])
        for j, candidate in enumerate(pairs[i]):
            completion = tok(candidate)["input_ids"]
            row = list(c.ids) + completion
            ids = torch.tensor([row])
            embeddings = model.embedding(ids).clone()
            embeddings[0, c.marker_index] = reader.alpha * H[i] / H[i].norm().clamp_min(1e-9)
            result = model(inputs_embeds=embeddings, attention_mask=torch.ones_like(ids),
                           position_ids=torch.arange(len(row))[None], use_cache=False)
            lp = torch.log_softmax(result.logits.float(), -1)
            expected = sum(float(lp[0, len(c.ids) + k - 1, token]) for k, token in enumerate(completion))
            assert got[i]["lp_A" if j == 0 else "lp_B"] == pytest.approx(expected, abs=1e-3)
    assert model.active_adapters == ["default"]


def test_reader_activates_original_adapter_restores_factual_and_cleans_failure():
    reader = reader_fixture()
    model = reader.target.model
    model.set_adapter("planted_sft")
    E.score_questioned_oracle(reader, torch.zeros((1, 8)), [("Oslo", "Lima")], "Which?", max_tokens=1000)
    assert model.calls[-1]["adapter"] == ("default",)
    assert model.active_adapters == ["planted_sft"]
    model.fail = True
    with pytest.raises(RuntimeError, match="intentional"):
        E.score_questioned_oracle(reader, torch.zeros((1, 8)), [("Oslo", "Lima")], "Which?", max_tokens=1000)
    assert model.active_adapters == ["planted_sft"]


def test_reader_fallback_without_logits_to_keep():
    class LegacyModel(ToyModel):
        def forward(self, input_ids=None, inputs_embeds=None, attention_mask=None, position_ids=None, use_cache=False):
            return super().forward(input_ids, inputs_embeds, attention_mask, position_ids, use_cache)

    reader = reader_fixture()
    expected = E.score_questioned_oracle(reader, torch.ones((1, 8)), [("Oslo", "Lima")], "Which?", max_tokens=1000)
    reader.target.model = LegacyModel()
    got = E.score_questioned_oracle(reader, torch.ones((1, 8)), [("Oslo", "Lima")], "Which?", max_tokens=1000)
    assert got[0]["lo"] == pytest.approx(expected[0]["lo"])


def test_exact_logits_and_intermediate_block_match_tiny_qwen_hidden_states():
    pytest.importorskip("transformers")
    from projects.g_agreement.tests.test_readers_mock import tiny_model
    model = tiny_model()
    rows = [[11, 12, 13], [21, 22]]
    got = E.capture_exact_prefix(model, rows, layers=(0, 2), pad_token_id=501, adapter_name=None)
    for i, row in enumerate(rows):
        ids = torch.tensor([row])
        with torch.no_grad():
            actual = model(input_ids=ids, attention_mask=torch.ones_like(ids),
                           position_ids=torch.arange(len(row))[None], use_cache=False, output_hidden_states=True)
        torch.testing.assert_close(got["logits"][i], actual.logits[0, -1], atol=1e-5, rtol=1e-5)
        for L in (0, 2):
            torch.testing.assert_close(got["states"][L][i], actual.hidden_states[L + 1][0, -1], atol=1e-5, rtol=1e-5)


def test_zz_protected_roots_untouched():
    _GUARD.assert_clean()
