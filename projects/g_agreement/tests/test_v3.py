"""V3 (PREREG_WV.md) tests on synthetic claim tables: the lexical matcher, the sensitivity proxies on a planted generic vs
specific claim, the claim-table loader on a tiny data directory in his schema, the control inventory, LOFO scoring, and the
item-level bootstrap on a planted effect. Nothing is read from nla-consistency/ or written under results/.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_v3.py -q``
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from projects.g_agreement.v3_sensitivity import analyze as AN  # noqa: E402
from projects.g_agreement.v3_sensitivity import claims as CL  # noqa: E402

GENERIC = "The next token must begin the second line of the couplet."
SPECIFIC = "The prompt asks for the chemical symbol of iron, Fe."


def _write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def _tiny_data(tmp_path: Path) -> Path:
    """Two families × 4 items; every item's samples contain GENERIC, only item p0 (and its claims) carries SPECIFIC content."""
    d = tmp_path / "data"
    rng = np.random.default_rng(0)
    fillers = ["Narrative prose in the past tense.", "A trivia question expecting a short factual answer.",
               "The register is formal and expository.", "A rhyming couplet about the sea and the sky."]
    samples, claims = [], {}
    for fam in ("poetry", "multihop"):
        for k in range(4):
            iid = f"{fam[0]}{k}"
            ss = []
            for _ in range(8):
                parts = [GENERIC, rng.choice(fillers)]
                if fam == "poetry" and k == 0:
                    parts.append(SPECIFIC)
                ss.append(" ".join(parts))
            samples.append(dict(family=fam, id=iid, samples=ss, adjacent_readouts=ss[:3]))
            cl = [dict(claim=GENERIC, label="workspace", evidence=""), dict(claim="The text is in German.", label="contradicted", evidence=""),
                  dict(claim="The text is prose.", label="background_true", evidence="")]
            if fam == "poetry" and k == 0:
                cl.append(dict(claim=SPECIFIC, label="workspace", evidence=""))
            claims[(fam, iid)] = cl
    _write_jsonl(d / "nla_samples.jsonl", samples)
    for fam in ("poetry", "multihop"):
        _write_jsonl(d / "claims" / f"{fam}.jsonl", [dict(id=i, claims=c) for (f, i), c in claims.items() if f == fam])
    sig = []
    for (fam, iid), cl in claims.items():
        for n, c in enumerate(cl):
            internal = None
            if c["label"] == "workspace":
                internal = "correct" if c["claim"] == SPECIFIC else "wrong"
            sig.append(dict(key=f"{fam}|{iid}|{n}", sample_support_of_8=8 if c["label"] == "workspace" else 1,
                            adjacent_support_of_3=1, internal_label=internal))
    _write_jsonl(d / "claim_signals.jsonl", sig)
    _write_jsonl(d / "prior_consistency.jsonl", [
        dict(key="noise|0", r=dict(claims=[dict(claim="The text is an academic seminar note.", support=6), dict(claim=GENERIC, support=7)])),
        dict(key="noise|1", r=dict(claims=[dict(claim="A film synopsis.", support=1)])),
        dict(key="mean|0", r=dict(claims=[dict(claim="x", support=3)])),
        dict(key="real|poetry|p0", r=dict(claims=[dict(claim="y", support=7)])),
    ])
    return d


def test_tokens_and_stem():
    assert CL.stem("targets") == "target" and CL.stem("waiting") == "wait" and CL.stem("is") == "is"
    assert CL.tokens("The Next tokens, 16 — of the couplet!") == ["token", "16", "couplet"]


def test_matcher_recall_bounds_and_idf_weighting():
    docs = ["iron is a metal", "iron is a metal", "iron is a metal", "the symbol Fe stands for iron"]
    m = CL.TermMatcher(docs)
    R = m.recall_matrix(["iron symbol Fe", "iron", "", "zzzz unseen"], docs)
    assert R.shape == (4, 4) and R.min() >= 0 and R.max() <= 1
    assert R[1].tolist() == [1, 1, 1, 1]                     # single term present everywhere
    assert R[0, 3] == pytest.approx(1.0) and 0 < R[0, 0] < 0.5  # rare terms (symbol, fe) weigh more than 'iron'
    assert R[2].max() == 0 and R[3].max() == 0               # no terms / unseen terms never match


