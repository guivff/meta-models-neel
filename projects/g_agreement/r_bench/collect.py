"""Phase R collection (GPU; BRIEF_R.md §2–3). Batched multi-layer last-token capture of the R-A / R-B banks in two
renders, logit-lens margins in the same forward, the prompt-only forced-choice baseline, every reader's native LO on
the test splits at its sites, and the shuffled / state-free controls.

    python -m projects.g_agreement.r_bench.collect --freeze-r                      # CPU: manifest/frozen_config_r.json
    python -m projects.g_agreement.r_bench.collect --phase A --datasets 92_glue_sst2 66_living-room --allow-unfrozen --renders chat  # smoke
    python -m projects.g_agreement.r_bench.collect --phase A                       # target: capture, logit lens, prompt-only, J-lens, Oracle, skip-lens
    python -m projects.g_agreement.r_bench.collect --phase B                       # NLA (reads the cached block-42 states)
    python -m projects.g_agreement.r_bench.collect --phase A --kway                # the multiclass parents (R-B)
    python -m projects.g_agreement.r_bench.collect --phase A --items-file dataset/items_re.json   # another bank in the same schema
    python -m projects.g_agreement.r_bench.collect --phase A --reader-states       # E3: the Oracle's / skip-lens's own hidden states while scoring
    python -m projects.g_agreement.r_bench.collect --phase A --readers olens --olens-alpha-scales 0.5 2 --olens-layers 44 48 52 56 --datasets ...  # E12
    python -m projects.g_agreement.r_bench.collect --phase A --shard 2/4 --pod A2   # PLAN_R §9: datasets 2, 6, 10, ... of the sorted list; outputs *.2.jsonl

Conventions (the ones ``core/`` fixes; audited 2026-10-18, see results/g_agreement/r/log.md):
  chat render  = the text as the user turn (plus the item's ``system`` turn when set), thinking off, generation prompt
                 appended (``core.model.render_item``); the default read site is the LAST token = the assistant onset after
                 ``<think>\\n\\n</think>\\n\\n`` (asserted per row)
  raw render   = the bare text, no special tokens, no system turn, read at its last text token (the SAE-probing site)
  read_position (E6 / E14; HANDOFF item 5) = items may carry ``{"kind": "char_span", "char_start": i, "char_end": j, "text", "role",
                 "fallback": "last_text_token"}``: the state is ALSO captured at the last token whose offset span (tokenizer offsets
                 on ``prompt_text`` BEFORE the chat template) overlaps ``prompt_text[i:j]``; chosen index per item and render in
                 index.json (``read_position_token``), rows keyed ``...|rp|...``
  capture      = RIGHT padding + attention mask, one forward per chunk, hooks on the block OUTPUT (== hidden_states[L+1]),
                 adapter disabled (``disable_adapter_ctx``); the prompt-only forward also runs adapter-off
  Oracle       = carrier prompt per read layer (``OLensReader.carrier(layer)``: "layer {L}" in the prompt), 42 off-grid as before;
                 ``--olens-alpha-scales`` adds variants ``olens_a<s>x`` with alpha = s × 16000 (E12)
  NLA / skip   = each item's template is registered under family ``r:<dataset>`` (spec template) or ``r:<dataset>:t<hash>``
  J-lens       = each candidate is scored on its own single-token variants, so a one-sided fact keeps s_pos when the
                 negative has no single-token form (``score_pairs``); two-sided facts need both
  logit lens   = first tokens per ``core.edit.first_token_candidates`` (first spelling whose first tokens differ; the
                 ``jlens_*`` short forms as the fallback), lp under final norm + W_U per captured layer, per item
  reader states (E3) = with --reader-states, hooks on the READER model's blocks save its hidden states at the marker, the
                 pre-answer token and the first answer token of each candidate during the natural LO scoring at the primary site

Outputs (all resumable by ``key``; ``cache/g_agreement/r/``, or ``r_unfrozen/`` for --allow-unfrozen runs):
  states/<dataset>/<render>_L<layer>.npy       fp16 [N, d] in the order of states/<dataset>/index.json (test items first)
  states/<dataset>/<render>_L<layer>_rp.npy    same rows at the item's read_position (NaN rows for items without one)
  reader_states/<reader>/<dataset>/<render>_L<layer>_rL<reader_layer>.npy   fp16 [N_test, T, 4, d] (E3) + index.json
  logit_lens.jsonl     key ll|<dataset>|<render>|<item_id>      per-layer lp(first token of pos) - lp(first token of neg)
  prompt_only.jsonl    key po|<dataset>|<item_id>                 forced-choice LO of the base model (adapter off), its greedy pick
  reader_lo.jsonl      key <reader>|L<layer>|<render>[|rp][|shuf]|<item_id>   lp_A = s_pos, lp_B = s_neg, lo = s_diff
  state_free.jsonl     key <reader>|L<layer>|<render>[|rp]|<dataset>[|p<k>]   the reader's scores on the dataset-mean state
  kway_lo.jsonl        key <reader>|L<layer>|<render>|<item_id>|c<i>  (R-B) lp of candidate i; prompt-only k-way rows too
  model_labels.jsonl   key ml|<dataset>|<item_id>                 facts with primary.label_source == "model" (ReaderBench INTERNAL /
                       CONTEXT against-belief): the base model's greedy continuation of the item's own render and the label
                       derived from it (``model_label``); analyze uses it instead of the provisional ``label``
  re_relabel.jsonl     key rl|<dataset>|<item_id>                 WS10's re_internal_refuse / re_internal_abstain: the base model's greedy
                       continuation (32 new tokens, adapter off) and the label ``beyond_text.CLASSIFIERS`` derives from it; every reader
                       row of those two facts is scored on that key (``primary.key = "greedy"``), phase B included
Items with ``capture_messages`` (an earlier-turn conversation) render through ``core.model.chat_ids`` on the full message
list; ``prompt_text`` is the last user turn, and the prompt-only render replaces that turn with the forced-choice prompt.
Ledger steps (module r, one row per step per run): load_target, capture_<render>, prompt_only, model_labels, lo_<reader>_L<layer>,
control_<reader>_L<layer>, kway_<reader>_L<layer>, reader_states_<reader>, load_nla.  Log: results/g_agreement/r/log.md.
Multi-pod runs (PLAN_R §9): ``--shard k/N`` takes the datasets whose index in the SORTED list of the bank's datasets is
≡ k-1 (mod N) (stable under --datasets filters); every appended file gets the shard suffix (``reader_lo.k.jsonl``,
``results/g_agreement/compute.k.jsonl``, ``results/g_agreement/r/log.k.md``) so there is one writer per file; every row,
ledger row and log line carries ``pod``, ``shard`` and ``git_sha``. Phase B skips datasets whose block-42 states are not on
disk yet and is re-run to completion (resumable per key).
Test items need manifest/frozen_config_r.json (the sha of the items file used) unless --allow-unfrozen.
Provenance (PODS.md rule 10 / GUARDS.md rule 3, 2026-10-20): every row, ledger row, index.json and log line also carries
``run_id`` (UTC start + uuid, once per process), ``run_kind`` and ``code_sha256`` (``row_meta``; callers such as planted.py may
override them through ``RUN_META``). The kind defaults to "unknown", never "real" by omission: a real run says
``--run-kind real``; ``--limit`` (a partial run) forces "smoke" and its own cache directory. ``--datasets`` never implies smoke
(real segmented runs use it). Every path written is enumerated by ``output_paths()`` (GUARDS.md rule 1).
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import platform
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import numpy as np

from projects.g_agreement.core import config as C
from projects.g_agreement.core import edit as E
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import StepLedger, append_jsonl, done_ids, log_line, now_iso, timed_call
from projects.g_agreement.r_bench import bank as B
from projects.g_agreement.r_bench import datasets as D

MODULE = "r"
R_DIR = C.CACHE_DIR / "r"
STATES_DIR = R_DIR / "states"
RS_DIR = R_DIR / "reader_states"
LL_PATH = R_DIR / "logit_lens.jsonl"
PO_PATH = R_DIR / "prompt_only.jsonl"
LO_PATH = R_DIR / "reader_lo.jsonl"
SF_PATH = R_DIR / "state_free.jsonl"
KWAY_PATH = R_DIR / "kway_lo.jsonl"
ML_PATH = R_DIR / "model_labels.jsonl"
RL_PATH = R_DIR / "re_relabel.jsonl"
RESULTS = C.RESULTS_DIR / "r"
LOG = RESULTS / "log.md"
PROVENANCE_DIR = RESULTS / "provenance"  # sidecars for rows written before the run stamps (write_legacy_provenance)
LEDGER_PATH: Path | None = None          # None = results/g_agreement/compute.jsonl; shard runs: compute.<k>.jsonl
FROZEN_R = C.MANIFEST_DIR / "frozen_config_r.json"
SHARD: tuple[int, int] | None = None     # (k, N), 1-based k
SUFFIX: str | None = None                # extra tag on every appended file (phase B under a shard: "B" -> reader_lo.<k>.B.jsonl)
ITEMS_PATH: Path | None = None           # the bank main() runs on; stamps rows whose caller passes no items_path
# The appended row files: module global -> file stem (``<stem>[.<k>][.<suffix>].jsonl`` under R_DIR). _apply_paths and
# output_paths both read this table, so a new row file exists in one place only (GUARDS.md rule 1).
ROW_FILES = {"LL_PATH": "logit_lens", "PO_PATH": "prompt_only", "LO_PATH": "reader_lo", "SF_PATH": "state_free",
             "KWAY_PATH": "kway_lo", "ML_PATH": "model_labels", "RL_PATH": "re_relabel"}
# Module-level paths that are read, never written (output_paths' catch-all, unlisted_paths, skips these and only these).
INPUT_PATHS = ("ITEMS_PATH",)

# Run provenance (GUARDS.md rule 3): one id per process, the kind declared, never inferred as "real".
RUN_KINDS = ("real", "smoke", "test", "unknown")
RUN_STARTED_AT = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
RUN_ID = f"{RUN_STARTED_AT.replace('-', '').replace(':', '')}-{uuid.uuid4().hex[:12]}"
RUN_KIND = "unknown"                     # main: --run-kind (real runs say so), --limit forces "smoke"; tests set "test"
# pod, shard, git_sha (set_run_meta) and collect.py's own run_id / run_kind defaults; callers may push overrides
# (planted.py: its run_id / run_kind / code_sha256). Merged into every row, ledger row, index and log line by row_meta().
RUN_META: dict[str, Any] = {"run_id": RUN_ID, "run_started_at": RUN_STARTED_AT, "run_kind": RUN_KIND}

LAYERS = (24, 28, 32, 36, 38, 40, 42, 44, 48, 52, 56, 60)   # captured; probes, the J-lens sweep and the logit lens use all of them; 38 = the R5 edit layer (WS4, HANDOFF)
# BRIEF_R §2.1 / §4.4: J-lens every captured block (sweep 24–60), Oracle 44 primary + 48/52/56 (+ 42 for continuity),
# skip-lens and NLA at 42 (training site).
READ_LAYERS = {"jlens": LAYERS, "olens": (42, 44, 48, 52, 56), "skip_a": (42,), "skip_d": (42,), "nla": (42,)}
PRIMARY_LAYER = {"jlens": 42, "olens": 44, "skip_a": 42, "skip_d": 42, "nla": 42}
# E6 / E14 read_position rows: the span site is read early (BRIEF_R §11: blocks 24–40 for the KHOP hop-1 span) and at
# the readers' usual sites; the Oracle's early blocks are on its training grid (20..60 step 4).
RP_READ_LAYERS = {"jlens": LAYERS, "olens": (24, 28, 32, 36, 40, 44, 48, 52, 56), "skip_a": (42,), "skip_d": (42,), "nla": (42,)}
RENDERS = ("chat", "raw")
MAX_TOKENS = 256          # texts are cut to this many tokens at render time (raw render keeps the last token = last text token)
CAPTURE_BATCH = 16
SHUFFLE_SEED = 20261019
POOL_EVAL = 64            # pool items (balanced, 32 per class) scored by every reader at its primary site: the quiver's labelled pool
CAPTURE_BUDGET_MIN = 45   # PLAN_R §1 WS2: beyond this, drop the raw render for the Oracle at 48–56 (--olens-raw-layers 42 44)
READER_STATE_LAYERS = (16, 32, 48, 60)   # E3: four blocks of the reader model, spread over its depth
READER_STATE_POSITIONS = ("marker", "pre_answer", "answer_A", "answer_B")
RP_KINDS = ("char_span", "hop1_span_end")   # accepted read_position kinds (WS11 contract; WS10's pre-contract name)


# ------------------------------------------------------------------ cache location, shards, run metadata
def _apply_paths() -> None:
    """Derive every appended-file path from ``R_DIR``, ``RESULTS`` and ``SHARD`` (``name.<k>.jsonl`` under a shard)."""
    global STATES_DIR, RS_DIR, LOG, LEDGER_PATH, PROVENANCE_DIR
    tag = (f".{SHARD[0]}" if SHARD else "") + (f".{SUFFIX}" if SUFFIX else "")
    STATES_DIR = R_DIR / "states"
    RS_DIR = R_DIR / "reader_states"
    for var, stem in ROW_FILES.items():
        globals()[var] = R_DIR / f"{stem}{tag}.jsonl"
    LOG = RESULTS / f"log{tag}.md"
    PROVENANCE_DIR = RESULTS / "provenance"
    LEDGER_PATH = (C.RESULTS_DIR / f"compute{tag}.jsonl") if (SHARD or SUFFIX) else None
    _DONE.clear()


def output_paths() -> dict[str, Path]:
    """Every location this module writes, as currently configured (after set_cache_dir / set_shard): the row files, the
    state trees, the log, the compute ledger, the freeze manifest and the provenance sidecars. Tests redirect THIS
    enumeration and check that nothing else is written (GUARDS.md rule 1); ``unlisted_paths`` is its catch-all."""
    out: dict[str, Path] = {stem: globals()[var] for var, stem in ROW_FILES.items()}
    out.update(cache_root=R_DIR, results_root=RESULTS, states_dir=STATES_DIR, reader_states_dir=RS_DIR, log=LOG,
               ledger=LEDGER_PATH or C.COMPUTE_LEDGER, frozen_manifest=FROZEN_R, provenance_dir=PROVENANCE_DIR)
    return out


def unlisted_paths() -> list[str]:
    """Module globals holding a Path that ``output_paths()`` does not enumerate and ``INPUT_PATHS`` does not declare
    (empty when the enumeration is complete). A new path constant added without its ``output_paths`` entry shows up
    here by name, so the tests' redirect cannot silently miss it (the 2026-10-20 swap_poetry_pool leak)."""
    listed = {Path(p) for p in output_paths().values()}
    return sorted(name for name, v in globals().items()
                  if isinstance(v, Path) and name not in INPUT_PATHS and not name.startswith("_") and v not in listed)


