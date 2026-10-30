"""CPU tests for the W1 matrix (projects/g_agreement/w_analysis/w1_matrix.py) on a synthetic world that mirrors the S2 / S3 schemas.

Synthetic world (written to tmp_path as the two jsonl files the analysis reads): ownership 8 pairs × 2 sources (L38 edit, read 42),
mapping 8 pairs × 2 sources (L38, read 42), errors 16 items (L48 edit, read-backs 42 and 48). Directions d_cm, d_pw, d_J, d_res, full at
α ∈ {0.5, 1.0} and K = 4 random directions at α 1; one natural row per state. The model flips under the full swap everywhere, under d_cm
rarely on ownership (P3 gap) and mostly on errors (layer-48 clause true), never under d_pw / random. Reader profiles (lo_toward_edit shifts
relative to the natural −1 / −1 of each pair, sep = 2):
  class-mean reader : d_cm +2, full +3, d_pw −0.2 + noise, d_J / d_res / random noise only   → P1 true, P2 true (reader half)
  probe             : d_cm +2, d_pw +2, full +3, others noise                                 → P2 true (probe half)
  "pw-follower"     : like class-mean but d_pw +2                                               → P2 false
  "flat"            : noise everywhere                                                          → P1 false (rule 3)
NLA and skip-lens A have error read-backs at layer 42 only (as the real S3), so their error cells are 'not evaluable'.
All paths are tmp_path; nothing under results/ or cache/ is written.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_w1.py -q``
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from projects.g_agreement.w_analysis import w1_matrix as W1  # noqa: E402

W1_DIR = REPO / "results" / "g_agreement" / "w" / "w1"
BEH_REAL = REPO / "cache" / "g_agreement" / "w" / "s2_behaviour.jsonl"
BEH_STAT = (BEH_REAL.stat().st_size, BEH_REAL.stat().st_mtime_ns) if BEH_REAL.exists() else None

READERS = ("jlens", "olens", "nla", "skip_a", "probe")
ERR48 = {"jlens", "olens", "probe"}  # readers scored on the error read-backs at layer 48 (as the real S3)
N_PAIRS, N_ERR, K_RANDOM = 8, 16, 4
NAT_READER = -1.0  # lo_toward_edit at the natural state (own favoured); sep = 2
NAT_MODEL = -6.0

FLIP_P = {  # P(flip) per (family, direction) at α 1; α 0.5 halves it
    "ownership": {"d_cm": 0.25, "d_pw": 0.0, "d_J": 0.0, "d_res": 0.1, "full": 1.0, "random": 0.0},
    "mapping": {"d_cm": 0.9, "d_pw": 0.0, "d_J": 0.1, "d_res": 0.2, "full": 1.0, "random": 0.0},
    "errors": {"d_cm": 0.75, "d_pw": 0.0, "d_J": 0.0, "d_res": 0.1, "full": 1.0, "random": 0.0},
}
CLASS_MEAN = {"d_cm": 2.0, "full": 3.0, "d_pw": -0.2}
PROBE = {"d_cm": 2.0, "d_pw": 2.0, "full": 3.0}
PW_FOLLOWER = {"d_cm": 2.0, "d_pw": 2.0, "full": 3.0}
FLAT = {}
PROFILES_OK = {"jlens": CLASS_MEAN, "olens": CLASS_MEAN, "nla": CLASS_MEAN, "skip_a": CLASS_MEAN, "probe": PROBE}


def _states():
    out = []
    for fam in ("ownership", "mapping"):
        for i in range(N_PAIRS):
            for src in ("A", "B"):
                out.append((fam, f"x{fam[:3]}-{i:02d}", src))
    for i in range(N_ERR):
        out.append(("errors", f"xpz-{i:04d}", "A"))
    return out


def _edits():
    for d in ("d_cm", "d_pw", "d_J", "d_res", "full"):
        for a in (0.5, 1.0):
            yield d, a, None
    for k in range(K_RANDOM):
        yield "random", 1.0, k


def make_world(tmp_path: Path, profiles: dict, seed: int = 0, err48=ERR48, noise: float = 0.3):
    """Writes s2_behaviour.jsonl and s3_lo.jsonl; returns (beh_path, lo_path, truth) with truth['flip'][key]."""
    rng = np.random.default_rng(seed)
    beh, lo, truth = [], [], {"flip": {}}
    for fam, pid, src in _states():
        own, oth = ("P", "Q") if src == "A" else ("Q", "P")
        edit_layer = 48 if fam == "errors" else 38
        read_layers = [42, 48] if fam == "errors" else [42]
        base = {"pair_id": pid, "family": fam, "source": src, "state_item_id": pid + src, "site": "W2", "cand_A": own, "cand_B": oth, "edit_layer": edit_layer,
                "read_layers": read_layers, "coherent": True, "lo_model_unscorable": False, "toward": 1.0}
        nat_key = f"{pid}|{src}|W2|natural|0.0|None"
        beh.append({**base, "key": nat_key, "direction": "natural", "condition": "natural", "alpha": 0.0, "k": None, "flipped_to_other": False, "lo_model": NAT_MODEL})
        rows = [(nat_key, "natural", 0.0)]
        for d, a, k in _edits():
            key = f"{pid}|{src}|W2|{d}|{float(a)}|{k}"
            p = FLIP_P[fam][d] * (a if d != "random" else 1.0)
            flip = bool(rng.random() < p)
            dlo = (10.0 if flip else 2.0) * a + rng.normal(0, 0.5)
            coherent = not (d == "d_res" and k is None and a == 1.0 and rng.random() < 0.1)
            beh.append({**base, "key": key, "direction": d, "condition": d, "alpha": a, "k": k, "flipped_to_other": flip, "coherent": coherent, "lo_model": NAT_MODEL + dlo})
            truth["flip"][key] = flip and coherent
            rows.append((key, d, a))
        for rd, prof in profiles.items():
            layers = [42] if fam != "errors" else ([42, 48] if rd in err48 else [42])
            for L in layers:
                for key, d, a in rows:
                    if d == "natural":
                        v = NAT_READER
                    elif L < edit_layer:
                        v = NAT_READER  # a read-back below the edit layer cannot see the edit
                    else:
                        v = NAT_READER + prof.get(d, 0.0) * a + rng.normal(0, noise)
                    unit = "S2" if L == 42 else f"S2@L{L}"
                    row = {"key": f"{rd}|{unit}|{key}", "entry_key": key, "reader": rd, "unit": unit, "read_layer": L, "pair_id": pid, "family": fam, "source": src,
                           "direction": d, "alpha": a, "cand_A": own, "cand_B": oth, "candidates": [own, oth], "lo_own": -v, "lo_toward_edit": v, "lo_toward_other": v}
                    if rd == "probe":
                        row.update(score_edited=-v, score_read=-(NAT_READER + 0.5 * (v - NAT_READER)), probe_on="edited_site_mean")
                    lo.append(row)
    bp, lp = tmp_path / "s2_behaviour.jsonl", tmp_path / "s3_lo.jsonl"
    bp.write_text("\n".join(json.dumps(r) for r in beh) + "\n", encoding="utf-8")
    lp.write_text("\n".join(json.dumps(r) for r in lo) + "\n", encoding="utf-8")
    return bp, lp, truth


def _args(tmp_path: Path, bp: Path, lp: Path | None, **kw):
    argv = ["--behaviour", str(bp), "--out", str(tmp_path / "out"), "--n-boot", str(kw.get("n_boot", 200)), "--seed", "0", "--no-fig"]
    if lp is not None:
        argv += ["--lo", str(lp)]
    for k, v in kw.items():
        if k not in ("n_boot",):
            argv += [f"--{k.replace('_', '-')}"] + ([] if v is True else [str(v)])
    return argv


@pytest.fixture(scope="module")
def ok_run(tmp_path_factory):
    tp = tmp_path_factory.mktemp("w1ok")
    bp, lp, truth = make_world(tp, PROFILES_OK)
    res = W1.main(_args(tp, bp, lp))
    return tp, bp, lp, truth, res


# --------------------------------------------------------------------------------------
def test_loading_and_read_layer_policy(ok_run):
    tp, bp, lp, truth, res = ok_run
    w = W1.load_behaviour(bp)
    assert len(w.nat) == 2 * 2 * N_PAIRS + N_ERR
    assert len(w.edited) == len(w.nat) * (10 + K_RANDOM)
    W1.attach_lo(w, lp)
    assert w.readers == list(READERS)
    assert w.read_layer[("jlens", "ownership")] == 42 and w.read_layer[("jlens", "errors")] == 48
    assert w.read_layer[("nla", "errors")] is None and w.read_layer[("skip_a", "errors")] is None
    assert any("nla/errors" in n for n in w.read_layer_notes)
    # shifts and separation
    st = ("xown-00", "A")
    assert w.separation("jlens", st) == pytest.approx(2.0)
    assert w.separation("probe", ("xpz-0000", "A")) is None
    row = [r for r in w.edited if r["key"] == "xown-00|A|W2|d_cm|1.0|None"][0]
    assert w.shift("jlens", row) == pytest.approx(w.lo[("jlens", 42, row["key"])] - NAT_READER)


def test_model_side_matches_truth(ok_run):
    tp, bp, lp, truth, res = ok_run
    w = W1.load_behaviour(bp)
    for fam in ("ownership", "mapping", "errors"):
        rows = w.entries(fam, "full", 1.0)
        c = W1.cell(res["matrix"], fam, "full", "model")
        k = sum(truth["flip"][r["key"]] for r in rows)
        assert c["flip_k"] == k and c["flip_n"] == len(rows)
        assert c["flip"] == pytest.approx(k / len(rows))
        assert c["flip_lo"] <= c["flip"] <= c["flip_hi"]
        # Δ lo_model vs natural: the simulated shift (10 if flip else 2) ± noise
        assert 6 < c["dlo_mean"] < 11 and c["dlo_lo"] <= c["dlo_mean"] <= c["dlo_hi"]
    m = W1.cell(res["matrix"], "ownership", "d_pw", "model")
    assert m["flip_k"] == 0 and m["flip"] == 0.0 and m["flip_hi"] > 0  # Wilson CI is not degenerate at 0/n
    # incoherent flips do not count
    rows = w.entries("ownership", "d_res", 1.0)
    inc = [r for r in rows if r["coherent"] is False]
    assert W1.cell(res["matrix"], "ownership", "d_res", "model")["n_incoherent"] == len(inc)


def test_p1_p2_p3_true_on_the_class_mean_world(ok_run):
    tp, bp, lp, truth, res = ok_run
    s = res["summary"]
    assert s["P1"]["holds"] is True
    assert s["P2"]["holds"] is True
    assert s["P3"]["holds"] is True and s["P3"]["families"]["ownership"]["ok"]
    assert s["layer48_clause"]["ge_050"] is True
    assert s["rule_applied"].startswith("rule 1")
    assert s["headline"].startswith("readers read class-mean directions; the model uses more")
    assert "load-bearing along d_cm at layer 48" in s["headline"]
    for rd in READERS:
        c = W1.cell(res["matrix"], "pooled", "d_cm", rd)
        assert c["follow"] >= 0.9, (rd, c["follow"])
        assert c["follow_lo"] <= c["follow"] <= c["follow_hi"]
    for rd in ("jlens", "olens", "nla", "skip_a"):
        c = W1.cell(res["matrix"], "pooled", "d_pw", rd)
        assert c["follow"] <= 0.5 and c["follow"] <= c["random_p95"]
    assert W1.cell(res["matrix"], "pooled", "d_pw", "probe")["follow"] >= 0.9
    # not-evaluable cells for NLA / skip-lens A on errors; the pooled row is over the evaluable families only
    assert np.isnan(W1.cell(res["matrix"], "errors", "d_cm", "nla")["follow"])
    assert W1.cell(res["matrix"], "pooled", "d_cm", "nla")["families_evaluable"] == "ownership+mapping"
    # fraction of own separation: d_cm shift 2 over sep 2 ≈ 1, full ≈ 1.5
    c = W1.cell(res["matrix"], "ownership", "d_cm", "jlens")
    assert 0.8 < c["frac_sep_median"] < 1.2 and 0.55 < c["frac_full_median"] < 0.8
    assert np.isnan(W1.cell(res["matrix"], "errors", "d_cm", "jlens")["frac_sep_median"])
    # random band: ten... here four directions, p95 ≤ max, pooled rate near 0.5 for noise readers
    b = s["random_band"]["jlens|ownership"]
    assert len(b["random_per_k"]) == K_RANDOM and b["random_p95"] <= b["random_max"] + 1e-9 and 0.25 < b["random_pooled"] < 0.75


def test_dauroc_and_reader_differences(ok_run):
    tp, bp, lp, truth, res = ok_run
    s = res["summary"]
    # the probe separates flips from non-flips beyond the dose on ownership? No: the dose cell already codes direction×α, so ΔAUROC ≈ 0 or below.
    g = s["gain_over_dose_per_family"]["jlens"]["ownership"]
    assert g["n_entries"] > 0 and not np.isnan(g["auroc_reader"]) and g["verdict"] in ("beats dose", "does not beat dose", "indistinguishable from dose")
    # the probe vs a lens reader on the d_pw row: Δwin ≥ 10 points with CI excluding 0 → threshold met
    met = {(r["family"], r["direction"], r["reader_a"], r["reader_b"]) for r in res["differences"] if r["dwin_met"]}
    assert ("pooled", "d_pw", "jlens", "probe") in met
    # two class-mean readers on d_cm: no difference
    same = [r for r in res["differences"] if (r["family"], r["direction"], r["reader_a"], r["reader_b"]) == ("pooled", "d_cm", "jlens", "olens")][0]
    assert not same["dwin_met"] and abs(same["dwin"]) < 0.1


def test_outputs_written(ok_run):
    tp, bp, lp, truth, res = ok_run
    out = tp / "out"
    for f in ("w1.md", "matrix.csv", "matrix_alpha0.5.csv", "w1_summary.json", "reader_differences.csv", "log.md"):
        assert (out / f).exists(), f
    md = (out / "w1.md").read_text(encoding="utf-8")
    assert md.count("\n") <= 60
    assert "HEADLINE" in md and "readers read class-mean directions" in md
    with open(out / "matrix.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert {r["column"] for r in rows} == set(READERS) | {"model"}
    assert {r["family"] for r in rows} == {"ownership", "mapping", "errors", "pooled"}
    assert all(r["alpha"] == "1.0" for r in rows)
    with open(out / "matrix_alpha0.5.csv", encoding="utf-8") as f:
        rows05 = list(csv.DictReader(f))
    assert {r["alpha"] for r in rows05 if r["direction"] != "random"} == {"0.5"}
    js = json.loads((out / "w1_summary.json").read_text(encoding="utf-8"))
    assert js["P1"]["holds"] is True and js["mode"] == "readers"


def test_figure(tmp_path):
    bp, lp, _ = make_world(tmp_path, PROFILES_OK)
    argv = _args(tmp_path, bp, lp, n_boot=50)
    argv.remove("--no-fig")
    W1.main(argv)
    assert (tmp_path / "out" / "fig_matrix.png").stat().st_size > 10_000


def test_p2_false_when_a_reader_follows_d_pw(tmp_path):
    prof = dict(PROFILES_OK, jlens=PW_FOLLOWER)
    bp, lp, _ = make_world(tmp_path, prof)
    res = W1.main(_args(tmp_path, bp, lp))
    s = res["summary"]
    assert s["P1"]["holds"] is True and s["P2"]["holds"] is False
    assert s["P2"]["cells"]["jlens"]["pooled"]["ok"] is False and s["P2"]["cells"]["jlens"]["pooled"]["le_060"] is False
    assert s["rule_applied"].startswith("none")


def test_p1_false_stops(tmp_path):
    prof = dict(PROFILES_OK, nla=FLAT)
    bp, lp, _ = make_world(tmp_path, prof)
    res = W1.main(_args(tmp_path, bp, lp))
    s = res["summary"]
    assert s["P1"]["holds"] is False and s["P1"]["cells"]["nla"]["pooled"] is False
    assert s["rule_applied"] == "rule 3 (P1 fails)" and "class-mean hypothesis is wrong" in s["headline"]


def test_model_only_mode(tmp_path):
    bp, lp, _ = make_world(tmp_path, PROFILES_OK)
    res = W1.main(_args(tmp_path, bp, None))
    s = res["summary"]
    assert s["mode"] == "model-only" and s["readers"] == []
    assert s["P1"]["holds"] is None and s["P2"]["holds"] is None and s["P3"]["holds"] is True
    assert s["layer48_clause"]["ge_050"] is True and s["rule_applied"] == "none (model-only)"
    assert {r["column"] for r in res["matrix"]} == {"model"}
    md = (tmp_path / "out" / "w1.md").read_text(encoding="utf-8")
    assert "model-only" in md and md.count("\n") <= 60
    assert not (tmp_path / "out" / "reader_differences.csv").exists()


def test_probe_on_switch_and_below_edit_flag(tmp_path):
    bp, lp, _ = make_world(tmp_path, PROFILES_OK)
    w = W1.load_behaviour(bp)
    W1.attach_lo(w, lp, probe_on="read")
    key = "xown-00|A|W2|d_cm|1.0|None"
    w2 = W1.load_behaviour(bp)
    W1.attach_lo(w2, lp, probe_on="auto")
    a, b = w.lo[("probe", 42, key)], w2.lo[("probe", 42, key)]
    assert a != b and (a - NAT_READER) == pytest.approx(0.5 * (b - NAT_READER))
    w3 = W1.load_behaviour(bp)
    W1.attach_lo(w3, lp, allow_below_edit=True)
    assert w3.read_layer[("nla", "errors")] == 42 and any("BELOW" in n for n in w3.read_layer_notes)
    # a read-back below the edit layer never moves → follow rate 0 on those rows (ties do not follow)
    fl = W1.follow_flags(w3, "nla", w3.entries("errors", "d_cm", 1.0))
    assert all(f is False for _, f in fl)


def test_headline_rules_directly():
    l48_lo = {"flip_d_cm_errors": 0.1, "ci": [0.0, 0.3], "ge_050": False}
    l48_hi = {"flip_d_cm_errors": 0.8, "ci": [0.6, 0.9], "ge_050": True}
    assert W1.headline(True, True, True, l48_hi, None)[1].startswith("rule 1")
    assert "rewritten" in W1.headline(True, True, True, l48_hi, None)[0]
    assert "Rule 2" in W1.headline(True, True, True, l48_lo, True)[0] and "withdraw" in W1.headline(True, True, True, l48_lo, True)[0]
    assert W1.headline(False, True, True, l48_hi, True)[1] == "rule 3 (P1 fails)"
    assert W1.headline(None, None, None, None, None)[1] == "none (model-only)"
    assert W1.headline(True, False, True, None, None)[1].startswith("none")


def test_determinism(tmp_path):
    bp, lp, _ = make_world(tmp_path, PROFILES_OK)
    r1 = W1.main(_args(tmp_path, bp, lp, n_boot=100))
    r2 = W1.main(_args(tmp_path, bp, lp, n_boot=100))
    for a, b in zip(r1["matrix"], r2["matrix"]):
        for k in ("follow", "follow_lo", "follow_hi", "flip", "dlo_mean", "dlo_lo", "dauroc", "dauroc_lo"):
            if k in a:
                assert (np.isnan(a[k]) and np.isnan(b[k])) or a[k] == b[k], k


def test_zz_real_inputs_untouched():
    """The real behaviour file is read-only for this module; the tests never write under results/."""
    if BEH_REAL.exists():
        assert (BEH_REAL.stat().st_size, BEH_REAL.stat().st_mtime_ns) == BEH_STAT
