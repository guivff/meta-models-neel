# §177 clarification1 — 6f9088bb

Supersedes the historical input SELECTION.json for display selection only. Acquisition inputs, GPU source seals, pools, model calls and scoring rules are unchanged. No display-only acquisition.

Select from verified acquired test identities, lowest ID plus two without-replacement draws from the remaining sorted IDs, NumPy PCG64 seed20261027. Eligibility requires all8repeats from both readers. D2 intersects implicit/report/first-letter framing coverage, selects on implicit IDs, and carries the exact same base IDs to every framing. No lexical content or score enters eligibility or selection. D3 requires all frozen token positions acquired for the selected prompt; D4 requires all three matched arms. D6 retains its explicitly registered two directions/all arms, with no invented third direction.

Updated entrypoints: analysis_acquired61.py (D3/D4) and export_acquired61.py (D2/D6). They verify the original acquisition seals plus DISPLAY_SOURCE_SEAL.json. Both retain the existing exclusive once-only output directory. No output has been produced or replaced. The display selection itself is recorded with the output at execution, from the integrator-verified pull.