def set_cache_dir(root: Path) -> Path:
    """Point every output path at ``root`` (the smoke / unfrozen runs use ``cache/g_agreement/r_unfrozen``)."""
    global R_DIR
    R_DIR = Path(root)
    _apply_paths()
    return R_DIR


def parse_shard(spec: str | None) -> tuple[int, int] | None:
    """``"k/N"`` with 1 <= k <= N (PLAN_R §9: ``--shard 2/4``)."""
    if spec is None:
        return None
    try:
        k, n = (int(x) for x in spec.split("/"))
    except ValueError as exc:
        raise ValueError(f"--shard must be k/N, got {spec!r}") from exc
    if not 1 <= k <= n:
        raise ValueError(f"--shard k/N needs 1 <= k <= N, got {spec!r}")
    return k, n


def set_shard(shard: tuple[int, int] | None, suffix: str | None = None) -> None:
    """Shard-suffix every appended file (one writer per file; states and reader_states are per dataset already).
    ``suffix`` adds a second tag (``reader_lo.<k>.<suffix>.jsonl``): phase B under a shard uses "B" so pod C never writes
    the file pod A-k is still appending to (PLAN_R §9 rule 2); the plain unsharded names are unchanged."""
    global SHARD, SUFFIX
    SHARD = shard
    SUFFIX = (suffix or None) if (shard or suffix) else None
    _apply_paths()


def shard_datasets(all_datasets: list[str], shard: tuple[int, int] | None) -> list[str]:
    """The datasets of shard k of N: positions ≡ k-1 (mod N) in the SORTED list of all the bank's datasets, so the
    partition does not depend on a ``--datasets`` filter or on item order."""
    ds = sorted(set(all_datasets))
    if shard is None:
        return ds
    k, n = shard
    return [d for i, d in enumerate(ds) if i % n == k - 1]


def git_sha() -> str | None:
    """HEAD's commit sha (PLAN_R §9 rule 1). The pods are rsync copies without ``.git``, so after git the fallbacks are
    ``$R_GIT_SHA`` and then a ``GIT_SHA`` file at the repo root (written on the Mac before the rsync, PODS.md §1)."""
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=C.REPO_ROOT, capture_output=True, text=True, timeout=5).stdout.strip()
        if out:
            return out
    except Exception:
        pass
    env = os.environ.get("R_GIT_SHA", "").strip()
    if env:
        return env
    try:
        f = C.REPO_ROOT / "GIT_SHA"
        if f.exists():
            words = f.read_text().split()
            return words[0] if words else None
    except Exception:
        pass
    return None


def set_run_meta(pod: str | None = None, shard: tuple[int, int] | None = None, run_kind: str | None = None) -> dict[str, Any]:
    """``RUN_META`` for this process: the pod id (``--pod``, else $RUNPOD_POD_ID, else the hostname), the shard tag and
    the commit sha (PLAN_R §9 rules 1 and 3), plus collect.py's own ``run_id`` / ``run_started_at`` / ``run_kind``
    defaults (GUARDS.md rule 3; ``run_kind`` given here is declared through ``set_run_kind``). A caller may still
    override any of them afterwards (planted.py pushes its own run_id, run_kind and code_sha256)."""
    if run_kind is not None:
        set_run_kind(run_kind)
    RUN_META.clear()
    RUN_META.update(pod=pod or os.environ.get("RUNPOD_POD_ID") or platform.node(),
                    shard=f"{shard[0]}/{shard[1]}" if shard else None, git_sha=git_sha(),
                    run_id=RUN_ID, run_started_at=RUN_STARTED_AT, run_kind=RUN_KIND)
    return dict(RUN_META)


def set_run_kind(kind: str) -> str:
    """Declare this process's run kind (one of ``RUN_KINDS``); ``RUN_META`` follows at once, so rows written after the
    call carry it (a stamp frozen at import is the WS4 decoy finding, GUARDS.md)."""
    global RUN_KIND
    if kind not in RUN_KINDS:
        raise ValueError(f"run kind {kind!r} is not one of {RUN_KINDS}")
    RUN_KIND = kind
    RUN_META["run_kind"] = kind
    return kind


def code_sha256() -> str:
    """sha256 over the r-code tree (``r_code_files``: core/*.py and r_bench/*.py, the freeze's ``r_code_sha256``), once per
    process; the same value as the rows' ``current_r_code_sha256``."""
    if "_code" not in _SHAS:
        _SHAS["_code"] = C.sha256_tree(r_code_files())
    return _SHAS["_code"]


def run_stamp() -> dict[str, Any]:
    """collect.py's own per-process provenance, evaluated at call time (GUARDS.md rule 3)."""
    return {"run_id": RUN_ID, "run_started_at": RUN_STARTED_AT, "run_kind": RUN_KIND, "code_sha256": code_sha256()}


def row_meta() -> dict[str, Any]:
    """What every appended row, ledger row, index.json and log line carries: collect.py's ``run_stamp`` defaults,
    overridden by ``RUN_META`` (pod, shard, git_sha and whatever a caller pushed in). The defaults stay even when a caller
    clears ``RUN_META`` or never calls ``set_run_meta``, so no collect.py row lacks a run_id, a run kind or a code sha."""
    return {**run_stamp(), **RUN_META}


def rlog(text: str) -> None:
    """A log.md line (shard-suffixed file) prefixed with the run metadata."""
    m = row_meta()
    tag = (f"[pod={m.get('pod')} shard={m.get('shard')} sha={(m.get('git_sha') or 'none')[:10]} run={m['run_id']} "
           f"kind={m['run_kind']} code={str(m['code_sha256'])[:10]}] ")
    log_line(LOG, tag + text)


# ------------------------------------------------------------------ resumability (keys loaded once per path per process)
_DONE: dict[Path, set[str]] = {}


def done_keys(path: Path) -> set[str]:
    """The ``key`` values already in ``path``; read from disk once, then kept current by ``append_row``."""
    p = Path(path)
    if p not in _DONE:
        _DONE[p] = done_ids(p, key="key")
    return _DONE[p]


def append_row(path: Path, row: dict[str, Any]) -> None:
    """Append a resumable row; the run metadata (pod, shard, git_sha, run_id, run_kind, code_sha256) rides on every row."""
    append_jsonl(path, {**row, **row_meta()})
    done_keys(path).add(row["key"])


# ------------------------------------------------------------------ ledger (one row per step per run; flushed by main / flush_ledgers)
_LEDGERS: dict[str, StepLedger] = {}


def ledger(step: str, **extra: Any) -> StepLedger:
    if step not in _LEDGERS:
        _LEDGERS[step] = StepLedger(step=step, module=MODULE, extra={**row_meta(), **extra})
    return _LEDGERS[step]


def flush_ledgers(path: Path | None = None) -> list[dict[str, Any]]:
    """Flush every accumulated step row to ``path`` (default: the shard's ``compute.<k>.jsonl``, else compute.jsonl)."""
    rows = []
    for step in list(_LEDGERS):
        r = _LEDGERS.pop(step).flush(path or LEDGER_PATH)
        if r:
            rows.append(r)
    return rows


# ------------------------------------------------------------------ freeze
def r_code_files() -> list[Path]:
    files = sorted(C.HERE.glob("*.py")) + sorted((C.PROJECT_DIR / "r_bench").glob("*.py"))
    return [f for f in files if f.exists()]


def items_files() -> dict[str, Path]:
    """Every bank in the items_r schema (items_r, items_rk, items_re, items_rx, items_rb, items_rc2, ...)."""
    return {p.name: p for p in sorted(C.DATASET_DIR.glob("items_r*.json"))}


def snapshot_r(frozen: bool) -> dict[str, Any]:
    return {"frozen": frozen, "frozen_at": now_iso(), "phase": "R",
            "items_r_sha256": C.sha256_file(B.ITEMS_R), "items_rk_sha256": C.sha256_file(B.ITEMS_RK),
            "items_sha256": {name: C.sha256_file(p) for name, p in items_files().items()},
            "spec_sha256": C.sha256_file(C.PROJECT_DIR / "r_bench" / "datasets.py"),
            "core_code_sha256": C.sha256_tree(C.core_code_files()), "r_code_sha256": C.sha256_tree(r_code_files()),
            "layers": list(LAYERS), "read_layers": {k: list(v) for k, v in READ_LAYERS.items()}, "primary_layer": PRIMARY_LAYER,
            "rp_read_layers": {k: list(v) for k, v in RP_READ_LAYERS.items()}, "reader_state_layers": list(READER_STATE_LAYERS),
            "renders": list(RENDERS), "max_tokens": MAX_TOKENS, "pool_eval": POOL_EVAL, "shuffle_seed": SHUFFLE_SEED,
            "prompt_only_fc_template": D.PROMPT_ONLY_FC_TEMPLATE, "prompt_only_kway_template": D.PROMPT_ONLY_KWAY_TEMPLATE,
            "nla_template_family": "r:<dataset>", "base_manifest": C.frozen_shas(),
            "assets": C.snapshot(frozen=False)["assets"]}


def freeze_r(force: bool = False) -> Path:
    if FROZEN_R.exists() and not force and json.loads(FROZEN_R.read_text()).get("frozen"):
        raise RuntimeError(f"{FROZEN_R} is already frozen; pass --force and add a dated Deviations note to BRIEF_R.md")
    if not B.ITEMS_R.exists():
        raise RuntimeError("dataset/items_r.json missing: run r_bench.bank --build first")
    C.MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    FROZEN_R.write_text(json.dumps(snapshot_r(True), indent=1, ensure_ascii=False) + "\n")
    _SHAS.clear()
    return FROZEN_R


def require_frozen_r(allow_unfrozen: bool, items_path: Path | None = None) -> None:
    """Test items need a frozen manifest whose recorded sha of the items file used matches disk."""
    if allow_unfrozen:
        return
    items_path = Path(items_path or B.ITEMS_R)
    if not FROZEN_R.exists():
        raise SystemExit("refusing to collect on test items: manifest/frozen_config_r.json missing (collect --freeze-r)")
    fz = json.loads(FROZEN_R.read_text())
    if not fz.get("frozen"):
        raise SystemExit("refusing to collect: frozen_config_r.json has frozen=false")
    recorded = (fz.get("items_sha256") or {}).get(items_path.name)
    if recorded is None and items_path.name == B.ITEMS_R.name:
        recorded = fz.get("items_r_sha256")
    if recorded is None and items_path.name == B.ITEMS_RK.name:
        recorded = fz.get("items_rk_sha256")
    if recorded is None:
        raise SystemExit(f"refusing to collect: {items_path.name} is not covered by the R freeze (re-freeze with --force + a Deviations note)")
    if recorded != C.sha256_file(items_path):
        raise SystemExit(f"refusing to collect: {items_path.name} changed since the R freeze")
    now = snapshot_r(True)
    for k in ("core_code_sha256", "r_code_sha256", "spec_sha256"):
        if fz.get(k) != now.get(k):
            print(f"[r] note: {k} changed since the R freeze; accepted, both recorded per row")


_SHAS: dict[str, Any] = {}


def r_shas(items_path: Path | None = None) -> dict[str, Any]:
    """Recorded per row; computed once per (items file, process): the items sha, the current and the frozen r-code sha."""
    items_path = Path(items_path or B.ITEMS_R)
    key = str(items_path)
    if key not in _SHAS:
        out = {"items_file": items_path.name, "items_sha256": C.sha256_file(items_path),
               "current_r_code_sha256": _SHAS.setdefault("_code", C.sha256_tree(r_code_files()))}
        if FROZEN_R.exists():
            out["frozen_r_code_sha256"] = json.loads(FROZEN_R.read_text()).get("r_code_sha256")
        _SHAS[key] = out
    return dict(_SHAS[key])


def set_items_path(items_path: Path | None) -> None:
    """The bank this process runs on (main sets it), stamped on rows whose caller passes no ``items_path``."""
    global ITEMS_PATH
    ITEMS_PATH = Path(items_path) if items_path is not None else None


def items_stamp(items_path: Path | None = None) -> dict[str, Any]:
    """``r_shas`` of the bank a row came from (``items_path``, else the process's ``ITEMS_PATH``). With neither known the
    fields are present and None, never another bank's sha (reader_lo / kway keep ``r_shas``' items_r default)."""
    p = items_path or ITEMS_PATH
    if p is None:
        return {"items_file": None, "items_sha256": None}
    return r_shas(p)


# ------------------------------------------------------------------ rendering
def truncate_text(tokenizer: Any, text: str, max_tokens: int = MAX_TOKENS) -> str:
    text_ids = list(tokenizer(text, add_special_tokens=False)["input_ids"])
    return tokenizer.decode(text_ids[:max_tokens]) if len(text_ids) > max_tokens else text


def render_ids(tokenizer: Any, text: str, render: str, max_tokens: int = MAX_TOKENS, system: str | None = None,
               messages: list[dict[str, str]] | None = None) -> list[int]:
    """chat: the text as the user turn (after the item's system turn, if any), thinking off, assistant onset appended
    (read at the onset); with ``messages`` (an item's ``capture_messages``: earlier turns + the text as the last user
    turn) the whole conversation is rendered and ``text`` must equal the last user turn (WS12 ReaderBench). raw: the
    bare text, no special tokens, no system turn (read at its last token). Long texts are cut to ``max_tokens`` text
    tokens BEFORE the chat template is applied, so the same text tokens feed both renders (not applied to ``messages``,
    whose texts are short by construction)."""
    if messages:
        if messages[-1]["role"] != "user" or messages[-1]["content"] != text:
            raise ValueError("capture_messages must end with the user turn equal to prompt_text")
        if system:
            raise ValueError("an item carries either a system turn or capture_messages, not both")
    text = truncate_text(tokenizer, text, max_tokens)
    if render == "raw":
        return list(tokenizer(text, add_special_tokens=False)["input_ids"])
    if render == "chat":
        return M.chat_ids(tokenizer, list(messages)) if messages else M.render_item(tokenizer, text, system)
    raise ValueError(render)


