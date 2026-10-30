"""F2-6 bank: hard-wrapped wikitext-103 TEST paragraphs (Suraj's recipe, experiments/02_nonj_features/s1_data.py), two read tokens
per passage (high / low col), four read sites. CPU, tokenizer only.

    python -m projects.g_agreement.f2.t6_bank --wikitext <test parquet> --out projects/g_agreement/f2/t6_bank.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import textwrap

SEED = 20261016
N = 60
WIDTHS = (30, 40, 50, 60, 70)
MIN_POS = 8
COUNT_INSTR = "Count the characters on each line as you read, and keep track of how many characters are on the current line.\n\n"


def paragraphs(path: str, seed: int) -> list[str]:
    import pandas as pd

    out = []
    for t in pd.read_parquet(path)["text"].tolist():
        t = t.strip()
        if len(t) < 900 or t.startswith("="):
            continue
        t = t.replace(" @-@ ", "-").replace(" @,@ ", ",").replace(" @.@ ", ".")
        t = re.sub(r" ([.,;:!?)\]'])", r"\1", t)
        t = re.sub(r"([(\[]) ", r"\1", t)
        t = t.replace(" n't", "n't").replace(" 's", "'s").replace('" ', '"', 1)
        if "<unk>" in t:
            continue
        out.append(t)
    random.Random(seed).shuffle(out)
    return out


def main() -> int:
    from transformers import AutoTokenizer

    ap = argparse.ArgumentParser()
    ap.add_argument("--wikitext", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tokenizer", default="Qwen/Qwen3.6-27B")
    a = ap.parse_args()
    tok = AutoTokenizer.from_pretrained(a.tokenizer)
    rng = random.Random(SEED)
    items = []
    for p in paragraphs(a.wikitext, SEED):
        if len(items) >= N:
            break
        W = WIDTHS[len(items) % len(WIDTHS)]
        text = textwrap.fill(p, width=W, break_long_words=False)[:1100]
        enc = tok(text, add_special_tokens=False, return_offsets_mapping=True)
        ids, offs = enc["input_ids"][:320], enc["offset_mapping"][:320]
        cand_hi, cand_lo = [], []
        for j, (s, e) in enumerate(offs):
            if j < MIN_POS or "\n" in text[s:e] or "\n" not in text[:s]:
                continue
            col = e - (text[:e].rfind("\n") + 1)
            if col >= 0.75 * W:
                cand_hi.append((j, col))
            elif 1 <= col <= 0.25 * W:
                cand_lo.append((j, col))
        if not cand_hi or not cand_lo:
            continue
        hi, lo = rng.choice(cand_hi), rng.choice(cand_lo)
        reads = {}
        for lab, (j, col) in (("high", hi), ("low", lo)):
            reads[lab] = {"index": j, "col": col, "token": tok.decode([ids[j]]), "ids": ids[: j + 1]}
        items.append({"id": f"col{len(items):02d}", "width": W, "text_sha1": hashlib.sha1(text.encode()).hexdigest(),
                      "text_head": text[:80], "reads": reads})
    im_end = tok.convert_tokens_to_ids("<|im_end|>")
    instr = tok(COUNT_INSTR, add_special_tokens=False)["input_ids"]
    for it in items:
        for lab, r in it["reads"].items():
            base = r.pop("ids")
            r["sites"] = {"s0_raw": base, "s1_im_end": base + [im_end], "s2_count": instr + base, "s3_count_im_end": instr + base + [im_end]}
    meta = {"seed": SEED, "n": len(items), "widths": WIDTHS, "source": "Salesforce/wikitext wikitext-103-raw-v1 test", "count_instruction": COUNT_INSTR,
            "im_end_id": im_end, "recipe": "mats-nla-workspace-main/experiments/02_nonj_features/s1_data.py build_wrap (width fixed per item)"}
    json.dump({"meta": meta, "items": items}, open(a.out, "w"))
    print(f"{len(items)} items; widths {[it['width'] for it in items[:10]]}...; mean col high {sum(i['reads']['high']['col'] for i in items)/len(items):.1f}, "
          f"low {sum(i['reads']['low']['col'] for i in items)/len(items):.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
