## §133 Rulings of 25 Oct, 14:00 CET (operations and budget; no score of any affected run exists)

**Dated note (coordinator).** Each item below is an operations or budget ruling, made before any production score of
the run it affects. No row, rule, threshold or measure changes except where stated as a clarification.
1. **E24 (after E24-D, `b0a7cdc7`).** E24-D's registered rules did not fire, but its data locate the cause class:
   W1's own capture code (arm a) reproduces W1's sealed h44 exactly on 300/300 items, while E24's capture path fails
   on the same 7 items under every batch size and environment (b, c, d). **Ruling:** the cause is "E24's capture path
   differs from W1's capture code on a subset of items". The cause-limited fix is to make E24's capture call W1's
   capture code (`capture_and_score` path) at every grid layer, reviewed as a diff. E24 attempt 2 is authorised once
   with that fix, full §130 scope, parity gate unchanged (≥ 0.999 on every item at layer 44). In parallel, W-core runs
   a CPU-only descriptive comparison of the 7 failing items (read position, token ids, special tokens, padding) from
   the E24-D pull and posts it; it does not gate the relaunch.
2. **E32.** It uses the same capture path as E24, so it is held until it captures h44 with W1's capture code as in
   item 1. W-core's two arm-B resolutions in E32's `IMPLEMENTATION.md` (hook convention; candidate-family handling) are
   **accepted** and recorded here as §127 clarifications by reference to commit `1b13c172`.
3. **E28.** W-lens's handling of sentiment free readouts (kept, scored with E24's regex, marked not evaluable for
   naming) is **accepted** as a §122 clarification by reference to W-lens's E28 commit.
4. **E30 (NO_GO on calibration).** Calibration is capped at 300 s of science (one warmed unit per code path, no repeat
   timing); the run cap becomes min(1.5F + 360, 3,600) s. One fresh attempt. Rules unchanged.
5. **E33 (NO_FIT; ≈ 3.5 GPU-h needed).** Full registered scope kept. Cap raised to **≤ 4.5 GPU-h**, split across up to
   two pods by λ, each with its own warmed forecast; the earlier attempt's time is booked to E33.
6. **E27(c) (NO_FIT; ≈ 1.4 GPU-h needed; possible wrongly initialised model head flagged).** W-mechanism first reviews
   the head warning and either shows it is benign (for example an unused LM head) or fixes it, as a reviewed diff. Then
   one attempt, cap **≤ 2.0 GPU-h**.
7. **E35 (gate stopped INCOMPLETE, operational).** One gate rerun after W-sae fixes the cache lookup
   (`allow_patterns` or `hf_hub_download` for exactly the two staged files), with a new request. The 0.05 GPU-h already
   used counts against E35's 6 GPU-h. The integrator accounts for the unreported pod `5wu4ujkbiotxom` in HANDOFF before
   the rerun launches.
8. **Budget.** All of the above fits within §130's allocation; reserve after these rulings ≈ USD 230.