def item_render_ids(tokenizer: Any, item: dict[str, Any], render: str, max_tokens: int = MAX_TOKENS) -> list[int]:
    """``render_ids`` with the item's own system turn / earlier messages."""
    return render_ids(tokenizer, item["prompt_text"], render, max_tokens, system=item.get("system"), messages=item.get("capture_messages"))


def onset_token(tokenizer: Any) -> int:
    """The last token of every chat render: the assistant onset after the empty think block."""
    return M.render_item(tokenizer, "", None)[-1]


def prompt_only_ids(tokenizer: Any, item: dict[str, Any], max_tokens: int = MAX_TOKENS) -> list[int]:
    text = truncate_text(tokenizer, item["prompt_text"], max_tokens)
    p = item["primary"]
    if p.get("sided") == "kway":
        opts = "\n".join(f"- {c}" for c in p["candidates"])
        user = D.PROMPT_ONLY_KWAY_TEMPLATE.format(text=text, question=p["question"], options=opts)
    else:
        user = D.PROMPT_ONLY_FC_TEMPLATE.format(text=text, question=p["question"], pos=p["candidates"][0], neg=p["candidates"][1])
    msgs = item.get("capture_messages")
    if msgs:   # earlier turns stay; the forced-choice prompt replaces the last user turn
        return M.chat_ids(tokenizer, list(msgs[:-1]) + [{"role": "user", "content": user}])
    return M.render_item(tokenizer, user, item.get("system"))


def logit_lens_tokens(tokenizer: Any, primary: dict[str, Any]) -> dict[str, Any]:
    """The two first tokens the logit lens compares (the Y1 convention, ``core.edit.first_token_candidates``): the first
    spelling (bare, space, capitalised, lower) whose first tokens DIFFER between pos and neg; when every spelling shares
    the first token ("a Democrat" / "a Republican") the dataset's ``jlens`` short forms are tried; else unscorable."""
    pos, neg = primary["candidates"][0], primary["candidates"][1]
    ft = E.first_token_candidates(tokenizer, pos, neg)
    source = "candidates"
    if ft["unscorable"]:
        jl = primary.get("jlens") or [None, None]
        if jl[0] and jl[1]:
            ft = E.first_token_candidates(tokenizer, jl[0], jl[1])
            source = "jlens_forms"
    return {"unscorable": bool(ft["unscorable"]), "form": ft.get("form"), "source": source if not ft["unscorable"] else None,
            "first_pos": ft.get("first_A"), "first_neg": ft.get("first_B"), "text_pos": ft.get("text_A"), "text_neg": ft.get("text_B"),
            "reason": ft.get("reason")}


def first_token_ids(tokenizer: Any, cand: str) -> dict[str, int]:
    """First token of a candidate in its bare and leading-space spellings (kept for WS5's ``planted.py``; the
    collector itself uses ``logit_lens_tokens``)."""
    out = {}
    for form, text in (("bare", cand), ("space", " " + cand)):
        ids = tokenizer(text, add_special_tokens=False)["input_ids"]
        if ids:
            out[form] = int(ids[0])
    return out


# ------------------------------------------------------------------ read_position (E6 / E14; HANDOFF item 5)
def text_offsets(tokenizer: Any, text: str) -> tuple[list[int], list[tuple[int, int]]]:
    """Token ids of ``text`` (no special tokens) and each token's [start, end) character span in ``text``: the fast
    tokenizer's ``offset_mapping`` when available, else the spans implied by decoding growing prefixes."""
    ids = list(tokenizer(text, add_special_tokens=False)["input_ids"])
    try:
        enc = tokenizer(text, add_special_tokens=False, return_offsets_mapping=True)
        offs = [(int(a), int(b)) for a, b in enc["offset_mapping"]]
        if len(offs) == len(ids) and list(enc["input_ids"]) == ids:
            return ids, offs
    except (KeyError, TypeError, NotImplementedError, ValueError):
        pass
    offs, prev = [], 0
    for k in range(len(ids)):
        end = len(tokenizer.decode(ids[: k + 1]))
        offs.append((prev, max(end, prev)))
        prev = max(end, prev)
    return ids, offs


def locate_text(render_ids_: list[int], text_ids: list[int]) -> tuple[int, int] | None:
    """(start, drop): ``render_ids_[start + k - drop] == text_ids[k]`` for k >= drop, the LAST occurrence of the text's
    token run inside a render; ``drop`` = 1 when only the first text token merged with the template (BPE boundary)."""
    for drop in (0, 1):
        sub = text_ids[drop:]
        if not sub:
            continue
        n = len(sub)
        for s in range(len(render_ids_) - n, -1, -1):
            if render_ids_[s: s + n] == sub:
                return s, drop
    return None


def resolve_read_position(tokenizer: Any, item: dict[str, Any], render: str, max_tokens: int = MAX_TOKENS) -> dict[str, Any] | None:
    """The token index to read for an item carrying ``read_position`` (None when the item has none). Contract (WS11
    HANDOFF item 5): the LAST token whose offset span over ``prompt_text`` (before the chat template) overlaps
    ``prompt_text[char_start:char_end]``; mapped into the render (raw: the text's own index; chat: inside the user
    turn). ``fallback`` ("last_text_token") is used when the span cannot be located (truncated away, or the text run not
    found in the render); ``status`` says which. WS10's pre-contract shape (``kind: hop1_span_end``, ``span_text``) is
    accepted; an unknown ``kind`` is recorded as ``unresolved``."""
    rp = item.get("read_position")
    if not rp:
        return None
    out: dict[str, Any] = {"kind": rp.get("kind"), "role": rp.get("role"), "text": rp.get("text", rp.get("span_text")),
                           "char_start": rp.get("char_start"), "char_end": rp.get("char_end"), "token_index": None, "status": "unresolved",
                           "fallback": rp.get("fallback", "last_text_token")}
    if rp.get("kind") not in RP_KINDS or rp.get("char_start") is None or rp.get("char_end") is None:
        return out
    text = truncate_text(tokenizer, item["prompt_text"], max_tokens)
    text_ids, offs = text_offsets(tokenizer, text)
    i, j = int(rp["char_start"]), int(rp["char_end"])
    hits = [k for k, (a, b) in enumerate(offs) if a < j and b > i]
    t_star = hits[-1] if hits else None
    if render == "raw":
        start, drop, last_text = 0, 0, len(text_ids) - 1
    else:
        ids = M.render_item(tokenizer, text, item.get("system"))
        loc = locate_text(ids, text_ids)
        if loc is None:
            return out
        start, drop = loc
        last_text = start + len(text_ids) - 1 - drop
    if t_star is not None:
        out.update(token_index=start + t_star - drop, status="span")
    elif out["fallback"] == "last_text_token":
        out.update(token_index=last_text, status="fallback_last_text_token")
    return out


# ------------------------------------------------------------------ batched capture
def pad_rows(rows: list[list[int]], pad: int) -> tuple[Any, Any]:
    """Right-padded ids and the attention mask (CPU long tensors)."""
    import torch

    n = max(len(r) for r in rows)
    ids = torch.full((len(rows), n), pad, dtype=torch.long)
    mask = torch.zeros_like(ids)
    for i, r in enumerate(rows):
        ids[i, : len(r)] = torch.tensor(r)
        mask[i, : len(r)] = 1
    return ids, mask


def capture_batch_positions(model: Any, rows: list[list[int]], layers: list[int], pad: int, positions: list[list[int]]) -> dict[int, Any]:
    """One forward over right-padded ``rows``; the block output at each row's own ``positions[i]`` (same count per
    row), per layer, as fp32 CPU [B, P, d]. Right padding + attention mask leaves the real positions untouched (causal
    attention; Qwen3.5's linear-attention blocks zero the padded rows and position ids run from 0 either way)."""
    import torch

    blks = M.blocks(model)
    ids, mask = pad_rows(rows, pad)
    P = len(positions[0])
    if any(len(p) != P for p in positions) or any(not 0 <= q < len(r) for r, p in zip(rows, positions) for q in p):
        raise ValueError("positions must have the same count per row and lie inside each row")
    pos = torch.tensor(positions)                       # [B, P]
    dev = next(model.parameters()).device
    ids, mask = ids.to(dev), mask.to(dev)
    store: dict[int, Any] = {}
    handles = []

    def make(L: int):
        def hook(_m, _i, out):
            h = out[0] if isinstance(out, tuple) else out
            b = torch.arange(h.shape[0], device=h.device)[:, None]
            store[L] = h[b, pos.to(h.device), :].detach().float().cpu()
        return hook

    for L in layers:
        if not 0 <= L < len(blks):
            raise ValueError(f"layer {L} out of range for a {len(blks)}-block model")
        handles.append(blks[L].register_forward_hook(make(L)))
    try:
        with torch.no_grad(), M.disable_adapter_ctx(model):
            try:
                model(input_ids=ids, attention_mask=mask, use_cache=False, logits_to_keep=1)
            except TypeError:
                model(input_ids=ids, attention_mask=mask, use_cache=False)
    finally:
        for h in handles:
            h.remove()
    missing = [L for L in layers if L not in store]
    if missing:
        raise RuntimeError(f"hooks on blocks {missing} did not fire")
    return store


def capture_batch(model: Any, rows: list[list[int]], layers: list[int], pad: int) -> dict[int, Any]:
    """The block output at each row's LAST REAL token, per layer, as fp32 CPU [B, d] (one forward)."""
    got = capture_batch_positions(model, rows, layers, pad, [[len(r) - 1] for r in rows])
    return {L: v[:, 0] for L, v in got.items()}


def _first_token_lists(spec: Any, n: int) -> list[list[int]]:
    """Per-row lists of first-token ids from an int, a {form: id} dict (WS5's ``first_token_ids``), or a per-row list."""
    if isinstance(spec, dict):
        return [sorted(set(int(v) for v in spec.values()))] * n
    if isinstance(spec, (int, np.integer)):
        return [[int(spec)]] * n
    out = []
    for x in spec:
        out.append(sorted(set(int(v) for v in x.values())) if isinstance(x, dict) else ([int(x)] if isinstance(x, (int, np.integer)) else [int(v) for v in x]))
    return out


def logit_lens_rows(target: M.Target, states: dict[int, Any], first_pos: Any, first_neg: Any) -> list[dict[int, dict[str, float]]]:
    """Per item (row of the states), per layer: lp of ITS two first tokens under final norm + W_U (as Y1's
    ``logit_lens_margins``, batched; the candidates may differ per item). ``first_pos`` / ``first_neg``: one id per row,
    or a single id / {form: id} dict for every row (max over the forms, the WS5 call form)."""
    import torch

    norm = M.final_norm(target.model)
    w_u = M.unembed_weight(target.model)
    dev, dt = w_u.device, w_u.dtype
    layers = sorted(states)
    n = states[layers[0]].shape[0]
    fp, fn = _first_token_lists(first_pos, n), _first_token_lists(first_neg, n)
    if len(fp) != n or len(fn) != n:
        raise ValueError(f"{n} states but {len(fp)} / {len(fn)} first tokens")
    out: list[dict[int, dict[str, float]]] = [dict() for _ in range(n)]
    with torch.no_grad():
        for L in layers:
            z = norm(states[L].to(dev, dt)[:, None, :])[:, 0]
            lp = torch.log_softmax((z @ w_u.T).float(), dim=-1).cpu()
            for i in range(n):
                a = max(float(lp[i, t]) for t in fp[i])
                b = max(float(lp[i, t]) for t in fn[i])
                out[i][L] = {"lp_pos": a, "lp_neg": b, "margin": a - b}
    return out


def stable_offset(name: str) -> int:
    """A process-independent small integer from a name (Python's hash() is salted per process)."""
    import hashlib

    return int(hashlib.sha256(name.encode("utf-8")).hexdigest()[:6], 16)


def derangement(n: int, rng: np.random.Generator) -> np.ndarray:
    """A random permutation with NO fixed point (a single n-cycle through a random ordering), so the shuffled
    control never scores an item on its own state. n < 2 returns the identity (nothing to shuffle)."""
    if n < 2:
        return np.arange(n)
    p = rng.permutation(n)
    perm = np.empty(n, dtype=int)
    perm[p] = p[(np.arange(n) + 1) % n]
    return perm


def state_file(dataset: str, render: str, layer: int, position: str = "last") -> Path:
    return STATES_DIR / dataset / f"{render}_L{layer}{'' if position == 'last' else '_' + position}.npy"


def index_file(dataset: str) -> Path:
    return STATES_DIR / dataset / "index.json"


def states_done(dataset: str, render: str, layers: tuple[int, ...] = LAYERS) -> bool:
    return index_file(dataset).exists() and all(state_file(dataset, render, L).exists() for L in layers)


def load_states(dataset: str, render: str, layer: int, position: str = "last") -> tuple[np.ndarray, list[str]]:
    """fp32 [N, d] and the item ids in row order (analysis and readers share this loader). ``position="rp"`` loads the
    read_position states (NaN rows for items without one)."""
    idx = json.loads(index_file(dataset).read_text())["item_ids"]
    X = np.load(state_file(dataset, render, layer, position)).astype(np.float32)
    if X.shape[0] != len(idx):
        raise RuntimeError(f"{dataset} {render} L{layer} {position}: {X.shape[0]} rows for {len(idx)} items")
    return X, idx


