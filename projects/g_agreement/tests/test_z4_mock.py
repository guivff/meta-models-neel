"""MOCK tests (CPU) for Phase Z4: the position subsample rule, planned-decode count + cap (single-stage printout unchanged; the
dependent stage's full-run table after the 2026-10-09 deviation), the restore / pair2 draws, the entry vectors (single / all_except /
restore / rand_single / pair2), the row-wise batched decode against core's batch, the collector end to end on the tiny model (stage
single then dependent, tmp paths) and analyze.py on synthetic rows for every classification outcome (SINGLE CAUSAL, REDUNDANT via a
position pair, JOINT, UNDETERMINED without pair2 rows) with the original all-except rule as the secondary label. Nothing is written
under results/ or cache/.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_z4_mock.py -q``
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
from projects.g_agreement.tests.test_x2_mock import MOCK_SITES, items_x  # noqa: E402
from projects.g_agreement.x2_causal import collect as X  # noqa: E402
from projects.g_agreement.z4_positions import analyze as ZA  # noqa: E402
from projects.g_agreement.z4_positions import collect as Z  # noqa: E402

RESULTS_SNAPSHOT = sorted(str(p) for p in (REPO / "results" / "g_agreement" / "z4").rglob("*")) if (REPO / "results" / "g_agreement" / "z4").exists() else None
CACHE_SNAPSHOT = sorted(str(p) for p in (REPO / "cache" / "g_agreement" / "z").rglob("*")) if (REPO / "cache" / "g_agreement" / "z").exists() else None
MOCK_EDIT = 1


@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    monkeypatch.setattr(C, "LAYER", MOCK_LAYER)
    monkeypatch.setattr(C, "HIDDEN_STATES_INDEX", MOCK_LAYER + 1)
    monkeypatch.setattr(C, "D_MODEL", MOCK_D)
    monkeypatch.setattr(C, "N_LAYERS", 4)
    monkeypatch.setattr(E, "X2_SITES", MOCK_SITES)
    monkeypatch.setattr(E, "X2_EDIT_LAYERS", (MOCK_EDIT, MOCK_LAYER))
    monkeypatch.setattr(E, "X2_READ_LAYER", MOCK_LAYER)
    monkeypatch.setattr(Z, "Z4_EDIT_LAYER", MOCK_EDIT)
    yield


@pytest.fixture(scope="module")
def target():
    return M.Target(model=tiny_model(), tokenizer=FakeTok(), device="cpu", model_id="MOCK/tiny", revision="mock", model_class="Qwen3_5ForCausalLM")


def rand_pair(T=12, seed=0, diff=(3, 7)):
    torch.manual_seed(seed)
    HA = {MOCK_EDIT: torch.randn(T, MOCK_D) * 5, MOCK_LAYER: torch.randn(T, MOCK_D) * 5}
    HB = {MOCK_EDIT: HA[MOCK_EDIT] + torch.randn(T, MOCK_D), MOCK_LAYER: HA[MOCK_LAYER] + torch.randn(T, MOCK_D)}
    ids_A = list(range(100, 100 + T))
    ids_B = list(ids_A)
    ids_B[diff[0]], ids_B[diff[1]] = ids_A[diff[1]], ids_A[diff[0]]
    return HA, HB, ids_A, ids_B


# ================================================================== (a) position subsample
def test_position_rule_fixed_positions_and_cap():
    ids_A = list(range(40))
    ids_B = list(ids_A)
    ids_B[7], ids_B[8], ids_B[13], ids_B[14] = ids_A[13], ids_A[14], ids_A[7], ids_A[8]  # two two-token names swapped
    assert Z.question_first_position(ids_A, ids_B) == 15
    P = Z.z4_positions("p", ids_A, ids_B)
    assert len(P["positions"]) == 15 == Z.Z4_MAX_POSITIONS and P["positions"] == sorted(P["positions"]) and len(set(P["positions"])) == 15
    assert {7, 8, 13, 14, 15, 39} <= set(P["positions"]) and P["fixed"] == [7, 8, 13, 14, 15, 39] and P["n_differing"] == 4 and P["question_first"] == 15
    assert P["roles"][7] == P["roles"][14] == "diff" and P["roles"][15] == "question_first" and P["roles"][39] == "last"
    assert Counter(P["roles"].values()) == {"diff": 4, "question_first": 1, "last": 1, "uniform": 9}
    assert Z.z4_positions("p", ids_A, ids_B) == P and Z.z4_positions("q", ids_A, ids_B)["positions"] != P["positions"]  # seeded per pair
    assert Z.z4_positions("p", ids_A, ids_B, seed=1)["positions"] != P["positions"]
    # a short prompt keeps every position; max_positions below the fixed set keeps the fixed set only
    short = Z.z4_positions("p", ids_A[:10], [ids_A[1], ids_A[0]] + ids_A[2:10])
    assert short["positions"] == list(range(10)) and short["question_first"] == 2
    assert Z.z4_positions("p", ids_A, ids_B, max_positions=3)["positions"] == [7, 8, 13, 14, 15, 39]
    with pytest.raises(ValueError):
        Z.z4_positions("p", ids_A, ids_A)
    # the question-first token is the first EQUAL position after the last differing one (a differing last token is excluded)
    ids_C = list(ids_A); ids_C[20] = 999
    assert Z.question_first_position(ids_A, ids_C) == 21
    # with a tokenizer the question-first token skips punctuation-only tokens (the period after the last name) -> the first word of the question
    class Tok:
        def decode(self, ids, skip_special_tokens=True):
            return {15: ".", 16: " Which", 21: " ?", 22: "x"}.get(int(ids[0]), " w")

    assert Z.question_first_position(ids_A, ids_B, Tok()) == 16 and Z.question_first_position(ids_A, ids_C, Tok()) == 22
    Pt = Z.z4_positions("p", ids_A, ids_B, tokenizer=Tok())
    assert Pt["question_first"] == 16 and Pt["roles"][16] == "question_first" and 15 not in Pt["fixed"] and Pt["rule"] == "first equal token after the last differing one with an alphanumeric character"
    assert P["rule"] == "first equal token after the last differing one"
    # rand triples: seeded, without replacement, inside the selected positions
    pos = {"p": P, "q": Z.z4_positions("q", ids_A, ids_B)}
    tr = Z.rand_triples(pos, n=10)
    assert len(tr) == 10 and len(set(tr)) == 10 and all(i in pos[pid]["positions"] and s in ("A", "B") for pid, s, i in tr) and Z.rand_triples(pos, n=10) == tr
    assert len(Z.rand_triples(pos, n=1000)) == 2 * 30


# ================================================================== (b) tables, planned count, cap
def test_tables_planned_decodes_and_cap():
    ids_A = list(range(36)); ids_B = list(ids_A); ids_B[7], ids_B[13] = ids_A[13], ids_A[7]
    pairs = [{"pair_id": f"xown-{i:02d}", "family": "ownership"} for i in range(2, 6)] + [{"pair_id": f"xmap-{i:02d}", "family": "mapping"} for i in range(2, 4)]
    pos = {p["pair_id"]: Z.z4_positions(p["pair_id"], ids_A, ids_B) for p in pairs}
    rand = Z.rand_triples(pos, n=5)
    tabs = Z.build_tables(pairs, pos, stage="single", rand=rand)
    plan = Z.planned_decodes(tabs, dependent_upper=Z.dependent_upper_bound(pairs))
    assert plan["single"] == 6 * 2 * 15 * 2 and plan["rand_single"] == 5 and plan["all_except"] == plan["restore"] == 0
    assert plan["reused"] == 6 * 2 * 2 * 2 and plan["dependent_upper_bound"] == 2 * 2 * 5 * 6 and plan["total_planned"] == 360 + 5 + 120
    t = tabs["xown-02"]
    assert len({e["key"] for e in t}) == len(t) and t[0]["key"].startswith("xown-02|A|Z4|single|0.75|") and all(e["site"] == "Z4" and e["edit_layer"] == Z.Z4_EDIT_LAYER for e in t)
    ro = [e for e in t if e["reused"]]
    assert {e["condition"] for e in ro} == {"name_only", "name_removed"} and {e["alpha"] for e in ro} == {0.75, 1.0}
    assert ro[0]["reused_key"] == f"xown-02|A|Y2|{ro[0]['condition']}|{ro[0]['alpha']}|None" and ro[0]["position"] is None and ro[0]["stage"] == "reused"
    assert all(e["stage"] == "single" for e in t if not e["reused"]) and {e["positions_kind"] for e in t if e["condition"] == "single"} == {"single"}
    # the real design: 64 pairs x <= 15 positions -> 3840 single + 64 rand + <= 1280 dependent = 5184 <= 6500
    real = [{"pair_id": f"p{i}", "family": "ownership" if i < 32 else "mapping"} for i in range(64)]
    rpos = {p["pair_id"]: Z.z4_positions(p["pair_id"], ids_A, ids_B) for p in real}
    rplan = Z.planned_decodes(Z.build_tables(real, rpos, stage="single", rand=Z.rand_triples(rpos, n=64)), dependent_upper=Z.dependent_upper_bound(real))
    assert rplan["total_planned"] == 3840 + 64 + 1280 == 5184 <= Z.Z4_DECODE_CAP
    Z.check_cap(rplan)
    with pytest.raises(SystemExit):
        Z.check_cap(rplan, cap=5000)
    # dependent stage: top positions per family, those beyond the render are dropped; no restore without a draw (deviation (1))
    top = {"ownership": [7, 35, 40], "mapping": [13]}
    tabs_d = Z.build_tables(pairs, pos, stage="dependent", top=top)
    pd = Z.planned_decodes(tabs_d, conditions=Z.Z4_DECODED_CONDITIONS)
    assert pd["single"] == pd["rand_single"] == pd["restore"] == pd["pair2"] == 0 and pd["all_except"] == 4 * 2 * 2 + 2 * 2 * 1 and pd["total_planned"] == 20
    d = [e for e in tabs_d["xown-02"] if not e["reused"]]
    assert {e["position"] for e in d} == {7, 35} and {e["stage"] for e in d} == {"dependent"} and all(e["alpha"] == 1.0 for e in d)
    assert next(e for e in d if e["position"] == 35)["role"] == "last" and all(e["positions_kind"] == "all_except_one" for e in d)
    # with the draws: restore only on the drawn triples, pair2 on the drawn items at its three doses
    draws = Z.dependent_draws(pairs, pos, top, n_restore=3, n_pair2=10)
    assert len([t for t in draws["restore"] if t[0].startswith("xown")]) == 3 and len([t for t in draws["restore"] if t[0].startswith("xmap")]) == 3
    assert all(i in ((7, 35) if pid.startswith("xown") else (13,)) for pid, _, i in draws["restore"]) and draws == Z.dependent_draws(pairs, pos, top, n_restore=3, n_pair2=10)
    assert {(i, j) for _, _, i, j in draws["pair2"]} == {(7, 35)}  # (40 beyond the render, mapping has one top position: no pair)
    tabs_dd = Z.build_tables(pairs, pos, stage="dependent", top=top, restore=draws["restore"], pair2=draws["pair2"])
    pdd = Z.planned_decodes(tabs_dd, conditions=Z.Z4_DECODED_CONDITIONS)
    assert pdd["restore"] == 6 and pdd["all_except"] == 20 and pdd["pair2"] == 3 * 8 and pdd["total_planned"] == 20 + 6 + 24  # 4 own pairs < 10 -> both sources
    e2 = [e for e in tabs_dd["xown-02"] if e["condition"] == "pair2"]
    assert e2 and {e["alpha"] for e in e2} == set(Z.Z4_PAIR2_ALPHAS) and all(e["position"] == "7-35" and e["pair_positions"] == [7, 35] for e in e2)
    assert e2[0]["key"] == f"xown-02|{e2[0]['source']}|Z4|pair2|0.5|7-35" and e2[0]["positions_kind"] == "pair" and e2[0]["stage"] == "dependent"
    assert e2[0]["role"] == "diff+last"
    # stage all = single + dependent + reused
    assert Z.planned_decodes(Z.build_tables(pairs, pos, stage="all", top={"ownership": [7]}, rand=rand))["total_planned"] == 365 + 4 * 2
    # the real design after the deviation: 3840 single + 64 rand + 640 all_except + 600 pair2 + 32 restore = 5176 <= 6500
    rtop = {"ownership": [3, 7, 13, 20, 35], "mapping": [5, 7, 13, 30, 35]}
    rdraws = Z.dependent_draws(real, rpos, rtop)
    full = Z.full_run_plan(real, rpos, top=rtop, rand=Z.rand_triples(rpos, n=64), draws=rdraws)
    assert (full["single"], full["rand_single"], full["all_except"], full["pair2"], full["restore"]) == (3840, 64, 640, 600, 32)
    assert full["total_planned"] == 5176 <= Z.Z4_DECODE_CAP and "pair2" in Z.format_plan_table(full) and "5176" in Z.format_plan_table(full)
    Z.check_cap(full)
    with pytest.raises(SystemExit):
        Z.check_cap(full, cap=5000)


def test_top_positions_rule():
    rows = []
    for fam, rates in (("ownership", {3: (10, 10), 5: (9, 10), 7: (9, 10), 9: (2, 10), 11: (1, 1)}), ("mapping", {2: (3, 4), 4: (1, 4)})):
        for p, (k, n) in rates.items():
            for i in range(n):
                rows.append({"family": fam, "condition": "single", "alpha": 1.0, "position": p, "pair_id": f"p{i}", "flipped_to_other": i < k, "coherent": True})
    rows.append({"family": "ownership", "condition": "single", "alpha": 0.75, "position": 9, "pair_id": "p0", "flipped_to_other": True, "coherent": True})  # other dose ignored
    top = Z.top_positions_by_family(rows, k=3, min_n=4)
    assert top["ownership"]["top"] == [3, 5, 7] and top["ownership"]["min_n_applied"] is True  # 11 (1/1) excluded by min_n; ties by index
    assert top["mapping"]["top"] == [2, 4] and top["mapping"]["min_n_applied"] is False  # fewer than k qualify -> all ranked
    assert Z.top_positions_by_family(rows, k=5, min_n=1)["ownership"]["top"] == [3, 11, 5, 7, 9]  # 3 and 11 tie at 1.0 -> lower index first
    # incoherent flips do not count
    rows2 = [dict(r, coherent=False) for r in rows if r["family"] == "ownership"]
    assert all(t["k"] == 0 for t in Z.top_positions_by_family(rows2, k=3, min_n=1)["ownership"]["table"])


def test_dependent_draws_restore_and_pair2():
    """Deviation 2026-10-09: restore = 16 determinism triples per family from the all_except table; pair2 = C(5,2) pairs × 10 items per
    family, seeded by C.stable_seed("z4", "pair2", family, 0), sources 5/5, eligibility = both positions inside the render."""
    import itertools

    pairs, pos = [], {}
    for i in range(64):
        fam = "ownership" if i < 32 else "mapping"
        pid = f"{'xown' if i < 32 else 'xmap'}-{i:02d}"
        T = 23 + (i % 14)
        ids_A = list(range(T)); ids_B = list(ids_A); ids_B[3], ids_B[9] = ids_A[9], ids_A[3]
        pairs.append({"pair_id": pid, "family": fam})
        pos[pid] = Z.z4_positions(pid, ids_A, ids_B)
    top = {"ownership": [9, 3, 30, 12, 22], "mapping": [3, 9, 12, 14, 20]}
    assert Z.pair2_seed("ownership") == C.stable_seed("z4", "pair2", "ownership", 0)
    rs = Z.restore_draw(pairs, pos, top)
    assert len(rs) == 32 and len(set(rs)) == 32 and sum(1 for t in rs if t[0].startswith("xown")) == 16
    assert all(i in top["ownership" if pid.startswith("xown") else "mapping"] and i < pos[pid]["n_tokens"] for pid, _, i in rs)
    assert Z.restore_draw(pairs, pos, top) == rs and Z.restore_draw(pairs, pos, top, seed=1) != rs
    p2 = Z.pair2_draw(pairs, pos, top)
    assert len(p2) == 2 * 10 * 10 and len(set(p2)) == len(p2)
    for fam in ("ownership", "mapping"):
        for i, j in itertools.combinations(sorted(top[fam]), 2):
            it = [(pid, src) for pid, src, a, b in p2 if (a, b) == (i, j) and ((pid.startswith("xown")) == (fam == "ownership"))]
            assert len(it) == 10 and len({pid for pid, _ in it}) == 10, (fam, i, j)
            assert sum(src == "A" for _, src in it) == 5 and all(pos[pid]["n_tokens"] > j for pid, _ in it)
    # position pairs every prompt can host share the same items (one permutation per family) -> paired across pairs
    items = lambda pre, i, j: [(pid, src) for pid, src, a, b in p2 if (a, b) == (i, j) and pid.startswith(pre)]
    assert items("xmap", 3, 9) == items("xmap", 3, 12) == items("xmap", 9, 14) and items("xown", 3, 9) == items("xown", 9, 12)
    assert items("xown", 3, 9) != items("xown", 9, 30)  # 30 excludes the short prompts
    assert Z.pair2_draw(pairs, pos, top) == p2 and Z.pair2_draw(pairs, pos, top, seed=1) != p2
    # fewer eligible pairs than items: both sources of each eligible pair (balanced, truncated)
    few = Z.pair2_draw(pairs[:3], {k: pos[k] for k in ("xown-00", "xown-01", "xown-02")}, {"ownership": [3, 9]})
    assert len(few) == 6 and sorted(src for _, src, _, _ in few) == ["A"] * 3 + ["B"] * 3
    assert Z.pair2_draw(pairs, pos, {"ownership": [3], "mapping": []}) == []
    assert Z.pair_label(9, 3) == "3-9" and Z.parse_pair_label("3-9") == (3, 9)


# ================================================================== (c) entry vectors
def test_entry_vectors_geometry():
    HA, HB, ids_A, ids_B = rand_pair()
    T = len(ids_A)
    P = Z.z4_positions("p", ids_A, ids_B)
    tab = Z.z4_condition_table("p", "ownership", P, stage="all", top_positions=[7], rand=[("p", "A", 3), ("p", "B", 7)],
                               restore=[("p", "A", 7), ("p", "B", 7)], pair2=[("p", "A", 3, 7), ("p", "B", 7, T - 1)])
    by = {(e["source"], e["condition"], e["alpha"], e["position"]): e for e in tab}
    D = HB[MOCK_EDIT] - HA[MOCK_EDIT]
    # single: only position i, alpha 1 from A lands on B there; mirror from B
    s = Z.z4_entry_vectors(by[("A", "single", 1.0, 7)], HA, HB, layer=MOCK_EDIT)
    assert s["positions"] == [7] and s["n_positions"] == 1 and torch.allclose(s["base"] + s["delta"], HB[MOCK_EDIT][[7]], atol=1e-5)
    assert s["delta_pos"] == pytest.approx(float(D[7].norm())) and s["dose_abs"] == pytest.approx(float(D[7].norm())) and s["last_edited"] is False
    assert s["input_norm_last"] == pytest.approx(float(HA[MOCK_EDIT][-1].norm()))
    s75 = Z.z4_entry_vectors(by[("A", "single", 0.75, 7)], HA, HB, layer=MOCK_EDIT)
    assert torch.allclose(s75["base"] + 0.75 * s75["delta"], HA[MOCK_EDIT][[7]] + 0.75 * D[[7]], atol=1e-5) and s75["dose_abs"] == pytest.approx(0.75 * float(D[7].norm()))
    sB = Z.z4_entry_vectors(by[("B", "single", 1.0, 7)], HA, HB, layer=MOCK_EDIT)
    assert torch.allclose(sB["delta"], -s["delta"], atol=1e-6) and torch.allclose(sB["base"] + sB["delta"], HA[MOCK_EDIT][[7]], atol=1e-5)
    sl = Z.z4_entry_vectors(by[("A", "single", 1.0, T - 1)], HA, HB, layer=MOCK_EDIT)
    assert sl["last_edited"] is True and sl["input_norm_last"] == pytest.approx(float(HB[MOCK_EDIT][-1].norm()), rel=1e-4)
    # all_except: every position but 7; at alpha 1 those equal B, 7 is untouched
    ae = Z.z4_entry_vectors(by[("A", "all_except", 1.0, 7)], HA, HB, layer=MOCK_EDIT)
    assert ae["positions"] == [j for j in range(T) if j != 7] and ae["n_positions"] == T - 1 and torch.allclose(ae["base"] + ae["delta"], HB[MOCK_EDIT][ae["positions"]], atol=1e-5)
    # restore: all positions, equals the full swap except position 7 which is the own state
    rs = Z.z4_entry_vectors(by[("A", "restore", 1.0, 7)], HA, HB, layer=MOCK_EDIT)
    v = rs["base"] + rs["delta"]
    assert rs["positions"] == list(range(T)) and torch.allclose(v[7], HA[MOCK_EDIT][7], atol=1e-5)
    keep = [j for j in range(T) if j != 7]
    assert torch.allclose(v[keep], HB[MOCK_EDIT][keep], atol=1e-5) and torch.allclose(rs["base"], HB[MOCK_EDIT], atol=1e-6) and float(rs["delta"][keep].abs().max()) == 0.0
    # restore from B mirrors: full swap to A, position 7 stays B
    rsB = Z.z4_entry_vectors(by[("B", "restore", 1.0, 7)], HA, HB, layer=MOCK_EDIT)
    vB = rsB["base"] + rsB["delta"]
    assert torch.allclose(vB[7], HB[MOCK_EDIT][7], atol=1e-5) and torch.allclose(vB[keep], HA[MOCK_EDIT][keep], atol=1e-5)
    # restore(A) and all_except(A) agree at alpha 1 on the whole sequence (same block state)
    full = HA[MOCK_EDIT].clone(); full[ae["positions"]] = ae["base"] + ae["delta"]
    assert torch.allclose(full, v, atol=1e-5)
    # rand_single: one position, norm-matched, seeded, random direction (not the swap direction)
    rd = Z.z4_entry_vectors(by[("A", "rand_single", 1.0, 3)], HA, HB, layer=MOCK_EDIT)
    assert rd["positions"] == [3] and float(rd["delta"].norm()) == pytest.approx(float(D[3].norm()), rel=1e-5) and abs(rd["cos_to_u_pos"]) < 0.6
    assert rd["rand_seed"] == Z.rand_dir_seed("p", "A", 3) and torch.equal(Z.z4_entry_vectors(by[("A", "rand_single", 1.0, 3)], HA, HB, layer=MOCK_EDIT)["delta"], rd["delta"])
    rdB = Z.z4_entry_vectors(by[("B", "rand_single", 1.0, 7)], HA, HB, layer=MOCK_EDIT)
    assert rdB["rand_seed"] != rd["rand_seed"] and float(rdB["delta"].norm()) == pytest.approx(float(D[7].norm()), rel=1e-5)
    # pair2: exactly the two positions; α 1 from A lands on B at both; the mirror from B lands on A; Frobenius norms
    p2 = Z.z4_entry_vectors(by[("A", "pair2", 1.0, "3-7")], HA, HB, layer=MOCK_EDIT)
    assert p2["positions"] == [3, 7] and p2["n_positions"] == 2 and torch.allclose(p2["base"] + p2["delta"], HB[MOCK_EDIT][[3, 7]], atol=1e-5)
    assert p2["delta_pos"] == pytest.approx(float(D[[3, 7]].norm())) and p2["dose_abs"] == pytest.approx(float(D[[3, 7]].norm())) and p2["last_edited"] is False
    p2h = Z.z4_entry_vectors(by[("A", "pair2", 0.5, "3-7")], HA, HB, layer=MOCK_EDIT)
    assert torch.allclose(p2h["base"] + 0.5 * p2h["delta"], HA[MOCK_EDIT][[3, 7]] + 0.5 * D[[3, 7]], atol=1e-5)
    p2B = Z.z4_entry_vectors(by[("B", "pair2", 1.0, f"7-{T - 1}")], HA, HB, layer=MOCK_EDIT)
    assert torch.allclose(p2B["base"] + p2B["delta"], HA[MOCK_EDIT][[7, T - 1]], atol=1e-5) and p2B["last_edited"] is True
    assert {e["position"] for e in tab if e["condition"] == "pair2"} == {"3-7", f"7-{T - 1}"} and len([e for e in tab if e["condition"] == "pair2"]) == 2 * 3
    assert len([e for e in tab if e["condition"] == "restore"]) == 2
    with pytest.raises(ValueError):
        Z.z4_entry_vectors(dict(by[("A", "pair2", 1.0, "3-7")], position=f"3-{T}"), HA, HB, layer=MOCK_EDIT)
    with pytest.raises(ValueError):
        Z.z4_entry_vectors(dict(by[("A", "pair2", 1.0, "3-7")], position="7-7"), HA, HB, layer=MOCK_EDIT)
    with pytest.raises(ValueError):
        Z.z4_entry_vectors(dict(by[("A", "single", 1.0, 7)], position=T), HA, HB, layer=MOCK_EDIT)
    with pytest.raises(ValueError):
        Z.z4_entry_vectors(dict(by[("A", "single", 1.0, 7)], condition="bogus"), HA, HB, layer=MOCK_EDIT)


# ================================================================== (d) row-wise batched decode == core batch
def test_rowwise_batch_matches_core(target):
    ids = M.render_item(target.tokenizer, "A has the key. B has the pen. Who has the key? Name only.")
    T = len(ids)
    base = E.capture_full(target, ids, [MOCK_EDIT])[MOCK_EDIT]
    torch.manual_seed(3)
    delta = torch.randn(T, MOCK_D) * 3
    cft = (ord("A"), ord("B"))
    # one row with positions {5}: core vs rowwise
    core = E.generate_with_interpolated_batch(target, ids, MOCK_EDIT, [5], (base[[5]] + delta[[5]])[None], read_layer=MOCK_LAYER, max_new_tokens=3, cand_first_tokens=cft)[0]
    rw = Z.generate_with_rowwise_positions(target, ids, MOCK_EDIT, [[5]], [base[[5]] + delta[[5]]], read_layer=MOCK_LAYER, max_new_tokens=3, cand_first_tokens=cft)[0]
    assert torch.allclose(core["read_vec"], rw["read_vec"], atol=1e-4) and abs(core["lo_model"] - rw["lo_model"]) < 1e-4 and core["answer_text"] == rw["answer_text"]
    assert rw["n_hook_edits"] == 1 and rw["n_read_hits"] == 1 and rw["positions"] == [5] and rw["batch_size"] == 1
    # a batch with different position sets per row: each row matches its own single-row call
    rowsets = [[2], [9], [j for j in range(T) if j != 4], list(range(T))]
    vecs = [base[ps] + delta[ps] for ps in rowsets]
    rows = Z.generate_with_rowwise_positions(target, ids, MOCK_EDIT, rowsets, vecs, read_layer=MOCK_LAYER, max_new_tokens=3, cand_first_tokens=cft)
    assert len(rows) == 4 and all(r["batch_size"] == 4 for r in rows)
    for ps, v, r in zip(rowsets, vecs, rows):
        one = E.generate_with_interpolated_batch(target, ids, MOCK_EDIT, ps, v[None], read_layer=MOCK_LAYER, max_new_tokens=3, cand_first_tokens=cft)[0]
        assert torch.allclose(one["read_vec"], r["read_vec"], atol=1e-3) and abs(one["lo_model"] - r["lo_model"]) < 1e-3
    assert not torch.allclose(rows[0]["read_vec"], rows[3]["read_vec"], atol=1e-2)  # different edits, different reads
    assert len(M.blocks(target.model)[MOCK_EDIT]._forward_hooks) == 0 and len(M.blocks(target.model)[MOCK_LAYER]._forward_hooks) == 0
    with pytest.raises(ValueError):
        Z.generate_with_rowwise_positions(target, ids, MOCK_EDIT, [[1, 2]], [base[[1]]], read_layer=MOCK_LAYER, max_new_tokens=2)


# ================================================================== (e) collector end to end: stage single, then dependent
def _fake_x2_y2(tmp_path, usable, lengths):
    """X2 natural + S2 α1 rows and Y2 name rows for the mock pairs (what analyze needs besides the Z4 files)."""
    x2rows, x2lo, y2rows, y2lo = [], [], [], []
    for p in usable:
        for src in ("A", "B"):
            it = p[src]
            ca, cb = it["primary"]["answer"], X.other_candidate(it)
            base = {"pair_id": p["pair_id"], "family": p["family"], "source": src, "cand_A": ca, "cand_B": cb, "coherent": True}
            x2rows.append({**base, "key": f"{p['pair_id']}|{src}|nat|natural|0.0|None", "site": "nat", "condition": "natural", "alpha": 0.0, "null_k": None, "parsed": ca,
                           "flipped_to_other": False, "kept_original": True, "lo_model": -2.0})
            x2rows.append({**base, "key": f"{p['pair_id']}|{src}|S2|planted|1.0|None", "site": "S2", "condition": "planted", "alpha": 1.0, "null_k": None, "parsed": cb,
                           "flipped_to_other": True, "kept_original": False, "lo_model": 3.0})
            for cond in ("name_only", "name_removed"):
                for a in (0.5, 0.75, 1.0):
                    y2rows.append({**base, "key": f"{p['pair_id']}|{src}|Y2|{cond}|{a}|None", "site": "Y2", "condition": cond, "alpha": a, "k": None, "parsed": cb if cond == "name_removed" else ca,
                                   "flipped_to_other": cond == "name_removed", "kept_original": cond != "name_removed", "lo_model": 2.0 if cond == "name_removed" else -2.0})
    for rows, lo in ((x2rows, x2lo), (y2rows, y2lo)):
        for r in rows:
            for rd in ("jlens", "olens"):
                v = -1.0 if r["condition"] == "natural" else 1.0
                lo.append({"key": f"{rd}|{r['key']}", "entry_key": r["key"], "reader": rd, "lo_toward_other": v, "unscorable": False})
    paths = {}
    for name, rows in (("x2b", x2rows), ("x2l", x2lo), ("y2b", y2rows), ("y2l", y2lo)):
        paths[name] = tmp_path / f"{name}.jsonl"
        paths[name].write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return paths


def test_z4_collect_end_to_end(target, tmp_path, monkeypatch):
    monkeypatch.setattr(C, "FROZEN_CANDIDATES", (tmp_path / "none.json",))
    pairs = X.x2_pairs(items_x(), n_pairs=32)
    fd, rv, beh, lo, led, log, sk = (tmp_path / f for f in ("full", "readvecs", "beh.jsonl", "lo.jsonl", "c.jsonl", "log.md", "skipped.json"))
    usable, skipped = X.ensure_full_states(target, pairs, full_dir=fd, ledger_path=led, log_path=log, skipped_path=sk)
    assert len(usable) == 5 and not skipped
    positions = Z.build_positions(usable, fd, max_positions=6, tokenizer=target.tokenizer)
    lengths = {pid: P["n_tokens"] for pid, P in positions.items()}
    for pid, P in positions.items():
        assert len(P["positions"]) == 6 and P["n_tokens"] - 1 in P["positions"] and P["question_first"] in P["positions"] and P["n_differing"] == (2 if pid.startswith("xown") else 3)
        idsA, idsB = torch.load(fd / f"{pid}A.pt")["ids"], torch.load(fd / f"{pid}B.pt")["ids"]
        assert set(E.differing_positions(idsA, idsB)) <= set(P["positions"])
    summ = Z.positions_summary(positions)
    assert summ["pairs"] == 5 and summ["positions_total"] == 30 and summ["roles"]["diff"] == 3 * 2 + 2 * 3 and summ["roles"]["last"] == 5
    rand = Z.rand_triples(positions, n=4)
    # ---- stage single
    tabs = Z.build_tables(usable, positions, stage="single", rand=rand)
    plan = Z.planned_decodes(tabs, dependent_upper=Z.dependent_upper_bound(usable, k=2))
    assert plan["single"] == 5 * 2 * 6 * 2 == 120 and plan["rand_single"] == 4 and plan["reused"] == 5 * 8 and plan["dependent_upper_bound"] == 2 * 2 * 2 * 5
    y2b = tmp_path / "y2_partial.jsonl"  # only xown-02's reused keys exist -> the log counts the missing ones
    y2b.write_text("\n".join(json.dumps({"key": e["reused_key"]}) for e in tabs["xown-02"] if e["reused"]) + "\n")
    n = Z.collect_behaviour(target, usable, tabs, beh_path=beh, readvec_dir=rv, full_dir=fd, ledger_path=led, log_path=log, max_new_tokens=3, batch=5,
                            edit_layer=MOCK_EDIT, read_layer=MOCK_LAYER, y2_beh_path=y2b)
    assert n == 124
    rows = A.read_jsonl(beh)
    assert len(rows) == n and len({r["key"] for r in rows}) == n and Counter(r["condition"] for r in rows) == {"single": 120, "rand_single": 4}
    assert all((rv / f"{E.x2_key_safe(r['key'])}.pt").exists() for r in rows)
    r0 = rows[0]
    for k in ("key", "pair_id", "family", "source", "site", "edit_layer", "stage", "condition", "position", "role", "rel_position", "positions_kind", "n_positions", "alpha",
              "cand_A", "cand_B", "answer_text", "parsed", "flipped_to_other", "kept_original", "coherent", "lo_model", "dose_abs", "delta_pos", "wall_s", "rand_seed",
              "cos_to_u_pos", "frozen_code_sha256", "current_code_sha256", "reused", "n_tokens"):
        assert k in r0, k
    assert all(r["site"] == "Z4" and r["edit_layer"] == MOCK_EDIT and r["read_layer"] == MOCK_LAYER and r["n_hook_edits"] >= 1 and r["n_positions"] == 1 and r["stage"] == "single" for r in rows)
    assert all(r["positions"] == [r["position"]] and r["rel_position"] == r["position"] - r["n_tokens"] for r in rows)
    assert all(r["role"] == positions[r["pair_id"]]["roles"][r["position"]] for r in rows)
    assert all(r["cand_A"] == "A" and r["cand_B"] == "B" and r["lo_model"] is not None for r in rows if r["pair_id"] == "xown-02" and r["source"] == "A")
    assert all(r["rand_seed"] is not None and r["alpha"] == 1.0 for r in rows if r["condition"] == "rand_single") and all(r["rand_seed"] is None for r in rows if r["condition"] == "single")
    assert Z.collect_behaviour(target, usable, tabs, beh_path=beh, readvec_dir=rv, full_dir=fd, ledger_path=led, log_path=log, max_new_tokens=3,
                               edit_layer=MOCK_EDIT, read_layer=MOCK_LAYER, y2_beh_path=y2b) == 0  # resumable
    logtxt = log.read_text()
    assert f"{5 * 8} name_only/name_removed entries reused" in logtxt and f"({4 * 8} MISSING" in logtxt
    # the recorded lo_model equals a direct single-row core decode of the same edit
    r = next(x for x in rows if x["condition"] == "single" and x["pair_id"] == "xown-02" and x["source"] == "A" and x["alpha"] == 1.0)
    H = {v: X.load_full(f"xown-02{v}", fd) for v in ("A", "B")}
    e = next(x for x in tabs["xown-02"] if x["key"] == r["key"])
    v = Z.z4_entry_vectors(e, H["A"]["layers"], H["B"]["layers"], layer=MOCK_EDIT)
    one = E.generate_with_interpolated_batch(target, H["A"]["ids"], MOCK_EDIT, v["positions"], (v["base"] + v["delta"])[None], read_layer=MOCK_LAYER, max_new_tokens=3,
                                             cand_first_tokens=(ord("A"), ord("B")))[0]
    assert abs(one["lo_model"] - r["lo_model"]) < 1e-3 and torch.allclose(one["read_vec"].to(torch.bfloat16).float(), X.load_readvec(r["key"], rv), atol=5e-2)
    # ---- stage dependent (top-2 per family from the single rows): all_except + pair2 (1 position pair per family) + restore (3/family)
    top = Z.top_positions_by_family(rows, k=2, min_n=1)
    assert set(top) == {"ownership", "mapping"} and all(len(v["top"]) == 2 for v in top.values())
    topd = {f: v["top"] for f, v in top.items()}
    draws = Z.dependent_draws(usable, positions, topd, n_restore=3)
    assert len(draws["restore"]) == 6 and len(draws["pair2"]) == 3 * 2 + 2 * 2  # 3 own / 2 map pairs < 10 items -> both sources
    tabs_d = Z.build_tables(usable, positions, stage="dependent", top=topd, restore=draws["restore"], pair2=draws["pair2"])
    pd = Z.planned_decodes(tabs_d, conditions=Z.Z4_DECODED_CONDITIONS)
    assert pd["all_except"] == 2 * 2 * 5 and pd["restore"] == 6 and pd["pair2"] == 10 * 3 and pd["single"] == 0 and pd["total_planned"] == 56
    # plan_dependent (what the pod's --stage dependent runs) reproduces the default draws and the full-run table
    pl = Z.plan_dependent(usable, positions, rows, top_k=2, n_rand=4)
    assert pl["top"] == topd and pl["draws"] == Z.dependent_draws(usable, positions, topd)
    assert pl["full_plan"]["single"] == 120 and pl["full_plan"]["rand_single"] == 4 and pl["full_plan"]["restore"] == 20 and pl["full_plan"]["pair2"] == 30
    with pytest.raises(SystemExit):
        Z.plan_dependent(usable, positions, [], top_k=2)
    n2 = Z.collect_behaviour(target, usable, tabs_d, beh_path=beh, readvec_dir=rv, full_dir=fd, ledger_path=led, log_path=log, max_new_tokens=3, batch=4,
                             edit_layer=MOCK_EDIT, read_layer=MOCK_LAYER, y2_beh_path=y2b)
    assert n2 == 56
    rows = A.read_jsonl(beh)
    assert len(rows) == 180 and Counter(r["condition"] for r in rows) == {"single": 120, "rand_single": 4, "all_except": 20, "restore": 6, "pair2": 30}
    T = lengths["xown-02"]
    ae = [r for r in rows if r["condition"] == "all_except" and r["pair_id"] == "xown-02"]
    assert all(r["n_positions"] == T - 1 and r["positions"] is None and r["stage"] == "dependent" and r["alpha"] == 1.0 for r in ae)
    assert all("pair_positions" not in r for r in rows if r["condition"] != "pair2")  # the old arms keep their row schema
    rs = [r for r in rows if r["condition"] == "restore"]
    assert {(r["pair_id"], r["source"], r["position"]) for r in rs} == set(draws["restore"]) and all(r["last_edited"] for r in rs)
    # restore(i) and all_except(i) are the same block state at alpha 1: the read vectors agree (the determinism check)
    for b in rs:
        a = next(x for x in rows if x["condition"] == "all_except" and x["pair_id"] == b["pair_id"] and x["source"] == b["source"] and x["position"] == b["position"])
        assert torch.allclose(X.load_readvec(a["key"], rv), X.load_readvec(b["key"], rv), atol=5e-2) and abs(a["lo_model"] - b["lo_model"]) < 0.1
    p2 = [r for r in rows if r["condition"] == "pair2"]
    i2, j2 = sorted(topd["ownership"])
    own2 = [r for r in p2 if r["family"] == "ownership"]
    assert {r["position"] for r in own2} == {f"{i2}-{j2}"} and all(r["pair_positions"] == [i2, j2] == r["positions"] and r["n_positions"] == 2 for r in own2)
    assert all(r["rel_position"] is None and r["positions_kind"] == "pair" and r["stage"] == "dependent" and r["key"].split("|")[3] == "pair2" for r in p2)
    assert {r["alpha"] for r in p2} == set(Z.Z4_PAIR2_ALPHAS)
    # the recorded pair2 lo_model equals a direct core decode of the same two-position edit
    r = next(x for x in own2 if x["alpha"] == 1.0)
    H = {v: X.load_full(f"{r['pair_id']}{v}", fd) for v in ("A", "B")}
    e = next(x for x in tabs_d[r["pair_id"]] if x["key"] == r["key"])
    v = Z.z4_entry_vectors(e, H["A"]["layers"], H["B"]["layers"], layer=MOCK_EDIT)
    one = E.generate_with_interpolated_batch(target, H[r["source"]]["ids"], MOCK_EDIT, v["positions"], (v["base"] + v["delta"])[None], read_layer=MOCK_LAYER,
                                             max_new_tokens=3, cand_first_tokens=(r["first_A"], r["first_B"]) if r["first_A"] is not None else None)[0]
    assert r["lo_model"] is None or abs(one["lo_model"] - r["lo_model"]) < 1e-3
    # ---- readers' LO (+ resumable)
    torch.manual_seed(1)
    J = {MOCK_LAYER: torch.eye(MOCK_D) + torch.randn(MOCK_D, MOCK_D) / 10}
    jl = R.JLensReader().bind_tensors(J, M.unembed_weight(target.model), target.tokenizer)
    ol = R.OLensReader(max_new_tokens=4); ol.target = target
    for rd in (jl, ol):
        assert Z.collect_lo(rd, beh_path=beh, lo_path=lo, readvec_dir=rv, ledger_path=led, log_path=log, batch=16) == 180
    assert Z.collect_lo(ol, beh_path=beh, lo_path=lo, readvec_dir=rv, ledger_path=led, log_path=log) == 0
    lrows = A.read_jsonl(lo)
    assert len(lrows) == 2 * 180 and {r["reader"] for r in lrows} == {"jlens", "olens"}
    q = lrows[0]
    assert q["key"].startswith("jlens|") and q["entry_key"] in {r["key"] for r in rows} and abs(q["lo_toward_other"] + q["lo_own"]) < 1e-9 and "position" in q and "role" in q
    steps = {x["step"] for x in A.read_jsonl(led)}
    assert {"z4_behaviour_single", "z4_behaviour_rand_single", "z4_behaviour_all_except", "z4_behaviour_restore", "z4_behaviour_pair2", "z4_lo_jlens", "z4_lo_olens"} <= steps
    # ---- analyze end to end on the mock output (fabricated X2 natural / S2 rows and Y2 name rows)
    p = _fake_x2_y2(tmp_path, usable, lengths)
    out = tmp_path / "res"
    s = ZA.main(["--behaviour", str(beh), "--lo", str(lo), "--x2-behaviour", str(p["x2b"]), "--x2-lo", str(p["x2l"]), "--y2-behaviour", str(p["y2b"]), "--y2-lo", str(p["y2l"]),
                 "--out", str(out), "--allow-unfrozen", "--n-boot", "20", "--min-n", "1", "--frozen-config", str(tmp_path / "nofreeze.json")])
    assert set(s["by_group"]) == {"ownership", "mapping", "pooled"} and set(s["readers"]) == {"jlens", "olens"}
    assert s["condition_counts"] == {"single": 120, "rand_single": 4, "all_except": 20, "restore": 6, "pair2": 30, "name_only": 20, "name_removed": 20}
    G = s["by_group"]["ownership"]
    assert G["all_positions_reference"]["flip"]["n"] == 6 and G["all_positions_reference"]["flip"]["p"] == 1.0 and G["rand_single"]["n"] >= 0
    assert set(G["name_arms"]) == {"name_only@0.75", "name_only@1.0", "name_removed@0.75", "name_removed@1.0"} and G["name_arms"]["name_removed@1.0"]["flip"]["p"] == 1.0
    assert len(G["all_except"]) == 2 and G["determinism"]["n_restore"] == G["determinism"]["n_twins"] == 3 and G["determinism"]["abs_d_lo_model"]["max"] < 0.1
    assert s["by_group"]["pooled"]["determinism"]["n_twins"] == 6 and list(G["pair2"]) == [f"{i2}-{j2}"] and G["pair2"][f"{i2}-{j2}"]["1.0"]["n_items"] == 6
    assert G["classification"]["verdict"] in ("SINGLE CAUSAL", "REDUNDANT", "JOINT") and G["classification"]["secondary_label"]
    assert (out / "pair2.csv").exists()
    assert set(G["z1_rerun"]["auroc"]) == {"jlens", "olens", "model", "dose"} and G["z1_rerun"]["n_entries"] == 72
    assert (out / "z4.md").exists() and (out / "per_position.csv").exists() and (out / "z4_summary.json").exists() and (out / "fig_main.png").exists()
    csv = (out / "per_position.csv").read_text().splitlines()
    assert csv[0].startswith("arm,family,position,alpha,role,rel_position,is_top") and any(l.startswith("all_x2_S2,") for l in csv) and any(l.startswith("restore,ownership,") for l in csv)
    assert any(l.startswith(f"pair2,ownership,{i2}-{j2},1.0,") for l in csv)


# ================================================================== (f) analyze on synthetic rows: every classification outcome
SYN_TOP = [9, 5, 10, 29, 2]  # the family's top-5 (absolute indices; 2 is outside the sampled singles for most pairs)


def synthetic(tmp_path, outcome: str, n_pairs=12, T=30, seed=0, with_pair2=True):
    """A family of ``n_pairs`` pairs with names at positions 5 and 9, question start 10, last 29. The all-position swap flips 100%.
    single:          position 9 alone flips ~95% (pairs containing 9 too), others ~5%; all_except ~95%.
    redundant:       no single position > 10%; the PAIR 5-9 flips ~95% (others ~5%); every all_except ~95%   (secondary: REDUNDANT)
    joint:           no single position, no pair > 10%; all_except:9 ~10%, the other all_except ~60%          (secondary: JOINT)
    joint_redundant: as joint but the other all_except ~95%                                                   (secondary: REDUNDANT+JOINT)
    restore rows (16 drawn) copy their all_except twin's answer (one disagreement planted) with |Δ lo_model| 0.01.
    Readers: olens' f_r tracks the model's flips (AUROC ~1), nla is flat, jlens follows the name token regardless of flipping."""
    rng = np.random.default_rng(seed)
    beh, lo, x2b, x2l, y2b, y2l = [], [], [], [], [], []
    ids_A = list(range(T)); ids_B = list(ids_A); ids_B[5], ids_B[9] = ids_A[9], ids_A[5]

    def p_flip(cond, pos, a):
        if cond == "single":
            if outcome == "single" and pos == 9:
                return 0.95 if a == 1.0 else 0.6
            return 0.05
        if cond == "pair2":
            i, j = Z.parse_pair_label(pos)
            if outcome == "single" and 9 in (i, j):
                return 0.95
            if outcome == "redundant" and (i, j) == (5, 9):
                return 0.95 if a == 1.0 else 0.5
            return 0.05
        if cond == "all_except":
            if outcome in ("joint", "joint_redundant") and pos == 9:
                return 0.1
            return 0.6 if outcome == "joint" else 0.95
        return 0.03  # rand_single

    pairs = [{"pair_id": f"xown-{i + 2:02d}", "family": "ownership"} for i in range(n_pairs)]
    positions = {q["pair_id"]: Z.z4_positions(q["pair_id"], ids_A, ids_B, max_positions=8) for q in pairs}
    draws = Z.dependent_draws(pairs, positions, {"ownership": SYN_TOP})
    if not with_pair2:
        draws["pair2"] = []
    for i, q in enumerate(pairs):
        pid = q["pair_id"]
        P = positions[pid]
        tab = Z.z4_condition_table(pid, "ownership", P, stage="all", top_positions=SYN_TOP, rand=[(pid, "A", 5)] if i % 3 == 0 else [],
                                   restore=draws["restore"], pair2=draws["pair2"])
        for src in ("A", "B"):
            base = {"pair_id": pid, "family": "ownership", "source": src, "cand_A": "A", "cand_B": "B", "coherent": True}
            x2b.append({**base, "key": f"{pid}|{src}|nat|natural|0.0|None", "site": "nat", "condition": "natural", "alpha": 0.0, "null_k": None, "lo_model": -3.0, "parsed": "A",
                        "flipped_to_other": False, "kept_original": True})
            x2b.append({**base, "key": f"{pid}|{src}|S2|planted|1.0|None", "site": "S2", "condition": "planted", "alpha": 1.0, "null_k": None, "lo_model": 4.0, "parsed": "B",
                        "flipped_to_other": True, "kept_original": False})
            for cond in ("name_only", "name_removed"):
                for a in (0.75, 1.0):
                    fl = cond == "name_removed"
                    y2b.append({**base, "key": f"{pid}|{src}|Y2|{cond}|{a}|None", "site": "Y2", "condition": cond, "alpha": a, "k": None, "lo_model": 3.0 if fl else -3.0,
                                "parsed": "B" if fl else "A", "flipped_to_other": fl, "kept_original": not fl})
        twin = {}
        for e in sorted((e for e in tab if not e["reused"]), key=lambda e: e["condition"] == "restore"):  # all_except before restore
            if e["condition"] == "restore":
                t = twin[(e["source"], e["position"])]
                fl, lom = t["flipped_to_other"], t["lo_model"] + 0.01
            else:
                fl = bool(rng.random() < p_flip(e["condition"], e["position"], e["alpha"]))
                lom = (3.0 if fl else -3.0) + rng.normal(0, 0.4)
            row = {**{k: e[k] for k in ("key", "pair_id", "family", "source", "site", "edit_layer", "stage", "condition", "position", "role", "positions_kind", "alpha", "n_tokens")},
                   "rel_position": None if e["condition"] == "pair2" else e["position"] - T,
                   "n_positions": {"single": 1, "rand_single": 1, "all_except": T - 1, "restore": T, "pair2": 2}[e["condition"]], "cand_A": "A", "cand_B": "B",
                   "parsed": "B" if fl else "A", "flipped_to_other": fl, "kept_original": not fl, "coherent": True, "lo_model": lom, "reused": False}
            if e["condition"] == "pair2":
                row["pair_positions"] = e["pair_positions"]
            if e["condition"] == "all_except":
                twin[(e["source"], e["position"])] = row
            beh.append(row)
    # plant one determinism disagreement
    r0 = next(r for r in beh if r["condition"] == "restore")
    r0["parsed"] = "B" if r0["parsed"] == "A" else "A"
    for r in x2b + y2b + beh:
        for rd in ("olens", "nla", "jlens"):
            if r["condition"] == "natural":
                v = -2.0  # natural own LO of both states; sep = (-(-2)) - (-2) = 4 for every reader
            elif rd == "olens":
                v = -2.0 + (4.0 if r["flipped_to_other"] else 0.3) + rng.normal(0, 0.2)
            elif rd == "nla":
                v = -2.0 + rng.normal(0, 0.05)
            else:  # jlens follows the name token: moves when position 5 or 9 is edited toward B, whatever the model does
                moved = ((r["condition"] in ("single", "rand_single") and r.get("position") in (5, 9))
                         or (r["condition"] == "pair2" and bool(set(r["pair_positions"]) & {5, 9}))
                         or r["condition"] in ("all_except", "restore", "name_only", "name_removed", "planted"))
                v = -2.0 + (3.0 if moved else 0.0) + rng.normal(0, 0.2)
            row = {"key": f"{rd}|{r['key']}", "entry_key": r["key"], "reader": rd, "lo_toward_other": float(v), "unscorable": False}
            (x2l if r["site"] in ("nat", "S2") else y2l if r["site"] == "Y2" else lo).append(row)
    tmp_path.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, rows in (("beh", beh), ("lo", lo), ("x2b", x2b), ("x2l", x2l), ("y2b", y2b), ("y2l", y2l)):
        paths[name] = tmp_path / f"{name}.jsonl"
        paths[name].write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    paths["draws"] = draws
    return paths


def _run(tmp_path, p, extra=()):
    return ZA.main(["--behaviour", str(p["beh"]), "--lo", str(p["lo"]), "--x2-behaviour", str(p["x2b"]), "--x2-lo", str(p["x2l"]), "--y2-behaviour", str(p["y2b"]),
                    "--y2-lo", str(p["y2l"]), "--out", str(tmp_path / "res"), "--allow-unfrozen", "--n-boot", "40", "--frozen-config", str(tmp_path / "nofreeze.json"), *extra])


@pytest.mark.parametrize("outcome,verdict,secondary", [("single", "SINGLE CAUSAL", "SINGLE CAUSAL POSITION"), ("redundant", "REDUNDANT", "REDUNDANT"),
                                                       ("joint", "JOINT", "JOINT"), ("joint_redundant", "JOINT", "REDUNDANT+JOINT")])
def test_analyze_classification_outcomes(tmp_path, outcome, verdict, secondary):
    p = synthetic(tmp_path / outcome, outcome)
    s = _run(tmp_path / outcome, p, ["--no-fig"] if outcome not in ("single", "redundant") else [])
    G = s["by_group"]["ownership"]
    c = G["classification"]
    assert s["classification"]["ownership"] == verdict and s["classification"]["pooled"] == verdict, c
    assert c["secondary_label"] == secondary and s["classification_secondary_original_rule"]["ownership"] == secondary, c
    assert c["r_all"] == 1.0 and G["all_positions_reference"]["flip"]["n"] == 24 and c["rule"].startswith("deviation 2026-10-09")
    assert c["pair2"]["n_pairs_ranked"] == 10 and len(G["pair2"]) == 10 and all(set(v) == {"0.5", "0.75", "1.0"} and v["1.0"]["n_items"] == 10 for v in G["pair2"].values())
    if outcome == "single":
        assert c["single"]["position"] == 9 and c["single"]["max"] >= 0.8 and c["flags"]["single_causal"] is True and c["flags"]["redundant_pair"] is False
        assert G["top_single_positions"][0]["position"] == 9 and G["top_single_positions"][0]["role"] == "diff"
        assert (tmp_path / outcome / "res" / "fig_main.png").exists()
    else:
        assert c["single"]["max"] < 0.5 and c["flags"]["single_causal"] is False and c["single"]["n_positions_ranked"] >= 4  # fixed positions have n = 24 >= min_n
    if outcome == "redundant":
        assert c["pair2"]["pair"] == "5-9" and c["pair2"]["max"] >= 0.8 and c["flags"]["redundant_pair"] is True and c["all_except"]["min"] >= 0.8
        assert G["pair2"]["5-9"]["1.0"]["d_model"]["mean"] > 3 and G["pair2"]["5-9"]["1.0"]["role"] == "diff+diff"
        assert (tmp_path / outcome / "res" / "fig_main.png").exists()
    if outcome.startswith("joint"):
        assert c["pair2"]["max"] < 0.8 and c["flags"]["redundant_pair"] is False and c["original"]["flags"]["joint"] is True
        assert c["all_except"]["min_position"] == 9 and c["all_except"]["min"] < 0.5
        assert c["original"]["flags"]["redundant"] is (outcome == "joint_redundant")
    # determinism check: 16 restore rows, each with its all_except twin; one planted disagreement; |Δ lo_model| = 0.01
    d = G["determinism"]
    assert d["n_restore"] == d["n_twins"] == 16 and d["answer_agreement"]["k"] == 15 and d["abs_d_lo_model"]["max"] == pytest.approx(0.01, abs=1e-6)
    assert len(d["twins"]) == 16 and sum(not t["same_answer"] for t in d["twins"]) == 1
    # random control is low; name arms come from Y2
    assert G["rand_single"]["flip"]["p"] <= 0.25 and G["name_arms"]["name_removed@1.0"]["flip"]["p"] == 1.0 and G["name_arms"]["name_only@1.0"]["flip"]["p"] == 0.0
    # Z1-style rerun: olens predicts flips (AUROC high), nla ~ chance, dose-only ~ chance unless single outcome
    Zr = G["z1_rerun"]
    assert Zr["n_entries"] == 24 * 8 * 2 and Zr["auroc"]["olens"]["auroc"] > 0.9 and Zr["auroc"]["model"]["auroc"] > 0.95
    assert abs(Zr["auroc"]["nla"]["auroc"] - 0.5) < 0.2 and Zr["auroc"]["olens"]["lo"] > Zr["auroc"]["nla"]["hi"]
    if outcome == "single":
        assert Zr["position_corr"]["olens"]["spearman"] > 0.5 and Zr["auroc_alpha1"]["olens"]["auroc"] > 0.9
    csv = (tmp_path / outcome / "res" / "per_position.csv").read_text().splitlines()
    single_cells = [l.split(",")[:4] for l in csv if l.startswith("single,ownership,")]
    assert len(single_cells) >= 8 * 2 and all(any(c[2] == str(pos) and c[3] == str(a) for c in single_cells) for pos in (5, 9, 10, 29) for a in (0.75, 1.0))
    assert sum(1 for l in csv if l.startswith("all_except,ownership,")) == 5 and sum(1 for l in csv if l.startswith("pair2,ownership,")) == 30
    p2csv = (tmp_path / outcome / "res" / "pair2.csv").read_text().splitlines()
    assert p2csv[0].startswith("family,pair,i,j,alpha") and len(p2csv) == 1 + 2 * 30  # ownership + pooled
    md = (tmp_path / outcome / "res" / "z4.md").read_text()
    assert verdict in md and "Z1-style rerun" in md and "all_except" in md and "Determinism check" in md and "Two-position arm" in md and secondary in md


def test_analyze_undetermined_without_pair2_and_min_n_guard(tmp_path):
    # no single reaches the bar and there are no pair2 rows yet -> UNDETERMINED (the secondary label is still computed)
    p = synthetic(tmp_path / "nopair", "joint", with_pair2=False)
    s = _run(tmp_path / "nopair", p, ["--no-fig"])
    c = s["by_group"]["ownership"]["classification"]
    assert c["verdict"] == "UNDETERMINED" and c["pair2"]["max"] is None and c["secondary_label"] == "JOINT"
    assert not (tmp_path / "nopair" / "res" / "pair2.csv").exists()
    # a single-causal family does not need pair2 rows
    p = synthetic(tmp_path / "nopair_single", "single", with_pair2=False)
    assert _run(tmp_path / "nopair_single", p, ["--no-fig"])["classification"]["ownership"] == "SINGLE CAUSAL"
    # the min_n guard: with min_n above every cell's n the single extrema are None -> UNDETERMINED (unguarded values still reported)
    p = synthetic(tmp_path / "guard", "joint")
    s2 = _run(tmp_path / "guard", p, ["--no-fig", "--min-n", "10000"])
    c2 = s2["by_group"]["ownership"]["classification"]
    assert c2["verdict"] == "UNDETERMINED" and c2["single"]["max"] is None and c2["single"]["max_unguarded"] is not None and c2["pair2"]["max_unguarded"] is not None


def test_analysis_does_not_touch_writeup(tmp_path):
    wu = REPO / "results" / "g_agreement" / "writeup.md"
    before = wu.read_bytes() if wu.exists() else None
    p = synthetic(tmp_path, "redundant")
    _run(tmp_path, p, ["--no-fig"])
    assert (wu.read_bytes() if wu.exists() else None) == before
    assert "writeup" not in Path(ZA.__file__).read_text().replace("writeup.md (deviation (5))", "").replace("written to writeup.md", "")


def test_auroc_and_helpers():
    assert ZA.auroc(np.array([0.1, 0.4, 0.35, 0.8]), np.array([0, 0, 1, 1])) == pytest.approx(0.75)
    assert np.isnan(ZA.auroc(np.array([1.0, 2.0, 3.0]), np.array([1, 1, 1])))
    assert ZA.auroc(np.array([1.0, 1.0]), np.array([0, 1])) == pytest.approx(0.5)
    assert ZA.spearman(np.array([1.0, 2, 3, 4]), np.array([1.0, 3, 2, 4])) == pytest.approx(0.8)
    mb = ZA.mean_boot([("p", 1.0), ("p", 3.0), ("q", 2.0)], 50, 0)
    assert mb["mean"] == pytest.approx(2.0) and mb["n"] == 3 and mb["n_pairs"] == 2 and mb["lo"] <= mb["mean"] <= mb["hi"]
    ab = ZA.auroc_boot([("p", 0.9, True), ("p", 0.1, False), ("q", 0.8, True), ("q", 0.2, False)], 50, 0)
    assert ab["auroc"] == 1.0 and ab["n"] == 4 and ab["n_flip"] == 2
    # the deviation rule: single ≥ 0.8·R_all -> SINGLE CAUSAL; else a pair ≥ 0.8·R_all -> REDUNDANT; else JOINT (guarded by min_n)
    cell = lambda p, n=20: {"n": n, "flip": {"p": p}}
    c = ZA.classify(1.0, {3: cell(0.9), 4: cell(1.0, 2)}, {}, {}, min_n=8)
    assert c["verdict"] == "SINGLE CAUSAL" and c["single"]["position"] == 3 and c["single"]["position_unguarded"] == 4
    c = ZA.classify(0.9, {3: cell(0.71)}, {"3-7": cell(0.72, 10), "1-2": cell(0.72, 10)}, {}, min_n=8)
    assert c["verdict"] == "REDUNDANT" and c["pair2"]["pair"] == "1-2"  # 0.72 ≥ 0.8·0.9; ties -> lowest pair
    c = ZA.classify(0.9, {3: cell(0.6)}, {"3-7": cell(0.7, 10)}, {3: cell(0.9)}, min_n=8)
    assert c["verdict"] == "JOINT" and c["secondary_label"] == "MIXED"
    c = ZA.classify(1.0, {3: cell(0.6)}, {"3-7": cell(1.0, 4)}, {}, min_n=8)
    assert c["verdict"] == "UNDETERMINED" and c["pair2"]["max_unguarded"] == 1.0  # the only pair is below min_n
    assert ZA.classify(float("nan"), {}, {}, {}, 8)["verdict"] == "UNDETERMINED"
    # the original rule survives as classify_original (secondary label)
    c = ZA.classify_original(1.0, {3: cell(0.9), 4: cell(1.0, 2)}, {}, min_n=8)
    assert c["verdict"] == "SINGLE CAUSAL POSITION" and c["single"]["position"] == 3 and c["single"]["position_unguarded"] == 4
    c = ZA.classify_original(1.0, {3: cell(0.3)}, {}, min_n=8)
    assert c["verdict"] == "UNDETERMINED" and c["flags"]["no_single_ge_half"] is True
    c = ZA.classify_original(1.0, {3: cell(0.6)}, {3: cell(0.9)}, min_n=8)
    assert c["verdict"] == "MIXED"
    c = ZA.classify_original(1.0, {3: cell(0.3)}, {3: cell(0.6)}, min_n=8)
    assert c["verdict"] == "MIXED" and c["flags"]["redundant"] is False and c["flags"]["joint"] is False
    assert ZA.classify_original(float("nan"), {}, {}, 8)["verdict"] == "UNDETERMINED"
    # determinism helper on hand-made twins
    d = ZA.determinism_check([{"condition": "all_except", "pair_id": "p", "source": "A", "position": 3, "alpha": 1.0, "parsed": "B", "lo_model": 1.0, "flipped_to_other": True},
                              {"condition": "restore", "pair_id": "p", "source": "A", "position": 3, "alpha": 1.0, "parsed": "B", "lo_model": 1.25, "flipped_to_other": True},
                              {"condition": "restore", "pair_id": "q", "source": "A", "position": 3, "alpha": 1.0, "parsed": "A", "lo_model": 0.0}])
    assert d["n_restore"] == 2 and d["n_twins"] == 1 and d["n_without_twin"] == 1 and d["answer_agreement"]["k"] == 1 and d["abs_d_lo_model"]["mean"] == 0.25


def test_zz_results_and_cache_untouched():
    now = sorted(str(p) for p in (REPO / "results" / "g_agreement" / "z4").rglob("*")) if (REPO / "results" / "g_agreement" / "z4").exists() else None
    assert now == RESULTS_SNAPSHOT
    cache = sorted(str(p) for p in (REPO / "cache" / "g_agreement" / "z").rglob("*")) if (REPO / "cache" / "g_agreement" / "z").exists() else None
    assert cache == CACHE_SNAPSHOT
