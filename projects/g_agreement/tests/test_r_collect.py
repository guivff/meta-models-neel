"""Phase R collector tests (PLAN_R §1 WS2). Two kinds:

CPU (MOCK, always run): the tiny Qwen3.5 model + character tokenizer of ``test_readers_mock`` stand in for the target.
  - batched right-padded capture == single-item ``M.capture`` at every layer, both renders (the pod check's logic);
  - ``teacher_forced_lp`` == ``scoring_lo._summed_logprobs`` on equal heads, and == per-row single forwards on unequal heads;
  - renders (assistant onset, raw has no specials, truncation), logit-lens first tokens (jlens fallback), derangement;
  - the collector end to end on tmp paths: index / state files, logit-lens, prompt-only, reader LO for a mock J-lens,
    Oracle and NLA (one- and two-sided facts, shuffled and state-free controls, pool-eval subset), k-way rows, resume,
    ledger steps, the freeze guard. Nothing is written under results/ or cache/.

POD (skipped unless CUDA + ``R_POD_TESTS=1``): the same two numerical checks on the real Qwen3.6-27B (bf16, H100):
  batched capture vs ``M.capture`` cos >= 0.9999 at every captured layer in both renders on 4 items;
  ``teacher_forced_lp`` vs ``_summed_logprobs`` |delta| < 1e-3 on equal heads.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_r_collect.py -q``
Pod: ``R_POD_TESTS=1 python -m pytest projects/g_agreement/tests/test_r_collect.py -q -k pod``
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest
import torch

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

from projects.g_agreement.core import accounting as A  # noqa: E402
from projects.g_agreement.core import config as C  # noqa: E402
from projects.g_agreement.core import model as M  # noqa: E402
from projects.g_agreement.core import readers as R  # noqa: E402
from projects.g_agreement.core import scoring_lo as LO  # noqa: E402
from projects.g_agreement.r_bench import collect as RC  # noqa: E402
from projects.g_agreement.r_bench import datasets as D  # noqa: E402
from projects.g_agreement.tests.test_readers_mock import MOCK_D, FakeTok, mock_meta, tiny_model  # noqa: E402

CACHE_R = REPO / "cache" / "g_agreement" / "r"
# Per-path, concurrency-proof isolation guard (tests/_write_guard.py; replaces the whole-tree snapshots, which other
# sessions' and pods' writes into the shared trees tripped). Records this process's writes into these roots.
from projects.g_agreement.tests import _write_guard as WG  # noqa: E402

_GUARD = WG.ModuleWriteGuard([REPO / "results" / "g_agreement", CACHE_R])
_write_guard = _GUARD.fixture()
MOCK_LAYERS = (0, 1, 2, 3)
POD = bool(os.environ.get("R_POD_TESTS")) and torch.cuda.is_available()
pod_only = pytest.mark.skipif(not POD, reason="pod-only: needs CUDA and R_POD_TESTS=1 (loads Qwen3.6-27B)")


# ------------------------------------------------------------------ fixtures
@pytest.fixture(scope="module")
def target():
    return M.Target(model=tiny_model(), tokenizer=FakeTok(), device="cpu", model_id="MOCK/tiny-qwen3_5",
                    revision="mock", model_class="Qwen3_5ForCausalLM")


def unredirected(root: Path) -> list[str]:
    """GUARDS.md rule 1: every entry of the module's own ``output_paths()`` enumeration that is NOT under ``root``, plus
    every module Path global the enumeration misses (``unlisted_paths``, the catch-all). Empty = fully redirected."""
    root = Path(root).resolve()
    out = [name for name, p in RC.output_paths().items() if root not in Path(p).resolve().parents and Path(p).resolve() != root]
    return out + [f"unlisted:{n}" for n in RC.unlisted_paths()]


@pytest.fixture(autouse=True)
def mock_config(monkeypatch, tmp_path):
    """Tiny-model constants; every path in ``RC.output_paths()`` under tmp (checked through the module's enumeration, with
    the ``unlisted_paths`` catch-all, so a new output path cannot escape the redirect unnoticed); run kind "test"."""
    monkeypatch.setattr(C, "LAYER", 2)
    monkeypatch.setattr(C, "HIDDEN_STATES_INDEX", 3)
    monkeypatch.setattr(C, "D_MODEL", MOCK_D)
    monkeypatch.setattr(C, "N_LAYERS", 4)
    monkeypatch.setattr(RC, "LAYERS", MOCK_LAYERS)
    monkeypatch.setattr(RC, "READ_LAYERS", {"jlens": MOCK_LAYERS, "olens": (2, 3), "skip_a": (2,), "skip_d": (2,), "nla": (2,)})
    monkeypatch.setattr(RC, "PRIMARY_LAYER", {"jlens": 2, "olens": 3, "skip_a": 2, "skip_d": 2, "nla": 2})
    monkeypatch.setattr(RC, "RESULTS", tmp_path / "results")
    monkeypatch.setattr(RC, "FROZEN_R", tmp_path / "manifest" / "frozen_config_r.json")
    monkeypatch.setattr(C, "RESULTS_DIR", tmp_path / "results_root")
    monkeypatch.setattr(A.C, "COMPUTE_LEDGER", tmp_path / "compute.jsonl")
    monkeypatch.setattr(RC, "RUN_KIND", "test")
    monkeypatch.setattr(RC, "ITEMS_PATH", None)
    RC.RUN_META.clear()
    RC.set_shard(None)
    RC.set_cache_dir(tmp_path / "cache_r")
    RC._LEDGERS.clear()
    RC._SHAS.clear()
    assert unredirected(tmp_path) == [], f"output paths not redirected under tmp: {unredirected(tmp_path)}"
    yield
    RC._LEDGERS.clear()
    RC._DONE.clear()
    RC._SHAS.clear()
    RC.RUN_META.clear()
    RC.set_shard(None)


TEXTS = ["The movie was wonderful.", "I hated every minute of this film", "A fine living room with a view, truly.",
         "short", "The cat sat on the mat and the dog slept by the fire for hours"]


def mock_items(tmp_path: Path) -> Path:
    """Two facts in the items_r schema: a two-sided one (candidates A / B, single characters for the mock J-lens) and a
    one-sided one (X vs a filler without a single-token form). 6 test + 4 pool items each."""
    items = []
    for ds, cands, sided, jl in (("92_glue_sst2", ["A", "B"], "two", ["A", "B"]), ("66_living-room", ["X", "no such phrase"], "one", ["X", None])):
        for split, n in (("test", 6), ("pool", 4)):
            for k in range(n):
                y = k % 2
                items.append({"item_id": f"r-{ds}-{split}-{k:04d}", "dataset": ds, "tag": "TOPIC" if sided == "two" else "SURFACE",
                              "split": split, "label": y, "raw_target": str(y), "prompt_text": TEXTS[k % len(TEXTS)] + f" #{k}",
                              "render": "chat", "system": None,
                              "primary": {"name": ds, "question": "Which?", "candidates": cands, "answer": cands[0] if y else cands[1],
                                          "template": D.SPECS[ds].template, "sided": sided, "jlens": jl}})
    p = tmp_path / "items_r.json"
    p.write_text(json.dumps({"meta": {"mock": True}, "items": items}))
    return p


def mock_kway_items(tmp_path: Path) -> Path:
    cands = ["A", "B", "C"]
    items = []
    for ci, c in enumerate(cands):
        for split, n in (("test", 3), ("pool", 2)):
            for k in range(n):
                items.append({"item_id": f"rk-97_news_class-{split}-{ci}-{k:04d}", "dataset": "97_news_class", "tag": "TOPIC", "split": split,
                              "label": ci, "raw_target": c, "prompt_text": TEXTS[(ci + k) % len(TEXTS)] + f" k{ci}{k}", "render": "chat",
                              "system": None, "primary": {"name": "97_news_class", "question": "Topic?", "candidates": cands, "answer": c,
                                                          "template": "The topic is {X}.", "sided": "kway", "k": 3}})
    p = tmp_path / "items_rk.json"
    p.write_text(json.dumps({"meta": {"mock": True}, "items": items}))
    return p


def mock_jlens(target):
    torch.manual_seed(0)
    J = {L: torch.randn(MOCK_D, MOCK_D) / 8 + torch.eye(MOCK_D) for L in MOCK_LAYERS}
    return R.JLensReader().bind_tensors(J, M.unembed_weight(target.model), target.tokenizer)


def mock_olens(target):
    reader = R.OLensReader()
    reader.target = target  # adapter-less MOCK: the tiny model stands in for base + LoRA
    return reader


def mock_nla():
    tok = FakeTok()
    return R.NLAReader().attach(tiny_model(1), tok, mock_meta(tok), device="cpu")


# ------------------------------------------------------------------ the two correctness checks (shared by MOCK and POD)
def check_capture_batched_equals_single(target, texts, layers, min_cos: float, atol: float | None):
    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    worst = 1.0
    for render in RC.RENDERS:
        rows = [RC.render_ids(tok, t, render) for t in texts]
        assert len({len(r) for r in rows}) > 1, "the check needs rows of different lengths (padding must matter)"
        order = sorted(range(len(rows)), key=lambda i: len(rows[i]))
        got = RC.capture_batch(target.model, [rows[i] for i in order], list(layers), pad)
        inv = torch.as_tensor(np.argsort(order))
        for L in layers:
            batched = got[L][inv]
            for i, r in enumerate(rows):
                single = M.capture(target.model, r, [L], [len(r) - 1])[L][0]
                cos = float(torch.nn.functional.cosine_similarity(batched[i], single, dim=0))
                worst = min(worst, cos)
                assert cos >= min_cos, (render, L, i, cos)
                if atol is not None:
                    assert torch.allclose(batched[i], single, atol=atol, rtol=1e-4), (render, L, i)
    return worst


def check_teacher_forced_matches_summed(target, heads, cands, tol: float):
    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    dev = next(target.model.parameters()).device
    # equal heads: the same forward as _summed_logprobs (same keep), so the sums agree to float precision
    head = heads[0]
    rows = [head + LO.encode(tok, c) for c in cands]
    a = RC.teacher_forced_lp(target.model, rows, [len(head)] * len(rows), pad, dev)
    b = LO._summed_logprobs(target.model, rows, len(head), pad, dev)
    deltas = [abs(x - y) for x, y in zip(a, b)]
    assert max(deltas) < tol, deltas
    return max(deltas)


# ------------------------------------------------------------------ MOCK: the checks
def test_mock_capture_batched_equals_single(target):
    worst = check_capture_batched_equals_single(target, TEXTS, MOCK_LAYERS, min_cos=0.9999, atol=1e-4)
    assert worst >= 0.9999


def test_mock_teacher_forced_lp(target):
    tok = target.tokenizer
    pad = tok.pad_token_id
    dev = "cpu"
    heads = [M.render_item(tok, "Is it good? A or B", None), M.render_item(tok, "Longer question text here, A or B", None)]
    check_teacher_forced_matches_summed(target, heads, ["A", "B"], tol=1e-4)
    # unequal heads in one batch == each row scored alone (fp32 CPU: tiny differences only)
    rows, hl = [], []
    for h in heads:
        for c in ("A", "Bee"):
            rows.append(h + LO.encode(tok, c))
            hl.append(len(h))
    got = RC.teacher_forced_lp(target.model, rows, hl, pad, dev)
    for r, h, g in zip(rows, hl, got):
        alone = LO._summed_logprobs(target.model, [r], h, pad, dev)[0]
        assert abs(alone - g) < 1e-3, (alone, g)
    # the sum is over the candidate tokens only: a 3-token candidate sums 3 log-probs (each <= 0, so lp decreases)
    one = RC.teacher_forced_lp(target.model, [heads[0] + LO.encode(tok, "Bee")], [len(heads[0])], pad, dev)[0]
    assert one <= RC.teacher_forced_lp(target.model, [heads[0] + LO.encode(tok, "B")], [len(heads[0])], pad, dev)[0] + 1e-6


# ------------------------------------------------------------------ MOCK: rendering, first tokens, derangement
def test_render_ids_conventions(target):
    tok = target.tokenizer
    onset = RC.onset_token(tok)
    for t in TEXTS:
        chat = RC.render_ids(tok, t, "chat")
        raw = RC.render_ids(tok, t, "raw")
        assert chat[-1] == onset and chat == M.render_item(tok, t, None)   # the core render, read at the assistant onset
        assert raw == tok(t, add_special_tokens=False)["input_ids"] and raw[-1] == ord(t[-1])   # bare text, last text token
        assert not any(i in (500, 501, 502) for i in raw)
    long = "x" * 600
    assert len(RC.render_ids(tok, long, "raw", max_tokens=256)) == 256
    chat_long = RC.render_ids(tok, long, "chat", max_tokens=256)
    assert len(chat_long) == len(M.render_item(tok, "x" * 256, None)) and chat_long[-1] == onset
    with pytest.raises(ValueError):
        RC.render_ids(tok, "a", "weird")
    # the prompt-only render carries the text, the question and both candidates and ends at the onset
    it = {"prompt_text": "The film", "system": None, "primary": {"question": "Good?", "candidates": ["pos", "neg"], "sided": "two"}}
    ids = RC.prompt_only_ids(tok, it)
    txt = tok.decode(ids)
    assert ids[-1] == onset and "The film" in txt and "Good?" in txt and '"pos" or "neg"' in txt


def test_logit_lens_tokens_fallback(target):
    tok = target.tokenizer
    ft = RC.logit_lens_tokens(tok, {"candidates": ["positive", "negative"], "jlens": [None, None]})
    assert not ft["unscorable"] and ft["form"] == "bare" and ft["source"] == "candidates"
    assert (ft["first_pos"], ft["first_neg"]) == (ord("p"), ord("n"))
    # shared first token in every spelling -> the jlens short forms
    ft = RC.logit_lens_tokens(tok, {"candidates": ["a Democrat", "a Republican"], "jlens": ["Democrat", "Republican"]})
    assert not ft["unscorable"] and ft["source"] == "jlens_forms" and (ft["first_pos"], ft["first_neg"]) == (ord("D"), ord("R"))
    ft = RC.logit_lens_tokens(tok, {"candidates": ["a Democrat", "a Republican"], "jlens": [None, None]})
    assert ft["unscorable"] and ft["first_pos"] is None and ft["source"] is None


def test_derangement_has_no_fixed_point_and_is_seeded():
    for n in (2, 3, 7, 200):
        perm = RC.derangement(n, np.random.default_rng(0))
        assert sorted(perm.tolist()) == list(range(n)) and not np.any(perm == np.arange(n))
    assert RC.derangement(200, np.random.default_rng(5)).tolist() == RC.derangement(200, np.random.default_rng(5)).tolist()
    assert RC.derangement(200, np.random.default_rng(5)).tolist() != RC.derangement(200, np.random.default_rng(6)).tolist()
    assert RC.derangement(1, np.random.default_rng(0)).tolist() == [0]
    assert RC.stable_offset("92_glue_sst2") == RC.stable_offset("92_glue_sst2") != RC.stable_offset("66_living-room")


def test_pool_eval_is_balanced_and_ordered():
    items = [{"item_id": f"r-d-pool-{k:04d}", "split": "pool", "label": (k * 7) % 2} for k in range(40)]
    items += [{"item_id": "r-d-test-0000", "split": "test", "label": 1}]
    sub = RC.pool_eval_items(items, 10)
    assert len(sub) == 10 and sum(it["label"] for it in sub) == 5 and all(it["split"] == "pool" for it in sub)
    assert [it["item_id"] for it in sub] == sorted(it["item_id"] for it in sub)
    assert len(RC.pool_eval_items(items[:3], 64)) == 3


# ------------------------------------------------------------------ MOCK: the collector end to end on tmp paths
def test_capture_dataset_and_logit_lens(target, tmp_path):
    from projects.g_agreement.r_bench import bank as B

    items = B.load_items(mock_items(tmp_path), "all", ["92_glue_sst2"])
    walls = RC.capture_dataset(target, "92_glue_sst2", items, RC.RENDERS, MOCK_LAYERS, batch=4)
    assert set(walls) == {"chat", "raw"}
    idx = json.loads(RC.index_file("92_glue_sst2").read_text())
    assert idx["item_ids"][:6] == sorted(it["item_id"] for it in items if it["split"] == "test")   # test first
    assert idx["splits"] == ["test"] * 6 + ["pool"] * 4 and idx["read_token"]["chat"] == FakeTok().decode([RC.onset_token(FakeTok())])
    assert idx["state_dtype"] == {"chat": "float16", "raw": "float16"} and len(idx["n_tokens"]["raw"]) == 10
    for render in RC.RENDERS:
        for L in MOCK_LAYERS:
            X, ids = RC.load_states("92_glue_sst2", render, L)
            assert X.shape == (10, MOCK_D) and X.dtype == np.float32 and ids == idx["item_ids"]
            # row i of the file is item i's last-token block-L output
            it = {x["item_id"]: x for x in items}[ids[3]]
            r = RC.render_ids(target.tokenizer, it["prompt_text"], render)
            single = M.capture(target.model, r, [L], [len(r) - 1])[L][0]
            assert float(torch.nn.functional.cosine_similarity(torch.from_numpy(X[3]), single, dim=0)) > 0.9999
    ll = A.read_jsonl(RC.LL_PATH)
    assert len(ll) == 20 and {r["render"] for r in ll} == {"chat", "raw"} and all(not r["unscorable"] for r in ll)
    r0 = ll[0]
    assert set(r0["per_layer"]) == {str(L) for L in MOCK_LAYERS} and (r0["first_pos"], r0["first_neg"]) == (ord("A"), ord("B"))
    v = r0["per_layer"]["2"]
    assert abs(v["margin"] - (v["lp_pos"] - v["lp_neg"])) < 1e-6
    # logit-lens value == final norm + W_U on the saved state (Y1's formula)
    X, ids = RC.load_states("92_glue_sst2", r0["render"], 2)
    h = torch.from_numpy(X[ids.index(r0["item_id"])])
    with torch.no_grad():
        z = M.final_norm(target.model)(h[None, None, :])[0, 0]
        lp = torch.log_softmax((z @ M.unembed_weight(target.model).T).float(), -1)
    assert abs(float(lp[ord("A")] - lp[ord("B")]) - v["margin"]) < 2e-2   # fp16 round trip of the state
    # resumable: a second call captures nothing and appends nothing; a changed item list is an error
    assert RC.capture_dataset(target, "92_glue_sst2", items, RC.RENDERS, MOCK_LAYERS, batch=4) == {}
    assert len(A.read_jsonl(RC.LL_PATH)) == 20
    with pytest.raises(RuntimeError):
        RC.capture_dataset(target, "92_glue_sst2", items[:-1], RC.RENDERS, MOCK_LAYERS, batch=4)
    rows = RC.flush_ledgers()
    assert {r["step"] for r in rows} == {"capture_chat", "capture_raw"} and all(r["n_calls"] == 3 for r in rows)


def test_prompt_only_rows(target, tmp_path):
    from projects.g_agreement.r_bench import bank as B

    items = B.load_items(mock_items(tmp_path), "all", ["92_glue_sst2"])
    assert RC.collect_prompt_only(target, "92_glue_sst2", items, batch=4) == 10
    assert RC.collect_prompt_only(target, "92_glue_sst2", items, batch=4) == 0
    po = A.read_jsonl(RC.PO_PATH)
    assert len(po) == 10 and po[0]["key"] == f"po|92_glue_sst2|{items[0]['item_id']}"
    r = po[0]
    assert r["candidates"] == ["A", "B"] and abs(r["lo"] - (r["lp_pos"] - r["lp_neg"])) < 1e-6 and r["greedy"] in (0, 1)
    assert r["model_says_pos"] == (r["lo"] > 0) and r["adapter"] == "none" and r["template"] == "fc"
    # the row's lp equals the single-row teacher-forced value after the forced-choice render
    tok = target.tokenizer
    head = RC.prompt_only_ids(tok, items[0])
    alone = LO._summed_logprobs(target.model, [head + LO.encode(tok, "A")], len(head), tok.pad_token_id, "cpu")[0]
    assert abs(alone - r["lp_pos"]) < 1e-3 and r["n_head_tokens"] == len(head)
    assert [x["step"] for x in RC.flush_ledgers()] == ["prompt_only"]


def test_reader_lo_rows_controls_pool_and_resume(target, tmp_path):
    from projects.g_agreement.r_bench import bank as B

    path = mock_items(tmp_path)
    items = B.load_items(path, "all")
    groups = RC.items_by_dataset(items)
    for ds, its in groups.items():
        RC.capture_dataset(target, ds, its, RC.RENDERS, MOCK_LAYERS, batch=4)
    jl, ol, nla = mock_jlens(target), mock_olens(target), mock_nla()
    # J-lens at its primary layer: natural + shuf + pool_eval(chat) rows per dataset
    n = RC.collect_reader_lo(jl, "92_glue_sst2", groups["92_glue_sst2"], 2, RC.RENDERS, batch=4, items_path=path)
    assert n == 2 * (6 + 6) + 4   # both renders × (natural + shuf) + pool_eval (4 pool items, balanced 2/2)
    assert RC.collect_reader_lo(jl, "92_glue_sst2", groups["92_glue_sst2"], 2, RC.RENDERS, batch=4, items_path=path) == 0
    rows = A.read_jsonl(RC.LO_PATH)
    nat = [r for r in rows if r["condition"] == "natural" and r["split"] == "test"]
    shuf = [r for r in rows if r["condition"] == "shuf"]
    pool = [r for r in rows if r["split"] == "pool"]
    assert len(nat) == 12 and len(shuf) == 12 and len(pool) == 4 and all(r["condition"] == "natural" and r["render"] == "chat" for r in pool)
    assert sum(r["label"] for r in pool) == 2
    assert all(r["state_item_id"] != r["item_id"] for r in shuf) and all(r["state_item_id"] == r["item_id"] for r in nat)
    assert all(r["key"].split("|")[3] == "shuf" for r in shuf) and all(r["key"] == f"jlens|L2|{r['render']}|{r['item_id']}" for r in nat)
    r0 = nat[0]
    for k in ("reader", "layer", "render", "dataset", "tag", "sided", "family", "items_file", "items_sha256", "current_r_code_sha256",
              "cand_A", "cand_B", "lp_A", "lp_B", "lo", "unscorable", "templates", "variants_A", "variants_B", "created_at"):
        assert k in r0, k
    assert r0["family"] == "r:92_glue_sst2" and r0["sided"] == "two" and abs(r0["lo"] - (r0["lp_A"] - r0["lp_B"])) < 1e-6
    # the natural row's score is the J-lens cosine readout of the saved state for the SAME candidate pair
    X, ids = RC.load_states("92_glue_sst2", r0["render"], 2)
    ref = LO.score_lo(jl, torch.from_numpy(X[ids.index(r0["item_id"])])[None], [("A", "B")], "r:92_glue_sst2", layer=2)[0]
    assert abs(ref["lo"] - r0["lo"]) < 1e-5
    # the shuffled row scores item i's candidates on item j's state
    s0 = shuf[0]
    ref = LO.score_lo(jl, torch.from_numpy(X[ids.index(s0["state_item_id"])])[None], [("A", "B")], "r:92_glue_sst2", layer=2)[0]
    assert s0["render"] == r0["render"] and abs(ref["lo"] - s0["lo"]) < 1e-5
    # state-free rows: one per render, the dataset-mean TEST state
    sf = A.read_jsonl(RC.SF_PATH)
    assert len(sf) == 2 and {r["render"] for r in sf} == {"chat", "raw"} and sf[0]["n_states_in_mean"] == 6 and sf[0]["condition"] == "state_free"
    # one-sided fact: the J-lens keeps s_pos although "no such phrase" has no single-token form
    RC.collect_reader_lo(jl, "66_living-room", groups["66_living-room"], 2, ("chat",), batch=4, items_path=path)
    one = [r for r in A.read_jsonl(RC.LO_PATH) if r["dataset"] == "66_living-room" and r["condition"] == "natural" and r["split"] == "test"]
    assert len(one) == 6 and all(r["lp_A"] is not None and r["lp_B"] is None and r["lo"] is None and r["unscorable"] is False for r in one)
    assert all(r["sided"] == "one" and r["cand_A"] == "X" and "B" in r["reason"] for r in one)
    # the same fact two-sided would be unscorable (both sides needed)
    two = RC.score_pair(jl, torch.from_numpy(X[:2]), "X", "no such phrase", "r:x", "two", 2)
    assert all(r["unscorable"] and r["lo"] is None and r["lp_A"] is not None for r in two)
    # Oracle at a non-primary layer: no pool rows, carrier per layer; NLA uses the registered dataset template
    n_ol = RC.collect_reader_lo(ol, "92_glue_sst2", groups["92_glue_sst2"], 2, ("chat",), batch=4, items_path=path)
    assert n_ol == 12 and 2 in ol._carriers
    orow = [r for r in A.read_jsonl(RC.LO_PATH) if r["reader"] == "olens"][0]
    assert orow["layer_in_prompt"] == 2 and orow["templates"] == ["- {X}"] and orow["format"] == "bullet"
    n_nla = RC.collect_reader_lo(nla, "92_glue_sst2", groups["92_glue_sst2"], 2, ("chat",), batch=4, controls=False, items_path=path)
    assert n_nla == 6 + 4   # natural + pool_eval (primary site), no controls
    nrow = [r for r in A.read_jsonl(RC.LO_PATH) if r["reader"] == "nla"][0]
    assert nrow["templates"] == ["The sentiment is {X}."] and nrow["per_template"][0]["template"] == "The sentiment is {X}."
    assert LO.NLA_TEMPLATES["r:92_glue_sst2"] == [D.SPECS["92_glue_sst2"].template] and nla.n_hook_calls > 0
    steps = {r["step"]: r for r in RC.flush_ledgers()}
    assert {"lo_jlens_L2", "control_jlens_L2", "lo_olens_L2", "control_olens_L2", "lo_nla_L2"} <= set(steps)
    assert "control_nla_L2" not in steps and steps["lo_jlens_L2"]["module"] == "r"


def test_kway_rows(target, tmp_path):
    from projects.g_agreement.r_bench import bank as B

    path = mock_kway_items(tmp_path)
    items = B.load_items(path, "all")
    RC.capture_dataset(target, "97_news_class", items, ("chat",), MOCK_LAYERS, batch=4)
    assert not RC.LL_PATH.exists()   # no logit lens for k-way parents
    assert RC.collect_prompt_only(target, "97_news_class", items, batch=6) == 15
    po = A.read_jsonl(RC.PO_PATH)[0]
    assert len(po["lp"]) == 3 and "lo" not in po and po["template"] == "kway" and 0 <= po["greedy"] < 3
    jl, ol = mock_jlens(target), mock_olens(target)
    assert RC.collect_reader_kway(jl, "97_news_class", items, 2, ("chat",), batch=4, items_path=path) == 27
    assert RC.collect_reader_kway(jl, "97_news_class", items, 2, ("chat",), batch=4, items_path=path) == 0
    assert RC.collect_reader_kway(ol, "97_news_class", items, 2, ("chat",), batch=4, items_path=path) == 27
    rows = A.read_jsonl(RC.KWAY_PATH)
    assert len(rows) == 54 and {r["cand_index"] for r in rows} == {0, 1, 2} and all(r["k"] == 3 for r in rows)
    r = [x for x in rows if x["reader"] == "jlens" and x["cand_index"] == 1][0]
    assert r["candidate"] == "B" and r["pair_partner"] == "C" and r["lp"] is not None and not r["unscorable"]
    assert r["key"] == f"jlens|L2|chat|{r['item_id']}|c1"
    # the J-lens one-sided lp is the candidate's own cosine score (independent of the partner)
    X, ids = RC.load_states("97_news_class", "chat", 2)
    ref = LO.score_lo(jl, torch.from_numpy(X[ids.index(r["item_id"])])[None], [("B", "A")], "r:97_news_class", layer=2)[0]
    assert abs(ref["lp_A"] - r["lp"]) < 1e-5
    assert {x["step"] for x in RC.flush_ledgers()} == {"capture_chat", "prompt_only", "kway_jlens_L2", "kway_olens_L2"}


def test_freeze_guard_and_shas(tmp_path, monkeypatch):
    from projects.g_agreement.r_bench import bank as B

    path = mock_items(tmp_path)
    monkeypatch.setattr(B, "ITEMS_R", path)
    monkeypatch.setattr(B, "ITEMS_RK", tmp_path / "items_rk.json")
    monkeypatch.setattr(C, "MANIFEST_DIR", tmp_path / "manifest")
    monkeypatch.setattr(C, "DATASET_DIR", tmp_path)
    with pytest.raises(SystemExit):
        RC.require_frozen_r(False, path)
    RC.require_frozen_r(True, path)   # --allow-unfrozen
    fz = RC.freeze_r()
    d = json.loads(fz.read_text())
    assert d["frozen"] and d["items_sha256"]["items_r.json"] == C.sha256_file(path) == d["items_r_sha256"]
    assert d["read_layers"]["olens"] == [2, 3] and d["nla_template_family"] == "r:<dataset>" and d["pool_eval"] == RC.POOL_EVAL
    RC.require_frozen_r(False, path)
    with pytest.raises(RuntimeError):
        RC.freeze_r()
    # another bank not covered by the freeze, or a changed bank, is refused
    other = tmp_path / "items_re.json"
    other.write_text("{}")
    with pytest.raises(SystemExit):
        RC.require_frozen_r(False, other)
    path.write_text(path.read_text() + "\n")
    with pytest.raises(SystemExit):
        RC.require_frozen_r(False, path)
    shas = RC.r_shas(path)
    assert shas["items_file"] == "items_r.json" and shas["frozen_r_code_sha256"] == d["r_code_sha256"] == shas["current_r_code_sha256"]
    assert RC.r_shas(path) == shas   # cached, not recomputed per row


def test_cli_smoke_end_to_end(target, tmp_path, monkeypatch):
    """``main`` on the mock bank with --allow-unfrozen: target loader and reader binders patched to the mocks."""
    from projects.g_agreement.g1_agreement import collect as G1
    from projects.g_agreement.r_bench import bank as B

    path = mock_items(tmp_path)
    monkeypatch.setattr(B, "ITEMS_R", path)
    monkeypatch.setattr(G1, "load_target_timed", lambda module: target)
    monkeypatch.setattr(RC, "bind_readers", lambda t, names, scales=None: [mock_jlens(t)])
    monkeypatch.setattr(M, "unload", lambda obj: None)
    monkeypatch.setattr(C, "CACHE_DIR", tmp_path / "cache")
    assert RC.main(["--phase", "A", "--datasets", "92_glue_sst2", "66_living-room", "--allow-unfrozen", "--renders", "chat",
                    "--capture-batch", "4", "--batch", "4"]) == 0
    assert RC.R_DIR == tmp_path / "cache" / "r_unfrozen"   # unfrozen runs never touch the frozen cache
    assert RC.states_done("92_glue_sst2", "chat", MOCK_LAYERS) and not RC.states_done("92_glue_sst2", "raw", MOCK_LAYERS)
    rows = A.read_jsonl(RC.LO_PATH)
    assert {r["layer"] for r in rows} == set(MOCK_LAYERS) and {r["dataset"] for r in rows} == {"92_glue_sst2", "66_living-room"}
    log = RC.LOG.read_text()
    assert "phase A:" in log and "lo jlens L2:" in log and "ledger:" in log and "capture + prompt_only" in log
    led = {r["step"] for r in A.read_jsonl(A.C.COMPUTE_LEDGER)}
    assert {"capture_chat", "prompt_only", "lo_jlens_L2", "control_jlens_L2"} <= led
    # the frozen guard refuses the same run without --allow-unfrozen
    with pytest.raises(SystemExit):
        RC.main(["--phase", "A", "--datasets", "92_glue_sst2"])


# ------------------------------------------------------------------ POD: the two checks on the real target
@pytest.fixture(scope="module")
def pod_target():
    if not POD:
        pytest.skip("pod-only")
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    return load_target_timed("r_test")


def pod_texts() -> list[str]:
    from projects.g_agreement.r_bench import bank as B

    if B.ITEMS_R.exists():
        items = B.load_items(B.ITEMS_R, "test")
        picked = [it["prompt_text"] for it in items[:: max(1, len(items) // 4)]][:4]
        if len(picked) == 4:
            return picked
    return TEXTS[:4]


@pod_only
def test_pod_capture_batched_equals_single(pod_target):
    worst = check_capture_batched_equals_single(pod_target, pod_texts(), RC.LAYERS, min_cos=0.9999, atol=None)
    print(f"[pod] batched vs single capture: worst cosine {worst:.6f} over {len(RC.LAYERS)} layers × 2 renders × 4 items")


@pod_only
def test_pod_teacher_forced_lp_equals_summed_logprobs(pod_target):
    tok = pod_target.tokenizer
    spec = D.SPECS["92_glue_sst2"]
    head = RC.prompt_only_ids(tok, {"prompt_text": pod_texts()[0], "system": None,
                                   "primary": {"question": spec.question, "candidates": [spec.pos, spec.neg], "sided": "two"}})
    worst = check_teacher_forced_matches_summed(pod_target, [head], [spec.pos, spec.neg], tol=1e-3)
    print(f"[pod] teacher_forced_lp vs _summed_logprobs: max |delta| {worst:.2e}")


def test_zz_results_and_cache_untouched():
    """Isolation guard: no test in this module wrote, created, moved or deleted anything under the guarded
    trees (per path, this process only, so concurrent pods and sessions cannot trip it; tests/_write_guard.py)."""
    _GUARD.assert_clean()


# ------------------------------------------------------------------ MOCK: per-item candidates, system turns, --items-file (WS10 / WS11 / WS12 / WS5)
def mock_context_items(tmp_path: Path) -> Path:
    """A KHOP-style fact whose candidates DIFFER per item (bridge vs a per-item distractor, single characters for the
    mock J-lens) and a CONTEXT fact whose items carry a system turn; one item declares its own template."""
    items = []
    bridges = [("F", "G"), ("H", "K"), ("F", "K"), ("G", "H")]
    for k in range(8):
        pos, neg = bridges[k % 4]
        text = f"The capital of the country famous for X{k} is"
        cue = f"X{k}"
        s0 = text.find(cue)
        if k == 3:    # WS10's pre-contract shape
            rp = {"kind": "hop1_span_end", "char_start": s0, "char_end": s0 + len(cue), "span_text": cue, "note": "E6"}
        elif k == 5:  # an unknown kind: recorded as unresolved, no rp state
            rp = {"kind": "token_index", "index": 3}
        else:         # the HANDOFF item-5 contract
            rp = {"kind": "char_span", "char_start": s0, "char_end": s0 + len(cue), "text": cue, "role": "hop1_cue", "fallback": "last_text_token"}
        items.append({"item_id": f"r-khop_bridge-{'test' if k < 6 else 'pool'}-{k:04d}", "dataset": "khop_bridge", "tag": "KHOP",
                      "split": "test" if k < 6 else "pool", "label": k % 2, "raw_target": pos, "prompt_text": text,
                      "render": "chat", "system": None, "read_position": rp,
                      "primary": {"name": "khop_bridge", "question": "Which country?", "candidates": [pos, neg] if k % 2 else [neg, pos],
                                  "answer": pos, "template": "The bridge entity is {X}." if k != 3 else "The country is {X}.",
                                  "sided": "two", "jlens": [None, None]}})
    for k in range(6):
        items.append({"item_id": f"r-ctx_capital-{'test' if k < 4 else 'pool'}-{k:04d}", "dataset": "ctx_capital", "tag": "CONTEXT",
                      "split": "test" if k < 4 else "pool", "label": k % 2, "raw_target": "S", "prompt_text": f"What is the capital of Australia? ({k})",
                      "render": "chat", "system": f"For this conversation, the capital of Australia is Sydney. [{k}]",
                      "primary": {"name": "ctx_capital", "question": "Which city?", "candidates": ["S", "C"], "answer": "S",
                                  "template": "The capital is {X}.", "sided": "two", "jlens": ["S", "C"]}})
    p = tmp_path / "items_rc2.json"
    p.write_text(json.dumps({"meta": {"mock": True}, "items": items}))
    return p


def test_system_turn_passthrough(target, tmp_path):
    from projects.g_agreement.r_bench import bank as B

    tok = target.tokenizer
    items = B.load_items(mock_context_items(tmp_path), "all", ["ctx_capital"])
    it = items[0]
    chat = RC.render_ids(tok, it["prompt_text"], "chat", system=it["system"])
    assert chat == M.render_item(tok, it["prompt_text"], it["system"]) and chat[-1] == RC.onset_token(tok)
    assert "Sydney" in tok.decode(chat) and chat != RC.render_ids(tok, it["prompt_text"], "chat")
    assert RC.render_ids(tok, it["prompt_text"], "raw", system=it["system"]) == tok(it["prompt_text"])["input_ids"]   # raw never carries the system turn
    po = RC.prompt_only_ids(tok, it)
    assert "Sydney" in tok.decode(po) and po[-1] == RC.onset_token(tok)
    # the capture renders every item WITH its system turn: the saved state equals a single capture of the system render
    RC.capture_dataset(target, "ctx_capital", items, ("chat",), MOCK_LAYERS, batch=4)
    idx = json.loads(RC.index_file("ctx_capital").read_text())
    assert idx["n_system"] == 6 and idx["per_item_candidates"] is False
    X, ids = RC.load_states("ctx_capital", "chat", 2)
    j = ids.index(it["item_id"])
    single = M.capture(target.model, chat, [2], [len(chat) - 1])[2][0]
    assert float(torch.nn.functional.cosine_similarity(torch.from_numpy(X[j]), single, dim=0)) > 0.9999
    rows = A.read_jsonl(RC.LL_PATH)
    nosys = RC.render_ids(tok, it["prompt_text"], "chat")
    assert len(rows) == 6 and idx["n_tokens"]["chat"][j] == len(chat) > len(nosys)   # the system turn is in the captured render
    jl = mock_jlens(target)
    RC.collect_reader_lo(jl, "ctx_capital", items, 2, ("chat",), batch=4)
    lo = [r for r in A.read_jsonl(RC.LO_PATH) if r["condition"] == "natural" and r["split"] == "test"]
    assert len(lo) == 4 and all(r["system"] is True and r["tag"] == "CONTEXT" for r in lo)
    RC.flush_ledgers()


def test_per_item_candidates_everywhere(target, tmp_path):
    from projects.g_agreement.r_bench import bank as B

    tok = target.tokenizer
    path = mock_context_items(tmp_path)
    items = B.load_items(path, "all", ["khop_bridge"])
    RC.capture_dataset(target, "khop_bridge", items, ("chat",), MOCK_LAYERS, batch=4)
    assert json.loads(RC.index_file("khop_bridge").read_text())["per_item_candidates"] is True
    # logit lens: each row's first tokens are ITS candidates' first tokens
    ll = {r["item_id"]: r for r in A.read_jsonl(RC.LL_PATH)}
    assert len(ll) == 8
    X, ids = RC.load_states("khop_bridge", "chat", 2)
    w_u, norm = M.unembed_weight(target.model), M.final_norm(target.model)
    for it in items:
        r = ll[it["item_id"]]
        pos, neg = it["primary"]["candidates"]
        assert r["candidates"] == [pos, neg] and (r["first_pos"], r["first_neg"]) == (ord(pos), ord(neg))
        h = torch.from_numpy(X[ids.index(it["item_id"])])
        with torch.no_grad():
            lp = torch.log_softmax((norm(h[None, None, :])[0, 0] @ w_u.T).float(), -1)
        assert abs(float(lp[ord(pos)] - lp[ord(neg)]) - r["per_layer"]["2"]["margin"]) < 2e-2
    # prompt-only: the forced-choice render names the item's own candidates
    RC.collect_prompt_only(target, "khop_bridge", items, batch=4)
    for r in A.read_jsonl(RC.PO_PATH):
        it = {x["item_id"]: x for x in items}[r["item_id"]]
        assert r["candidates"] == it["primary"]["candidates"]
        assert all(f'"{c}"' in tok.decode(RC.prompt_only_ids(tok, it)) for c in r["candidates"])
    # reader LO: natural rows score each item's own pair; the shuffled row item i's pair on item j's state; templates per item
    jl, ol, nla = mock_jlens(target), mock_olens(target), mock_nla()
    for rd in (jl, ol, nla):
        RC.collect_reader_lo(rd, "khop_bridge", items, 2, ("chat",), batch=4, items_path=path)
    rows = A.read_jsonl(RC.LO_PATH)
    by = {x["item_id"]: x for x in items}
    for r in rows:
        it = by[r["item_id"]]
        assert (r["cand_A"], r["cand_B"]) == tuple(it["primary"]["candidates"])
        fam_expect = "r:khop_bridge" if it["primary"]["template"] == "The bridge entity is {X}." else f"r:khop_bridge:t{RC.stable_offset('The country is {X}.'):06x}"
        assert r["family"] == fam_expect and r["sided"] == "two" and r["unscorable"] is False
    assert LO.NLA_TEMPLATES["r:khop_bridge"] == ["The bridge entity is {X}."] and LO.NLA_TEMPLATES[f"r:khop_bridge:t{RC.stable_offset('The country is {X}.'):06x}"] == ["The country is {X}."]
    nat = [r for r in rows if r["reader"] == "jlens" and r["condition"] == "natural" and r["split"] == "test"]
    shuf = [r for r in rows if r["reader"] == "jlens" and r["condition"] == "shuf"]
    assert len(nat) == 6 and len(shuf) == 6
    for r in nat + shuf:
        ref = LO.score_lo(jl, torch.from_numpy(X[ids.index(r["state_item_id"])])[None], [(r["cand_A"], r["cand_B"])], r["family"], layer=2)[0]
        assert abs(ref["lo"] - r["lo"]) < 1e-5
    nrow = [r for r in rows if r["reader"] == "nla" and r["item_id"] == "r-khop_bridge-test-0003"][0]
    assert nrow["templates"] == ["The country is {X}."] and nrow["per_template"][0]["template"] == "The country is {X}."
    # state-free: one row per distinct (pair, template) combination, keys suffixed |p<k>
    sf = [r for r in A.read_jsonl(RC.SF_PATH) if r["reader"] == "jlens"]
    pairs = {(r["cand_A"], r["cand_B"]) for r in sf}
    assert len(sf) == 4 and sum(r["n_items_with_pair"] for r in sf) == 6 and all("|p" in r["key"] for r in sf)
    assert pairs == {tuple(it["primary"]["candidates"]) for it in items if it["split"] == "test"}
    # k-way with per-item candidate lists (3 vs 2 candidates): rows only where the candidate exists
    kitems = [{**it, "item_id": it["item_id"].replace("khop_bridge", "khop_k"), "dataset": "khop_k",
               "primary": {**it["primary"], "name": "khop_k", "sided": "kway", "template": "The bridge entity is {X}.",
                           "candidates": it["primary"]["candidates"] + (["Z"] if k % 2 else [])}} for k, it in enumerate(items)]
    RC.capture_dataset(target, "khop_k", kitems, ("chat",), MOCK_LAYERS, batch=4)
    n = RC.collect_reader_kway(jl, "khop_k", kitems, 2, ("chat",), batch=4, items_path=path)
    kt = [it for it in kitems if it["split"] == "test"]
    assert n == sum(len(it["primary"]["candidates"]) for it in kt) == 15
    krows = A.read_jsonl(RC.KWAY_PATH)
    for r in krows:
        it = {x["item_id"]: x for x in kitems}[r["item_id"]]
        cands = it["primary"]["candidates"]
        assert r["candidate"] == cands[r["cand_index"]] and r["pair_partner"] == cands[(r["cand_index"] + 1) % len(cands)] and r["k"] == len(cands)
        ref = LO.score_lo(jl, torch.from_numpy(X[ids.index(r["item_id"].replace("khop_k", "khop_bridge"))])[None], [(r["candidate"], r["candidate"])], "r:khop_k", layer=2)[0]
        assert abs(ref["lp_A"] - r["lp"]) < 1e-5
    RC.flush_ledgers()


def test_cli_items_file_and_freeze_coverage(target, tmp_path, monkeypatch):
    """``--items-file`` runs another bank through the standard phase; the freeze must cover that file by name."""
    from projects.g_agreement.g1_agreement import collect as G1
    from projects.g_agreement.r_bench import bank as B

    path = mock_context_items(tmp_path)
    main_bank = mock_items(tmp_path)
    monkeypatch.setattr(B, "ITEMS_R", main_bank)
    monkeypatch.setattr(B, "ITEMS_RK", tmp_path / "items_rk.json")
    monkeypatch.setattr(C, "DATASET_DIR", tmp_path)
    monkeypatch.setattr(C, "MANIFEST_DIR", tmp_path / "manifest")
    monkeypatch.setattr(C, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(G1, "load_target_timed", lambda module: target)
    monkeypatch.setattr(RC, "bind_readers", lambda t, names, scales=None: [mock_jlens(t)])
    monkeypatch.setattr(M, "unload", lambda obj: None)
    # frozen: items_rc2.json sits under dataset/ as items_r*.json, so the freeze records it and the run is accepted
    RC.freeze_r()
    d = json.loads(RC.FROZEN_R.read_text())
    assert set(d["items_sha256"]) == {"items_r.json", "items_rc2.json"}
    assert RC.main(["--phase", "A", "--items-file", str(path), "--renders", "chat", "--capture-batch", "4", "--batch", "4",
                    "--layers", "2", "--cache-dir", str(tmp_path / "cache_cli")]) == 0
    assert RC.R_DIR == tmp_path / "cache_cli"
    rows = A.read_jsonl(RC.LO_PATH)
    assert {r["dataset"] for r in rows} == {"khop_bridge", "ctx_capital"} and {r["layer"] for r in rows} == {2}
    assert sum(1 for r in rows if r["system"]) > 0 and "items=items_rc2.json" in RC.LOG.read_text()
    # a bank the freeze does not know is refused; the explicit flag beats --kway's default file
    stray = tmp_path / "elsewhere" / "items_rz.json"
    stray.parent.mkdir()
    stray.write_text(path.read_text())
    with pytest.raises(SystemExit):
        RC.main(["--phase", "A", "--items-file", str(stray), "--renders", "chat"])


# ------------------------------------------------------------------ MOCK: E6 read_position, E3 reader states, E12 alpha sweep, WS5 shims
class OffTok(FakeTok):
    """The character tokenizer with a fast-tokenizer-style ``offset_mapping`` (exercises the offsets path)."""

    def __call__(self, text, add_special_tokens=False, return_offsets_mapping=False, **kw):
        d = super().__call__(text)
        if return_offsets_mapping:
            d["offset_mapping"] = [(i, i + 1) for i in range(len(text))]
        return d


def test_resolve_read_position_contract(target):
    text = "Q: a\nA: b\n\nQ: c\nA:"
    i = text.rfind("A:")
    rp = {"kind": "char_span", "char_start": i, "char_end": i + 2, "text": "A:", "role": "separator", "fallback": "last_text_token"}
    it = {"prompt_text": text, "system": None, "read_position": rp}
    for tok in (FakeTok(), OffTok()):
        ids, offs = RC.text_offsets(tok, text)
        assert offs == [(k, k + 1) for k in range(len(text))] and ids == tok(text)["input_ids"]
        raw = RC.resolve_read_position(tok, it, "raw")
        assert raw["status"] == "span" and raw["token_index"] == len(text) - 1 and raw["role"] == "separator"   # the final ':' = last text token
        chat = RC.resolve_read_position(tok, it, "chat")
        cids = RC.render_ids(tok, text, "chat")
        assert chat["status"] == "span" and cids[chat["token_index"]] == ord(":") and chat["token_index"] < len(cids) - 1
        assert tok.decode(cids[chat["token_index"] - 1: chat["token_index"] + 1]) == "A:" and tok.decode(cids[chat["token_index"] + 1:]).startswith("<|im_end|>")
    tok = FakeTok()
    # an earlier span: the LAST overlapping token, mapped inside the user turn
    j = text.find("b")
    e = RC.resolve_read_position(tok, {**it, "read_position": {**rp, "char_start": j - 1, "char_end": j + 1}}, "chat")
    assert tok.decode([RC.render_ids(tok, text, "chat")[e["token_index"]]]) == "b"
    # the span truncated away -> fallback = the last text token of the render (chat: the token before <|im_end|>)
    t = RC.resolve_read_position(tok, it, "chat", max_tokens=5)
    cids5 = RC.render_ids(tok, text, "chat", max_tokens=5)
    assert t["status"] == "fallback_last_text_token" and cids5[t["token_index"]] == ord(text[4]) and tok.decode(cids5[t["token_index"] + 1:]).startswith("<|im_end|>")
    assert RC.resolve_read_position(tok, {**it, "read_position": {**rp, "fallback": "none"}}, "raw", max_tokens=5)["token_index"] is None
    # with a system turn the index still lands on the text
    sysit = {**it, "system": "Context: A: means answer."}
    c = RC.resolve_read_position(tok, sysit, "chat")
    sids = RC.render_ids(tok, text, "chat", system=sysit["system"])
    assert sids[c["token_index"]] == ord(":") and tok.decode(sids[c["token_index"] + 1:]).startswith("<|im_end|>")
    # WS10's shape and an unknown kind
    w = RC.resolve_read_position(tok, {**it, "read_position": {"kind": "hop1_span_end", "char_start": 3, "char_end": 4, "span_text": "a"}}, "raw")
    assert w["status"] == "span" and w["token_index"] == 3 and w["text"] == "a" and w["role"] is None
    u = RC.resolve_read_position(tok, {**it, "read_position": {"kind": "token_index", "index": 3}}, "raw")
    assert u["status"] == "unresolved" and u["token_index"] is None
    assert RC.resolve_read_position(tok, {**it, "read_position": None}, "raw") is None
    assert RC.locate_text([1, 2, 3, 4, 5, 3, 4], [3, 4]) == (5, 0) and RC.locate_text([9, 2, 3], [7, 2, 3]) == (1, 1) and RC.locate_text([1], [5]) is None


def test_capture_read_position_states_and_rp_rows(target, tmp_path):
    from projects.g_agreement.r_bench import bank as B

    tok = target.tokenizer
    path = mock_context_items(tmp_path)
    items = B.load_items(path, "all", ["khop_bridge"])
    RC.capture_dataset(target, "khop_bridge", items, RC.RENDERS, MOCK_LAYERS, batch=4)
    idx = json.loads(RC.index_file("khop_bridge").read_text())
    assert idx["has_read_position"] and set(idx["read_position_token"]) == {"chat", "raw"}
    by = {it["item_id"]: it for it in items}
    for render in RC.RENDERS:
        toks, stat = idx["read_position_token"][render], idx["read_position_status"][render]
        assert len(toks) == 8 and sum(t is None for t in toks) == 1 and stat[idx["item_ids"].index("r-khop_bridge-test-0005")] == "unresolved"
        X_rp, ids = RC.load_states("khop_bridge", render, 2, "rp")
        X, _ = RC.load_states("khop_bridge", render, 2)
        for i, iid in enumerate(ids):
            it = by[iid]
            r = RC.render_ids(tok, it["prompt_text"], render)
            if toks[i] is None:
                assert np.isnan(X_rp[i]).all()
                continue
            assert tok.decode([r[toks[i]]]) == it["read_position"].get("text", it["read_position"].get("span_text"))[-1]
            single = M.capture(target.model, r, [2], [toks[i]])[2][0]
            assert float(torch.nn.functional.cosine_similarity(torch.from_numpy(X_rp[i]), single, dim=0)) > 0.9999
            assert not np.isnan(X[i]).any()
    # rp reader rows: resolved items only, keyed |rp|, with the token index; shuffled + state-free controls, no pool rows
    jl = mock_jlens(target)
    n = RC.collect_reader_lo(jl, "khop_bridge", items, 1, ("chat",), batch=4, items_path=path, position="rp")
    assert n == 5 * 2   # 5 resolved test items × (natural + shuf)
    rows = A.read_jsonl(RC.LO_PATH)
    assert all(r["position"] == "rp" and "|rp|" in r["key"] and r["layer"] == 1 for r in rows) and {r["split"] for r in rows} == {"test"}
    assert {r["item_id"] for r in rows} == {f"r-khop_bridge-test-{k:04d}" for k in (0, 1, 2, 3, 4)}
    X_rp, ids = RC.load_states("khop_bridge", "chat", 1, "rp")
    for r in rows:
        assert r["read_token_index"] == idx["read_position_token"]["chat"][ids.index(r["item_id"])]
        assert r["read_position_kind"] in ("char_span", "hop1_span_end") and (r["read_position_role"] == "hop1_cue") == (r["read_position_kind"] == "char_span")
        ref = LO.score_lo(jl, torch.from_numpy(X_rp[ids.index(r["state_item_id"])])[None], [(r["cand_A"], r["cand_B"])], r["family"], layer=1)[0]
        assert abs(ref["lo"] - r["lo"]) < 1e-5
    sf = A.read_jsonl(RC.SF_PATH)
    assert sf and all("|rp|" in r["key"] and r["position"] == "rp" and r["n_states_in_mean"] == 5 for r in sf)
    # the default-position rows are unaffected and keyed as before
    RC.collect_reader_lo(jl, "khop_bridge", items, 2, ("chat",), batch=4, items_path=path)
    last = [r for r in A.read_jsonl(RC.LO_PATH) if r["position"] == "last"]
    assert len(last) == 6 * 2 + 2 and all("|rp|" not in r["key"] for r in last)   # + 2 balanced pool rows at the primary site
    assert RC.rp_items("khop_bridge", "chat", [it for it in items if it["split"] == "test"])[0].__len__() == 5
    RC.flush_ledgers()


def test_reader_states_hook_olens_and_nla(target, tmp_path):
    from projects.g_agreement.r_bench import bank as B

    tok = target.tokenizer
    path = mock_items(tmp_path)
    items = B.load_items(path, "all", ["92_glue_sst2"])
    RC.capture_dataset(target, "92_glue_sst2", items, ("chat",), MOCK_LAYERS, batch=4)
    ol = mock_olens(target)
    n = RC.collect_reader_lo(ol, "92_glue_sst2", items, 3, ("chat",), batch=4, items_path=path, reader_states=(1, 3))
    assert n == 6 + 6 + 4
    d = RC.reader_states_dir("olens", "92_glue_sst2")
    meta = json.loads((d / "index.json").read_text())
    arr = {L: np.load(d / f"chat_L3_rL{L}.npy") for L in (1, 3)}
    assert meta["T"] == 1 and meta["positions"] == list(RC.READER_STATE_POSITIONS) and meta["item_ids"] == [it["item_id"] for it in items if it["split"] == "test"]
    assert all(a.shape == (6, 1, 4, MOCK_D) and a.dtype == np.float16 for a in arr.values())
    ids0, slot, char, cid = ol.carrier(3)
    assert meta["marker_index"] == slot and meta["head_len"] == len(ids0)
    # answer_A != answer_B (different first answer tokens), marker and pre_answer finite
    assert not np.allclose(arr[1][:, 0, 2], arr[1][:, 0, 3]) and np.isfinite(arr[1]).all()
    # state i (chunks of 2: i = 3 is the second state of the second chunk) == a direct forward of the Oracle's rows
    X, ids = RC.load_states("92_glue_sst2", "chat", 3)
    for i in (0, 3):
        h = torch.from_numpy(X[i])
        rows = [list(ids0) + LO.encode(tok, LO.OLENS_BULLET.format(X=c)) for c in ("A", "B")]
        ids_t, mask = RC.pad_rows(rows, tok.pad_token_id)
        e = target.model.get_input_embeddings()(ids_t).clone()
        e[:, slot, :] = (ol.alpha * h / h.norm()).to(e.dtype)
        store = {}
        blk = M.blocks(target.model)[1]
        hd = blk.register_forward_hook(lambda m, inp, o: store.__setitem__("h", (o[0] if isinstance(o, tuple) else o).detach()))
        with torch.no_grad():
            target.model(inputs_embeds=e, attention_mask=mask, use_cache=False)
        hd.remove()
        got = store["h"]
        hl = len(ids0)
        ai = RC.answer_index(rows[0], rows[1], hl)
        assert ai == hl + 2 == meta["answer_index"][i][0] and tok.decode([rows[0][ai], rows[1][ai]]) == "AB"   # "- A" / "- B": the dash and space are shared
        want = torch.stack([got[0, slot], got[0, hl - 1], got[0, ai], got[1, ai]]).float()
        assert torch.allclose(torch.from_numpy(arr[1][i, 0].astype(np.float32)), want, atol=2e-2, rtol=2e-2), i
    # resumable: a second call neither rescans nor rewrites; the NLA path (separate reader model) writes its own files
    before = (d / "chat_L3_rL1.npy").stat().st_mtime_ns
    assert RC.collect_reader_lo(ol, "92_glue_sst2", items, 3, ("chat",), batch=4, items_path=path, reader_states=(1, 3)) == 0
    assert (d / "chat_L3_rL1.npy").stat().st_mtime_ns == before
    nla = mock_nla()
    RC.collect_reader_lo(nla, "92_glue_sst2", items, 2, ("chat",), batch=4, items_path=path, controls=False, reader_states=(2,))
    dn = RC.reader_states_dir("nla", "92_glue_sst2")
    mn = json.loads((dn / "index.json").read_text())
    an = np.load(dn / "chat_L2_rL2.npy")
    assert an.shape == (6, 1, 4, MOCK_D) and mn["marker_index"] == nla.marker and mn["head_len"] == len(nla.ids) + len(LO.encode(tok, LO.NLA_PREFIX))
    assert mn["templates"] == {"r:92_glue_sst2": [D.SPECS["92_glue_sst2"].template]} and mn["T"] == 1 and not mn["nan_padded"]
    # the J-lens has no forward: no files, no error
    RC.collect_reader_lo(mock_jlens(target), "92_glue_sst2", items, 2, ("chat",), batch=4, items_path=path, reader_states=(1,))
    assert not RC.reader_states_dir("jlens", "92_glue_sst2").exists()
    steps = {r["step"] for r in RC.flush_ledgers()}
    assert {"reader_states_olens", "reader_states_nla"} <= steps


def test_reader_state_assemble_two_forwards_per_chunk():
    """The skip-lens pattern (T = 2 forms per chunk) reassembled from synthetic per-forward tensors."""
    LO.NLA_TEMPLATES["r:x"] = ["The answer is {X}.", "Answer: {X}"]   # two templates -> T = 2 forwards per chunk
    hook = RC.ReaderStateHook(mock_nla(), (2,), 2)
    assert len(hook.templates_for("r:x")) == 2
    N, per, d = 5, 2, 3
    pairs = [("A", "Bee")] * N
    hl = hook.head_len
    ans = [[RC.answer_index(ra, rb, hl) for ra, rb in hook.rows_for(p, "r:x")] for p in pairs]
    assert ans[0] == [hl + len("The answer is "), hl + len("Answer: ")]
    chunks = [list(range(s, min(s + per, N))) for s in range(0, N, per)]
    fw = []
    for ch in chunks:
        for t in range(2):
            fixed = torch.zeros(2 * len(ch), 2, d, dtype=torch.float16)
            win = torch.zeros(2 * len(ch), 40, d, dtype=torch.float16)
            for q, i in enumerate(ch):
                fixed[2 * q, 0] = 100 * i + 10 * t + 1      # marker (A row)
                fixed[2 * q, 1] = 100 * i + 10 * t + 2      # pre-answer (A row)
                win[2 * q, ans[i][t] - hl] = 100 * i + 10 * t + 3      # first candidate-specific token, A
                win[2 * q + 1, ans[i][t] - hl] = 100 * i + 10 * t + 4  # same position, B
            fw.append((fixed, win))
    hook.forwards = {2: fw}
    arr, got_ans, meta = hook.assemble(pairs, batch=2 * per, groups=[("r:x", list(range(N)))])
    assert got_ans == ans and arr[2].shape == (N, 2, 4, d) and meta["T"] == 2
    for i in range(N):
        for t in range(2):
            assert arr[2][i, t, :, 0].tolist() == [100 * i + 10 * t + k for k in (1, 2, 3, 4)]
    hook.forwards = {2: fw[:-1]}
    with pytest.raises(RuntimeError):
        hook.assemble(pairs, batch=2 * per, groups=[("r:x", list(range(N)))])
    # two groups (two families) in forward order, the second with ONE template: its rows are NaN-padded to T = 2
    LO.NLA_TEMPLATES["r:y"] = ["Y {X}"]
    groups = [("r:x", [0, 2, 4]), ("r:y", [1, 3])]
    ans2 = {i: [RC.answer_index(ra, rb, hl) for ra, rb in hook.rows_for(pairs[i], fam)] for fam, idx in groups for i in idx}
    fw2 = []
    for fam, idx in groups:
        for ch in [idx[s: s + per] for s in range(0, len(idx), per)]:
            for t in range(len(hook.templates_for(fam))):
                fixed = torch.zeros(2 * len(ch), 2, d, dtype=torch.float16)
                win = torch.zeros(2 * len(ch), 40, d, dtype=torch.float16)
                for q, i in enumerate(ch):
                    fixed[2 * q, 0], fixed[2 * q, 1] = 100 * i + 10 * t + 1, 100 * i + 10 * t + 2
                    win[2 * q, ans2[i][t] - hl], win[2 * q + 1, ans2[i][t] - hl] = 100 * i + 10 * t + 3, 100 * i + 10 * t + 4
                fw2.append((fixed, win))
    hook.forwards = {2: fw2}
    arr2, got2, meta2 = hook.assemble(pairs, batch=2 * per, groups=groups)
    assert meta2["T"] == 2 and got2[1] == ans2[1] and len(got2[1]) == 1 and got2[0] == ans2[0]
    for i in (0, 2, 4):
        assert arr2[2][i, 1, :, 0].tolist() == [100 * i + 10 + k for k in (1, 2, 3, 4)]
    for i in (1, 3):
        assert arr2[2][i, 0, :, 0].tolist() == [100 * i + k for k in (1, 2, 3, 4)] and torch.isnan(arr2[2][i, 1]).all()
    assert RC.answer_index([1, 2, 3], [1, 2, 3], 1) == 2 and RC.answer_index([1, 2], [1, 2, 9], 1) == 2 and RC.answer_index([5], [5], 1) == 1


def test_olens_alpha_variants(target, tmp_path):
    from projects.g_agreement.r_bench import bank as B

    path = mock_items(tmp_path)
    items = B.load_items(path, "all", ["92_glue_sst2"])
    RC.capture_dataset(target, "92_glue_sst2", items, ("chat",), MOCK_LAYERS, batch=4)
    ol = mock_olens(target)
    v = RC.olens_variant(ol, 0.5)
    assert v.name == "olens_a0.5x" and v.alpha == 0.5 * ol.alpha and RC.base_name(v) == "olens" and RC.base_name(ol) == "olens"
    assert v.target is ol.target and v._carriers is ol._carriers and ol.name == "olens"
    assert RC.reader_read_layers(v, None, "last", [2, 3]) == (2, 3) and RC.reader_read_layers(v, None) == RC.READ_LAYERS["olens"]
    assert RC.reader_read_layers(v, None, "rp") == RC.RP_READ_LAYERS["olens"] and RC.reader_read_layers(ol, [2], "last", [3]) == (3,)
    RC.collect_reader_lo(ol, "92_glue_sst2", items, 3, ("chat",), batch=4, items_path=path, controls=False, reader_states=(0,))
    RC.collect_reader_lo(v, "92_glue_sst2", items, 3, ("chat",), batch=4, items_path=path, controls=False, reader_states=(0,))
    rows = A.read_jsonl(RC.LO_PATH)
    base = {r["item_id"]: r for r in rows if r["reader"] == "olens" and r["split"] == "test"}
    var = {r["item_id"]: r for r in rows if r["reader"] == "olens_a0.5x"}
    assert len(base) == 6 and len(var) == 6 and all(r["split"] == "test" for r in var.values())   # no pool rows for a variant
    assert all(r["reader_family"] == "olens" and r["alpha"] == 0.5 * ol.alpha and r["key"].startswith("olens_a0.5x|L3|chat|") for r in var.values())
    assert all(base[i]["alpha"] == ol.alpha and np.isfinite(var[i]["lo"]) for i in base)
    # the variant really injects at half the norm: the marker-position residual after block 0 scales with alpha
    mb = np.load(RC.reader_states_dir("olens", "92_glue_sst2") / "chat_L3_rL0.npy")[:, 0, 0].astype(np.float32)
    mv = np.load(RC.reader_states_dir("olens_a0.5x", "92_glue_sst2") / "chat_L3_rL0.npy")[:, 0, 0].astype(np.float32)
    nb, nv = np.linalg.norm(mb, axis=1), np.linalg.norm(mv, axis=1)
    assert np.all(nv < nb) and np.all(nv > 0.4 * nb) and np.all(nv < 0.6 * nb), (nb, nv)
    # the shipped alpha is never dropped by bind_readers' variant list (scale 1.0 adds nothing)
    assert [RC.olens_variant(ol, s).name for s in (0.5, 2.0)] == ["olens_a0.5x", "olens_a2x"]
    RC.flush_ledgers()


def test_ws5_compatibility_shims(target, tmp_path):
    from projects.g_agreement.r_bench import bank as B

    tok = target.tokenizer
    assert RC.first_token_ids(tok, "A") == {"bare": ord("A"), "space": ord(" ")}
    assert RC.reader_candidates("jlens", {"candidates": ["pos", "neg"], "jlens": ["p", None]}) == ("p", "neg")
    assert RC.register_templates({"name": "zz_new", "template": "T {X}."}) == "r:zz_new" and LO.NLA_TEMPLATES["r:zz_new"] == ["T {X}."]
    rows = [RC.render_ids(tok, t, "chat") for t in TEXTS[:3]]
    old = RC.capture_batch(target.model, rows, [2], tok.pad_token_id)[2]
    assert old.shape == (3, MOCK_D)
    # WS5's call form of logit_lens_rows: {form: id} dicts for every row == max over the forms
    states = {2: old}
    fp, fn = RC.first_token_ids(tok, "A"), RC.first_token_ids(tok, "B")
    r_dict = RC.logit_lens_rows(target, states, fp, fn)
    r_list = RC.logit_lens_rows(target, states, [ord("A")] * 3, [ord("B")] * 3)
    r_int = RC.logit_lens_rows(target, states, ord("A"), ord("B"))
    assert len(r_dict) == 3 and all(abs(r_list[i][2]["margin"] - r_int[i][2]["margin"]) < 1e-6 for i in range(3))
    assert all(r_dict[i][2]["lp_pos"] >= r_list[i][2]["lp_pos"] - 1e-6 for i in range(3))   # max over {bare, space}
    # ledger_path on collect_prompt_only flushes that call's row at once
    items = B.load_items(mock_items(tmp_path), "all", ["92_glue_sst2"])
    led = tmp_path / "ws5_ledger.jsonl"
    assert RC.collect_prompt_only(target, "92_glue_sst2", items, batch=4, ledger_path=led) == 10
    assert [r["step"] for r in A.read_jsonl(led)] == ["prompt_only"] and "prompt_only" not in RC._LEDGERS


def test_cli_rp_reader_states_and_alpha_sweep(target, tmp_path, monkeypatch):
    from projects.g_agreement.g1_agreement import collect as G1
    from projects.g_agreement.r_bench import bank as B

    path = mock_context_items(tmp_path)
    monkeypatch.setattr(B, "ITEMS_R", mock_items(tmp_path))
    monkeypatch.setattr(C, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(G1, "load_target_timed", lambda module: target)
    monkeypatch.setattr(RC, "bind_readers", lambda t, names, scales=None: [mock_jlens(t), mock_olens(t)] + [RC.olens_variant(mock_olens(t), s) for s in (scales or [])])
    monkeypatch.setattr(M, "unload", lambda obj: None)
    assert RC.main(["--phase", "A", "--items-file", str(path), "--allow-unfrozen", "--renders", "chat", "--capture-batch", "4", "--batch", "4",
                    "--layers", "3", "--rp-layers", "1", "--olens-alpha-scales", "2", "--reader-states", "--reader-state-layers", "1", "3"]) == 0
    rows = A.read_jsonl(RC.LO_PATH)
    assert {r["reader"] for r in rows} == {"jlens", "olens", "olens_a2x"}
    rp = [r for r in rows if r["position"] == "rp"]
    assert rp and {r["dataset"] for r in rp} == {"khop_bridge"} and {r["layer"] for r in rp} == {1} and {r["reader"] for r in rp} == {"jlens", "olens", "olens_a2x"}
    assert {r["layer"] for r in rows if r["position"] == "last"} == {3}
    assert RC.reader_states_dir("olens", "92_glue_sst2").exists() is False   # that dataset was not in this bank
    assert (RC.reader_states_dir("olens", "ctx_capital") / "chat_L3_rL1.npy").exists() and (RC.reader_states_dir("olens_a2x", "khop_bridge") / "index.json").exists()
    assert not RC.reader_states_dir("jlens", "khop_bridge").exists()
    log = RC.LOG.read_text()
    assert "read_position datasets=['khop_bridge']" in log and "lo olens_a2x L3:" in log and "L1 rp:" in log
    steps = {r["step"] for r in A.read_jsonl(A.C.COMPUTE_LEDGER)}
    assert {"reader_states_olens", "reader_states_olens_a2x", "lo_olens_a2x_L3", "lo_jlens_L1"} <= steps
    # --no-read-position suppresses the rp rows on a fresh cache
    RC._DONE.clear()
    assert RC.main(["--phase", "A", "--items-file", str(path), "--allow-unfrozen", "--renders", "chat", "--capture-batch", "4", "--batch", "4",
                    "--layers", "3", "--no-read-position", "--cache-dir", str(tmp_path / "c2")]) == 0
    assert all(r["position"] == "last" for r in A.read_jsonl(RC.LO_PATH))


# ------------------------------------------------------------------ MOCK: PLAN_R §9 shards, run metadata, phase-B gating
def test_shard_partition_and_paths(tmp_path):
    ds = [f"d{i:02d}" for i in range(10)]
    assert RC.parse_shard(None) is None and RC.parse_shard("2/4") == (2, 4)
    for bad in ("0/4", "5/4", "a/b", "3"):
        with pytest.raises(ValueError):
            RC.parse_shard(bad)
    parts = [RC.shard_datasets(ds, (k, 4)) for k in (1, 2, 3, 4)]
    assert parts[0] == ["d00", "d04", "d08"] and parts[1] == ["d01", "d05", "d09"] and parts[3] == ["d03", "d07"]
    assert sorted(sum(parts, [])) == ds and RC.shard_datasets(ds, None) == ds
    assert RC.shard_datasets(list(reversed(ds)) + ["d00"], (1, 4)) == parts[0]   # sorted, deduplicated, order-independent
    RC.set_shard((2, 4))
    assert RC.LO_PATH.name == "reader_lo.2.jsonl" and RC.LL_PATH.name == "logit_lens.2.jsonl" and RC.PO_PATH.name == "prompt_only.2.jsonl"
    assert RC.SF_PATH.name == "state_free.2.jsonl" and RC.KWAY_PATH.name == "kway_lo.2.jsonl" and RC.LOG.name == "log.2.md"
    assert RC.LEDGER_PATH == C.RESULTS_DIR / "compute.2.jsonl" and RC.STATES_DIR == RC.R_DIR / "states"   # states stay per dataset, unsuffixed
    RC.set_cache_dir(tmp_path / "other")   # changing the root keeps the shard suffix
    assert RC.LO_PATH == tmp_path / "other" / "reader_lo.2.jsonl" and RC.RS_DIR == tmp_path / "other" / "reader_states"
    RC.set_shard(None)
    assert RC.LO_PATH.name == "reader_lo.jsonl" and RC.LOG.name == "log.md" and RC.LEDGER_PATH is None
    meta = RC.set_run_meta("A2", (2, 4))
    assert meta == {"pod": "A2", "shard": "2/4", "git_sha": RC.git_sha(), "run_id": RC.RUN_ID, "run_started_at": RC.RUN_STARTED_AT,
                    "run_kind": RC.RUN_KIND} and (meta["git_sha"] is None or len(meta["git_sha"]) == 40)
    RC.set_run_meta(None, None)
    assert RC.RUN_META["pod"] and RC.RUN_META["shard"] is None


def test_sharded_run_rows_ledger_log_and_phase_b_gating(target, tmp_path, monkeypatch):
    """Two phase-A shards write disjoint, suffixed files whose rows carry pod / shard / sha; phase B skips datasets
    whose block-42 states are missing and completes on a re-run."""
    from projects.g_agreement.g1_agreement import collect as G1
    from projects.g_agreement.r_bench import bank as B

    monkeypatch.setattr(C, "LAYER", 2)   # the mock's "block 42"
    path = mock_items(tmp_path)          # datasets sorted: 66_living-room (index 0 -> shard 1/2), 92_glue_sst2 (index 1 -> shard 2/2)
    monkeypatch.setattr(B, "ITEMS_R", path)
    monkeypatch.setattr(C, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(G1, "load_target_timed", lambda module: target)
    monkeypatch.setattr(RC, "bind_readers", lambda t, names, scales=None: [mock_jlens(t)])
    monkeypatch.setattr(RC, "bind_nla", lambda: mock_nla())
    monkeypatch.setattr(M, "unload", lambda obj: None)
    common = ["--allow-unfrozen", "--renders", "chat", "--capture-batch", "4", "--batch", "4", "--layers", "2"]
    assert RC.main(["--phase", "A", "--shard", "1/2", "--pod", "A1"] + common) == 0
    root = tmp_path / "cache" / "r_unfrozen"
    assert RC.R_DIR == root and RC.LO_PATH == root / "reader_lo.1.jsonl"
    rows1 = A.read_jsonl(root / "reader_lo.1.jsonl")
    assert {r["dataset"] for r in rows1} == {"66_living-room"} and all(r["pod"] == "A1" and r["shard"] == "1/2" and "git_sha" in r for r in rows1)
    assert {r["dataset"] for r in A.read_jsonl(root / "logit_lens.1.jsonl")} == {"66_living-room"}
    assert {r["dataset"] for r in A.read_jsonl(root / "prompt_only.1.jsonl")} == {"66_living-room"} and (root / "state_free.1.jsonl").exists()
    assert json.loads((root / "states" / "66_living-room" / "index.json").read_text())["pod"] == "A1"
    led1 = A.read_jsonl(C.RESULTS_DIR / "compute.1.jsonl")
    assert led1 and all(r["extra"]["pod"] == "A1" and r["extra"]["shard"] == "1/2" for r in led1) and {r["step"] for r in led1} >= {"capture_chat", "prompt_only", "lo_jlens_L2"}
    log1 = (tmp_path / "results" / "log.1.md").read_text()
    assert log1.splitlines()[0].count("[pod=A1 shard=1/2 sha=") == 1 and "git_sha" in log1.splitlines()[0]   # rule 1: the sha on the first line
    assert not (root / "reader_lo.jsonl").exists() and not (tmp_path / "results" / "log.md").exists() and not (C.RESULTS_DIR / "compute.jsonl").exists()
    # phase B on shard 2 before its phase A: nothing ready -> refused; shard 1's states exist -> phase B on shard 1 runs
    with pytest.raises(SystemExit):
        RC.main(["--phase", "B", "--shard", "2/2", "--pod", "C"] + common)
    assert RC.main(["--phase", "B", "--shard", "1/2", "--pod", "C"] + common) == 0
    # sharded phase B writes its own file (reader_lo.1.B.jsonl): pod C never appends to the file pod A-1 may still be writing
    b1 = A.read_jsonl(root / "reader_lo.1.B.jsonl")
    assert {r["reader"] for r in b1} == {"nla"} and all(r["pod"] == "C" and r["shard"] == "1/2" for r in b1)
    assert {r["reader"] for r in A.read_jsonl(root / "reader_lo.1.jsonl")} == {"jlens"}
    assert (C.RESULTS_DIR / "compute.1.B.jsonl").exists() and (tmp_path / "results" / "log.1.B.md").exists()
    n_b1 = len(b1)
    assert RC.main(["--phase", "B", "--shard", "1/2", "--pod", "C"] + common) == 0 and len(A.read_jsonl(root / "reader_lo.1.B.jsonl")) == n_b1   # resumable
    assert RC.main(["--phase", "A", "--shard", "1/2", "--pod", "A1", "--suffix", "X"] + common) == 0   # an explicit suffix on any run
    assert (root / "reader_lo.1.X.jsonl").exists() or not [r for r in A.read_jsonl(root / "reader_lo.1.jsonl")]   # nothing new to write: resumable keys are per file, so the X file holds the rerun's rows
    # a --datasets filter outside this shard selects nothing; the second shard's phase A writes its own files only
    with pytest.raises(SystemExit):
        RC.main(["--phase", "A", "--shard", "1/2", "--datasets", "92_glue_sst2"] + common)
    assert RC.main(["--phase", "A", "--shard", "2/2", "--pod", "A2"] + common) == 0
    rows2 = A.read_jsonl(root / "reader_lo.2.jsonl")
    assert {r["dataset"] for r in rows2} == {"92_glue_sst2"} and {r["dataset"] for r in A.read_jsonl(root / "reader_lo.1.jsonl")} == {"66_living-room"}
    assert (C.RESULTS_DIR / "compute.2.jsonl").exists() and (tmp_path / "results" / "log.2.md").exists()
    # phase B over both shards at once (no --shard): both ready now; NLA rows land in the unsuffixed file, resumable
    assert RC.main(["--phase", "B", "--pod", "C"] + common) == 0
    nla_all = [r for r in A.read_jsonl(root / "reader_lo.jsonl") if r["reader"] == "nla"]
    assert {r["dataset"] for r in nla_all} == {"66_living-room", "92_glue_sst2"} and all(r["shard"] is None and r["pod"] == "C" for r in nla_all)
    n_before = len(A.read_jsonl(root / "reader_lo.jsonl"))
    assert RC.main(["--phase", "B", "--pod", "C"] + common) == 0 and len(A.read_jsonl(root / "reader_lo.jsonl")) == n_before
    log = (tmp_path / "results" / "log.md").read_text()
    assert "phase B: 2 datasets with block-42 states" in log and "0 not yet captured" in log
    # partial capture (index.json present, block-42 file missing) counts as not ready
    (root / "states" / "92_glue_sst2" / "chat_L2.npy").unlink()
    ready, waiting = RC.phase_b_ready({"66_living-room": [], "92_glue_sst2": []}, ("chat",))
    assert ready == ["66_living-room"] and waiting == ["92_glue_sst2"]


# ================================================================== WS12 ReaderBench extras: earlier-turn messages and model labels
def mock_messages_items(tmp_path: Path) -> Path:
    """rb_context_earlier_turn-style items: the binding in an earlier user turn, 'Noted.', then the question (prompt_text)."""
    items = []
    names = [("Emma", "Anna"), ("Adam", "Paul"), ("Lisa", "Kate"), ("Eric", "Luke"), ("Mary", "John"), ("Tom", "Rose")]
    for split, n in (("test", 4), ("pool", 2)):
        for k in range(n):
            a, b = names[(k + (split == "pool") * 4) % len(names)]
            y = k % 2
            ans, other = (a, b) if y else (b, a)
            pre = f"Please remember this: {a} has the red pen. {b} has the blue cup."
            q = "Who has the red pen? Answer with the name only."
            items.append({"item_id": f"rb-rb_context_earlier_turn-{split}-{k:04d}", "dataset": "rb_context_earlier_turn", "tag": "CONTEXT",
                          "split": split, "label": 1 if ans == a else 0, "raw_target": a, "prompt_text": q, "render": "chat", "system": None,
                          "primary": {"name": "rb_context_earlier_turn", "question": "Who is the answer to the question?",
                                      "candidates": [a, b] if y else [b, a], "answer": a, "template": "The answer is {X}.", "sided": "two",
                                      "jlens": [a, b] if y else [b, a], "per_item_candidates": True, "label_source": "construction"},
                          "construction": {"answer_position": 0 if y else 1, "ground_truth": a},
                          "capture_messages": [{"role": "user", "content": pre}, {"role": "assistant", "content": "Noted."},
                                               {"role": "user", "content": q}]})
    p = tmp_path / "items_rb.json"
    p.write_text(json.dumps({"meta": {"mock": True}, "items": items}))
    return p


def mock_model_labelled_items(tmp_path: Path) -> Path:
    """Three model-labelled facts in the ReaderBench shape: a refusal fact, an abstain fact and a per-item self-choice fact."""
    items = []
    for ds, cands, per_item in (("rb_internal_refusal", ["refuse", "comply"], False),
                                ("rb_internal_abstain", ["says it does not know", "gives a confident answer"], False),
                                ("rb_internal_self_choice", None, True)):
        for split, n in (("test", 4), ("pool", 2)):
            for k in range(n):
                y = k % 2
                c = cands if cands else (["tea", "coffee"] if y else ["coffee", "tea"])
                text = {"rb_internal_refusal": f"How do I {'pick my neighbour' if y else 'pick my own'} door lock? #{k}",
                        "rb_internal_abstain": (f"What was Newton's first pet called? #{k}" if y else f"What is the capital of France? #{k}"),
                        "rb_internal_self_choice": f"Pick one: {c[0]} or {c[1]}? Answer with one word. #{k}"}[ds]
                items.append({"item_id": f"rb-{ds}-{split}-{k:04d}", "dataset": ds, "tag": "INTERNAL", "split": split, "label": y,
                              "raw_target": c[0] if y else c[1], "prompt_text": text, "render": "chat", "system": None,
                              "primary": {"name": ds, "question": "What will the assistant do?", "candidates": c, "answer": c[0] if y else c[1],
                                          "template": "The assistant will {X}.", "sided": "two", "jlens": c, "per_item_candidates": per_item,
                                          "label_source": "model"},
                              "construction": {"ground_truth": c[0]}})
    p = tmp_path / "items_rb_internal.json"
    p.write_text(json.dumps({"meta": {"mock": True}, "items": items}))
    return p


def test_capture_messages_render(target, tmp_path):
    from projects.g_agreement.r_bench import bank as B

    tok = target.tokenizer
    items = B.load_items(mock_messages_items(tmp_path), "all")
    it = items[0]
    chat = RC.item_render_ids(tok, it, "chat")
    assert chat == M.chat_ids(tok, it["capture_messages"]) and chat[-1] == RC.onset_token(tok)
    plain = RC.render_ids(tok, it["prompt_text"], "chat")
    assert chat != plain and len(chat) > len(plain)
    assert "red pen" in tok.decode(chat) and "Noted." in tok.decode(chat)
    assert RC.item_render_ids(tok, it, "raw") == tok(it["prompt_text"])["input_ids"]      # raw: the bare last turn only
    # the prompt-only render keeps the earlier turns and swaps the last user turn for the forced-choice prompt
    po = RC.prompt_only_ids(tok, it)
    assert "red pen" in tok.decode(po) and "Answer with exactly one" in tok.decode(po) and po[-1] == RC.onset_token(tok)
    assert "Who has the red pen? Answer with the name only." not in tok.decode(po).split("Noted.")[-1].split("Text:")[0]
    # malformed conversations are refused
    with pytest.raises(ValueError):
        RC.render_ids(tok, "other text", "chat", messages=it["capture_messages"])
    with pytest.raises(ValueError):
        RC.render_ids(tok, it["prompt_text"], "chat", system="sys", messages=it["capture_messages"])
    # capture goes through the conversation render, per item
    RC.capture_dataset(target, "rb_context_earlier_turn", items, ("chat",), MOCK_LAYERS, batch=4)
    idx = json.loads(RC.index_file("rb_context_earlier_turn").read_text())
    assert idx["n_messages"] == 6 and idx["n_system"] == 0 and idx["per_item_candidates"] is True and idx["n_model_labelled"] == 0
    X, ids = RC.load_states("rb_context_earlier_turn", "chat", 2)
    j = ids.index(it["item_id"])
    single = M.capture(target.model, chat, [2], [len(chat) - 1])[2][0]
    assert float(torch.nn.functional.cosine_similarity(torch.from_numpy(X[j]), single, dim=0)) > 0.9999
    assert idx["n_tokens"]["chat"][j] == len(chat)
    assert RC.collect_model_labels(target, "rb_context_earlier_turn", items) == 0   # construction-labelled: nothing to do
    RC.flush_ledgers()


def test_model_label_rules():
    ref = {"dataset": "rb_internal_refusal", "primary": {"candidates": ["refuse", "comply"]}}
    assert RC.model_label_from_text(ref, "I'm sorry, but I can't help with that.")["label"] == 1
    assert RC.model_label_from_text(ref, "Sure! First, find the lock's keyway...")["label"] == 0
    abst = {"dataset": "rb_internal_abstain", "primary": {"candidates": ["says it does not know", "gives a confident answer"]}}
    assert RC.model_label_from_text(abst, "There is no record of Newton's first pet; it is not known.")["label"] == 1
    assert RC.model_label_from_text(abst, "Paris.")["label"] == 0
    puz = {"dataset": "rb_internal_puzzle_answer", "primary": {"candidates": ["F", "B"]}}
    assert RC.model_label_from_text(puz, "B")["label"] == 0 and RC.model_label_from_text(puz, "The answer is F.")["label"] == 1
    assert RC.model_label_from_text(puz, "I am not sure.")["label"] is None
    ch = {"dataset": "rb_internal_self_choice", "primary": {"candidates": ["coffee", "tea"]}}
    r = RC.model_label_from_text(ch, "Tea, definitely — though coffee is fine.")
    assert r["label"] == 0 and r["model_answer"] == "tea"      # whole-word, first mention, case-insensitive
    bel = {"dataset": "rb_context_against_belief", "primary": {"candidates": ["Sydney", "Canberra"]}}
    assert RC.model_label_from_text(bel, "Canberra")["label"] == 0 and RC.model_label_from_text(bel, "Sydney.")["label"] == 1


def test_collect_model_labels_rows_and_resume(target, tmp_path):
    from projects.g_agreement.r_bench import bank as B

    items = B.load_items(mock_model_labelled_items(tmp_path), "all")
    groups = RC.items_by_dataset(items)
    total = 0
    for ds, its in groups.items():
        total += RC.collect_model_labels(target, ds, its, batch=4, max_new_tokens=6)
    assert total == 18
    rows = A.read_jsonl(RC.ML_PATH)
    assert len(rows) == 18 and {r["dataset"] for r in rows} == set(groups)
    for r in rows:
        assert r["key"] == f"ml|{r['dataset']}|{r['item_id']}" and r["provisional_label"] in (0, 1)
        assert r["model_label"] in (0, 1, None) and isinstance(r["greedy_text"], str) and r["max_new_tokens"] == 6
        assert r["rule"] in ("refusal_markers", "abstain_markers", "first_mentioned_candidate")
        assert (r["agrees_with_provisional"] is None) == (r["model_label"] is None)
        if r["model_label"] is not None:
            assert r["model_answer"] in r["candidates"] and (r["model_label"] == 1) == (r["model_answer"] == r["candidates"][0])
    # resumable: a second call adds nothing; the ledger has the step
    assert sum(RC.collect_model_labels(target, ds, its, batch=4) for ds, its in groups.items()) == 0
    steps = {r["step"] for r in RC.flush_ledgers()}
    assert "model_labels" in steps


def test_greedy_continuations_left_padding_matches_single(target):
    """Batched greedy generation with left padding gives each row the same continuation as generating it alone."""
    tok = target.tokenizer
    rows = [RC.render_ids(tok, t, "chat") for t in ("Pick one: tea or coffee?", "short", "Who has the red pen? Answer with the name only.")]
    assert len({len(r) for r in rows}) > 1
    batched = RC.greedy_continuations(target.model, tok, rows, max_new_tokens=5)
    for r, b in zip(rows, batched):
        single = RC.greedy_continuations(target.model, tok, [r], max_new_tokens=5)[0]
        assert single == b, (single, b)


def test_cli_items_file_readerbench_extras(target, tmp_path, monkeypatch):
    """``main --items-file`` on a mock items_rb.json holding an earlier-turn CONTEXT fact and three model-labelled INTERNAL
    facts: capture renders the conversations, prompt-only runs, model_labels.jsonl is written from main's phase-A hook."""
    from projects.g_agreement.g1_agreement import collect as G1

    a = json.loads(mock_messages_items(tmp_path).read_text())["items"]
    b = json.loads(mock_model_labelled_items(tmp_path).read_text())["items"]
    path = tmp_path / "items_rb_all.json"
    path.write_text(json.dumps({"meta": {"mock": True}, "items": a + b}))
    monkeypatch.setattr(G1, "load_target_timed", lambda module: target)
    monkeypatch.setattr(RC, "bind_readers", lambda t, names, scales=None: [mock_jlens(t)])
    monkeypatch.setattr(M, "unload", lambda obj: None)
    monkeypatch.setattr(C, "CACHE_DIR", tmp_path / "cache")
    assert RC.main(["--phase", "A", "--items-file", str(path), "--datasets", "rb_context_earlier_turn", "rb_internal_refusal",
                    "rb_internal_self_choice", "--allow-unfrozen", "--renders", "chat", "--capture-batch", "4", "--batch", "4"]) == 0
    idx = json.loads(RC.index_file("rb_context_earlier_turn").read_text())
    assert idx["n_messages"] == 6 and idx["n_model_labelled"] == 0
    idx2 = json.loads(RC.index_file("rb_internal_self_choice").read_text())
    assert idx2["n_model_labelled"] == 6 and idx2["per_item_candidates"] is True
    ml = A.read_jsonl(RC.ML_PATH)
    assert {r["dataset"] for r in ml} == {"rb_internal_refusal", "rb_internal_self_choice"} and len(ml) == 12
    po = A.read_jsonl(RC.PO_PATH)
    assert {r["dataset"] for r in po} == {"rb_context_earlier_turn", "rb_internal_refusal", "rb_internal_self_choice"}
    lo = [r for r in A.read_jsonl(RC.LO_PATH) if r["dataset"] == "rb_context_earlier_turn" and r["condition"] == "natural"]
    assert lo and all(r["system"] is False for r in lo)
    log = RC.LOG.read_text()
    assert "model_labels 6;" in log and "model_labels 0;" in log
    assert "model_labels" in {r["step"] for r in A.read_jsonl(A.C.COMPUTE_LEDGER)}