def ordered_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The row order of every state file: test items first, then pool, each by item_id."""
    return sorted(items, key=lambda it: (it["split"] != "test", it["item_id"]))


def write_index(dataset: str, items: list[dict[str, Any]], layers: tuple[int, ...], renders: tuple[str, ...]) -> dict[str, Any]:
    """Create states/<dataset>/index.json or check that the existing one lists the same items in the same order
    (a changed bank is an error, never an overwrite)."""
    p = index_file(dataset)
    ids = [it["item_id"] for it in items]
    if p.exists():
        idx = json.loads(p.read_text())
        if idx["item_ids"] != ids:
            raise RuntimeError(f"{p}: cached states belong to a different item list; delete {p.parent} to recapture")
        changed = False
        for r in renders:
            if r not in idx["renders"]:
                idx["renders"].append(r)
                changed = True
        if changed:
            p.write_text(json.dumps(idx, indent=1))
        return idx
    p.parent.mkdir(parents=True, exist_ok=True)
    idx = {"dataset": dataset, "item_ids": ids, "splits": [it["split"] for it in items], "labels": [it["label"] for it in items],
           "layers": list(layers), "renders": list(renders), "max_tokens": MAX_TOKENS, "n_tokens": {}, "read_token": {},
           "state_dtype": {}, "n_system": sum(1 for it in items if it.get("system")),
           "n_messages": sum(1 for it in items if it.get("capture_messages")),
           "n_model_labelled": sum(1 for it in items if it["primary"].get("label_source") == "model"),
           "per_item_candidates": len({tuple(it["primary"]["candidates"]) for it in items}) > 1,
           "has_read_position": any(it.get("read_position") for it in items), "read_position_token": {}, "read_position_status": {},
           **row_meta(), "created_at": now_iso()}
    p.write_text(json.dumps(idx, indent=1))
    return idx


def capture_dataset(target: M.Target, dataset: str, items: list[dict[str, Any]], renders: tuple[str, ...] = RENDERS,
                    layers: tuple[int, ...] = LAYERS, batch: int = CAPTURE_BATCH, items_path: Path | None = None) -> dict[str, float]:
    """All items of one dataset (test first, then pool), the requested renders, every layer, into .npy files; the
    logit-lens rows for each item's candidates' first tokens into logit_lens.jsonl; for items carrying
    ``read_position``, the state at the resolved token too (``<render>_L<layer>_rp.npy``, same forward). Skips renders
    already on disk. Returns the wall-clock per render captured. ``items_path``: the bank stamped on the rows
    (``items_stamp``; default the process's ``ITEMS_PATH``)."""
    import torch

    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    items = ordered_items(items)
    shas = items_stamp(items_path)
    idx = write_index(dataset, items, layers, renders)
    kway = items[0]["primary"].get("sided") == "kway"
    has_rp = any(it.get("read_position") for it in items)
    ll_cache: dict[tuple[Any, ...], dict[str, Any]] = {}

    def ll_tokens(it: dict[str, Any]) -> dict[str, Any]:
        """The logit lens's two first tokens for THIS item (candidates may differ per item: KHOP, R-C2)."""
        p = it["primary"]
        key = (tuple(p["candidates"][:2]), tuple(p.get("jlens") or [None, None]))
        if key not in ll_cache:
            ll_cache[key] = logit_lens_tokens(tok, p)
        return ll_cache[key]

    onset = onset_token(tok)
    walls: dict[str, float] = {}
    for render in renders:
        if states_done(dataset, render, layers):
            continue
        led = ledger(f"capture_{render}", batch=batch, layers=list(layers))
        acc: dict[int, list[Any]] = {L: [] for L in layers}
        acc_rp: dict[int, list[Any]] = {L: [] for L in layers}
        n_tokens: list[int] = []
        rp_tok: list[int | None] = []
        rp_status: list[str | None] = []
        wall = 0.0
        for s in range(0, len(items), batch):
            chunk = items[s: s + batch]
            rows = [item_render_ids(tok, it, render) for it in chunk]
            if render == "chat" and any(r[-1] != onset for r in rows):
                raise RuntimeError(f"{dataset}: a chat render does not end at the assistant onset token {onset}")
            n_tokens += [len(r) for r in rows]
            rps = [resolve_read_position(tok, it, render) for it in chunk] if has_rp else [None] * len(chunk)
            for r, rp in zip(rows, rps):
                t = rp["token_index"] if rp else None
                if t is not None and not 0 <= t < len(r):
                    rp.update(token_index=None, status="out_of_range")
                    t = None
                rp_tok.append(t)
                rp_status.append(rp["status"] if rp else None)
            positions = [[len(r) - 1, (rp["token_index"] if rp and rp["token_index"] is not None else len(r) - 1)] for r, rp in zip(rows, rps)]
            order = sorted(range(len(rows)), key=lambda i: len(rows[i]))  # sort by length inside the chunk to limit padding
            with timed_call() as st:
                got_p = capture_batch_positions(target.model, [rows[i] for i in order], list(layers), pad, [positions[i] for i in order])
            inv = torch.as_tensor(np.argsort(order))   # restore the chunk order
            got = {L: got_p[L][inv, 0] for L in layers}
            for L in layers:
                acc[L].append(got[L])
                if has_rp:
                    rp_states = got_p[L][inv, 1].clone()
                    for i, rp in enumerate(rps):
                        if not rp or rp["token_index"] is None:
                            rp_states[i] = float("nan")
                    acc_rp[L].append(rp_states)
            if not kway:
                fts = [ll_tokens(it) for it in chunk]
                ok = [i for i, ft in enumerate(fts) if not ft["unscorable"]]
                ll: list[dict[int, dict[str, float]]] = [{} for _ in chunk]
                if ok:
                    sub = logit_lens_rows(target, {L: got[L][torch.as_tensor(ok)] for L in layers},
                                          [fts[i]["first_pos"] for i in ok], [fts[i]["first_neg"] for i in ok])
                    for i, row in zip(ok, sub):
                        ll[i] = row
                for it, ft, row in zip(chunk, fts, ll):
                    key = f"ll|{dataset}|{render}|{it['item_id']}"
                    if key in done_keys(LL_PATH):
                        continue
                    append_row(LL_PATH, {"key": key, "module": MODULE, "dataset": dataset, "render": render, "item_id": it["item_id"],
                                         "split": it["split"], "label": it["label"], "candidates": it["primary"]["candidates"][:2],
                                         "first_pos": ft["first_pos"], "first_neg": ft["first_neg"],
                                         "form": ft.get("form"), "source": ft.get("source"), "text_pos": ft.get("text_pos"),
                                         "text_neg": ft.get("text_neg"), "unscorable": ft["unscorable"], "reason": ft.get("reason"),
                                         "per_layer": {str(L): v for L, v in row.items()}, **shas, "created_at": now_iso()})
            led.add(sum(len(r) for r in rows), 0, st.wall_s, st.peak_mem_gb)
            wall += st.wall_s
        dtype = "float16"
        arrays = {L: torch.cat(acc[L]) for L in layers}
        if any(not torch.isfinite(a.to(torch.float16)).all() for a in arrays.values()):
            dtype = "float32"   # a state beyond the fp16 range (never seen: block-42 norms are ~70–100); keep full precision
        for L in layers:
            np.save(state_file(dataset, render, L), arrays[L].to(getattr(torch, dtype)).numpy())
            if has_rp:
                np.save(state_file(dataset, render, L, "rp"), torch.cat(acc_rp[L]).to(getattr(torch, dtype)).numpy())
        idx = json.loads(index_file(dataset).read_text())
        idx.setdefault("n_tokens", {})[render] = n_tokens
        idx.setdefault("read_token", {})[render] = M.token_str(tok, onset) if render == "chat" else "last text token"
        idx.setdefault("state_dtype", {})[render] = dtype
        idx["has_read_position"] = has_rp
        if has_rp:
            idx.setdefault("read_position_token", {})[render] = rp_tok
            idx.setdefault("read_position_status", {})[render] = rp_status
        index_file(dataset).write_text(json.dumps(idx, indent=1))
        walls[render] = wall
        n_rp = sum(t is not None for t in rp_tok)
        print(f"[r/capture] {dataset} {render}: {len(items)} items × {len(layers)} layers in {wall:.1f}s"
              + (f"; read_position resolved for {n_rp}/{len(items)}" if has_rp else ""), flush=True)
    return walls


# ------------------------------------------------------------------ prompt-only forced choice (the model's own report)
def teacher_forced_lp(model: Any, rows: list[list[int]], head_lens: list[int], pad: int, device: Any) -> list[float]:
    """Sum of log p(candidate tokens | head) per row, with a DIFFERENT head length per row (right padding, attention
    mask; ``logits_to_keep`` from the shortest head on, one fp32 log-softmax per row over its own candidate
    positions). With equal heads this is exactly ``scoring_lo._summed_logprobs`` (same forward, same slice)."""
    import torch

    ids, mask = pad_rows(rows, pad)
    n = ids.shape[1]
    ids, mask = ids.to(device), mask.to(device)
    keep = n - min(head_lens) + 1   # logits from the last token of the shortest head on: position u predicts ids[u+1]
    out: list[float] = []
    with torch.no_grad():
        logits = LO._forward_logits(model, ids, mask, keep)
        off = n - logits.shape[1]
        for i, r in enumerate(rows):
            h, L = head_lens[i], len(r)
            lp = torch.log_softmax(logits[i, h - 1 - off: L - 1 - off].float(), dim=-1)
            tgt = ids[i, h:L]
            out.append(float(lp.gather(-1, tgt[:, None]).sum()))
    return out


def collect_prompt_only(target: M.Target, dataset: str, items: list[dict[str, Any]], batch: int = 32,
                        ledger_path: Path | None = None, items_path: Path | None = None) -> int:
    """Teacher-forced LO = lp(pos) − lp(neg) of the base model (adapter off) after the assistant onset of the
    forced-choice render; every candidate of an item in the same forward batch, several items per batch.
    k-way items: one ``lp`` entry per candidate. ``greedy`` = argmax over the candidates (the MODEL answer).
    ``ledger_path``: flush this call's ledger row there at once (WS5's call form); otherwise ``flush_ledgers`` does.
    ``items_path``: the bank stamped on the rows (``items_stamp``; default the process's ``ITEMS_PATH``)."""
    todo = [it for it in items if f"po|{dataset}|{it['item_id']}" not in done_keys(PO_PATH)]
    if not todo:
        return 0
    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    dev = next(target.model.parameters()).device
    shas = items_stamp(items_path)
    led = ledger("prompt_only", batch=batch)
    n = 0
    k = len(todo[0]["primary"]["candidates"])
    kway = todo[0]["primary"].get("sided") == "kway"
    per = max(1, batch // k)
    for s in range(0, len(todo), per):
        chunk = todo[s: s + per]
        heads = [prompt_only_ids(tok, it) for it in chunk]
        rows, head_lens = [], []
        for it, head in zip(chunk, heads):
            for c in it["primary"]["candidates"]:
                rows.append(head + LO.encode(tok, c))
                head_lens.append(len(head))
        with timed_call() as st:
            with M.disable_adapter_ctx(target.model):
                lps_all = teacher_forced_lp(target.model, rows, head_lens, pad, dev)
        j0 = 0
        for it, head in zip(chunk, heads):
            cands = it["primary"]["candidates"]
            lps = lps_all[j0: j0 + len(cands)]
            j0 += len(cands)
            row = {"key": f"po|{dataset}|{it['item_id']}", "module": MODULE, "dataset": dataset, "item_id": it["item_id"],
                   "split": it["split"], "label": it["label"], "candidates": cands, "lp": lps,
                   "greedy": int(np.argmax(lps)), "n_head_tokens": len(head), "adapter": "none", "system": bool(it.get("system")),
                   "template": "kway" if kway else "fc", **shas, "created_at": now_iso()}
            if not kway:
                row.update(lp_pos=lps[0], lp_neg=lps[1], lo=lps[0] - lps[1], model_says_pos=bool(lps[0] > lps[1]))
            append_row(PO_PATH, row)
            n += 1
        led.add(sum(len(r) for r in rows), 0, st.wall_s, st.peak_mem_gb)
    if ledger_path is not None:
        _LEDGERS.pop("prompt_only").flush(ledger_path)
    print(f"[r/prompt_only] {dataset}: {n} items", flush=True)
    return n


# ------------------------------------------------------------------ model labels (facts whose label is the model's own behaviour)
REFUSAL_MARKERS = ("i can't", "i cannot", "i can not", "i won't", "i will not", "i'm sorry", "i am sorry", "sorry, but", "i'm not able",
                   "i am not able", "not able to help", "can't help", "cannot help", "can't assist", "cannot assist", "i must decline",
                   "i'm unable", "i am unable", "not something i can", "against my", "i'd rather not", "i can't provide", "cannot provide")
ABSTAIN_MARKERS = ("i don't know", "i do not know", "no way to know", "not known", "unknown", "cannot know", "can't know", "no record",
                   "impossible to know", "not possible to know", "no one knows", "nobody knows", "isn't known", "is not known",
                   "there is no information", "no information", "not documented", "i'm not sure", "i am not sure", "cannot be determined",
                   "can't be determined", "no reliable", "not recorded", "unanswerable", "i don't have", "i do not have")
MODEL_LABEL_MAX_NEW = 24


def greedy_continuations(model: Any, tokenizer: Any, rows: list[list[int]], max_new_tokens: int = MODEL_LABEL_MAX_NEW) -> list[str]:
    """Greedy continuation of each row (LEFT padding + attention mask, adapter off), decoded without special tokens."""
    import torch

    pad = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
    n = max(len(r) for r in rows)
    ids = torch.full((len(rows), n), pad, dtype=torch.long)
    mask = torch.zeros_like(ids)
    for i, r in enumerate(rows):
        ids[i, n - len(r):] = torch.tensor(r)
        mask[i, n - len(r):] = 1
    dev = next(model.parameters()).device
    with torch.no_grad(), M.disable_adapter_ctx(model):
        out = model.generate(input_ids=ids.to(dev), attention_mask=mask.to(dev), max_new_tokens=max_new_tokens, do_sample=False,
                             pad_token_id=pad, eos_token_id=getattr(tokenizer, "eos_token_id", None))
    new = out[:, n:].tolist()
    eos = getattr(tokenizer, "eos_token_id", None)
    texts = []
    for seq in new:
        if eos is not None and eos in seq:
            seq = seq[: seq.index(eos)]
        texts.append(tokenizer.decode(seq, skip_special_tokens=True))
    return texts


def _first_mention(text: str, cands: list[str]) -> int | None:
    """Index of the candidate that occurs first in ``text`` (whole word, case-insensitive); None when none does."""
    import re

    best: tuple[int, int] | None = None
    for i, c in enumerate(cands):
        m = re.search(r"(?<!\w)" + re.escape(c) + r"(?!\w)", text, flags=re.IGNORECASE)
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), i)
    return None if best is None else best[1]


