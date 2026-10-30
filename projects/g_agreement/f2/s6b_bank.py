"""S6b: the G1 test bank with every candidate made single-token in the Qwen3 tokenizer (BRIEF_S.md "S6b"). CPU.

    python -m projects.g_agreement.f2.s6b_bank
-> projects/g_agreement/f2/s6b_items.json (items.json-like). Language and tense items are copied unchanged. In ownership
and mapping, a candidate with no single-token variant (core/scoring_lo.token_variants, the J-lens rule) is replaced, in
both versions of the pair and everywhere in the prompt, by the first name / nonce word of a fixed list that has one and is
not already in the item.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from projects.g_agreement.core import config as C
from projects.g_agreement.core import scoring_lo as LO

OUT = Path(__file__).with_name("s6b_items.json")
NAMES = ["Anna", "Mark", "Sara", "Maria", "David", "Laura", "Peter", "John", "Paul", "Linda"]
NONCE = ["zap", "mog", "fep", "dax", "vot", "kip"]


def main() -> int:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained("Qwen/Qwen3-4B")
    ok = lambda w: bool(LO.token_variants(tok, w))  # noqa: E731
    items = C.load_items("test")
    by_pair: dict[str, list[dict]] = {}
    for it in items:
        by_pair.setdefault(it["pair_id"], []).append(it)
    out, swaps = [], []
    for pid, its in by_pair.items():
        fam = its[0]["family"]
        its = [copy.deepcopy(x) for x in its]
        if fam in ("ownership", "mapping"):
            cands = its[0]["primary"]["candidates"]
            used = set(re.findall(r"\w+", " ".join(x["prompt_text"] for x in its)))
            pool = NAMES if fam == "ownership" else NONCE
            for c in cands:
                if ok(c):
                    continue
                new = next(w for w in pool if ok(w) and w not in used)
                used.add(new)
                swaps.append({"pair_id": pid, "old": c, "new": new})
                for x in its:
                    x["prompt_text"] = re.sub(rf"\b{re.escape(c)}\b", new, x["prompt_text"])
                    for k in ("candidates",):
                        x["primary"][k] = [new if y == c else y for y in x["primary"][k]]
                    if x["primary"]["answer"] == c:
                        x["primary"]["answer"] = new
                    x["primary"]["answer_aliases"] = [new.lower() if a == c.lower() else a for a in x["primary"].get("answer_aliases", [])]
                    for sk in ("entities", "objects"):
                        if (x.get("secondary") or {}).get(sk):
                            x["secondary"][sk] = [new if y == c else y for y in x["secondary"][sk]]
                    x["target_answer_regex"] = x.get("target_answer_regex", "").replace(c, new)
        for x in its:
            assert all(ok(c) for c in x["primary"]["candidates"]) or fam in ("language", "tense"), (x["item_id"], x["primary"]["candidates"])
            x["notes"] = (x.get("notes") or "") + " | S6b single-token candidates"
            out.append(x)
    OUT.write_text(json.dumps({"items": out, "swaps": swaps, "tokenizer": "Qwen/Qwen3-4B"}, indent=1, ensure_ascii=False))
    print(json.dumps(swaps, indent=1))
    for x in out:
        if x["family"] in ("ownership", "mapping"):
            print(x["item_id"], x["primary"]["candidates"], x["primary"]["answer"], "|", x["prompt_text"][:110])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
