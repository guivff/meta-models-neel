# Cross-scoring inputs for `experiments/17_harden` (mats-nla-workspace)

Files in the shape of `experiments/17_harden/inputs/README.md`:

| file | content |
|---|---|
| `guiv_items_tb_tablecol.json` | 84 items (42 `first` / 42 `late`), the W1 `table_column` **test** split |
| `guiv_items_tb_paren.json` | 84 items (42 `inside` / 42 `outside`), the W1 `prose_paren` **test** split |
| `guiv_phrasings.json` | the two frozen W1 phrasing pairs per reader for both rows (`nla`, `ol`) |
| `guiv_items_*_dev.json` | the 84 dev items of each row, same shape (not used in any of our verdicts; extra in case you want them) |

Each item is `{"id", "text", "value", "cluster"}` with exactly these four keys.

## Conventions, checked by `share/export_w1.py`

- **Read position.** The last token of `text`: no chat template and no special tokens. Every text re-tokenises with the
  pinned Qwen3.6-27B `tokenizer.json`, without special tokens, to exactly the ids we captured: 7,296/7,296 match (see
  `share/EXPORT_RECEIPT.json`).
- **Value names.** Our row values are `first`/`later` and `inside`/`outside`. `later` is renamed to `late` to fit your
  contract. Nothing else changed.
- **Cluster.** `cluster` is the template family (`table_column:t01` … `t11`). It is the unit of our 2,000-sample
  cluster bootstrap. The test split has six families per row, all with ids odd; the dev families are even.
- **Text layout.** Every text has the same three parts:
  - an unrelated preamble (`Unrelated archive note: <word> archive <digits> note note …`), which pads the two values to
    exactly equal token length;
  - the delimiter `\n\n--- Current excerpt ---\n`;
  - the local excerpt.

  The feature lives in the excerpt only. The preamble is needed for length matching, but it means the texts are not
  natural prose. Keep that in mind when you compare against your exp 13 items.

## How our contrasts differ from yours (read before comparing numbers)

- **`tb_tablecol`.** Our `first` means the read cell is in column 1, and our `late` means **column 5 exactly**
  (`w1_templates.py`, `column = 1 if side == 0 else 5`). Your `late` is columns 4–6. This is per E27's design table,
  `results/g_agreement/understand/e27/RESULTS.md`.
- **`tb_paren`.** Each pair is a minimal pair. The `outside` item is the `inside` item with the parenthesis closed by a
  single `)` before the next word. So `outside` means a parenthesis was opened and closed earlier. It never means a text
  with no parenthesis.
- **Pairs.** Pairs share a template family, and their texts have identical token length.

## Phrasings and scoring

These are the exact strings, frozen before capture (`projects/g_agreement/blindspot/items.py` `Feature.pairs`,
`results/.../w1-bank-v2/templates.json`):

- **NLA** (block 42):
  - `p1`: "The current excerpt has {v}."
  - `p2`: "At the read position, there is {v}."
- **Oracle lens** (block 44):
  - `p1`: "- {v}"
  - `p2`: "- At the read position, the excerpt has {v}."
- **Fillers**, which are the same for both readers:
  - `tb_tablecol`: "the first table column" / "a later table column"
  - `tb_paren`: "the read position inside a parenthesis" / "the read position outside any parenthesis"

The paren `p2` strings read awkwardly ("At the read position, there is the read position inside a parenthesis."). That
is the frozen text, and we have not edited it.

How our numbers were scored:
- **Function.** Your `mats.readers.nla.paired_logodds_templates` and the Oracle `paired_logodds_templates`, vendored at
  `2e98a5db` (`external/PINS.md`).
- **Score.** The summed teacher-forced sequence log-prob of the A filler minus the B filler, averaged over `p1` and
  `p2`. The NLA uses your `EXPLANATION_PREFIX`.
- **Metric.** AUROC with value A (`first` / `inside`) positive, on the 84 test items, with a 2,000-sample
  template-cluster bootstrap (seed 20261023).
- **Mismatched arm.** The same score on the opposite-value paired item's activation, which has the identical template
  and length. A reader is NOT EVALUABLE if that AUROC is > 0.60.

## What these items gave on our side (W1, test split, AUROC [95% cluster CI])

| row | probe@42 | probe@44 | NLA@42 | Oracle@44 | J-lens@44 | logit@44 |
|---|---|---|---|---|---|---|
| table_column → `tb_tablecol` | 1.000 | 1.000 | 0.568 [0.349, 0.789] | 0.474 [0.334, 0.615] | 0.632 [0.600, 0.758] | 0.587 [0.532, 0.676] |
| prose_paren → `tb_paren` | 0.982 | 1.000 | 0.744 [0.571, 0.934] | 0.485 [0.276, 0.653] | 0.438 [0.245, 0.605] | 0.376 [0.172, 0.501] (NOT EVALUABLE) |

Your exp 13 pilot point estimates were NLA 1.00 / Oracle 0.67 / J 0.64 (table column) and 0.98 / 0.76 / 0.47 (paren).
Our fresh items did not replicate the NLA numbers. That gap is the reason for the 2×2 cross-scoring. The full row,
with gates and mismatched AUROCs, is in `../experiments/W1_40row/table_40rows.json`.
