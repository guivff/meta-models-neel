# Activation readers — Neel handoff (draft)

We evaluated activation readers on Qwen3.6-27B against prompt facts, interventions and the model’s own behaviour. The evidence supports a qualified picture: a state can be decodable inside a reader without establishing faithful reporting; some readouts track beliefs or choices better than text baselines, while an early readout can remain stale as later computation changes. These findings have different scopes and include exploratory comparisons. The table below links each number to its result, registration, computation and reviewer. This is a draft from the recorded pre-seal snapshot; the final handoff must refresh it after the analysis seal.

| Claim | One headline number | Scope |
|---|---:|---|
| State information is decodable inside the Oracle reader | **3/3** bookkeeping rows pass the registered any-layer rule | E113; decodability, not causal use |
| Oracle reports name the model’s belief more often than the forecast baseline | **+37.1 pp** | E107b; conditional on naming a value; descriptive |
| Later readouts better predict non-modal choices than the outside baseline | **+25.5 pp** | E116 note 2; post hoc, exploratory |
| An early readout can state the old fact even when generated text states the new one | **26/43** | E131/§246; strong-steer, text-new subset; exploratory |
| Late read-token representations mediate the fact answer-preference effect | **87.6%** median restoration | E126, block 56; fact-only registered result |

Start here: [FINDINGS.md](FINDINGS.md) → the linked aggregate and reviewer → the linked registration and analysis source. For an experiment such as E100, use [EXPERIMENT_INDEX.md](EXPERIMENT_INDEX.md); the JSON index contains aggregate, source and seal paths. [AGENTS.md](AGENTS.md) gives the map and reading rules. `projects/g_agreement/BRIEF_UNDERSTAND.md` holds the evolving registrations; results are under `results/g_agreement/`.

This is a **pre-seal snapshot**, pinned to original `r/blindspot@c16db5689937c1895c9cb6d605bc39df19f15411`, plus explicitly traced dependencies. Results remain under review. The original repository remains private and unchanged. [PROVENANCE.md](PROVENANCE.md) records original branch/commit/path and byte hashes; original commit history is available there to authorized readers. This snapshot's commit date cannot establish experiment ordering.

**Suraj Prasad’s code** remains upstream: [mats-nla-workspace at 4d43ecb2](https://github.com/Jarus77/mats-nla-workspace/tree/4d43ecb2ef8f2cfab9d8ef673a1c7f56380460fd). `external/` is not vendored in this plan; vendoring requires Guiv to confirm Suraj’s consent. Imports referring to it are preserved as historical source and may not run standalone.

Results under review until 18:00 CET (E95 descriptive fallback, R-Q); the deck, narrative and claim ledger will be added in a second commit after 21:00 CET.

## Known issues

- **F01 — label disclosure:** E109’s `cpu_only/INVENTORY.json` exposed DEV/TEST labels; it is excluded from this snapshot. Judge exposure was not established; future blind confirmation needs a protected new bank.
- **F02 — E104 language rubric:** sampled codes treated English prose as stating the language value, where the rubric calls for “exhibits”; no corrected full-cohort rate is claimed.
- **F05 — split overlap:** disjoint DEV/TEST item IDs reuse underlying questions; they do not establish held-out-task generalization.
- **F06 — E136 scope:** explicit cue words and length recover labels; this supports a prompt-cue result, not a hidden-intention claim.
- **F10 — incomplete reproduction:** private/raw inputs and bindings are absent for several analyses. Source/seal closure preserves provenance, not full numerical reproducibility.
- **F14 — fixed prose arm order:** E37’s correct counts are **RL 4/1,344; SFT/pre-RL 1/1,344**. The narrative reversal is corrected here; checkpoint-identity qualifications remain.
- **F15 — E96 judged sensitivity:** sampled codes credit plural enactment as “states value”; preserve the original verdict and channel distinctions. This does not establish a changed primary verdict or a corrected full-bank rate.

The F11 endpoint exclusion also applies: files containing IP/SSH addresses are omitted whole. The original private repository retains the complete audit trail. The forthcoming narrative and deck must be checked against these issues before inclusion.

The working repository's original README and CLAUDE.md are linked in PROVENANCE.md.