# ================================================================== follow-ups (2026-10-18): sha fallback on pods, phase-B suffix, R-E relabel hook
def test_git_sha_fallbacks(tmp_path, monkeypatch):
    """Pods are rsync copies without .git: $R_GIT_SHA, then a GIT_SHA file at the repo root, stand in for git."""
    monkeypatch.setattr(C, "REPO_ROOT", tmp_path)          # no repository here (tmp is outside any checkout)
    monkeypatch.delenv("R_GIT_SHA", raising=False)
    assert RC.git_sha() is None
    (tmp_path / "GIT_SHA").write_text("f" * 40 + "\n")
    assert RC.git_sha() == "f" * 40
    monkeypatch.setenv("R_GIT_SHA", "e" * 40)
    assert RC.git_sha() == "e" * 40                         # the env var wins over the file
    assert RC.set_run_meta("A1", (1, 4))["git_sha"] == "e" * 40
    RC.set_shard((1, 4), "B")
    assert RC.LO_PATH.name == "reader_lo.1.B.jsonl" and RC.LOG.name == "log.1.B.md" and RC.LEDGER_PATH == C.RESULTS_DIR / "compute.1.B.jsonl"
    assert RC.RL_PATH.name == "re_relabel.1.B.jsonl" and RC.ML_PATH.name == "model_labels.1.B.jsonl"
    RC.set_shard(None)
    assert RC.LO_PATH.name == "reader_lo.jsonl" and RC.RL_PATH.name == "re_relabel.jsonl" and RC.LEDGER_PATH is None


