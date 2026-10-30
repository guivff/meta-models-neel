# Exclusion and restoration review — tonight's release update

This records the scoped publication decisions for the private `guivff/meta-models-neel` release on 30 October 2026. The source repository was not edited; Suraj Prasad's original numerical citation pin remains `4d43ecb2ef8f2cfab9d8ef673a1c7f56380460fd`; current upstream context and exp 31 use `10d495f12fd63c434e8d9752f4a223ea59fa9d95`. Both are link-only. Scientific code was inspected as text, not executed.

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
