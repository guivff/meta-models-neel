"""CPU synthetic mechanics for the separately registered complete-answer follow-up."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

torch = pytest.importorskip("torch")
from projects.g_agreement.r_bench import complete_answers as A
from projects.g_agreement.r_bench import exact_prefix as E
from projects.g_agreement.tests import _write_guard as WG

REPO = Path(__file__).resolve().parents[3]
_GUARD = WG.ModuleWriteGuard([REPO / "results/g_agreement", REPO / "cache/g_agreement",
                             REPO / "projects/g_agreement/dataset", REPO / "projects/g_agreement/manifest"])
_write_guard = _GUARD.fixture()


class Tokenizer:
    all_special_ids = [0, 2, 3]
    pieces = {0: "<pad>", 2: "<eos>", 3: "<end>", 6: "x", 10: "Os", 11: "lo", 12: " Oslo",
              13: "Li", 14: "ma", 15: " Lima", 16: "!", 17: " Os", 20: "P", 21: "Q", 22: "R", 23: "S"}
    encodings = {"Oslo": [10, 11], " Oslo": [12], "Lima": [13, 14], " Lima": [15], "Os": [10], " Os": [17]}

    def __call__(self, text, add_special_tokens=False):
        return {"input_ids": self.encodings[text][:]}

    def decode(self, ids, **kwargs):
        return "".join(self.pieces.get(int(i), "?") for i in ids)


class MarkovModel(torch.nn.Module):
    """Finite transition table; adapters and real position IDs alter logits."""
    def __init__(self):
        super().__init__()
        table = torch.full((32, 32), -9.)
        table[20, [10, 12, 13, 15]] = torch.tensor([2., 1., .5, 0.])
        table[21, 13] = 3.
        table[22, 2] = 3.
        table[23, 16] = 3.
        table[10, [11, 16]] = torch.tensor([2., 1.])
        table[13, [14, 16]] = torch.tensor([2., 0.])
        table[11, [2, 3, 16]] = torch.tensor([2., 1., 1.5])
        table[14, [2, 3, 16]] = torch.tensor([1., 2., 1.5])
        table[12, [2, 3, 16]] = torch.tensor([0., -1., 2.])
        table[15, [2, 3, 16]] = torch.tensor([0., -1., 2.])
        table[16, 16] = 3.
        self.table = torch.nn.Parameter(table, requires_grad=False)
        self.active_adapters = ["reader"]
        self.peft_config = {"reader": {}, "planted_sft": {}}
        self.disable_adapters = False
        self.calls = []
        self.fail = False

    def set_adapter(self, name):
        self.active_adapters = [name] if isinstance(name, str) else list(name)

    @contextmanager
    def disable_adapter(self):
        previous = self.disable_adapters
        self.disable_adapters = True
        try:
            yield
        finally:
            self.disable_adapters = previous

    def forward(self, input_ids, attention_mask, position_ids, use_cache=False, logits_to_keep=None):
        if self.fail:
            raise RuntimeError("synthetic forward failure")
        self.calls.append({"ids": input_ids.clone(), "mask": attention_mask.clone(),
                           "positions": position_ids.clone(), "adapter": self.active_adapters[:], "cache": use_cache})
        logits = self.table[input_ids].clone()
        logits += position_ids[:, :, None] * torch.arange(32)[None, None, :] * .0002
        if not self.disable_adapters and self.active_adapters == ["planted_sft"]:
            logits[:, :, 10] += .25
        return SimpleNamespace(logits=logits[:, -logits_to_keep:] if logits_to_keep else logits)


def frozen():
    return A.freeze_answer_paths(Tokenizer(), ["Oslo", "Lima"])


def score(model, prefixes, contract=None, **kwargs):
    return A.score_complete_answers(model, prefixes, frozen() if contract is None else contract,
        pad_token_id=0, adapter_name="planted_sft", eos_token_ids=[2, 3], **kwargs)


def test_frozen_paths_are_exact_bare_and_one_space_with_serializable_ids():
    contract = frozen()
    assert contract.candidates == ("Oslo", "Lima")
    assert [(p.surface, p.token_ids, p.form) for p in contract.paths] == [
        ("Oslo", (10, 11), "bare"), (" Oslo", (12,), "leading_space"),
        ("Lima", (13, 14), "bare"), (" Lima", (15,), "leading_space")]
    assert contract.as_dict()["paths"][0]["token_ids"] == [10, 11]
    with pytest.raises(ValueError, match="prefix overlap"):
        A.freeze_answer_paths(Tokenizer(), ["Os", "Oslo"])
    with pytest.raises(ValueError, match="distinct"):
        A.freeze_answer_paths(Tokenizer(), ["Oslo", "Oslo"])
    with pytest.raises(ValueError, match="exceeds"):
        A.freeze_answer_paths(Tokenizer(), ["Oslo", "Lima"], max_answer_tokens=1)


def test_duplicate_frozen_paths_are_rejected_not_double_counted():
    contract = frozen()
    paths = list(contract.paths)
    paths[1] = replace(paths[1], token_ids=paths[0].token_ids)
    with pytest.raises(ValueError, match="duplicate"):
        score(MarkovModel(), [[20]], replace(contract, paths=tuple(paths)))


@pytest.mark.parametrize("side", ["left", "right"])
def test_all_suffix_tokens_count_exact_positions_and_eos_mass(side):
    model = MarkovModel()
    prefixes = [[20], [6, 6, 21]]
    originals = [p[:] for p in prefixes]
    contract = frozen()
    got = score(model, prefixes, padding_side=side, batch=8)
    assert prefixes == originals
    assert len(model.calls) == 1
    call = model.calls[0]
    assert call["adapter"] == ["planted_sft"] and call["cache"] is False
    for r, (prefix, path) in enumerate((p, path) for p in prefixes for path in contract.paths):
        assert call["ids"][r][call["mask"][r].bool()].tolist() == prefix + list(path.token_ids)
        assert call["positions"][r][call["mask"][r].bool()].tolist() == list(range(len(prefix) + len(path.token_ids)))
    for i, prefix in enumerate(prefixes):
        expected_candidates, expected_terminated = [], []
        for ci in range(2):
            expected_paths, terminated_paths = [], []
            for path in [p for p in contract.paths if p.candidate_index == ci]:
                ids = torch.tensor([prefix + list(path.token_ids)])
                with E.adapter_context(model, "planted_sft"):
                    logits = model(ids, torch.ones_like(ids), torch.arange(ids.shape[1])[None]).logits
                lp = torch.log_softmax(logits.float(), -1)
                parts = [float(lp[0, len(prefix) + j - 1, token]) for j, token in enumerate(path.token_ids)]
                total = sum(parts)
                terminal = total + float(torch.logsumexp(lp[0, -1, [2, 3]], 0))
                stored = next(p for p in got[i]["path_scores"] if p["surface"] == path.surface)
                assert stored["token_logprobs"] == pytest.approx(parts)
                assert stored["logprob"] == pytest.approx(total)
                assert stored["eos_terminated_logprob"] == pytest.approx(terminal)
                if len(parts) > 1:
                    assert stored["logprob"] != pytest.approx(parts[0])
                    assert stored["logprob"] != pytest.approx(sum(parts) / len(parts))
                expected_paths.append(total); terminated_paths.append(terminal)
            expected_candidates.append(float(torch.logsumexp(torch.tensor(expected_paths), 0)))
            expected_terminated.append(float(torch.logsumexp(torch.tensor(terminated_paths), 0)))
        assert got[i]["candidate_logprobs"] == pytest.approx(expected_candidates)
        assert got[i]["eos_terminated_candidate_logprobs"] == pytest.approx(expected_terminated)
        assert 0 < got[i]["eos_terminated_candidate_mass"] < got[i]["candidate_mass"] < 1
        assert not got[i]["length_normalization"]
        assert "continuation" in got[i]["probability_event"]
        assert "immediately" in got[i]["eos_probability_event"]
    assert model.active_adapters == ["reader"]


def test_batch_equals_single_with_candidate_order_and_varied_heads():
    model = MarkovModel()
    contracts = [frozen(), A.freeze_answer_paths(Tokenizer(), ["Lima", "Oslo"])]
    prefixes = [[20], [6, 6, 6, 21]]
    batched = score(model, prefixes, contracts, batch=8)
    for i in range(2):
        single = score(model, prefixes[i:i+1], contracts[i], batch=4)[0]
        assert batched[i]["candidate_logprobs"] == pytest.approx(single["candidate_logprobs"])
        assert batched[i]["eos_terminated_candidate_mass"] == pytest.approx(single["eos_terminated_candidate_mass"])
    assert batched[1]["candidates"] == ["Lima", "Oslo"]


def test_failure_restores_adapter_and_disabled_adapter_is_rejected():
    model = MarkovModel()
    model.fail = True
    with pytest.raises(RuntimeError, match="synthetic"):
        score(model, [[20]])
    assert model.active_adapters == ["reader"]
    model.fail = False
    with model.disable_adapter():
        with pytest.raises(RuntimeError, match="disabled"):
            score(model, [[20]])
    assert model.active_adapters == ["reader"]


def test_full_logits_fallback_matches_optimized_positions():
    class Legacy(MarkovModel):
        def forward(self, input_ids, attention_mask, position_ids, use_cache=False):
            return super().forward(input_ids, attention_mask, position_ids, use_cache)
    expected = score(MarkovModel(), [[20], [6, 21]], batch=8)
    actual = score(Legacy(), [[20], [6, 21]], batch=8)
    assert [r["candidate_mass"] for r in actual] == pytest.approx([r["candidate_mass"] for r in expected])


def test_incomplete_inputs_overlap_and_ceiling_fail_closed():
    model = MarkovModel()
    for prefixes in ([], [[]]):
        with pytest.raises(ValueError):
            score(model, prefixes)
    with pytest.raises(ValueError, match="batch"):
        score(model, [[20]], batch=3)
    with pytest.raises(ValueError, match="ceiling"):
        score(model, [[20]], max_input_tokens=2)
    with pytest.raises(ValueError, match="EOS"):
        A.score_complete_answers(model, [[20]], frozen(), pad_token_id=0, adapter_name="planted_sft", eos_token_ids=[2, 2])


def test_greedy_exact_prefix_eos_and_eight_token_cap_with_variable_left_padding():
    model, tokenizer = MarkovModel(), Tokenizer()
    prefixes = [[20], [6, 6, 21], [22], [6, 23]]
    result = A.greedy_complete_answers(model, tokenizer, prefixes, pad_token_id=0, adapter_name="planted_sft",
                                       eos_token_ids=[2, 3], max_new_tokens=8, batch=4)
    assert result[0]["generated_token_ids"] == [10, 11, 2]
    assert result[1]["generated_token_ids"] == [13, 14, 3]
    assert result[2]["generated_token_ids"] == [2]
    assert result[3]["generated_token_ids"] == [16] * 8
    assert [r["text"] for r in result] == ["Oslo", "Lima", "", "!!!!!!!!"]
    assert result[0]["raw_text"] == "Oslo<eos>"
    assert result[1]["answer_token_ids"] == [13, 14]
    assert [r["finish_reason"] for r in result] == ["eos", "eos", "eos", "length"]
    assert [r["eos_reached"] for r in result] == [True, True, True, False]
    assert model.active_adapters == ["reader"]
    first = model.calls[0]
    for i, prefix in enumerate(prefixes):
        assert first["ids"][i][first["mask"][i].bool()].tolist() == prefix
    # A finished row disappears, rather than generating padding or more words.
    assert [call["ids"].shape[0] for call in model.calls] == [4, 3, 3, 1, 1, 1, 1, 1]
    assert all(call["adapter"] == ["planted_sft"] for call in model.calls)


def test_greedy_batch_equals_single_and_restores_on_failure():
    model = MarkovModel()
    kw = dict(pad_token_id=0, adapter_name="planted_sft", eos_token_ids=[2, 3])
    prefixes = [[20], [6, 21], [22]]
    batched = A.greedy_complete_answers(model, Tokenizer(), prefixes, **kw)
    for i, prefix in enumerate(prefixes):
        single = A.greedy_complete_answers(model, Tokenizer(), [prefix], **kw)[0]
        assert batched[i] == single
    model.fail = True
    with pytest.raises(RuntimeError, match="synthetic"):
        A.greedy_complete_answers(model, Tokenizer(), [[20]], **kw)
    assert model.active_adapters == ["reader"]
    for bad in (0, 9):
        with pytest.raises(ValueError):
            A.greedy_complete_answers(model, Tokenizer(), [[20]], **kw, max_new_tokens=bad)


def test_zz_protected_roots_untouched():
    _GUARD.assert_clean()