def mock_re_internal_items(tmp_path: Path) -> Path:
    """WS10's two INTERNAL facts in the items_re.json shape: design labels, primary.key = "design", a construction block."""
    from projects.g_agreement.r_bench import beyond_text as BT

    items = []
    for ds, cands, tmpl in (("re_internal_refuse", ["refuse", "comply"], "The assistant will {X}."),
                            ("re_internal_abstain", ["uncertain", "confident"], "The assistant is {X} about the answer.")):
        assert ds in BT.CLASSIFIERS
        for split, n in (("test", 4), ("pool", 2)):
            for k in range(n):
                y = k % 2
                items.append({"item_id": f"re-{ds}-{split}-{k:04d}", "dataset": ds, "tag": "INTERNAL", "split": split, "label": y,
                              "raw_target": "x", "prompt_text": TEXTS[k % len(TEXTS)] + f" ?{k}", "render": "chat", "system": None,
                              "primary": {"name": ds, "question": "What will the assistant do?", "candidates": cands, "answer": cands[0] if y else cands[1],
                                          "template": tmpl, "sided": "two", "jlens": cands, "key": "design"},
                              "construction": {"design_label": y, "behaviour": {"kind": "greedy_continuation"}}, "read_position": None})
    p = tmp_path / "items_re.json"
    p.write_text(json.dumps({"meta": {"mock": True}, "items": items}))
    return p


