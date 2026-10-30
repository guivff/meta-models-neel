"""CPU tests for the Friday R1 re-analysis (projects/g_agreement/x_friday_r1.py) on a synthetic tiny X2 world.

The world is built from integers so every quantity is exact: each reader's LO at a planted dose is
lo_nat(this) + alpha * sep, so the fraction of the reader's own natural separation is exactly alpha, and exactly 1.0
at alpha 1 (S2/S3). All paths are tmp_path; nothing under results/ or cache/ is read or written.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_x_friday_r1.py -q``
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from projects.g_agreement import x_friday_r1 as R  # noqa: E402

# x2/ only: another analysis may be writing elsewhere under results/g_agreement concurrently
RESULTS_SNAPSHOT = sorted(str(p) for p in (REPO / "results" / "g_agreement" / "x2").rglob("*")) if (REPO / "results" / "g_agreement" / "x2").exists() else None
CACHE_SNAPSHOT = sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None

READERS = ("olens", "nla", "jlens")
# pair -> (own answer of A, own answer of B); natural lo_own per state per reader (integers), model natural lo_own (A, B)
PAIRS = {"p1": ("Ann", "Bob"), "p2": ("Cat", "Dan"), "p3": ("Eve", "Fay")}
# reader natural lo_own: p1 ordered in both states; p2 pair-ordered only (constant candidate bias); p3 misordered (sep < 0)
NAT_OWN = {
    "olens": {"p1": (3, 5), "p2": (-1, 4), "p3": (-2, -1)},
    "nla": {"p1": (2, 2), "p2": (-2, 3), "p3": (1, -4)},
    "jlens": {"p1": (1, 1), "p2": (-1, 2), "p3": (-1, -1)},
}
MODEL_OWN = {"p1": (10, 12), "p2": (8, 9), "p3": (11, 7)}
# the model's flip dose per (pair, source) at S2 / S3; S1 never flips
ASTAR = {("p1", "A"): 0.5, ("p1", "B"): 0.75, ("p2", "A"): 0.75, ("p2", "B"): 0.5, ("p3", "A"): 0.75, ("p3", "B"): None}
LADDER = {"S1": [0.5, 1.0, 1.5, 2.0, 3.0, 4.0], "S2": [0.25, 0.5, 0.75, 1.0], "S3": [0.25, 0.5, 0.75, 1.0]}
K_NULL, K_OTHER = 3, 2


def _entry(pair, src, site, cond, alpha, null_k=None, other=None):
    key = f"{pair}|{src}|{site}|{cond}|{alpha}|{null_k}" + (f"|{other}" if other else "")
    a_own, b_own = PAIRS[pair]
    own, oth = (a_own, b_own) if src == "A" else (b_own, a_own)
    return key, {"key": key, "pair_id": pair, "family": "ownership" if pair != "p3" else "mapping", "source": src, "site": site, "alpha": alpha, "condition": cond,
                 "null_k": null_k, "other_pair_id": other, "cand_A": own, "cand_B": oth}


def _model_lo_toward_other(pair, src, alpha, cond):
    """natural lo_model (toward other) + a walk: planted = alpha * sep (exact), nulls = 0."""
    a_own, b_own = MODEL_OWN[pair]
    this_own, other_own = (a_own, b_own) if src == "A" else (b_own, a_own)
    nat = -this_own
    sep = this_own + other_own
    if cond == "planted":
        return nat + alpha * sep
    return nat + (0.5 if cond == "null_other" else 0.0)


def build_world(tmp: Path):
    beh, lo = [], []
    for pair in PAIRS:
        for src in ("A", "B"):
            entries = [(_entry(pair, src, "nat", "natural", 0.0), "natural", 0.0)]
            for site, ladder in LADDER.items():
                for a in ladder:
                    entries.append((_entry(pair, src, site, "planted", a), "planted", a))
                na = 2.0 if site == "S1" else 1.0
                for k in range(K_NULL):
                    entries.append((_entry(pair, src, site, "null", na, null_k=k), "null", na))
                if site == "S1":
                    for k in range(K_OTHER):
                        entries.append((_entry(pair, src, site, "null_other", na, null_k=k, other="p1" if pair != "p1" else "p2"), "null_other", na))
            for (key, e), cond, a in entries:
                site = e["site"]
                flipped = cond == "planted" and site in ("S2", "S3") and ASTAR[(pair, src)] is not None and a >= ASTAR[(pair, src)]
                lo_model = _model_lo_toward_other(pair, src, a if site != "S1" else 0.0, cond if site != "S1" else "null")
                beh.append({**e, "answer_text": e["cand_B"] if flipped else e["cand_A"], "parsed": e["cand_B"] if flipped else e["cand_A"],
                            "flipped_to_other": bool(flipped), "coherent": True, "lo_model": lo_model, "lo_model_unscorable": False})
                for rd in READERS:
                    a_own, b_own = NAT_OWN[rd][pair]
                    this_own, other_own = (a_own, b_own) if src == "A" else (b_own, a_own)
                    nat = -this_own
                    sep = this_own + other_own
                    if cond == "planted" and site in ("S2", "S3"):
                        v = nat + a * sep                     # exact linear walk: fraction == alpha
                    elif cond == "planted":                    # S1: a small reader-side move, no flip
                        v = nat + 0.25 * a
                    elif cond == "null_other":
                        v = nat + 0.125
                    else:
                        v = nat
                    lo.append({"key": f"{rd}|{key}", "entry_key": key, "reader": rd, "pair_id": pair, "source": src, "site": site, "alpha": a, "condition": cond,
                               "cand_A": e["cand_A"], "cand_B": e["cand_B"], "lo_own": -v, "lo_toward_other": v, "unscorable": False})
    bp, lp = tmp / "x2_behaviour.jsonl", tmp / "x2_lo.jsonl"
    bp.write_text("\n".join(json.dumps(r) for r in beh) + "\n")
    lp.write_text("\n".join(json.dumps(r) for r in lo) + "\n")
    return bp, lp


def _read_csv(p: Path):
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def world_run(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("r1")
    bp, lp = build_world(tmp)
    out_f, out_x2 = tmp / "friday", tmp / "x2"
    summary = R.run(bp, lp, out_f, out_x2, follow_csv=None, n_boot=50, seed=0, make_figure=True)
    return tmp, out_f, out_x2, summary


def test_results_and_cache_untouched(world_run):
    if RESULTS_SNAPSHOT is not None:
        assert sorted(str(p) for p in (REPO / "results" / "g_agreement" / "x2").rglob("*")) == RESULTS_SNAPSHOT
    if CACHE_SNAPSHOT is not None:
        assert sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) == CACHE_SNAPSHOT


def test_separation_is_pair_symmetric_and_mirrored(world_run):
    tmp, *_ = world_run
    w = R.load_world(tmp / "x2_behaviour.jsonl", tmp / "x2_lo.jsonl")
    for rd in READERS:
        sep = R.separation(w, rd)
        for pair, (a, b) in NAT_OWN[rd].items():
            assert sep[(pair, "A")] == sep[(pair, "B")] == a + b
    od_both, od_pair = R.ordered(w, "olens", "both"), R.ordered(w, "olens", "pair")
    assert od_both == {"p1": True, "p2": False, "p3": False}
    assert od_pair == {"p1": True, "p2": True, "p3": False}


def test_fraction_is_exactly_alpha_and_one_at_alpha_1(world_run):
    tmp, out_f, out_x2, summary = world_run
    rows = _read_csv(out_f / "r1_fraction.csv")
    assert {r["site"] for r in rows} == {"S1", "S2", "S3"}
    for r in rows:
        if r["site"] in ("S2", "S3"):
            a = float(r["alpha"])
            assert float(r["median"]) == a, r          # exact by construction (integer world)
            assert float(r["q25"]) == a and float(r["q75"]) == a
            assert int(r["n"]) == 6                     # 3 pairs x 2 states, all scorable
    assert summary["sanity_fraction_at_alpha_1"] == {f"{s}|{rd}": 1.0 for s in ("S2", "S3") for rd in list(READERS) + [R.MODEL]}
    # the model's fraction uses lo_model the same way
    assert all(float(r["median"]) == float(r["alpha"]) for r in rows if r["reader"] == R.MODEL and r["site"] == "S2")


def test_alpha_star_and_conditional_table_shape(world_run):
    tmp, out_f, out_x2, summary = world_run
    w = R.load_world(tmp / "x2_behaviour.jsonl", tmp / "x2_lo.jsonl")
    assert R.alpha_star(w, "S2") == ASTAR
    assert all(v is None for v in R.alpha_star(w, "S1").values())
    cond = _read_csv(out_f / "r1_conditional.csv")
    assert set(cond[0].keys()) == {"reader", "site", "definition", "ordered", "k", "n", "win", "lo", "hi", "n_pairs", "n_pairs_ordered_total"}
    assert len(cond) == 3 * 4 * 2 * 2                   # sites x (readers + model) x definitions x {yes, no}
    assert {(r["reader"], r["site"], r["definition"], r["ordered"]) for r in cond} == {(rd, s, d, o) for rd in list(READERS) + ["model"] for s in ("S1", "S2", "S3") for d in ("both", "pair") for o in ("yes", "no")}
    # with an exact linear walk, win at alpha* <=> sep > 0, i.e. the 'pair' ordering predicts the win perfectly
    for r in cond:
        if r["site"] == "S2" and r["definition"] == "pair" and r["reader"] in READERS and int(r["n"]):
            assert float(r["win"]) == (1.0 if r["ordered"] == "yes" else 0.0), r
    s2_nla = {r["ordered"]: r for r in cond if r["site"] == "S2" and r["definition"] == "pair" and r["reader"] == "nla"}
    assert int(s2_nla["yes"]["n"]) == 4 and int(s2_nla["no"]["n"]) == 1   # 5 flipping states: p1 (2) + p2 (2) ordered, p3 A misordered
    # S1 has no alpha*, so every S1 row is empty
    assert all(int(r["n"]) == 0 for r in cond if r["site"] == "S1")


def test_per_pair_and_s1_preview_outputs(world_run):
    tmp, out_f, out_x2, summary = world_run
    pp = _read_csv(out_x2 / "per_pair.csv")
    assert len(pp) == 6 and {(r["pair_id"], r["source"]) for r in pp} == set(ASTAR)
    row = {(r["pair_id"], r["source"]): r for r in pp}[("p1", "A")]
    assert row["alpha_star_S2"] == "0.5" and row["alpha_star_S1"] == "" and row["subflip_alpha_S2"] == "0.25"
    assert float(row["olens_sep"]) == 8 and float(row["olens_frac_at_astar_S2"]) == 0.5 and float(row["olens_frac_at_subflip_S2"]) == 0.25
    assert row["olens_win_at_astar_S2"] == "True" and row["olens_ordered_both"] == "True"
    assert float(row["lo_model_nat"]) == -10 and float(row["lo_model_at_astar_S2"]) == -10 + 0.5 * 22
    for col in ("olens_lo_own_nat_this", "olens_lo_own_nat_other", "nla_sep", "jlens_frac_at_astar_S2", "jlens_win_at_astar_S2", "model_frac_at_astar_S2"):
        assert col in row
    no_flip = {(r["pair_id"], r["source"]): r for r in pp}[("p3", "B")]
    assert no_flip["alpha_star_S2"] == "" and no_flip["olens_frac_at_astar_S2"] == "" and no_flip["olens_win_at_astar_S2"] == ""
    s1 = _read_csv(out_f / "r1_s1_otherpair.csv")
    assert {(r["reader"], r["condition"]) for r in s1} == {(rd, c) for rd in list(READERS) + ["model"] for c in ("planted", "null", "null_other")}
    by = {(r["reader"], r["condition"]): r for r in s1}
    assert int(by[("olens", "null")]["n"]) == 6 * K_NULL and int(by[("olens", "null_other")]["n"]) == 6 * K_OTHER and int(by[("olens", "planted")]["n"]) == 6
    assert float(by[("olens", "planted")]["mean_shift"]) == 0.5 and float(by[("olens", "null_other")]["mean_shift"]) == 0.125 and float(by[("olens", "null")]["mean_shift"]) == 0.0
    assert all(int(r["model_flips_k"]) == 0 for r in s1)
    assert "NOTHING FLIPS" in summary["s1_otherpair"]["note"]
    assert (out_x2 / "fig_fraction.png").exists() and (out_f / "R1.md").exists() and (out_f / "r1_summary.json").exists()
    assert not (out_x2 / "fig_main.png").exists()
    assert len((out_f / "R1.md").read_text().splitlines()) <= 25
