"""V3 analysis (PREREG_WV.md, brief_wv.md §V3): does a sensitivity proxy add to recurrence for P(claim true)?

Pre-registered (before any AUROC was computed):
  claim types   input claims: TRUE (workspace, background_true) vs FALSE (misquote, contradicted) — his definition;
                internal claims: workspace claims labelled correct vs wrong (vague / excluded dropped); rows without an
                8-sample or adjacent-token support count are dropped (as in his notebook).
  models        M1 recurrence  = his sample_support_of_8 / 8 (raw score, higher → true);
                M2 sensitivity = sens_family (raw score, higher → true);
                M3 both        = logistic(recurrence, sens_family), leave-one-family-out (LOFO): fit on 4 families, score
                                 the 5th, AUROC on the pooled out-of-fold scores.
                secondary      proxy-recurrence alone and + sens_family (same matcher on both sides), both with sens_all,
                               recurrence + adjacent (his 0.80 check) and + sens_family, sens_noise alone.
  subsets       all claims of the type; the "≥ 7 of 8" subset of internal claims (443 correct, 39 wrong).
  uncertainty   item-level bootstrap (resample the 500 items with replacement, 1,000 draws, seed 0), LOFO refitted inside
                each draw; ΔAUROC(both − recurrence) paired within draws; 95 % percentile CIs.
  threshold     sensitivity adds ≥ 0.05 AUROC over recurrence alone on internal claims, CI excluding 0.
Outputs: results/g_agreement/v/{v3.md, v3.csv, v3_claims.csv, fig_v3.png, for_michael_v3.md}.
Run: PYTHONPATH=. .venv/bin/python -m projects.g_agreement.v3_sensitivity.analyze [--n-boot 1000] [--seed 0]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from projects.g_agreement.v3_sensitivity import claims as CL  # noqa: E402

DATA = REPO / "nla-consistency" / "data"
OUT = REPO / "results" / "g_agreement" / "v"
THRESH = 0.05
# name -> (features, kind). kind "raw" = the single feature is the score; "logit" = LOFO logistic on the features.
MODELS: Dict[str, Tuple[Tuple[str, ...], str]] = {
    "recurrence": (("recurrence",), "raw"),
    "sensitivity": (("sens_family",), "raw"),
    "both": (("recurrence", "sens_family"), "logit"),
    # secondary
    "proxy_recurrence": (("proxy_recurrence",), "raw"),
    "proxy_both": (("proxy_recurrence", "sens_family"), "logit"),
    "both_all_families": (("recurrence", "sens_all"), "logit"),
    "recurrence+adjacent": (("recurrence", "adjacent"), "logit"),
    "recurrence+adjacent+sensitivity": (("recurrence", "adjacent", "sens_family"), "logit"),
    "sens_noise": (("sens_noise",), "raw"),
    # POST-HOC (added 2026-10-11 after the primary run, see v3.md "Deviations"): parameter-free sum of the two scores (the analogue
    # of his "samples/8 + tokens/3" combination; no fitting, so no fold-pooling artefact) and the in-sample logistic fit (reference only).
    "both_sum(post-hoc)": (("recurrence", "sens_family"), "sum"),
    "both_insample(post-hoc)": (("recurrence", "sens_family"), "logit_insample"),
}
PRIMARY = ("recurrence", "sensitivity", "both")
PLOTTED = PRIMARY + ("both_sum(post-hoc)",)
COLORS = {"recurrence": "#2a78d6", "sensitivity": "#eb6834", "both": "#1baf7a", "both_sum(post-hoc)": "#1baf7a"}  # slots 1–3; hatch = post-hoc
HATCH = {"both_sum(post-hoc)": "///"}
LEGEND = {"recurrence": "recurrence (his 8-sample support)", "sensitivity": "sensitivity proxy", "both": "both: LOFO logistic (pre-registered)",
          "both_sum(post-hoc)": "both: unfitted sum (post-hoc)"}


def auroc(y: Sequence[float], s: Sequence[float]) -> float:
    y, s = np.asarray(y, float), np.asarray(s, float)
    if len(y) == 0 or y.min() == y.max():
        return float("nan")
    return float(roc_auc_score(y, s))


def lofo_scores(X: np.ndarray, y: np.ndarray, groups: np.ndarray, C: float = 1e4) -> np.ndarray:
    """Out-of-fold logistic scores, one fold per group value. A training fold with one class scores its test fold NaN."""
    out = np.full(len(y), np.nan)
    for g in np.unique(groups):
        te, tr = groups == g, groups != g
        if tr.sum() == 0 or len(np.unique(y[tr])) < 2:
            continue
        m = LogisticRegression(C=C, max_iter=2000).fit(X[tr], y[tr])
        out[te] = m.decision_function(X[te])
    return out


def model_scores(df: pd.DataFrame, ycol: str, feats: Tuple[str, ...], kind: str) -> np.ndarray:
    if kind == "raw":
        return df[feats[0]].to_numpy(float)
    if kind == "sum":
        return df[list(feats)].to_numpy(float).sum(axis=1)
    if kind == "logit_insample":
        X, y = df[list(feats)].to_numpy(float), df[ycol].to_numpy(float)
        if len(np.unique(y)) < 2:
            return np.full(len(y), np.nan)
        return LogisticRegression(C=1e4, max_iter=2000).fit(X, y).decision_function(X)
    return lofo_scores(df[list(feats)].to_numpy(float), df[ycol].to_numpy(float), df["family"].to_numpy())


def subset(df: pd.DataFrame, claim_type: str) -> pd.DataFrame:
    ycol = "y_input" if claim_type == "input" else "y_internal"
    d = df[df[ycol].notna() & df["recurrence"].notna() & df["adjacent"].notna() & df["sens_family"].notna()].copy()
    d["y"] = d[ycol].astype(float)
    return d.reset_index(drop=True)


def evaluate(d: pd.DataFrame, models: Dict[str, Tuple[Tuple[str, ...], str]] = MODELS) -> Dict[str, Dict[str, float]]:
    """AUROC per model on all rows and on the ≥ 7/8 subset (rows with support8 ≥ 7); scores computed on all rows."""
    res: Dict[str, Dict[str, float]] = {}
    hi = d["support8"].to_numpy(float) >= 7
    for name, (feats, kind) in models.items():
        s = model_scores(d, "y", feats, kind)
        ok = ~np.isnan(s)
        res[name] = {"all": auroc(d["y"][ok], s[ok]), "ge7": auroc(d["y"][ok & hi], s[ok & hi])}
    return res


def bootstrap(d: pd.DataFrame, n_boot: int, seed: int, models=MODELS) -> Dict[str, Dict[str, np.ndarray]]:
    """Item-level bootstrap of every model's AUROC (all / ge7); returns name -> {"all": draws, "ge7": draws}."""
    rng = np.random.default_rng(seed)
    item = (d["family"] + "|" + d["id"]).to_numpy()
    uniq = np.unique(item)
    idx_of = {u: np.flatnonzero(item == u) for u in uniq}
    draws = {name: {"all": np.full(n_boot, np.nan), "ge7": np.full(n_boot, np.nan)} for name in models}
    for b in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        rows = np.concatenate([idx_of[u] for u in pick])
        db = d.iloc[rows].reset_index(drop=True)
        if db["y"].nunique() < 2:
            continue
        r = evaluate(db, models)
        for name in models:
            draws[name]["all"][b] = r[name]["all"]
            draws[name]["ge7"][b] = r[name]["ge7"]
    return draws