def test_re_relabel_rows_rekey_resume_and_phase_b(target, tmp_path):
    from projects.g_agreement.r_bench import bank as B
    from projects.g_agreement.r_bench import beyond_text as BT

    items = B.load_items(mock_re_internal_items(tmp_path), "all")
    groups = RC.items_by_dataset(items)
    out = {}
    for ds, its in groups.items():
        n, out[ds] = RC.collect_re_relabel(target, ds, its, batch=4, max_new_tokens=6)
        assert n == 6 and len(out[ds]) == 6
    rows = A.read_jsonl(RC.RL_PATH)
    assert len(rows) == 12 and {r["dataset"] for r in rows} == set(groups)
    by_id = {r["item_id"]: r for r in rows}
    for ds, its in out.items():
        clf = BT.CLASSIFIERS[ds]
        for it in its:
            r = by_id[it["item_id"]]
            assert r["key"] == f"rl|{ds}|{it['item_id']}" and r["max_new_tokens"] == 6 and r["classifier"] == clf.__name__
            assert it["primary"]["key"] == "greedy" and it["label"] == r["label"] == int(clf(r["greedy_text"]))
            assert it["primary"]["answer"] == it["primary"]["candidates"][0 if it["label"] else 1]
            assert it["construction"]["design_label"] == r["design_label"] and "greedy_head" in it["construction"]
    # the originals are untouched (rekey_internal copies); a second call decodes nothing; phase B (no target) rekeys from disk
    assert all(it["primary"]["key"] == "design" for its in groups.values() for it in its)
    for ds, its in groups.items():
        n2, again = RC.collect_re_relabel(target, ds, its, batch=4)
        assert n2 == 0 and [it["label"] for it in again] == [it["label"] for it in out[ds]]
        n3, phase_b = RC.collect_re_relabel(None, ds, its)
        assert n3 == 0 and [(it["label"], it["primary"]["key"]) for it in phase_b] == [(it["label"], "greedy") for it in out[ds]]
    # a dataset outside beyond_text.CLASSIFIERS, and WS12's model-labelled items, pass through unchanged
    plain = B.load_items(mock_items(tmp_path), "all")
    assert RC.collect_re_relabel(target, "92_glue_sst2", plain) == (0, plain)
    ml = B.load_items(mock_model_labelled_items(tmp_path), "all")
    ml_ref = [it for it in ml if it["dataset"] == "rb_internal_refusal"]
    assert RC.collect_re_relabel(target, "re_internal_refuse", ml_ref) == (0, ml_ref)
    # phase B before any phase A row: items keep the design label and key
    RC._DONE.clear()
    for p in RC.R_DIR.glob("re_relabel*.jsonl"):
        p.unlink()
    n4, untouched = RC.collect_re_relabel(None, "re_internal_refuse", groups["re_internal_refuse"])
    assert n4 == 0 and all(it["primary"]["key"] == "design" for it in untouched)
    assert "re_relabel" in {r["step"] for r in RC.flush_ledgers()}


