# E36 scaffold validation — 2026-10-25

**25 CPU tests pass. No actual E36 item bank, label check or model run exists.**

Command from the repository root:

```sh
python -m unittest discover -s results/g_agreement/understand/e36 -p 'test_*.py' -v
```

The tested environment was the project's existing Python virtual environment.
The suite uses only synthetic text/labels, temporary files and mocked model APIs.
It does not open historical item banks, candidate artifacts, scores or weights.

Six builder tests verify authorization before module loading, the complete raw
freeze before checker loading, preservation of failed banks, refusal to overwrite
a freeze, raw-output confinement to cache, label-free GPU inputs and exact final
token position. Eight contract tests exercise the registered thresholds and
denominators, missing H3 eligibility, raw-log-odds aggregation, dev-only pair
validity, plan/source bindings, budget accounting and integrator assignment.
Eleven worker tests exercise the complete mocked acquisition/analysis, separate
value-word channels, missing-score handling, labels/family leakage rejection,
native score shapes/prefixes and capture positions, frozen function namespaces,
source-root and asset binding, and forecast failures before work begins.

The bounded operational audit confirmed that the existing asset verifier hashes
the actual cached files, requires complete inventory coverage, and verifies the
registered tokenizer and adapter digests. Its time is charged inside setup. No
weights were opened during this audit. Model, Oracle and NLA revisions and the
asset inventory manifest are mandatory plan bindings.

Git confirms `e36/cache/` is ignored. No new file outside `e36/` was edited.
The launch request is a hold record with no command or bank/candidate bindings;
synthetic validation is not evidence that a real bank has passed its label check.

## Dated completion, 2026-10-25

The earlier scaffold-only state is superseded by the sealed bank and ready
package. **99 CPU test methods pass**, including the independent checker audit,
both scopes and their rule counts, candidate extraction, path portability,
dataclass import recovery and preservation of the original frozen bank.

The real bank's first full label screen passed 4,200/4,200 items. All 2,100 A/B
length pairs pass. Exact original raw-bank and source-seal hashes were preserved
through the pre-label loader repair. No item was replaced, dropped or reauthored.

Final verification checked every prepared-bank file, every runtime source
binding, all three original candidate-source hashes, every archive member and
the source-ready request digest. The archive excludes the actual item labels,
raw authored bank and per-item label-check ledger. Exact counts and hashes are
in `VERIFICATION_READY_2026-10-25.json`.

No actual model, GPU, measured runtime forecast or reader outcome was used in
this validation. The integrator still supplies and verifies its local model
inventory, forecasts and external-stop assignment before launch. The committed
request is ready for that operational binding.