def ci(x: np.ndarray) -> Tuple[float, float]:
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return float("nan"), float("nan")
    return float(np.quantile(x, 0.025)), float(np.quantile(x, 0.975))


def summarise(d: pd.DataFrame, claim_type: str, n_boot: int, seed: int) -> List[dict]:
    point = evaluate(d)
    draws = bootstrap(d, n_boot, seed)
    hi = d["support8"] >= 7
    n = {"all": (int(d["y"].sum()), int((1 - d["y"]).sum())), "ge7": (int(d["y"][hi].sum()), int((1 - d["y"][hi]).sum()))}
    rows = []
    for name in MODELS:
        for sub in ("all", "ge7"):
            lo, hi_ = ci(draws[name][sub])
            rows.append(dict(claim_type=claim_type, subset=sub, model=name, auroc=point[name][sub], lo=lo, hi=hi_,
                             n_pos=n[sub][0], n_neg=n[sub][1], n_boot=n_boot, seed=seed))
    for sub in ("all", "ge7"):
        for a, b in (("both", "recurrence"), ("sensitivity", "recurrence"), ("proxy_both", "proxy_recurrence"),
                     ("recurrence+adjacent+sensitivity", "recurrence+adjacent"), ("both_all_families", "recurrence"),
                     ("both_sum(post-hoc)", "recurrence"), ("both_insample(post-hoc)", "recurrence")):
            dd = draws[a][sub] - draws[b][sub]
            lo, hi_ = ci(dd)
            rows.append(dict(claim_type=claim_type, subset=sub, model=f"delta:{a}-{b}", auroc=point[a][sub] - point[b][sub],
                             lo=lo, hi=hi_, n_pos=n[sub][0], n_neg=n[sub][1], n_boot=n_boot, seed=seed))
    return rows