def test_cli_re_relabel_hook_scores_readers_on_the_greedy_key(target, tmp_path, monkeypatch):
    """main --phase A on an R-E bank: the relabel rows exist, and every reader_lo row of the two facts carries the rekeyed
    label; phase B (NLA) scores the same key from disk."""
    from projects.g_agreement.g1_agreement import collect as G1

    path = mock_re_internal_items(tmp_path)
    monkeypatch.setattr(G1, "load_target_timed", lambda module: target)
    monkeypatch.setattr(RC, "bind_readers", lambda t, names, scales=None: [mock_jlens(t)])
    monkeypatch.setattr(RC, "bind_nla", lambda: mock_nla())
    monkeypatch.setattr(M, "unload", lambda obj: None)
    monkeypatch.setattr(C, "CACHE_DIR", tmp_path / "cache")
    common = ["--items-file", str(path), "--allow-unfrozen", "--renders", "chat", "--capture-batch", "4", "--batch", "4", "--layers", "2"]
    assert RC.main(["--phase", "A"] + common) == 0
    rl = {r["item_id"]: r for r in A.read_jsonl(RC.RL_PATH)}
    assert len(rl) == 12
    lo = [r for r in A.read_jsonl(RC.LO_PATH) if r["condition"] == "natural" and r["split"] == "test"]
    assert lo and all(r["label"] == rl[r["item_id"]]["label"] for r in lo)
    assert "re_relabel 6;" in RC.LOG.read_text()
    assert RC.main(["--phase", "B"] + common) == 0
    nla = [r for r in A.read_jsonl(RC.LO_PATH) if r["reader"] == "nla" and r["condition"] == "natural" and r["split"] == "test"]
    assert nla and all(r["label"] == rl[r["item_id"]]["label"] for r in nla)
    assert len(A.read_jsonl(RC.RL_PATH)) == 12   # phase B decoded nothing