def test_claim_table_and_sensitivity_on_tiny_data(tmp_path):
    d = _tiny_data(tmp_path)
    df, inv = CL.build(d)
    assert len(df) == 2 * 4 * 3 + 1 and set(df.family) == {"poetry", "multihop"}
    assert (df.input_type == "input").sum() == 25   # every claim here is workspace / background_true / contradicted
    assert df.y_internal.notna().sum() == 9 and df.y_internal.sum() == 1
    assert inv["per_state_control_readouts"] is False and inv["n_noise_vectors"] == 2 and inv["n_noise_claims"] == 3
    assert inv["noise_share_ge6_of_7"] == pytest.approx(2 / 3)
    gen = df[df.claim == GENERIC]; spec = df[df.claim == SPECIFIC].iloc[0]
    assert (gen.own_proxy8 == 8).all() and spec.own_proxy8 == 8
    assert np.allclose(gen.sens_family, 0.0) and np.allclose(gen.sens_all, 0.0)
    assert spec.sens_family == pytest.approx(1.0) and spec.sens_all == pytest.approx(1.0)
    assert gen.sens_noise.iloc[0] == pytest.approx(0.0) and spec.sens_noise > 0.5
    german = df[df.claim == "The text is in German."].iloc[0]
    assert german.own_proxy8 == 0 and german.sens_family == pytest.approx(1.0)


def test_auroc_ties_and_lofo_scores():
    assert AN.auroc([1, 1, 0, 0], [0.9, 0.8, 0.2, 0.1]) == 1.0
    assert AN.auroc([1, 0], [0.5, 0.5]) == 0.5
    assert np.isnan(AN.auroc([1, 1], [0.1, 0.2]))
    rng = np.random.default_rng(1)
    n = 400
    y = rng.integers(0, 2, n).astype(float)
    X = np.c_[y + rng.normal(0, 0.5, n), rng.normal(0, 1, n)]
    groups = np.array(["a", "b", "c", "d"])[np.arange(n) % 4]
    s = AN.lofo_scores(X, y, groups)
    assert s.shape == (n,) and not np.isnan(s).any() and AN.auroc(y, s) > 0.9
    # a training fold with a single class leaves its test fold NaN
    y2 = y.copy(); y2[groups != "a"] = 1.0
    s2 = AN.lofo_scores(X, y2, groups)
    assert np.isnan(s2[groups == "a"]).all()


def _synthetic_table(n_items=60, effect=1.5, seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    fams = CL.FAMS
    for i in range(n_items):
        fam = fams[i % len(fams)]
        for n in range(6):
            y = float(rng.random() < 0.6)
            rec = np.clip(rng.normal(0.6 + 0.3 * y, 0.25), 0, 1)
            sens = np.clip(rng.normal(0.5 + effect * 0.2 * (y - 0.5), 0.2), 0, 1)
            rows.append(dict(family=fam, id=f"it{i}", y=y, support8=round(rec * 8), recurrence=rec, sens_family=sens, sens_all=sens,
                             proxy_recurrence=rec, adjacent=rng.random(), sens_noise=rng.random()))
    return pd.DataFrame(rows)


def test_bootstrap_detects_planted_effect_and_null():
    d = _synthetic_table(effect=3.0)
    point = AN.evaluate(d)
    assert point["both"]["all"] > point["recurrence"]["all"]
    draws = AN.bootstrap(d, n_boot=60, seed=0)
    dd = draws["both"]["all"] - draws["recurrence"]["all"]
    lo, hi = AN.ci(dd)
    assert lo > 0 and lo <= point["both"]["all"] - point["recurrence"]["all"] <= hi
    d0 = _synthetic_table(effect=0.0, seed=1)
    draws0 = AN.bootstrap(d0, n_boot=60, seed=0)
    lo0, hi0 = AN.ci(draws0["both"]["all"] - draws0["recurrence"]["all"])
    assert lo0 <= 0.05 and abs(AN.evaluate(d0)["sensitivity"]["all"] - 0.5) < 0.1


def test_summarise_rows_and_ge7_subset():
    d = _synthetic_table(effect=1.0)
    rows = pd.DataFrame(AN.summarise(d, "internal", n_boot=20, seed=0))
    assert set(rows.subset) == {"all", "ge7"} and rows.model.str.startswith("delta:").sum() == 14
    r = rows[(rows.model == "recurrence") & (rows.subset == "ge7")].iloc[0]
    assert r.n_pos + r.n_neg == int((d.support8 >= 7).sum())
    assert (rows.lo <= rows.hi).all() and np.isfinite(rows[["auroc", "lo", "hi"]].to_numpy()).all()
    # percentile CIs of the 'all' subset bracket the point estimate on this well-populated table
    a = rows[rows.subset == "all"]
    assert (a.lo <= a.auroc + 0.02).all() and (a.hi >= a.auroc - 0.02).all()


def test_main_end_to_end_on_tiny_data(tmp_path):
    d = _tiny_data(tmp_path)
    out = tmp_path / "out"
    res = AN.main(["--n-boot", "3", "--seed", "0", "--data", str(d), "--out", str(out)])
    for f in ("v3.md", "v3.csv", "v3_claims.csv", "fig_v3.png", "for_michael_v3.md"):
        assert (out / f).exists(), f
    assert "Verdict" in (out / "v3.md").read_text() and len(res["summary"]) > 0
