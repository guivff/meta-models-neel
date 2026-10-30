"""MOCK tests (CPU only) for the reader integration. Everything here runs on a tiny random
``Qwen3_5ForCausalLM`` (4 blocks, d=64, vocab 512) with a character-level fake tokenizer. The
numbers mean nothing scientifically; the tests check mechanics: hook == hidden_states[L+1],
state-cache rows, the OLens embedding replacement, the NLA block-1 norm-matched add (against
EasyNLA's reference when importable), the J-lens cosine formula, seeds, finish_reason, parsing,
resumability, the compute ledger. Nothing is written under ``results/``: every path is a
``tmp_path``, and a guard test asserts ``results/g_agreement`` is untouched.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_readers_mock.py -q``
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")

from projects.g_agreement.core import accounting as A  # noqa: E402
from projects.g_agreement.core import config as C  # noqa: E402
from projects.g_agreement.core import generate as G  # noqa: E402
from projects.g_agreement.core import model as M  # noqa: E402
from projects.g_agreement.core import readers as R  # noqa: E402
from projects.g_agreement.core import states as S  # noqa: E402

MOCK_LAYER = 2
MOCK_D = 64
VOCAB = 512
IM_END, PAD, IM_START = 500, 501, 502
RESULTS_SNAPSHOT = sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*"))


# ------------------------------------------------------------------ fake tokenizer (MOCK)
class FakeTok:
    """Character-level tokenizer: ASCII -> ord, other chars -> 400 + ord % 100 (so an enclosed
    ideograph is a single token and distinct from the ASCII carrier text)."""

    pad_token_id = PAD
    eos_token_id = IM_END
    unk_token_id = -1
    chat_template = "mock"

    @staticmethod
    def _tok(ch: str) -> int:
        o = ord(ch)
        return o if o < 400 else 400 + (o % 100)

    def __call__(self, text, add_special_tokens=False, **kw):
        return {"input_ids": [self._tok(c) for c in text]}

    def apply_chat_template(self, messages, tokenize=True, add_generation_prompt=True, enable_thinking=False, **kw):
        ids: list[int] = []
        for m in messages:
            ids += [IM_START] + self("%s\n%s" % (m["role"], m["content"]))["input_ids"] + [IM_END, 10]
        if add_generation_prompt:
            ids += [IM_START] + self("assistant\n")["input_ids"]
            ids += self("<think>\n\n</think>\n\n" if not enable_thinking else "<think>\n")["input_ids"]
        return {"input_ids": ids} if tokenize else "".join(self.decode([i]) for i in ids)

    def decode(self, ids, skip_special_tokens=False):
        out = []
        for i in ids:
            i = int(i)
            if i in (IM_END, PAD, IM_START):
                if not skip_special_tokens:
                    out.append({IM_END: "<|im_end|>", PAD: "<|endoftext|>", IM_START: "<|im_start|>"}[i])
            elif i < 400:
                out.append(chr(i))
            else:
                out.append("㈀" if i == 400 else chr(0x3200 + (i - 400)))
        return "".join(out)

    def batch_decode(self, seqs, skip_special_tokens=False):
        return [self.decode(s, skip_special_tokens) for s in seqs]

    def convert_ids_to_tokens(self, ids):
        return ["Ġ" + self.decode([i]) for i in ids]

    def convert_tokens_to_ids(self, t):
        return {"<|im_end|>": IM_END, "<|endoftext|>": PAD}.get(t, -1)


def tiny_model(seed: int = 0):
    from transformers import Qwen3_5ForCausalLM
    from transformers.models.qwen3_5.configuration_qwen3_5 import Qwen3_5TextConfig

    cfg = Qwen3_5TextConfig(
        hidden_size=MOCK_D, intermediate_size=128, num_hidden_layers=4, num_attention_heads=4, num_key_value_heads=2,
        head_dim=16, vocab_size=VOCAB, layer_types=["linear_attention", "linear_attention", "linear_attention", "full_attention"],
        linear_num_key_heads=2, linear_num_value_heads=4, linear_key_head_dim=16, linear_value_head_dim=16,
        linear_conv_kernel_dim=4, max_position_embeddings=512, full_attention_interval=4,
        rope_parameters={"rope_theta": 10000.0, "partial_rotary_factor": 0.25, "rope_type": "default",
                         "mrope_section": [2, 1, 1], "mrope_interleaved": True},
        eos_token_id=IM_END, pad_token_id=PAD,
    )
    torch.manual_seed(seed)
    m = Qwen3_5ForCausalLM(cfg).eval()
    for p in m.parameters():
        p.requires_grad_(False)
    return m


@pytest.fixture(scope="module")
def target():
    return M.Target(model=tiny_model(), tokenizer=FakeTok(), device="cpu", model_id="MOCK/tiny-qwen3_5",
                    revision="mock", model_class="Qwen3_5ForCausalLM")


@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    """Point the frozen constants at the tiny model and keep every path inside tmp (set per test)."""
    monkeypatch.setattr(C, "LAYER", MOCK_LAYER)
    monkeypatch.setattr(C, "HIDDEN_STATES_INDEX", MOCK_LAYER + 1)
    monkeypatch.setattr(C, "D_MODEL", MOCK_D)
    monkeypatch.setattr(C, "N_LAYERS", 4)
    monkeypatch.setattr(C, "DEV_EXTRA_LAYERS", (1, 3))
    yield


def items():
    return [
        {"item_id": "own-01A", "pair_id": "own-01", "family": "ownership", "split": "dev", "render": "chat", "system": None,
         "prompt_text": "Mira has the red key. Leo has the blue key. Who has the red key?",
         "primary": {"name": "red_key_owner", "question": "Who has the red key?", "candidates": ["Mira", "Leo"], "answer": "Mira"}},
        {"item_id": "own-02B", "pair_id": "own-02", "family": "ownership", "split": "test", "render": "chat", "system": None,
         "prompt_text": "Leo has the red key. Mira has the blue key. Who has the red key?",
         "primary": {"name": "red_key_owner", "question": "Who has the red key?", "candidates": ["Mira", "Leo"], "answer": "Leo"}},
    ]


# ================================================================== capture / states
def test_capture_hook_equals_hidden_states(target):
    ids = target.tokenizer("hello world")["input_ids"]
    acts = M.capture(target.model, ids, [0, 1, 2], [len(ids) - 1, 2])
    with torch.no_grad():
        out = target.model(torch.tensor([ids]), output_hidden_states=True)
    for L in (0, 1, 2):
        assert torch.allclose(acts[L][0], out.hidden_states[L + 1][0, -1].float(), atol=1e-5)
        assert torch.allclose(acts[L][1], out.hidden_states[L + 1][0, 2].float(), atol=1e-5)
        assert acts[L].dtype == torch.float32


def test_render_is_pre_answer(target):
    ids = M.render_item(target.tokenizer, "Who has the key?")
    text = target.tokenizer.decode(ids)
    assert text.endswith("<think>\n\n</think>\n\n")
    assert "<|im_start|>assistant" in text
    assert target.tokenizer.decode([ids[-1]]) == "\n"


def test_states_cache_rows_and_resume(target, tmp_path):
    sd, mp, ledger = tmp_path / "states", tmp_path / "meta.jsonl", tmp_path / "compute.jsonl"
    meta = S.ensure_states(target, items(), states_dir=sd, meta_path=mp, ledger_path=ledger, module="mock")
    r = meta["own-01A"]
    for k in ("item_id", "model_id", "model_sha", "layer", "hook", "hidden_states_index", "pos", "n_tokens", "read_token",
              "prompt_ids_sha256", "render", "enable_thinking", "dtype_capture", "dtype_saved", "norm", "captured_at", "pre_answer"):
        assert k in r, k
    assert r["pre_answer"] is True and r["layer"] == MOCK_LAYER and r["hidden_states_index"] == MOCK_LAYER + 1
    assert r["pos"] == r["n_tokens"] - 1 and r["read_token"] == "\n" and r["dtype_saved"] == "float32"
    h = S.load_state("own-01A", sd)
    assert h.dtype == torch.float32 and h.shape == (MOCK_D,)
    # dev item gets the extra layers, test item does not
    assert S.state_path("own-01A", sd, 1).exists() and S.state_path("own-01A", sd, 3).exists()
    assert not S.state_path("own-02B", sd, 1).exists()
    rows = A.read_jsonl(mp)
    assert {(x["item_id"], x["layer"]) for x in rows} == {("own-01A", 2), ("own-01A", 1), ("own-01A", 3), ("own-02B", 2)}
    assert [x["role"] for x in rows if x["layer"] != MOCK_LAYER] == ["dev_extra_layer", "dev_extra_layer"]
    # the state equals a direct capture; resume is a no-op; ledger has the two steps
    ids = M.render_item(target.tokenizer, items()[0]["prompt_text"])
    assert torch.allclose(h, M.capture_last(target.model, ids, MOCK_LAYER))
    n_before = len(A.read_jsonl(ledger))
    S.ensure_states(target, items(), states_dir=sd, meta_path=mp, ledger_path=ledger, module="mock")
    assert len(A.read_jsonl(mp)) == 4 and len(A.read_jsonl(ledger)) == n_before
    assert {x["step"] for x in A.read_jsonl(ledger)} == {"capture", "capture_offgrid"}
    stats = S.dev_state_stats(items(), sd)
    assert stats["n"] == 1 and torch.allclose(stats["mean"], h)


def test_render_drift_is_an_error(target, tmp_path):
    sd, mp = tmp_path / "states", tmp_path / "meta.jsonl"
    S.ensure_states(target, items()[1:], states_dir=sd, meta_path=mp, ledger_path=tmp_path / "c.jsonl")
    drifted = dict(items()[1], prompt_text="changed text")
    with pytest.raises(RuntimeError, match="different render"):
        S.ensure_states(target, [drifted], states_dir=sd, meta_path=mp, ledger_path=tmp_path / "c.jsonl")


# ================================================================== generation
def test_greedy_target_and_prompt_only(target):
    res, ids = G.target_answer(target, items()[0], max_new_tokens=6)
    assert res.n_prompt_tokens == len(ids) and 0 <= res.n_new_tokens <= 6
    assert res.finish_reason in ("eos", "length") and res.sampling["do_sample"] is False
    res2, ids2, visible = G.prompt_only_answer(target, items()[0], max_new_tokens=6)
    assert items()[0]["prompt_text"] in visible and items()[0]["primary"]["question"] in visible
    assert "<explanation>" not in visible and "<activation>" not in visible
    assert target.tokenizer.decode(ids2).endswith("<think>\n\n</think>\n\n")


def test_finish_reason_logic():
    assert G._finish([1, 2, IM_END, 4], 8, {IM_END}) == ([1, 2], "eos")
    assert G._finish([1, 2, 3, 4], 4, {IM_END}) == ([1, 2, 3, 4], "length")
    assert G._finish([1, 2], 4, {IM_END}) == ([1, 2], "eos")


def test_seed_is_stable_and_recorded(target):
    assert C.stable_seed("g1", "nla", "own-03A", 0) == C.stable_seed("g1", "nla", "own-03A", 0)
    assert C.stable_seed("g1", "nla", "own-03A", 0) != C.stable_seed("g1", "nla", "own-03A", 1)
    assert C.stable_seed("g1", "nla", "own-03A", 0) != C.stable_seed("g1", "olens", "own-03A", 0)
    assert C.gen_id("g1", "nla", "own-03A", 0) == "g1|nla|own-03A|s0"
    ids = target.tokenizer("abc")["input_ids"]
    a = G.generate_ids(target.model, target.tokenizer, ids, max_new_tokens=8, sampling=C.SAMPLING, seed=123)
    b = G.generate_ids(target.model, target.tokenizer, ids, max_new_tokens=8, sampling=C.SAMPLING, seed=123)
    assert a.new_ids == b.new_ids and a.seed == 123 and a.sampling["top_k"] == 64


# ================================================================== OLens
def test_olens_carrier_scan(target):
    ids, slot, char, cid = R.olens_carrier(target.tokenizer, MOCK_LAYER)
    assert 0x3200 <= ord(char) < 0x3400 and ids.count(cid) == 1 and ids[slot] == cid
    assert target.tokenizer(char)["input_ids"] == [cid]
    rendered = target.tokenizer.decode(ids)
    assert f"layer {MOCK_LAYER} of a language model" in rendered and f"<activation>{char}</activation>" in rendered


def test_olens_embedding_replacement(target, monkeypatch):
    reader = R.OLensReader(max_new_tokens=5)
    reader.target = target  # adapter-less MOCK: the probed tiny model stands in for base+LoRA
    captured = {}

    def fake_generate_ids(model, tok, ids, *, max_new_tokens, sampling, seed, inputs_embeds, adapter_enabled):
        captured.update(ids=ids, e=inputs_embeds.clone(), cap=max_new_tokens, seed=seed, sampling=sampling)
        return G.GenResult([1], "- a concept\n- another one", len(ids), 2, "eos", 0.01, None, seed, dict(sampling))

    monkeypatch.setattr(R, "generate_ids", fake_generate_ids)
    h = torch.randn(MOCK_D) * 300
    res = reader.read(h, MOCK_LAYER, seed=7)
    ids, slot, char, cid = reader.carrier(MOCK_LAYER)
    e, base = captured["e"], target.model.get_input_embeddings()(torch.tensor([ids]))
    assert torch.allclose(e[0, slot].norm(), torch.tensor(C.OLENS_ALPHA), rtol=1e-3)
    assert torch.nn.functional.cosine_similarity(e[0, slot], h, dim=0) > 0.999
    mask = torch.ones(len(ids), dtype=torch.bool)
    mask[slot] = False
    assert torch.allclose(e[0, mask], base[0, mask])
    assert captured["cap"] == 5 and captured["seed"] == 7 and captured["sampling"]["top_p"] == 0.95
    assert res.native["samples"] == ["- a concept\n- another one"] and res.native["bullets"] == ["a concept", "another one"]
    assert res.input["injection"] == "olens_replace_alpha16000_unit" and res.input["marker_index"] == slot
    assert res.input["layer_in_prompt"] == MOCK_LAYER and res.input["prompt_ids_sha256"] == C.sha256_ids(ids)
    row = res.row()
    for k in ("input", "sampling", "raw_output", "native", "n_prompt_tokens", "n_new_tokens", "finish_reason", "wall_s", "adapter"):
        assert k in row


def test_olens_real_generate_is_seeded(target):
    reader = R.OLensReader(max_new_tokens=6)
    reader.target = target
    h = torch.randn(MOCK_D)
    a = reader.read(h, MOCK_LAYER, seed=11)
    b = reader.read(h, MOCK_LAYER, seed=11)
    assert a.raw_output == b.raw_output and a.n_new_tokens <= 6 and a.finish_reason in ("eos", "length")
    assert a.n_prompt_tokens == len(reader.carrier(MOCK_LAYER)[0])


# ================================================================== NLA
def mock_meta(tok: FakeTok):
    text = "Here is the vector:\n\n<concept>㈜</concept>\n\nPlease provide an explanation."
    ids = tok(text)["input_ids"]
    inj = tok("㈜")["input_ids"][0]
    p = ids.index(inj)
    return {"_mock": True, "tokens": {"injection_char": "㈜", "injection_token_id": inj,
                                      "injection_left_neighbor_id": ids[p - 1], "injection_right_neighbor_id": ids[p + 1]},
            "prompt_templates": {"actor": "Describe the vector.\n\nHere is the vector:\n\n<concept>{injection_char}</concept>\n\nPlease provide an explanation."}}


def test_marker_well_formed_matches_reference():
    ok = R.marker_well_formed([1, 29, 158983, 510, 2], 158983, 29, 510)
    assert ok is True
    assert R.marker_well_formed([1, 29, 158983, 511, 2], 158983, 29, 510) is False
    assert R.marker_well_formed([29, 158983, 510, 158983], 158983, 29, 510) is False
    assert R.marker_well_formed([158983, 510], 158983, 29, 510) is False


def test_nla_hook_norm_matched_add():
    tok = FakeTok()
    model = tiny_model(1)
    reader = R.NLAReader(max_new_tokens=4).attach(model, tok, mock_meta(tok), device="cpu")
    ids, mp = reader.ids, reader.marker
    meta = reader.meta["tokens"]
    assert ids[mp] == meta["injection_token_id"] and (ids[mp - 1], ids[mp + 1]) == (meta["injection_left_neighbor_id"], meta["injection_right_neighbor_id"])
    v = torch.randn(MOCK_D) * 50
    store = {}
    blk = M.blocks(model)[C.NLA_INJECT_LAYER_IDX]
    hd = blk.register_forward_hook(lambda m, i, o: store.__setitem__("h", (o[0] if isinstance(o, tuple) else o).detach().clone()))
    x = torch.tensor([ids])
    with torch.no_grad():
        reader._vec["v"] = None
        model(x, use_cache=False)
        clean = store["h"]
        reader._vec["v"] = v
        model(x, use_cache=False)
        injected = store["h"]
        reader._vec["v"] = None
    hd.remove()
    # our hook runs after the capture hook? no: hooks run in registration order, reader's first,
    # so `injected` is the post-injection residual. Expected: clean + ||clean[mp]|| * unit(v) at mp only.
    expect = clean.clone()
    expect[0, mp] = clean[0, mp] + clean[0, mp].norm() * v / (v.norm() + 1e-9)
    assert torch.allclose(injected, expect, atol=1e-4)
    assert reader.n_hook_calls == 1
    # EasyNLA's reference implementation agrees (if importable)
    C.add_third_party_to_path()
    try:
        from nla.injection import karvonen_inject_in_residual  # type: ignore
    except Exception:
        pytest.skip("EasyNLA not importable; reference comparison skipped")
    ref = karvonen_inject_in_residual(x, clean.clone(), v[None], meta["injection_token_id"],
                                      meta["injection_left_neighbor_id"], meta["injection_right_neighbor_id"])
    assert torch.allclose(ref, injected, atol=1e-4)
    # decode steps (seq_len 1) never re-inject
    with torch.no_grad():
        reader._vec["v"] = v
        model(torch.tensor([[ids[0]]]), use_cache=False)
        reader._vec["v"] = None
    assert reader.n_hook_calls == 1


def test_nla_read_and_strip():
    tok = FakeTok()
    reader = R.NLAReader(max_new_tokens=6).attach(tiny_model(2), tok, mock_meta(tok), device="cpu")
    h = torch.randn(MOCK_D)
    res = reader.read(h, MOCK_LAYER, seed=3)
    assert res.extra["n_hook_injections"] == 1 and res.n_prompt_tokens == len(reader.ids)
    assert res.input["injection"] == "nla_add_normmatched_block1" and res.input["marker_index"] == reader.marker
    assert isinstance(res.native["samples"][0], str) and res.finish_reason in ("eos", "length")
    assert R.strip_explanation("<explanation>foo bar</explanation> trailing") == "foo bar"
    assert R.strip_explanation("no tags at all") == "no tags at all"
    assert R.strip_explanation("<explanation>unclosed") == "unclosed"


def test_nla_marker_drift_raises():
    tok = FakeTok()
    meta = mock_meta(tok)
    meta["tokens"]["injection_right_neighbor_id"] = 999
    with pytest.raises(RuntimeError, match="marker not well formed"):
        R.NLAReader().attach(tiny_model(), tok, meta)


# ================================================================== J-lens
def test_jlens_cosine_readout(target):
    torch.manual_seed(0)
    J = {MOCK_LAYER: torch.randn(MOCK_D, MOCK_D) / 8 + torch.eye(MOCK_D)}
    w_u = M.unembed_weight(target.model).float()
    reader = R.JLensReader(k=10).bind_tensors(J, w_u, target.tokenizer)
    h = torch.randn(MOCK_D) * 20
    res = reader.read(h, MOCK_LAYER)
    direct = (w_u @ (J[MOCK_LAYER] @ h)) / (w_u @ J[MOCK_LAYER]).norm(dim=1)
    vals, ids = torch.topk(direct, 10)
    assert res.native["token_ids"] == ids.tolist()
    assert all(abs(a - b) < 2e-3 for a, b in zip(res.native["scores"], vals.tolist()))
    assert res.native["tokens"] == M.display_tokens(target.tokenizer, ids.tolist())
    assert all(not t.startswith("Ġ") for t in res.native["tokens"]) and res.input["injection"] == "none"
    assert abs(res.native["scores"][0]) <= float(h.norm()) + 1e-3  # magnitude-free in W_U rows, bounded by ||h||
    with pytest.raises(ValueError):
        reader.read(h, 99)


# ================================================================== accounting / resume / guard
def test_ledger_and_resume_in_tmp(tmp_path):
    led = A.StepLedger(step="olens", module="g1")
    led.add(60, 90, 1.5, 55.0)
    led.add(60, 128, 2.0, 57.0)
    row = led.flush(tmp_path / "compute.jsonl")
    assert row["n_calls"] == 2 and row["new_tokens"] == 218 and row["peak_mem_gb"] == 57.0
    for k in ("step", "module", "n_calls", "prompt_tokens", "new_tokens", "wall_s", "peak_mem_gb", "gpu", "started", "ended"):
        assert k in row
    gens = tmp_path / "g1.jsonl"
    A.append_jsonl(gens, {"gen_id": "g1|nla|own-03A|s0", "x": 1})
    assert A.done_ids(gens) == {"g1|nla|own-03A|s0"}
    assert A.StepLedger(step="x", module="y").flush(tmp_path / "c2.jsonl") is None


def test_collector_rows_resume(target, tmp_path, monkeypatch):
    from projects.g_agreement.g1_agreement import collect as G1

    sd, mp, gens, led = tmp_path / "states", tmp_path / "meta.jsonl", tmp_path / "g1.jsonl", tmp_path / "c.jsonl"
    S.ensure_states(target, items(), states_dir=sd, meta_path=mp, ledger_path=led)
    reader = R.OLensReader(max_new_tokens=4)
    reader.target = target
    n1 = G1.collect_verbalizer(reader, items(), module="g1", sample_idxs=[0], gens_path=gens, ledger_path=led, states_dir=sd, layer=MOCK_LAYER)
    n2 = G1.collect_verbalizer(reader, items(), module="g1", sample_idxs=[0], gens_path=gens, ledger_path=led, states_dir=sd, layer=MOCK_LAYER)
    assert (n1, n2) == (2, 0)
    rows = A.read_jsonl(gens)
    r = rows[0]
    for k in ("gen_id", "module", "method", "condition", "item_id", "state_item_id", "sample_idx", "seed", "input", "sampling",
              "raw_output", "native", "n_prompt_tokens", "n_new_tokens", "finish_reason", "wall_s", "peak_mem_gb", "model_sha", "adapter", "created_at"):
        assert k in r, k
    assert r["gen_id"] == "g1|olens|own-01A|s0" and r["seed"] == C.stable_seed("g1", "olens", "own-01A", 0)
    # off-grid rows get a layer tag and their own condition
    G1.collect_verbalizer(reader, items()[:1], module="g1", sample_idxs=[0], gens_path=gens, ledger_path=led,
                          states_dir=sd, layer=1, condition="offgrid_check", step="olens_offgrid")
    off = [x for x in A.read_jsonl(gens) if x["condition"] == "offgrid_check"]
    assert off and off[0]["gen_id"].endswith("|L1") and off[0]["layer"] == 1 and off[0]["input"]["layer_in_prompt"] == 1
    # state_free (mean of dev states) and jlens_null rows
    G1.collect_state_free(reader, items(), module="g3", gens_path=gens, ledger_path=led, states_dir=sd)
    sf = [x for x in A.read_jsonl(gens) if x["condition"] == "state_free"]
    assert len(sf) == len(items()) and sf[0]["state_item_id"] is None and sf[0]["module"] == "g3"
    assert sf[0]["input"]["injection_source"] == "mean_dev_activation" and sf[0]["item_id"] == items()[0]["item_id"]
    J = {MOCK_LAYER: torch.eye(MOCK_D)}
    jl = R.JLensReader().bind_tensors(J, M.unembed_weight(target.model), target.tokenizer)
    G1.collect_jlens_null(jl, items(), module="g1", gens_path=gens, ledger_path=led, states_dir=sd)
    nz = [x for x in A.read_jsonl(gens) if x["method"] == "jlens_null"]
    assert len(nz) == 2 * len(items()) and {x["condition"] for x in nz} == {"noise_ceiling"}
    assert {x["input"]["injection_source"] for x in nz} == {"random_same_norm", "mean_dev_activation"}
    assert all(x["state_item_id"] is None and x["item_id"] in {i["item_id"] for i in items()} for x in nz)
    steps = {x["step"] for x in A.read_jsonl(led)}
    assert {"olens", "olens_offgrid", "state_free_olens", "jlens_null"} <= steps


def test_frozen_guard_refuses_test_without_freeze(monkeypatch, tmp_path):
    monkeypatch.setattr(C, "FROZEN_CONFIG", tmp_path / "frozen_config.json")
    with pytest.raises(SystemExit):
        C.require_frozen("test")
    C.require_frozen("dev")  # dev may run unfrozen


# ================================================================== optional: real tokenizer proxy
def real_tokenizer_proxy():
    """Qwen3.5-4B-Base's cached tokenizer.json (NOT byte-identical to Qwen3.6-27B's; same vocab
    size) with the Qwen3.6-27B chat template from cache/g_assets — a MOCK PROXY for the render
    and marker-scan logic. Skipped when not cached locally."""
    snaps = sorted((Path.home() / ".cache/huggingface/hub/models--Qwen--Qwen3.5-4B-Base/snapshots").glob("*"))
    tmpl = REPO / "cache/g_assets/Qwen__Qwen3.6-27B/chat_template.jinja"
    if not snaps or not tmpl.exists():
        return None
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(str(snaps[-1]))
    tok.chat_template = tmpl.read_text()
    return tok


@pytest.mark.skipif(real_tokenizer_proxy() is None, reason="no cached Qwen3.5 tokenizer / Qwen3.6 template")
def test_proxy_tokenizer_render_and_markers():
    import yaml

    tok = real_tokenizer_proxy()
    ids = M.render_item(tok, "Mira has the red key. Who has the red key?")
    assert tok.decode(ids).endswith("<think>\n\n</think>\n\n")
    _ids, slot, char, cid = R.olens_carrier(tok, 42)
    assert ord(char) >= 0x3200 and _ids.count(cid) == 1
    meta_p = REPO / "cache/g_assets/ceselder__qwen3.6-27b-nla-rl/nla_meta.yaml"
    if meta_p.exists():
        meta = yaml.safe_load(meta_p.read_text())
        nids, marker, _ = R.nla_prompt(tok, meta)
        assert nids[marker] == C.NLA_INJECTION_TOKEN_ID
        assert (nids[marker - 1], nids[marker + 1]) == (C.NLA_LEFT_NEIGHBOR_ID, C.NLA_RIGHT_NEIGHBOR_ID)
        assert (char, cid) == (C.NLA_INJECTION_CHAR, C.NLA_INJECTION_TOKEN_ID)  # README: the scan lands on ㈜


def test_zz_results_dir_untouched():
    """MOCK tests never write under results/."""
    now = sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*"))
    assert now == RESULTS_SNAPSHOT
