"""Re-point the WS9 (r_gemma) pipeline at one BRIEF_RP pair, before any r_gemma module but ``config`` is imported.

``activate(pair)`` overwrites the constants of ``projects.r_gemma.config`` (target, oracle, grid, sites, cache and results
paths, module name), then imports ``gemma`` / ``oracle`` / ``collect`` so their default arguments bind to the pair, and
swaps in the Qwen3 pieces:
  * ``gemma.chat_ids``: Qwen3's template with ``enable_thinking=False`` (BRIEF_R's chat render; the oracle's training render,
    ``create_training_datapoint``); ``raw`` needs nothing (Qwen3 has no BOS);
  * the ledger: ``results/g_agreement/compute.rp.jsonl`` (BRIEF_RP §8);
  * Q8B: the five-slot reader (``multi.MultiAOReader``), the virtual layer ``Q8B_VIRTUAL`` = blocks 21–25 stacked from Q8's
    states, prompt-only and capture skipped (same target as Q8, already done).
The rules, statistics and file formats are r_gemma's (BRIEF_RP: "the rules are BRIEF_RG's").
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from projects.r_panel import pairs as PR

ACTIVE: dict[str, Any] = {}


def _guard() -> None:
    loaded = [m for m in ("projects.r_gemma.gemma", "projects.r_gemma.oracle", "projects.r_gemma.collect",
                          "projects.r_gemma.analyze", "projects.r_gemma.followup") if m in sys.modules]
    if loaded and not ACTIVE:
        raise RuntimeError(f"activate() must run before importing {loaded}")


def qwen_chat_ids(tokenizer: Any, user: str, assistant: str | None = None) -> tuple[list[int], list[int]]:
    msgs = [{"role": "user", "content": user}]

    def ids(x: Any) -> list[int]:
        return list(x["input_ids"] if hasattr(x, "keys") else x)

    head = ids(tokenizer.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True, enable_thinking=False))
    if assistant is None:
        return head, head
    full = ids(tokenizer.apply_chat_template(msgs + [{"role": "assistant", "content": assistant}], tokenize=True,
                                             add_generation_prompt=False, enable_thinking=False))
    if full[: len(head)] != head:   # Qwen3 renders the final assistant turn without the empty think block: build it from head
        full = head + list(tokenizer(assistant, add_special_tokens=False)["input_ids"])
    return head, full


def pos_probe_job(pair: str, dataset: str, layers: Any = None, seed: int = 0) -> int:
    """Picklable entry for r_gemma's joblib position-probe workers: a fresh worker process re-activates the pair and the
    cache dir (env ``RP_CACHE_DIR``, set by ``run.py`` before the pool starts), then runs r_gemma's ``pos_probes`` on the
    pair's probe blocks."""
    import os

    activate(pair)
    from projects.r_gemma import collect as RGC

    if os.environ.get("RP_CACHE_DIR") and RGC.RG_DIR != Path(os.environ["RP_CACHE_DIR"]):
        RGC.set_cache_dir(Path(os.environ["RP_CACHE_DIR"]))
    spec = PR.PAIRS[pair]
    return ACTIVE["orig_pos_probes"](dataset, tuple(spec.get("pos_probe", spec["pos_layers"])), seed)


def activate(pair: str, cache_root: Path | None = None, analysis_worker: bool = False) -> dict[str, Any]:
    """``analysis_worker``: a joblib worker of the CPU analysis, where unpickling the job's arguments has already imported
    r_gemma.analyze; that module reads the pair's constants at call time, and the caller re-runs its ``configure_analyze``."""
    if ACTIVE:
        if ACTIVE["pair"] != pair:
            raise RuntimeError(f"r_panel already activated for {ACTIVE['pair']}")
        return ACTIVE
    if not analysis_worker:
        _guard()
    p = PR.PAIRS[pair]
    from projects.g_agreement.core import config as C
    from projects.r_gemma import config as G

    G.MODULE = "rp"
    G.TARGET_ID, G.TARGET_SHA = p["target"]
    G.ATTN_IMPL = "eager"
    G.N_LAYERS, G.D_MODEL = p["n_layers"], p["d_model"]
    G.AO_REPO, G.AO_SHA = p["ao"]
    G.AO_FILES = list(PR.AO_FILES)
    G.AO_GRID = tuple(p["grid"])
    G.LAYERS = tuple(p["layers"])
    G.SAE_LAYER = p["probe"]              # r_gemma names the probe / rotation-readout site "SAE_LAYER"; no SAE on this panel
    G.AO_READ_LAYERS = {k: tuple(v) for k, v in p["ao_read"].items()}
    G.PRIMARY_LAYER = {"ao": p["primary"], "ao_yn": p["primary"], "logit_lens": p["probe"], "probe": p["probe"]}
    G.POS_LAYERS = tuple(p["pos_layers"])
    G.SAES = {}
    root = Path(cache_root) if cache_root else C.CACHE_DIR / "rp"
    G.RG_DIR = root / pair
    G.RESULTS = C.RESULTS_DIR / "rp" / pair
    G.LOG = C.RESULTS_DIR / "rp" / "log.md"
    G.FROZEN_RG = C.MANIFEST_DIR / f"frozen_config_rp_{pair}.json"
    ACTIVE.update(pair=pair, spec=p, ao_model_name=p["ao_model_name"])

    from projects.r_gemma import gemma as GM

    GM.chat_ids = qwen_chat_ids

    from projects.r_gemma import oracle as O

    _orig_check = O.AOReader._check_config

    def _check_config(self) -> None:   # the oracle's model_name is the pair's target (Q8B: unsloth base, K2)
        saved = G.TARGET_ID
        G.TARGET_ID = ACTIVE["ao_model_name"]
        try:
            _orig_check(self)
        finally:
            G.TARGET_ID = saved

    O.AOReader._check_config = _check_config

    from projects.r_gemma import collect as RGC

    RGC.MODULE = "rp"
    RGC.RG_DIR, RGC.RESULTS, RGC.LOG = G.RG_DIR, G.RESULTS, G.LOG
    _orig_derive = RGC._derive_paths

    def _derive_paths() -> None:
        _orig_derive()
        RGC.LOG = G.LOG
        RGC.LEDGER_PATH = C.RESULTS_DIR / "compute.rp.jsonl"
        if p.get("states_from"):
            RGC.STATES_DIR = RGC.RG_DIR.parent / p["states_from"] / "states"

    RGC._derive_paths = _derive_paths
    RGC._derive_paths()
    ACTIVE["orig_pos_probes"] = RGC.pos_probes

    if "pos_ao" in p:
        fn = RGC.collect_reader_positions

        def collect_reader_positions(reader: Any, dataset: str, items: Any, layers: Any = None, *a: Any, **k: Any) -> Any:
            return fn(reader, dataset, items, tuple(p["pos_ao"]), *a, **k)

        RGC.collect_reader_positions = collect_reader_positions
    import functools

    # every pair: joblib workers must re-activate the pair (a bare r_gemma pos_probes in a worker sees Gemma's paths)
    RGC.pos_probes = functools.partial(pos_probe_job, pair)

    if p.get("multi"):
        from projects.r_panel import multi as MU

        MU.install(RGC, O, p)
    return ACTIVE
