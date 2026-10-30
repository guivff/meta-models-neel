# G1–G4 pilot, 7 Oct — summary for Suraj

Setup: your conventions exactly (Qwen3.6-27B block-42 output = hidden_states[43], last prompt token;
NLA av_base + iter_000400, thinking off; OL olens_s3d_rl600, concepts_raw, layer 42; J-lens n1000 cosine).
Reproduced your K0 (block-42 cosine 0.9999 / rel-L2 0.025 on the 64 shipped activations) and your
single-layer typo_mt numbers (OL 0.71 vs your 0.76 [0.68, 0.84]; NLA 0.71 vs 0.73 [0.64, 0.81], n = 100).

Data: 20 synthetic pairs (language / tense / ownership / mapping), 8 dev + 32 test states, frozen
answer keys, rule-based claim extraction (hand-checked on dev only). Everything is pair-bootstrapped;
n = 16 pairs, so ±20 pp per rate.

What came out:
1. Coverage is entirely family-driven. NLA and OL assert the requested language 8/8 and tense 8/8
   (all correct, κ = 0.88 between them, 1 contradiction in 32); both abstain on ownership 0/8 and
   mapping 1/8. J-lens: 5/32 hits (language/tense only), noise ceiling 0/32.
2. G2: on ownership/mapping neither verbalizer ever names a prompt entity (0/16), binds a relation or
   tracks the A/B swap. The readouts describe the *kind* of prompt ("a name is requested", "a two-step
   symbol puzzle") with invented fillers (Alice, John, A→B→C) — the NLA rewrites the specifics every time.
3. G3 (cached-readout reassignment, not an intervention): recipient-scored accuracy drops from
   17/32 to 4/32 (= the donor/recipient key-coincidence rate), donor-scored equals the genuine rate;
   state-free (mean activation) prior 3–4/32. So what they read, they read from the state — but
   prompt-only recovers 32/32, so none of it is beyond the text.
4. Consensus (2-of-3 or 3-of-3) vs best single reader on the same states: 0 pp difference — the
   covered set is at 100%, there is no room. G4 (8 states): three samples of one reader agree 4/4 on
   the same 4 covered states and abstain on the rest, so cross-method agreement adds nothing at
   matched coverage.

Reading: agreement is high exactly where the property is in the text, and the failure mode is shared
silence on bindings, not contradiction. Next: plant the binding inside the state (A→B swap direction,
prompt fixed) and score the readers' native paired log-odds, your pipeline style; plus a family where
the property is the model's own choice so prompt-only is not at ceiling.

Files: results/g_agreement/writeup.md, figures g1..g4/fig_main.png, blind sheet claims/g1_sheet.jsonl
(136 readouts, if you want to adjudicate), repro/r0.json. Your repo is used read-only.
