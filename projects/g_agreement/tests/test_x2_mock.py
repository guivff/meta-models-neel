"""MOCK tests (CPU) for Phase X2: full-sequence capture, the interpolation edit + read-back hook,
the condition table, the collector on tmp paths and analyze.py end to end on synthetic rows.
Same tiny random Qwen3_5 model and fake tokenizer as test_readers_mock.py; nothing is written under
results/ or cache/.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_x2_mock.py -q``
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
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
from projects.g_agreement.tests.test_readers_mock import MOCK_D, MOCK_LAYER, FakeTok, tiny_model  # noqa: E402
from projects.g_agreement.x2_causal import analyze as XA  # noqa: E402
from projects.g_agreement.x2_causal import collect as X  # noqa: E402

RESULTS_SNAPSHOT = sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*"))
CACHE_SNAPSHOT = sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None
MOCK_SITES = {"S1": {"layer": 1, "positions": "last"}, "S2": {"layer": 1, "positions": "all"}, "S3": {"layer": MOCK_LAYER, "positions": "all"}}


@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    monkeypatch.setattr(C, "LAYER", MOCK_LAYER)
    monkeypatch.setattr(C, "HIDDEN_STATES_INDEX", MOCK_LAYER + 1)
    monkeypatch.setattr(C, "D_MODEL", MOCK_D)
    monkeypatch.setattr(C, "N_LAYERS", 4)
    monkeypatch.setattr(E, "X2_SITES", MOCK_SITES)
    monkeypatch.setattr(E, "X2_EDIT_LAYERS", (1, MOCK_LAYER))
    monkeypatch.setattr(E, "X2_READ_LAYER", MOCK_LAYER)
    yield


@pytest.fixture(scope="module")
def target():
    return M.Target(model=tiny_model(), tokenizer=FakeTok(), device="cpu", model_id="MOCK/tiny", revision="mock", model_class="Qwen3_5ForCausalLM")


def mk_item(iid, pair, version, family, prompt, answer, other):
    return {"item_id": iid, "pair_id": pair, "version": version, "family": family, "split": "test", "render": "chat", "system": None,
            "prompt_text": prompt, "primary": {"name": "x", "question": "Who?", "candidates": [answer, other] if version == "A" else [other, answer],
                                               "answer": answer, "answer_aliases": [answer.lower()]}}


def items_x():  # A/B are token permutations (equal length); single-letter candidates
    out = []
    for n, (a, b) in enumerate([("A", "B"), ("C", "D"), ("E", "F")], start=2):
        out.append(mk_item(f"xown-{n:02d}A", f"xown-{n:02d}", "A", "ownership", f"{a} has the key. {b} has the pen. Who has the key? Name only.", a, b))
        out.append(mk_item(f"xown-{n:02d}B", f"xown-{n:02d}", "B", "ownership", f"{b} has the key. {a} has the pen. Who has the key? Name only.", b, a))
    out.append(mk_item("xmap-02A", "xmap-02", "A", "mapping", "x->y, y->z. Twice from x?", "z", "y"))
    out.append(mk_item("xmap-02B", "xmap-02", "B", "mapping", "x->z, z->y. Twice from x?", "y", "z"))
    out.append(mk_item("xmap-03A", "xmap-03", "A", "mapping", "p->q, q->r. Twice from p?", "r", "q"))
    out.append(mk_item("xmap-03B", "xmap-03", "B", "mapping", "p->r, r->q. Twice from p?", "q", "r"))
    return out


# ================================================================== (i) capture_full
def test_capture_full_shapes(target):
    ids = M.render_item(target.tokenizer, "A has the key. Who has the key?")
    H = E.capture_full(target, ids, [1, MOCK_LAYER])
    assert set(H) == {1, MOCK_LAYER} and all(tuple(h.shape) == (len(ids), MOCK_D) and h.dtype == torch.float32 for h in H.values())
    # the last row equals the single-position capture
    assert torch.allclose(H[MOCK_LAYER][-1], M.capture_last(target.model, ids, MOCK_LAYER), atol=1e-5)


# ================================================================== (ii) interpolation hook
def test_interpolation_prefill_only_and_readback_at_s3(target):
    ids = M.render_item(target.tokenizer, "A has the key. B has the pen. Who has the key? Name only.")
    T = len(ids)
    base = E.capture_full(target, ids, [MOCK_LAYER])[MOCK_LAYER]
    delta = torch.randn(T, MOCK_D) * 3
    ft = E.first_token_candidates(target.tokenizer, "A", "B")
    assert ft["form"] == "bare" and ft["first_A"] == ord("A") and ft["first_B"] == ord("B")
    seen = []  # input of the next block: edited during the prefill only
    nxt = M.blocks(target.model)[MOCK_LAYER + 1]
    hd = nxt.register_forward_pre_hook(lambda m, args: seen.append(args[0][0, -1].detach().float().clone()))
    try:
        r = E.generate_with_interpolated_state(target, ids, MOCK_LAYER, list(range(T)), base, delta, 0.5, read_layer=MOCK_LAYER, max_new_tokens=3,
                                               cand_first_tokens=(ft["first_A"], ft["first_B"]))
    finally:
        hd.remove()
    assert r["n_hook_edits"] == 1 and r["n_read_hits"] == 1 and r["n_new_tokens"] <= 3
    assert torch.allclose(r["read_vec"], base[-1] + 0.5 * delta[-1], atol=1e-5)  # S3: the read is the interpolation itself
    assert torch.allclose(seen[0], base[-1] + 0.5 * delta[-1], atol=1e-4) and len(seen) > 1 and not torch.allclose(seen[1], seen[0], atol=1e-2)
    assert len(M.blocks(target.model)[MOCK_LAYER]._forward_hooks) == 0
    # lo_model equals a manual edited forward's first-token log-odds
    v = base + 0.5 * delta

    def hk(m, i, o):
        h = o[0] if isinstance(o, tuple) else o
        h[:, :, :] = v.to(h.dtype)
        return o

    h2 = M.blocks(target.model)[MOCK_LAYER].register_forward_hook(hk)
    try:
        with torch.no_grad():
            lp = torch.log_softmax(target.model(torch.tensor([ids]), use_cache=False).logits[0, -1].float(), -1)
    finally:
        h2.remove()
    assert abs(r["lo_model"] - float(lp[ord("B")] - lp[ord("A")])) < 1e-4
    # batched rows get their own vector and match the single call; the natural path has no edit
    V = torch.stack([base + a * delta for a in (0.25, 0.5, 1.0)])
    rows = E.generate_with_interpolated_batch(target, ids, MOCK_LAYER, list(range(T)), V, read_layer=MOCK_LAYER, max_new_tokens=3, cand_first_tokens=(65, 66))
    assert len(rows) == 3 and torch.allclose(rows[1]["read_vec"], r["read_vec"], atol=1e-5) and abs(rows[1]["lo_model"] - r["lo_model"]) < 1e-4
    assert torch.allclose(rows[2]["read_vec"], base[-1] + delta[-1], atol=1e-5)
    nat = E.generate_with_interpolated_batch(target, ids, None, None, None, read_layer=MOCK_LAYER, max_new_tokens=3)[0]
    assert nat["n_hook_edits"] == 0 and torch.allclose(nat["read_vec"], base[-1], atol=1e-5) and nat["lo_model"] is None
    # S1-style edit at an earlier layer: the read is propagated, not the edit itself
    r1 = E.generate_with_interpolated_state(target, ids, 1, [T - 1], base[-1:], delta[-1:], 1.0, read_layer=MOCK_LAYER, max_new_tokens=2)
    assert r1["n_hook_edits"] == 1 and not torch.allclose(r1["read_vec"], base[-1] + delta[-1], atol=1e-2)


# ================================================================== (iii) condition table
def test_condition_table_counts_and_vectors():
    tab = E.x2_condition_table("xown-02", "ownership", other_pair_ids=["xown-03", "xown-04", "xown-05", "xown-06"], seed=5)
    assert len(tab) == 74 and len({e["key"] for e in tab}) == 74
    c = Counter((e["source"], e["site"], e["condition"]) for e in tab)
    for src in ("A", "B"):
        assert c[(src, "S1", "planted")] == 6 and c[(src, "S2", "planted")] == 4 and c[(src, "S3", "planted")] == 4
        assert c[(src, "S1", "null")] == c[(src, "S2", "null")] == c[(src, "S3", "null")] == 6
        assert c[(src, "S1", "null_other")] == 4 and c[(src, "nat", "natural")] == 1
    assert sum(1 for e in tab if e["condition"] == "null_other") == 8 and all(e["site"] == "S1" for e in tab if e["condition"] == "null_other")
    assert {e["alpha"] for e in tab if e["site"] == "S1" and e["condition"] == "planted"} == {0.5, 1, 1.5, 2, 3, 4}
    assert {e["alpha"] for e in tab if e["site"] == "S1" and e["condition"].startswith("null")} == {2.0}
    assert {e["alpha"] for e in tab if e["site"] in ("S2", "S3") and e["condition"] == "null"} == {1.0}
    assert tab[0]["key"] == "xown-02|A|nat|natural|0.0|None" and all(e["sign"] in (-1, 1) for e in tab if e["condition"].startswith("null"))
    # vectors: geometry in the A->B frame
    torch.manual_seed(0)
    T = 7
    HA = {1: torch.randn(T, MOCK_D) * 5, MOCK_LAYER: torch.randn(T, MOCK_D) * 5}
    HB = {1: HA[1] + torch.randn(T, MOCK_D), MOCK_LAYER: HA[MOCK_LAYER] + torch.randn(T, MOCK_D)}
    nulls = E.X2Nulls(5)
    od = {p: torch.randn(MOCK_D) for p in ("xown-03", "xown-04", "xown-05", "xown-06")}
    by = {(e["source"], e["site"], e["condition"], e["alpha"], e["null_k"]): e for e in tab}
    vA = E.x2_entry_vectors(by[("A", "S2", "planted", 1.0, None)], HA, HB, nulls, od)
    assert torch.allclose(vA["base"] + 1.0 * vA["delta"], HB[1], atol=1e-5)  # alpha 1 from A lands on B at every position
    vB = E.x2_entry_vectors(by[("B", "S3", "planted", 1.0, None)], HA, HB, nulls, od)
    assert torch.allclose(vB["base"] + vB["delta"], HA[MOCK_LAYER], atol=1e-5)
    v1 = E.x2_entry_vectors(by[("A", "S1", "planted", 2.0, None)], HA, HB, nulls, od)
    assert tuple(v1["base"].shape) == (1, MOCK_D) and abs(v1["dose_abs"] - 2 * float((HB[1][-1] - HA[1][-1]).norm())) < 1e-4
    n2 = E.x2_entry_vectors(by[("A", "S2", "null", 1.0, 0)], HA, HB, nulls, od)
    per_pos = (HB[1] - HA[1]).norm(dim=1)
    assert torch.allclose(n2["delta"].norm(dim=1), per_pos, atol=1e-4)  # null norm matches the planted edit at every position
    n1 = E.x2_entry_vectors(by[("A", "S1", "null", 2.0, 0)], HA, HB, nulls, od)
    assert torch.allclose(n1["delta"][0], n2["delta"][-1], atol=1e-5)  # S1's null direction = S2's at the last position
    n2b = E.x2_entry_vectors(by[("B", "S2", "null", 1.0, 0)], HA, HB, nulls, od)
    assert torch.allclose(n2b["delta"], -n2["delta"], atol=1e-5)  # mirror for the other source
    no = E.x2_entry_vectors(by[("A", "S1", "null_other", 2.0, 1)], HA, HB, nulls, od)
    u = od["xown-04"] / od["xown-04"].norm() if by[("A", "S1", "null_other", 2.0, 1)]["other_pair_id"] == "xown-04" else None
    assert abs(float(no["delta"].norm()) - float(per_pos[-1])) < 1e-4 and (u is None or abs(abs(float(no["delta"][0] @ u)) - float(per_pos[-1])) < 1e-3)
    assert E.x2_entry_vectors(by[("A", "nat", "natural", 0.0, None)], HA, HB, nulls, od)["base"] is None
    assert E.X2Nulls(5).sign_iso == nulls.sign_iso and torch.allclose(E.X2Nulls(5).iso_direction(2, T, MOCK_D), nulls.iso_direction(2, T, MOCK_D))


def test_first_token_candidates_unscorable():
    ft = E.first_token_candidates(FakeTok(), "Ab", "Ac")  # char-level: every spelling starts with the same token
    assert ft["unscorable"] is True and ft["first_A"] is None
    assert E.first_token_candidates(FakeTok(), "Mira", "Leo")["form"] == "bare"


# ================================================================== collector on tmp paths
def test_x2_collect_end_to_end(target, tmp_path, monkeypatch):
    monkeypatch.setattr(C, "FROZEN_CANDIDATES", (tmp_path / "none.json",))
    items = items_x()
    pairs = X.x2_pairs(items, n_pairs=32)
    assert [p["pair_id"] for p in pairs] == ["xown-02", "xown-03", "xown-04", "xmap-02", "xmap-03"]
    assert [p["pair_id"] for p in X.x2_pairs(items, n_pairs=2)] == ["xown-02", "xown-03", "xmap-02", "xmap-03"]
    fd, rv, beh, lo, led, log, sk = (tmp_path / f for f in ("full", "readvecs", "beh.jsonl", "lo.jsonl", "c.jsonl", "log.md", "skipped.json"))
    usable, skipped = X.ensure_full_states(target, pairs, full_dir=fd, ledger_path=led, log_path=log, skipped_path=sk)
    assert len(usable) == 5 and skipped == [] and json.loads(sk.read_text())["n_skipped"] == 0
    full = torch.load(fd / "xown-02A.pt")
    assert set(full["layers"]) == {1, MOCK_LAYER} and full["layers"][1].dtype == torch.bfloat16 and full["n_tokens"] == full["layers"][1].shape[0]
    assert X.ensure_full_states(target, pairs, full_dir=fd, ledger_path=led, log_path=log, skipped_path=sk)[0] == usable  # idempotent
    # an unequal-length pair is skipped and recorded
    bad = dict(pairs[0], pair_id="xown-09", A=mk_item("xown-09A", "xown-09", "A", "ownership", "A has the key. Who?", "A", "B"),
               B=mk_item("xown-09B", "xown-09", "B", "ownership", "B has the key, really. Who?", "B", "A"))
    u2, s2 = X.ensure_full_states(target, [bad], full_dir=fd, ledger_path=led, log_path=log, skipped_path=sk)
    assert u2 == [] and s2[0]["pair_id"] == "xown-09" and json.loads(sk.read_text())["n_skipped"] == 1
    others = X.other_pair_ids(pairs[0], usable)
    assert len(others) == 2 and set(others) <= {"xown-03", "xown-04"} and X.other_pair_ids(pairs[0], usable) == others
    n = X.collect_behaviour(target, usable, sites=("S1", "S2", "S3"), beh_path=beh, readvec_dir=rv, full_dir=fd, ledger_path=led, log_path=log,
                            max_new_tokens=3, batch=4)
    # 74 per pair with 4 other pairs; here ownership has 2 others (2 x 2 null_other), mapping 1 other (2 x 1)
    assert n == 3 * (74 - 8 + 4) + 2 * (74 - 8 + 2)
    assert sum(1 for r in A.read_jsonl(beh) if r["condition"] == "null_other") == 3 * 4 + 2 * 2
    rows = A.read_jsonl(beh)
    assert len(rows) == n and len({r["key"] for r in rows}) == n
    r = rows[0]
    for k in ("key", "pair_id", "family", "source", "site", "edit_layer", "positions_kind", "alpha", "condition", "null_k", "cand_A", "cand_B", "answer_text",
              "parsed", "flipped_to_other", "kept_original", "coherent", "lo_model", "dose_abs", "wall_s", "frozen_code_sha256", "current_code_sha256"):
        assert k in r, k
    assert all((rv / f"{E.x2_key_safe(r['key'])}.pt").exists() for r in rows)
    nat = [r for r in rows if r["condition"] == "natural"]
    assert len(nat) == 10 and all(r["site"] == "nat" and r["alpha"] == 0.0 and r["n_hook_edits"] == 0 for r in nat)
    s3 = [r for r in rows if r["site"] == "S3" and r["condition"] == "planted" and r["alpha"] == 1.0 and r["source"] == "A" and r["pair_id"] == "xown-02"][0]
    # at S3 alpha 1 from A the read vector is h_B (block output at the last position)
    hB = torch.load(fd / "xown-02B.pt")["layers"][MOCK_LAYER][-1].float()
    assert torch.allclose(X.load_readvec(s3["key"], rv), hB, atol=5e-2)
    own = [r for r in rows if r["pair_id"] == "xown-02" and r["source"] == "A"]
    assert all(r["cand_A"] == "A" and r["cand_B"] == "B" and r["lo_model"] is not None and r["lo_model_form"] == "bare" for r in own)
    assert X.collect_behaviour(target, usable, beh_path=beh, readvec_dir=rv, full_dir=fd, ledger_path=led, log_path=log, max_new_tokens=3) == 0
    # readers' LO on the read vectors (+ resumable)
    torch.manual_seed(1)
    J = {MOCK_LAYER: torch.eye(MOCK_D) + torch.randn(MOCK_D, MOCK_D) / 10}
    jl = R.JLensReader().bind_tensors(J, M.unembed_weight(target.model), target.tokenizer)
    ol = R.OLensReader(max_new_tokens=4); ol.target = target
    for rd in (jl, ol):
        assert X.collect_lo(rd, beh_path=beh, lo_path=lo, readvec_dir=rv, ledger_path=led, log_path=log, batch=8) == n
    assert X.collect_lo(ol, beh_path=beh, lo_path=lo, readvec_dir=rv, ledger_path=led, log_path=log) == 0
    lrows = A.read_jsonl(lo)
    assert len(lrows) == 2 * n and {r["reader"] for r in lrows} == {"jlens", "olens"}
    q = lrows[0]
    assert q["key"].startswith("jlens|") and q["entry_key"] in {r["key"] for r in rows} and abs(q["lo_toward_other"] + q["lo_own"]) < 1e-9
    steps = {x["step"] for x in A.read_jsonl(led)}
    assert {"x2_capture_full", "x2_behaviour_S1", "x2_behaviour_S2", "x2_behaviour_S3", "x2_behaviour_nat", "x2_lo_jlens", "x2_lo_olens"} <= steps
    # analyze runs on the mock output (no claims about the numbers)
    out = tmp_path / "res"
    s = XA.main(["--behaviour", str(beh), "--lo", str(lo), "--out", str(out), "--allow-unfrozen", "--n-boot", "20", "--frozen-config", str(tmp_path / "nofreeze.json")])
    assert set(s["by_site"]) == {"S1", "S2", "S3"} and (out / "summary.json").exists() and (out / "fig_main.png").exists() and (out / "fig_flips.png").exists()


# ================================================================== (iv) analyze on synthetic rows
def synthetic(tmp_path, n_pairs=20, seed=0):
    """A model that flips at alpha >= 0.5 (S2/S3) / 2 (S1); reader 'olens' tracks lo_model, 'nla' is flat, 'jlens' moves before the model."""
    rng = np.random.default_rng(seed)
    beh, lo = [], []
    for i in range(n_pairs):
        pid = f"xown-{i + 2:02d}"
        tab = E.x2_condition_table(pid, "ownership", other_pair_ids=[f"xown-{(i + 3) % n_pairs + 2:02d}"] * 4, seed=i)
        for e in tab:
            a, site, cond = e["alpha"], e["site"], e["condition"]
            scale = 2.0 if site == "S1" else 0.5  # ratio r = a / scale; the model plateaus to r = 0.5, then rises 4 nats per unit r
            if cond == "planted":
                lom = -3 + max(0.0, 4.0 * (a / scale - 0.5))
            elif cond == "natural":
                lom = -3
            else:
                lom = -3 + rng.normal(0, 0.3)
            flipped = lom > 0
            beh.append({**{k: e[k] for k in ("key", "pair_id", "family", "source", "site", "edit_layer", "positions_kind", "alpha", "condition", "null_k", "sign", "other_pair_id")},
                        "cand_A": "A", "cand_B": "B", "answer_text": "B" if flipped else "A", "parsed": "B" if flipped else "A", "flipped_to_other": flipped,
                        "kept_original": not flipped, "coherent": True, "lo_model": lom, "dose_abs": a})
            noise = rng.normal(0, 0.2, 3)
            vals = {"olens": lom + noise[0],                                   # tracks the model (null shifts = zero-mean noise)
                    "nla": 0.1,                                                # flat: identical on every entry
                    "jlens": (-3 + 6 * min(1.0, a / (scale / 2)) if cond == "planted" else (-3 if cond == "natural" else -3 + rng.normal(0, 0.3))) + noise[2]}
            for rd, v in vals.items():
                lo.append({"key": f"{rd}|{e['key']}", "entry_key": e["key"], "reader": rd, "lo_toward_other": float(v), "unscorable": False,
                           "pair_id": pid, "site": site, "alpha": a, "condition": cond})
    tmp_path.mkdir(parents=True, exist_ok=True)
    bp, lp = tmp_path / "beh.jsonl", tmp_path / "lo.jsonl"
    bp.write_text("\n".join(json.dumps(r) for r in beh) + "\n"); lp.write_text("\n".join(json.dumps(r) for r in lo) + "\n")
    return bp, lp


def test_analyze_classifies_synthetic_readers(tmp_path):
    bp, lp = synthetic(tmp_path)
    out = tmp_path / "res"
    s = XA.main(["--behaviour", str(bp), "--lo", str(lp), "--out", str(out), "--allow-unfrozen", "--n-boot", "50", "--frozen-config", str(tmp_path / "nofreeze.json")])
    S2 = s["by_site"]["S2"]
    assert S2["E4_flip_by_alpha"]["1.0"]["flip"]["p"] == 1.0 and S2["E4_flip_by_alpha"]["0.25"]["flip"]["p"] == 0.0 and S2["E4_flip_by_alpha"]["1.0"]["coherence_flag"] is False
    assert S2["E5_alpha_star"]["n_with_alpha_star"] == 40 and S2["E5_alpha_star"]["median_alpha_star"] == 0.75
    assert S2["E6_subflip_dose"]["n_items_with_subflip_dose"] >= 36 and set(S2["E6_subflip_dose"]["per_item"].values()) <= {0.25, None}
    assert S2["readers"]["olens"]["E6_null_win"]["p"] < 0.1 and 0.4 < S2["readers"]["olens"]["E6_null_shift_positive"]["p"] < 0.6
    assert S2["K5"]["pairs_with_alpha_star_le_1_any_source"] == 20 and S2["K5"]["killed"] is False
    assert S2["readers"]["olens"]["verdict"] == "TRACKS" and S2["readers"]["nla"]["verdict"] == "INSENSITIVE"
    assert S2["readers"]["jlens"]["verdict"] == "SUB-FLIP" and S2["readers"]["jlens"]["flags"]["subflip"]
    g = S2["readers"]["olens"]["E7_gain_ratio"]
    assert 0.8 < g["slope"] < 1.2 and g["lo"] <= g["slope"] <= g["hi"]
    assert abs(S2["readers"]["nla"]["E7_gain_ratio"]["slope"]) < 0.2
    assert s["by_site"]["S1"]["E5_alpha_star"]["median_alpha_star"] == 3.0 and s["classification"]["S3"]["olens"] == "TRACKS"
    assert (out / "flips.csv").exists() and (out / "follow.csv").exists() and (out / "fig_main.png").exists() and (out / "fig_flips.png").exists()
    fl = (out / "flips.csv").read_text()
    assert "null_other" in fl and "S1" in fl
    # K5: too few pairs -> UNDERPOWERED at S2 only
    bp2, lp2 = synthetic(tmp_path / "small", 4)
    s2 = XA.main(["--behaviour", str(bp2), "--lo", str(lp2), "--out", str(tmp_path / "res2"), "--allow-unfrozen", "--n-boot", "20", "--no-fig",
                  "--frozen-config", str(tmp_path / "nofreeze.json")])
    assert s2["by_site"]["S2"]["K5"]["killed"] is True and s2["classification"]["S2"]["olens"] == "UNDERPOWERED" and s2["classification"]["S3"]["olens"] == "TRACKS"


def test_zz_results_and_cache_untouched():
    now = sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*"))
    assert now == RESULTS_SNAPSHOT
    cache = sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None
    assert cache == CACHE_SNAPSHOT