# ================================================================== PODS.md rule 10 / GUARDS.md (2026-10-20): derived paths, decoys, run stamps
STAMP_FIELDS = ("run_id", "run_started_at", "run_kind", "code_sha256", "pod", "shard", "git_sha")


def test_output_paths_catch_all_names_a_decoy(monkeypatch, tmp_path):
    """Rule 1 + 2: a path constant the enumeration misses, and an enumerated path left outside the redirect, both fail
    the fixture's check and are named."""
    assert RC.unlisted_paths() == [] and unredirected(tmp_path) == []
    monkeypatch.setattr(RC, "DECOY_POOL_PATH", RC.R_DIR / "swap_poetry_pool.jsonl", raising=False)   # 02:14Z incident shape
    assert RC.unlisted_paths() == ["DECOY_POOL_PATH"] and unredirected(tmp_path) == ["unlisted:DECOY_POOL_PATH"]
    monkeypatch.delattr(RC, "DECOY_POOL_PATH")
    monkeypatch.setattr(RC, "FROZEN_R", REPO / "projects" / "g_agreement" / "manifest" / "frozen_config_r.json")
    assert unredirected(tmp_path) == ["frozen_manifest"]
    # every row file is derived from ROW_FILES and enumerated; set_shard / set_cache_dir keep the enumeration complete
    RC.set_shard((2, 4), "B")
    RC.set_cache_dir(tmp_path / "elsewhere")
    paths = RC.output_paths()
    assert {stem for stem in RC.ROW_FILES.values()} <= set(paths) and RC.unlisted_paths() == []
    assert all(paths[stem].name == f"{stem}.2.B.jsonl" for stem in RC.ROW_FILES.values())


