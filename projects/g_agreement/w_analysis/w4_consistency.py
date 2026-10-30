"""W4 — consistency filter on the S4 samples (PREREG_WV.md "Analysis", brief_wv.md "W4"; Michael Kenney's `nla-consistency` recipe).

    python -m projects.g_agreement.w_analysis.w4_consistency [--claims results/g_agreement/w/w3/claims_s4.jsonl]
        [--s4 cache/g_agreement/w/s4_samples.jsonl] [--s3 cache/g_agreement/w/s3_lo.jsonl] [--x3-lo cache/g_agreement/x/x3_lo.jsonl]
        [--out results/g_agreement/w/w4] [--n-boot 1000 --seed 0] [--match primary|strict|lenient] [--no-figure]
      -> <out>/{w4.md, w4.csv, w4_summary.json, fig_w4.png, claims_agreement.jsonl}

Question. Michael keeps the NLA claims that recur in >= 2 of 8 samples of the same activation (support judged by Gemini): false
input claims fall from 38% to 13%, AUROC(support, true vs false) 0.90 on input claims but only 0.75 on internal-computation claims, and
29% of claims on random vectors are still self-consistent (>= 6 of the 7 other samples). Pre-registered expectation: NO gain on
internal-computation claims here either. Every number below is a difference (kept vs all, reader vs reader, natural vs random).

Agreement count. For every judged claim (any type) of a natural S4 state: the number of the state's 8 samples (same reader) in which
some claim MATCHES it, its own sample included (1..8). "Kept" = agreement >= 2, i.e. the claim recurs in at least one other sample
("in >= 2 of 8 samples"). Matching is deterministic (no further API calls), on the claim texts the Track C judge split out:
  normalise: NFKC, lower-case, NLA tags and quotes removed, English number words -> digits, light synonym folding
  (output/reply/response/say/write/produce/predict -> answer; input/text/query/question/context -> prompt; model/network/llm -> model;
  plural -s dropped on content words), stop-words dropped;
  anchors = the integers, the standalone capital letters A-H (puzzle symbols) and the state's candidate values the claim names;
  content tokens = the remaining words.
  primary rule (pre-specified): two claims match iff their anchor sets are IDENTICAL and their judge claim types are equal and
    (anchored: they share >= 1 content token, or both have none; unanchored: Jaccard(content tokens) >= 0.5); identical normalised
    strings always match. Different numbers or symbols therefore never match ("the answer is 27" vs "... 26"), nor does an input
    claim about a symbol match a computation claim about the same symbol.
  strict (sensitivity): anchors identical, same type, Jaccard >= 0.75.  lenient (sensitivity): anchors identical, any type,
    anchored -> match, unanchored -> Jaccard >= 1/3.
  The rule is conservative relative to a judge: paraphrases with no shared content word do not count, so recurrence is under- rather
  than over-counted; the strict/lenient variants bound the effect of the choice.

(a) Kept vs all. Errors: favours-actual = share of states with >= 1 computation claim naming the model's ACTUAL answer (the judge's
    computation_true) among kept claims vs among all claims; also the precision vs actual and vs correct among kept vs all. Counts:
    exact-match = share of states with >= 1 computation claim whose stated number == the value (judge computation_true), kept vs all;
    plus precision among kept vs all. Differences with state-paired bootstrap CIs. Input claims: false share kept vs all (Michael's 38 -> 13).
(b) AUROC of the agreement count vs claim correctness (Michael's tie-aware formula), per reader x claim type x family, state bootstrap.
(c) Random-vector self-consistency: share of claims from the random-vector samples (1 per reader per vector) that match a claim which
    recurs (agreement >= 2) in some natural state of the same reader; next to it the same statistic for natural claims against OTHER
    states (cross-state genericity, the matched control), the share of natural claims that recur in their own state (our analogue of
    Michael's 84% real / 29% random at >= 6 of 7) and, when a random vector has >= 2 samples, the within-random recurrence.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from projects.g_agreement.w_claims.stats import precision_item_bootstrap, wilson

from . import w3_claims as W3

OUT_W4 = W3.RESULTS_W / "w4"
N_BOOT, SEED = 1000, 0
KEEP_MIN = 2
MICHAEL = {"auroc_input": 0.90, "auroc_internal": 0.75, "random_self_consistency": 0.29, "real_self_consistency": 0.84,
           "input_false_all": 0.38, "input_false_kept": 0.13}
COLORS = {"Oracle": "#2a78d6", "NLA": "#eb6834"}

STOP = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "of", "to", "that", "this", "these", "those", "it", "its", "and",
        "or", "in", "on", "at", "as", "with", "for", "by", "from", "there", "here", "which", "who", "whom", "what", "will", "would", "should",
        "can", "could", "has", "have", "had", "do", "does", "did", "not", "no", "about", "into", "than", "then", "so", "very", "likely",
        "probably", "appears", "appear", "seems", "seem", "some", "any", "one", "s", "t", "i", "you", "we", "they", "he", "she", "his", "her",
        "their", "our", "your", "being", "also", "just", "only", "up", "out", "if", "but", "such", "most", "more", "less", "much", "many"}
SYN = {"output": "answer", "outputs": "answer", "reply": "answer", "replies": "answer", "response": "answer", "respond": "answer", "responds": "answer",
       "say": "answer", "says": "answer", "said": "answer", "write": "answer", "writes": "answer", "produce": "answer", "produces": "answer",
       "predict": "answer", "predicts": "answer", "prediction": "answer", "answering": "answer", "answers": "answer", "answered": "answer",
       "input": "prompt", "text": "prompt", "query": "prompt", "question": "prompt", "context": "prompt", "passage": "prompt", "prompts": "prompt",
       "network": "model", "llm": "model", "assistant": "model", "system": "model", "models": "model", "symbols": "symbol", "letters": "letter",
       "numbers": "number", "digits": "digit", "arrows": "arrow", "steps": "step", "times": "time", "objects": "object", "items": "item"}
_QUOTES = "\"'`‘’“”«»"


# ----------------------------------------------------------------------------------------------- matcher
def normalise(text: str, candidates: Optional[Sequence[Any]] = None) -> Tuple[str, FrozenSet[str], FrozenSet[str]]:
    """-> (normalised string, anchors, content tokens). See the module docstring."""
    t = unicodedata.normalize("NFKC", text or "")
    t = re.sub(r"</?(explanation|br)/?>", " ", t)
    anchors = set()
    for letter in "ABCDEFGH":                                                  # standalone / quoted capital symbols, before lower-casing
        if W3.symbol_mentioned(t, letter):
            anchors.add(letter)
    for c in (candidates or []):
        if W3.mentions(t, c):
            anchors.add(str(c))
    t = W3.words_to_digits(t.lower())
    for m in re.finditer(r"(?<![\d.:])\d{1,3}(?![\d.:])", t):
        anchors.add(str(int(m.group(0))))
    t = re.sub(r"[" + _QUOTES + r"]", " ", t)
    words = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", t)
    toks = []
    for w in words:
        if w.isdigit() or w in STOP:
            continue
        w = SYN.get(w, w)
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        toks.append(w)
    return " ".join(words), frozenset(anchors), frozenset(toks)


def jaccard(a: FrozenSet[str], b: FrozenSet[str]) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def claims_match(a: dict, b: dict, mode: str = "primary") -> bool:
    """``a``/``b`` carry 'norm' (string), 'anchors', 'tokens', 'claim_type' (see annotate_claims)."""
    if mode != "lenient" and a["claim_type"] != b["claim_type"]:
        return False
    if a["norm"] == b["norm"]:
        return True
    if a["anchors"] != b["anchors"]:
        return False
    j = jaccard(a["tokens"], b["tokens"])
    if mode == "strict":
        return j >= 0.75
    if mode == "lenient":
        return bool(a["anchors"]) or j >= 1 / 3
    if a["anchors"]:
        return bool(a["tokens"] & b["tokens"]) or (not a["tokens"] and not b["tokens"])
    return j >= 0.5


def annotate_claims(claims: List[dict]) -> List[dict]:
    out = []
    for c in claims:
        if not c.get("claim_text"):
            continue
        d = dict(c)
        d["norm"], d["anchors"], d["tokens"] = normalise(c["claim_text"], c.get("candidates"))
        out.append(d)
    return out


def agreement_counts(claims: List[dict], mode: str = "primary", n_samples: Optional[Dict[Tuple[str, str], int]] = None) -> List[dict]:
    """Adds 'agreement' (1..n samples in which the claim recurs, own sample included), 'n_samples' and 'kept' to every natural claim."""
    groups: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for c in claims:
        if c.get("condition") == "natural":
            groups[(c["reader"], c["item_id"])].append(c)
    for key, cl in groups.items():
        by_sample: Dict[int, List[dict]] = defaultdict(list)
        for c in cl:
            by_sample[int(c.get("sample_idx", 0))].append(c)
        ns = (n_samples or {}).get(key) or max(W3.N_SAMPLES, len(by_sample))
        for c in cl:
            own = int(c.get("sample_idx", 0))
            k = 1 + sum(1 for s, others in by_sample.items() if s != own and any(claims_match(c, o, mode) for o in others))
            c["agreement"], c["n_samples"], c["kept"] = k, ns, k >= KEEP_MIN
    return claims


# ----------------------------------------------------------------------------------------------- statistics
def auroc(pos: Sequence[float], neg: Sequence[float]) -> float:
    """Michael's tie-aware AUROC (nla-consistency/scripts/nla_verify_eval.py): P(pos > neg) + 0.5 P(pos == neg)."""
    if not len(pos) or not len(neg):
        return float("nan")
    p, n = np.asarray(pos, float)[:, None], np.asarray(neg, float)[None, :]
    return float(((p > n).sum() + 0.5 * (p == n).sum()) / (p.size * n.size))


