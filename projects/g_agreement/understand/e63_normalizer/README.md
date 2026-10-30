# E63 full normalized real-row inventory

Guiv delegated normalization and the verified receipt to W-mech2 on 2026-10-28.
The receipt truthfully names W-mech2; it does not impersonate Integrator.
This is a CPU format/custody adapter, not a repeat of any completed bank analysis.

Freeze all input metadata and source seals; commit this package and pass synthetic
tests before running `python3 -m projects.g_agreement.understand.e63_normalizer.normalize`.
That command verifies all pinned files and seals, then writes the ignored bundle
and receipt to the original E63 SPEC destinations. It never calls a scorer.
The serialized list order follows the existing native sampling/input order and the
unchanged800-record pool order. The existing400-record D5 packet is untouched.

The complete inventory is138 row-reader cells: E56 13×2, E57 20×2, E59 6×2,
E62 30×2. All acquired native readouts are retained, including nonbinary/count/eval
rows; E62 NLA's30 unacquired cells are explicit NOT_RUN. E56 injection readouts are
retained separately as non-native source records, never substituted for native text.
Missing native rates remain NOT_EVALUABLE, not MISSED. Existing bank rates and the
registered S≥.20/lowerCI>0 criterion determine reporting status without rescoring.

Regex definitions come byte-for-byte from the already-frozen E76 REGEX_CATALOG,
whose source files are also pinned. No aliases, escaping corrections or stemming
are added. Unavailable regexes remain explicit NOT_EVALUABLE. E57's multiple value
families use the frozen annotation groups and exact test counts; no family selection
uses readout text. Labels stay in the private CPU bundle.

The original readerbench-v1 loader cannot encode this inventory: it assumes a
COMPLETE_ONCE status literal, one pattern pair for every row, and acquired outputs
for every cell. Actual bank seals say COMPLETE and seal an ONCE.json. These original
seals are verified without rewriting them or manufacturing replacement bank seals.
The v2 compatibility command is:

```
python3 -m projects.g_agreement.understand.e63_normalizer.analyze --verify-only
python3 -m projects.g_agreement.understand.e63_normalizer.analyze
```

Only Integrator runs the second command, once. It uses the ORIGINAL global E63
REGEX_ANALYSIS_ONCE.json guard and original regex_once output path. Do not run the
legacy wrapper on this v2 bundle. No original sealed code or source seals are edited.
Every load independently reconstructs the full normalized source join before scoring.
Single-family scoring is regression-tested against the unchanged registered scorer.
For multiple families, real records use their own frozen family; the same placebo
vectors are scored under each family, weighted by fixed native test-family counts.
Scores are combined per vector before the unchanged item-bootstrap (2000 draws,
20261027 real /20261028 placebo; random placebo labels seed20261029). This retains
shared-vector dependence. Both/neither score zero; no vectors are dropped. R-P1
threshold and REPORTED eligibility are unchanged. Unknown/nonbinary/unacquired cells
remain explicit, with no fabricated zero rates. R-P2 remains W-internals' separate
D5 analysis and requires matching-reader MISSED references.

Large DATA.json is private/ignored; commit the text-free inventory and hash receipt,
which locate and bind the local payload and all original sealed source records.
