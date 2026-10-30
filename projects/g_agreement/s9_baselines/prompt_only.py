"""S9 (a): prompt-only baseline on the 297 X3 ERROR items (BRIEF_S.md "S9").

google/gemini-3.8-flash (the answer judge paired with rule-v1), temperature 0, reasoning effort minimal, one user turn =
the item's prompt_text, max_tokens 2000 (deviation 1; 64 as pre-registered via S9_MAX_TOKENS=64). Parsed with X3's parse_symbol; class m / c / other. Stops on HTTP 402.

    zsh -ic '.venv/bin/python -m projects.g_agreement.s9_baselines.prompt_only'
"""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

from projects.g_agreement.x3_floor.collect import parse_symbol
from projects.g_agreement.w_claims.judge import JUDGE_MODEL, OPENROUTER_URL, Usage

REPO = Path(__file__).resolve().parents[3]
CACHE_ROOT = Path(os.environ.get("G_CACHE", REPO / "cache"))
SELECTED = REPO / "projects/g_agreement/dataset/items_x3_selected.json"
TARGET = CACHE_ROOT / "g_agreement/x/x3_target.jsonl"
OUT_DIR = CACHE_ROOT / "g_agreement/s9"
MAX_TOKENS = int(os.environ.get("S9_MAX_TOKENS", 2000))  # 64 = first run (pre-registered; 70/297 empty)
OUT = OUT_DIR / ("prompt_only.jsonl" if MAX_TOKENS == 2000 else f"prompt_only_max{MAX_TOKENS}.jsonl")


class PaymentRequired(RuntimeError):
    pass


def load_error_items():
    items = [x for x in json.loads(SELECTED.read_text())["items"] if x["set"] == "error"]
    tgt = {r["item_id"]: r for r in map(json.loads, TARGET.read_text().splitlines()) if r.get("family") == "puzzle"}
    rows = []
    for it in items:
        t = tgt[it["item_id"]]
        assert t["is_error"] and t["parsed"] != t["correct"]
        rows.append({"item_id": it["item_id"], "prompt_text": it["prompt_text"], "m": t["parsed"], "c": t["correct"]})
    return rows


def ask(prompt: str, usage: Usage, retries: int = 4) -> tuple[str, str]:
    key = os.environ["OPENROUTER_API_KEY"]
    payload = {"model": JUDGE_MODEL, "temperature": 0, "max_tokens": MAX_TOKENS, "reasoning": {"effort": "minimal"},
               "messages": [{"role": "user", "content": prompt}], "usage": {"include": True}}
    err = None
    for attempt in range(retries):
        r = requests.post(OPENROUTER_URL, headers={"Authorization": f"Bearer {key}"}, json=payload, timeout=120)
        if r.status_code == 402:
            raise PaymentRequired(r.text[:300])
        if r.status_code == 200 and "error" not in r.json():
            j = r.json()
            usage.add(JUDGE_MODEL, j.get("usage") or {})
            ch = j["choices"][0]
            return ch["message"]["content"] or "", ch.get("finish_reason")
        err = f"{r.status_code}: {r.text[:200]}"
        time.sleep(min(2 ** attempt, 10))
    raise RuntimeError(f"failed after {retries}: {err}")


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = load_error_items()
    print(f"{len(rows)} ERROR items")
    done = {r["item_id"]: r for r in map(json.loads, OUT.read_text().splitlines())} if OUT.exists() else {}
    todo = [r for r in rows if r["item_id"] not in done or done[r["item_id"]].get("error")]
    usage = Usage(OUT_DIR / "judge_usage.json")

    def one(r):
        try:
            text, fin = ask(r["prompt_text"], usage)
            p, ev = parse_symbol(text)
            cls = "m" if p == r["m"] else "c" if p == r["c"] else "other"
            return {**r, "model": JUDGE_MODEL, "response": text, "parsed": p, "parse_evidence": ev, "class": cls,
                    "max_tokens": MAX_TOKENS, "finish_reason": fin}
        except PaymentRequired:
            raise
        except Exception as e:  # noqa: BLE001
            return {**r, "model": JUDGE_MODEL, "error": repr(e)[:300]}

    with ThreadPoolExecutor(4) as ex:
        for res in ex.map(one, todo):
            done[res["item_id"]] = res
    with OUT.open("w") as f:
        for r in rows:
            f.write(json.dumps(done[r["item_id"]]) + "\n")
    print(f"wrote {OUT}; errors {sum(1 for r in done.values() if r.get('error'))}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except PaymentRequired as e:
        print(f"HTTP 402 from OpenRouter — stopping: {e}")
        sys.exit(2)
