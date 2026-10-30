"""G3 prompt-only arm (GPU, phase A, independent of G1 outputs): the base model answers each
item's primary question from the item prompt text alone, through the frozen
``config.PROMPT_ONLY_TEMPLATE`` (chat render, thinking off, greedy, 128 new tokens). No
activation, no reader output, no target answer is ever in the prompt.

    python -m projects.g_agreement.g3_activation_dependence.collect_prompt_only --items test
    python -m projects.g_agreement.g3_activation_dependence.collect_prompt_only --items dev
    # G6: --items-file projects/g_agreement/dataset/items_g6.json --module g6  (-> gens/g6_prompt_only.jsonl)

Rows: ``cache/g_agreement/gens/g3.jsonl`` (INTERFACES §5, ``method: prompt_only``,
``input.visible_prompt`` = the exact rendered prompt). Resumable.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import generate as G
from projects.g_agreement.core import model as M
from projects.g_agreement.core.accounting import StepLedger, append_jsonl, done_ids, log_line
from projects.g_agreement.g1_agreement import collect as G1
from projects.g_agreement.g1_agreement.collect import base_row, load_target_timed, select_items

MODULE = "g3"
GENS = C.GENS_DIR / "g3.jsonl"  # shared with the state_free rows (same module)
LOG = C.RESULTS_DIR / "g3" / "log.md"


def collect_prompt_only(target: M.Target, items: list[dict[str, Any]], *, gens_path: Path = GENS,
                        max_new_tokens: int = C.PROMPT_ONLY_MAX_NEW_TOKENS, ledger_path: Path | None = None,
                        log_path: Path | None = LOG, module: str = MODULE) -> int:
    done = done_ids(gens_path)
    ledger = StepLedger(step="prompt_only", module=module)
    n = 0
    for it in items:
        row = base_row(module, "prompt_only", "prompt_only", it, 0)
        row["seed"] = None
        row["state_item_id"] = None
        if row["gen_id"] in done:
            continue
        res, ids, visible = G.prompt_only_answer(target, it, max_new_tokens)
        rendered = target.tokenizer.decode(ids, skip_special_tokens=False)
        for forbidden in ("<explanation>", "<activation>"):
            assert forbidden not in visible, "prompt-only prompt must not contain reader material"
        row.update({
            "input": {"fixed_instruction": C.PROMPT_ONLY_TEMPLATE, "layer_in_prompt": None,
                      "visible_prompt": rendered, "visible_prompt_user_turn": visible,
                      "prompt_ids_sha256": C.sha256_ids(ids), "injection": "none", "activation_norm": None,
                      "question": it["primary"]["question"]},
            "sampling": res.sampling, "raw_output": res.raw_output, "native": {"text": res.raw_output.strip()},
            "n_prompt_tokens": res.n_prompt_tokens, "n_new_tokens": res.n_new_tokens,
            "finish_reason": res.finish_reason, "wall_s": res.wall_s, "peak_mem_gb": res.peak_mem_gb,
            "model_sha": C.TARGET_MODEL_SHA, "adapter": "none",
        })
        append_jsonl(gens_path, row)
        ledger.add(res.n_prompt_tokens, res.n_new_tokens, res.wall_s, res.peak_mem_gb)
        n += 1
        print(f"[{module}/prompt_only] {row['gen_id']} -> {res.raw_output.strip()[:60]!r}", flush=True)
    r = ledger.flush(ledger_path)
    if log_path and r:
        log_line(log_path, f"prompt_only: {r}")
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--items", choices=["dev", "test", "all"], default="dev")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--item-ids", default=None)
    ap.add_argument("--max-new-tokens", type=int, default=C.PROMPT_ONLY_MAX_NEW_TOKENS)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--items-file", default=None, help="another items.json (G6: dataset/items_g6.json); sha recorded per row")
    ap.add_argument("--module", default=MODULE, help="module name (G6: g6)")
    ap.add_argument("--gens", default=None, help="output JSONL (default gens/<module>_prompt_only.jsonl)")
    a = ap.parse_args(argv)
    items_path = Path(a.items_file) if a.items_file else None
    gens_path = Path(a.gens) if a.gens else (GENS if a.module == MODULE else C.GENS_DIR / f"{a.module}_prompt_only.jsonl")
    log_path = LOG if a.module == MODULE else C.RESULTS_DIR / a.module / "log.md"
    if items_path is not None:
        G1.ROW_EXTRA.update(items_file=str(items_path), items_file_sha256=C.sha256_file(items_path), **C.frozen_shas())
        C.require_frozen(a.items, allow_unfrozen_dev=a.allow_unfrozen or a.items == "dev", strict_code=False)
    else:
        C.require_frozen(a.items, allow_unfrozen_dev=a.allow_unfrozen or a.items == "dev")
    items = select_items(a.items, a.limit, a.item_ids.split(",") if a.item_ids else None, path=items_path)
    if not items:
        raise SystemExit("no items selected")
    target = load_target_timed(a.module)
    log_line(log_path, f"prompt-only: {len(items)} items ({a.items}{' from ' + str(items_path) if items_path else ''}), "
                       f"template sha {C.sha256_bytes(C.PROMPT_ONLY_TEMPLATE.encode())[:12]}")
    collect_prompt_only(target, items, gens_path=gens_path, max_new_tokens=a.max_new_tokens, log_path=log_path, module=a.module)
    M.unload(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