def auroc_item_bootstrap(items: Sequence[str], scores: Sequence[float], truth: Sequence[Optional[bool]], n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    rows = [(i, s, t) for i, s, t in zip(items, scores, truth) if t is not None and s is not None]
    pos = [s for _, s, t in rows if t]
    neg = [s for _, s, t in rows if not t]
    out = {"n_items": len({i for i, _, _ in rows}), "n_pos": len(pos), "n_neg": len(neg), "auroc": auroc(pos, neg) if pos and neg else None, "lo": None, "hi": None}
    if not pos or not neg:
        return out
    by_item: Dict[str, List[Tuple[float, bool]]] = defaultdict(list)
    for i, s, t in rows:
        by_item[i].append((s, bool(t)))
    ids = sorted(by_item)
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(ids), len(ids))
        p = [s for j in pick for s, t in by_item[ids[j]] if t]
        n = [s for j in pick for s, t in by_item[ids[j]] if not t]
        if p and n:
            boots.append(auroc(p, n))
    if boots:
        out["lo"], out["hi"] = float(np.quantile(boots, 0.025)), float(np.quantile(boots, 0.975))
    return out


def paired_rate_diff(flags_a: Sequence[bool], flags_b: Sequence[bool], n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Rates of two state-paired boolean vectors (a = kept, b = all) and the bootstrap CI of a - b over states."""
    a, b = np.asarray(flags_a, float), np.asarray(flags_b, float)
    n = len(a)
    if n == 0:
        return {"n": 0, "rate_a": None, "rate_b": None, "diff": None, "lo": None, "hi": None}
    out = {"n": n, "rate_a": float(a.mean()), "rate_b": float(b.mean()), "diff": float(a.mean() - b.mean()), "lo": None, "hi": None}
    if n_boot > 0:
        rng = np.random.default_rng(seed)
        idx = rng.integers(0, n, (n_boot, n))
        d = (a[idx].mean(1) - b[idx].mean(1))
        out["lo"], out["hi"] = float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))
    return out


def _rate(k: int, n: int) -> dict:
    p, lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": (None if n == 0 else p), "lo": (None if n == 0 else lo), "hi": (None if n == 0 else hi)}


def correctness(c: dict) -> Optional[bool]:
    """The correctness used for AUROC / kept-vs-all: input claims -> judge truth; computation claims -> vs the model's actual answer
    (errors) or the value (counts), i.e. the judge's label; unverifiable -> None."""
    if c.get("claim_type") == "input":
        return c.get("truth")
    if c.get("claim_type") == "computation":
        return c.get("truth")
    return None


# ----------------------------------------------------------------------------------------------- summary
def summarise(claims: List[dict], *, n_boot: int = N_BOOT, seed: int = SEED, mode: str = "primary", n_samples: Optional[Dict[Tuple[str, str], int]] = None,
              lo: Optional[Dict[Tuple[str, str], dict]] = None) -> dict:
    ann = annotate_claims(claims)
    agreement_counts(ann, mode, n_samples)
    nat = [c for c in ann if c.get("condition") == "natural"]
    rnd = [c for c in ann if c.get("condition") == "random"]
    S: Dict[str, Any] = {"n_boot": n_boot, "seed": seed, "match_mode": mode, "keep_min": KEEP_MIN, "n_claims_natural": len(nat), "n_claims_random": len(rnd),
                         "readers": {}, "random": {}, "michael": MICHAEL}
    states_of = W3.state_table(claims)
    for rd in W3.READERS:
        R: Dict[str, Any] = {}
        for fam in W3.FAMILIES:
            cs = [c for c in nat if c["reader"] == rd and c.get("family") == fam]
            sts = sorted({sid for (r_, sid), v in states_of.items() if r_ == rd and v["family"] == fam})
            d: Dict[str, Any] = {"n_states": len(sts), "n_claims": len(cs), "agreement_hist": dict(sorted(Counter(c["agreement"] for c in cs).items())),
                                 "kept_share": _rate(sum(c["kept"] for c in cs), len(cs)), "auroc": {}, "kept_vs_all": {}}
            for t in ("input", "computation"):
                sub = [c for c in cs if c.get("claim_type") == t]
                d["auroc"][t] = auroc_item_bootstrap([c["item_id"] for c in sub], [c["agreement"] for c in sub], [correctness(c) for c in sub], n_boot, seed)
                d["kept_share_" + t] = _rate(sum(c["kept"] for c in sub), len(sub))
                d["high_consistency_false_" + t] = _rate(sum(1 for c in sub if c.get("truth") is False and c["agreement"] >= 7), sum(1 for c in sub if c.get("truth") is False))
            # (a) kept vs all, per state
            comp = [c for c in cs if c.get("claim_type") == "computation"]
            inp = [c for c in cs if c.get("claim_type") == "input"]
            by_state: Dict[str, List[dict]] = defaultdict(list)
            for c in comp:
                by_state[c["item_id"]].append(c)
            all_flag = [any(c.get("judge_label") == "computation_true" for c in by_state.get(s, [])) for s in sts]
            kept_flag = [any(c.get("judge_label") == "computation_true" and c["kept"] for c in by_state.get(s, [])) for s in sts]
            kv: Dict[str, Any] = {"states_naming_actual_or_value": paired_rate_diff(kept_flag, all_flag, n_boot, seed)}
            if fam == "errors":
                corr_all = [any(W3.computation_truths(c)["vs_correct_judge"] for c in by_state.get(s, [])) for s in sts]
                corr_kept = [any(W3.computation_truths(c)["vs_correct_judge"] and c["kept"] for c in by_state.get(s, [])) for s in sts]
                kv["states_naming_correct"] = paired_rate_diff(corr_kept, corr_all, n_boot, seed)
            has_kept = [s for s in sts if any(c["kept"] for c in by_state.get(s, []))]
            kv["states_with_kept_computation_claim"] = _rate(len(has_kept), len(sts))
            keys = ("vs_actual_judge", "vs_correct_judge") if fam == "errors" else ("vs_value_judge",)
            for k in keys:
                kv[f"precision_{k}"] = {"all": W3.precision_block(comp, k, n_boot, seed), "kept": W3.precision_block([c for c in comp if c["kept"]], k, n_boot, seed),
                                        "dropped": W3.precision_block([c for c in comp if not c["kept"]], k, n_boot, seed)}
            kv["input_false_share"] = {"all": _rate(sum(c.get("truth") is False for c in inp), sum(c.get("truth") is not None for c in inp)),
                                       "kept": _rate(sum(c.get("truth") is False for c in inp if c["kept"]), sum(c.get("truth") is not None for c in inp if c["kept"]))}
            kv["input_true_kept_share"] = _rate(sum(c["kept"] for c in inp if c.get("truth") is True), sum(1 for c in inp if c.get("truth") is True))
            # kept-vs-all inside the native-LO cells (does the filter help where the native reading already agrees?)
            if lo:
                cells = {}
                for ok in (True, False):
                    sel = [i for i, s in enumerate(sts) if (rd, s) in lo and lo[(rd, s)]["ok"] is ok]
                    cells[("lo_favours_actual" if ok else "lo_favours_correct") if fam == "errors" else ("lo_exact" if ok else "lo_not_exact")] = \
                        paired_rate_diff([kept_flag[i] for i in sel], [all_flag[i] for i in sel], n_boot, seed)
                kv["by_native_lo"] = cells
            d["kept_vs_all"] = kv
            R[fam] = d
        S["readers"][rd] = R
    # (c) random-vector self-consistency
    for rd in W3.READERS:
        nat_r = [c for c in nat if c["reader"] == rd]
        recurring = [c for c in nat_r if c["kept"]]
        rnd_r = [c for c in rnd if c["reader"] == rd]
        hit_rec = [any(claims_match(c, o, mode) for o in recurring) for c in rnd_r]
        hit_any = [any(claims_match(c, o, mode) for o in nat_r) for c in rnd_r]
        # matched control: natural recurring claims vs recurring claims of OTHER states (same reader)
        rng = np.random.default_rng(seed)
        ctrl_pool = recurring if len(recurring) <= 400 else [recurring[i] for i in sorted(rng.choice(len(recurring), 400, replace=False))]
        ctrl = [any(o["item_id"] != c["item_id"] and claims_match(c, o, mode) for o in recurring) for c in ctrl_pool]
        by_vec: Dict[str, List[dict]] = defaultdict(list)
        for c in rnd_r:
            by_vec[c["item_id"]].append(c)
        n_samp_rand = Counter(len({int(c.get("sample_idx", 0)) for c in v}) for v in by_vec.values())
        within = None
        if any(k >= 2 for k in n_samp_rand):
            rr = [dict(c, condition="natural") for c in rnd_r]
            agreement_counts(rr, mode, {(rd, k): len({int(c.get("sample_idx", 0)) for c in v}) for k, v in by_vec.items()})
            multi = [c for c in rr if c["n_samples"] >= 2]
            within = {"n_claims": len(multi), "recur_ge2": _rate(sum(c["agreement"] >= 2 for c in multi), len(multi)),
                      "recur_ge_7_of_8": _rate(sum(c["agreement"] >= 7 for c in multi), len(multi))}
        S["random"][rd] = {"n_random_vectors": len(by_vec), "n_random_claims": len(rnd_r), "samples_per_vector": dict(n_samp_rand),
                           "claims_per_sample": len(rnd_r) / max(1, sum(n_samp_rand.values())),
                           "random_matches_recurring_natural_claim": _rate(sum(hit_rec), len(hit_rec)),
                           "random_matches_any_natural_claim": _rate(sum(hit_any), len(hit_any)),
                           "control_natural_recurring_matches_other_state": _rate(sum(ctrl), len(ctrl)),
                           "natural_recur_ge2": _rate(sum(c["kept"] for c in nat_r), len(nat_r)),
                           "natural_recur_ge_7_of_8": _rate(sum(c["agreement"] >= 7 for c in nat_r), len(nat_r)),
                           "within_random_recurrence": within,
                           "random_label_mix": dict(Counter(c.get("claim_type") for c in rnd_r))}
    S["annotated"] = ann
    return S


# ----------------------------------------------------------------------------------------------- outputs
def fmt_a(a: Optional[dict]) -> str:
    if not a or a.get("auroc") is None:
        return "n/a"
    ci = f" [{a['lo']:.2f}, {a['hi']:.2f}]" if a.get("lo") is not None else ""
    return f"{a['auroc']:.2f}{ci} ({a['n_pos']}+{a['n_neg']})"


def fmt_d(d: Optional[dict]) -> str:
    if not d or d.get("diff") is None:
        return "n/a"
    return f"{100 * d['rate_a']:.0f}% vs {100 * d['rate_b']:.0f}% (Δ {100 * d['diff']:+.0f} [{100 * d['lo']:+.0f}, {100 * d['hi']:+.0f}], n={d['n']})"


def csv_rows(S: dict) -> List[dict]:
    rows = []
    for rd, R in S["readers"].items():
        for fam, d in R.items():
            for t, a in d["auroc"].items():
                rows.append({"metric": "auroc_agreement_vs_correct", "reader": rd, "family": fam, "claim_type": t, "n_items": a["n_items"], "n_pos": a["n_pos"], "n_neg": a["n_neg"],
                             "value": a["auroc"], "lo": a["lo"], "hi": a["hi"], "kept": None, "all": None})
            kv = d["kept_vs_all"]
            for name in ("states_naming_actual_or_value", "states_naming_correct"):
                if name in kv:
                    x = kv[name]
                    rows.append({"metric": f"kept_vs_all_{name}", "reader": rd, "family": fam, "claim_type": "computation", "n_items": x["n"], "n_pos": None, "n_neg": None,
                                 "value": x["diff"], "lo": x["lo"], "hi": x["hi"], "kept": x["rate_a"], "all": x["rate_b"]})
            for k, v in kv.items():
                if k.startswith("precision_"):
                    rows.append({"metric": f"kept_vs_all_{k}", "reader": rd, "family": fam, "claim_type": "computation", "n_items": v["all"]["n_items"], "n_pos": v["kept"]["n_claims"],
                                 "n_neg": v["all"]["n_claims"], "value": (None if v["kept"]["precision"] is None or v["all"]["precision"] is None else v["kept"]["precision"] - v["all"]["precision"]),
                                 "lo": None, "hi": None, "kept": v["kept"]["precision"], "all": v["all"]["precision"]})
            x = kv["input_false_share"]
            rows.append({"metric": "kept_vs_all_input_false_share", "reader": rd, "family": fam, "claim_type": "input", "n_items": d["n_states"], "n_pos": x["kept"]["n"], "n_neg": x["all"]["n"],
                         "value": (None if x["kept"]["rate"] is None or x["all"]["rate"] is None else x["kept"]["rate"] - x["all"]["rate"]), "lo": None, "hi": None,
                         "kept": x["kept"]["rate"], "all": x["all"]["rate"]})
    for rd, r in S["random"].items():
        for k in ("random_matches_recurring_natural_claim", "random_matches_any_natural_claim", "control_natural_recurring_matches_other_state", "natural_recur_ge2", "natural_recur_ge_7_of_8"):
            x = r[k]
            rows.append({"metric": k, "reader": rd, "family": "random" if k.startswith("random") else "natural", "claim_type": "all", "n_items": r["n_random_vectors"], "n_pos": x["k"], "n_neg": x["n"],
                         "value": x["rate"], "lo": x["lo"], "hi": x["hi"], "kept": None, "all": None})
    return rows


def render_md(S: dict, inputs: dict, sens: Optional[dict] = None, notes: Sequence[str] = ()) -> str:
    L = ["# W4 — does sample consistency (>= 2 of 8) help, and on which claims?", "",
         f"Agreement count = number of a state's 8 same-reader samples in which the claim recurs (own sample included); kept = agreement >= {KEEP_MIN}. "
         f"Matcher `{S['match_mode']}` (deterministic, anchors identical + same claim type + shared content; see the module docstring). Correctness: input claims = "
         "judge truth; computation claims = the judge's label against the model's ACTUAL answer (errors) / the value (counts). CIs: state bootstrap "
         f"({S['n_boot']} resamples, seed {S['seed']}). Michael's numbers (nla-consistency README): AUROC 0.90 input / 0.75 internal; random-vector self-consistency 29%.", "",
         "Inputs: " + ", ".join(f"{k}={v}" for k, v in inputs.items() if v), "",
         "## (b) AUROC of agreement count vs correctness", "",
         "| reader | family | states | claims | kept share | AUROC input [CI] | AUROC computation [CI] | false computation claims at >= 7/8 | agreement histogram |",
         "|---|---|---|---|---|---|---|---|---|"]
    for rd, R in S["readers"].items():
        for fam, d in R.items():
            hc = d["high_consistency_false_computation"]
            L.append(f"| {rd} | {fam} | {d['n_states']} | {d['n_claims']} | {W3.fmt_r(d['kept_share'])} | {fmt_a(d['auroc']['input'])} | {fmt_a(d['auroc']['computation'])} | "
                     f"{W3.fmt_r(hc)} | {' '.join(f'{k}:{v}' for k, v in d['agreement_hist'].items())} |")
    L += ["", "## (a) Kept (agreement >= 2) vs all claims", "",
          "| reader | family | states with a kept computation claim | states whose computation claims name the ACTUAL / value: kept vs all | states naming the CORRECT answer: kept vs all | "
          "computation precision vs actual: kept / all / dropped | vs correct: kept / all | input false share: kept vs all | true input claims kept |",
          "|---|---|---|---|---|---|---|---|---|"]
    for rd, R in S["readers"].items():
        for fam, d in R.items():
            kv = d["kept_vs_all"]
            pa = kv.get("precision_vs_actual_judge") or kv.get("precision_vs_value_judge")
            pc = kv.get("precision_vs_correct_judge")
            ifs = kv["input_false_share"]
            L.append(f"| {rd} | {fam} | {W3.fmt_r(kv['states_with_kept_computation_claim'])} | {fmt_d(kv['states_naming_actual_or_value'])} | "
                     f"{fmt_d(kv.get('states_naming_correct')) if fam == 'errors' else '(= value)'} | {W3.fmt_p(pa['kept'])} / {W3.fmt_p(pa['all'])} / {W3.fmt_p(pa['dropped'])} | "
                     f"{(W3.fmt_p(pc['kept']) + ' / ' + W3.fmt_p(pc['all'])) if pc else '—'} | {W3.fmt_r(ifs['kept'])} vs {W3.fmt_r(ifs['all'])} | {W3.fmt_r(kv['input_true_kept_share'])} |")
    if any("by_native_lo" in d["kept_vs_all"] for R in S["readers"].values() for d in R.values()):
        L += ["", "Kept vs all (states naming the actual / value) inside the native-LO cells: " + "; ".join(
            f"{rd}/{fam} {cell}: {fmt_d(x)}" for rd, R in S["readers"].items() for fam, d in R.items() for cell, x in d["kept_vs_all"].get("by_native_lo", {}).items())]
    L += ["", "## (c) Random-vector self-consistency", "",
          "| reader | random vectors (samples/vector) | random claims | random claim matches a RECURRING natural claim (some state) | matches any natural claim | "
          "control: natural recurring claim matches another state | natural claims recurring (>= 2/8) | natural at >= 7/8 | within-random recurrence |",
          "|---|---|---|---|---|---|---|---|---|"]
    for rd, r in S["random"].items():
        w = r["within_random_recurrence"]
        ws = "n/a (1 sample per vector)" if not w else f">=2: {W3.fmt_r(w['recur_ge2'])}; >=7/8: {W3.fmt_r(w['recur_ge_7_of_8'])}"
        L.append(f"| {rd} | {r['n_random_vectors']} ({', '.join(f'{k}x{v}' for k, v in r['samples_per_vector'].items())}) | {r['n_random_claims']} | "
                 f"{W3.fmt_r(r['random_matches_recurring_natural_claim'])} | {W3.fmt_r(r['random_matches_any_natural_claim'])} | {W3.fmt_r(r['control_natural_recurring_matches_other_state'])} | "
                 f"{W3.fmt_r(r['natural_recur_ge2'])} | {W3.fmt_r(r['natural_recur_ge_7_of_8'])} | {ws} |")
    L += ["", "Michael's 29% is the share of a random vector's sample-1 claims supported by >= 6 of its 7 other samples (Gemini-judged support); with one S4 sample per "
          "random vector the comparable within-vector number is only available when >= 2 samples exist, so the cross-state rate (random claim matches a claim that "
          "recurs in some natural state) is reported with its natural control (a recurring claim matching another state)."]
    if sens:
        L += ["", "## Sensitivity to the matcher", "", "| matcher | " + " | ".join(f"{rd}/{fam} AUROC input / computation; kept share" for rd in S["readers"] for fam in S["readers"][rd]) + " |",
              "|---|" + "---|" * sum(len(R) for R in S["readers"].values())]
        for mode, s2 in sens.items():
            cells = [f"{fmt_a(s2['readers'][rd][fam]['auroc']['input']).split(' (')[0]} / {fmt_a(s2['readers'][rd][fam]['auroc']['computation']).split(' (')[0]}; "
                     f"{100 * (s2['readers'][rd][fam]['kept_share']['rate'] or 0):.0f}%" for rd in S["readers"] for fam in S["readers"][rd]]
            L.append(f"| {mode} | " + " | ".join(cells) + " |")
    L += ["", "## Verdict against the pre-registered expectation", ""]
    for rd, R in S["readers"].items():
        for fam, d in R.items():
            x = d["kept_vs_all"]["states_naming_actual_or_value"]
            a = d["auroc"]["computation"]
            gain = (x["diff"] is not None and x["lo"] is not None and x["lo"] > 0)
            sep = (a.get("lo") is not None and a["lo"] > 0.5)
            L.append(f"- {rd}/{fam}: keeping recurring claims {'RAISES' if gain else 'does not raise'} the share of states naming the "
                     f"{'actual answer' if fam == 'errors' else 'value'} ({fmt_d(x)}); agreement count {'separates' if sep else 'does not separate'} correct from wrong "
                     f"computation claims ({fmt_a(a)}) vs input claims ({fmt_a(d['auroc']['input'])}).")
    if notes:
        L += ["", "## Notes", ""] + [f"- {n}" for n in notes]
    return "\n".join(L) + "\n"


def make_figure(S: dict, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    readers = list(S["readers"])
    fams = W3.FAMILIES
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6))
    # left: AUROC bars, groups = family x claim type, bars = readers
    groups = [(f, t) for f in fams for t in ("input", "computation")]
    w = 0.36
    for i, rd in enumerate(readers):
        xs, ys, lo, hi = [], [], [], []
        for g, (f, t) in enumerate(groups):
            a = S["readers"][rd][f]["auroc"][t]
            if a.get("auroc") is None:
                continue
            xs.append(g + (i - 0.5) * w)
            ys.append(a["auroc"])
            lo.append(a["auroc"] - (a["lo"] if a["lo"] is not None else a["auroc"]))
            hi.append((a["hi"] if a["hi"] is not None else a["auroc"]) - a["auroc"])
        ax1.bar(xs, ys, w * 0.94, color=COLORS.get(rd, "#888"), label=rd, yerr=[lo, hi], capsize=3, error_kw={"lw": 1, "color": "#444"})
    ax1.axhline(0.5, color="#999", lw=1, ls=":")
    for g, (f, t) in enumerate(groups):
        ref = MICHAEL["auroc_input"] if t == "input" else MICHAEL["auroc_internal"]
        ax1.plot([g - 0.45, g + 0.45], [ref, ref], color="#444", lw=1.2, ls="--")
    ax1.set_xticks(range(len(groups)))
    ax1.set_xticklabels([f"{f}\n{t}" for f, t in groups])
    ax1.set_ylim(0.0, 1.0)
    ax1.set_ylabel("AUROC of agreement count vs claim correctness")
    ax1.set_title("(b) consistency separates correct from wrong claims?\n(dashed: Michael's NLA, input 0.90 / internal 0.75; dotted: chance)", fontsize=10)
    ax1.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=len(readers))
    # right: kept vs all rates (states naming the actual / value), each with its Wilson CI; the paired difference as text
    labels, xpos = [], 0
    for rd in readers:
        for f in fams:
            x = S["readers"][rd][f]["kept_vs_all"]["states_naming_actual_or_value"]
            if x.get("diff") is None:
                continue
            col = COLORS.get(rd, "#888")
            n = x["n"]
            for dx, rate, hatch, alpha, lab in ((-0.2, x["rate_b"], None, 0.45, "all claims"), (0.2, x["rate_a"], "//", 1.0, f"kept (>= {KEEP_MIN} of 8)")):
                _, lo, hi = wilson(int(round(rate * n)), n)
                ax2.bar(xpos + dx, rate, 0.38, color=col, alpha=alpha, hatch=hatch, edgecolor="white" if hatch else None, label=lab if xpos == 0 else None)
                ax2.errorbar([xpos + dx], [rate], yerr=[[rate - lo], [hi - rate]], fmt="none", ecolor="#444", capsize=3, lw=1)
            if x["lo"] is not None:
                ax2.text(xpos, 1.02, f"Δ {100 * x['diff']:+.0f} [{100 * x['lo']:+.0f}, {100 * x['hi']:+.0f}]", ha="center", va="bottom", fontsize=8, color="#333")
            labels.append(f"{rd}\n{f} (n={n})")
            xpos += 1
    ax2.set_xticks(range(len(labels)))
    ax2.set_xticklabels(labels)
    ax2.set_ylim(0, 1.12)
    ax2.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax2.set_ylabel("share of states whose computation claims\nname the actual answer (errors) / value (counts)")
    ax2.set_title("(a) kept vs all claims\n(bars: Wilson CI; text: kept − all with state-paired bootstrap CI)", fontsize=10)
    ax2.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2)
    for ax in (ax1, ax2):
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)