def model_label_from_text(item: dict[str, Any], text: str) -> dict[str, Any]:
    """The model's behaviour as a label for ONE item. Rules by dataset family (ReaderBench INTERNAL / CONTEXT):
      *refusal*   label 1 ("refuse") iff a refusal marker opens the continuation (first 160 chars)
      *abstain*   label 1 ("says it does not know") iff an abstention marker occurs in the continuation
      otherwise   the candidate mentioned first in the continuation; label 1 iff it is candidates[0]
    ``label`` is None when no rule fires (left to the judge); ``rule`` names the rule."""
    p = item["primary"]
    cands = list(p["candidates"])
    low = text.lower()
    ds = item["dataset"]
    if "refusal" in ds:
        hit = any(m in low[:160] for m in REFUSAL_MARKERS)
        return {"label": 1 if hit else 0, "model_answer": cands[0] if hit else cands[1], "rule": "refusal_markers", "marker_hit": hit}
    if "abstain" in ds:
        hit = any(m in low for m in ABSTAIN_MARKERS)
        return {"label": 1 if hit else 0, "model_answer": cands[0] if hit else cands[1], "rule": "abstain_markers", "marker_hit": hit}
    i = _first_mention(text, cands)
    if i is None:
        return {"label": None, "model_answer": None, "rule": "first_mentioned_candidate", "marker_hit": False}
    return {"label": 1 if i == 0 else 0, "model_answer": cands[i], "rule": "first_mentioned_candidate", "marker_hit": True}


def collect_model_labels(target: M.Target, dataset: str, items: list[dict[str, Any]], batch: int = 16,
                         max_new_tokens: int = MODEL_LABEL_MAX_NEW, items_path: Path | None = None) -> int:
    """For items with ``primary.label_source == "model"``: the base model's greedy continuation of the item's own chat
    render (system turn / earlier messages included) and the label derived from it (``model_label_from_text``). One row
    per item, resumable; the provisional construction label is kept alongside as ``provisional_label``. Rows are stamped
    like prompt_only rows: ``row_meta`` (run_id, run_kind, code_sha256, pod, shard, git_sha) and ``items_stamp(items_path)``
    (items_file, items_sha256; WS12's finding, 2026-10-20)."""
    todo = [it for it in items if it["primary"].get("label_source") == "model" and f"ml|{dataset}|{it['item_id']}" not in done_keys(ML_PATH)]
    if not todo:
        return 0
    tok = target.tokenizer
    shas = items_stamp(items_path)
    led = ledger("model_labels", batch=batch, max_new_tokens=max_new_tokens)
    n = 0
    for s in range(0, len(todo), batch):
        chunk = todo[s: s + batch]
        rows = [item_render_ids(tok, it, "chat") for it in chunk]
        with timed_call() as st:
            texts = greedy_continuations(target.model, tok, rows, max_new_tokens)
        for it, row_ids, text in zip(chunk, rows, texts):
            lab = model_label_from_text(it, text)
            append_row(ML_PATH, {"key": f"ml|{dataset}|{it['item_id']}", "module": MODULE, "dataset": dataset, "item_id": it["item_id"],
                                 "split": it["split"], "provisional_label": it["label"], "model_label": lab["label"],
                                 "model_answer": lab["model_answer"], "rule": lab["rule"], "marker_hit": lab["marker_hit"],
                                 "agrees_with_provisional": None if lab["label"] is None else lab["label"] == it["label"],
                                 "candidates": it["primary"]["candidates"], "greedy_text": text, "n_prompt_tokens": len(row_ids),
                                 "max_new_tokens": max_new_tokens, "adapter": "none", **shas, "created_at": now_iso()})
            n += 1
        led.add(sum(len(r) for r in rows), len(chunk) * max_new_tokens, st.wall_s, st.peak_mem_gb)
    print(f"[r/model_labels] {dataset}: {n} items", flush=True)
    return n


# ------------------------------------------------------------------ R-E INTERNAL relabel (WS10 `beyond_text`: the model's own behaviour as the key)
RE_RELABEL_MAX_NEW = 32


def re_relabel_classifiers() -> dict[str, Any]:
    from projects.g_agreement.r_bench import beyond_text as BT

    return BT.CLASSIFIERS


def load_re_generations(dataset: str) -> dict[str, str]:
    """item_id -> greedy continuation from every ``re_relabel*.jsonl`` under ``R_DIR`` (any shard or suffix: phase B
    reads what phase A wrote, whichever pod wrote it)."""
    gens: dict[str, str] = {}
    for p in sorted(R_DIR.glob("re_relabel*.jsonl")):
        for line in p.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("dataset") == dataset:
                gens[r["item_id"]] = r["greedy_text"]
    return gens


def collect_re_relabel(target: M.Target | None, dataset: str, items: list[dict[str, Any]], batch: int = 16,
                       max_new_tokens: int = RE_RELABEL_MAX_NEW, items_path: Path | None = None) -> tuple[int, list[dict[str, Any]]]:
    """WS10's `re_internal_refuse` / `re_internal_abstain` (HANDOFF): the base model's greedy continuation of each item's
    own chat render (adapter off, ``max_new_tokens`` new tokens) is the behavioural key. Rows go to ``RL_PATH``
    (resumable, key ``rl|<dataset>|<item_id>``); then ``beyond_text.rekey_internal`` rewrites ``label`` and sets
    ``primary.key = "greedy"`` on a copy of the items, which the caller scores. With ``target`` None (phase B) nothing is
    decoded: the items are rekeyed from the rows already on disk, and items without a row keep their design label.
    Datasets outside ``beyond_text.CLASSIFIERS`` — and WS12's ``label_source == "model"`` items, which
    ``collect_model_labels`` owns — are returned unchanged."""
    from projects.g_agreement.r_bench import beyond_text as BT

    clf = BT.CLASSIFIERS.get(dataset)
    if clf is None or any(it["primary"].get("label_source") == "model" for it in items):
        return 0, items
    gens = load_re_generations(dataset)
    todo = [it for it in items if it["item_id"] not in gens]
    n = 0
    if todo and target is not None:
        tok = target.tokenizer
        shas = items_stamp(items_path)
        led = ledger("re_relabel", batch=batch, max_new_tokens=max_new_tokens)
        for s in range(0, len(todo), batch):
            chunk = todo[s: s + batch]
            rows = [item_render_ids(tok, it, "chat") for it in chunk]
            with timed_call() as st:
                texts = greedy_continuations(target.model, tok, rows, max_new_tokens)
            for it, row_ids, text in zip(chunk, rows, texts):
                y = int(clf(text))
                append_row(RL_PATH, {"key": f"rl|{dataset}|{it['item_id']}", "module": MODULE, "dataset": dataset, "item_id": it["item_id"],
                                     "split": it["split"], "design_label": it.get("construction", {}).get("design_label", it["label"]),
                                     "label": y, "classifier": clf.__name__, "key_window": BT.KEY_WINDOW, "greedy_text": text,
                                     "n_prompt_tokens": len(row_ids), "max_new_tokens": max_new_tokens, "adapter": "none",
                                     **shas, "created_at": now_iso()})
                gens[it["item_id"]] = text
                n += 1
            led.add(sum(len(r) for r in rows), len(chunk) * max_new_tokens, st.wall_s, st.peak_mem_gb)
        print(f"[r/re_relabel] {dataset}: {n} items decoded", flush=True)
    rekeyed, summary = BT.rekey_internal(items, gens)
    still_design = [it["item_id"] for it in rekeyed if it["primary"].get("key") != "greedy"]
    if still_design:
        print(f"[r/re_relabel] WARNING {dataset}: {len(still_design)} items have no greedy row yet and keep the design label "
              f"(run phase A on this dataset first)", flush=True)
    return n, rekeyed


# ------------------------------------------------------------------ reader LO on the test split
def family_for(primary: dict[str, Any]) -> str:
    """The NLA template family of ONE item, registered in ``LO.NLA_TEMPLATES``: ``r:<dataset>`` for the dataset's
    spec template (or, for banks without a spec, the first template seen), ``r:<dataset>:t<hash>`` for any other
    template the bank declares per item. Templates may therefore differ per item (WS10–12 banks)."""
    name, tmpl = primary["name"], primary["template"]
    fam = f"r:{name}"
    spec = D.SPECS.get(name) or D.MULTICLASS.get(name)
    base_tmpl = spec.template if spec is not None else LO.NLA_TEMPLATES.get(fam, [tmpl])[0]
    if tmpl != base_tmpl:
        fam = f"r:{name}:t{stable_offset(tmpl):06x}"
    LO.NLA_TEMPLATES[fam] = [tmpl]
    return fam


def register_templates(spec_like: dict[str, Any]) -> str:
    """Backward-compatible alias of ``family_for``."""
    return family_for(spec_like)


def item_pair(reader_name: str, primary: dict[str, Any]) -> tuple[str, str]:
    """The (pos, neg) pair a reader scores for ONE item: the J-lens (and R-lens) get the ``jlens`` short forms where the
    item declares them; everyone else the item's own candidates (which may differ per item)."""
    pos, neg = primary["candidates"][0], primary["candidates"][1]
    if reader_name in ("jlens", "rlens"):
        jl = primary.get("jlens") or [None, None]
        pos = jl[0] or pos
        neg = jl[1] or neg
    return pos, neg


def reader_candidates(reader_name: str, primary: dict[str, Any]) -> tuple[str, str]:
    """Backward-compatible alias of ``item_pair``."""
    return item_pair(reader_name, primary)


ROW_EXTRA = ("per_template", "variants_A", "variants_B", "best_A", "best_B", "reason", "n_tokens_A", "n_tokens_B", "format",
             "layer_in_prompt", "marker_index", "adapter_name")


def _row_extra(r: dict[str, Any]) -> dict[str, Any]:
    return {k: r[k] for k in ROW_EXTRA if k in r}


def base_name(reader: Any) -> str:
    """The reader family of a (possibly alpha-variant) reader: ``olens_a0.5x`` -> ``olens``."""
    return getattr(reader, "base_name", reader.name)


def score_pairs(reader: Any, H: Any, pairs: list[tuple[str, str]], fam: str, layer: int, batch: int = 32,
                one_sided: bool = False) -> list[dict[str, Any]]:
    """``scoring_lo.score_lo`` on one (pos, neg) pair PER STATE, with the Phase R sidedness rule for the J-lens: each
    candidate is scored on its OWN single-token variants, so a one-sided fact ("living room" vs "no such phrase")
    keeps s_pos when the negative has no single-token form; ``unscorable`` then means "s_pos missing" (one-sided) or
    "either side missing" (two-sided) and ``lo`` is None whenever a side is missing. The other readers score both
    candidates of a state in one forward batch exactly as before."""
    if H.shape[0] != len(pairs):
        raise ValueError(f"{H.shape[0]} states but {len(pairs)} pairs")
    if not isinstance(reader, R.JLensReader):
        rows = LO.score_lo(reader, H, pairs, fam, layer=layer, batch=batch)
        for r in rows:
            r["reader"] = reader.name
        return rows
    ra = LO.score_lo(reader, H, [(a, a) for a, _ in pairs], fam, layer=layer, batch=batch)
    rb = LO.score_lo(reader, H, [(b, b) for _, b in pairs], fam, layer=layer, batch=batch)
    out = []
    for (pos, neg), a, b in zip(pairs, ra, rb):
        lp_a, lp_b = a["lp_A"], b["lp_A"]
        lo = (lp_a - lp_b) if (lp_a is not None and lp_b is not None) else None
        unsc = (lp_a is None) if one_sided else (lo is None)
        row = {"reader": reader.name, "cand_A": pos, "cand_B": neg, "family": fam, "lo": lo, "lp_A": lp_a, "lp_B": lp_b,
               "templates": a["templates"], "format": a.get("format", "cosine"), "unscorable": unsc,
               "variants_A": a.get("variants_A"), "variants_B": b.get("variants_A")}
        if "best_A" in a:
            row["best_A"] = a["best_A"]
        if "best_A" in b:
            row["best_B"] = b["best_A"]
        if lp_a is None or lp_b is None:
            row["reason"] = "no single-token variant for " + ("A" if lp_a is None else "") + ("B" if lp_b is None else "")
        out.append(row)
    return out


def score_pair(reader: Any, H: Any, pos: str, neg: str, fam: str, sided: str, layer: int, batch: int = 32) -> list[dict[str, Any]]:
    """One pair for every state (the dataset-level case)."""
    return score_pairs(reader, H, [(pos, neg)] * H.shape[0], fam, layer, batch, one_sided=(sided == "one"))


def score_items(reader: Any, H: Any, items: list[dict[str, Any]], layer: int, batch: int = 32,
                cand_index: int | None = None, return_groups: bool = False) -> Any:
    """Score state ``H[i]`` against ITEM i's own candidates (and template family), grouping the forward batches by
    (family, sidedness) so each ``score_lo`` call has one family. ``cand_index`` = k-way mode: candidate i of each
    item scored one-sided in the pair (c_i, c_{i+1}); rows then carry ``lp`` = that candidate's one-sided score.
    ``return_groups``: also return the (family, item indices) groups in the order the forwards ran (the E3 hook)."""
    if H.shape[0] != len(items):
        raise ValueError(f"{H.shape[0]} states but {len(items)} items")
    groups: dict[tuple[str, bool], list[int]] = {}
    fams = [family_for(it["primary"]) for it in items]
    for i, it in enumerate(items):
        one = it["primary"].get("sided") in ("one", "kway") if cand_index is None else True
        groups.setdefault((fams[i], one), []).append(i)
    out: list[dict[str, Any] | None] = [None] * len(items)
    order: list[tuple[str, list[int]]] = []
    for (fam, one), idx in groups.items():
        order.append((fam, list(idx)))
        pairs = []
        for i in idx:
            p = items[i]["primary"]
            if cand_index is None:
                pairs.append(item_pair(base_name(reader), p))
            else:
                cands = p["candidates"]
                pairs.append((cands[cand_index], cands[(cand_index + 1) % len(cands)]))
        rows = score_pairs(reader, H[idx], pairs, fam, layer, batch, one_sided=one)
        for i, r in zip(idx, rows):
            if cand_index is not None:
                r = {**r, "lp": r["lp_A"], "unscorable": r["lp_A"] is None, "pair_partner": r["cand_B"]}
            out[i] = r
    rows_out = [r for r in out if r is not None]
    return (rows_out, order) if return_groups else rows_out


