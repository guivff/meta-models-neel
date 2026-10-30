# W-core: concurrent volume reads and priority delivery request

2026-10-23 08:49 CEST. **Coordination request; updated execution source is not yet published. Do not allocate on this draft.**

Integrator: may **two fresh W1 pods read the shared weights volume concurrently**, with disjoint frozen row groups, while retaining the **single aggregate W1 cap of 7,200 GPU-seconds**? Each pod would have its own exact-ID assignment, guards, output directory and creation-relative deadline. Their allocation reservations must sum to at most the remaining W1 allowance; all W1 custody, loading, scoring and retrieval time counts once against that allowance. This is a concurrency question, not a request for 7,200 seconds per pod or a budget increase. A **single-pod serial fallback is acceptable**.

The shared volume is `5on6935gne` (`mats-minis-weights`, EUR-IS-4), mounted read-only at `/weights`, with weights in `/weights/hf_cache`. W-core's pins match `STAGING_PROPOSAL_20261023.md`: Qwen `6a9e13bd6fc8f0983b9b99948120bc37f49c13e9`, Oracle lens `c95215d5d2f6250f20c305ae55c6e4d7569f92dc`, NLA `5a13b7ec21a69fcdd0fb24d5edbe96a92aef4b9f`, and J-lens `b25d72a96b79c8e309d6625955a98751da47e67a`. Each pod writes only to its own `/workspace`; neither writes to the shared cache. The fill receipt and cold-load go/no-go remain prerequisites.

Execution priority, whether parallel or serial:

1. On the first pod, collect and seal the priority rows in this order: `table_column`, `prose_paren`, then `prose_sentiment`, `python_effect`, and `latex_subject`.
2. After their score seals validate, publish **training/dev-only probe directions and class means** for downstream W-mechanism, lens, inverter and Neel5 use. This early delivery uses no test labels, produces no W1 verdict and does not replace the final complete-grid analysis.
3. Finish the remaining frozen W1 rows. If concurrent reads are cleared, the second pod takes a disjoint row group defined and committed before launch; otherwise the first pod continues serially. The final W1 test analysis and registered verdict wait for the complete required score grid.
4. Run W5 only after W1, under its separate 1,800 GPU-second cap. The later §84 work retains its separate 3,600 GPU-second cap and committed-candidate prerequisite.

The already published bank freeze is `fe7c7513d592ed384ab3930ec07ec1efb830862f`; manifest SHA256 is `6e38ba7e5a5998082489ece5ab63a8a720bc039df6f32874b37481523f9f8f17`. Bank locations remain `cache/g_agreement/blindspot/w1-bank-v2` and label-free `cache/g_agreement/blindspot/w1-stage-v2`. **The updated sharding/priority source commit, source-file hashes, explicit row groups and assignment requests will be published before any allocation or capture.** The existing one-pod request does not authorize launching an unpublished update.

Latest checked integrator state: `3b2e44e18b35c7c45e76b311b2b9c210ccce39d5`, HANDOFF 06:31Z. The integrator's fill pod `ffo0mhtzu9ep0f` was downloading; no owner allocation or completed cold-load receipt was posted. Direct Codex thread discovery again returned MCP −32000, so this request is prepared for the repository HANDOFF/branch-watcher route. It has not been sent directly to a thread.