def sample_inventory(s4_rows: List[dict]) -> Dict[Tuple[str, str], int]:
    inv: Dict[Tuple[str, str], set] = defaultdict(set)
    for r in s4_rows:
        if r.get("condition") == "natural":
            inv[(W3.reader_name(r["reader"]), r["state_item_id"])].add(int(r.get("sample_idx", 0)))
    return {k: len(v) for k, v in inv.items()}


def run(*, claims_path: Path = W3.CLAIMS_S4, s4: Path = W3.S4_SAMPLES, s3: Path = W3.S3_LO, x3: Path = W3.X3_LO, out_dir: Path = OUT_W4, n_boot: int = N_BOOT,
        seed: int = SEED, mode: str = "primary", figure: bool = True, sensitivity: bool = True, notes: Sequence[str] = ()) -> dict:
    claims = W3.load_claims(claims_path)
    if not claims:
        raise SystemExit(f"no judged claims at {claims_path}")
    inv = sample_inventory(W3.read_jsonl(s4)) if Path(s4).exists() else None
    actual_of = {c["item_id"]: c.get("actual_answer") for c in claims if c.get("actual_answer") is not None}
    lo = W3.native_lo(W3.read_jsonl(s3), W3.read_jsonl(x3), actual_of)
    S = summarise(claims, n_boot=n_boot, seed=seed, mode=mode, n_samples=inv, lo=lo)
    ann = S.pop("annotated")
    sens = None
    if sensitivity:
        sens = {m: summarise(claims, n_boot=0 if n_boot == 0 else 100, seed=seed, mode=m, n_samples=inv) for m in ("strict", "lenient") if m != mode}
        for s2 in sens.values():
            s2.pop("annotated", None)
    inputs = {"claims": str(claims_path), "s4": str(s4) if inv else None, "s3_lo": str(s3) if Path(s3).exists() else None, "x3_lo": str(x3) if Path(x3).exists() else None}
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    W3.write_jsonl(out_dir / "claims_agreement.jsonl", [{k: (sorted(v) if isinstance(v, frozenset) else v) for k, v in c.items() if k not in ("prompt_text",)} for c in ann])
    rows = csv_rows(S)
    with (out_dir / "w4.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    (out_dir / "w4_summary.json").write_text(json.dumps({"summary": S, "sensitivity": sens, "inputs": inputs, "notes": list(notes)}, indent=1, ensure_ascii=False, default=str))
    (out_dir / "w4.md").write_text(render_md(S, inputs, sens, notes))
    if figure:
        make_figure(S, out_dir / "fig_w4.png")
    return S


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--claims", type=Path, default=W3.CLAIMS_S4)
    ap.add_argument("--s4", type=Path, default=W3.S4_SAMPLES)
    ap.add_argument("--s3", type=Path, default=W3.S3_LO)
    ap.add_argument("--x3-lo", type=Path, default=W3.X3_LO)
    ap.add_argument("--out", type=Path, default=OUT_W4)
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--match", default="primary", choices=["primary", "strict", "lenient"])
    ap.add_argument("--no-figure", action="store_true")
    ap.add_argument("--no-sensitivity", action="store_true")
    ap.add_argument("--note", action="append", default=[])
    a = ap.parse_args(argv)
    run(claims_path=a.claims, s4=a.s4, s3=a.s3, x3=a.x3_lo, out_dir=a.out, n_boot=a.n_boot, seed=a.seed, mode=a.match, figure=not a.no_figure, sensitivity=not a.no_sensitivity, notes=a.note)
    print((Path(a.out) / "w4.md").read_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
