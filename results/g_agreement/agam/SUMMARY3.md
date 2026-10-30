# Agam follow-ups 3 — summary (2026-10-14)

Qwen3.6-27B. Both tasks pre-registered in `projects/g_agreement/BRIEF_Z.md` ("Agam follow-ups 3") before any GPU work.
1.07 GPU-hours. Details: `results/g_agreement/f2/t5/t5.md` and `f2/t6/t6.md`, figure `f2/t6/fig_t6.png`.

**5. Agam's exact stems, with a copy control (32 pilot states).** For language and tense we used his wording ("The
answer, in Spanish, is") with the right candidate, and the same stem naming the wrong one ("…in Italian, is").
- **With the right candidate in the stem,** the Oracle names it 94–98% of the time. But with the wrong candidate it
  names the wrong one 64–95% of the time and the right one at most 5%. The NLA behaves the same (59–70% vs 0%). So the
  readers copy the word that sits just before the read position; these stems test copying, not reading.
- **For ownership and mapping, his generic stem "The answer is" does not help;** it lowers the hit rate at every layer.
- **The read layer is what matters.** With the plain chat template and no stem, the Oracle names the person or the
  mapping answer in free text 86% [67, 98] of the time at layer 56, against 12% at layer 44. It names the right answer
  for both versions of a pair (e.g. "Jonas" for one, "Elif" for the other), so it is reading the state. The J-lens shows
  the same pattern (0% at 36–52, 25–62% at 56–60).
- **Changes to the write-up:** "readers abstain on bindings" holds only at layers 42–44. Read at layer 56, the Oracle
  reports them in free text. The G1 misses were a read-layer problem, not a formatting one.
- **Scoring caveat:** free text was scored with rule-v1, because the OpenRouter credits ran out after 78 judge calls.
  In the first prefill run rule-v1 agreed with the judge on 92% of readouts.

**6. The newline feature (characters since the last newline) at new read sites.** We used 60 hard-wrapped wikitext
passages with Suraj's fixed reader templates. Each passage had a read near the end of a long line and a read near the
start of a line. We tried four read sites: raw text; `<|im_end|>` appended; a counting instruction before the
passage; and both together.
- **No reader tracks the feature at any site.** Oracle, NLA and J-lens put the long-line read above the short-line read
  in 48–65% of passages, with every CI near 50%. A ridge probe on the same states does it 85–97% of the time.
- **With the counting instruction plus `<|im_end|>`,** the Oracle starts mentioning line length in about half its
  readouts (61/120 and 60/120), but equally for long and short lines. It is echoing the instruction, not reporting the
  count.
- **Changes to the write-up:** this extends Suraj's non-workspace result to the read sites Agam suggested. The
  information is linearly present, and no reader reports it there either.