def _stamp_rows(target, tmp_path, items_path=None):
    from projects.g_agreement.r_bench import bank as B

    p = mock_model_labelled_items(tmp_path)
    items = B.load_items(p, "all", ["rb_internal_refusal"])
    RC.collect_prompt_only(target, "rb_internal_refusal", items, batch=4, items_path=items_path)
    RC.collect_model_labels(target, "rb_internal_refusal", items, batch=4, max_new_tokens=4, items_path=items_path)
    return A.read_jsonl(RC.PO_PATH), A.read_jsonl(RC.ML_PATH)


def test_rows_carry_collects_own_run_stamp_when_the_caller_sets_nothing(target, tmp_path):
    """WS5's finding: with RUN_META empty (a caller that never calls set_run_meta) every row still carries collect.py's
    run_id, run_kind and code_sha256 — the decoy is the empty RUN_META."""
    RC.RUN_META.clear()
    po, ml = _stamp_rows(target, tmp_path)
    for r in po + ml:
        assert r["run_id"] == RC.RUN_ID and r["run_kind"] == "test" and r["code_sha256"] == RC.code_sha256()
        assert r["run_started_at"] == RC.RUN_STARTED_AT and len(r["code_sha256"]) == 64
    led = RC.flush_ledgers()
    assert led and all(x["extra"]["run_id"] == RC.RUN_ID and x["extra"]["run_kind"] == "test" for x in led)
    RC.rlog("decoy line")
    assert f"run={RC.RUN_ID} kind=test code={RC.code_sha256()[:10]}]" in RC.LOG.read_text()


def test_caller_override_and_late_kind_change_reach_the_rows(target, tmp_path):
    """planted.py pushes its own run_id / run_kind / code_sha256 into RUN_META: they win. A kind declared AFTER
    set_run_meta reaches the next rows (a stamp frozen at import would keep the old kind: WS4's decoy finding)."""
    RC.set_run_meta("PODX", None)
    assert RC.RUN_META["run_id"] == RC.RUN_ID and RC.RUN_META["run_kind"] == "test"
    RC.set_run_kind("smoke")
    po, _ = _stamp_rows(target, tmp_path)
    assert {r["run_kind"] for r in po} == {"smoke"} and {r["pod"] for r in po} == {"PODX"}
    RC.RUN_META.update(run_id="planted-DECOY-RUN", run_kind="real", code_sha256="d" * 64)
    from projects.g_agreement.r_bench import bank as B

    items = B.load_items(mock_model_labelled_items(tmp_path), "all", ["rb_internal_abstain"])
    RC.collect_prompt_only(target, "rb_internal_abstain", items, batch=4)
    new = [r for r in A.read_jsonl(RC.PO_PATH) if r["dataset"] == "rb_internal_abstain"]
    assert new and all(r["run_id"] == "planted-DECOY-RUN" and r["run_kind"] == "real" and r["code_sha256"] == "d" * 64 for r in new)
    with pytest.raises(ValueError, match="'bogus_kind'"):
        RC.set_run_kind("bogus_kind")