def figure(summary: pd.DataFrame, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#898781",
                         "axes.labelcolor": "#52514e", "xtick.color": "#52514e", "ytick.color": "#52514e", "font.size": 9})
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(8.4, 3.6), gridspec_kw={"width_ratios": [2.0, 1.0]})
    width, groups = 0.2, ["input", "internal"]
    for gi, ct in enumerate(groups):
        for mi, m in enumerate(PLOTTED):
            r = summary[(summary.claim_type == ct) & (summary.subset == "all") & (summary.model == m)].iloc[0]
            x = gi + (mi - 1.5) * (width + 0.015)
            ax.bar(x, r.auroc, width, color=COLORS[m], hatch=HATCH.get(m), edgecolor="#fcfcfb", lw=0.5, label=LEGEND[m] if gi == 0 else None, zorder=2)
            ax.errorbar(x, r.auroc, yerr=_yerr(r), fmt="none", ecolor="#0b0b0b", lw=1, capsize=2, zorder=3)
            ax.text(x, max(r.hi, r.auroc) + 0.012, f"{r.auroc:.2f}", ha="center", va="bottom", fontsize=7.5, color="#0b0b0b")
    ax.axhline(0.5, color="#c3c2b7", lw=1, ls="--", zorder=1)
    ax.set_xticks(range(len(groups)))
    ax.set_xticklabels([f"input claims\n(true vs false, n={int(summary[(summary.claim_type=='input')&(summary.subset=='all')].iloc[0].n_pos+summary[(summary.claim_type=='input')&(summary.subset=='all')].iloc[0].n_neg)})",
                        f"internal claims\n(correct vs wrong, n={int(summary[(summary.claim_type=='internal')&(summary.subset=='all')].iloc[0].n_pos+summary[(summary.claim_type=='internal')&(summary.subset=='all')].iloc[0].n_neg)})"])
    ax.set_ylim(0.2, 1.05)
    ax.set_ylabel("AUROC for P(claim true) (item-level bootstrap 95 % CI)")
    ax.set_title("V3: recurrence vs sensitivity proxy vs both", loc="left", fontsize=10)
    handles, labels = ax.get_legend_handles_labels()
    fig.legend(handles, labels, frameon=False, fontsize=7.5, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.005))
    ax.grid(axis="y", color="#f0efec", zorder=0)
    # inset: internal claims repeated in ≥ 7 of 8 samples
    for mi, m in enumerate(PLOTTED):
        r = summary[(summary.claim_type == "internal") & (summary.subset == "ge7") & (summary.model == m)].iloc[0]
        ax2.bar(mi, r.auroc, 0.6, color=COLORS[m], hatch=HATCH.get(m), edgecolor="#fcfcfb", lw=0.5, zorder=2)
        ax2.errorbar(mi, r.auroc, yerr=_yerr(r), fmt="none", ecolor="#0b0b0b", lw=1, capsize=2, zorder=3)
        ax2.text(mi, max(r.hi, r.auroc) + 0.012, f"{r.auroc:.2f}", ha="center", va="bottom", fontsize=7.5, color="#0b0b0b")
    r = summary[(summary.claim_type == "internal") & (summary.subset == "ge7") & (summary.model == "both")].iloc[0]
    ax2.axhline(0.5, color="#c3c2b7", lw=1, ls="--", zorder=1)
    ax2.set_xticks(range(len(PLOTTED))); ax2.set_xticklabels(["recurrence", "sensitivity", "both\n(LOFO)", "both\n(sum)"], fontsize=7.5)
    ax2.set_ylim(0.2, 1.05)
    ax2.set_title(f"internal, repeated ≥ 7/8\n({int(r.n_pos)} correct vs {int(r.n_neg)} wrong)", loc="left", fontsize=9)
    ax2.grid(axis="y", color="#f0efec", zorder=0)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    fig.savefig(path, dpi=200)
    plt.close(fig)


def _yerr(r: pd.Series):
    """Asymmetric error bar from a percentile CI; a CI that misses the point estimate (possible for a percentile bootstrap) is clipped at 0."""
    return [[max(r.auroc - r.lo, 0.0)], [max(r.hi - r.auroc, 0.0)]]


def fmt(r: pd.Series) -> str:
    return f"{r.auroc:.3f} [{r.lo:.3f}, {r.hi:.3f}]"


