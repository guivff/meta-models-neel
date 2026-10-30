# Exclusion and restoration review — tonight's release update

This records the scoped publication decisions for the private `guivff/meta-models-neel` release on 30 October 2026. The source repository was not edited; Suraj Prasad's original numerical citation pin remains `4d43ecb2ef8f2cfab9d8ef673a1c7f56380460fd`; current upstream context and exp 31 use `10d495f12fd63c434e8d9752f4a223ea59fa9d95`. The earlier handoff linked both pins; the later author-approved vendoring is recorded below. Scientific code was inspected as text, not executed.

## Restored source false positives

The earlier `literal-label-map-review` heuristic excluded whole files for assignments named `labels`, `targets`, or similar. The 25 flagged lines in the 23 files below are computed dictionaries/lists, empty collections, synthetic fixtures, or feature-category definitions, not exposed real item-label maps. Each complete file was re-scanned before staging and verified against the exact SHA-256 in GAP_REPORT §6. These exceptions apply only to this rule at these exact file hashes; credential and endpoint findings are not exempted.

The table comprises **22 Python files plus the full R-4 review**, all restored byte-for-byte from `guivff/activation-readers@c16db5689937c1895c9cb6d605bc39df19f15411` at the same relative paths. R-4 was already one of the report's 23 entries, so it is restored once.

| Restored path | Source SHA-256 |
| --- | --- |
| `projects/g_agreement/e100_analysis/test_analysis.py` | `7c88be745656e6521f2429f7b13470f2f29d68e83e1fa78794292b80ef9321ef` |
| `projects/g_agreement/e131_analysis/adapter.py` | `e8792ffde441aafe51a8a9edec8f08867ba9e366a3eae8127fd2d4123b680b17` |
| `projects/g_agreement/e131_followup246/test_adapter.py` | `65b5c711e67e7ff8f28177b064d9f93532fe743a08dadb0f85a29ee2f10841cf` |
| `projects/g_agreement/e133_analysis/probes.py` | `7fc8ac8cbe810f96a803f9b74075debb771e45f3ff05738750c37942fda10ab5` |
| `projects/g_agreement/e134/test_sources.py` | `a2cbe1d9e7dfdb6a92cff344de0fa247a633be1b73ec26f28f4773843f98a7b6` |
| `projects/g_agreement/e137_analysis/probes.py` | `08cfccdcbb0d1e57c9ad2a1e958a4db75c143478439783ad94d453c0b063ae80` |
| `projects/g_agreement/e138/test_runner.py` | `b9a4ccf062f3ede527abe36d9482678945403e89595e18471a6bf5be66ef4188` |
| `projects/g_agreement/e139/freeze.py` | `defc31f082c0604493bb871413cfb641da22d866da21e80e547b69f53d84c408` |
| `projects/g_agreement/e140_analysis/run.py` | `6a7b488be7c272a44f9367e27890df1437c26af68817f8a2ba1e15f9fcd23887` |
| `results/g_agreement/reviews/R-4.md` | `204f65cae7a5d036079cddfcdcfe880ab0f76ed78ac7181e695b23d198170092` |
| `results/g_agreement/understand/e100/vectors/finalize100.py` | `6cf872e9c85769ef72ab54e7becd4b7035b7383c32a1de401b1efe3aac21d6ad` |
| `results/g_agreement/understand/e120/decoder/test_adapter.py` | `e87f2fc600404819243f1a5fab081ec53c0e49b37d16ccc6ba10db5b1e358968` |
| `results/g_agreement/understand/e27/analyze.py` | `a11a2fc2160f009638734be344dd89b5c52d53374cec7bc3b76f885d11cd7929` |
| `results/g_agreement/understand/e37/analyse.py` | `efaeff32c60bc9dd1aad245b05e552174283547df6ccc24eafbecdedce87b2cf` |
| `results/g_agreement/understand/e37/prepare.py` | `8cb0901672e88c28e772021207b06bb1694adfa754ef7e1733e16d4c75ab22c0` |
| `results/g_agreement/understand/e39/contract.py` | `ca7fe5194009a6f4ca7d3775c6db896b885d875b5a650ba399920258b406d2d2` |
| `results/g_agreement/understand/e39/test_training_environment.py` | `9d2d49d36add3775e25cb9b8ef88f0e170b08f2071b4954edfa60ff34caa81ec` |
| `results/g_agreement/understand/e39/worker.py` | `aa094994c68f1cb4bce2c80c5eba082b351b6383706b8d35e8ba7d7727f2187f` |
| `results/g_agreement/understand/e50/contract.py` | `7222007e764843d89b8a22c83a6f507bc2e1433e5c363f53e72d279f5b802fa4` |
| `results/g_agreement/understand/e50/test_training_environment.py` | `15efaac4f851e6852c954e3040c9e58ad65bf163315ddbcf9be1c0563b394591` |
| `results/g_agreement/understand/e50/worker.py` | `7d7e8fb3b76e6f76c554c0363fa68f444c01ebdb55e4036ecc64df6800fafbf6` |
| `results/g_agreement/understand/e56/job/smoke_profile.py` | `7fb898794b799a0c744467057099b434aff343300345fa75f19dea990aa5fb8e` |
| `results/g_agreement/understand/e57/bank57.py` | `cca62a55b7e6654b05873df1e198e7a337d2e4d4908feea6d78ea23e62e84b7e` |

The additional `results/g_agreement/reviews/R-Q.md` is copied from `6264b71737479e55369ce50ab15398969fd57131` (SHA-256 `1519af4e517614b08f05dab8ec85d6db442cc801f72a2d51e7abe94aae623863`). Its later E95 section records dependent H-M1 parts as **NOT EVALUABLE**, not a measured negative map result. The full file passed the scan without a source-rule exception.

## Decision 1 — retain historical answer-bearing banks tonight

The user explicitly chose to retain the ten existing legacy bank files listed below for tonight, with disclosure. Together they contain **3,264 nonempty item-level `primary.answer` fields**. These historical synthetic-bank answers remain available; this release is **not label-free**. They are not evidence that the later E137 private labels or API credentials were exposed. Each retained file is unchanged from release `1ab33ae6`; hash-scoped retention is an explicit exception, not a clean label-scan result. No new answer payload is introduced by the source restoration.

