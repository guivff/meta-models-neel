"""MOCK tests (CPU) for Phase Y2: differing positions, the name_only / name_removed partition, other-pair rescaling,
the J-space basis and split, the condition table counts, the collector end to end on the tiny model (tmp paths)
and analyze.py on synthetic rows. Nothing is written under results/ or cache/.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_y2_mock.py -q``
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
from projects.g_agreement.tests.test_x2_mock import MOCK_SITES, items_x, mk_item  # noqa: E402
from projects.g_agreement.x2_causal import collect as X  # noqa: E402
from projects.g_agreement.y2_identity import analyze as YA  # noqa: E402
from projects.g_agreement.y2_identity import collect as Y  # noqa: E402

RESULTS_SNAPSHOT = sorted(str(p) for p in (REPO / "results" / "g_agreement" / "y2").rglob("*")) if (REPO / "results" / "g_agreement" / "y2").exists() else None
CACHE_SNAPSHOT = sorted(str(p) for p in (REPO / "cache" / "g_agreement" / "y").rglob("*")) if (REPO / "cache" / "g_agreement" / "y").exists() else None
MOCK_EDIT = 1
MOCK_R = 16


@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    monkeypatch.setattr(C, "LAYER", MOCK_LAYER)
    monkeypatch.setattr(C, "HIDDEN_STATES_INDEX", MOCK_LAYER + 1)
    monkeypatch.setattr(C, "D_MODEL", MOCK_D)
    monkeypatch.setattr(C, "N_LAYERS", 4)
    monkeypatch.setattr(E, "X2_SITES", MOCK_SITES)
    monkeypatch.setattr(E, "X2_EDIT_LAYERS", (MOCK_EDIT, MOCK_LAYER))
    monkeypatch.setattr(E, "X2_READ_LAYER", MOCK_LAYER)
    monkeypatch.setattr(E, "Y2_EDIT_LAYER", MOCK_EDIT)
    monkeypatch.setattr(Y, "JLENS_LAYERS_KEEP", (MOCK_EDIT, MOCK_LAYER))
    yield


@pytest.fixture(scope="module")
def target():
    return M.Target(model=tiny_model(), tokenizer=FakeTok(), device="cpu", model_id="MOCK/tiny", revision="mock", model_class="Qwen3_5ForCausalLM")


def rand_pair(T=9, seed=0):
    torch.manual_seed(seed)
    HA = {MOCK_EDIT: torch.randn(T, MOCK_D) * 5, MOCK_LAYER: torch.randn(T, MOCK_D) * 5}
    HB = {MOCK_EDIT: HA[MOCK_EDIT] + torch.randn(T, MOCK_D), MOCK_LAYER: HA[MOCK_LAYER] + torch.randn(T, MOCK_D)}
    ids_A = [10, 65, 20, 30, 66, 40, 50, 60, 70]
    ids_B = [10, 66, 20, 30, 65, 40, 50, 60, 70]  # the two names swapped: a token permutation
    return HA, HB, ids_A, ids_B


# ================================================================== (a) positions + masks
def test_differing_positions_and_masks():
    assert E.differing_positions([1, 2, 3, 4], [1, 3, 2, 4]) == [1, 2]
    assert E.differing_positions([1, 2], [1, 2]) == []
    with pytest.raises(ValueError):
        E.differing_positions([1, 2], [1, 2, 3])
    m = E.position_masks([5, 1, 9, 2, 7], [5, 2, 9, 1, 7])
    assert m["name_only"] == [1, 3] and m["name_removed"] == [0, 2, 4] and sorted(m["name_only"] + m["name_removed"]) == list(range(5))


def test_name_only_plus_name_removed_is_full_delta():
    HA, HB, ids_A, ids_B = rand_pair()
    T = len(ids_A)
    tab = E.y2_condition_table("p", "ownership", other_pair_ids=["q"])
    by = {(e["source"], e["condition"], e["alpha"], e["k"]): e for e in tab}
    Q = E.random_subspace(MOCK_D, MOCK_R, seed=3)
    full = E.y2_entry_vectors(by[("A", "full", 1.0, None)], HA, HB, ids_A, ids_B, basis=Q)
    no = E.y2_entry_vectors(by[("A", "name_only", 1.0, None)], HA, HB, ids_A, ids_B, basis=Q)
    nr = E.y2_entry_vectors(by[("A", "name_removed", 1.0, None)], HA, HB, ids_A, ids_B, basis=Q)
    assert no["positions"] == [1, 4] and nr["positions"] == [0, 2, 3, 5, 6, 7, 8] and no["n_positions"] + nr["n_positions"] == T
    recomposed = torch.zeros(T, MOCK_D)
    recomposed[no["positions"]] = no["delta"]
    recomposed[nr["positions"]] = nr["delta"]
    assert torch.allclose(recomposed, full["delta"], atol=1e-6) and torch.allclose(full["delta"], HB[MOCK_EDIT] - HA[MOCK_EDIT], atol=1e-6)
    assert torch.allclose(full["base"] + full["delta"], HB[MOCK_EDIT], atol=1e-5)  # alpha 1 from A lands on B
    assert torch.allclose(nr["base"] + nr["delta"], HB[MOCK_EDIT][nr["positions"]], atol=1e-5)
    assert no["last_edited"] is False and nr["last_edited"] is True and no["input_norm_last"] == pytest.approx(float(HA[MOCK_EDIT][-1].norm()))
    # mirror for source B
    noB = E.y2_entry_vectors(by[("B", "name_only", 1.0, None)], HA, HB, ids_A, ids_B, basis=Q)
    assert torch.allclose(noB["delta"], -no["delta"], atol=1e-6) and torch.allclose(noB["base"], HB[MOCK_EDIT][[1, 4]], atol=1e-6)
    # energy fractions: the full one is the same number on every entry of the pair
    assert full["frac_norm_in_J_full"] == pytest.approx(no["frac_norm_in_J_full"]) and 0.0 < full["frac_norm_in_J"] < 1.0
    with pytest.raises(ValueError):
        E.y2_entry_vectors(by[("A", "name_only", 1.0, None)], HA, HB, ids_A, ids_A, basis=Q)  # identical renders: no name positions


# ================================================================== (b) other-pair delta
def test_other_pair_delta_matches_per_position_norm():
    HA, HB, ids_A, ids_B = rand_pair(seed=1)
    D = HB[MOCK_EDIT] - HA[MOCK_EDIT]
    torch.manual_seed(7)
    O = torch.randn_like(D) * 3
    O[2] = 0.0  # a vanishing position stays zero
    OO = E.other_pair_delta(D, O)
    n_self, n_oo = D.norm(dim=1), OO.norm(dim=1)
    keep = torch.ones(len(D), dtype=torch.bool); keep[2] = False
    assert torch.allclose(n_oo[keep], n_self[keep], atol=1e-4) and float(n_oo[2]) == 0.0
    cos = (OO[keep] * O[keep]).sum(1) / (OO[keep].norm(dim=1) * O[keep].norm(dim=1))
    assert torch.allclose(cos, torch.ones_like(cos), atol=1e-5)  # direction is the other pair's
    with pytest.raises(ValueError):
        E.other_pair_delta(D, O[:-1])
    tab = E.y2_condition_table("p", "ownership", other_pair_ids=["q", "r"])
    e = next(x for x in tab if x["condition"] == "other_pair" and x["source"] == "B" and x["alpha"] == 0.5 and x["k"] == 1)
    assert e["other_pair_id"] == "r"
    v = E.y2_entry_vectors(e, HA, HB, ids_A, ids_B, other_deltas={"r": O})
    assert torch.allclose(v["delta"], -E.other_pair_delta(D, O), atol=1e-6) and v["dose_abs"] == pytest.approx(0.5 * float(v["delta"].norm()))


# ================================================================== (c) J-space basis + split
def test_jspace_basis_orthonormal_and_split_recomposes(tmp_path):
    torch.manual_seed(0)
    W = torch.randn(300, MOCK_D)
    J = torch.eye(MOCK_D) + torch.randn(MOCK_D, MOCK_D) / 10
    cache = tmp_path / "basis.pt"
    Q = E.jspace_basis(J, W, MOCK_R, cache_path=cache, layer=MOCK_EDIT)
    assert tuple(Q.shape) == (MOCK_D, MOCK_R) and Q.dtype == torch.float32
    assert torch.allclose(Q.T @ Q, torch.eye(MOCK_R), atol=1e-5)
    # the columns are the top right singular vectors of W J (same span as the SVD's)
    _, S, Vh = torch.linalg.svd(W @ J)
    V = Vh[:MOCK_R].T
    P1, P2 = Q @ Q.T, V @ V.T
    assert torch.allclose(P1, P2, atol=1e-3)
    meta = torch.load(cache)
    assert meta["r_star"] == MOCK_R and meta["layer"] == MOCK_EDIT and meta["d"] == MOCK_D and torch.allclose(meta["evals"].sqrt(), S[:MOCK_R], rtol=1e-3)
    assert 0 < meta["energy_fraction_top_r"] <= 1
    # cache reuse (a different J gives the cached basis back) and a smaller r* slices it
    Q2 = E.jspace_basis(torch.randn(MOCK_D, MOCK_D), W, MOCK_R, cache_path=cache, layer=MOCK_EDIT)
    assert torch.equal(Q2, Q) and torch.equal(E.jspace_basis(J, W, 4, cache_path=cache, layer=MOCK_EDIT), Q[:, :4])
    # the split recomposes the delta; Δ_J lies in the span, Δ_⊥ is orthogonal to it
    D = torch.randn(7, MOCK_D)
    DJ, Dp = E.split_delta(D, Q)
    assert torch.allclose(DJ + Dp, D, atol=1e-5) and torch.allclose(Dp @ Q, torch.zeros(7, MOCK_R), atol=1e-4) and torch.allclose((DJ @ Q) @ Q.T, DJ, atol=1e-4)
    f = E.j_energy_fraction(D, Q)
    assert abs(f - float(DJ.norm() / D.norm())) < 1e-6 and E.j_energy_fraction(DJ, Q) == pytest.approx(1.0, abs=1e-4) and E.j_energy_fraction(Dp, Q) == pytest.approx(0.0, abs=1e-4)
    with pytest.raises(ValueError):
        E.jspace_basis(J, W, MOCK_D + 1)


def test_random_subspace_controls():
    Q = E.random_subspace(MOCK_D, MOCK_R, seed=11)
    assert tuple(Q.shape) == (MOCK_D, MOCK_R) and torch.allclose(Q.T @ Q, torch.eye(MOCK_R), atol=1e-5)
    assert torch.equal(Q, E.random_subspace(MOCK_D, MOCK_R, seed=11)) and not torch.allclose(Q, E.random_subspace(MOCK_D, MOCK_R, seed=12))
    # a random vector puts ~ r/d of its energy in a random rank-r subspace
    torch.manual_seed(0)
    fr = [E.j_energy_fraction(torch.randn(MOCK_D), E.random_subspace(MOCK_D, MOCK_R, seed=s)) ** 2 for s in range(200)]
    assert abs(float(np.mean(fr)) - MOCK_R / MOCK_D) < 0.03
    assert Y.rand_seed(0) != Y.rand_seed(1) and Y.rand_seed(0) == Y.rand_seed(0)


# ================================================================== (d) condition table
def test_condition_table_counts_and_keys():
    tab = E.y2_condition_table("xown-02", "ownership", other_pair_ids=["xown-03", "xown-04", "xown-05", "xown-06"])
    assert len(tab) == 90 and len({e["key"] for e in tab}) == 90
    assert sum(1 for e in tab if not e["reused"]) == 84 and sum(1 for e in tab if e["reused"]) == 6
    c = Counter((e["source"], e["alpha"], e["condition"]) for e in tab)
    for src in ("A", "B"):
        for a in (0.5, 0.75, 1.0):
            assert c[(src, a, "full")] == 1 and c[(src, a, "name_only")] == 1 and c[(src, a, "name_removed")] == 1 and c[(src, a, "other_pair")] == 4
            assert c[(src, a, "J_only")] == c[(src, a, "J_perp")] == 1 and c[(src, a, "rand_only")] == c[(src, a, "rand_perp")] == 3
            assert sum(v for (s, al, _), v in c.items() if s == src and al == a) == 15
    e = next(x for x in tab if x["condition"] == "full" and x["source"] == "A" and x["alpha"] == 0.5)
    assert e["key"] == "xown-02|A|Y2|full|0.5|None" and e["reused_key"] == "xown-02|A|S2|planted|0.5|None" and e["positions_kind"] == "all"
    assert {e["positions_kind"] for e in tab if e["condition"] == "name_only"} == {"differing"} and {e["positions_kind"] for e in tab if e["condition"] == "name_removed"} == {"equal"}
    assert all(e["r_star"] == 384 for e in tab if e["condition"] in ("J_only", "J_perp", "rand_only", "rand_perp")) and all(e["sign"] == 1 for e in tab)
    assert {e["key"].split("|")[-1] for e in tab if e["condition"] == "rand_perp"} == {"0", "1", "2"}
    # fewer usable other pairs shrink only the other_pair rows; a 5th other pair is ignored (K = 4)
    assert len(E.y2_condition_table("p", "ownership", other_pair_ids=["q"])) == 90 - 3 * 2 * 3
    assert len(E.y2_condition_table("p", "ownership", other_pair_ids=[])) == 90 - 4 * 2 * 3
    assert len(E.y2_condition_table("p", "ownership", other_pair_ids=list("abcde"))) == 90
    assert len(E.y2_condition_table("p", "ownership", other_pair_ids=list("abcd"), conditions=("name_only", "name_removed"))) == 12
    # the brief's totals for the 64 X2 pairs, if every pair had 4 equal-length siblings
    assert 64 * 84 == 5376


# ================================================================== collector on tmp paths
def test_y2_collect_end_to_end(target, tmp_path, monkeypatch):
    monkeypatch.setattr(C, "FROZEN_CANDIDATES", (tmp_path / "none.json",))
    pairs = X.x2_pairs(items_x(), n_pairs=32)
    fd, rv, beh, lo, led, log, sk, bp = (tmp_path / f for f in ("full", "readvecs", "beh.jsonl", "lo.jsonl", "c.jsonl", "log.md", "skipped.json", "basis.pt"))
    usable, skipped = X.ensure_full_states(target, pairs, full_dir=fd, ledger_path=led, log_path=log, skipped_path=sk)
    assert len(usable) == 5 and not skipped
    lengths = Y.pair_lengths(usable, fd)
    assert set(lengths) == {p["pair_id"] for p in usable} and lengths["xown-02"] == lengths["xown-03"] == lengths["xown-04"]
    others = Y.y2_other_pair_ids(usable[0], usable, lengths)
    assert len(others) == 2 and set(others) == {"xown-03", "xown-04"} and Y.y2_other_pair_ids(usable[0], usable, lengths) == others
    # an unequal-length sibling is never an other pair
    assert Y.y2_other_pair_ids(usable[0], usable, {**lengths, "xown-03": lengths["xown-03"] + 1}) == ["xown-04"]
    tables = Y.build_tables(usable, full_dir=fd, r_star=MOCK_R)
    cnt = Y.table_counts(tables)
    n_other_mapping = len(Y.y2_other_pair_ids(usable[3], usable, lengths))
    expected_new = 3 * (84 - (4 - 2) * 6) + 2 * (84 - (4 - n_other_mapping) * 6)
    assert cnt["new_decodes"] == expected_new and cnt["reused_full"] == 5 * 6 and cnt["pairs"] == 5
    # J-lens bound on the mock tensors -> basis + random controls
    torch.manual_seed(1)
    J = {MOCK_EDIT: torch.eye(MOCK_D) + torch.randn(MOCK_D, MOCK_D) / 10, MOCK_LAYER: torch.eye(MOCK_D) + torch.randn(MOCK_D, MOCK_D) / 10}
    jl = R.JLensReader().bind_tensors(J, M.unembed_weight(target.model), target.tokenizer)
    basis = Y.ensure_basis(jl, path=bp, r_star=MOCK_R, layer=MOCK_EDIT, ledger_path=led, log_path=log)
    assert tuple(basis.shape) == (MOCK_D, MOCK_R) and bp.exists()
    assert torch.equal(Y.ensure_basis(jl, path=bp, r_star=MOCK_R, layer=MOCK_EDIT, ledger_path=led, log_path=log), basis)  # cached
    rb = Y.rand_bases(MOCK_D, MOCK_R, 3, layer=MOCK_EDIT)
    assert len(rb) == 3 and all(tuple(q.shape) == (MOCK_D, MOCK_R) for q in rb)
    x2beh = tmp_path / "x2_beh.jsonl"  # a fake X2 file holding only some of the reused keys -> the log counts the missing ones
    x2beh.write_text("\n".join(json.dumps({"key": e["reused_key"]}) for e in tables["xown-02"] if e["reused"]) + "\n")
    n = Y.collect_behaviour(target, usable, tables, basis, rb, beh_path=beh, readvec_dir=rv, full_dir=fd, ledger_path=led, log_path=log, max_new_tokens=3, batch=4,
                            edit_layer=MOCK_EDIT, read_layer=MOCK_LAYER, x2_beh_path=x2beh)
    assert n == expected_new
    rows = A.read_jsonl(beh)
    assert len(rows) == n and len({r["key"] for r in rows}) == n and not any(r["condition"] == "full" for r in rows)
    assert all((rv / f"{E.x2_key_safe(r['key'])}.pt").exists() for r in rows)
    r0 = rows[0]
    for k in ("key", "pair_id", "family", "source", "site", "edit_layer", "positions_kind", "n_positions", "alpha", "condition", "k", "null_k", "r_star", "frac_norm_in_J",
              "frac_norm_in_J_full", "cand_A", "cand_B", "answer_text", "parsed", "flipped_to_other", "kept_original", "coherent", "lo_model", "dose_abs", "wall_s",
              "frozen_code_sha256", "current_code_sha256", "basis_sha16", "reused"):
        assert k in r0, k
    assert all(r["site"] == "Y2" and r["edit_layer"] == MOCK_EDIT and r["read_layer"] == MOCK_LAYER and r["n_hook_edits"] >= 1 for r in rows)
    T = lengths["xown-02"]
    own = {r["condition"]: r for r in rows if r["pair_id"] == "xown-02" and r["source"] == "A" and r["alpha"] == 1.0 and r.get("k") in (None, 0)}
    assert own["name_only"]["n_positions"] == 2 and own["name_only"]["positions"] == sorted(E.differing_positions(torch.load(fd / "xown-02A.pt")["ids"], torch.load(fd / "xown-02B.pt")["ids"]))
    assert own["name_removed"]["n_positions"] == T - 2 and own["name_only"]["n_positions"] + own["name_removed"]["n_positions"] == T
    assert own["J_only"]["n_positions"] == T and own["J_only"]["positions"] is None and own["J_only"]["frac_norm_in_J"] == pytest.approx(1.0, abs=1e-3)
    assert own["J_perp"]["frac_norm_in_J"] == pytest.approx(0.0, abs=1e-3) and own["other_pair"]["other_pair_id"] in others
    assert own["rand_only"]["rand_seed"] == Y.rand_seed(0) and own["J_only"]["rand_seed"] is None
    assert all(r["cand_A"] == "A" and r["cand_B"] == "B" and r["lo_model"] is not None for r in rows if r["pair_id"] == "xown-02" and r["source"] == "A")
    # the J_only + J_perp edits at alpha 1 reach B: the read vectors from the two halves differ, while an all-position alpha-1 edit of the
    # full delta would equal h_B; here we check the other-pair dose equals the pair's own per-position dose
    assert own["other_pair"]["delta_edited"] == pytest.approx(own["J_only"]["delta_total"], rel=1e-3)
    assert Y.collect_behaviour(target, usable, tables, basis, rb, beh_path=beh, readvec_dir=rv, full_dir=fd, ledger_path=led, log_path=log, max_new_tokens=3,
                               edit_layer=MOCK_EDIT, read_layer=MOCK_LAYER, x2_beh_path=x2beh) == 0  # resumable
    logtxt = log.read_text()
    assert f"{5 * 6} full entries reused" in logtxt and f"({4 * 6} MISSING" in logtxt
    # readers' LO on the read vectors (+ resumable)
    ol = R.OLensReader(max_new_tokens=4); ol.target = target
    for rd in (jl, ol):
        assert Y.collect_lo(rd, beh_path=beh, lo_path=lo, readvec_dir=rv, ledger_path=led, log_path=log, batch=8) == n
    assert Y.collect_lo(ol, beh_path=beh, lo_path=lo, readvec_dir=rv, ledger_path=led, log_path=log) == 0
    lrows = A.read_jsonl(lo)
    assert len(lrows) == 2 * n and {r["reader"] for r in lrows} == {"jlens", "olens"}
    q = lrows[0]
    assert q["key"].startswith("jlens|") and q["entry_key"] in {r["key"] for r in rows} and abs(q["lo_toward_other"] + q["lo_own"]) < 1e-9 and "frac_norm_in_J" in q
    steps = {x["step"] for x in A.read_jsonl(led)}
    assert {"y2_jspace_basis", "y2_behaviour_name_only", "y2_behaviour_name_removed", "y2_behaviour_other_pair", "y2_behaviour_J_only", "y2_behaviour_J_perp",
            "y2_behaviour_rand_only", "y2_behaviour_rand_perp", "y2_lo_jlens", "y2_lo_olens"} <= steps
    # analyze needs X2 natural + S2 rows: fabricate them for the mock pairs, then run end to end
    x2rows, x2lo = [], []
    for p in usable:
        for src in ("A", "B"):
            it = p[src]
            ca, cb = it["primary"]["answer"], X.other_candidate(it)
            base = {"pair_id": p["pair_id"], "family": p["family"], "source": src, "cand_A": ca, "cand_B": cb, "coherent": True, "lo_model": -2.0}
            x2rows.append({**base, "key": f"{p['pair_id']}|{src}|nat|natural|0.0|None", "site": "nat", "condition": "natural", "alpha": 0.0, "null_k": None, "parsed": ca,
                           "flipped_to_other": False, "kept_original": True})
            for a in (0.25, 0.5, 0.75, 1.0):
                x2rows.append({**base, "key": f"{p['pair_id']}|{src}|S2|planted|{a}|None", "site": "S2", "condition": "planted", "alpha": a, "null_k": None,
                               "parsed": cb if a >= 0.5 else ca, "flipped_to_other": a >= 0.5, "kept_original": a < 0.5, "lo_model": -2.0 + 6 * a})
    for r in x2rows:
        for rd in ("jlens", "olens"):
            x2lo.append({"key": f"{rd}|{r['key']}", "entry_key": r["key"], "reader": rd, "lo_toward_other": float(-1.0 + 2 * r["alpha"]), "unscorable": False})
    (tmp_path / "x2b.jsonl").write_text("\n".join(json.dumps(r) for r in x2rows) + "\n"); (tmp_path / "x2l.jsonl").write_text("\n".join(json.dumps(r) for r in x2lo) + "\n")
    out = tmp_path / "res"
    s = YA.main(["--behaviour", str(beh), "--lo", str(lo), "--x2-behaviour", str(tmp_path / "x2b.jsonl"), "--x2-lo", str(tmp_path / "x2l.jsonl"), "--out", str(out),
                 "--allow-unfrozen", "--n-boot", "20", "--frozen-config", str(tmp_path / "nofreeze.json")])
    assert set(s["conditions"]) == set(E.Y2_CONDITIONS) and s["E12_flip_by_condition_alpha"]["full"]["1.0"]["flip"]["n"] == 10
    assert (out / "summary.json").exists() and (out / "fig_main.png").exists() and (out / "flips.csv").exists() and (out / "follow.csv").exists()
    assert set(s["classification"]) == {"jlens", "olens"} and s["delta_J_energy"]["n_pairs"] == 5


# ================================================================== analyze on synthetic rows
def synthetic(tmp_path, n_pairs=16, seed=0):
    """Model: flips under full, name_removed and J_perp at alpha >= 0.5 (and rand_perp), never under name_only, J_only, rand_only, other_pair.
    Readers: olens follows the binding (name_removed, J_perp, full, rand_perp), jlens follows the name (name_only, full) and J_only (a J-space
    leak), its J_perp win is as low as its rand_perp; nla is flat (shift exactly 0 everywhere)."""
    rng = np.random.default_rng(seed)
    beh, lo, x2b, x2l = [], [], [], []
    flips = {"full": True, "name_only": False, "name_removed": True, "other_pair": False, "J_only": False, "J_perp": True, "rand_only": False, "rand_perp": True}
    follow = {"olens": {"full", "name_removed", "J_perp", "rand_perp"}, "jlens": {"full", "name_only", "J_only"}, "nla": set()}
    for i in range(n_pairs):
        pid = f"xown-{i + 2:02d}"
        for src in ("A", "B"):
            base = {"pair_id": pid, "family": "ownership", "source": src, "cand_A": "A", "cand_B": "B", "coherent": True}
            x2b.append({**base, "key": f"{pid}|{src}|nat|natural|0.0|None", "site": "nat", "condition": "natural", "alpha": 0.0, "null_k": None, "lo_model": -3.0,
                        "parsed": "A", "flipped_to_other": False, "kept_original": True})
            for a in (0.25, 0.5, 0.75, 1.0):
                fl = a >= 0.5
                x2b.append({**base, "key": f"{pid}|{src}|S2|planted|{a}|None", "site": "S2", "condition": "planted", "alpha": a, "null_k": None, "lo_model": -3.0 + 8 * a,
                            "parsed": "B" if fl else "A", "flipped_to_other": fl, "kept_original": not fl})
        tab = E.y2_condition_table(pid, "ownership", other_pair_ids=[f"xown-{(i + j) % n_pairs + 2:02d}" for j in range(1, 5)])
        for e in tab:
            if e["reused"]:
                continue
            a, cond = e["alpha"], e["condition"]
            fl = flips[cond] and a >= 0.5
            beh.append({**{k: e[k] for k in ("key", "pair_id", "family", "source", "site", "edit_layer", "positions_kind", "alpha", "condition", "k", "other_pair_id", "r_star")},
                        "null_k": e["k"], "cand_A": "A", "cand_B": "B", "parsed": "B" if fl else "A", "flipped_to_other": fl, "kept_original": not fl, "coherent": True,
                        "lo_model": (-3.0 + 8 * a) if flips[cond] else -3.0 + rng.normal(0, 0.3), "frac_norm_in_J": {"J_only": 1.0, "J_perp": 0.0}.get(cond, 0.3),
                        "frac_norm_in_J_full": 0.3})
    allrows = beh + [r for r in x2b]
    for r in allrows:
        cond, a = r["condition"], r["alpha"]
        c = "full" if cond == "planted" else cond
        for rd in ("olens", "nla", "jlens"):
            if cond == "natural":
                v = -2.0
            elif c in follow[rd]:
                v = -2.0 + 4 * a + rng.normal(0, 0.1)
            elif rd == "nla":
                v = -2.0
            else:  # not followed: a small shift AWAY from the planted candidate (win ~ 0), so the <= 0.5 rules are met deterministically
                v = -2.3 + rng.normal(0, 0.1)
            lo_row = {"key": f"{rd}|{r['key']}", "entry_key": r["key"], "reader": rd, "lo_toward_other": float(v), "unscorable": False}
            (x2l if r["site"] in ("nat", "S2") else lo).append(lo_row)
    tmp_path.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name, rows in (("beh", beh), ("lo", lo), ("x2b", x2b), ("x2l", x2l)):
        paths[name] = tmp_path / f"{name}.jsonl"
        paths[name].write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return paths


def test_analyze_decisions_on_synthetic_rows(tmp_path):
    p = synthetic(tmp_path)
    out = tmp_path / "res"
    s = YA.main(["--behaviour", str(p["beh"]), "--lo", str(p["lo"]), "--x2-behaviour", str(p["x2b"]), "--x2-lo", str(p["x2l"]), "--out", str(out),
                 "--allow-unfrozen", "--n-boot", "50", "--frozen-config", str(tmp_path / "nofreeze.json")])
    e12 = s["E12_flip_by_condition_alpha"]
    assert e12["full"]["1.0"]["flip"]["p"] == 1.0 and e12["full"]["1.0"]["n_items"] == 32 and "0.25" not in e12["full"]
    assert e12["name_removed"]["1.0"]["flip"]["p"] == 1.0 and e12["name_only"]["1.0"]["flip"]["p"] == 0.0 and e12["other_pair"]["1.0"]["flip"]["n"] == 32 * 4
    assert e12["rand_perp"]["1.0"]["per_k"] is not None and set(e12["rand_perp"]["1.0"]["per_k"]) == {"0", "1", "2"}
    assert s["site"]["status"] == "WELL-POSED" and s["site"]["other_pair_flips_model"] is False
    assert s["alpha_star"]["n_with_alpha_star"] == 32 and s["alpha_star"]["counts"] == {"0.5": 32} and s["alpha_star"]["n_mapped_up"] == 0
    assert s["classification"] == {"olens": "READS THE BINDING", "nla": "MIXED", "jlens": "READS THE NAME"}
    assert s["jspace_classification"]["jlens"] == "J-SPACE LEAK" and s["jspace_classification"]["olens"] == "READS NON-J" and s["jspace_classification"]["nla"] == "NONE"
    ol = s["E13_follow"]["olens"]["by_condition"]
    assert ol["name_removed"]["alpha_1"]["win"]["p"] >= 0.95 and ol["name_only"]["alpha_1"]["win"]["p"] < 0.7
    assert abs(ol["name_removed"]["alpha_1"]["fraction_median"] - 1.0) < 0.1 and abs(ol["name_removed"]["alpha_star"]["fraction_median"] - 0.5) < 0.1
    assert ol["name_removed"]["above_other_pair_band"] is True and ol["other_pair"]["above_other_pair_band"] is False
    assert s["E13_follow"]["jlens"]["J_perp_inside_rand_perp_band"] is True and s["E13_follow"]["nla"]["by_condition"]["full"]["alpha_1"]["win"]["n"] == 32
    assert s["decisions"]["olens"]["other_pair_moves_reader"] is False
    assert abs(s["delta_J_energy"]["median"] - 0.3) < 1e-9 and s["delta_J_energy"]["r_star"] == 384 and abs(s["delta_J_energy"]["expected_random"] - (384 / 5120) ** 0.5) < 1e-9
    assert (out / "fig_main.png").exists()
    fl = (out / "flips.csv").read_text()
    assert "other_pair" in fl and "pooled" in fl
    fo = (out / "follow.csv").read_text().splitlines()
    assert fo[0].startswith("reader,condition,at,alpha,pair_id") and any(",alpha_star," in l for l in fo)
    # a model that does not flip under name_removed makes the site ill-posed: no reader claim
    rows = [json.loads(l) for l in p["beh"].read_text().splitlines()]
    for r in rows:
        if r["condition"] == "name_removed":
            r["flipped_to_other"], r["parsed"], r["kept_original"] = False, "A", True
    p["beh"].write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    s2 = YA.main(["--behaviour", str(p["beh"]), "--lo", str(p["lo"]), "--x2-behaviour", str(p["x2b"]), "--x2-lo", str(p["x2l"]), "--out", str(tmp_path / "res2"),
                  "--allow-unfrozen", "--n-boot", "20", "--no-fig", "--frozen-config", str(tmp_path / "nofreeze.json")])
    assert s2["site"]["status"] == "ILL-POSED" and set(s2["classification"].values()) == {"ILL-POSED"}


def test_alpha_used_mapping():
    assert YA.alpha_used(0.25, [0.5, 0.75, 1.0]) == 0.5 and YA.alpha_used(0.75, [0.5, 0.75, 1.0]) == 0.75 and YA.alpha_used(None, [0.5]) is None
    assert YA.alpha_used(1.5, [0.5, 0.75, 1.0]) is None


def test_zz_results_and_cache_untouched():
    now = sorted(str(p) for p in (REPO / "results" / "g_agreement" / "y2").rglob("*")) if (REPO / "results" / "g_agreement" / "y2").exists() else None
    assert now == RESULTS_SNAPSHOT
    cache = sorted(str(p) for p in (REPO / "cache" / "g_agreement" / "y").rglob("*")) if (REPO / "cache" / "g_agreement" / "y").exists() else None
    assert cache == CACHE_SNAPSHOT