def write_md(summary: pd.DataFrame, df: pd.DataFrame, inv: dict, calib: dict, meta: dict, path: Path, michael: Path) -> str:
    g = lambda ct, sub, m: summary[(summary.claim_type == ct) & (summary.subset == sub) & (summary.model == m)].iloc[0]  # noqa: E731
    d_int = g("internal", "all", "delta:both-recurrence")
    d_inp = g("input", "all", "delta:both-recurrence")
    d_ge7 = g("internal", "ge7", "delta:both-recurrence")
    passed = (d_int.auroc >= THRESH) and (d_int.lo > 0)
    excluded = d_int.hi < THRESH
    verdict = ("PASS: the sensitivity proxy adds ≥ 0.05 AUROC on internal claims with CI excluding 0." if passed else
               ("FAIL (effect excluded): ΔAUROC(both − recurrence) on internal claims is below the pre-registered 0.05 and its "
                "95 % CI upper bound is below 0.05, so an effect of the pre-registered size is excluded for this proxy." if excluded else
                "FAIL (inconclusive): ΔAUROC on internal claims does not reach 0.05 with CI excluding 0, but the CI does not exclude 0.05."))
    ni = g("internal", "all", "recurrence"); nin = g("input", "all", "recurrence")
    lines = [
        "# V3 — sensitivity-based confabulation detector on Michael Kenney's released NLA data",
        "",
        f"Pre-registration: `projects/g_agreement/PREREG_WV.md` (Part V, V3) from `manifest/brief_wv.md` §V3. Run {meta['date']} on "
        f"the Mac (CPU, no model calls; {meta['wall_s']:.0f} s wall; seed {meta['seed']}; {meta['n_boot']} item-level bootstrap draws). "
        "Code `projects/g_agreement/v3_sensitivity/`, tests `projects/g_agreement/tests/test_v3.py`. Data and labels: "
        "M. Kenney, `nla-consistency` (repo root, read-only), notebook numbers reproduced exactly (see §1).",
        "",
        "## Verdict",
        "",
        f"**{verdict}** ΔAUROC(both − recurrence), internal claims: **{d_int.auroc:+.3f} [{d_int.lo:+.3f}, {d_int.hi:+.3f}]** "
        f"(threshold ≥ +0.05, CI excluding 0). Input claims: {d_inp.auroc:+.3f} [{d_inp.lo:+.3f}, {d_inp.hi:+.3f}]. "
        f"On the ≥ 7/8 internal subset ({int(d_ge7.n_pos)} correct vs {int(d_ge7.n_neg)} wrong): sensitivity alone "
        f"{fmt(g('internal', 'ge7', 'sensitivity'))}, both {fmt(g('internal', 'ge7', 'both'))}, recurrence {fmt(g('internal', 'ge7', 'recurrence'))}.",
        "",
        "## Limitation that frames everything (stated first on purpose)",
        "",
        "The brief's sensitivity score is 1 − P(claim recurs under matched-norm random/control-vector readouts **of the same state**). "
        f"Michael's release has **no per-state perturbed or control readouts**: `prior_consistency.jsonl` holds {inv['n_noise_vectors']} "
        f"GLOBAL Gaussian vectors at the mean activation norm (one shared set, not one per item), {inv['n_mean_vectors']} mean vector and "
        f"{inv['n_real_items']} real items, and for each only the Gemini-split claims of sample 1 with their support among samples 2–8 "
        f"({inv['n_noise_claims']} random-vector claim strings in total; the readout texts are not released). `nla_samples.jsonl` carries "
        f"only {inv['per_state_fields_in_nla_samples']} per item. The 29 % figure is the share of random-vector claims repeated in "
        f"≥ 6 of 7 other samples ({100*inv['noise_share_ge6_of_7']:.0f} % recomputed here; real items {100*inv['real_share_ge6_of_7']:.0f} %).",
        "",
        "**Proxy used instead** (fixed before any AUROC was computed): a claim's *prior recurrence* = the share of the 8 × 99 NLA "
        "readouts of the OTHER states of the same family that contain the claim; sensitivity = 1 − that share. A claim the NLA emits "
        "for other activations of the same family regardless of content is low-sensitivity. \"Contains\" is a lexical matcher: idf-weighted "
        f"recall of the claim's stemmed content terms in the readout ≥ τ = {CL.TAU:.2f}. τ and the matcher were chosen **label-free** by "
        "agreement with his judged `sample_support_of_8` on the claim's own 8 samples (§2); they were never tuned on true/false labels. "
        "Secondary proxies: the same over all 499 other states (`sens_all`), and 1 − max recall against the 146 released random-vector claim "
        "strings (`sens_noise`). Caveats: (a) other-state readouts are not matched-norm random vectors — they carry other content of the same "
        "family, so this measures family-level genericity, not activation-independence; (b) the lexical matcher is a weak stand-in for his "
        "Gemini support judge (§2); (c) the item-level matched \"control\" of the brief would need S4-style per-state random-vector samples, which "
        "our pod stage S4 collects for our own readers, not for his NLA.",
        "",
        "## 1. Reconstructed claim table (matches his notebook)",
        "",
        f"- {len(df)} claims on {df[['family','id']].drop_duplicates().shape[0]} items; labels: " +
        ", ".join(f"{k} {v}" for k, v in df['label'].value_counts().items()) + ".",
        f"- Input claims (his TRUE = workspace + background_true vs FALSE = misquote + contradicted): {int(nin.n_pos)} true vs {int(nin.n_neg)} false.",
        f"- Internal claims (workspace claims graded correct vs wrong; vague {int((df.internal_label=='vague').sum())} and excluded "
        f"{int((df.internal_label=='excluded').sum())} dropped): {int(ni.n_pos)} correct vs {int(ni.n_neg)} wrong; "
        f"wrong repeated in ≥ 7 of 8 samples: {int(d_ge7.n_neg)} (= {calib['ge7_wrong_adj0']} with adjacent support 0 + "
        f"{int(d_ge7.n_neg) - calib['ge7_wrong_adj0']} with ≥ 1: his \"27 + 12\"); correct at ≥ 7/8: {int(d_ge7.n_pos)}.",
        f"- His signals reproduced: recurrence AUROC input {g('input','all','recurrence').auroc:.2f} / internal {ni.auroc:.2f}; "
        f"recurrence + adjacent (his \"both\") internal {g('internal','all','recurrence+adjacent').auroc:.2f} (LOFO logistic; his in-sample 0.80).",
        f"- Per-claim table with every signal and proxy: `v3_claims.csv` (columns: key, family, id, label, internal_label, support8, "
        "adjacent3, own_proxy8, prior_rate_family, prior_rate_all, sens_family, sens_all, noise_max_recall).",
        "",
        "## 2. Matcher calibration (label-free)",
        "",
        f"- Own-sample proxy count (`own_proxy8`) vs his judged `sample_support_of_8`: Spearman ρ = {calib['rho_own']:.2f}; "
        f"P(proxy ≥ 4 | judged ≥ 4) = {calib['sens_cut']:.2f}, P(proxy < 4 | judged < 4) = {calib['spec_cut']:.2f}; "
        f"mean proxy {calib['mean_proxy']:.2f} vs judged {calib['mean_judged']:.2f} of 8. "
        "Alternatives tried on this label-free target only: sentence-level TF-IDF cosine (word 1–2-gram, char 3–5-gram; ρ ≤ 0.25), whole-sample "
        "TF-IDF cosine (ρ ≤ 0.20), unweighted stem recall (ρ 0.41 but over-matches at the 4/8 cut). τ = 0.50 sits on the ρ plateau "
        "(0.45–0.55) and balances the two conditional agreement rates.",
        f"- Prior recurrence (same family) by label: " + ", ".join(f"{k} {v:.2f}" for k, v in calib['prior_by_label'].items()) +
        f"; internal correct {calib['prior_internal']['correct']:.2f} vs wrong {calib['prior_internal']['wrong']:.2f}; "
        f"≥ 7/8 wrong {calib['prior_ge7']['wrong']:.2f} vs ≥ 7/8 correct {calib['prior_ge7']['correct']:.2f}.",
        "",
        "## 3. AUROC table (LOFO for logistic models; item-level bootstrap 95 % CI, 1,000 draws)",
        "",
        "| model | input claims (true vs false) | internal claims (correct vs wrong) | internal, repeated ≥ 7/8 |",
        "|---|---|---|---|",
    ]
    for m in MODELS:
        lines.append(f"| {m} | {fmt(g('input','all',m))} | {fmt(g('internal','all',m))} | {fmt(g('internal','ge7',m))} |")
    lines += ["", "| paired ΔAUROC | input | internal | internal ≥ 7/8 |", "|---|---|---|---|"]
    for m in [x for x in summary.model.unique() if x.startswith("delta:")]:
        lines.append(f"| {m[6:]} | {fmt(g('input','all',m))} | {fmt(g('internal','all',m))} | {fmt(g('internal','ge7',m))} |")
    lines += [
        "",
        "Per-family out-of-fold AUROCs are in `v3.csv` (rows `family=<f>`); typo and association have a single wrong internal claim each, so "
        "their per-family internal AUROCs are not interpretable and only the pooled out-of-fold AUROC is reported above.",
        "",
        "## 4. Reading",
        "",
        "- **Why the pre-registered combination loses to its own inputs.** The LOFO coefficients are stable across the five folds (recurrence "
        f"{calib['lofo_coef_range']['recurrence']}, sensitivity {calib['lofo_coef_range']['sens_family']}, same sign everywhere), but the fold intercepts "
        f"run from {calib['lofo_coef_range']['intercept']} because the wrong-claim base rate differs by family (poetry 54 of 89, typo 1 of 167). Pooling "
        "out-of-fold decision scores across folds therefore mixes incompatible offsets, and the pooled AUROC of any *fitted* model is pushed down relative to a "
        "raw score, which has no fold offsets. Within each family (same fitted fold) \"both\" beats recurrence in the three families with more than one wrong "
        "claim and ties in the two with one (table below). This is a flaw of the pre-registered design, not evidence against the combination; the verdict above "
        "is nevertheless reported as pre-registered.",
        "",
        "| family (internal claims, correct / wrong) | recurrence | sensitivity | both (LOFO fold) | both (sum, post-hoc) |",
        "|---|---|---|---|---|",
    ] + [
        f"| {fam} ({int(g('internal', f'family={fam}', 'recurrence').n_pos)} / {int(g('internal', f'family={fam}', 'recurrence').n_neg)}) | "
        f"{g('internal', f'family={fam}', 'recurrence').auroc:.2f} | {g('internal', f'family={fam}', 'sensitivity').auroc:.2f} | "
        f"{g('internal', f'family={fam}', 'both').auroc:.2f} | {g('internal', f'family={fam}', 'both_sum(post-hoc)').auroc:.2f} |"
        for fam in CL.FAMS
    ] + [
        "",
        f"- **Post-hoc (dated 2026-10-11, after the primary run):** the parameter-free sum recurrence + sensitivity — the analogue of Michael's own "
        f"\"samples/8 + tokens/3\" — scores {fmt(g('internal','all','both_sum(post-hoc)'))} on internal claims, Δ vs recurrence "
        f"{g('internal','all','delta:both_sum(post-hoc)-recurrence').auroc:+.3f} [{g('internal','all','delta:both_sum(post-hoc)-recurrence').lo:+.3f}, "
        f"{g('internal','all','delta:both_sum(post-hoc)-recurrence').hi:+.3f}], and {fmt(g('internal','ge7','both_sum(post-hoc)'))} on the ≥ 7/8 subset "
        f"(Δ {g('internal','ge7','delta:both_sum(post-hoc)-recurrence').auroc:+.3f} [{g('internal','ge7','delta:both_sum(post-hoc)-recurrence').lo:+.3f}, "
        f"{g('internal','ge7','delta:both_sum(post-hoc)-recurrence').hi:+.3f}]). It has no fitted parameters, so the caveat is not overfitting but that the choice of "
        "combination was made after seeing the LOFO failure (one post-hoc comparison). It would have met the pre-registered bar; it needs a fresh dataset "
        "(or the per-state control readouts of §5) to count. The in-sample logistic fit (reference only) gives the same numbers.",
        f"- **Sensitivity alone** already beats recurrence on internal claims ({fmt(g('internal','all','sensitivity'))} vs {fmt(ni)}; paired Δ "
        f"{g('internal','all','delta:sensitivity-recurrence').auroc:+.3f} [{g('internal','all','delta:sensitivity-recurrence').lo:+.3f}, "
        f"{g('internal','all','delta:sensitivity-recurrence').hi:+.3f}], CI includes 0). Mean sensitivity of wrong internal claims "
        f"{calib['sens_internal']['wrong']:.2f} vs correct {calib['sens_internal']['correct']:.2f}; the gap is carried by poetry "
        f"({calib['sens_internal_poetry']['wrong']:.2f} vs {calib['sens_internal_poetry']['correct']:.2f}: the repeated wrong claims there are generic "
        "\"the next token must begin the second line\" statements) and basic_readout; multihop and the one-wrong-claim families show none.",
        f"- **Input claims: the proxy runs backwards.** Sensitivity alone scores {g('input','all','sensitivity').auroc:.2f} (< 0.5): true background claims "
        "(\"the text is prose\", \"a trivia question\") are exactly the generic, family-wide statements the proxy calls insensitive, while misquotes are "
        "specific strings that recur nowhere else. The logistic fit learns the negative sign (input coefficient on sensitivity "
        f"{calib['input_sens_coef']:+.2f}) and lands on recurrence alone; the unfitted sum, which assumes a positive sign, loses 0.05. So genericity helps "
        "only for claims about internal computation, where a generic claim is a confabulation risk; for claims about the input it marks truisms.",
        "",
        f"- The ≥ 7/8 wrong internal claims are the case the brief targets. Sensitivity alone orders them against the ≥ 7/8 correct claims at AUROC "
        f"{g('internal','ge7','sensitivity').auroc:.2f} [{g('internal','ge7','sensitivity').lo:.2f}, {g('internal','ge7','sensitivity').hi:.2f}]; "
        f"the adjacent-token check Michael already reports gives 0.67 there.",
        f"- Using the same lexical matcher on both sides (proxy recurrence + sensitivity vs proxy recurrence) gives Δ "
        f"{g('internal','all','delta:proxy_both-proxy_recurrence').auroc:+.3f} [{g('internal','all','delta:proxy_both-proxy_recurrence').lo:+.3f}, "
        f"{g('internal','all','delta:proxy_both-proxy_recurrence').hi:+.3f}] on internal claims: this is the apples-to-apples version, "
        "but proxy recurrence is itself a degraded copy of his judged recurrence (§2), so the primary comparison keeps his judged recurrence.",
        f"- On top of his best signal (recurrence + adjacent), sensitivity adds {g('internal','all','delta:recurrence+adjacent+sensitivity-recurrence+adjacent').auroc:+.3f} "
        f"[{g('internal','all','delta:recurrence+adjacent+sensitivity-recurrence+adjacent').lo:+.3f}, {g('internal','all','delta:recurrence+adjacent+sensitivity-recurrence+adjacent').hi:+.3f}] on internal claims.",
        "",
        "## Deviations (dated)",
        "",
        "- 2026-10-11: the sensitivity score is a family-genericity proxy (above) because the release has no per-state control readouts; the brief anticipates this.",
        "- 2026-10-11, after the primary run: added `both_sum(post-hoc)` and `both_insample(post-hoc)` models, the within-family table and the pooled-OOF "
        "explanation, and `--rerender`. No decision rule or pre-registered model changed; the verdict is on the pre-registered LOFO comparison. Rows lacking an "
        "adjacent-token count (4 claims) are dropped from every model so that all models score the same rows (his notebook does the same).",
        "",
        "",
        "## 5. What would settle it",
        "",
        "Per-state control readouts: for each of the 500 items, 8 NLA samples on K random vectors of the item's norm (and ideally on the "
        "item's activation with its class-mean component removed), then his support judge on the same claims. Our pod stage S4 does this for "
        "our own readers (100 error states + 50 counts states, 50 random vectors); it does not cover his NLA or his claim set. Until then the "
        "sensitivity hypothesis (\"consistent wrong claims are prior-generated and activation-invariant\") is tested here only through "
        "family-level genericity.",
        "",
        "## Log",
        "",
        f"- {meta['date']}: `PYTHONPATH=. .venv/bin/python -m projects.g_agreement.v3_sensitivity.analyze --n-boot {meta['n_boot']} --seed {meta['seed']}` "
        f"({meta['wall_s']:.0f} s wall, CPU only, 0 GPU-hours, 0 API calls). Matcher calibration exploration (label-free, scratchpad only) preceded it; "
        "no decision rule changed after seeing AUROCs. Deviations from the brief: the sensitivity score is the proxy described above because per-state "
        "control readouts do not exist in the release (the brief anticipates this case).",
    ] + ([f"- {meta['rerendered']}: `--rerender` (md + figure rebuilt from the saved `v3.csv`; post-hoc rows were produced by the same 1,000-draw run, "
          "every model is evaluated on every bootstrap draw)."] if meta.get("rerendered") else [])
    path.write_text("\n".join(lines) + "\n")
    # paragraph for Michael
    mi = [
        "# Note for Michael Kenney — V3 sensitivity proxy on `nla-consistency`",
        "",
        f"Using your released `nla-consistency` data (claims/, claim_signals.jsonl, nla_samples.jsonl, prior_consistency.jsonl; numbers reproduce your "
        f"notebook: recurrence AUROC {g('input','all','recurrence').auroc:.2f} input / {ni.auroc:.2f} internal, {int(d_ge7.n_neg)} wrong internal claims at ≥ 7/8 = "
        f"{calib['ge7_wrong_adj0']} + {int(d_ge7.n_neg) - calib['ge7_wrong_adj0']}), I tested whether a *sensitivity* signal helps where consensus cannot: "
        "the idea being that a claim the NLA repeats in 8/8 but gets wrong is generated from its prior and would recur on other vectors too. Your release "
        f"has no per-state control readouts (the {inv['n_noise_vectors']} random vectors are one global set and only sample-1 claims with support counts are "
        "released), so the sensitivity score I could build is a proxy: 1 − the share of the 8 × 99 readouts of the *other* items of the same family that "
        f"contain the claim, with \"contain\" = idf-weighted recall of the claim's stemmed content words ≥ {CL.TAU:.2f} (τ chosen by agreement with your judged "
        f"sample support, Spearman ρ {calib['rho_own']:.2f}, never on labels). Result, leave-one-family-out logistic, item-level bootstrap (1,000): "
        f"on internal claims recurrence alone {fmt(ni)}, sensitivity alone {fmt(g('internal','all','sensitivity'))}, both {fmt(g('internal','all','both'))}, "
        f"ΔAUROC(both − recurrence) {d_int.auroc:+.3f} [{d_int.lo:+.3f}, {d_int.hi:+.3f}] against a pre-registered bar of +0.05 with CI excluding 0 → "
        f"{'passes' if passed else 'does not pass'}. On input claims Δ = {d_inp.auroc:+.3f} [{d_inp.lo:+.3f}, {d_inp.hi:+.3f}]. "
        f"Among the ≥ 7/8 internal claims the proxy alone separates wrong from correct at {g('internal','ge7','sensitivity').auroc:.2f} "
        f"[{g('internal','ge7','sensitivity').lo:.2f}, {g('internal','ge7','sensitivity').hi:.2f}] (your adjacent-token check: 0.67). "
        f"Two things worth knowing: (i) the pre-registered combination fails for a design reason — pooled leave-one-family-out scores inherit per-family "
        f"intercepts that differ because poetry has 54 wrong internal claims and typo 1 — and the unfitted sum recurrence/8 + sensitivity (your own recipe) "
        f"gives {fmt(g('internal','all','both_sum(post-hoc)'))} on internal claims, Δ {g('internal','all','delta:both_sum(post-hoc)-recurrence').auroc:+.3f} "
        f"[{g('internal','all','delta:both_sum(post-hoc)-recurrence').lo:+.3f}, {g('internal','all','delta:both_sum(post-hoc)-recurrence').hi:+.3f}], which I report "
        "as post-hoc only; (ii) on input claims the proxy runs backwards (AUROC "
        f"{g('input','all','sensitivity').auroc:.2f}): true background claims are generic, misquotes are specific, so genericity is a confabulation signal only "
        "for claims about internal computation. "
        "The honest test needs 8 samples per item on K matched-norm random vectors (or the item's vector with its class-mean component removed) "
        "scored by your support judge; if you still have the pod set-up, that is about 500 × K × 8 NLA decodes plus one judge pass. "
        f"Code and per-claim table: `projects/g_agreement/v3_sensitivity/`, `results/g_agreement/v/v3_claims.csv` in our repo.",
    ]
    michael.write_text("\n".join(mi) + "\n")
    return verdict


