# P3 pre-launch review of §73 W4

Review status: **APPROVED for the exact code bytes below**. No blocking defect found in the requested residual construction, norm rescaling or three controls. This is a code review, not a GPU allocation or authorization for P3 to run anything.

Reviewed local W-mechanism implementation before its push (concurrent changes prevented its rebase). Remote r/blindspot still has the superseded scaffold. W-mechanism must commit/freeze the reviewed bytes in its own branch before launch; changed bytes require re-review. Do not launch the older remote scaffold.

- `ar_tests.py` SHA256: `69b1991881413ea5b07bd469427b1afca13538a2d065e7da39919878044db769`
- Adopted `BRIEF_BLINDSPOT.md` SHA256: `eaeec74a6d0e36f381f514c000565c6282f1350d988e897303162386036d5d6e`

## Checks

1. **Residual and swap (lines125–158): PASS.** Per-item residual is raw `h - AR(OL(h))`, with matching shapes and finite float32 CPU inputs. Main synthetic state is recipient reconstruction plus donor residual. The implementation does not substitute a projection onto one feature direction.
2. **Rescaling (lines142–158): PASS.** The entire synthetic vector is rescaled to the recipient activation norm. The same rule is applied to every arm. Zero or nonfinite synthetic norms fail; identity/self recovers the recipient to floating-point tolerance. Inputs are not modified.
3. **All three controls (lines146–149,257–291): PASS.** Self uses recipient residual; random uses a same-domain item excluding recipient/donor, selected without examining its value; AR-only omits the residual. Random control values are not selected to be opposite. Forty directed test pairs are sampled without replacement, opposite-value and matched in domain/template family/length bin.
4. **NLA scoring/site (lines160–180,924–940): PASS.** Direct import of the same `mats.readers.nla.paired_logodds_templates` used by W-core run.py337–345; same load flags, default explanation prefix, positive-candidate order and exact sealed W1 phrasing pairs. Synthetic block44 vectors are read through NLA's block42-native interface and explicitly labelled OFF-NATIVE. There is no unregistered block42 reconstruction.
5. **Sealing and analysis (lines294–342,895–959): PASS.** Pair/template/definition grid is sealed before scoring; target/residual/order/template hashes checked. Scores are complete and sealed before analysis labels are joined. Donor AUROC is used for blind-spot rows and recipient AUROC for semantic rows, with template-cluster bootstrap. The blind-spot CI lower-bound gate and semantic AUROC gate match §73. No pooled fraction threshold is invented.
6. **Review/admission gate (lines458–465,476–532): PASS.** Exact AR source and brief hashes bind this approval; assignment/source/cap/own pod checks still apply. A code approval does not waive upstream W1/W3 or integrator staging/allocation gates.

## CPU validation

Independent rerun: `test_ar_mechanism.py` plus `test_ar_pipeline.py`, **48 passed in4.74s**, using CPU synthetic fixtures, bytecode/cache writes disabled. This covers formula/control identity, norm preservation, zero-vector refusal, exact upstream scorer/phrasing dispatch, matched pairing, donor-value-blind random selection, malformed grids, donor/recipient analysis and sealed pipeline. No model forward, GPU usage, judge/API call or real scientific outcome was produced. It does not validate actual checkpoint/kernel/runtime compatibility.

## Interpretation notes (non-blocking)

- Directed pairs may reuse items, and both directions may be sampled. They are not 40 independent items. Preserve the template-cluster analysis and report unique items/families; a small number of families limits bootstrap reliability.
- Opposite-value donor/recipient labels make their AUROCs complementary; they are not independent corroboration.
- Control expectations are diagnostics, not extra registered numerical pass thresholds. Report self/random/AR-only results even if inconvenient. OFF-NATIVE results do not establish the native block42 mechanism.
- Random donors can come from other same-domain rows/dev pool, as disclosed by the frozen pairing rule. This is a same-domain residual control, not a same-template population estimate.
