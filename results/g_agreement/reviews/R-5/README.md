R-5 E118b reproduction prepared under coordinator commit 434061b36 item 4.

`reproduce_e118b.py` independently groups the raw terminal three-way judgments by original family/item, derives original belief/truth membership from sealed categorical source references, and recomputes every numeric/count/reading field in pooled and family summaries. It uses common/stats.py directly: item bootstrap 5,000 draws, seed 0; readout Wilson z=1.96. Item order follows the original frozen custody sequence so deterministic bootstrap endpoints are comparable. Both-stating membership remains overlapping; unknown classifications remain unknown; missing positions exclude the whole item from descriptive estimates and invalidate the affected reading; no-truth items remain separate. No reader, judge, provider, owner adapter, watcher or once guard is invoked.

Synthetic-only preparation:

    python results/g_agreement/reviews/R-5/reproduce_e118b.py --self-test
    python -m pytest -q projects/g_agreement/e118b_analysis/test_analysis.py

After the final scientific seal opens, run from the repository root with the independently verified seal digest:

    python results/g_agreement/reviews/R-5/reproduce_e118b.py \
      --analysis-seal /absolute/path/ANALYSIS_SEAL.json --seal-sha256 VERIFIED_SHA256

The real-input path checks the preparation source pins, COMPLETE_ONCE E118b seal and all sealed member hashes before reading BINDING or raw judgments. It then checks the original 6,790-position/209-item UNIT_SEAL, original source refs and literal context/readout membership, bank source/input/privacy metadata and input/cap seals. It prints aggregate verification metadata only. It writes no outputs or guards. Unchanged source pin mismatches stop for inspection; do not silently refresh pins after outputs open.

This is a numerical reproduction tool, not a complete custody verdict. Final review must separately verify transport/prompt wires, Git commit versus actual archived first-output chronology, source-before-seal compliance, original physical response/cost/audit links, conservative 429 upper-bound treatment and the combined lifetime USD1 cap including part-a USD0.027057. The owner README's stale R-2 assignment is superseded by §236 clarification 3: R-5 is sole E118b reviewer. No real E118b result or partial judgment was opened during preparation.

E138 (§250, clarification1): `reproduce_e138.py` is a pre-output statistical core only, tested by `test_reproduce_e138.py` (7 synthetic cases). Donor arm alone determines the primary descriptive reading; random recipient-old can withdraw the wording but a low rate cannot support it. All-arm coherence, dual/multiple and missing counts plus Wilson intervals and supplementary completion bounds are retained. Exact original rubric normalization, E100 pairing/seed, E76 random protocol, E127 no-prefix clean reuse, source/cap/chronology bindings remain PENDING until the owner adapter/tests arrive. No real-input CLI is enabled and no source-conformance verdict is claimed.

E138 owner source5a8e024f now bound prospectively: `reproduce_e138.py --analysis-seal /absolute/ANALYSIS_SEAL.json --seal-sha256 VERIFIED_SHA` verifies the final COMPLETE_ONCE seal and private binding before resolving real original references. All owner arm/count/Wilson/2000-draw paired bootstrap/contrast/missingness/readings fields are independently compared; bootstrap uses common.stats.py with sorted recipient IDs, seed20261027 and separate arm masks. Eight reviewer tests plus14owner tests pass. This supersedes the earlier no-CLI/schema-pending preparation note; actual identity/source/first-output/physical-charge custody still requires terminal review.

E140 (§252): independent prospective `reproduce_e140.py` statistical/selection kernel and12reviewer tests plus22owner synthetics PASS. Only both-X/Y pairs enter tracking/prior; other, none, terminal missing and all coverage denominators are separate, no cross-block filtering. common.stats Wilson z1.96 reproduces all fields. First84 selection is checked against full600original screen labels/order; no parser rerun. Actual final raw-reference normalizer remains PENDING; no real-input CLI until exact frozen bindings arrive. I2 resource HOLD remains its responsibility, no trim/pilot/cap change authorized by reviewer preparation.
