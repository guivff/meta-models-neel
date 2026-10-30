# E36 expanded v2 bank — frozen 2026-10-25

**All 25 rows are frozen and automatically checked.** The raw-bank freeze was
2026-10-25 at **14:51:59 CET**, before the Monday 26 October 12:00 CET deadline.
The original eight-row fallback is therefore not selected.

There are 4,200 prefixes: 16 structure rows and nine semantic rows, each with
12 template families × seven fillers × two values. Every row has 84 dev and
84 test items, with 42 A and 42 B in each split. Families 0–5 are dev and 6–11
test. All 4,200 IDs and exact texts are unique. No W1 text was used for a
similarity or deduplication check.

The first full-bank automatic label screen passed **4,200/4,200** items. Token
length matching passed **2,100/2,100** same-family, same-filler A/B pairs, using
`longer/shorter <= 1.10`; the maximum ratio was 1.098039216. Prefixes span 12–551
tokens. The read position is the final token of the raw prefix, with no chat
template, added special tokens or truncation. No model was called.

| Commitment | SHA256 |
|---|---|
| Raw authored bank | `291e1616884e2d2254599e2f87f6cb17449a998e68db29f6a53ae9561e0742a4` |
| Original bank/source seal | `ed064ff2ef4cd9075052d39766f42b8801a3d4e1982f59ef9e428853719d0a6c` |
| Label-free tokenized input | `2d3b14226b76fb51b7afe83190b34fd03a2c9cb3ded6f3f867ac35cb3de10690` |
| Freeze receipt | `e6c1a2349f9dca7faead507bfc521fce8e4e47dd1bba8b317bae4c9f1c38c184` |
| Complete prepared-bank seal | `381fad8114a3dcd4a1142f9b776840d611db6c0ca10fad054a807a81c46e0b37` |

Raw text, tokenized input, private labels and per-item check evidence remain under
`cache/v2_25_2026-10-25/`. Small receipts and seals are copied byte-for-byte into
this directory. The coordinator packet, authorship boundary and independent
synthetic checker audit are recorded separately. The authors received only the
coordinator packet; reader candidates are bound after this freeze.

## Dated operational repair, before any item label was checked

The initial build wrote the full raw bank and source seal, then failed while
importing the content checker: its dataclass required the dynamically loaded
module to be registered in `sys.modules`. No item label had been checked.

The loader was repaired, with synthetic regression tests for dataclass loading
and recovery. Recovery verified the original bank, definition packet and every
author/checker source hash, refused any changed author/checker, and read the
existing raw bank without importing generators or rewriting the original bank
or seal. That bank then passed its first full label screen. **Zero items were
replaced, dropped or reauthored.** `OPERATIONAL_RESUME.json` binds the original
and repaired builder versions. The exact original builder is retained in
`cache/source_before_loader_repair/build_bank.py`, verified against its recorded
SHA256 `1fa5d8f85ebda335bd644f2c2b1ab332f53a6afc90ecf0cc4bc8beab8896263a`.

## Limits of the automatic label check

The checkers use explicit parsers and lexical rules, with conservative rejection
outside supported forms. Python semantic checking assumes ordinary finite
built-in collections and operator-compatible elements; it does not prove behavior
for arbitrary Python objects or arguments. Independent tests cover invented
counterexamples and all 50 A/B orientations. The audit is not a model-based
semantic judgment or a reader-score screen. All real bank checks preceded any
capture, reader score or candidate binding.
