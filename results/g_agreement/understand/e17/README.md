# E17 horizon test — frozen before capture

Prediction: Oracle continuation readability follows the information in the real next
16 tokens even when source-activation decoding stays flat. No E17 activations or
scores exist at item freeze; this document makes no result claim.

Authority: §110, `409690eef4efe65ac222c80b0c446f91ba448ce2` on `r/blindspot`.
The full section is copied verbatim into `REGISTERED_SECTION.md`. Terminal
`git pull --rebase origin r/blindspot` was attempted in a clean isolated worktree
before authoring and failed DNS resolution. The original worktree's unrelated log
edits were preserved. The authority was read through the GitHub connector; the
integrator must reconcile/publish the local E17 commits before capture.

## Items and exact boundary conventions

The committed `freeze/items.jsonl.gz` is the complete frozen bank, including full
authored texts, tokens, capture indices and labels. Its compressed and uncompressed
SHA256 hashes are in `freeze/manifest.json`. It is an audit artifact and MUST NOT be
staged with the worker. The separate staged bank contains only the four allowlisted
files in `INPUT_SEAL.json`; labels stay in the sibling `DO_NOT_STAGE` file.

There are 960 minimal pairs / 1,920 items: four cells each for `prose_paren` and
`python_string`, and two for `list_depth`. Every cell has 32 dev and 64 test pairs.
Twelve W1 grammar families are reused with fresh seeded lexical fills: four entire
families are dev and eight are test, with eight instances per family. No W1 bank
is read or reused. Seed is 20261025. The same lexical instance is paired across a
row's horizon cells; bootstrap resampling must preserve that dependence.

Span length counts tokens strictly between the opener and closer. Each marker is
one token. Early means `read_index - opener_index` is 5–8; late means
`closer_index - read_index` is 3–8. Short spans actually range 20–29 tokens and long
spans 60–78. Every early-long closer is 53–74 tokens away. The inside/outside twin
differs at exactly the two marker token slots: parentheses versus commas, or double
quotes versus the bare word `note`. No length-matching padding is added. Python's
outside-string neutral control is a lexical state control and need not be executable
Python; W1's original asked wording is retained, including its closed-string wording.

Lists have common ancestors indented 2 and 4 spaces, then the previous/current item
and its next sibling at either 2 spaces (top level) or 6 (third level). The shared
root indentation makes the whitespace token counts match exactly; depth is parsed
relative to that root. This gives the source activation the current depth at both
capture positions. Mid-item is 25–31 prose tokens before the line end. Line-end
capture is the last token strictly before the newline; the next line repeats the
same depth. The two continuations from E15 remain 2 versus 4 spaces, an inherited
shallow/deep proxy rather than an exact third-level marker match.

Capture uses only the prefix ending at `read_index`, inclusive. The reconstructor
receives exactly `full_ids[read_index+1:read_index+17]`, not generated text or a
window including the read token. Every window must decode and retokenize identically
with the pinned Qwen tokenizer. Windows are identical between twins in all early-long
and list mid-item pairs, and different in all late and line-end pairs. Short-early
has 26 pairs whose window includes the closer and 70 whose window does not; all are
retained, with no data-dependent selection.

## Channels and controls

- Source44 and E1b AR44 window vectors, each with a separate fixed W1 logistic
  probe trained on pooled dev cells only; no test fitting or sign reversal.
- Native Oracle continuation likelihoods with both already-valid E15 frozen pairs,
  unchanged prompt and `- ` prefix. Both pairs are averaged; there is no new
  E17 validity selection. All individual pair scores are retained.
- Oracle asked likelihoods with the two unchanged W1 phrasing pairs.
- Random donors selected by a value-independent hash within row, cell, split,
  template family and 16-token length bin; self-donors are allowed. Opposite-state
  donors are the exact neutral twins. Since each reader prompt is common within
  a row, donor controls are exact score reindexings and require no duplicate call.

The worker and analysis details are frozen in a subsequent source commit and
launch receipt, after this item-bank commit. All outputs seal before label joins.
Integrator alone publishes and operates the pod. Science cap is
`min(1.5F + 360, 3600)` seconds; setup is 2,400 seconds. No retry, scope reduction,
or replacement items are authorized by this request. W12's Sunday 25 October
evening freeze remains scheduled and takes precedence over any overlapping E17 work.

CPU verification is available as:

```sh
python -m projects.g_agreement.understand.e17_items verify \
  --tokenizer PINNED_QWEN_TOKENIZER \
  --frozen results/g_agreement/understand/e17
python -m pytest -q projects/g_agreement/understand/tests/test_e17_items.py
```

The audit checks every item, not a sample. Corrupted indices, labels, twin text,
windows and split metadata are also exercised in CPU tests.
