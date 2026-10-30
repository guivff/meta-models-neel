"""V3 claim table and sensitivity proxies, built from Michael Kenney's `nla-consistency/data/` (CPU, no model calls).

What his release contains (checked 2026-10-11, see `control_inventory`):
  * `claims/<family>.jsonl` — the original readout of each of the 500 WorkspaceBench items split into atomic claims
    with a label against the source (`workspace`, `background_true`, `misquote`, `contradicted`, `invented_content`,
    `unverifiable`); `claims/<family>.readouts.jsonl` — the original readout texts.
  * `claim_signals.jsonl` — per claim: `sample_support_of_8` (how many of 8 fresh NLA samples of the SAME activation
    state the claim, Gemini-judged), `adjacent_support_of_3` (same for one readout at each of the 3 preceding tokens),
    `internal_label` for workspace claims (`correct` / `wrong` / `vague` / `excluded`).
  * `nla_samples.jsonl` — the 8 samples and 3 adjacent-token readouts per item (texts).
  * `prior_consistency.jsonl` — for 20 GLOBAL random Gaussian vectors at the mean activation norm (`noise|j`), the mean
    vector (`mean|0`) and 40 real items, sample 1 split into claims with the count of samples 2–8 that repeat each
    claim. Only the judged claims of sample 1 are released, not the 8 readout texts; and the random vectors are not
    per-state perturbations (there is one shared set of 20, not one per item).

So there are NO per-state perturbed or control-vector readouts; the sensitivity score of the brief
(1 − P(claim recurs under matched-norm random readouts of the same state)) cannot be computed as written.
Proxy (fixed before any AUROC was computed; the only free parameter, the match threshold TAU, was chosen label-free
by agreement with his judged `sample_support_of_8`, see `results/g_agreement/v/v3.md`):

  match(claim, readout) := idf-weighted recall of the claim's stemmed content terms in the readout ≥ TAU (0.50)
  prior_rate_family     := share of the 8 × 99 readouts of the OTHER states of the same family that match the claim
  sens_family           := 1 − prior_rate_family            (primary sensitivity proxy)
  sens_all              := 1 − share over the 8 × 499 readouts of all other states   (secondary)
  sens_noise            := 1 − max idf-weighted recall against the 146 released random-vector claims (secondary)
  own_proxy8            := number of the claim's own 8 samples that match (the same matcher applied to his signal,
                           to show how much of his judged recurrence the lexical matcher recovers)

A claim the NLA emits for other activations of the same family regardless of content ("the next token must begin
the second line of the couplet") has a high prior rate and low sensitivity; a claim tied to this activation has a
low prior rate. Reuse of his labels, counts and texts is cited: M. Kenney, `nla-consistency` (2026).
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

FAMS = ["multihop", "poetry", "typo", "association", "basic_readout"]
TRUE_INPUT = ("workspace", "background_true")       # his TRUE set for input claims
FALSE_INPUT = ("misquote", "contradicted")          # his FALSE set for input claims
TAU = 0.50                                          # match threshold (label-free calibration, v3.md "Matcher")
N_SAMPLES = 8
_SUFFIXES = ("ingly", "edly", "ing", "ed", "es", "s", "ly")


def jl(path: Path) -> List[dict]:
    path = Path(path)
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()] if path.exists() else []


def stem(w: str) -> str:
    for suf in _SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def tokens(text: str) -> List[str]:
    """Lower-cased alphanumeric content terms (English stop words and 1-char tokens dropped), crudely stemmed."""
    return [stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in ENGLISH_STOP_WORDS and len(w) > 1]


class TermMatcher:
    """idf-weighted recall of a claim's content terms in a document.

    idf is fitted on the readout corpus passed to the constructor (log(N / (1 + df)) + 1). Terms of a claim that never
    occur in the corpus get the maximal idf and sit in the denominator only, so an unmatched specific term lowers recall.
    """

    def __init__(self, docs: Sequence[str]):
        self.n_docs = len(docs)
        df: Counter = Counter()
        for d in docs:
            df.update(set(tokens(d)))
        self.vocab: Dict[str, int] = {w: i for i, w in enumerate(sorted(df))}
        self.idf = np.array([math.log(self.n_docs / (1 + df[w])) + 1.0 for w in sorted(df)], dtype=np.float64)
        self.idf_unseen = math.log(max(self.n_docs, 1)) + 1.0

    def _doc_matrix(self, docs: Sequence[str]) -> sp.csr_matrix:
        rows, cols = [], []
        for j, d in enumerate(docs):
            for w in set(tokens(d)):
                i = self.vocab.get(w)
                if i is not None:
                    rows.append(j)
                    cols.append(i)
        return sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(docs), len(self.vocab)))

    def recall_matrix(self, claims: Sequence[str], docs: Sequence[str]) -> np.ndarray:
        """(n_claims × n_docs) idf-weighted recall in [0, 1]; a claim without content terms scores 0 everywhere."""
        rows, cols, vals, den = [], [], [], np.zeros(len(claims))
        for i, c in enumerate(claims):
            for w in set(tokens(c)):
                k = self.vocab.get(w)
                if k is None:
                    den[i] += self.idf_unseen
                else:
                    rows.append(i)
                    cols.append(k)
                    vals.append(self.idf[k])
                    den[i] += self.idf[k]
        W = sp.csr_matrix((vals, (rows, cols)), shape=(len(claims), len(self.vocab)))
        num = np.asarray((W @ self._doc_matrix(docs).T).todense())
        with np.errstate(divide="ignore", invalid="ignore"):
            out = np.where(den[:, None] > 0, num / np.maximum(den[:, None], 1e-12), 0.0)
        return out


def load_claim_table(data_dir: Path) -> pd.DataFrame:
    """One row per claim of the 500 items, joined with his signals and labels (reconstructs his notebook's `recs`)."""
    data_dir = Path(data_dir)
    sig = {d["key"]: d for d in jl(data_dir / "claim_signals.jsonl")}
    rows = []
    for fam in FAMS:
        for r in jl(data_dir / "claims" / f"{fam}.jsonl"):
            for n, c in enumerate(r["claims"]):
                key = f"{fam}|{r['id']}|{n}"
                s = sig.get(key, {})
                label, internal = c["label"], s.get("internal_label")
                s8, a3 = s.get("sample_support_of_8"), s.get("adjacent_support_of_3")
                if label in TRUE_INPUT or label in FALSE_INPUT:
                    claim_type, y = "input", float(label in TRUE_INPUT)
                else:
                    claim_type, y = None, np.nan
                internal_y = {"correct": 1.0, "wrong": 0.0}.get(internal, np.nan)
                rows.append(dict(key=key, family=fam, id=r["id"], claim_idx=n, claim=c["claim"], label=label,
                                 internal_label=internal, input_type=claim_type, y_input=y, y_internal=internal_y,
                                 support8=s8, adjacent3=a3,
                                 recurrence=np.nan if s8 is None else s8 / N_SAMPLES,
                                 adjacent=np.nan if a3 is None else a3 / 3.0))
    return pd.DataFrame(rows)


def load_samples(data_dir: Path) -> Dict[Tuple[str, str], List[str]]:
    return {(r["family"], r["id"]): list(r["samples"]) for r in jl(Path(data_dir) / "nla_samples.jsonl")}


def load_noise_claims(data_dir: Path) -> List[dict]:
    """The released sample-1 claims of the 20 random vectors, with their 0–7 support among samples 2–8."""
    return [c for d in jl(Path(data_dir) / "prior_consistency.jsonl") if d["key"].startswith("noise|") for c in d["r"]["claims"]]


def control_inventory(data_dir: Path) -> dict:
    """What control-vector material exists. Per-state perturbed readouts: none (see module docstring)."""
    pc = jl(Path(data_dir) / "prior_consistency.jsonl")
    kinds = Counter(d["key"].split("|")[0] for d in pc)
    noise = [c["support"] for d in pc if d["key"].startswith("noise|") for c in d["r"]["claims"]]
    real = [c["support"] for d in pc if d["key"].startswith("real|") for c in d["r"]["claims"]]
    ns = jl(Path(data_dir) / "nla_samples.jsonl")
    keys = set().union(*(r.keys() for r in ns)) if ns else set()
    return dict(
        n_noise_vectors=kinds.get("noise", 0), n_mean_vectors=kinds.get("mean", 0), n_real_items=kinds.get("real", 0),
        n_noise_claims=len(noise),
        noise_mean_support_frac=float(np.mean(noise) / 7) if noise else float("nan"),
        noise_share_ge6_of_7=float(np.mean([v >= 6 for v in noise])) if noise else float("nan"),
        real_mean_support_frac=float(np.mean(real) / 7) if real else float("nan"),
        real_share_ge6_of_7=float(np.mean([v >= 6 for v in real])) if real else float("nan"),
        noise_readout_texts_released=False,
        per_state_control_readouts=False,
        per_state_fields_in_nla_samples=sorted(keys),
    )


def add_sensitivity(df: pd.DataFrame, samples: Dict[Tuple[str, str], List[str]], noise_claims: Iterable[str],
                    tau: float = TAU) -> pd.DataFrame:
    """Append own_proxy8, prior_rate_family, prior_rate_all, sens_family, sens_all, noise_max_recall, sens_noise."""
    items = sorted(samples)
    docs, doc_item = [], []
    for it in items:
        for s in samples[it]:
            docs.append(s)
            doc_item.append(it)
    doc_item = np.array([f"{f}|{i}" for f, i in doc_item])
    doc_fam = np.array([f for f, _ in (it.split("|", 1) for it in doc_item)])
    matcher = TermMatcher(docs)
    R = matcher.recall_matrix(df["claim"].tolist(), docs) >= tau
    claim_item = (df["family"] + "|" + df["id"]).to_numpy()
    claim_fam = df["family"].to_numpy()
    own = np.zeros(len(df)); pf = np.full(len(df), np.nan); pa = np.full(len(df), np.nan)
    for i in range(len(df)):
        self_mask = doc_item == claim_item[i]
        own[i] = R[i, self_mask].sum()
        fam_mask = (doc_fam == claim_fam[i]) & ~self_mask
        if fam_mask.any():
            pf[i] = R[i, fam_mask].mean()
        if (~self_mask).any():
            pa[i] = R[i, ~self_mask].mean()
    noise_claims = list(noise_claims)
    nmax = matcher.recall_matrix(df["claim"].tolist(), noise_claims).max(axis=1) if noise_claims else np.zeros(len(df))
    out = df.copy()
    out["own_proxy8"] = own
    out["proxy_recurrence"] = own / N_SAMPLES
    out["prior_rate_family"] = pf
    out["prior_rate_all"] = pa
    out["sens_family"] = 1 - pf
    out["sens_all"] = 1 - pa
    out["noise_max_recall"] = nmax
    out["sens_noise"] = 1 - nmax
    return out


def build(data_dir: Path, tau: float = TAU) -> Tuple[pd.DataFrame, dict]:
    df = load_claim_table(data_dir)
    df = add_sensitivity(df, load_samples(data_dir), [c["claim"] for c in load_noise_claims(data_dir)], tau=tau)
    return df, control_inventory(data_dir)