def calibration(df: pd.DataFrame) -> dict:
    from scipy.stats import spearmanr
    ok = df["support8"].notna()
    j, p = df.loc[ok, "support8"].to_numpy(float), df.loc[ok, "own_proxy8"].to_numpy(float)
    rho = spearmanr(p, j).correlation
    internal = df[df.y_internal.notna()]
    hi = internal[internal.support8 >= 7]
    d_int, d_inp = subset(df, "internal"), subset(df, "input")
    rng_ = lambda v: f"{min(v):+.2f} to {max(v):+.2f}"  # noqa: E731
    coefs = {"recurrence": [], "sens_family": [], "intercept": []}
    for fam in CL.FAMS:
        tr = (d_int.family != fam).to_numpy()
        if tr.sum() == 0 or d_int.loc[tr, "y"].nunique() < 2:
            continue
        m = LogisticRegression(C=1e4, max_iter=2000).fit(d_int.loc[tr, ["recurrence", "sens_family"]], d_int.loc[tr, "y"])
        coefs["recurrence"].append(m.coef_[0][0]); coefs["sens_family"].append(m.coef_[0][1]); coefs["intercept"].append(m.intercept_[0])
    input_sens_coef = float("nan")
    if len(d_inp) and d_inp["y"].nunique() == 2:
        input_sens_coef = float(LogisticRegression(C=1e4, max_iter=2000).fit(d_inp[["recurrence", "sens_family"]], d_inp["y"]).coef_[0][1])
    poetry = d_int[d_int.family == "poetry"]
    return dict(
        lofo_coef_range={k: (rng_(v) if v else "n/a") for k, v in coefs.items()},
        input_sens_coef=input_sens_coef,
        sens_internal={"wrong": float("nan"), "correct": float("nan")} | {("wrong" if k == 0 else "correct"): float(v) for k, v in d_int.groupby("y")["sens_family"].mean().items()},
        sens_internal_poetry={"wrong": float("nan"), "correct": float("nan")} | {("wrong" if k == 0 else "correct"): float(v) for k, v in poetry.groupby("y")["sens_family"].mean().items()},
        rho_own=float(rho), sens_cut=float(np.mean(p[j >= 4] >= 4)), spec_cut=float(np.mean(p[j < 4] < 4)),
        mean_proxy=float(p.mean()), mean_judged=float(j.mean()),
        prior_by_label={k: float(v) for k, v in df.groupby("label")["prior_rate_family"].mean().items()},
        prior_internal={k: float(v) for k, v in internal.groupby("internal_label")["prior_rate_family"].mean().items()},
        prior_ge7={k: float(v) for k, v in hi.groupby("internal_label")["prior_rate_family"].mean().items()},
        ge7_wrong_adj0=int(((internal.internal_label == "wrong") & (internal.support8 >= 7) & (internal.adjacent3 == 0)).sum()),
    )


