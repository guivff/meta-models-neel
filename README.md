# Activation readers — Neel handoff (draft)

We evaluated activation readers on Qwen3.6-27B against prompt facts, interventions and the model’s own behaviour. The evidence supports a qualified picture: a state can be decodable inside a reader without establishing faithful reporting; some readouts track beliefs or choices better than text baselines, while an early readout can remain stale as later computation changes. These findings have different scopes and include exploratory comparisons. The table below links each number to its result, registration, computation and reviewer. This is a draft from the recorded pre-seal snapshot; the final handoff must refresh it after the analysis seal.

| Claim | One headline number | Scope |
|---|---:|---|
| State information is decodable inside the Oracle reader | **3/3** bookkeeping rows pass the registered any-layer rule | E113; decodability, not causal use |
| Oracle reports name the model’s belief more often than the forecast baseline | **+37.1 pp** | E107b; conditional on naming a value; descriptive |
| Later readouts better predict non-modal choices than the outside baseline | **+25.5 pp** | E116 note 2; post hoc, exploratory |
| An early readout can state the old fact even when generated text states the new one | **26/43** | E131/§246; strong-steer, text-new subset; exploratory |
| Late read-token representations mediate the fact answer-preference effect | **87.6%** median restoration | E126, block 56; fact-only registered result |

Start here: [presentation deck](docs/DECK.pdf) → [narrative](docs/NARRATIVE.md) → [claim ledger](docs/CLAIM_LEDGER.md). Then use [FINDINGS.md](FINDINGS.md) for the linked results and computations, [EXPERIMENT_INDEX.md](EXPERIMENT_INDEX.md) to look up an E-ID, and [AGENTS.md](AGENTS.md) for the repository map.

This is a **pre-seal snapshot**, pinned to original `r/blindspot@c16db5689937c1895c9cb6d605bc39df19f15411`, plus explicitly traced dependencies. Results remain under review. The original repository remains private and unchanged. [PROVENANCE.md](PROVENANCE.md) records original branch/commit/path and byte hashes; original commit history is available there to authorized readers. This snapshot's commit date cannot establish experiment ordering.

**Suraj Prasad’s code** is vendored, with his consent (30–31 October 2026), at [`external/mats-nla-workspace/`](external/mats-nla-workspace/) from [Jarus77/mats-nla-workspace@10d495f1](https://github.com/Jarus77/mats-nla-workspace/tree/10d495f12fd63c434e8d9752f4a223ea59fa9d95). Files above 5,000,000 bytes and raw tensors are excluded; see [EXCLUDED.md](external/mats-nla-workspace/EXCLUDED.md). Per-file hashes are in [docs/provenance/mats-nla-workspace.md](docs/provenance/mats-nla-workspace.md). Suraj’s own entry points: [README.md](external/mats-nla-workspace/README.md), [notes/decisions.md](external/mats-nla-workspace/notes/decisions.md) (D1–D51), `experiments/NN_*/RESULTS.md` and [figures/](external/mats-nla-workspace/figures/). `common/__init__.py` now finds `mats` in this copy, but Guiv’s experiments ran against earlier Suraj commits: for the executed bytes use the sealed `executed_source/` and `code/external/` copies recorded in PROVENANCE.md, not this vendored tree. The claim ledger, narrative and speaker notes cite the earlier pin `4d43ecb2`, an ancestor of the vendored commit.

Results remain pre-seal and under review (E95 descriptive fallback, R-Q). The deck, narrative, claim ledger and speaker notes are included in this second pre-seal commit.

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

The deck's numbers were read at `r/blindspot c60fa970` ([original commit](https://github.com/guivff/activation-readers/commit/c60fa9703f6dadc8150e11b0c2d5bbe899db02bc)); the repository snapshot is `r/blindspot c16db568` ([original commit](https://github.com/guivff/activation-readers/commit/c16db5689937c1895c9cb6d605bc39df19f15411)). Both are pre-seal.