| Historical bank path | Answer-bearing rows | Original release SHA-256 |
| --- | --- | --- |
| `projects/g_agreement/banks/binding_factorial/items_binding_factorial.json` | 256 | `f03f3fd8722260f30b940b58ffae0b9f5c86df5bccdd97595efe0b359d0d8278` |
| `projects/g_agreement/banks/w/items_v7.json` | 32 | `b87f529b26b3f7af9a4902e4ea8728d62ac1eeea6f4981ab733ed8d766ee0bcd` |
| `projects/g_agreement/banks/w/items_v7c.json` | 192 | `0ce441c9d1ce7c109a35feead52429000affd28f104fb3615e445644c51b5ba4` |
| `projects/g_agreement/banks/w/items_w.json` | 828 | `da2c61738f3cd516a52816e0ba3c6bfc49957741b77ae3f1654ea3df9b322cb7` |
| `projects/g_agreement/dataset/items.json` | 40 | `33d74a533d6d0b7c104dc79530d17d4613a3efae51abb69fc44eaa4d2997195b` |
| `projects/g_agreement/dataset/items_x.json` | 288 | `9ce15cedbf6195f0b169a7f838e81bbab77aae84ed88a37d55df42f0c7e1776e` |
| `projects/g_agreement/dataset/items_x3_candidates.json` | 400 | `2e69ed1669a30e8b1b574a3863fda99f2c894287bd9a96319deb7c6da11ff489` |
| `projects/g_agreement/dataset/items_x3_selected.json` | 466 | `fb90c81b185feb48a0398385c21179957ca244dd3be3d422c3c2597033c0accb` |
| `projects/g_agreement/dataset/items_y1_selected.json` | 730 | `2dcbe8b55fca8a642023a97be2b697558c23645244d0e5242a6ff8e39043611c` |
| `projects/g_agreement/f2/s6b_items.json` | 32 | `86a437849f10d82b429b7f6b5ba601a85656e9c2b1f3805694c3620ec41c46b6` |

## Decision 2 — targeted operational cleanup; remaining candidates disclosed

At the user's direction, `results/g_agreement/blindspot/W5_POD_REQUEST.json` is removed from this tip. The pod alias/identifier in `results/g_agreement/s8/s8.md` is sanitized and operational-volume wording is generalized. GPU type, recorded times, duration/cap and all scientific numbers are unchanged. The scientific source path containing `w_pod` is not an operational identifier and is preserved.

The baseline audit found **892 literal pod/host field matches in 470 candidate files**, including synthetic fixtures. Removing the W5 request removes two such matches, leaving **890 matches in 469 candidate files**. These remaining candidates are **known and individually unreviewed**; Guiv states that the pods are expired. This release update does not independently verify provider state. Real operational identifiers may also remain in free-form notes and path names. This is **not a host-metadata-free release**.

The scanner records unchanged remaining candidates as accepted known gaps, separately from reviewed source false positives. New or modified pod/host-field findings outside the explicitly reviewed cleanup remain blocking. Credential-token, private-key, credential-assignment and SSH endpoint findings are not authorized by this decision.

## Five hash-only label receipts retained as provenance

These receipts identify excluded label payloads by filename/hash; they do not contain the underlying label arrays. They remain at their existing paths as an explicit provenance exception to a literal ban on directory names containing `labels`.

| Retained receipt | SHA-256 |
| --- | --- |
| `results/g_agreement/understand/e57/jlens/reader_exports_2026-10-27/E56/labels/INPUT_SEAL.json` | `97142d46b127b5ff6492b8367f4e6f3ecb039cc0917959530dfbd4473e2b85fb` |
| `results/g_agreement/understand/e57/jlens/reader_exports_2026-10-27/E57/labels/INPUT_SEAL.json` | `5c4021bc250a999ee481a144586e6c9ad728fbdf4d6670239c455c47f5dc58c8` |
| `results/g_agreement/understand/e57/jlens/reader_exports_2026-10-27/E59/labels/INPUT_SEAL.json` | `6270dc80c8b150706f115018b7b36a8e49552593bee866551876a8c70f73a3f4` |
| `results/g_agreement/understand/e57/jlens/reader_exports_2026-10-27/E62/labels/INPUT_SEAL.json` | `0ad7971882d5701be1ad75694c5ffbb9af914ea2133a8edb7e093632b7bd46a6` |
| `results/g_agreement/understand/e57/jlens/reader_exports_2026-10-27/E62P/labels/INPUT_SEAL.json` | `aa092610423d810b3ae0fad898f74ece5139a3d844d517d93bc94dc544a33cde` |

## Reproduction and history limits

- Removal at the tip does not purge Git history. No history rewrite or force push is part of this update; earlier commits retain their original bytes.
- This is **not a standalone raw-data rerun bundle**. Private vectors, real label joins, raw API responses and some original bindings are absent. A seal/hash proves identity, not the truth or availability of omitted data.
- E109's exposed `cpu_only/INVENTORY.json` remains excluded. Judge exposure was not established. Historical analyst exposure cannot be undone by excluding a file.
- The restored source makes methods inspectable but does not reset any experiment guard, rerun analysis, refit a model or establish additional independent human replication.
- The registration ledger and extra quantitative claim-ledger rows are deferred tonight and listed as known gaps in README.
- The release scan reports counts only. It distinguishes blocking findings, reviewed source false positives and explicit historical retention exceptions. Zero unresolved blocking findings means the agreed release policy passed; accepted known gaps remain individually unreviewed and it does not mean the tree contains no labels or host metadata.

## Presentation screening

The nine supplied presentation files were checked against the authorized SHA-256 values before and after copying. Both PPTX packages' slide XML, speaker notes, metadata, relationship files and embedded chart-workbook XML were screened. No comments or active Office payloads were found. PDF text and metadata were screened separately for each PDF. The authorized talk bytes have42 pages/slides (26 core +16 backup, appendix starts at slide27); the detailed deck has39. The earlier requested27+16 count was superseded by the verified file count, without changing any supplied presentation bytes. The presentations were copied without editing their bytes. Pattern checks are bounded and do not constitute an OCR audit of every embedded image.

## Targeted-cleanup hash receipt

| Path | Original release SHA-256 | Updated disposition |
| --- | --- | --- |
| `results/g_agreement/blindspot/W5_POD_REQUEST.json` | `c800387a5e0de577b60a4df743f375ff777d8b31d5c67ae706d19618218bc81a` | Removed from new tip; original history retained |
| `results/g_agreement/s8/s8.md` | `0dd99070c79178a01e3285189a50e4f9c3cdd98810db7e51c18375b19a35c935` | Sanitized SHA-256 `6666e6968858e4f3a57788d0624c0dec642291dd37da1325c647462dd8dd13d1`; only lines4/67 changed |

## Suraj workspace vendoring — 30 October 2026

Guiv confirmed Suraj Prasad's permission at 19:41 CET. All 6,088 upstream files are retained byte-for-byte at `10d495f12fd63c434e8d9752f4a223ea59fa9d95`; `.git` is not copied. No upstream file is edited, renamed, reformatted or executed. There is no top-level licence file; included with author's permission. The nested third-party licence remains unchanged.

### Credential screening

Strict raw-byte and ZIP-member screening found zero credential-token values. Twenty-two private-key-header matches were reviewed: one is a header-only bytes literal in public code used as bank text; the others occur in model-generated explanations or derived training targets. Thirteen complete-looking blocks fail private-key parsing; truncated/placeholder outputs and the header marker are not usable keys. Two assignment-pattern matches are a public API base URL without userinfo. Three URL-userinfo candidates contain placeholder passwords on example domains. These exact-file false positives are recorded separately from actual secrets. No live credential was found; no upstream service was contacted to test credentials or resource liveness.

### Retained answer and label data

Item answers and labels in Suraj's banks/results are retained by Guiv's explicit instruction, matching the disclosed policy for Guiv's historical banks. The release is not label-free. The supplemental scan found 3671 files with answer/label field-name candidates; structured payload detection records 19663 payload findings and 1460 identified-row value findings. These counts overlap and are not distinct item counts.

