"""MOCK tests (CPU) for the G5/G6 follow-up: teacher-forced log-odds in each reader's native
format (core/scoring_lo.py), the state edit + swap vectors (core/edit.py), the G5 collector
(g5_planted/collect.py) on tmp paths, and the G6 plumbing of the G1/G3 collectors. Same tiny
random Qwen3_5 model and fake tokenizer as test_readers_mock.py; nothing is written under
results/ or cache/.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_g5_mock.py -q``
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

torch = pytest.importorskip("torch")

from projects.g_agreement.core import accounting as A  # noqa: E402
from projects.g_agreement.core import config as C  # noqa: E402
from projects.g_agreement.core import edit as E  # noqa: E402
from projects.g_agreement.core import model as M  # noqa: E402
from projects.g_agreement.core import readers as R  # noqa: E402
from projects.g_agreement.core import scoring_lo as LO  # noqa: E402
from projects.g_agreement.core import states as S  # noqa: E402
from projects.g_agreement.tests.test_readers_mock import MOCK_D, MOCK_LAYER, FakeTok, mock_meta, tiny_model  # noqa: E402

RESULTS_SNAPSHOT = sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*"))
CACHE_SNAPSHOT = sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None


@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    monkeypatch.setattr(C, "LAYER", MOCK_LAYER)
    monkeypatch.setattr(C, "HIDDEN_STATES_INDEX", MOCK_LAYER + 1)
    monkeypatch.setattr(C, "D_MODEL", MOCK_D)
    monkeypatch.setattr(C, "N_LAYERS", 4)
    monkeypatch.setattr(C, "DEV_EXTRA_LAYERS", ())
    yield


@pytest.fixture(scope="module")
def target():
    return M.Target(model=tiny_model(), tokenizer=FakeTok(), device="cpu", model_id="MOCK/tiny", revision="mock",
                    model_class="Qwen3_5ForCausalLM")


@pytest.fixture(scope="module")
def olens(target):
    r = R.OLensReader(max_new_tokens=4)
    r.target = target  # MOCK: no LoRA; the tiny model stands in for base+adapter
    return r


@pytest.fixture(scope="module")
def nla():
    tok = FakeTok()
    return R.NLAReader(max_new_tokens=4).attach(tiny_model(3), tok, mock_meta(tok), device="cpu")


@pytest.fixture(scope="module")
def jlens(target):
    torch.manual_seed(1)
    J = {MOCK_LAYER: torch.eye(MOCK_D) + torch.randn(MOCK_D, MOCK_D) / 10}
    return R.JLensReader().bind_tensors(J, M.unembed_weight(target.model), target.tokenizer)


def mk_item(iid, pair, version, family, prompt, answer, other):
    return {"item_id": iid, "pair_id": pair, "version": version, "family": family, "split": "test", "render": "chat",
            "system": None, "prompt_text": prompt,
            "primary": {"name": "x", "question": "Who?", "candidates": [answer, other] if version == "A" else [other, answer],
                        "answer": answer, "answer_aliases": [answer.lower()]}}


def items():  # single-letter candidates so the char-level FakeTok has single-token variants
    return [mk_item("own-01A", "own-01", "A", "ownership", "A has the key. B has the pen. Who has the key? Name only.", "A", "B"),
            mk_item("own-01B", "own-01", "B", "ownership", "B has the key. A has the pen. Who has the key? Name only.", "B", "A"),
            mk_item("map-01A", "map-01", "A", "mapping", "x->y, y->z. Twice from x?", "z", "y"),
            mk_item("map-01B", "map-01", "B", "mapping", "x->z, z->y. Twice from x?", "y", "z")]


# ================================================================== scoring_lo
def manual_logprob(model, ids, head_len, embed_fn=None):
    """Reference: one unbatched full forward, sum log p of the tokens after the head."""
    x = torch.tensor([ids])
    with torch.no_grad():
        out = model(inputs_embeds=embed_fn(x), use_cache=False) if embed_fn else model(x, use_cache=False)
        lp = torch.log_softmax(out.logits[0].float(), dim=-1)
    return float(sum(lp[u - 1, ids[u]] for u in range(head_len, len(ids))))


def test_olens_lo_matches_unbatched_reference(olens, target):
    torch.manual_seed(0)
    H = torch.randn(2, MOCK_D) * 50
    pairs = [("A", "B"), ("Mira", "Leo")]
    rows = LO.score_lo(olens, H, pairs, "ownership")
    ids0, slot, char, cid = olens.carrier(MOCK_LAYER)
    embed = target.model.get_input_embeddings()
    for i, (a, b) in enumerate(pairs):
        def embed_fn(x, h=H[i]):
            e = embed(x).clone()
            e[0, slot, :] = olens.alpha * h / h.norm()
            return e
        ref = {c: manual_logprob(target.model, ids0 + LO.encode(target.tokenizer, f"- {c}"), len(ids0), embed_fn) for c in (a, b)}
        assert abs(rows[i]["lp_A"] - ref[a]) < 1e-3 and abs(rows[i]["lp_B"] - ref[b]) < 1e-3
        assert abs(rows[i]["lo"] - (ref[a] - ref[b])) < 1e-3
        assert rows[i]["cand_A"] == a and rows[i]["templates"] == ["- {X}"] and rows[i]["unscorable"] is False
    # scoring the states one at a time (different batch composition) gives the same numbers in fp32
    single = LO.score_lo(olens, H[1:], pairs[1:], "ownership")
    assert abs(single[0]["lo"] - rows[1]["lo"]) < 1e-3


def test_nla_lo_templates_and_per_row_hook(nla):
    torch.manual_seed(0)
    H = torch.randn(2, MOCK_D) * 30
    pairs = [("A", "B"), ("z", "y")]
    rows = LO.score_lo(nla, H, pairs, "ownership")
    temps = LO.templates_for("ownership")
    assert len(temps) == 2 and rows[0]["templates"] == temps and "name" in temps[0]
    assert LO.templates_for("mapping")[0] == 'The answer must be the symbol "{X}".'
    head = list(nla.ids) + LO.encode(nla.tokenizer, LO.NLA_PREFIX)
    for i, (a, b) in enumerate(pairs):
        for j, tmpl in enumerate(temps):
            ref = {}
            for c in (a, b):
                nla._vec["v"] = H[i]  # single-vector path (the generation hook)
                try:
                    ref[c] = manual_logprob(nla.model, head + LO.encode(nla.tokenizer, tmpl.format(X=c)), len(head))
                finally:
                    nla._vec["v"] = None
            pt = rows[i]["per_template"][j]
            assert abs(pt["lp_A"] - ref[a]) < 1e-3 and abs(pt["lp_B"] - ref[b]) < 1e-3, (i, j)
        assert abs(rows[i]["lo"] - sum(p["lo"] for p in rows[i]["per_template"]) / 2) < 1e-6
    assert nla._vec["v"] is None


def test_nla_hook_rows_get_their_own_vector(nla):
    ids = nla.ids
    x = torch.tensor([ids, ids])
    v = torch.randn(2, MOCK_D) * 40
    store = {}
    blk = M.blocks(nla.model)[C.NLA_INJECT_LAYER_IDX]
    hd = blk.register_forward_hook(lambda m, i, o: store.__setitem__("h", (o[0] if isinstance(o, tuple) else o).detach().clone()))
    with torch.no_grad():
        nla._vec["v"] = v
        nla.model(x, use_cache=False)
        batched = store["h"]
        singles = []
        for k in range(2):
            nla._vec["v"] = v[k]
            nla.model(x[k:k + 1], use_cache=False)
            singles.append(store["h"][0])
        nla._vec["v"] = None
    hd.remove()
    for k in range(2):
        assert torch.allclose(batched[k], singles[k], atol=1e-4)
    with pytest.raises(RuntimeError, match="vectors for a batch"):
        nla._vec["v"] = v[:1]
        try:
            with torch.no_grad():
                nla.model(x, use_cache=False)
        finally:
            nla._vec["v"] = None


def test_jlens_lo_variants_and_unscorable(jlens, target):
    torch.manual_seed(0)
    H = torch.randn(2, MOCK_D)
    rows = LO.score_lo(jlens, H, [("A", "B"), ("Mira", "B")], "ownership")
    r = rows[0]
    assert r["unscorable"] is False and {"A", "a"} <= set(r["variants_A"])  # " A" is two chars in the MOCK tokenizer
    J, w = jlens.J[MOCK_LAYER], jlens.w_u
    z = (H[0] @ J.T) @ w.T / (w @ J).norm(dim=1)
    sa = max(float(z[t]) for t in r["variants_A"].values())
    sb = max(float(z[t]) for t in r["variants_B"].values())
    assert abs(r["lo"] - (sa - sb)) < 1e-4 and r["best_A"] in r["variants_A"]
    assert rows[1]["unscorable"] is True and rows[1]["lo"] is None and rows[1]["variants_A"] == {} and "no single-token" in rows[1]["reason"]
    assert LO.token_variants(target.tokenizer, "Mira") == {}


# ================================================================== edit
def test_generate_with_edited_state_replaces_prefill_only(target):
    ids = M.render_item(target.tokenizer, "A has the key. Who has the key?")
    v = torch.randn(MOCK_D) * 10
    seen = []  # observe the INPUT of the next block: the edited output, whatever the hook order
    blk, nxt = M.blocks(target.model)[MOCK_LAYER], M.blocks(target.model)[MOCK_LAYER + 1]
    hd = nxt.register_forward_pre_hook(lambda m, args: seen.append(args[0][0, -1].detach().float().clone()))
    try:
        res = E.generate_with_edited_state(target, ids, v, pos=-1, max_new_tokens=3)
    finally:
        hd.remove()
    assert res["n_hook_edits"] == 1 and res["pos"] == len(ids) - 1 and res["n_new_tokens"] <= 3
    assert torch.allclose(seen[0], v, atol=1e-2)  # the prefill's last position is the vector (bf16/fp32 cast)
    assert len(seen) > 1 and not torch.allclose(seen[1], v, atol=1e-2)  # decode steps are the model's own
    assert isinstance(res["answer_text"], str)
    # no hook left behind
    assert len(blk._forward_hooks) == 0


def test_swap_vectors_geometry():
    torch.manual_seed(0)
    hA, hB = torch.randn(MOCK_D) * 20, torch.randn(MOCK_D) * 20
    ent = E.swap_vectors(hA, hB, alphas=(0.5, 1.0, 1.5), signs=(1,), n_null=3, seed=7)
    delta = float((hB - hA).norm())
    by = {(e["source"], e["condition"], e["alpha"], e["null_k"]): e for e in ent}
    assert len(ent) == 2 * (1 + 3 + 3)
    assert torch.allclose(by[("A", "planted", 1.0, None)]["vector"], hB, atol=1e-4)  # alpha 1 from A lands on B
    assert torch.allclose(by[("B", "planted", 1.0, None)]["vector"], hA, atol=1e-4)
    assert abs(by[("A", "planted", 0.5, None)]["dose_abs"] - 0.5 * delta) < 1e-4
    for k in range(3):
        n = by[("A", "null", 1.0, k)]
        assert abs(float((n["vector"] - hA).norm()) - delta) < 1e-3 and abs(n["cos_to_u"]) < 0.6
        assert torch.allclose(by[("B", "null", 1.0, k)]["vector"] - hB, -(n["vector"] - hA), atol=1e-4)  # same r_k, toward frame
    again = E.swap_vectors(hA, hB, alphas=(1.0,), n_null=3, seed=7)
    assert torch.allclose(again[-1]["vector"], by[("B", "null", 1.0, 2)]["vector"])
    assert by[("A", "natural", 0.0, None)]["sign"] == 0 and by[("A", "planted", 1.0, None)]["sign"] == 1


# ================================================================== g5 collector on tmp paths
def test_g5_collect_end_to_end(target, olens, nla, jlens, tmp_path, monkeypatch):
    from projects.g_agreement.g5_planted import collect as G5

    monkeypatch.setattr(C, "FROZEN_CANDIDATES", (tmp_path / "none.json",))
    sd = tmp_path / "states"
    S.ensure_states(target, items(), states_dir=sd, meta_path=tmp_path / "meta.jsonl", ledger_path=tmp_path / "c.jsonl")
    pairs = G5.g5_pairs(items=items())
    assert [p["pair_id"] for p in pairs] == ["map-01", "own-01"] and pairs[1]["A"]["item_id"] == "own-01A"
    ents = G5.pair_entries(pairs[1], 2, sd)
    assert {e["condition"] for e in ents} == {"natural", "planted", "null"} and len(ents) == 2 * (1 + 3 + 2)
    assert ents[0]["cand_A"] == "A" and ents[0]["cand_B"] == "B" and ents[0]["state_item_id"] == "own-01A"
    lo, beh, gens, led, log = (tmp_path / f for f in ("lo.jsonl", "beh.jsonl", "g5.jsonl", "c.jsonl", "log.md"))
    for reader in (jlens, olens, nla):
        n = G5.collect_lo(reader, pairs, n_null=2, lo_path=lo, ledger_path=led, log_path=log, states_dir=sd, batch=4)
        assert n == 2 * 2 * (1 + 3 + 2)
    rows = A.read_jsonl(lo)
    assert len(rows) == 3 * 24 and {r["reader"] for r in rows} == {"jlens", "olens", "nla"}
    r = rows[0]
    for k in ("key", "pair_id", "state_item_id", "family", "reader", "condition", "alpha", "sign", "null_k", "cand_A", "cand_B",
              "lo", "lp_A", "lp_B", "templates", "dose_abs", "input_norm", "unscorable", "frozen_code_sha256"):
        assert k in r, k
    assert G5.collect_lo(olens, pairs, n_null=2, lo_path=lo, ledger_path=led, log_path=log, states_dir=sd) == 0  # resumable
    nb = G5.collect_behaviour(target, pairs, n_null=2, beh_path=beh, ledger_path=led, log_path=log, states_dir=sd, max_new_tokens=3)
    assert nb == 24
    b = A.read_jsonl(beh)[0]
    for k in ("state_item_id", "condition", "alpha", "sign", "null_k", "answer_text", "parsed", "flipped_to_other", "n_hook_edits"):
        assert k in b, k
    assert b["n_hook_edits"] == 1 and b["parsed"] in ("A", "B", None)
    assert G5.collect_behaviour(target, pairs, n_null=2, beh_path=beh, ledger_path=led, log_path=log, states_dir=sd, max_new_tokens=3) == 0
    nf = G5.collect_free(olens, pairs, gens_path=gens, ledger_path=led, log_path=log, states_dir=sd, max_new_tokens=4)
    nf2 = G5.collect_free(nla, pairs, gens_path=gens, ledger_path=led, log_path=log, states_dir=sd, max_new_tokens=4)
    assert (nf, nf2) == (4, 4)
    g = A.read_jsonl(gens)[0]
    assert g["module"] == "g5" and g["condition"] == "planted" and g["gen_id"].startswith("g5|olens|")
    assert g["input"]["injection_source"] == "pair_swap_alpha1.0" and g["input"]["swap_toward"] != g["item_id"]
    assert abs(g["input"]["dose_abs"] - g["input"]["delta"]) < 1e-6
    steps = {x["step"] for x in A.read_jsonl(led)}
    assert {"g5_lo_jlens", "g5_lo_olens", "g5_lo_nla", "g5_behaviour", "g5_free"} <= steps


# ================================================================== G6 plumbing
def test_g6_items_file_plumbing(target, tmp_path, monkeypatch):
    from projects.g_agreement.g1_agreement import collect as G1

    g6 = tmp_path / "items_g6.json"
    its = [mk_item("choice-01A", "choice-01", "A", "choice", "Choose apple or pear; reply with the word only.", "apple", "pear"),
           mk_item("choice-01B", "choice-01", "B", "choice", "Choose pear or apple; reply with the word only.", "pear", "apple")]
    g6.write_text(json.dumps({"meta": {}, "items": its}))
    sel = G1.select_items("test", 0, path=g6)
    assert [i["item_id"] for i in sel] == ["choice-01A", "choice-01B"]
    monkeypatch.setattr(G1, "ROW_EXTRA", {"items_file": str(g6), "items_file_sha256": C.sha256_file(g6)})
    row = G1.base_row("g6", "olens", "genuine", sel[0], 0)
    assert row["items_file_sha256"] == C.sha256_file(g6) and row["gen_id"] == "g6|olens|choice-01A|s0" and row["module"] == "g6"
    sd = tmp_path / "states"
    S.ensure_states(target, sel, states_dir=sd, meta_path=tmp_path / "m.jsonl", ledger_path=tmp_path / "c.jsonl", module="g6")
    assert S.state_path("choice-01A", sd).exists()
    # the G6 argparse surface exists on both collectors
    import argparse

    for mod in (G1, __import__("projects.g_agreement.g3_activation_dependence.collect_prompt_only", fromlist=["main"])):
        src = Path(mod.__file__).read_text()
        for flag in ("--items-file", "--module", "--gens"):
            assert flag in src, (mod.__name__, flag)
    assert isinstance(argparse.ArgumentParser(), argparse.ArgumentParser)


def test_frozen_status_accepts_either_manifest(tmp_path, monkeypatch):
    main, coll = tmp_path / "frozen_config.json", tmp_path / "frozen_config_collection.json"
    monkeypatch.setattr(C, "FROZEN_CANDIDATES", (main, coll))
    ok, probs = C.frozen_status()
    assert not ok and "missing" in probs[0]
    snap = C.snapshot(frozen=True)
    coll.write_text(json.dumps(snap))
    assert C.frozen_status()[0] is True
    snap2 = dict(snap, code_sha256="stale")
    coll.write_text(json.dumps(snap2))
    assert C.frozen_status(strict_code=True)[0] is False
    assert C.frozen_status(strict_code=False)[0] is True
    assert C.frozen_shas()["manifest"] == "frozen_config_collection.json" and C.frozen_shas()["frozen_code_sha256"] == "stale"
    with pytest.raises(SystemExit):
        C.require_frozen("test", strict_code=True)
    C.require_frozen("test", strict_code=False)


def test_zz_results_and_cache_untouched():
    now = sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*"))
    assert now == RESULTS_SNAPSHOT
    cache = sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None
    assert cache == CACHE_SNAPSHOT