def score_candidate(reader: Any, H: Any, cand: str, partner: str, fam: str, layer: int, batch: int = 32) -> list[dict[str, Any]]:
    """One-sided score of ``cand`` on every state (dataset-level k-way case)."""
    rows = score_pairs(reader, H, [(cand, partner)] * H.shape[0], fam, layer, batch, one_sided=True)
    return [{"lp": r["lp_A"], "unscorable": r["lp_A"] is None, **_row_extra(r)} for r in rows]


def pool_eval_items(items: list[dict[str, Any]], n: int = POOL_EVAL) -> list[dict[str, Any]]:
    """The quiver's labelled validation pool (BRIEF_R §2.3): the first n/2 pool items of each class in item order."""
    pool = [it for it in items if it["split"] == "pool"]
    out: list[dict[str, Any]] = []
    for lab in (1, 0):
        out += [it for it in pool if it["label"] == lab][: n // 2]
    return sorted(out, key=lambda it: it["item_id"])


def lo_key(reader_name: str, layer: int, render: str, item_id: str, cond: str = "natural", position: str = "last") -> str:
    return (f"{reader_name}|L{layer}|{render}" + ("|rp" if position == "rp" else "") + ("|shuf" if cond == "shuf" else "")
            + f"|{item_id}")


def distinct_pairs(reader_name: str, items: list[dict[str, Any]]) -> list[tuple[tuple[str, str], str, bool, int]]:
    """The distinct (pair, family, one_sided, count) combinations of a dataset in order of first appearance (one for
    the usual dataset-level candidates; one per item pattern for per-item banks)."""
    seen: dict[tuple[Any, ...], int] = {}
    order: list[tuple[tuple[str, str], str, bool]] = []
    for it in items:
        p = it["primary"]
        key = (item_pair(reader_name, p), family_for(p), p.get("sided") == "one")
        if key not in seen:
            seen[key] = 0
            order.append(key)
        seen[key] += 1
    return [(pair, fam, one, seen[(pair, fam, one)]) for pair, fam, one in order]


def rp_items(dataset: str, render: str, test: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """The test items whose read_position resolved in this render, and their token index (from index.json)."""
    idx = json.loads(index_file(dataset).read_text())
    toks = (idx.get("read_position_token") or {}).get(render)
    if not toks:
        return [], {}
    pos_of = {iid: t for iid, t in zip(idx["item_ids"], toks) if t is not None}
    return [it for it in test if it["item_id"] in pos_of], pos_of


# ------------------------------------------------------------------ E3: the reader's own hidden states during LO scoring
def answer_index(row_a: list[int], row_b: list[int], head_len: int) -> int:
    """The first position where the two candidates' rows differ (the first candidate-specific token; the Oracle's
    bullet dash and an NLA template's leading words are shared), never before ``head_len``."""
    n = min(len(row_a), len(row_b))
    for k in range(head_len, n):
        if row_a[k] != row_b[k]:
            return k
    return min(n, max(len(row_a), len(row_b)) - 1) if n > head_len else head_len


class ReaderStateHook:
    """Forward hooks on the READER model's blocks that record, for every row of every teacher-forced forward during
    ``score_lo``, the hidden state at the marker (where the activation is injected), at the pre-answer token (the last
    head token, whose state produces the first answer logit) and the whole post-head window. ``assemble`` rebuilds
    [N, T, 4, d] in state order from ``score_items``' group order and ``score_lo``'s deterministic chunking (per =
    batch // 2 states per forward, T forwards per chunk: one per NLA template or skip-lens form, rows ordered
    A_0, B_0, A_1, B_1, ...), taking each candidate's state at the first token where the A and B rows differ
    (``answer_index``). Groups whose family has fewer templates than T_max are NaN-padded."""

    def __init__(self, reader: Any, layers: tuple[int, ...], read_layer: int):
        import torch

        self.layers = tuple(layers)
        self.reader = reader
        if isinstance(reader, R.OLensReader):
            ids0, slot, _c, _cid = reader.carrier(read_layer)
            self.model, self.tok, self.marker, self.head = reader.target.model, reader.target.tokenizer, slot, list(ids0)
        elif isinstance(reader, R.SkipLensReader):
            self.model, self.tok, self.marker, self.head = reader.target.model, reader.tokenizer, reader.marker, list(reader.ids)
        elif isinstance(reader, R.NLAReader):
            self.model, self.tok, self.marker = reader.model, reader.tokenizer, reader.marker
            self.head = list(reader.ids) + LO.encode(reader.tokenizer, LO.NLA_PREFIX)
        else:
            raise TypeError(f"no reader states for {type(reader).__name__} (no forward pass)")
        self.head_len = len(self.head)
        self.fixed = torch.tensor([self.marker, self.head_len - 1])
        self.forwards: dict[int, list[tuple[Any, Any]]] = {L: [] for L in self.layers}
        self._handles: list[Any] = []

    def templates_for(self, fam: str) -> list[str]:
        """The T templates / forms ``scoring_lo`` runs per chunk for this reader and family."""
        if isinstance(self.reader, R.OLensReader):
            return [LO.OLENS_BULLET]
        if isinstance(self.reader, R.SkipLensReader):
            return list(C.SKIPLENS_LO_FORMS)
        return LO.templates_for(fam)

    def rows_for(self, pair: tuple[str, str], fam: str) -> list[tuple[list[int], list[int]]]:
        """(row_A, row_B) per template, built exactly as ``scoring_lo`` builds them."""
        return [(self.head + LO.encode(self.tok, t.format(X=pair[0])), self.head + LO.encode(self.tok, t.format(X=pair[1])))
                for t in self.templates_for(fam)]

    def __enter__(self) -> "ReaderStateHook":
        import torch

        blks = M.blocks(self.model)
        for L in self.layers:
            if not 0 <= L < len(blks):
                raise ValueError(f"reader-state layer {L} out of range for a {len(blks)}-block reader")

            def make(L: int):
                def hook(_m, _i, out):
                    h = out[0] if isinstance(out, tuple) else out
                    if h.shape[1] <= self.head_len:
                        return
                    b = torch.arange(h.shape[0], device=h.device)[:, None]
                    fixed = h[b, self.fixed.to(h.device), :].detach().to(torch.float16).cpu()
                    window = h[:, self.head_len:, :].detach().to(torch.float16).cpu()
                    self.forwards[L].append((fixed, window))
                return hook

            self._handles.append(blks[L].register_forward_hook(make(L)))
        return self

    def __exit__(self, *a: Any) -> bool:
        for h in self._handles:
            h.remove()
        self._handles = []
        return False

    def assemble(self, pairs: list[tuple[str, str]], batch: int, groups: list[tuple[str, list[int]]] | None = None
                 ) -> tuple[dict[int, Any], list[list[int]], dict[str, Any]]:
        """({reader_layer: fp16 [N, T_max, 4, d]}, answer index per state per template, meta). Positions
        READER_STATE_POSITIONS: marker and pre_answer from the A row (identical for the B row), answer_A / answer_B at
        ``answer_index``. ``groups`` = ``score_items``' (family, indices) in forward order; default one group."""
        import torch

        n_states = len(pairs)
        groups = groups or [("", list(range(n_states)))]
        per = max(1, batch // 2)
        temps = {fam: self.templates_for(fam) for fam, _ in groups}
        t_max = max(len(t) for t in temps.values())
        ans: list[list[int]] = [[] for _ in range(n_states)]
        for fam, idx in groups:
            for i in idx:
                ans[i] = [answer_index(ra, rb, self.head_len) for ra, rb in self.rows_for(pairs[i], fam)]
        plan = [(fam, [idx[s: s + per] for s in range(0, len(idx), per)]) for fam, idx in groups]
        n_fw = sum(len(chunks) * len(temps[fam]) for fam, chunks in plan)
        out = {}
        for L, fw in self.forwards.items():
            if len(fw) != n_fw:
                raise RuntimeError(f"reader states L{L}: {len(fw)} forwards, expected {n_fw} ({[(f, len(c), len(temps[f])) for f, c in plan]})")
            d = fw[0][0].shape[-1]
            arr = torch.full((n_states, t_max, 4, d), float("nan"), dtype=torch.float16)
            k = 0
            for fam, chunks in plan:
                for ch in chunks:
                    for t in range(len(temps[fam])):
                        fixed, win = fw[k]
                        k += 1
                        if fixed.shape[0] != 2 * len(ch):
                            raise RuntimeError(f"reader states L{L}: forward with {fixed.shape[0]} rows for a chunk of {len(ch)} states")
                        for q, i in enumerate(ch):
                            a = ans[i][t] - self.head_len
                            if not 0 <= a < win.shape[1]:
                                raise RuntimeError(f"reader states L{L}: answer index {ans[i][t]} outside the recorded window")
                            arr[i, t, 0] = fixed[2 * q, 0]
                            arr[i, t, 1] = fixed[2 * q, 1]
                            arr[i, t, 2] = win[2 * q, a]
                            arr[i, t, 3] = win[2 * q + 1, a]
            out[L] = arr
        meta = {"T": t_max, "templates": {fam: temps[fam] for fam, _ in groups}, "groups": [(fam, idx) for fam, idx in groups]}
        return out, ans, meta


def reader_states_dir(reader_name: str, dataset: str) -> Path:
    return RS_DIR / reader_name / dataset


def reader_states_done(reader_name: str, dataset: str, render: str, layer: int, rs_layers: tuple[int, ...]) -> bool:
    d = reader_states_dir(reader_name, dataset)
    return (d / "index.json").exists() and all((d / f"{render}_L{layer}_rL{rl}.npy").exists() for rl in rs_layers)


def collect_reader_lo(reader: Any, dataset: str, items: list[dict[str, Any]], layer: int, renders: tuple[str, ...] = RENDERS,
                      batch: int = 32, controls: bool = True, pool_eval: int = POOL_EVAL, items_path: Path | None = None,
                      position: str = "last", reader_states: tuple[int, ...] | None = None) -> int:
    """Rows for the TEST items of one dataset at one read layer, the given renders, each item scored against ITS OWN
    candidates / J-lens forms / template; plus the shuffled control (item i's candidates on item j's state, a seeded
    derangement) and the state-free rows (the dataset-mean test state against each distinct candidate pair). At the
    reader's PRIMARY site (chat render, PRIMARY_LAYER) a balanced ``pool_eval`` subset of the pool is scored too: the
    quiver's labelled validation pool (BRIEF_R §2.3). ``position="rp"``: the read_position states instead (items whose
    span resolved; keys ``...|rp|...``; no pool rows). ``reader_states``: E3 — save the reader's own hidden states at
    these reader blocks during the natural scoring of the test items, chat render, primary site. Resumable by key."""
    import torch

    test = [it for it in items if it["split"] == "test"]
    if not test:
        return 0
    name = reader.name
    fam_name = base_name(reader)
    primary_site = layer == PRIMARY_LAYER.get(fam_name) and position == "last"
    pool_sub = pool_eval_items(items, pool_eval) if primary_site and name == fam_name else []   # the quiver pool: the shipped reader only
    shas = r_shas(items_path or ITEMS_PATH)
    led = ledger(f"lo_{name}_L{layer}", batch=batch)
    led_c = ledger(f"control_{name}_L{layer}", batch=batch)
    base = {"module": MODULE, "reader": name, "reader_family": fam_name, "layer": layer, "dataset": dataset, "tag": test[0].get("tag"),
            "position": position, **shas}
    if isinstance(reader, R.OLensReader):
        base["alpha"] = reader.alpha
    n = 0
    for render in renders:
        if position == "rp":
            its_all, tok_of = rp_items(dataset, render, test)
            if not its_all:
                continue
        else:
            its_all, tok_of = test, {}
        X, idx = load_states(dataset, render, layer, position)
        pos_of = {iid: i for i, iid in enumerate(idx)}
        H = torch.from_numpy(X[[pos_of[it["item_id"]] for it in its_all]])
        conds: list[tuple[str, Any, list[dict[str, Any]], list[str | None]]] = [("natural", H, its_all, [None] * len(its_all))]
        if controls:
            perm = derangement(len(its_all), np.random.default_rng(SHUFFLE_SEED + stable_offset(dataset)))
            conds.append(("shuf", H[torch.as_tensor(perm)], its_all, [its_all[j]["item_id"] for j in perm]))
        if pool_sub and render == "chat":
            conds.append(("pool_eval", torch.from_numpy(X[[pos_of[it["item_id"]] for it in pool_sub]]), pool_sub, [None] * len(pool_sub)))
        for cond, Hc, its, state_ids in conds:
            keys = [lo_key(name, layer, render, it["item_id"], cond, position) for it in its]
            want_rs = (reader_states and cond == "natural" and render == "chat" and primary_site
                       and not isinstance(reader, R.JLensReader) and not reader_states_done(name, dataset, render, layer, reader_states))
            if all(k in done_keys(LO_PATH) for k in keys) and not want_rs:
                continue
            hook = ReaderStateHook(reader, reader_states, layer) if want_rs else None
            groups_rs = None
            with timed_call() as st:
                if hook is not None:
                    with hook:
                        rows, groups_rs = score_items(reader, Hc, its, layer, batch, return_groups=True)
                else:
                    rows = score_items(reader, Hc, its, layer, batch)
            if hook is not None:
                d = reader_states_dir(name, dataset)
                d.mkdir(parents=True, exist_ok=True)
                pairs_rs = [item_pair(fam_name, it["primary"]) for it in its]
                arrays, ans, rs_meta = hook.assemble(pairs_rs, batch, groups_rs)
                for rl, arr in arrays.items():
                    np.save(d / f"{render}_L{layer}_rL{rl}.npy", arr.numpy())
                (d / "index.json").write_text(json.dumps({"reader": name, "dataset": dataset, "render": render, "read_layer": layer,
                                                          "item_ids": [it["item_id"] for it in its], "labels": [it["label"] for it in its],
                                                          "pairs": pairs_rs, "answer_index": ans, "reader_layers": list(reader_states),
                                                          "positions": list(READER_STATE_POSITIONS), "marker_index": hook.marker,
                                                          "head_len": hook.head_len, **rs_meta, "shape": "[N, T, 4, d]", "dtype": "float16",
                                                          "nan_padded": any(len(a) < rs_meta["T"] for a in ans), **row_meta(),
                                                          "created_at": now_iso()}, indent=1))
                ledger(f"reader_states_{name}", layers=list(reader_states)).add(0, 0, 0.0, st.peak_mem_gb)
            for it, key, r, sid in zip(its, keys, rows, state_ids):
                if key in done_keys(LO_PATH):
                    continue
                row = {"key": key, **base, "render": render, "condition": "natural" if cond == "pool_eval" else cond,
                       "split": it["split"], "item_id": it["item_id"], "state_item_id": sid if cond == "shuf" else it["item_id"],
                       "label": it["label"], "sided": it["primary"].get("sided", "two"), "family": r["family"],
                       "system": bool(it.get("system")), "cand_A": r["cand_A"], "cand_B": r["cand_B"], "lp_A": r["lp_A"],
                       "lp_B": r["lp_B"], "lo": r["lo"], "unscorable": r["unscorable"], "templates": r["templates"],
                       **_row_extra(r), "wall_s_chunk": st.wall_s, "chunk_size": len(its), "created_at": now_iso()}
                if position == "rp":
                    rp = it.get("read_position") or {}
                    row.update(read_token_index=tok_of.get(it["item_id"]), read_position_role=rp.get("role"), read_position_kind=rp.get("kind"))
                append_row(LO_PATH, row)
                n += 1
            (led_c if cond == "shuf" else led).add(0, 0, st.wall_s, st.peak_mem_gb)
        if controls:
            pairs = distinct_pairs(fam_name, its_all)
            h_mean = H.mean(0, keepdim=True)
            for k, (pair, fam, one, count) in enumerate(pairs):
                key = f"{name}|L{layer}|{render}" + ("|rp" if position == "rp" else "") + f"|{dataset}" + (f"|p{k}" if len(pairs) > 1 else "")
                if key in done_keys(SF_PATH):
                    continue
                with timed_call() as st:
                    r = score_pairs(reader, h_mean, [pair], fam, layer, batch, one_sided=one)[0]
                append_row(SF_PATH, {"key": key, **base, "render": render, "condition": "state_free", "n_states_in_mean": len(its_all),
                                     "mean_norm": float(h_mean.norm()), "pair_index": k, "n_items_with_pair": count, "sided": "one" if one else "two",
                                     "family": fam, "cand_A": r["cand_A"], "cand_B": r["cand_B"], "lp_A": r["lp_A"], "lp_B": r["lp_B"],
                                     "lo": r["lo"], "unscorable": r["unscorable"], "templates": r["templates"], **_row_extra(r),
                                     "created_at": now_iso()})
                led_c.add(0, 0, st.wall_s, st.peak_mem_gb)
    print(f"[r/lo/{name}/L{layer}{'/rp' if position == 'rp' else ''}] {dataset}: {n} rows", flush=True)
    return n


def collect_reader_kway(reader: Any, dataset: str, items: list[dict[str, Any]], layer: int, renders: tuple[str, ...] = RENDERS,
                        batch: int = 32, items_path: Path | None = None) -> int:
    """R-B: one-sided score of EVERY candidate of every test item on its state (candidates per item); key ...|c<i>."""
    import torch

    test = [it for it in items if it["split"] == "test"]
    if not test:
        return 0
    k_max = max(len(it["primary"]["candidates"]) for it in test)
    shas = r_shas(items_path or ITEMS_PATH)
    led = ledger(f"kway_{reader.name}_L{layer}", batch=batch)
    n = 0
    for render in renders:
        X, idx = load_states(dataset, render, layer)
        pos_of = {iid: i for i, iid in enumerate(idx)}
        for i in range(k_max):
            its = [it for it in test if len(it["primary"]["candidates"]) > i]
            keys = [f"{reader.name}|L{layer}|{render}|{it['item_id']}|c{i}" for it in its]
            if all(kk in done_keys(KWAY_PATH) for kk in keys):
                continue
            H = torch.from_numpy(X[[pos_of[it["item_id"]] for it in its]])
            with timed_call() as st:
                rows = score_items(reader, H, its, layer, batch, cand_index=i)
            for it, key, r in zip(its, keys, rows):
                if key in done_keys(KWAY_PATH):
                    continue
                cands = it["primary"]["candidates"]
                append_row(KWAY_PATH, {"key": key, "module": MODULE, "reader": reader.name, "reader_family": base_name(reader), "layer": layer,
                                       "render": render, "dataset": dataset, "tag": it.get("tag"), "item_id": it["item_id"], "label": it["label"],
                                       "cand_index": i, "candidate": cands[i], "pair_partner": r["pair_partner"], "k": len(cands),
                                       "family": r["family"], "system": bool(it.get("system")), "lp": r["lp"], "unscorable": r["unscorable"],
                                       **_row_extra(r), **shas, "created_at": now_iso()})
                n += 1
            led.add(0, 0, st.wall_s, st.peak_mem_gb)
    print(f"[r/kway/{reader.name}/L{layer}] {dataset}: {n} rows", flush=True)
    return n


# ------------------------------------------------------------------ main
def items_by_dataset(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        out.setdefault(it["dataset"], []).append(it)
    return out


def olens_variant(ol: R.OLensReader, scale: float) -> R.OLensReader:
    """E12: the same mounted Oracle with alpha = scale × the shipped 16000, named ``olens_a<scale>x`` (its rows carry
    ``alpha`` and ``reader_family = olens``); the carrier cache and the PEFT model are shared with the base reader."""
    v = copy.copy(ol)
    v.alpha = scale * ol.alpha
    v.name = f"olens_a{scale:g}x"
    v.base_name = "olens"
    return v


def bind_readers(target: M.Target, names: list[str], olens_alpha_scales: list[float] | None = None) -> list[Any]:
    """Phase A readers on the probed model. Mount order matters: the Oracle lens FIRST (its bind unloads any mounted
    adapter), then the skip-lens arms as named adapters beside it; the J-lens copies W_U before any wrapping."""
    readers: list[Any] = []
    if "jlens" in names:
        jl = R.JLensReader().bind(target, layers_keep=sorted(LAYERS))
        missing = [L for L in LAYERS if L not in jl.J]
        if missing:
            rlog(f"jlens: lens has no Jacobian for blocks {missing}; those read layers are skipped")
        readers.append(jl)
    if "olens" in names:
        ol = R.OLensReader().bind(target)
        rlog(f"olens adapter={ol.adapter_dir} liveness={ol.liveness}")
        readers.append(ol)
        for s in olens_alpha_scales or []:
            if s != 1.0:
                readers.append(olens_variant(ol, s))
    for arm in ("skip_a", "skip_d"):
        if arm in names:
            sk = R.SKIPLENS_READERS[arm]().bind(target)
            rlog(f"{arm} adapter={sk.adapter_dir} liveness={sk.liveness}")
            readers.append(sk)
    return readers


def reader_read_layers(reader: Any, override: list[int] | None, position: str = "last", olens_layers: list[int] | None = None) -> tuple[int, ...]:
    table = RP_READ_LAYERS if position == "rp" else READ_LAYERS
    layers = tuple(override) if override else table[base_name(reader)]
    if olens_layers and isinstance(reader, R.OLensReader):
        layers = tuple(olens_layers)
    if isinstance(reader, R.JLensReader):
        layers = tuple(L for L in layers if L in reader.J)
    return layers


def datasets_with_rp(groups: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    return {ds: its for ds, its in groups.items() if any(it.get("read_position") for it in its)}


def bind_nla() -> Any:
    """Phase B reader (its own model); separate so tests can substitute the MOCK."""
    return R.NLAReader().bind()


def phase_b_ready(groups: dict[str, list[dict[str, Any]]], renders: tuple[str, ...], layer: int | None = None) -> tuple[list[str], list[str]]:
    """PLAN_R §9 rule 5: phase B waits on states, not on phase A's completion. A dataset is ready when its index.json and
    its block-``layer`` (default 42, the NLA's site) state file exist for every requested render; the others are skipped."""
    layer = C.LAYER if layer is None else layer
    ready, waiting = [], []
    for ds in groups:
        ok = index_file(ds).exists() and all(state_file(ds, r, layer).exists() for r in renders)
        (ready if ok else waiting).append(ds)
    return ready, waiting


# ------------------------------------------------------------------ provenance sidecars for rows that predate the run stamps
# Row files whose per-dataset row count main logs per dataset ("<ds>: N items; ... model_labels N; ..."): the stem -> the
# count's pattern in that line. The sidecar checks the file against these counts, so the rows are tied to ONE process.
LEGACY_COUNTS = {"model_labels": r"model_labels (\d+);", "prompt_only": r"prompt_only (\d+) new rows", "re_relabel": r"re_relabel (\d+);"}


def legacy_provenance(rows_path: Path, log_path: Path) -> dict[str, Any]:
    """Provenance for a row file written before ``run_id`` / ``run_kind`` / ``code_sha256`` existed, derived from the file
    and the run's log, never from the operator's memory (WS12's finding for ``model_labels.RB.jsonl``, 2026-10-20). Refused,
    naming the offending row, dataset or process, unless: no row is already stamped; every row has the same pod, git_sha
    and shard; every ``created_at`` falls inside ONE process (from its ``phase A|B: run=`` log line to that pod's next
    one); and each dataset's row count equals that process's logged count. The phase line gives items_file, items_sha256
    and the code sha; the kind is "real" only when that process wrote the real cache (``…/cache/g_agreement/r``) with a
    frozen r-code sha, else "unknown"."""
    import ast
    import collections
    import re
    from datetime import datetime

    rows_path, log_path = Path(rows_path), Path(log_path)
    stem = rows_path.name.split(".")[0]
    if stem not in LEGACY_COUNTS:
        raise SystemExit(f"legacy provenance: no per-dataset log count for {stem!r} rows (known: {sorted(LEGACY_COUNTS)})")
    raw = rows_path.read_bytes()
    rows = [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
    if not rows:
        raise SystemExit(f"legacy provenance: {rows_path} has no rows")
    stamped = [r["key"] for r in rows if r.get("run_id")]
    if stamped:
        raise SystemExit(f"legacy provenance: {len(stamped)} row(s) already carry run_id (first {stamped[0]}); no sidecar for stamped rows")
    idents = collections.Counter((r.get("pod"), r.get("git_sha"), r.get("shard")) for r in rows)
    if len(idents) != 1:
        (main_id, _), *others = idents.most_common()
        odd = next(r["key"] for r in rows if (r.get("pod"), r.get("git_sha"), r.get("shard")) != main_id)
        raise SystemExit(f"legacy provenance: rows from more than one pod/git_sha/shard {dict(idents)}; e.g. row {odd}")
    pod, sha, shard = next(iter(idents))
    t = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))   # noqa: E731
    phase_re = re.compile(r"^- (\S+) \[pod=(\S+) shard=(\S+) sha=([^\s\]]+)(?: [^\]]*)?\] phase ([AB]): run=")
    lines = log_path.read_text(encoding="utf-8").splitlines()
    starts = []
    for i, ln in enumerate(lines):
        m = phase_re.match(ln)
        if m and m.group(2) == str(pod) and sha and sha.startswith(m.group(4)):
            starts.append((t(m.group(1)), i, m.group(5)))
    if not starts:
        raise SystemExit(f"legacy provenance: no 'phase A|B: run=' line for pod={pod} sha={str(sha)[:10]} in {log_path}")
    starts.sort()
    windows = [(s, starts[k + 1][0] if k + 1 < len(starts) else None, i, ph) for k, (s, i, ph) in enumerate(starts)]

    def window_of(ts: str) -> int | None:
        x = t(ts)
        for k, (s, e, _i, _ph) in enumerate(windows):
            if x >= s and (e is None or x < e):
                return k
        return None

    where = collections.Counter(window_of(r["created_at"]) for r in rows)
    if len(where) != 1 or None in where:
        k0 = where.most_common(1)[0][0]
        odd = next(r["key"] for r in rows if window_of(r["created_at"]) != k0)
        raise SystemExit(f"legacy provenance: rows span {len(where)} processes {dict(where)} (None = before any phase line); "
                         f"e.g. row {odd}")
    k = next(iter(where))
    start, end, line_no, phase = windows[k]
    count_re = re.compile(rf"^- (\S+) \[pod={re.escape(str(pod))} [^\]]*\] (\S+): \d+ items; .*{LEGACY_COUNTS[stem]}")
    logged: dict[str, int] = collections.Counter()
    for ln in lines:
        m = count_re.match(ln)
        if m and t(m.group(1)) >= start and (end is None or t(m.group(1)) < end):
            logged[m.group(2)] += int(m.group(3))
    have = collections.Counter(r["dataset"] for r in rows)
    logged = {ds: n for ds, n in logged.items() if n}
    if dict(have) != logged:
        bad = sorted(ds for ds in set(have) | set(logged) if have.get(ds, 0) != logged.get(ds, 0))
        raise SystemExit("legacy provenance: per-dataset counts differ from the process's log: "
                         + ", ".join(f"{ds} rows {have.get(ds, 0)} vs logged {logged.get(ds, 0)}" for ds in bad))
    head = lines[line_no]
    m_sh = re.search(r"shas=(\{.*\})\s*$", head)
    shas = ast.literal_eval(m_sh.group(1)) if m_sh else {}
    m_cache = re.search(r"cache=(\S+?),", head)
    cache = m_cache.group(1) if m_cache else None
    real = bool(cache and cache.rstrip("/").endswith("/cache/g_agreement/r") and shas.get("frozen_r_code_sha256"))
    return {"rows_file": rows_path.name, "rows_sha256": hashlib_sha256(raw), "n_rows": len(rows),
            "per_dataset": dict(sorted(have.items())), "pod": pod, "shard": shard, "git_sha": sha,
            "created_at_min": min(r["created_at"] for r in rows), "created_at_max": max(r["created_at"] for r in rows),
            "run_id": f"legacy-{pod}-{start.strftime('%Y%m%dT%H%M%SZ')}", "run_kind": "real" if real else "unknown",
            "run_kind_basis": (f"phase {phase} process wrote the real cache {cache} with frozen_r_code_sha256 set" if real
                               else f"cache {cache!r} / frozen sha {shas.get('frozen_r_code_sha256')!r}: not provably real"),
            "code_sha256": shas.get("current_r_code_sha256"), "frozen_r_code_sha256": shas.get("frozen_r_code_sha256"),
            "items_file": shas.get("items_file"), "items_sha256": shas.get("items_sha256"),
            "process": {"phase": phase, "started_at": start.isoformat(), "ended_before": end.isoformat() if end else None,
                        "log_file": log_path.name, "log_line": line_no + 1, "cache": cache},
            "rows_rewritten": False, "written_at": now_iso(), "written_by": run_stamp()}


def hashlib_sha256(data: bytes) -> str:
    import hashlib

    return hashlib.sha256(data).hexdigest()


def write_legacy_provenance(rows_path: Path, log_path: Path, out_dir: Path | None = None) -> Path:
    """``legacy_provenance`` as ``<out_dir or PROVENANCE_DIR>/<rows stem>.provenance.json``; the rows file is only read."""
    prov = legacy_provenance(rows_path, log_path)
    d = Path(out_dir or PROVENANCE_DIR)
    d.mkdir(parents=True, exist_ok=True)
    out = d / (Path(rows_path).name.removesuffix(".jsonl") + ".provenance.json")
    out.write_text(json.dumps(prov, indent=1) + "\n")
    return out


def select_items(items_all: list[dict[str, Any]], shard: tuple[int, int] | None, datasets: list[str] | None = None,
                 limit: int | None = None) -> list[dict[str, Any]]:
    """main's selection: the shard's datasets (``shard_datasets`` over the bank's own dataset list), filtered by
    ``--datasets``, and with ``limit`` the first ``limit`` test and pool items of each dataset (``ordered_items`` order).
    A ``--datasets`` name the bank does not have is refused by name (a typo would otherwise drop a dataset silently);
    an empty selection names the requested datasets and the shard each belongs to."""
    bank = sorted({it["dataset"] for it in items_all})
    if datasets:
        unknown = sorted(set(datasets) - set(bank))
        if unknown:
            raise SystemExit(f"--datasets not in the bank: {unknown}")
    mine = set(shard_datasets(bank, shard))
    picked = [it for it in items_all if it["dataset"] in mine and (not datasets or it["dataset"] in datasets)]
    if not picked:
        where = ""
        if shard and datasets:
            owner = {ds: k for k in range(1, shard[1] + 1) for ds in shard_datasets(bank, (k, shard[1]))}
            where = f": requested {sorted(datasets)} belong to shard(s) " + ", ".join(f"{ds}→{owner[ds]}/{shard[1]}" for ds in sorted(set(datasets)))
        raise SystemExit("no items selected" + (f" for shard {shard[0]}/{shard[1]}" if shard else "") + where)
    if limit is not None:
        out: list[dict[str, Any]] = []
        for _ds, its in items_by_dataset(picked).items():
            its = ordered_items(its)
            out += [it for it in its if it["split"] == "test"][:limit] + [it for it in its if it["split"] != "test"][:limit]
        picked = out
    return picked


def resolve_run_kind(declared: str | None, limit: int | None) -> str:
    """The run kind main declares (GUARDS.md rule 3, chat 7's design): ``--limit`` (a partial run) forces "smoke" and
    refuses a declared "real"; otherwise the declared kind, default "unknown" (never "real" by omission). Nothing else
    implies smoke: ``--datasets`` is how real segmented runs are cut."""
    if limit is not None:
        if declared not in (None, "smoke"):
            raise SystemExit(f"--limit {limit} is a partial run: its kind is smoke, not --run-kind {declared}")
        return "smoke"
    return declared or "unknown"


def check_kind_dir(kind: str, root: Path) -> None:
    """A smoke or test run never writes into the real collection cache (``C.CACHE_DIR / "r"``; the 2026-10-19 --limit
    smoke landed beside the real rows): refused, naming the directory."""
    if kind in ("smoke", "test") and Path(root).resolve() == (C.CACHE_DIR / "r").resolve():
        raise SystemExit(f"refusing a {kind} run in the real cache {root}: give it its own --cache-dir")


def main(argv: list[str] | None = None) -> int:
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "B"], default=None)
    ap.add_argument("--datasets", nargs="*", default=None, help="restrict to these dataset ids (smoke)")
    ap.add_argument("--kway", action="store_true", help="run on dataset/items_rk.json (R-B) instead of items_r.json")
    ap.add_argument("--items-file", default=None, help="another bank in the items_r.json schema (items_re / items_rx / items_rb / items_rc2)")
    ap.add_argument("--renders", nargs="*", default=list(RENDERS))
    ap.add_argument("--readers", nargs="*", default=["jlens", "olens", "skip_a"], help="phase A readers")
    ap.add_argument("--layers", nargs="*", type=int, default=None, help="override the read layers of every reader")
    ap.add_argument("--olens-layers", nargs="*", type=int, default=None, help="E12: the Oracle's read layers (all its variants)")
    ap.add_argument("--olens-alpha-scales", nargs="*", type=float, default=None,
                    help="E12: extra Oracle variants with alpha = scale × 16000 (e.g. 0.5 2); the shipped alpha always runs")
    ap.add_argument("--olens-raw-layers", nargs="*", type=int, default=None,
                    help="budget guard (PLAN_R WS2): the Oracle's raw render only at these layers (e.g. 42 44)")
    ap.add_argument("--rp-layers", nargs="*", type=int, default=None, help="E6: override the read layers of the read_position rows")
    ap.add_argument("--no-read-position", action="store_true", help="E6: skip the read_position rows")
    ap.add_argument("--reader-states", action="store_true", help="E3: save the Oracle's / skip-lens's (/ NLA's) own hidden states")
    ap.add_argument("--reader-state-layers", nargs="*", type=int, default=list(READER_STATE_LAYERS))
    ap.add_argument("--no-controls", action="store_true")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--capture-batch", type=int, default=CAPTURE_BATCH)
    ap.add_argument("--cache-dir", default=None, help="output root (default cache/g_agreement/r; r_unfrozen for --allow-unfrozen)")
    ap.add_argument("--shard", default=None, help="PLAN_R §9: k/N — this pod's datasets (sorted index ≡ k-1 mod N); outputs *.k.jsonl")
    ap.add_argument("--pod", default=None, help="pod id recorded on every row ($RUNPOD_POD_ID or the hostname by default)")
    ap.add_argument("--suffix", default=None,
                    help="extra tag on every appended file (reader_lo.<k>.<suffix>.jsonl); default B for --phase B under --shard, none otherwise")
    ap.add_argument("--run-kind", choices=list(RUN_KINDS), default=None,
                    help="stamped on every row (GUARDS.md rule 3); default unknown — a real run says --run-kind real")
    ap.add_argument("--limit", type=int, default=None,
                    help="partial run: the first N test and pool items per dataset; forces --run-kind smoke and cache/g_agreement/r_smoke")
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--freeze-r", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--legacy-provenance", default=None, metavar="ROWS_JSONL",
                    help="write a provenance sidecar for a row file that predates the run stamps (rows untouched)")
    ap.add_argument("--legacy-log", default=None, help="with --legacy-provenance: the log.md holding that run's phase line")
    a = ap.parse_args(argv)
    if a.freeze_r:
        print(f"wrote {freeze_r(force=a.force)}")
        return 0
    if a.legacy_provenance:
        print(f"wrote {write_legacy_provenance(Path(a.legacy_provenance), Path(a.legacy_log or LOG))}")
        return 0
    if a.phase is None:
        ap.error("--phase A|B is required (or --freeze-r)")
    if a.limit is not None and a.limit < 1:
        ap.error("--limit must be >= 1")
    kind = resolve_run_kind(a.run_kind, a.limit)
    items_path = Path(a.items_file) if a.items_file else (B.ITEMS_RK if a.kway else B.ITEMS_R)
    require_frozen_r(a.allow_unfrozen, items_path)
    shard = parse_shard(a.shard)
    suffix = a.suffix if a.suffix is not None else ("B" if (a.phase == "B" and shard) else None)
    if a.limit is not None and a.suffix is None:   # a --limit smoke's log and ledger rows go to their own files too
        suffix = "smoke" if suffix is None else f"{suffix}.smoke"
    set_shard(shard, suffix)
    set_run_meta(a.pod, shard, run_kind=kind)
    set_items_path(items_path)
    if a.cache_dir:
        set_cache_dir(Path(a.cache_dir))
    elif a.limit is not None:
        set_cache_dir(C.CACHE_DIR / "r_smoke")
    elif a.allow_unfrozen:
        set_cache_dir(C.CACHE_DIR / "r_unfrozen")
    check_kind_dir(kind, R_DIR)
    items_all = B.load_items(items_path, "all")
    items = select_items(items_all, shard, a.datasets, a.limit)
    kway = a.kway or items[0]["primary"].get("sided") == "kway"
    groups = items_by_dataset(items)
    rp_groups = {} if (a.no_read_position or kway) else datasets_with_rp(groups)
    renders = tuple(a.renders)
    rs_layers = tuple(a.reader_state_layers) if a.reader_states else None
    R_DIR.mkdir(parents=True, exist_ok=True)
    rlog(f"phase {a.phase}: run={row_meta()} limit={a.limit} {len(groups)} datasets, {len(items)} items, renders={renders}, kway={kway}, "
         f"items={items_path.name}, cache={R_DIR}, readers={a.readers if a.phase == 'A' else ['nla']}, "
         f"read_position datasets={sorted(rp_groups)}, reader_states={rs_layers}, olens_alpha_scales={a.olens_alpha_scales}, "
         f"shas={r_shas(items_path)}")

    def rend_for(reader: Any, L: int) -> tuple[str, ...]:
        if base_name(reader) == "olens" and a.olens_raw_layers is not None and L not in a.olens_raw_layers:
            return tuple(r for r in renders if r != "raw")
        return renders

    def run_reader(rd: Any) -> None:
        for L in reader_read_layers(rd, a.layers, "last", a.olens_layers):
            rs = rend_for(rd, L)
            with timed_call() as st:
                n = 0
                for ds, its in groups.items():
                    if kway:
                        n += collect_reader_kway(rd, ds, its, L, rs, a.batch, items_path=items_path)
                    else:
                        n += collect_reader_lo(rd, ds, its, L, rs, a.batch, controls=not a.no_controls, items_path=items_path,
                                               reader_states=rs_layers)
            rlog(f"{'kway' if kway else 'lo'} {rd.name} L{L}: {n} new rows, renders={rs}, {st.wall_s:.0f}s")
        if rp_groups:   # E6: the read_position rows follow RP_READ_LAYERS (or --rp-layers); --olens-layers is the E12 sweep at the default site
            for L in reader_read_layers(rd, a.rp_layers, "rp"):
                with timed_call() as st:
                    n = sum(collect_reader_lo(rd, ds, its, L, renders, a.batch, controls=not a.no_controls, items_path=items_path,
                                              position="rp") for ds, its in rp_groups.items())
                rlog(f"lo {rd.name} L{L} rp: {n} new rows over {len(rp_groups)} datasets, {st.wall_s:.0f}s")

    try:
        if a.phase == "A":
            target = load_target_timed(MODULE)
            with timed_call() as st_all:
                for ds, its in groups.items():
                    with timed_call() as st:
                        walls = capture_dataset(target, ds, its, renders, LAYERS, a.capture_batch, items_path=items_path)
                        n_po = collect_prompt_only(target, ds, its, batch=a.batch, items_path=items_path)
                        n_ml = collect_model_labels(target, ds, its, batch=max(1, a.batch // 2), items_path=items_path)
                        n_rl, groups[ds] = collect_re_relabel(target, ds, its, batch=max(1, a.batch // 2), items_path=items_path)
                    rlog(f"{ds}: {len(its)} items; capture {walls}; prompt_only {n_po} new rows; model_labels {n_ml}; "
                         f"re_relabel {n_rl}; {st.wall_s:.0f}s")
            rlog(f"capture + prompt_only: {len(groups)} datasets in {st_all.wall_s / 60:.1f} min")
            if st_all.wall_s / 60 > CAPTURE_BUDGET_MIN:
                msg = (f"capture exceeded {CAPTURE_BUDGET_MIN} min: PLAN_R WS2 budget guard applies — rerun the Oracle with "
                       f"--olens-raw-layers 42 44 and record the deviation in BRIEF_R.md")
                rlog(msg)
                print(f"[r] WARNING {msg}", flush=True)
            for rd in bind_readers(target, a.readers, a.olens_alpha_scales):
                run_reader(rd)
            M.unload(target)
        else:
            ready, waiting = phase_b_ready(groups, renders)
            rlog(f"phase B: {len(ready)} datasets with block-42 states in {renders}, {len(waiting)} not yet captured (skipped, re-run later): {waiting}")
            if not ready:
                raise SystemExit("phase B: no dataset has its block-42 states yet; run phase A first")
            groups = {ds: groups[ds] for ds in ready}
            rp_groups = {ds: its for ds, its in rp_groups.items() if ds in groups}
            for ds in list(groups):   # R-E INTERNAL: score the NLA on the behavioural key phase A wrote (no decode here)
                _, groups[ds] = collect_re_relabel(None, ds, groups[ds])
            led = ledger("load_nla")
            with timed_call() as st:
                nla = bind_nla()
            led.add(0, 0, st.wall_s, st.peak_mem_gb)
            rlog(f"phase B: nla adapter={nla.adapter_dir} liveness={nla.liveness}")
            run_reader(nla)
            nla.unload()
    finally:
        rows = flush_ledgers()
        rlog(f"phase {a.phase} ledger: " + "; ".join(f"{r['step']} {r['wall_s']:.0f}s×{r['n_calls']}" for r in rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