### Operational-reference candidates

The 215 paths below contain Modal API/resource references, recorded run URLs, host/SSH/IP-like text, or generated/public-example text. Static inspection does not establish current liveness. No confirmed live operational value was identified, so none was removed or sanitized. Retention is not a claim that these files are free of operational metadata; no endpoint was contacted. Each original file hash is recorded for follow-up.

| Upstream path under `external/mats-nla-workspace/` | Original SHA-256 | Disposition |
|---|---|---|
| `experiments/00_nla_gate/fp32_check.py` | `12f4dae1f586e1c58d5d98233b5a10d03ad26a54c4878ef4307ab171735443ec` | Retained; liveness unconfirmed; no edit |
| `experiments/00_nla_gate/fve_gate.py` | `05df9db945044d739377b759c3d88ac8e7e94d2999066c4999362f8d07765bb4` | Retained; liveness unconfirmed; no edit |
| `experiments/00_nla_gate/layer_check.py` | `c049ebbfb019712c0280894daeeea66d7bceb6c7d5c69c3f5dd945db824c71ae` | Retained; liveness unconfirmed; no edit |
| `experiments/00_nla_gate/offbyone.py` | `3a81d8381fe704da7f38d059dc5a5280e923350831d4b65132c4f4f351b9656d` | Retained; liveness unconfirmed; no edit |
| `experiments/00_nla_gate/score_gate.py` | `fc844b2b25a00d2e954ad3288ebb39bd41279a94e47cf3434fca603a7b02cd9b` | Retained; liveness unconfirmed; no edit |
| `experiments/00_nla_gate/textnla.py` | `956e480c86f8d8e9224787bb62154b109611bf65149e1dcde4a7b258ea093f6b` | Retained; liveness unconfirmed; no edit |
| `experiments/01_wsbench_replication/produce_modal.py` | `59093d093a9f9fa99685ec5c48fa35e73ea0c3f369085ab56d0af0b822b8e559` | Retained; liveness unconfirmed; no edit |
| `experiments/02_nonj_features/s0_setup.py` | `59bf626ed877cff41326caf4f028b95641c7895cdbadf8807a049fedbc82307b` | Retained; liveness unconfirmed; no edit |
| `experiments/02_nonj_features/s10_followups.py` | `4cee399f4fd34400b6303f1dbab912cd8c45ccb9c171542e2cb1b63bfe75c1a3` | Retained; liveness unconfirmed; no edit |
| `experiments/02_nonj_features/s1_data.py` | `969dd5d66c752945eb5962728e9c89630b38be0db58ff718f5e370e8f559401a` | Retained; liveness unconfirmed; no edit |
| `experiments/02_nonj_features/s1b_data.py` | `54f540f089874f5688c2f7b396032f49862c16aae109f1fdaf76425e1d8779a3` | Retained; liveness unconfirmed; no edit |
| `experiments/02_nonj_features/s2_capture.py` | `89ca08716b25e886c118b10b90424a88558b7278b48967f66652d393749e1f53` | Retained; liveness unconfirmed; no edit |
| `experiments/02_nonj_features/s2c_predpos.py` | `2aacbce3673a756e65e556757df1be4e32f661fedb212d93c781410a7e93d7d1` | Retained; liveness unconfirmed; no edit |
| `experiments/02_nonj_features/s3_probe.py` | `fdd508348de09ea3a70683131ed6a5e9b6b3d63ad2f7d0764a8b2fb7d9b477a3` | Retained; liveness unconfirmed; no edit |
| `experiments/02_nonj_features/s3b_sens.py` | `0076713a2f0e96881cd2c2e3d15a156374b5fdccbbe98d068f5db764d4ee5fcd` | Retained; liveness unconfirmed; no edit |
| `experiments/02_nonj_features/s3c_jonly.py` | `c7679d193f5f9db9d688f665131a49ce8421ca60047a00cd2d3b6a11ca41957e` | Retained; liveness unconfirmed; no edit |
| `experiments/02_nonj_features/s3d_functional.py` | `b10389067f650329bc2de6768662741ec4c9bb44eabba13ec9c0cf65e4e780e1` | Retained; liveness unconfirmed; no edit |
| `experiments/02_nonj_features/s4_causal.py` | `d5c85bd56f7522fb55e9628f1b7846afcf4ce6b33a1cfb4d440069e35581f84a` | Retained; liveness unconfirmed; no edit |
| `experiments/02_nonj_features/s5_selfreport.py` | `53a8fcf9c61965bb06746d5402cfb6442bb03c8520a5a3055ccff1bf005f34cb` | Retained; liveness unconfirmed; no edit |
| `experiments/02_nonj_features/s6_linewrap_replication.py` | `a053fd01cd6fce0b73a5b5c5355130ba7cde29422f731982611d952380c7b525` | Retained; liveness unconfirmed; no edit |
| `experiments/02_nonj_features/s7_lensbag.py` | `542bb77e7cfeca4232c1477569088024fa3c5da473d76d58342554c24200a2cd` | Retained; liveness unconfirmed; no edit |
| `experiments/02_nonj_features/s8_rstar.py` | `4380c2e53ab9f4431a65c75d1c1d9a30a438847f203882df4dd11bb4d97dd5fd` | Retained; liveness unconfirmed; no edit |
| `experiments/02_nonj_features/s9_leak.py` | `e5f3f9a1ae143ef34e5dcdea1af53a05ea12c5c074161413bb3bb8805ff05263` | Retained; liveness unconfirmed; no edit |
| `experiments/03_pipeline_smoke/normrerun_modal.py` | `6f9882a57848f858ff9af148ac965c53991be6d85577b7378f0f7b2886ba6134` | Retained; liveness unconfirmed; no edit |
| `experiments/03_pipeline_smoke/smoke_modal.py` | `4c1c15a9b355618d277ebee77ef766a528934936e8958d06e03ecc125f9c77f8` | Retained; liveness unconfirmed; no edit |
| `experiments/04_backup_features/bf_causal.py` | `e88b029c60389b7e11bfc48da45271daae6e7c001f52110ec149e96fc3ee39c1` | Retained; liveness unconfirmed; no edit |
| `experiments/04_backup_features/bf_colcheck.py` | `f06a64b47b0b6f59943e188eb2c069f6f21a74c99889d1e4072b2eee8192bfb4` | Retained; liveness unconfirmed; no edit |
| `experiments/04_backup_features/bf_modal.py` | `2550dc533c6dbc4f57170cbd3bdefccb5dfb5c3d815a35d5503168902a355fc1` | Retained; liveness unconfirmed; no edit |
| `experiments/05_planted_intermediates/plant_modal.py` | `73dfa44ba559ed33eacb7be83e90a7aa5432769888221924f954d04d95f3b301` | Retained; liveness unconfirmed; no edit |
| `experiments/06_resolving_decomposition/data/floor_gen.json` | `f60626e19d5eefc8eb3113ae41dc14ac38294cc9c9d35d196a788ad56507dfba` | Retained; liveness unconfirmed; no edit |
| `experiments/06_resolving_decomposition/data/floor_run.log` | `69aa5aec789e3916a5d9ac4c978c137c682d64e6bb0b433f3158fb77f3d34991` | Retained; liveness unconfirmed; no edit |
| `experiments/06_resolving_decomposition/data/qwen_gen.json` | `72f049e71282aa218b0428c101331e8b12baf601373dc9763fadbcdd2bc59589` | Retained; liveness unconfirmed; no edit |
| `experiments/06_resolving_decomposition/data/qwen_run.log` | `23f174dc9af192f5e3d69a90b7e226e97672635cec2f7c7dbe3c655451ab1bf9` | Retained; liveness unconfirmed; no edit |
| `experiments/06_resolving_decomposition/data/smoke_run.log` | `6481c26da4a4da61bac8358a84e53792981eafeb483cbfd8bdd83bd9669d1c43` | Retained; liveness unconfirmed; no edit |
| `experiments/06_resolving_decomposition/floor_modal.py` | `2a316b02d1170c462db6aecc340dc9026a620291060b907f30b01735ebd5d5f1` | Retained; liveness unconfirmed; no edit |
| `experiments/06_resolving_decomposition/judge_in/floor_think_off/multihop_mt.jsonl` | `c770355046e5d2e44fbf6c19362d79b81a4ed008a200c77e02de33b056e25770` | Retained; liveness unconfirmed; no edit |
| `experiments/06_resolving_decomposition/judge_in/qwen_resolve_nla_s2/multihop_mt.jsonl` | `e235a10cbe8940d1e974d4eb9725ac25805f665e5d9e335744b7c91ede7e49ea` | Retained; liveness unconfirmed; no edit |
| `experiments/06_resolving_decomposition/qwen_modal.py` | `e2f1e2143ab273205e43e8c20f10bc3ecf3beffef8ed044ad6611652488d673d` | Retained; liveness unconfirmed; no edit |
| `experiments/07_template_mining/results/build.log` | `f3cd6d69d8a60b83da1a4a99efc938614ffde060d9a992734ba243f073829bcd` | Retained; liveness unconfirmed; no edit |
| `experiments/07_template_mining/results/build_extra.log` | `882b48e0d8e44744ca922793ec7a3e4aa10e65613549df15a29cdf0e7210ea20` | Retained; liveness unconfirmed; no edit |
| `experiments/07_template_mining/results/gen_nla.log` | `866d967723b36e7d0fe2d1102d085fffb6dedee18073bfb07cca93f2841a0d51` | Retained; liveness unconfirmed; no edit |
| `experiments/07_template_mining/results/gen_nla2.log` | `63982d02b98100a0d2701f77ec3e5cb0689d1af6627d56aed7d5bc38b024053d` | Retained; liveness unconfirmed; no edit |
| `experiments/07_template_mining/results/gen_ol.log` | `9a06ea6ba1ac06042212b9fdb4312a8551e239b6c88609df9c9fe26a851b0148` | Retained; liveness unconfirmed; no edit |
| `experiments/07_template_mining/results/gen_ol2.log` | `ddfc93b6e4dc4b270f1299c96878dd401d367f55ba5e3994edc50a04a8202cbd` | Retained; liveness unconfirmed; no edit |
| `experiments/07_template_mining/results/score1.log` | `b7028edf1fd55e2c65ae4caadce2803f6fde9f4d0740188fb4685939f3ead352` | Retained; liveness unconfirmed; no edit |
| `experiments/07_template_mining/results/score1b.log` | `d3f0b8cebe490dde4472594903ce4baeb5a1134537de4656cbb11d8f52d85344` | Retained; liveness unconfirmed; no edit |
| `experiments/07_template_mining/results/score2.log` | `0459a37f9cd27cd96dba051956fec5a52a3201b29e980bdeee371361b34c2930` | Retained; liveness unconfirmed; no edit |
| `experiments/07_template_mining/results/textnla.log` | `ae3abad46e23aa5bf4c6c9c16ebb4587726d6d0dc65ccb9c9a9c222a713cc782` | Retained; liveness unconfirmed; no edit |
| `experiments/07_template_mining/textnla_col.py` | `6126d677f70cc8b1b0e18b41e4e89681d18ec0b7023f2933e241cf3d6df31ecf` | Retained; liveness unconfirmed; no edit |
| `experiments/07_template_mining/tm_modal.py` | `2600c9a95c0d87899be5f0db7179926530cad393e0dcf00c54cff4a60e47dcbe` | Retained; liveness unconfirmed; no edit |
| `experiments/08_col_pilot/calib_modal.py` | `523b372ff550bef90b11a37ade5f5e4227bffc636a84e7a3243e2b77ac45ca56` | Retained; liveness unconfirmed; no edit |
| `experiments/08_col_pilot/pilot_modal.py` | `bbea6e2552d2ae9e23a4b8d0553d867b7d4e64771f52bd6009c458a8612a5a3d` | Retained; liveness unconfirmed; no edit |
| `experiments/08_col_pilot/r5_mech_modal.py` | `4beefd1258d09a6d093421ffdb66c90504524edf5eb2c56eb845aac3a6f8c0f7` | Retained; liveness unconfirmed; no edit |
| `experiments/08_col_pilot/r5_modal.py` | `19798088a4c8c556ca06b77e08ec69799b595bd541fc5dc634b9757d6aa2fe1b` | Retained; liveness unconfirmed; no edit |
| `experiments/08_col_pilot/results/calib_run.log` | `6d809d0bacd4629f30b99728099bea61b74433e763749bf8b9e33b728086c62b` | Retained; liveness unconfirmed; no edit |
| `experiments/08_col_pilot/results/r5_behave0.log` | `e1fcd06f1bd6c20705dac5ce144cab8e1cc6fe34651091c190f2574b8a7da54a` | Retained; liveness unconfirmed; no edit |
| `experiments/08_col_pilot/results/r5_behave1.log` | `6714462459c60bbafff6da0194f47a9aa1a0a0e62484720a12ebf75eb3a51dfd` | Retained; liveness unconfirmed; no edit |
| `experiments/08_col_pilot/results/r5_behave2.log` | `5743e719d9acb08cc92a5aadbf1c9ebda9e2677f0abcee7c1c43a67d37fe6ccb` | Retained; liveness unconfirmed; no edit |
| `experiments/08_col_pilot/results/r5_mech_run.log` | `fee4122a222bac719b0308c37f2d91ee19bbf8070626a22452c4894ba786030e` | Retained; liveness unconfirmed; no edit |
| `experiments/08_col_pilot/results/r5_run.log` | `dbd8d2796eede14ff6c7264bf93ef052c618b3b37f2372621fdf15b3d4eac721` | Retained; liveness unconfirmed; no edit |
| `experiments/08_col_pilot/results/r5_run2.log` | `45bc9b85a2102b9ed4f2920b2c378ff3be97432166468ebecfe3fdba03c2a447` | Retained; liveness unconfirmed; no edit |
| `experiments/08_col_pilot/results/run.log` | `3ab4a78a7763bed413cb27a68ade401e5e7d0a8e5a6e2e94ea77adc68dbdb704` | Retained; liveness unconfirmed; no edit |
| `experiments/09_ol_mechanism/o9_modal.py` | `0465228f9080bd5fca6d2e074f3587fc49fad4daa67a096985488a1433159de2` | Retained; liveness unconfirmed; no edit |
| `experiments/09_ol_mechanism/o9_modal_rfm.py` | `363ecdf8acacbd3fa287bc78d0aa7f6c40526f17d9b3d4481c10dd607c1b7b8e` | Retained; liveness unconfirmed; no edit |
| `experiments/09_ol_mechanism/results/09_ol_mechanism/items.json` | `fd32e7924af277582317ebdbf9c4a7a301b81630fb6f9859316bc2ef61c19b8c` | Retained; liveness unconfirmed; no edit |
| `experiments/09_ol_mechanism/results/build.log` | `e676071ec390aadf82778945a96af533308b1f2c0254e6753c5eaeb6203c89b0` | Retained; liveness unconfirmed; no edit |
| `experiments/09_ol_mechanism/results/deploy.log` | `b2ae05c8998d0456e79b205a2ebd6c8fbad0d6aeccd617b9db4a1bf70d58cd89` | Retained; liveness unconfirmed; no edit |
| `experiments/09_ol_mechanism/results/deploy_rfm.log` | `281b27cbdfdb3ad2c1f263af6ec55cf69bd48f8aee76193a5122e6d40c3f4558` | Retained; liveness unconfirmed; no edit |
| `experiments/09_ol_mechanism/results/deploy_rfm2.log` | `c6b43d9ae9f09b44c1f518b24fd2605ff7fb439cce1a8f7c01247ecdb04b8dc8` | Retained; liveness unconfirmed; no edit |
| `experiments/09_ol_mechanism/results/deploy_rfm3.log` | `d9bcc2efcf80a094f7e712ef2aa6859ac00ff5262fea74d3cfca7a573b2921e5` | Retained; liveness unconfirmed; no edit |
| `experiments/09_ol_mechanism/results/deploy_rfm4.log` | `382bd5777eef71140eeb7a640af7e14de945c67fb543c1a6a2ec2c9ad019af9b` | Retained; liveness unconfirmed; no edit |
| `experiments/09_ol_mechanism/results/prep.log` | `fd80012912371bbede3840382e10f9f6d4e11953fa7eb161659d97647ea5aa74` | Retained; liveness unconfirmed; no edit |
| `experiments/09_ol_mechanism/results/prep2.log` | `65aa0b24b66a1c5aafe232838b302c8edbf9df65cfc967f734ee75972a1a3e98` | Retained; liveness unconfirmed; no edit |
| `experiments/09_ol_mechanism/results/prep3.log` | `02edd72ff9057871777530ff3f12b01d1e409baef274de5553f56a45c421d5af` | Retained; liveness unconfirmed; no edit |
| `experiments/09_ol_mechanism/results/prep4.log` | `39a294fb1fe5cab7c6696464eee53b9f353f02e896f171b977704cd05eb83c4b` | Retained; liveness unconfirmed; no edit |
| `experiments/10_operand_gate/jpp_inspect.py` | `57896ef11dea56a314d68a6846fed262b176d27ee5dadb0a264073e9f6a7de3d` | Retained; liveness unconfirmed; no edit |
| `experiments/10_operand_gate/o10_modal_rfm.py` | `e6bde32be2f89c2f5cc4d2830dbea1ddb7314fcd625178cd82b660c44962ed26` | Retained; liveness unconfirmed; no edit |
| `experiments/10_operand_gate/o10g4_modal_rfm.py` | `7febc97620dcb926a158edb1d4963b32cb3af28c9b78defec09f9edd00b8635b` | Retained; liveness unconfirmed; no edit |
| `experiments/10_operand_gate/o10g4b_modal_rfm.py` | `166bdfbad0f97d71065a9908b6a6656d8206f571c0c6538bb93fc193fd69d55d` | Retained; liveness unconfirmed; no edit |
| `experiments/10_operand_gate/o10s2_modal_rfm.py` | `67175c785319d55217bfd1f3f5ab016a0d9a6336bcf705d41047fb96ae841886` | Retained; liveness unconfirmed; no edit |
| `experiments/11_agam_followups/a11_modal_rfm.py` | `0f22d162289dafb8a232d845cfc5f4884c9bb0a76977833a4c98999bf8beca93` | Retained; liveness unconfirmed; no edit |
| `experiments/13_new_rows/modal13.py` | `cc64b14943f1a180f79870dfa3a864497fd5b4cd131f831b1bc6a570cfa652bb` | Retained; liveness unconfirmed; no edit |
| `experiments/13_new_rows/results/gen_nla.log` | `3bb42863b1cd4b0240512bd26749180e781236a440a55996b2a6beb0adfd1c55` | Retained; liveness unconfirmed; no edit |
| `experiments/13_new_rows/results/gen_nla_fmt_listdepth.json` | `1d1557b78ab5f66fc459b1450d904c079ba9f3aee1255f87551128df6cecb2ff` | Retained; liveness unconfirmed; no edit |
| `experiments/13_new_rows/results/gen_ol.log` | `1ddbe5cc1d6791cb5219ff51ab1948d5a21f572873f853566a4f1e0e0eb2a6e7` | Retained; liveness unconfirmed; no edit |
| `experiments/13_new_rows/results/score_nla.log` | `643a8824566b68ab735ccd2096833402eb5e984e181bc0e4775dc71e6405b77f` | Retained; liveness unconfirmed; no edit |
| `experiments/13_new_rows/results/score_ol.log` | `69b49884a778ec914235bc627b3fe2514ea4155b0c67d6ecc18fcdb7f3fc0973` | Retained; liveness unconfirmed; no edit |
| `experiments/14_ar_blindspot/fetch_whiteners.py` | `9e28ebf5fc4f77f9c9013181501e2bd07f3680c193dd4ab41630cc5c52d4d32b` | Retained; liveness unconfirmed; no edit |
| `experiments/14_ar_blindspot/modal14.py` | `339be5ba5d830dc50cd4d0a5fcb88c3c74b012a4b590a883b10c7dfa351de8fc` | Retained; liveness unconfirmed; no edit |
| `experiments/14_ar_blindspot/results/gen14_ol_tb_tablecol.json` | `a93153214fea869fd653f1f037fc5c56ef78b6baefd9f7d5fb7e4926cdeed25e` | Retained; liveness unconfirmed; no edit |
| `experiments/15_ar_steering/env.py` | `0c0b7f1f571696ff87bf7357f216b8b88a43fad2b9d8b079fe19e40ab63809c1` | Retained; liveness unconfirmed; no edit |
| `experiments/15_ar_steering/modal15.py` | `13c438e86a0c690eee5dad05ca856cb65f2f32c317c57315df94ec1dfff7e943` | Retained; liveness unconfirmed; no edit |
| `experiments/16_difference_term/env.py` | `10746ae4c75b4aa33c4ba3115cbe1893453f41e14027c51da981b2991c0a15fb` | Retained; liveness unconfirmed; no edit |
| `experiments/16_difference_term/modal16.py` | `e22e0ec082c3a29d1ec7cc4b990d58ad06b85041c0b3b8d7fcaa0d7ef6727009` | Retained; liveness unconfirmed; no edit |
| `experiments/17_harden/env.py` | `fed3d7be54900a8a0117cb925aa157d4da572149b2beaec9a4e2314baa10bf2c` | Retained; liveness unconfirmed; no edit |
| `experiments/17_harden/modal17.py` | `5a78c86bb523c1ab0fde8805052cebfa5d846209599056372ab9fb7682cd7c00` | Retained; liveness unconfirmed; no edit |
| `experiments/17_harden/results/mc_nla.log` | `b45df7a2e910df140f96c0c6ecb96e5102c2d7532d292f44d4a3a9f1e5fdd9a0` | Retained; liveness unconfirmed; no edit |
| `experiments/17_harden/results/mc_ol.log` | `0e6e949c2d401e4bea4051d217fceeac817bf0b303952759b86ecd0b998f3ee6` | Retained; liveness unconfirmed; no edit |
| `experiments/17_harden/results/vocab.log` | `e831aa65529bdffab11a8f87d20d0cf9793453bbe84d67e3497d05f83184d27d` | Retained; liveness unconfirmed; no edit |
| `experiments/18_prediction_test/modal18.py` | `1ff87d95d29ee0ac25b51721f8385b3e9b709673bf47942ca4584a0f6d122c8d` | Retained; liveness unconfirmed; no edit |
| `experiments/18_prediction_test/results/gen_nla_py_string.json` | `26cf01f05feea184ba7dce1abe271be1f1ec52262cd1cd7aa3cf7feb0b51fdbf` | Retained; liveness unconfirmed; no edit |
| `experiments/18_prediction_test/results/gen_ol_csv_col.json` | `f62499a4cb9fe445b125dcf2ce09b66c071950029264bd3020eeac022bf79116` | Retained; liveness unconfirmed; no edit |
| `experiments/18_prediction_test/results/gen_ol_json_depth.json` | `daceedc9c4fb38a6c8770a8f92e6ee717247c391c277b3117413b72e72e4e08d` | Retained; liveness unconfirmed; no edit |
| `experiments/19_natural_bank/modal19.py` | `ec7f08fda1004778fbcf0670705b1287eb9e51ddb4610599c3587dc2954b4f09` | Retained; liveness unconfirmed; no edit |
| `experiments/20_ar_structure/modal20.py` | `31e0d4b904627ba2081e0adf7dfb4c039faa91b9c8de46a5752316fd8be41257` | Retained; liveness unconfirmed; no edit |
| `experiments/22_public_bank/modal22.py` | `8068e4f1dc232ca624dda1b0e88207d5d1e722a1a0323bf77c4958c775f2461b` | Retained; liveness unconfirmed; no edit |
| `experiments/22_public_bank/results/items_base.json` | `3260ea2697b33d7516190c3c77027d8dd9275e6348c2aadde0c41a2fa4d5aa08` | Retained; liveness unconfirmed; no edit |
| `experiments/23_random_points/modal23.py` | `46e79f28d4172e73c43dff558c532a32a657d7d3219f00cd789e6af52ca51b1a` | Retained; liveness unconfirmed; no edit |
| `experiments/23_random_points/results/items_base.json` | `edfb346fc5603fe9f68ab436139ae824dc70e5ecdba2e87d9627e8485e275be0` | Retained; liveness unconfirmed; no edit |
| `experiments/23_random_points/results/nla23.json` | `1d58a0583391a2f53c412aabc66c57a280942db9ddd4b3ccbbfb93d1083e0ba5` | Retained; liveness unconfirmed; no edit |
| `experiments/23_random_points/results/ol23.json` | `9bf927e2be08b3fe83e3b428270fb02489606191856fec4e00111e13b7453c0b` | Retained; liveness unconfirmed; no edit |
| `experiments/24_second_decoder/modal24.py` | `fd746d0b858e35ed48ca0f07d2cb49e993bce4da8c380b9c5452bb7effe32651` | Retained; liveness unconfirmed; no edit |
| `experiments/25_public_exhibits/modal25.py` | `7627ab37389ad8182a0badcf1733c0c766c94add5df3ebb760ebbc24a69284c3` | Retained; liveness unconfirmed; no edit |
| `experiments/25_public_exhibits/results/nla_sel_js_string.json` | `2772faf7294c3dd8ba572a35b6f191d8497d3ba42a673f32f35240732924060a` | Retained; liveness unconfirmed; no edit |
| `experiments/25_public_exhibits/results/nla_sel_md_list.json` | `92feb605c926176b6953cbf108da7676b3c52294d23af6aab43d128963c6d6a2` | Retained; liveness unconfirmed; no edit |
| `experiments/25_public_exhibits/results/nla_sel_py_string.json` | `b7864fba0bdadc29a6cd74539b608c27f1f19377e44e8fe0b9c4313c88439208` | Retained; liveness unconfirmed; no edit |
| `experiments/25_public_exhibits/results/ol_sel_md_heading.json` | `af1f6a1ed109dcc7a2c42e4d2bdfe31a1fce1145307c84fd1596d5cb525afd2a` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/modal26.py` | `71d110a4d86f84e508208674ca21b993a2579142765e9c9504c9f752bbf9633e` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_code_lang_L24.json` | `e32a9e8b2942fd8237bd37733caf794d99b90292dc246f2d883d2b3d5e75b95b` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_code_lang_L40.json` | `e20977393c3392f67060976bdbc14aa154aadb0106c2b34df072b9fe1c33b322` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_code_lang_L48.json` | `7ff357f79bf5072a353c53310926be7f84ac6a6b747cd324a3cc7bc2e4a1b7a5` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_code_lang_L52.json` | `408a2412047f91d57762c253dde5bb413669f98f0332cde70ffbb2992c55ae41` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_code_lang_L60.json` | `19ec5e66fcfdb60b0c86ca7a9001255e1c6dae655d918aa8701b2266ab1bde66` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_js_string_L32.json` | `8a7ec63d6d02eb4f600b7ebfc1d2347eafc31c8c79fd7b1cbf5485e1e3e88211` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_js_string_L48.json` | `5f2f327a170d339e10f373a26ae99167295f39008625309cf4edc1b680df9cd3` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_js_string_L52.json` | `0ebcd9172b659b6462e36fe2d53d367b1ef895d13d64a40bdfb41ef5cfcb2e99` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_js_string_L56.json` | `497765d18c4e78cb28a53b0f06d6117c527d87ee90b4b3239d09fcaaee060e4c` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_js_string_L60.json` | `f88f5f411567222437df4d9ad82796af964786144bf1759669002b9efe3f5a7e` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_json_depth_L20.json` | `cd5d9824ba47b820a241c6c34c83b2a9d0cac5a63e9e5d0da72cb41288967fca` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_json_depth_L24.json` | `df20366c38b07bf1e0b0080e6ffa6d3c4e5600626d4a4e6e813ea24f1c2980c8` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_json_depth_L36.json` | `e1f9726c388fc34ee878ba1a9cedc7e3477439876168545fa2d84cc6501aed8f` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_json_depth_L48.json` | `a88b88a50083bb8d4749ced81e1ff30f20649c46138914eb7e34932413059cbe` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_json_depth_L52.json` | `8d686419eed8900ce65f7176e55646300740a82e3815ad4b789cd00fdd3f8e5b` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_json_depth_L56.json` | `fa5283e910d4c5bb7ab7b3c3a2571d9e28cd869393021bfcd60d157a656f5e40` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_latex_math_L60.json` | `19c82dae15aced4eda455784fbac0be1fc344301e5cda14af0e214e3144cd4d7` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_md_heading_L42.json` | `cfaf56b35a148c8621b562da6737376d497307b3bc83497e5a6bafacdf0ca6df` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_md_heading_L44.json` | `ddc30b52b0f7ce3fd0e87c7f8220144069685c57d9c0e5e54cb8f11a93307bb4` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_md_list_L36.json` | `bd5ce8a50d0f27c59f04502ce16e46486e3cbee981e7d171582312430897a61e` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_md_list_L48.json` | `ef18d0ee688a5717aa10288e00996d2fa1e648a4b51f34b6cf1548c71047107d` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_py_arg_L24.json` | `84433b6b99f9adff588ff9fc774a53918a1af7c80368796e4c98e69c41aeba16` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_py_string_L48.json` | `5cc53af56eb14e7a24d3c8647635ade66a6c51ba98a9cc1f92bce163e3c12fd4` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/ol26_py_string_L52.json` | `ff503875cd04a85f52a0e9b799dd04279decd9da708a3c861fb7f18f50cbde1a` | Retained; liveness unconfirmed; no edit |
| `experiments/26_layer_sweep/results/sweep26_code_lang.json` | `869c4ac20033d13c760691629d18a25a4a866e1d5deb9b8c7a041ebecbc7967e` | Retained; liveness unconfirmed; no edit |
| `experiments/27_random_2000/modal27.py` | `0e57b43489b54a26452923fa2b0c1ff5fc15d22f5a3c3064830cbd7582129a38` | Retained; liveness unconfirmed; no edit |
| `experiments/27_random_2000/results/items_base.json` | `e95bddd36db82014f7decc6b12e90f65163345e58e396e870be69c65dd7d8156` | Retained; liveness unconfirmed; no edit |
| `experiments/27_random_2000/results/judged27.jsonl` | `b6bcc6d7e66574acb7b5cb512890b6887d06dba7f279322c79ab672f70478788` | Retained; liveness unconfirmed; no edit |
| `experiments/27_random_2000/results/nla27.json` | `9c6330b8cadc6840038103749bd700ffeb32fdfab5ded8651c1735ef3c17c0d0` | Retained; liveness unconfirmed; no edit |
| `experiments/27_random_2000/results/ol27.json` | `0be479f29fe4c66502edd69623d7a67deab4767edccee2e4d07cc2dfe5e1160e` | Retained; liveness unconfirmed; no edit |
| `experiments/28_stmt_curve/modal28.py` | `5f0a52afa76c7872a6483deef627c3568b7d6a64000f0ebd356a58b6294b7f01` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/modal29.py` | `2d25abc7251d9040fe50f7337107df114038a69c29bdaeb9af64eb6a89d6690c` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_av_base_code_lang.json` | `e59dd95ec08183e61fd330c849a5463962886fb19eca6241864f2a335ac7a8a3` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_av_base_js_string.json` | `5d5d6a19329bcf993b29c277b1d99c71af0e090fc4c6bb99e87a6de815835b57` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_av_base_json_depth.json` | `bbb9cec4c66f014fba6e7ca6e1494a409ebca566345a4edac874be7dcf1ffac2` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_av_base_py_arg.json` | `753bc6ef1b27c1dcd2e7bbc5fecd7f9b7afa5ccf4e58a7f6db5fd7eb3e127485` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_av_base_py_string.json` | `9dee770d83249f532034017352e89d8a73c27c1e87ff6959b44fe7693bd01980` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000100_code_lang.json` | `6fa0017fd3a5fb9e0847c98ea76da934d6f3e8ce783cecfe002be0ba8e5e24e1` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000100_js_string.json` | `679a616d6ebd0d28184b5ed690e8cb2ca8355dad789ed23b9bf9ad84c3d75e4f` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000100_json_depth.json` | `1199c7bab997350e0b580252346367e624246265b304ec4ba264c2e11c689ab5` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000100_md_list.json` | `7ad781f33bd9ce2710ea015fd3996d98378ace2a8735333fda06716e305ee930` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000100_py_arg.json` | `7d605d8a2ad6d79710555bc1c3404ee60887ef14ebc43d875e4f07524c25052a` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000200_code_lang.json` | `17f5aebbe7e650f0203b3a1dec07900efaa0ce98ec08a6473520fee2748ac5ab` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000200_js_string.json` | `f69cf26e244e0e3e963a1ce8ed107b74773a5d4bf275c6cd874ae615c8f57319` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000200_latex_math.json` | `732c0c14c351258f08d4c678071d0fdf10b5dea9df7ff1e912ca08d2aa80f0fb` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000200_md_list.json` | `3909379f09af10fb46657f7772fd9d93a1422204e529408c436fcec96572b883` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000200_py_arg.json` | `2c246876c1399d24afff3725223089ded625060d6f59069b629fa10f9ee83f10` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000200_py_string.json` | `d40ffecab3817b5db5abc81d749c4ac50fc71b0b53ee30a31643549446fabbc4` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000300_code_lang.json` | `96c9d59bd77ec276bf487afaa2d072f1f3110fdecc0775217ebeff40155453c8` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000300_js_string.json` | `6d31c98cc269277e90b1f590ac1ac3ecf79194aa4c75d3b5c9a47dfa516184b7` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000300_json_depth.json` | `925785fa46b7ec84e700ba227ab11842ce6b182f5463e9135d4962612c20c1b9` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000300_latex_math.json` | `7f54766f2c92ee19b97d3e2c6407a31caa9f485c9e0b394f7d0d6edb5838be5f` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000300_md_heading.json` | `a4b8d85fd50bfab1711d0646c02b8bd196672010f869b4c7cbfff5fb4123406d` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000300_py_arg.json` | `c691fd5e7dc89f2508d42c70ea9693eef75c46c27f683edc6e4eb96656a731c1` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000400_code_lang.json` | `8e64ea5ce028fc73846413148afeb27f57b2add04cc6ad545f829e79265d6033` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000400_js_string.json` | `190829e3cb7ddfa1da3fa249014f494963963606b2b280433451f131ff3e57ce` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000400_json_depth.json` | `5c45699eb74f5be520ad422c0538f644c8434b05e8e822c7044600fd2e6aeb09` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000400_md_list.json` | `0b55d34134837496fa72cc210f023c6419d7d5c24863ed36c81f845fcc6b022a` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000400_py_arg.json` | `bacd3013923d5d180d7698d02cdd9d9bc79870f880e877f85fcdcb4cb2f7e489` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000500_code_lang.json` | `7ead532bab74126e710fa6cbb9a48b2fa159bc7f125213ca6925b7f96114d317` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000500_js_string.json` | `87f50b328ef403d57c7ecab67f0f02c94f3990354b34356e2707d63a810fbaa6` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000500_json_depth.json` | `6d8531bfee0990f13cf192b0e53f1cdd168d821a95241ea9f94ea58eb07c6a54` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000500_md_list.json` | `b281e8862c164758b866df4ecbad88280f3ef3943a8fe3e7f334b3cab16aac4e` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000500_py_arg.json` | `2379df2fedd44ce4a063c244e1ce36311cc83e09140f7ef96f2a35c5246da994` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000500_py_string.json` | `eb35ce8cf505a107bb1600765c1d0ca1442517f46e4f83064f89c18037c191f7` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000600_code_lang.json` | `1c9f8bf7372a82c8581be140b955728b6a9fc5ed41aa443cebdddb42a4fd76b9` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000600_js_string.json` | `43465a7b15aa1c927fb9323777a3e015fdb61f26683a7e1d250fad8c7e62d195` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000600_json_depth.json` | `23025cd96938114cf68ed74955f1ce40cdb60e525710896eb43361337dfd8c28` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000600_md_heading.json` | `487a4646a518bbff418929269993b976998bfe4116db1831e5d5f691f607f935` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000600_py_arg.json` | `36388b15f30f3a248eacf0cd278e5f8415bedcfef7f8a9370e30aec985702a88` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000700_code_lang.json` | `b8e4515833261623b0411e9a5a325cc15901753566faa72f86fabf5cb2e239cb` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000700_js_string.json` | `c028eb35682d0f9358a7dc9499701419a94b15a595327c251e185bdb5d184685` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000700_py_arg.json` | `daa96202a45d08ded923a12d12fa4cd694c9d4983f4ef378e0f61be670311676` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000700_py_string.json` | `762f68e5453675515e5868c6bcebb59e3ee354a1ed1ed40921cd04d448936328` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000800_code_lang.json` | `ec09034d17c2c4e4a554fa3c5e9a874787566f26866bb509aa938dd38e2b1fb6` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000800_js_string.json` | `fcb1441a2b8f3b2796a4ea9fcc9429307731ea408b0bc32f6c56c0c438cd74c4` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000800_json_depth.json` | `bdbe0d9a3c3ba3c58b9659e8497f62d3c1c5e4594962090cc17e05e9048b54a7` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000800_md_heading.json` | `dc89eb1f32f36f0cc585f672f3a914935bff7fbca7c2e6437f65aad59db83604` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000800_md_list.json` | `245be1dc308f620ef7bc1722b6e494465af01ebc27fd6252935c08025a1dd17a` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000800_py_arg.json` | `242dbae169ac0537eaf78e3aadd5af238746504626ba0f34ad62d06e4b0620fa` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_iter_000800_py_string.json` | `38ed7b37afe2018c660ee7fcd96d41f352a390de50f0dded5ed3e3423c1a5749` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_textnla_js_string.json` | `a25e8af045341c07b39b2a356bfd491dee1bc4479aaba8ef0acb5f45191a07ff` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_textnla_md_heading.json` | `5a85d4de8c2cdcec47fd8f85cc846d7a8c9acf2aa9bca19e5ba7fd45464e10c2` | Retained; liveness unconfirmed; no edit |
| `experiments/29_trajectory/results/gen29_textnla_py_string.json` | `10648e91a81759520a4ae116dd2c931184265dc52a9a77b9eca8739bc28672e7` | Retained; liveness unconfirmed; no edit |
| `experiments/30_naming_lora/modal30.py` | `8c39f6c2c3cb760ed2b918acc9cac032267470cbfd8036075eec6a39d2717093` | Retained; liveness unconfirmed; no edit |
| `experiments/30_naming_lora/results/data30.json` | `8c78ab62428f22d9b339b0563ed1824d5819bde248e837d31a5caf64bc53a68d` | Retained; liveness unconfirmed; no edit |
| `experiments/30_naming_lora/results/eval30_C.json` | `402ac855a7adf6daeb1cf3ee3a0c2e5acfcb2f754acea282b48d77a3e6aa260e` | Retained; liveness unconfirmed; no edit |
| `experiments/30_naming_lora/results/eval30_S.json` | `193954802e229bccc25eaec4117f26d92455638cfef8d4c3e3b02ca1498a1ab5` | Retained; liveness unconfirmed; no edit |
| `experiments/30_naming_lora/results/eval30_base.json` | `ea11916e963615ba390af0671b7d7a63c0b90ff1ce192707a53f5767b39540ba` | Retained; liveness unconfirmed; no edit |
| `experiments/handoff_inputs/14_ar_blindspot/gen14_ol_tb_tablecol.json` | `a93153214fea869fd653f1f037fc5c56ef78b6baefd9f7d5fb7e4926cdeed25e` | Retained; liveness unconfirmed; no edit |
| `infra/download_weights.py` | `4214bb861695226453b5fb37d5497cd28ffd2d61b789f20feb2a05abba6baa58` | Retained; liveness unconfirmed; no edit |
| `infra/modal_common.py` | `f7342e3c46982f19e08f700d43f7f5d900839e2efe540efbb04ddf15aff6ecba` | Retained; liveness unconfirmed; no edit |
| `infra/smoke_test.py` | `ba83bab39835b37677c8cbaedd9c5e2732970418ff1726b5c5a57f683368162a` | Retained; liveness unconfirmed; no edit |
| `phase1_recovered/code/jverify.py` | `7498b9f5f94d8dc30e006caf8485d2368d762d507448eab00620b9cdaee5a204` | Retained; liveness unconfirmed; no edit |
| `phase1_recovered/code/workshop_runs.py` | `63bc4437ca71b461f5d90442507b7f58fdcfb8b904e1a48f603d22bd55fbd702` | Retained; liveness unconfirmed; no edit |
| `third_party/workspace-bench/evals/hallucination/items.json` | `cf84fee47c5c91fdb07f94f85f10de9c9b7b1352968444483bbc6a89eb1a8606` | Retained; liveness unconfirmed; no edit |
| `third_party/workspace-bench/uv.lock` | `70a0c74e48d71e92d0e132670842d2822f1ba9e1caf09335424da9d133ae9701` | Retained; liveness unconfirmed; no edit |

### Size and binary screening

Upstream tree: 349,669,789 bytes (349.67 decimal MB), 6,088 files. No file exceeds 50,000,000 bytes; none is omitted. Files above 10,000,000 bytes:

| Upstream path | Bytes |
|---|---:|
| `experiments/handoff_inputs/03_pipeline_smoke/jspace_basis_L42.pt` | 41961453 |
| `experiments/handoff_inputs/07_template_mining/acts_bk_listidx.pt` | 12293737 |
| `experiments/handoff_inputs/07_template_mining/acts_ij2_lang.pt` | 12294167 |
| `experiments/handoff_inputs/13_new_rows/acts_tb_paren.pt` | 12294679 |
| `experiments/handoff_inputs/13_new_rows/acts_tb_tablecol.pt` | 12293490 |

Binary tensor/array/image files were searched as bytes; ZIP members, including tensor serialization containers and Office XML, were inspected without loading pickles, tensors or upstream modules. This is a bounded pattern scan, not arbitrary binary semantic validation or image OCR. Source whitespace is preserved unchanged.
30 Oct 21:18: restored 227 files (152 .py, 69 .png, 3 .docx reports, 3 .md) previously dropped by the label heuristic; list and hashes in docs/provenance/RESTORE_LIST.tsv
