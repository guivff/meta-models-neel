## §79 S1. Probe-gap screen over 100+ scripted features

**Owner:** lens chat (freed by the §64 cut). **Cap:** 1.5 GPU-h. **Target:** features frozen Friday 20:00; ranking
frozen Sunday 18:00.

- **Corpus.** 2,400 documents, 600 each of prose, Python, LaTeX and tables/markdown, from pinned public datasets (HF
  revision recorded) and our frozen banks. The manifest is hashed before capture.
- **Features.** ≥ 100 binary features computed by deterministic scripts from the text up to the read position.
  - Examples: bracket depth ≥ 1 or ≥ 2; inside a string, a math environment or a code block; table column index; line
    index; indentation level; items so far in a list; position in the sentence; quote state; part of speech of the
    current token; tense of the clause; numeric magnitude; language; register; capitalisation.
  - `features.py` and its unit tests are frozen before capture, and each feature carries a class label (count-like /
    state-like / semantic) assigned there.
- **Sampling.** Per feature: 150 positive and 150 negative positions, matched on domain and absolute-position bin (5
  bins), with ≤ 3 positions per document. A feature with fewer than 100 per side is dropped, and the drop is reported.
- **Arms.**
  - Grouped-CV probe (grouped by document) at blocks 42 and 44.
  - Oracle lens and NLA asked scoring, with one phrasing pair per feature, generated from the feature's definition by
    a fixed template and frozen with `features.py`.
  - The mismatched gate (§70 rule) for every feature.
- **Outcome.** gap = probe AUROC − reader asked AUROC, per reader × feature, among features with probe ≥ 0.85 that
  pass the gate.
- **Primary rules.**
  - (H1) The Oracle lens's mean gap on count- and state-like features exceeds its mean gap on semantic features by
    ≥ 0.10 (feature-level bootstrap CI > 0).
  - (H2) On count- and state-like features, the NLA's mean gap is smaller than the Oracle lens's by ≥ 0.10 (paired
    bootstrap CI > 0).
- **Selection for §84.** The top 10 features by Oracle gap, excluding those already in W1. The list is committed
  before any §84 item is built.

