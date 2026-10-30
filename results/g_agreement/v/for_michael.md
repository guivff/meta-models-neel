# Note for Michael Kenney — V3 sensitivity proxy on `nla-consistency`

Using your released `nla-consistency` data (claims/, claim_signals.jsonl, nla_samples.jsonl, prior_consistency.jsonl; numbers reproduce your notebook: recurrence AUROC 0.90 input / 0.75 internal, 39 wrong internal claims at ≥ 7/8 = 27 + 12), I tested whether a *sensitivity* signal helps where consensus cannot: the idea being that a claim the NLA repeats in 8/8 but gets wrong is generated from its prior and would recur on other vectors too. Your release has no per-state control readouts (the 20 random vectors are one global set and only sample-1 claims with support counts are released), so the sensitivity score I could build is a proxy: 1 − the share of the 8 × 99 readouts of the *other* items of the same family that contain the claim, with "contain" = idf-weighted recall of the claim's stemmed content words ≥ 0.50 (τ chosen by agreement with your judged sample support, Spearman ρ 0.40, never on labels). Result, leave-one-family-out logistic, item-level bootstrap (1,000): on internal claims recurrence alone 0.752 [0.703, 0.799], sensitivity alone 0.785 [0.732, 0.833], both 0.709 [0.606, 0.793], ΔAUROC(both − recurrence) -0.043 [-0.124, +0.019] against a pre-registered bar of +0.05 with CI excluding 0 → does not pass. On input claims Δ = -0.002 [-0.013, +0.003]. Among the ≥ 7/8 internal claims the proxy alone separates wrong from correct at 0.83 [0.75, 0.89] (your adjacent-token check: 0.67). Two things worth knowing: (i) the pre-registered combination fails for a design reason — pooled leave-one-family-out scores inherit per-family intercepts that differ because poetry has 54 wrong internal claims and typo 1 — and the unfitted sum recurrence/8 + sensitivity (your own recipe) gives 0.846 [0.804, 0.884] on internal claims, Δ +0.094 [+0.062, +0.125], which I report as post-hoc only; (ii) on input claims the proxy runs backwards (AUROC 0.27): true background claims are generic, misquotes are specific, so genericity is a confabulation signal only for claims about internal computation. The honest test needs 8 samples per item on K matched-norm random vectors (or the item's vector with its class-mean component removed) scored by your support judge; if you still have the pod set-up, that is about 500 × K × 8 NLA decodes plus one judge pass. Code and per-claim table: `projects/g_agreement/v3_sensitivity/`, `results/g_agreement/v/v3_claims.csv` in our repo.

---

# Two more things that touch your results (added 2026-10-12)

## Bridge: your Result 2 probe recipe on our arithmetic states

Same base (Qwen/Qwen3.6-27B), same NLA (ceselder/qwen3.6-27b-nla-rl, av_rl_adapters/iter_000400), layer 42, your
plain "a ± b =" render read at "=", 100 new triples disjoint from your 600. Your recipe (18 class-mean + 18
probe-weight dimensions per operand, 5-fold softmax digit probes) gives operand exact-match a 0.24 [0.16, 0.32] and
b 0.48 [0.38, 0.57] on our states vs your 0.83 / 0.93. The sample-size curve (20 → 80 training rows per fold:
a 0.08 → 0.24, b 0.12 → 0.48) rises without a plateau, so we read the gap as n = 100 vs 480 per fold, not as a
pipeline difference; per-digit accuracies are 0.33–0.68 against majority baselines of 0.15–0.18. Two things we could
not reproduce: your NLA free-text exact-match (our free-text sampling on these states did not run) and the model's
own answer (in the plain format the model continues with " ?" in 483/600 of your prompts and 83/100 of ours). The
readers' native score vectors over 0..198 rank the *result* at Spearman 0.44–0.50 but place the operands nowhere
(argmax = a in 0 %, = b in ≤ 6 %). Full table: `results/g_agreement/w/bridge/bridge.md`.

## Positions: where the binding lives at layer 38 (Phase Z4, V6)

Your consistency filter reads one position. On our ownership prompts no single pre-answer position, and no pair of
positions, carries the binding: re-planting the swap at any one index flips the model 0 %, the full post-statement
span flips it 100 %, and the chat-template tokens alone flip it 11 %. Mapping is different: the two differing
symbol tokens together flip 95 %, either one alone < 10 %. An Oracle lens that reads the whole prompt span wins
32/32 pairs vs 28/32 at the last token, while the post-statement span alone wins 23/32 and the same span shuffled
22/32 (`results/g_agreement/v/v6.md`). If you extend the filter to multi-position readouts, the full-span reading is
the one that helped here; the "post-statement only" window did not.
