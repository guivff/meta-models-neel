# WR-2 alias audit and minimum additional-state plan

**Final report — 2026-10-19 23:59 Europe/Zurich.** `NO_SUFFICIENT_CACHED_PARTITION`: after all 118 candidate identities are adjudicated, the same registered rule has a solver-certified maximum **242 held-out test  / 525 pool captures**. Every other numerical gate passes, and finite-corpus alias adjudication is complete. The smallest validated collection **under §20's registered augmentation rule is 14 new test states and 0 new pool states**. An explicit metadata-only 14-context plan yields 256 test / 525 pool with unchanged name, alias, template and capture holdouts. **No new states were collected and no training was run.**

Branch `r/i2-wr2`. Preregistration `ee07607`; alias table/implementation committed and pushed as `571bda5` before coverage. The integrator's result commit is recorded in `../HANDOFF.md`.

## What the alias audit changed

The saved 244 / 526 witness was invalid after adjudication. `Nightbloom` and `Night Blooms` are conservatively one holdout identity, so their two-row block no longer has distinct targets. Pool item `re-re_khop2_answer-pool-0106` contains `zloty`, now linked to held-out `złoty`. Removing those two test captures and one pool capture leaves 242 / 525; a fresh global optimization independently certifies those maximum counts.

The table covers 79 PersonaQA favorites, 16 currencies, 19 cities and four countries, including all 23 alternatives outside the old 95-identity witness. It preserves all prior exclusions, adds 13 pool conflict edges after remapping, and leaves templates unchanged. Relevant additions include honey cake/cakes/honeycakes, ice berry/berries, qualified currency names/codes, and conservative night-run/running, windrace/wind-racing and nightbloom/night-blooms links. Country/capital/currency relationships remain distinct. Homographic `PEN`/pen and `US`/us are conservative holdout links, not asserted answer equivalences. Resulting components are holdout units; they do not define a trained decoder's accepted-answer list.

Finite-corpus completion means review of the frozen indexed inputs and local source metadata. It does not establish worldwide synonym completeness or invented fantasy-world ontology. Related labels sharing a theme remain distinct unless evidence supports a spelling/morphological or conservative possible-alias link. Unobserved prospective spelling exclusions are explicitly marked in the table.

## Unchanged gates

| Gate | Required | Actual cached | With proposed 14 test captures |
|---|---:|---:|---:|
| Distinct held-out test captures |256|242 — fail|256|
| Suitable distinct pool captures |512|525|525|
| Held-out identity components |32|91|91|
| First-token families |8|31|31|
| Independent challenge groups |8|10|10|
| Test source families |2|2|2|

All 35 retained blocks contain at least two distinct holdout identities and suffix token sequences. Complete-capture name/alias exclusions, template holdouts, original pool/test roles and capture uniqueness pass. The future 256 count is **prospective metadata**, not available states. Coverage guards do not guarantee statistical power.

## Smallest validated collection

Collect exactly **14 additional Qwen3.6-27B L42/chat/last test states** for the proposed captures in `wr2_alias_audit_proposed_captures.json`; no pool collection is needed. The manifest supplies full prompts/system cards, exact labels/answers/candidates, frozen target tokens, source evidence, aliases, template/block/parent IDs and capture hashes. Its SHA256 is `b750cd029a25fc18aa34017fec10758b5bf911f05b75c03d59438333e6ef87b9`. Each proposed state currently has `state_available=false`.

The concrete construction adds two contexts to each of seven already retained PersonaQA shared-prefix blocks. Only the person-name slot changes, using 14 distinct names from the corresponding frozen raw source vocabulary; favorite facts/targets, query templates and labels stay fixed. These are synthetic recombinations of the existing generator, not additional original dataset records. Original prototype parents/components remain linked, so the 14 contexts earn **zero new independent groups**. They are novel against all 11,224 frozen cached captures and retain both-suffix support.

| Existing block target pair | Additional captures |
|---|---:|
|Trivial Pursuit / Truco|2|
|Borscht / Biryani|2|
|Kwaito / K-Pop|2|
|Stone Quest / Stone Wars|2|
|Tower Wars / Tower Defense|2|
|Mind Maze / Mind Forge|2|
|Shadow Quest / Shadow Realm|2|

The minimum calculation explicitly allowed new pool captures to replace conflicted cached ones. For each k=0…14, maximize cached tests with cached pool>=512−k while retaining every other registered constraint; the FINAL gate remains 512. Every frontier optimum is 242 tests. Thus an allocation with exactly k new pool captures needs at least 14+k total new captures; any k>14 already costs more than 14. All primary/secondary/tie solves report zero gap. The explicit 14-test plan attains the lower bound within this scope.

**Scope of “smallest”:** this is the minimum for the frozen, audited usable candidate universe, with cached tests already satisfying the identity/prefix/group/source/both-suffix gates and new test contexts extending existing usable blocks. It is not a global minimum over newly designed targets, templates or counterparts that could rehabilitate currently unusable cached blocks. Those would require a separately registered design and alias audit. The proposed plan clears the registered metadata gates once its states exist; future collection still needs successful provenance/index/activation checks.

## Verification and reproducibility

Independent audits reconstructed the alias graph, all 1,200 eligible pool rows' full-metadata conflicts, the prefilter independence closure, every saved frontier constraint matrix and selected witness, and the 14 proposed captures. A second combined audit rebuilt full-universe closure and re-scanned every selected pool capture against the final held-out phrases. All passed; no overlap, duplicate capture or extra independence credit was found. Solver optima are HiGHS primal/dual certificates with independently checked matrices/witnesses, not formally verified integer-program proofs.

Measured metadata review CPU 16.838935s; build/frontier/construction/audits 13.149269s. All computation used CPU; zero state-payload reads, new fits, model forwards, downloads, acquired states or GPU hours. Main checkout HEAD/branch and cache link remain unchanged.

The population remains mostly currency/favorite descriptions, not a pure unseen-proper-name benchmark. h≈Jh remains expected from J42's full rank, and the random-subspace caveat still applies; eventual informative decoder contrasts are native-token and state-free controls. Stage 2 has not been preregistered in full or trained.

Committed artifacts: `wr2_alias_audit_table.{json,csv}`, `wr2_alias_audit_ids.csv`, `wr2_alias_audit_coverage.csv`, `wr2_alias_audit_frontier.csv`, `wr2_alias_audit_collection_plan.csv`, full proposed captures, result/frontier/build summaries and independent verification JSONs. Large inputs, matrices and full review evidence are in ignored `cache/g_agreement/r/i2/wr2_alias_audit/`. Scripts are under `projects/g_agreement/r_bench/wr2_alias_*`; the build is the existing `wr2_partition_build.py --alias-audit …`. Use fresh output directories for reproduction; do not overwrite frozen results.
