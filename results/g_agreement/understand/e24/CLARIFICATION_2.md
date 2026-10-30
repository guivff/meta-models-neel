Authority: 88841629 (analysis rules), db564376 (source hash). Original pre-generation snapshot remains unchanged.

**Dated clarification 2, 2026-10-25 10:40 CET (after an independent red-team review of the registrations; before any
E24 capture or score).** Two rules were wrong as written and are corrected now, on the sealed E1b data, not on E24
data:
- **R6 was contradicted before the run.** E1b's sealed continuation AUROCs on count/position rows already exceed 0.65
  at layer 44 (python_argument 0.8994, python_indent 0.8810, table_row 0.7517). R6 is withdrawn. Replacement **R6′:**
  C5 is reported per row and layer, descriptively, with the layer-44 cell required to reproduce E1b within ±0.03 (R0);
  no across-layer rule.
- **R3's swap control passed a swap that does nothing.** "Swap ≤ 0.50" is satisfied at exactly 0.50. Replacement
  **R3′:** C2 ≥ 0.70 on a majority of valid rows, *and* the same-layer opposite-state swap gives AUROC ≤ 0.40 on those
  rows (CI upper bound < 0.50), i.e. the swap reverses the preference rather than merely removing it.
- Predictions updated accordingly: R1, R3′, R4 and R5 hold at all or almost all layers; C5 is descriptive.


**Dated correction, 2026-10-25 10:10 CET (coordinator transcription error; before any E24 capture or score).** In
clarification 1 the abbreviated sha256 of `experiments/14_ar_blindspot/modal14.py` was written `339be5ba…a8de8fc`. The
correct full hash is `339be5ba5d830dc50cd4d0a5fcb88c3c74b012a4b590a883b10c7dfa351de8fc` (suffix `51de8fc`), verified
from the pinned commit by W-core, the integrator and the coordinator independently. The file is the pinned one; only the
abbreviation was wrong. The other five hashes in clarification 1 are rechecked against full hashes and correct. The
source gate uses the full hash.

