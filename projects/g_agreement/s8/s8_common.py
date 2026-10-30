"""S8 shared definitions (BRIEF_S.md S8 + amendment 2026-10-16): three-way candidates for X3 ERROR, F2-2 name set."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

SYMBOLS = tuple("ABCDEFGH")
S8B_LAYERS = (42, 48, 52, 56)
S8B_FT_LAYERS = (42, 56)
S8A_ARMS = ("natural", "J_scaled", "perp_scaled", "rand_scaled_0", "rand_scaled_1")


def _mentioned(prompt: str, sym: str) -> bool:
    return re.search(r"(?<![A-Za-z])" + sym + r"(?![A-Za-z])", prompt) is not None


def three_way(item: dict) -> dict:
    """(m) model's answer, (c) task-correct answer, (d) off-trace symbol (not on start..answer trace, not m),
    preferring one mentioned in the prompt; seeded by sha256(item_id)."""
    m, c = item["primary"]["answer"], item["source"]["correct"]
    trace = set(item["source"]["trace"])
    elig = [s for s in SYMBOLS if s not in trace and s not in (m, c)]
    ment = [s for s in elig if _mentioned(item["prompt_text"], s)]
    pool = ment or elig
    seed = int(hashlib.sha256(item["item_id"].encode()).hexdigest(), 16)
    d = pool[seed % len(pool)]
    return {"m": m, "c": c, "d": d, "d_in_prompt": bool(ment), "n_eligible": len(elig)}


def error_items(items_x3_selected: Path) -> list[dict]:
    its = json.loads(Path(items_x3_selected).read_text())["items"]
    return sorted((it for it in its if it["set"] == "error"), key=lambda it: it["item_id"])


def name_set(behaviour_jsonl: Path) -> list[str]:
    names = set()
    for l in open(behaviour_jsonl):
        r = json.loads(l)
        names |= {r["cand_A"], r["cand_B"]}
    return sorted(names)