def per_family_rows(d: pd.DataFrame, claim_type: str) -> List[dict]:
    rows = []
    for name, (feats, kind) in MODELS.items():
        s = model_scores(d, "y", feats, kind)
        for fam in CL.FAMS:
            m = (d["family"] == fam).to_numpy() & ~np.isnan(s)
            rows.append(dict(claim_type=claim_type, subset=f"family={fam}", model=name, auroc=auroc(d["y"][m], s[m]), lo=np.nan, hi=np.nan,
                             n_pos=int(d["y"][m].sum()), n_neg=int((1 - d["y"][m]).sum()), n_boot=0, seed=0))
    return rows


def main(argv: Optional[List[str]] = None) -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--data", type=Path, default=DATA)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--rerender", action="store_true", help="rebuild md/figure from the saved v3.csv and v3_inventory.json without re-bootstrapping")
    a = ap.parse_args(argv)
    t0 = time.time()
    a.out.mkdir(parents=True, exist_ok=True)
    df, inv = CL.build(a.data)
    calib = calibration(df)
    if a.rerender:
        summary = pd.read_csv(a.out / "v3.csv")
        meta = json.loads((a.out / "v3_inventory.json").read_text())["meta"]
        meta["rerendered"] = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
        figure(summary, a.out / "fig_v3.png")
        verdict = write_md(summary, df, inv, calib, meta, a.out / "v3.md", a.out / "for_michael_v3.md")
        (a.out / "v3_inventory.json").write_text(json.dumps(dict(inventory=inv, calibration=calib, meta=meta), indent=1, default=str))
        print(verdict)
        return dict(summary=summary, verdict=verdict, inventory=inv, calibration=calib)
    rows = []
    for ct in ("input", "internal"):
        d = subset(df, ct)
        rows += summarise(d, ct, a.n_boot, a.seed)
        rows += per_family_rows(d, ct)
    summary = pd.DataFrame(rows)
    summary.to_csv(a.out / "v3.csv", index=False)
    keep = ["key", "family", "id", "claim_idx", "label", "internal_label", "support8", "adjacent3", "own_proxy8", "prior_rate_family",
            "prior_rate_all", "sens_family", "sens_all", "noise_max_recall", "claim"]
    df[keep].to_csv(a.out / "v3_claims.csv", index=False)
    figure(summary, a.out / "fig_v3.png")
    meta = dict(date=time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), wall_s=time.time() - t0, seed=a.seed, n_boot=a.n_boot)
    verdict = write_md(summary, df, inv, calib, meta, a.out / "v3.md", a.out / "for_michael_v3.md")
    (a.out / "v3_inventory.json").write_text(json.dumps(dict(inventory=inv, calibration=calib, meta=meta), indent=1, default=str))
    print(verdict)
    print(summary[(summary.subset.isin(["all", "ge7"])) & (summary.model.isin(list(PRIMARY) + ["delta:both-recurrence"]))].to_string(index=False))
    return dict(summary=summary, verdict=verdict, inventory=inv, calibration=calib)


if __name__ == "__main__":
    main()
