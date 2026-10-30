## §184 E67. Reader fidelity audit: how much of what the readers say is about this input?

**Registered 2026-10-27 15:10 CET. CONFIRMATORY for R-F1 and R-F2; R-F3 DESCRIPTIVE.** **Owners:** W-sae (sampling
and blind packets), W-internals (judge path for the claims rubric), integrator (judging with the key in custody,
once-only analysis). **Cost:** CPU; judging ≤ USD 5 on the E56 route, separately authorised.
**Why.** Verbatim readouts show fluent output that is not about the input: the Oracle lens's near-identical boilerplate
across D4's arms, and the NLA describing D4's copy task while inventing the sentence being copied. A reader that
confabulates is a different and more consequential failure than one that stays silent.
**Data (sealed readouts only; each bank enters only after its own once-only analysis has sealed).** E49 (Oracle lens;
NLA flagged as 128-token truncated), E54 (both readers; NLA truncated), E61 D4 (both readers, 512-token NLA), E56 and
E57 (both readers, 512-token NLA). Per bank × reader, up to 100 test readouts drawn uniformly (seed 20261027), one per
item; D4 balanced across arms.
**Design: matched vs mismatched prompt.** Every sampled readout is judged twice, in separate shuffled packets: against
its **own prompt text** and against the prompt of a **different item from the same row** (seed 20261028). The judge
sees only an opaque ID, a prompt text and a readout, never the bank, row, reader, arm or which pairing it is. The
mismatched pairing measures how often a readout "fits" or "contradicts" an unrelated input of the same kind.
**Rubric (frozen with the packets).** List up to 5 specific claims the readout makes about the input (content, quoted
words, numbers, format, structure); code each SUPPORTED by the prompt text, CONTRADICTED by it, or UNVERIFIABLE; flag
the readout GENERIC if it makes no specific claim. Validation and retries as judging clarifications 1–2.
**Measures, per reader.** F = share of readouts with ≥ 1 CONTRADICTED claim (fabrication rate); G = share GENERIC;
Sup = share with ≥ 1 SUPPORTED claim; each under matched and mismatched pairing, with item-bootstrap CIs.
**Rules.**
- **R-F1 (input-specific content exists):** for each reader, Sup(matched) − Sup(mismatched) ≥ 0.10 with bootstrap
  lower bound > 0. A reader failing R-F1 is reported as producing no detectable input-specific content.
- **R-F2 (fabrication):** for each reader, F(matched) with Wilson CI is reported; the NLA is predicted F ≥ 0.20 and the
  Oracle lens F ≤ 0.10 with G ≥ 0.40. R-F2 is met for a reader if F(matched) ≥ 0.20 with Wilson lower bound ≥ 0.10.
- **R-F3 (descriptive):** F and G by kind of row (E58a category: structure vs content), and against E63's placebo
  readouts where available (judged against a random same-bank prompt, as the mismatched control).
**Caveats carried:** the judge sees the prompt, so it is blind to condition but not to the item; "unverifiable" will be
common, so the headline is contradicted claims; E49/E54 NLA numbers come from truncated readouts and are reported apart.
