"""G4 repeated readings (GPU): +2 OLens samples (phase A) and +2 NLA samples (phase B) on the
8 preselected states of ``dataset/g4_pairs.json`` (chosen by seed before any test output
existed). Same frozen sampling as G1; sample_idx 1 and 2 (G1's first sample is idx 0), so
seeds differ by construction and the three samples are comparable.

    python -m projects.g_agreement.g4_repeats.collect --phase A
    python -m projects.g_agreement.g4_repeats.collect --phase B

Rows: ``cache/g_agreement/gens/g4.jsonl`` (``module: g4``, ``condition: repeat``). Resumable.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import states as S
from projects.g_agreement.core.accounting import StepLedger, log_line, timed_call
from projects.g_agreement.g1_agreement.collect import collect_verbalizer, load_target_timed

MODULE = "g4"
GENS = C.GENS_DIR / "g4.jsonl"
LOG = C.RESULTS_DIR / "g4" / "log.md"
SAMPLE_IDXS = [1, 2]


def g4_items(limit: int = 0) -> list[dict[str, Any]]:
    if not C.G4_PAIRS_JSON.exists():
        raise SystemExit(f"{C.G4_PAIRS_JSON} missing: run dataset/g4_selection.py first")
    sel = json.loads(C.G4_PAIRS_JSON.read_text(encoding="utf-8"))
    if not sel.get("chosen_before_test_outputs", False):
        raise SystemExit("g4_pairs.json does not assert chosen_before_test_outputs")
    want = list(sel["item_ids"])
    by_id = {it["item_id"]: it for it in C.load_items("all")}
    missing = [i for i in want if i not in by_id]
    if missing:
        raise SystemExit(f"g4 item ids not in dataset: {missing}")
    items = [by_id[i] for i in want]
    return items[: limit or None]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "B", "all"], default="A")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-new-tokens", type=int, default=None)
    ap.add_argument("--allow-unfrozen", action="store_true", help="development only")
    a = ap.parse_args(argv)
    if not a.allow_unfrozen:
        C.require_frozen("test", allow_unfrozen_dev=False)
    items = g4_items(a.limit)
    cap = a.max_new_tokens or C.VERBALIZER_MAX_NEW_TOKENS
    print(f"G4: {len(items)} items {[it['item_id'] for it in items]}; samples {SAMPLE_IDXS}; cap {cap}")
    if a.phase in ("A", "all"):
        target = load_target_timed(MODULE)
        S.ensure_states(target, items, module=MODULE)  # normally all cached by G1
        ol = R.OLensReader(max_new_tokens=cap).bind(target)
        log_line(LOG, f"phase A olens adapter={ol.adapter_dir} liveness={ol.liveness} items={len(items)}")
        collect_verbalizer(ol, items, module=MODULE, sample_idxs=SAMPLE_IDXS, gens_path=GENS,
                           condition="repeat", max_new_tokens=cap, log_path=LOG)
        M.unload(target)
    if a.phase in ("B", "all"):
        missing = [it["item_id"] for it in items if not S.state_path(it["item_id"]).exists()]
        if missing:
            raise SystemExit(f"missing states {missing}; run G1 phase A first")
        ledger = StepLedger(step="load_nla", module=MODULE)
        with timed_call() as st:
            nla = R.NLAReader(max_new_tokens=cap).bind()
        ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        ledger.flush()
        log_line(LOG, f"phase B nla adapter={nla.adapter_dir} liveness={nla.liveness} items={len(items)}")
        collect_verbalizer(nla, items, module=MODULE, sample_idxs=SAMPLE_IDXS, gens_path=GENS,
                           condition="repeat", max_new_tokens=cap, log_path=LOG)
        nla.unload()
    return 0


if __name__ == "__main__":
    sys.exit(main())