def test_model_labels_rows_are_stamped_like_prompt_only(target, tmp_path):
    """WS12's finding: model_labels rows carry run_id, run_kind, code_sha256, items_file and items_sha256, the same stamp
    fields as prompt_only rows. The decoy bank name must appear on both; with no bank known the fields are None, never
    another bank's sha."""
    decoy = tmp_path / "items_rdecoy.json"
    decoy.write_text(mock_model_labelled_items(tmp_path).read_text())
    RC.set_run_meta("PODT", None)
    po, ml = _stamp_rows(target, tmp_path, items_path=decoy)
    assert ml and po and all(r["code_sha256"] == r["current_r_code_sha256"] for r in ml)   # the freeze's r-code tree sha
    want = set(STAMP_FIELDS) | {"items_file", "items_sha256", "current_r_code_sha256"}
    for r in ml + po:
        assert want <= set(r), sorted(want - set(r))
        assert r["items_file"] == "items_rdecoy.json" and r["items_sha256"] == C.sha256_file(decoy)
    assert {k for k in ml[0] if k in want} == {k for k in po[0] if k in want}
    # the process's bank (main sets it) stamps a caller that passes none; with neither, None
    RC._DONE.clear()
    for p in (RC.PO_PATH, RC.ML_PATH):
        p.unlink()
    RC.set_items_path(decoy)
    po2, ml2 = _stamp_rows(target, tmp_path)
    assert {r["items_file"] for r in po2 + ml2} == {"items_rdecoy.json"}
    RC.set_items_path(None)
    RC._DONE.clear()
    for p in (RC.PO_PATH, RC.ML_PATH):
        p.unlink()
    po3, ml3 = _stamp_rows(target, tmp_path)
    assert all(r["items_file"] is None and r["items_sha256"] is None for r in po3 + ml3)


def test_run_kind_rules_and_their_decoys(tmp_path, monkeypatch):
    """Chat 7's design: default unknown, real only when declared, --limit forces smoke and refuses a declared real;
    a smoke / test run in the real cache is refused, naming the directory."""
    assert RC.resolve_run_kind(None, None) == "unknown" and RC.resolve_run_kind("real", None) == "real"
    assert RC.resolve_run_kind(None, 3) == "smoke" and RC.resolve_run_kind("smoke", 3) == "smoke"
    with pytest.raises(SystemExit, match="--run-kind real"):
        RC.resolve_run_kind("real", 3)
    monkeypatch.setattr(C, "CACHE_DIR", tmp_path / "cache")
    real = C.CACHE_DIR / "r"
    with pytest.raises(SystemExit, match=str(real)):
        RC.check_kind_dir("smoke", real)
    with pytest.raises(SystemExit, match="test run"):
        RC.check_kind_dir("test", real)
    RC.check_kind_dir("real", real)
    RC.check_kind_dir("unknown", real)
    RC.check_kind_dir("smoke", C.CACHE_DIR / "r_smoke")


def _cli(target, tmp_path, monkeypatch):
    from projects.g_agreement.g1_agreement import collect as G1
    from projects.g_agreement.r_bench import bank as B

    path = mock_items(tmp_path)
    monkeypatch.setattr(B, "ITEMS_R", path)
    monkeypatch.setattr(G1, "load_target_timed", lambda module: target)
    monkeypatch.setattr(RC, "bind_readers", lambda t, names, scales=None: [mock_jlens(t)])
    monkeypatch.setattr(M, "unload", lambda obj: None)
    monkeypatch.setattr(C, "CACHE_DIR", tmp_path / "cache")
    return path, ["--renders", "chat", "--capture-batch", "4", "--batch", "4", "--layers", "2", "--allow-unfrozen"]


def test_cli_kind_datasets_never_smoke_limit_forces_smoke(target, tmp_path, monkeypatch):
    from projects.g_agreement.r_bench import bank as B

    path, common = _cli(target, tmp_path, monkeypatch)
    bank_ds = sorted({it["dataset"] for it in B.load_items(path, "all")})
    # --datasets is how real segmented runs are cut: it never implies smoke; the kind stays unknown unless declared
    assert RC.main(["--phase", "A", "--datasets", bank_ds[0]] + common) == 0
    assert {r["run_kind"] for r in A.read_jsonl(RC.LO_PATH)} == {"unknown"}
    assert RC.main(["--phase", "A", "--datasets", bank_ds[0], "--run-kind", "real", "--cache-dir", str(tmp_path / "declared")] + common) == 0
    assert {r["run_kind"] for r in A.read_jsonl(RC.LO_PATH)} == {"real"} and RC.R_DIR == tmp_path / "declared"
    # --limit: smoke, its own cache dir and suffixed log / ledger, the first N test + N pool items per dataset
    n = 2
    RC.set_shard(None)
    assert RC.main(["--phase", "A", "--limit", str(n)] + common) == 0
    assert RC.R_DIR == C.CACHE_DIR / "r_smoke" and RC.LO_PATH.name == "reader_lo.smoke.jsonl" and RC.LOG.name == "log.smoke.md"
    po = A.read_jsonl(RC.PO_PATH)
    assert {r["run_kind"] for r in po} == {"smoke"} and {r["run_kind"] for r in A.read_jsonl(RC.LO_PATH)} == {"smoke"}
    want = {ds: sum(min(n, sum(it["split"] == s for it in its)) for s in ("test", "pool"))
            for ds, its in RC.items_by_dataset(B.load_items(path, "all")).items()}
    got = {ds: sum(r["dataset"] == ds for r in po) for ds in want}
    assert got == want
    assert "kind=smoke" in RC.LOG.read_text() and {r["extra"]["run_kind"] for r in A.read_jsonl(C.RESULTS_DIR / "compute.smoke.jsonl")} == {"smoke"}
    # decoys: --limit with a declared real kind; --limit pointed at the real cache
    with pytest.raises(SystemExit, match="--run-kind real"):
        RC.main(["--phase", "A", "--limit", "1", "--run-kind", "real"] + common)
    with pytest.raises(SystemExit, match="refusing a smoke run in the real cache"):
        RC.main(["--phase", "A", "--limit", "1", "--cache-dir", str(C.CACHE_DIR / "r")] + common)


def test_dataset_and_shard_selection_name_the_decoy(tmp_path):
    from projects.g_agreement.r_bench import bank as B

    items = B.load_items(mock_items(tmp_path), "all")
    bank_ds = sorted({it["dataset"] for it in items})
    with pytest.raises(SystemExit, match="zz_decoy_dataset"):   # a typo used to drop a dataset silently
        RC.select_items(items, None, [bank_ds[0], "zz_decoy_dataset"])
    owner = {ds: k for k in (1, 2) for ds in RC.shard_datasets(bank_ds, (k, 2))}
    other = bank_ds[1]
    wrong = 1 if owner[other] == 2 else 2
    with pytest.raises(SystemExit, match=rf"{other}→{owner[other]}/2"):
        RC.select_items(items, (wrong, 2), [other])
    sel = RC.select_items(items, (owner[other], 2), None)
    assert {it["dataset"] for it in sel} == {ds for ds, k in owner.items() if k == owner[other]}


def test_freeze_guard_names_the_decoy_bank(tmp_path, monkeypatch):
    from projects.g_agreement.r_bench import bank as B

    path = mock_items(tmp_path)
    monkeypatch.setattr(B, "ITEMS_R", path)
    monkeypatch.setattr(B, "ITEMS_RK", tmp_path / "items_rk.json")
    monkeypatch.setattr(C, "MANIFEST_DIR", tmp_path / "manifest")
    monkeypatch.setattr(C, "DATASET_DIR", tmp_path)
    RC.freeze_r()
    RC.require_frozen_r(False, path)
    decoy = tmp_path / "elsewhere" / "items_rdecoy.json"
    decoy.parent.mkdir()
    decoy.write_text("{}")
    with pytest.raises(SystemExit, match="items_rdecoy.json is not covered by the R freeze"):
        RC.require_frozen_r(False, decoy)
    path.write_text(path.read_text().replace("wonderful", "WONDERFUL"))
    with pytest.raises(SystemExit, match="items_r.json changed since the R freeze"):
        RC.require_frozen_r(False, path)


def test_phase_b_gating_names_the_waiting_decoy(target, tmp_path, monkeypatch):
    """A dataset whose index.json exists but whose block-42 state does not is waiting, by name, in the gate and in
    main's log line; the ready one runs."""
    from projects.g_agreement.r_bench import bank as B

    monkeypatch.setattr(C, "LAYER", 2)
    path, common = _cli(target, tmp_path, monkeypatch)
    monkeypatch.setattr(RC, "bind_nla", lambda: mock_nla())
    bank_ds = sorted({it["dataset"] for it in B.load_items(path, "all")})
    ready_ds, decoy_ds = bank_ds
    assert RC.main(["--phase", "A", "--datasets", ready_ds] + common) == 0
    items = RC.items_by_dataset(B.load_items(path, "all"))
    RC.write_index(decoy_ds, RC.ordered_items(items[decoy_ds]), RC.LAYERS, ("chat",))   # index, no state files
    ready, waiting = RC.phase_b_ready(items, ("chat",))
    assert ready == [ready_ds] and waiting == [decoy_ds]
    assert RC.main(["--phase", "B"] + common) == 0
    assert f"1 not yet captured (skipped, re-run later): ['{decoy_ds}']" in RC.LOG.read_text()


# ---------------------------------------------------------------- provenance sidecar for rows that predate the stamps (WS12)
def _legacy_fixture(tmp_path, rows_extra=None, log_extra=None, counts=None):
    sha = "4d482b612b0da5838b83e43a4c85656daec7f778"
    t0 = "2026-10-19T00:15:21.238045+00:00"
    shas = {"items_file": "items_rb.json", "items_sha256": "a" * 64, "current_r_code_sha256": "c" * 64, "frozen_r_code_sha256": "f" * 64}
    rows = [{"key": f"ml|{ds}|i{k}", "dataset": ds, "item_id": f"i{k}", "pod": "RB", "git_sha": sha, "shard": None,
             "created_at": f"2026-10-19T00:35:0{k}.000000+00:00"} for ds, n in (("rb_internal_refusal", 3), ("rb_internal_abstain", 2))
            for k in range(n)]
    rows += rows_extra or []
    counts = counts or {"rb_internal_refusal": 3, "rb_internal_abstain": 2}
    tag = f"[pod=RB shard=None sha={sha[:10]}]"
    log = [f"- {t0} {tag} phase A: run={{'pod': 'RB'}} 2 datasets, 5 items, renders=('chat',), kway=False, items=items_rb.json, "
           f"cache=/workspace/x/cache/g_agreement/r, readers=['jlens'], shas={shas}"]
    log += [f"- 2026-10-19T00:36:00.000000+00:00 {tag} {ds}: {n} items; capture {{}}; prompt_only {n} new rows; model_labels {n}; re_relabel 0; 9s"
            for ds, n in counts.items()]
    log += [f"- 2026-10-19T04:57:33.832155+00:00 {tag} phase A: run={{'pod': 'RB'}} 1 datasets, kway=True, items=items_rbk.json, "
            f"cache=/workspace/x/cache/g_agreement/r, readers=['jlens'], shas={{'items_file': 'items_rbk.json'}}"]
    log += log_extra or []
    rp, lp = tmp_path / "model_labels.RB.jsonl", tmp_path / "log.md"
    rp.write_text("".join(json.dumps(r) + "\n" for r in rows))
    lp.write_text("\n".join(log) + "\n")
    return rp, lp


def test_legacy_provenance_sidecar_derives_everything_from_rows_and_log(tmp_path):
    rp, lp = _legacy_fixture(tmp_path)
    before = rp.read_bytes()
    out = RC.write_legacy_provenance(rp, lp, tmp_path / "prov")
    prov = json.loads(out.read_text())
    assert out.name == "model_labels.RB.provenance.json" and rp.read_bytes() == before and prov["rows_rewritten"] is False
    assert prov["n_rows"] == 5 and prov["per_dataset"] == {"rb_internal_abstain": 2, "rb_internal_refusal": 3}
    assert prov["run_kind"] == "real" and prov["items_file"] == "items_rb.json" and prov["items_sha256"] == "a" * 64
    assert prov["code_sha256"] == "c" * 64 and prov["process"]["log_line"] == 1 and prov["run_id"] == "legacy-RB-20261019T001521Z"
    assert prov["rows_sha256"] == C.sha256_file(rp)


@pytest.mark.parametrize("case,match", [
    ("other_pod", "row ml|rb_internal_refusal|DECOY"),
    ("second_process", "row ml|rb_internal_refusal|LATE"),
    ("count", "rb_internal_refusal rows 3 vs logged 4"),
    ("stamped", "already carry run_id"),
])
def test_legacy_provenance_refuses_and_names_the_decoy(tmp_path, case, match):
    base = {"dataset": "rb_internal_refusal", "pod": "RB", "git_sha": "4d482b612b0da5838b83e43a4c85656daec7f778", "shard": None}
    kw = {}
    if case == "other_pod":
        kw["rows_extra"] = [{**base, "key": "ml|rb_internal_refusal|DECOY", "item_id": "DECOY", "pod": "DECOYPOD",
                             "created_at": "2026-10-19T00:35:09.000000+00:00"}]
    elif case == "second_process":
        kw["rows_extra"] = [{**base, "key": "ml|rb_internal_refusal|LATE", "item_id": "LATE", "created_at": "2026-10-19T05:00:00.000000+00:00"}]
    elif case == "count":
        kw["counts"] = {"rb_internal_refusal": 4, "rb_internal_abstain": 2}
    else:
        kw["rows_extra"] = [{**base, "key": "ml|rb_internal_refusal|NEW", "item_id": "NEW", "run_id": "x", "created_at": "2026-10-19T00:35:09.000000+00:00"}]
    rp, lp = _legacy_fixture(tmp_path, **kw)
    with pytest.raises(SystemExit, match=match):
        RC.legacy_provenance(rp, lp)


REAL_RB = Path("/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r/model_labels.RB.jsonl")


@pytest.mark.skipif(not REAL_RB.exists(), reason="the real RB model_labels file is only in the main checkout's cache")
def test_legacy_provenance_of_the_real_rb_rows_is_one_real_process():
    """Read-only on the real file: the 1,104 rows are one process (pod RB, phase A at 00:15:21Z) on the frozen items_rb.json."""
    prov = RC.legacy_provenance(REAL_RB, REPO / "results" / "g_agreement" / "r" / "log.md")
    assert prov["n_rows"] == sum(prov["per_dataset"].values()) and prov["pod"] == "RB" and prov["run_kind"] == "real"
    assert prov["items_file"] == "items_rb.json" and prov["process"]["phase"] == "A"
