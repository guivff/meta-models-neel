"""Shared, CPU-only helpers for the G1–G4 analysis scripts and the consensus view.

Everything here consumes the frozen artefacts described in INTERFACES.md §1–§7 and never
calls a model. The module has four parts:

1. paths + loaders + *validators that raise* (split leakage, donor validity, blind-sheet
   leakage, activation-site/cache mismatch, sampling mismatch, frozen gate);
2. vote logic (a claim votes only if it asserts exactly one candidate; `unclear` and
   `self_contradictory` abstain; two abstentions never agree; ties are unresolved;
   leave-one-out consistency excludes the method's own vote);
3. pair-level bootstrap (resample base pairs with replacement, ratio of sums; n_boot 2000,
   seed 0 by default) and the 3×3 agreement matrix;
4. a small matplotlib style (surface/ink tokens, fixed method colours, CI bars always).

Nothing in this file writes under results/ by itself; scripts decide where to write.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from common.stats import wilson  # noqa: E402  (re-exported for scripts)

G_DIR = ROOT / "projects" / "g_agreement"
DEFAULTS: Dict[str, Path] = {
    "items": G_DIR / "dataset" / "items.json",
    "donors": G_DIR / "dataset" / "donors.json",
    "g4_pairs": G_DIR / "dataset" / "g4_pairs.json",
    "frozen_config": G_DIR / "manifest" / "frozen_config.json",
    "states_meta": ROOT / "cache" / "g_agreement" / "states_meta.jsonl",
    "gens_dir": ROOT / "cache" / "g_agreement" / "gens",
    "claims_dir": ROOT / "results" / "g_agreement" / "claims",
    "results_dir": ROOT / "results" / "g_agreement",
}

METHODS: Tuple[str, ...] = ("nla", "olens", "jlens")
METHOD_LABELS = {"nla": "NLA", "olens": "Oracle lens", "jlens": "J-lens", "prompt_only": "prompt-only", "target": "target"}
FAMILIES: Tuple[str, ...] = ("language", "tense", "ownership", "mapping")
RELATION_FAMILIES: Tuple[str, ...] = ("ownership", "mapping")
SPLITS = ("dev", "test")

EXPECTED_LAYER = 42
EXPECTED_HOOK = "block_output"
EXPECTED_HIDDEN_STATES_INDEX = 43
SAMPLING_KEYS = ("temperature", "top_p", "top_k", "max_new_tokens", "do_sample")

STATE_FREE_CONDITIONS = frozenset({"state_free", "noise_ceiling"})
STATE_FREE_SOURCES = frozenset({"mean_dev_activation", "zeros", "random_same_norm"})
NULL_METHODS = frozenset({"jlens_null"})

ASSERTING_STATUSES = frozenset({"supports", "contradicts"})
ABSTAIN_STATUSES = frozenset({"unclear", "self_contradictory"})
ALL_STATUSES = ASSERTING_STATUSES | ABSTAIN_STATUSES

N_BOOT = 2000
SEED = 0


# --------------------------------------------------------------------------------------
# errors
# --------------------------------------------------------------------------------------
class AnalysisError(Exception):
    """Base class: any violated precondition of the analysis."""


class SplitLeakageError(AnalysisError):
    """An item from another split entered a per-split summary."""


class DonorAssignmentError(AnalysisError):
    """donors.json violates the G3 rules (same pair, cross-family, non-test, self)."""


class BlindSheetLeakageError(AnalysisError):
    """A blinded annotation sheet carries item ids or answer-key material."""


class SiteMismatchError(AnalysisError):
    """states_meta / gen rows disagree with the frozen activation site or prompt hash."""


class SamplingMismatchError(AnalysisError):
    """A generation's sampling dict differs from the frozen sampling setting."""


class FrozenConfigError(AnalysisError):
    """Test summaries were requested without a frozen=true manifest."""


# --------------------------------------------------------------------------------------
# io
# --------------------------------------------------------------------------------------
def load_json(path: os.PathLike | str) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: os.PathLike | str) -> List[dict]:
    rows: List[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: os.PathLike | str, obj: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=_json_default)


def write_csv(path: os.PathLike | str, rows: Sequence[Mapping[str, Any]], columns: Optional[Sequence[str]] = None) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if columns is None:
        columns = []
        for r in rows:
            for k in r:
                if k not in columns:
                    columns.append(k)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(columns))
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in columns})


def _json_default(o: Any) -> Any:
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (set, frozenset)):
        return sorted(o)
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON serialisable: {type(o)}")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_items_sha(items: Sequence[dict]) -> str:
    """sha256 of the canonical JSON of the item list (sorted keys, no whitespace)."""
    return sha256_text(json.dumps(items, sort_keys=True, ensure_ascii=False, separators=(",", ":")))


# --------------------------------------------------------------------------------------
# dataset / artefact loaders
# --------------------------------------------------------------------------------------
def load_items(path: os.PathLike | str) -> Tuple[dict, Dict[str, dict]]:
    """Return (meta, {item_id: item}). Validates the pair invariants of INTERFACES §1."""
    d = load_json(path)
    meta = d.get("meta", {})
    items = {it["item_id"]: it for it in d["items"]}
    if len(items) != len(d["items"]):
        raise AnalysisError("duplicate item_id in items.json")
    by_pair: Dict[str, List[dict]] = {}
    for it in items.values():
        by_pair.setdefault(it["pair_id"], []).append(it)
    for pid, its in by_pair.items():
        if len(its) != 2:
            raise AnalysisError(f"pair {pid} has {len(its)} versions, expected 2")
        a, b = its
        for k in ("family", "split", "template_id"):
            if a[k] != b[k]:
                raise AnalysisError(f"pair {pid}: versions differ in {k}")
        if a["primary"]["candidates"] != b["primary"]["candidates"]:
            raise AnalysisError(f"pair {pid}: candidate sets differ or are re-ordered")
        if len(a["primary"]["candidates"]) != 2:
            raise AnalysisError(f"pair {pid}: expected exactly two candidates")
        if a["primary"]["answer"] == b["primary"]["answer"]:
            raise AnalysisError(f"pair {pid}: both versions share the same answer")
        for it in its:
            if it["primary"]["answer"] not in it["primary"]["candidates"]:
                raise AnalysisError(f"{it['item_id']}: answer not among candidates")
            if it["split"] not in SPLITS:
                raise AnalysisError(f"{it['item_id']}: unknown split {it['split']}")
    return meta, items


def pairs_of(items: Mapping[str, dict], item_ids: Iterable[str]) -> List[str]:
    seen: List[str] = []
    for i in item_ids:
        p = items[i]["pair_id"]
        if p not in seen:
            seen.append(p)
    return seen


def split_item_ids(items: Mapping[str, dict], split: str, families: Optional[Iterable[str]] = None) -> List[str]:
    fams = set(families) if families is not None else None
    out = [i for i, it in sorted(items.items()) if it["split"] == split and (fams is None or it["family"] in fams)]
    return out


def assert_split(items: Mapping[str, dict], item_ids: Iterable[str], split: str) -> None:
    """Raise SplitLeakageError if any item is not of `split` (dev must never enter a test summary)."""
    bad = [i for i in item_ids if items[i]["split"] != split]
    if bad:
        raise SplitLeakageError(f"{len(bad)} item(s) of another split entered a '{split}' summary: {bad[:5]}")


def load_gens(path: os.PathLike | str) -> List[dict]:
    rows = load_jsonl(path)
    ids = [r["gen_id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise AnalysisError(f"duplicate gen_id in {path}")
    return rows


def index_by(rows: Iterable[dict], key: str) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for r in rows:
        if r[key] in out:
            raise AnalysisError(f"duplicate {key}={r[key]}")
        out[r[key]] = r
    return out


def load_claims(path: os.PathLike | str) -> Dict[str, dict]:
    """{gen_id: claim}. Statuses are validated against the rubric vocabulary."""
    rows = load_jsonl(path)
    out: Dict[str, dict] = {}
    for r in rows:
        st = r["primary"]["status"]
        if st not in ALL_STATUSES:
            raise AnalysisError(f"claim {r['gen_id']}: unknown status {st!r}")
        if st in ASSERTING_STATUSES and not r["primary"].get("value"):
            raise AnalysisError(f"claim {r['gen_id']}: status {st} without a value")
        if r["gen_id"] in out:
            raise AnalysisError(f"duplicate claim for gen_id {r['gen_id']}")
        out[r["gen_id"]] = r
    return out


def load_states_meta(path: os.PathLike | str, layer: int = EXPECTED_LAYER) -> Dict[str, dict]:
    """{item_id: meta row} for the read layer. The collector also writes dev-only extra-layer rows
    (blocks 40/44, same item_id, `layer` set) for the off-grid check; those are kept under
    "<item_id>@L<layer>" so the layer-42 index stays unique."""
    out: Dict[str, dict] = {}
    for r in load_jsonl(path):
        L = int(r.get("layer", layer))
        key = r["item_id"] if L == layer else f"{r['item_id']}@L{L}"
        if key in out:
            raise AnalysisError(f"duplicate states_meta row for {key}")
        out[key] = r
    return out


def load_frozen_config(path: os.PathLike | str) -> Optional[dict]:
    p = Path(path)
    if not p.exists():
        return None
    return load_json(p)


# --------------------------------------------------------------------------------------
# validators that raise
# --------------------------------------------------------------------------------------
def require_frozen(frozen_config_path: os.PathLike | str, allow_unfrozen: bool) -> Tuple[bool, Optional[dict]]:
    """Return (frozen, config). Raise FrozenConfigError unless frozen=true or dev-only is allowed."""
    cfg = load_frozen_config(frozen_config_path)
    frozen = bool(cfg and cfg.get("frozen") is True)
    if not frozen and not allow_unfrozen:
        raise FrozenConfigError(
            f"{frozen_config_path} missing or frozen!=true; test summaries refused. "
            "Pass --allow-unfrozen for a dev-only run (writes to results/g_agreement/<module>/dev/)."
        )
    return frozen, cfg


def resolve_split_and_out(module: str, split: Optional[str], frozen: bool, out: Optional[str]) -> Tuple[str, Path]:
    """Dev and test are always summarised separately. Test needs frozen=true, full stop."""
    if split is None:
        split = "test" if frozen else "dev"
    if split == "test" and not frozen:
        raise FrozenConfigError("split=test requested without a frozen manifest; only dev summaries may run unfrozen")
    if out:
        return split, Path(out)
    base = DEFAULTS["results_dir"] / module
    return split, (base if split == "test" else base / "dev")


def check_dataset_sha(items_meta: Mapping[str, Any], items: Mapping[str, dict], frozen_cfg: Optional[Mapping[str, Any]]) -> Optional[str]:
    """If the frozen manifest records a dataset sha, it must match items.json. Returns the sha compared."""
    if not frozen_cfg:
        return None
    recorded = None
    # core/config.py records the items-level sha under `dataset_meta_sha256_items` (what items.json
    # declares) and the whole-file sha under `dataset_sha256`; compare like with like.
    for k in ("dataset_meta_sha256_items", "sha256_items", "items_sha256", "dataset_sha256", "dataset_sha"):
        if k in frozen_cfg:
            recorded = frozen_cfg[k]
            break
        if isinstance(frozen_cfg.get("shas"), Mapping) and k in frozen_cfg["shas"]:
            recorded = frozen_cfg["shas"][k]
            break
    if recorded is None:
        return None
    declared = items_meta.get("sha256_items")
    if declared is not None and declared != recorded:
        raise FrozenConfigError(f"items.json meta.sha256_items={declared} != frozen manifest {recorded}")
    return recorded


def check_states_meta_row(row: Mapping[str, Any], expected_layer: int = EXPECTED_LAYER, expected_hook: str = EXPECTED_HOOK,
                          expected_hs_index: Optional[int] = EXPECTED_HIDDEN_STATES_INDEX) -> None:
    iid = row.get("item_id", "?")
    if int(row.get("layer", -1)) != expected_layer:
        raise SiteMismatchError(f"states_meta {iid}: layer={row.get('layer')} != {expected_layer}")
    if row.get("hook") != expected_hook:
        raise SiteMismatchError(f"states_meta {iid}: hook={row.get('hook')!r} != {expected_hook!r}")
    if expected_hs_index is not None and "hidden_states_index" in row and int(row["hidden_states_index"]) != expected_hs_index:
        raise SiteMismatchError(f"states_meta {iid}: hidden_states_index={row['hidden_states_index']} != {expected_hs_index}")
    if row.get("pre_answer") is not True:
        raise SiteMismatchError(f"states_meta {iid}: pre_answer is not true (an answer token may have been generated)")
    if "n_tokens" in row and "pos" in row and int(row["pos"]) != int(row["n_tokens"]) - 1:
        raise SiteMismatchError(f"states_meta {iid}: pos={row['pos']} is not the last prompt token (n_tokens={row['n_tokens']})")


def check_gen_against_states(gen: Mapping[str, Any], states_meta: Mapping[str, dict], expected_layer: int = EXPECTED_LAYER) -> None:
    """Activation-reading methods must point at a cached state whose prompt hash they carry.

    State-free control rows (condition state_free / method jlens_null) carry no state: they must have
    state_item_id null and a declared input.injection_source from STATE_FREE_SOURCES.
    """
    if gen.get("condition") in STATE_FREE_CONDITIONS or gen.get("method") in NULL_METHODS:
        if gen.get("state_item_id") is not None:
            raise SiteMismatchError(f"gen {gen.get('gen_id')}: state-free/null row must have state_item_id null, got {gen.get('state_item_id')!r}")
        src = (gen.get("input") or {}).get("injection_source")
        if src not in STATE_FREE_SOURCES:
            raise SiteMismatchError(f"gen {gen.get('gen_id')}: state-free/null row needs input.injection_source in {sorted(STATE_FREE_SOURCES)}, got {src!r}")
        return
    if gen.get("method") not in METHODS:
        return
    if gen.get("condition") == "offgrid_check":
        # dev-only OLens sensitivity rows: state <item>@L40/@L44 captured at that block, layer integer = that
        # block; validated against their own meta row and excluded from every test metric.
        expected_layer = int(gen.get("layer", expected_layer))
    sid = gen.get("state_item_id")
    if gen.get("condition") == "offgrid_check" and f"{sid}@L{expected_layer}" in states_meta:
        sid = f"{sid}@L{expected_layer}"  # the dev-only extra-layer state of that item
    if sid not in states_meta:
        raise SiteMismatchError(f"gen {gen.get('gen_id')}: state_item_id={sid!r} has no states_meta row")
    meta = states_meta[sid]
    check_states_meta_row(meta, expected_layer=expected_layer, expected_hs_index=expected_layer + 1)
    g_sha = (gen.get("input") or {}).get("prompt_ids_sha256")
    # the J-lens receives no prompt (it is a function of the activation alone); its rows carry no
    # prompt hash and are tied to the state through state_item_id + activation_norm below
    if gen["method"] == "jlens" and g_sha is None:
        g_sha = meta.get("prompt_ids_sha256")
    # the verbalizers' `input.prompt_ids_sha256` is the hash of THEIR OWN fixed carrier prompt (the
    # collector records what the reader received, INTERFACES §5), not of the item render; their link
    # to the captured state is state_item_id plus the activation-norm equality checked below
    if gen["method"] in ("nla", "olens"):
        g_sha = meta.get("prompt_ids_sha256")
    if g_sha != meta.get("prompt_ids_sha256"):
        raise SiteMismatchError(f"gen {gen.get('gen_id')}: prompt_ids_sha256 {g_sha} != states_meta {meta.get('prompt_ids_sha256')}")
    lip = (gen.get("input") or {}).get("layer_in_prompt")
    if gen["method"] in ("nla", "olens") and lip is not None and int(lip) != expected_layer:
        raise SiteMismatchError(f"gen {gen.get('gen_id')}: layer_in_prompt={lip} != {expected_layer}")
    if gen["method"] == "jlens" and lip not in (None, expected_layer):
        raise SiteMismatchError(f"gen {gen.get('gen_id')}: J-lens row carries layer_in_prompt={lip}")
    an = (gen.get("input") or {}).get("activation_norm")
    if an is not None and meta.get("norm") is not None and not np.isclose(float(an), float(meta["norm"]), rtol=1e-3, atol=1e-2):
        raise SiteMismatchError(f"gen {gen.get('gen_id')}: activation_norm {an} != cached norm {meta['norm']}")


def validate_gens_against_states(gens: Iterable[dict], states_meta: Mapping[str, dict]) -> int:
    n = 0
    for g in gens:
        if g.get("method") in METHODS or g.get("method") in NULL_METHODS or g.get("condition") in STATE_FREE_CONDITIONS:
            check_gen_against_states(g, states_meta)
            n += 1
    return n


def validate_dev_donors(items: Mapping[str, dict], donors: Mapping[str, Any]) -> Dict[str, str]:
    """`dev_assignments`: development-only plumbing check. Dev items only, donor != recipient pair; cross-family is allowed."""
    blk = donors.get("dev_assignments") or {}
    # donors.py writes a block {"dev_cross_family": true, "scored": false, ..., "assignments": {...}};
    # a flat {recipient: donor} mapping is accepted too.
    assignments: Dict[str, str] = dict(blk.get("assignments") or {}) if isinstance(blk, dict) and "assignments" in blk else dict(blk)
    if not assignments:
        raise DonorAssignmentError("donors.json has no dev_assignments block; G3 cannot run in dev mode")
    for rec, don in assignments.items():
        if rec not in items or don not in items:
            raise DonorAssignmentError(f"dev assignment with unknown item: {rec} <- {don}")
        if items[rec]["split"] != "dev" or items[don]["split"] != "dev":
            raise DonorAssignmentError(f"dev assignment {rec} <- {don} touches a non-dev item (test leakage into development)")
        if items[rec]["pair_id"] == items[don]["pair_id"]:
            raise DonorAssignmentError(f"dev assignment {rec} <- {don}: same pair")
    return assignments


def validate_donors(items: Mapping[str, dict], donors: Mapping[str, Any], require_complete: bool = True) -> Dict[str, str]:
    """Return the validated {recipient: donor} map or raise DonorAssignmentError."""
    assignments: Dict[str, str] = dict(donors["assignments"])
    test_ids = set(split_item_ids(items, "test"))
    for rec, don in assignments.items():
        if rec not in items or don not in items:
            raise DonorAssignmentError(f"unknown item in assignment {rec} <- {don}")
        r, d = items[rec], items[don]
        if rec == don:
            raise DonorAssignmentError(f"{rec}: donor is the recipient itself")
        if r["pair_id"] == d["pair_id"]:
            raise DonorAssignmentError(f"{rec}: donor {don} is from the same pair {r['pair_id']}")
        if r["family"] != d["family"]:
            raise DonorAssignmentError(f"{rec}: donor {don} is cross-family ({d['family']} -> {r['family']})")
        if r["split"] != "test" or d["split"] != "test":
            raise DonorAssignmentError(f"{rec} <- {don}: donors are test-only (got {r['split']}, {d['split']})")
    if require_complete and set(assignments) != test_ids:
        missing = sorted(test_ids - set(assignments))
        extra = sorted(set(assignments) - test_ids)
        raise DonorAssignmentError(f"assignments must cover exactly the test items; missing={missing[:5]} extra={extra[:5]}")
    return assignments


BLIND_SHEET_ALLOWED_KEYS = frozenset({"sheet_id", "method", "text"})
BLIND_SHEET_FORBIDDEN_KEYS = frozenset({"gen_id", "item_id", "state_item_id", "pair_id", "answer", "answer_key", "primary", "candidates",
                                        "answer_aliases", "target_answer", "target_answer_regex", "family", "split", "status", "value"})


def make_sheet_id(gen_id: str, salt: str, n: int = 12) -> str:
    """Opaque id for the blind sheet, identical to core.scoring (sha256(salt + gen_id)[:12]); the
    gen_id <-> sheet_id map lives in cache/g_agreement/sheet_map_<module>.json."""
    return hashlib.sha256((salt + gen_id).encode("utf-8")).hexdigest()[:n]


def validate_blind_sheet(rows: Iterable[Mapping[str, Any]], item_ids: Iterable[str] = (), answer_strings: Iterable[str] = ()) -> int:
    """A blind sheet carries exactly sheet_id, method, text. Raise on any leakage.

    `item_ids`: every known item id; none may appear as a substring of any field (this is what made
    the old gen_id-keyed sheet non-blind). `answer_strings`: per-item answer-key identifiers that must not
    appear verbatim in the text; the candidate words themselves are allowed since the readout names them.
    """
    n = 0
    ids = [i for i in item_ids if i]
    forbidden_text = [a for a in answer_strings if a]
    for r in rows:
        n += 1
        keys = set(r.keys())
        bad = keys & BLIND_SHEET_FORBIDDEN_KEYS
        if bad:
            raise BlindSheetLeakageError(f"blind sheet row {r.get('sheet_id')} carries forbidden key(s) {sorted(bad)}")
        if keys != BLIND_SHEET_ALLOWED_KEYS:
            raise BlindSheetLeakageError(f"blind sheet row {r.get('sheet_id')} keys {sorted(keys)} != {sorted(BLIND_SHEET_ALLOWED_KEYS)}")
        for field_name, val in r.items():
            sval = str(val)
            for i in ids:
                if i in sval:
                    raise BlindSheetLeakageError(f"blind sheet row {r.get('sheet_id')}: field {field_name!r} contains item id {i!r}")
        for a in forbidden_text:
            if a in str(r.get("text", "")):
                raise BlindSheetLeakageError(f"blind sheet row {r.get('sheet_id')}: text contains answer-key material {a!r}")
    return n


def check_sampling_matches(sampling: Mapping[str, Any], frozen_sampling: Mapping[str, Any], keys: Sequence[str] = SAMPLING_KEYS,
                           where: str = "") -> None:
    diffs = []
    for k in keys:
        a, b = sampling.get(k), frozen_sampling.get(k)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
            same = np.isclose(float(a), float(b))
        else:
            same = a == b
        if not same:
            diffs.append(f"{k}: {a!r} != frozen {b!r}")
    if diffs:
        raise SamplingMismatchError(f"sampling mismatch {where}: " + "; ".join(diffs))


def frozen_sampling(frozen_cfg: Optional[Mapping[str, Any]]) -> Optional[dict]:
    """The frozen verbalizer sampling dict. core/config.py stores temperature/top_p/top_k/do_sample
    under `sampling` and the verbalizer cap under `caps.verbalizer`; the rows carry both in one
    dict, so merge them here (an explicit `sampling.max_new_tokens` wins if present)."""
    if not frozen_cfg:
        return None
    base = None
    for k in ("sampling", "verbalizer_sampling"):
        if isinstance(frozen_cfg.get(k), Mapping):
            base = dict(frozen_cfg[k])
            break
    if base is None:
        return None
    caps = frozen_cfg.get("caps") or {}
    if "max_new_tokens" not in base and isinstance(caps, Mapping) and caps.get("verbalizer") is not None:
        base["max_new_tokens"] = int(caps["verbalizer"])
    return base


# --------------------------------------------------------------------------------------
# claims, votes, answers
# --------------------------------------------------------------------------------------
def claim_status(claim: Optional[Mapping[str, Any]]) -> str:
    if claim is None:
        return "absent"
    return claim["primary"]["status"]


def vote(claim: Optional[Mapping[str, Any]]) -> Optional[str]:
    """The candidate a readout asserts, or None. unclear / self_contradictory / absent never vote."""
    if claim is None:
        return None
    p = claim["primary"]
    if p["status"] in ASSERTING_STATUSES and p.get("value"):
        return p["value"]
    return None


def is_truncated(claim: Optional[Mapping[str, Any]], gen: Optional[Mapping[str, Any]] = None) -> bool:
    if claim is not None and claim.get("truncated"):
        return True
    if gen is not None and gen.get("finish_reason") == "length":
        return True
    return False


def normalise_answer(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return re.sub(r"\s+", " ", str(s).strip().lower())


def claim_correct(claim: Optional[Mapping[str, Any]], item: Mapping[str, dict]) -> Optional[bool]:
    """Independent check of the asserted value against the answer key (None = abstained)."""
    v = vote(claim)
    if v is None:
        return None
    key = item["primary"]
    truth = {normalise_answer(key["answer"])} | {normalise_answer(a) for a in key.get("answer_aliases", [])}
    return normalise_answer(v) in truth


def status_value_consistent(claim: Optional[Mapping[str, Any]], item: Mapping[str, dict]) -> bool:
    """`supports` must name the key answer, `contradicts` the other candidate. False flags extractor errors."""
    if claim is None:
        return True
    st = claim["primary"]["status"]
    if st not in ASSERTING_STATUSES:
        return True
    c = claim_correct(claim, item)
    return (st == "supports") == bool(c)


def _mentions(text: str, needle: str) -> bool:
    return re.search(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", text, flags=re.IGNORECASE) is not None


def parse_target_answer(item: Mapping[str, Any], text: Optional[str]) -> Optional[str]:
    """Which candidate the target model answered. Exactly one candidate (or alias) must be present."""
    if not text:
        return None
    cands = item["primary"]["candidates"]
    aliases = {item["primary"]["answer"]: list(item["primary"].get("answer_aliases", []))}
    hits = []
    for c in cands:
        names = [c] + aliases.get(c, [])
        if any(_mentions(text, n) for n in names):
            hits.append(c)
    return hits[0] if len(hits) == 1 else None


def target_answers(items: Mapping[str, dict], gens: Iterable[dict], claims: Optional[Mapping[str, dict]] = None) -> Dict[str, Optional[str]]:
    """{item_id: target's own answer (candidate) or None}. Prefers an extracted claim row when present."""
    out: Dict[str, Optional[str]] = {}
    for g in gens:
        if g.get("method") != "target":
            continue
        iid = g["item_id"]
        if claims and g["gen_id"] in claims:
            out[iid] = vote(claims[g["gen_id"]])
        else:
            text = (g.get("native") or {}).get("text") or g.get("raw_output")
            out[iid] = parse_target_answer(items[iid], text)
    return out


def classify_pair(claim_a: Optional[Mapping[str, Any]], claim_b: Optional[Mapping[str, Any]]) -> str:
    """'agree' = both assert the same candidate; 'contradict' = both assert, different; 'missing' otherwise.

    Two abstentions are 'missing', never 'agree'.
    """
    va, vb = vote(claim_a), vote(claim_b)
    if va is None or vb is None:
        return "missing"
    return "agree" if normalise_answer(va) == normalise_answer(vb) else "contradict"


@dataclass
class Consensus:
    value: Optional[str]
    n_agree: int           # votes for the winning value (0 if unresolved)
    n_cast: int            # number of non-abstaining votes
    bucket: Optional[int]  # 1, 2, 3 (number of agreeing votes) or None if unresolved
    resolved: bool
    reason: str            # "ok" | "all_abstain" | "tie"
    dissent: bool          # some cast vote disagreed with the winner
    voters: List[str] = field(default_factory=list)


def consensus(votes: Mapping[str, Optional[str]]) -> Consensus:
    """Majority of cast votes. All-abstain and ties are unresolved; a single cast vote is bucket 1."""
    cast = {m: normalise_answer(v) for m, v in votes.items() if v is not None}
    if not cast:
        return Consensus(None, 0, 0, None, False, "all_abstain", False, [])
    counts: Dict[str, int] = {}
    for v in cast.values():
        counts[v] = counts.get(v, 0) + 1
    top = max(counts.values())
    winners = [v for v, c in counts.items() if c == top]
    if len(winners) > 1:
        return Consensus(None, 0, len(cast), None, False, "tie", True, sorted(cast))
    w = winners[0]
    orig = next(v for v in votes.values() if v is not None and normalise_answer(v) == w)
    voters = sorted(m for m, v in cast.items() if v == w)
    return Consensus(orig, top, len(cast), top, True, "ok", len(cast) > top, voters)


def loo_consistency(votes: Mapping[str, Optional[str]], method: str) -> str:
    """How `method` relates to the consensus of the OTHER methods (its own vote excluded).

    Returns 'agree' | 'disagree' | 'own_abstain' | 'unresolved' (others tie or all abstain).
    """
    own = votes.get(method)
    if own is None:
        return "own_abstain"
    others = {m: v for m, v in votes.items() if m != method}
    c = consensus(others)
    if not c.resolved:
        return "unresolved"
    return "agree" if normalise_answer(own) == normalise_answer(c.value) else "disagree"


# --------------------------------------------------------------------------------------
# pair bootstrap and rates
# --------------------------------------------------------------------------------------
@dataclass
class Rate:
    k: int
    n: int
    p: float
    lo: float
    hi: float
    n_pairs: int
    ci: str = "pair-bootstrap"

    def as_dict(self) -> dict:
        return {"k": self.k, "n": self.n, "p": self.p, "lo": self.lo, "hi": self.hi, "n_pairs": self.n_pairs, "ci": self.ci}

    def __str__(self) -> str:
        if self.n == 0:
            return f"0/0 (undefined)"
        return f"{self.k}/{self.n} = {100 * self.p:.1f}% [{100 * self.lo:.1f}, {100 * self.hi:.1f}] ({self.n_pairs} pairs)"


def pair_bootstrap_stat(pair_ids: Sequence[str], stat: Callable[[Sequence[str]], float], n_boot: int = N_BOOT, seed: int = SEED,
                        alpha: float = 0.05) -> Tuple[float, float, float]:
    """Resample base pairs with replacement; `stat(list_of_pair_ids_with_repeats)` -> float (nan allowed)."""
    pair_ids = list(pair_ids)
    est = float(stat(pair_ids))
    if len(pair_ids) == 0:
        return est, float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    vals = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, len(pair_ids), len(pair_ids))
        vals[b] = stat([pair_ids[i] for i in idx])
    if np.all(np.isnan(vals)):
        return est, float("nan"), float("nan")
    return est, float(np.nanquantile(vals, alpha / 2)), float(np.nanquantile(vals, 1 - alpha / 2))


def pair_rate(flags: Iterable[Tuple[str, Optional[bool]]], n_boot: int = N_BOOT, seed: int = SEED) -> Rate:
    """Rate over observations tagged with their pair id. flags: (pair_id, True/False/None); None = excluded
    from numerator and denominator. CI by pair bootstrap of the ratio of sums."""
    num: Dict[str, int] = {}
    den: Dict[str, int] = {}
    for pid, f in flags:
        num.setdefault(pid, 0)
        den.setdefault(pid, 0)
        if f is None:
            continue
        den[pid] += 1
        num[pid] += int(bool(f))
    pids = sorted(num)
    k, n = sum(num.values()), sum(den.values())

    def stat(ps: Sequence[str]) -> float:
        d = sum(den[p] for p in ps)
        return float("nan") if d == 0 else sum(num[p] for p in ps) / d

    if n == 0:
        return Rate(0, 0, float("nan"), float("nan"), float("nan"), len(pids))
    p, lo, hi = pair_bootstrap_stat(pids, stat, n_boot=n_boot, seed=seed)
    return Rate(k, n, p, lo, hi, len(pids))


def pair_rate_diff(flags_a: Iterable[Tuple[str, Optional[bool]]], flags_b: Iterable[Tuple[str, Optional[bool]]],
                   n_boot: int = N_BOOT, seed: int = SEED) -> Tuple[float, float, float]:
    """Paired (same pairs resampled) difference of two rates, a − b."""
    def acc(flags):
        num: Dict[str, int] = {}
        den: Dict[str, int] = {}
        for pid, f in flags:
            num.setdefault(pid, 0)
            den.setdefault(pid, 0)
            if f is None:
                continue
            den[pid] += 1
            num[pid] += int(bool(f))
        return num, den

    na, da = acc(flags_a)
    nb, db = acc(flags_b)
    pids = sorted(set(na) | set(nb))

    def stat(ps: Sequence[str]) -> float:
        d1 = sum(da.get(p, 0) for p in ps)
        d2 = sum(db.get(p, 0) for p in ps)
        if d1 == 0 or d2 == 0:
            return float("nan")
        return sum(na.get(p, 0) for p in ps) / d1 - sum(nb.get(p, 0) for p in ps) / d2

    return pair_bootstrap_stat(pids, stat, n_boot=n_boot, seed=seed)


# --------------------------------------------------------------------------------------
# primary endpoint: consensus-k vs best single reader on the same covered states
# --------------------------------------------------------------------------------------
def consensus_k_verdict(votes: Mapping[str, Optional[str]], k: int) -> Optional[str]:
    """Consensus with at least k agreeing votes; ties and all-abstain unresolved; k == n_methods needs unanimity."""
    c = consensus(votes)
    if not c.resolved or c.n_agree < k:
        return None
    if k >= len(votes) and c.n_cast != len(votes):
        return None
    return c.value


def consensus_vs_best_single(claims_by_method: Mapping[str, Mapping[str, Optional[dict]]], items: Mapping[str, dict], k: int,
                             item_ids: Optional[Sequence[str]] = None, methods: Sequence[str] = METHODS,
                             n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Accuracy of the consensus-k rule minus the best single reader's accuracy on the SAME covered states.

    Covered = states where the consensus-k rule gives a verdict. A single reader that abstains on a covered
    state is counted as not correct there (the rule is credited with a verdict on all covered states, so the
    comparison population is identical). The best reader is chosen by point estimate on the full covered set
    (reported) and re-selected inside every bootstrap resample, so the interval includes selection noise.
    Paired pair-level bootstrap: base pairs are resampled once per replicate and both arms recomputed on them.
    """
    ids = list(item_ids) if item_ids is not None else sorted({i for m in methods for i in claims_by_method[m]})
    n_cov: Dict[str, int] = {}
    k_cons: Dict[str, int] = {}
    k_read: Dict[str, Dict[str, int]] = {m: {} for m in methods}
    k_read_voted: Dict[str, Dict[str, int]] = {m: {} for m in methods}
    n_voted: Dict[str, Dict[str, int]] = {m: {} for m in methods}
    covered: List[str] = []
    for i in ids:
        p = items[i]["pair_id"]
        n_cov.setdefault(p, 0); k_cons.setdefault(p, 0)
        for m in methods:
            k_read[m].setdefault(p, 0); k_read_voted[m].setdefault(p, 0); n_voted[m].setdefault(p, 0)
        votes = {m: vote(claims_by_method[m].get(i)) for m in methods}
        v = consensus_k_verdict(votes, k)
        if v is None:
            continue
        covered.append(i)
        key = normalise_answer(items[i]["primary"]["answer"])
        n_cov[p] += 1
        k_cons[p] += int(normalise_answer(v) == key)
        for m in methods:
            ok = votes[m] is not None and normalise_answer(votes[m]) == key
            k_read[m][p] += int(ok)
            if votes[m] is not None:
                n_voted[m][p] += 1
                k_read_voted[m][p] += int(ok)
    pids = sorted(n_cov)

    def rates(ps: Sequence[str]):
        d = sum(n_cov[p] for p in ps)
        if d == 0:
            return float("nan"), {m: float("nan") for m in methods}
        return sum(k_cons[p] for p in ps) / d, {m: sum(k_read[m][p] for p in ps) / d for m in methods}

    def stat(ps: Sequence[str]) -> float:
        c, r = rates(ps)
        return float("nan") if np.isnan(c) else c - max(r.values())

    N = sum(n_cov.values())
    acc_c, acc_r = rates(pids)
    best = max(methods, key=lambda m: (acc_r[m] if not np.isnan(acc_r[m]) else -1))
    est, lo, hi = pair_bootstrap_stat(pids, stat, n_boot=n_boot, seed=seed) if N else (float("nan"), float("nan"), float("nan"))
    fixed = pair_bootstrap_stat(pids, lambda ps: (lambda c, r: float("nan") if np.isnan(c) else c - r[best])(*rates(ps)), n_boot=n_boot, seed=seed) if N else (float("nan"),) * 3
    return {
        "k": k, "n_states": len(ids), "n_covered": N, "coverage": (N / len(ids)) if ids else float("nan"), "covered_items": covered,
        "consensus_accuracy": {"k": sum(k_cons.values()), "n": N, "p": acc_c},
        "single_reader_accuracy_on_covered": {m: {"k": sum(k_read[m].values()), "n": N, "p": acc_r[m],
                                                  "k_given_voted": sum(k_read_voted[m].values()), "n_voted": sum(n_voted[m].values())} for m in methods},
        "best_single_reader": best,
        "difference_reselected_best": {"est": est, "lo": lo, "hi": hi},
        "difference_fixed_best": {"est": fixed[0], "lo": fixed[1], "hi": fixed[2]},
        "n_pairs": len(pids), "n_boot": n_boot, "seed": seed,
        "definition": "consensus-k accuracy minus best single reader accuracy on the same covered states; reader abstention on a covered state counts as not correct; paired pair bootstrap",
    }


# --------------------------------------------------------------------------------------
# Cohen's kappa (chance-corrected agreement) on states where both readers assert
# --------------------------------------------------------------------------------------
def kappa_from_counts(n: int, agree: int, a_pos0: int, b_pos0: int) -> float:
    """kappa over two candidate positions (0/1). n = states where both assert; a_pos0/b_pos0 = how often each chose position 0."""
    if n == 0:
        return float("nan")
    po = agree / n
    pa, pb = a_pos0 / n, b_pos0 / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    if pe >= 1.0:
        return float("nan")
    return (po - pe) / (1 - pe)


def candidate_position(item: Mapping[str, Any], value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    for j, c in enumerate(item["primary"]["candidates"]):
        if normalise_answer(c) == normalise_answer(value):
            return j
    if normalise_answer(value) in {normalise_answer(a) for a in item["primary"].get("answer_aliases", [])}:
        return item["primary"]["candidates"].index(item["primary"]["answer"])
    return None


def pair_kappa(claims_a: Mapping[str, Optional[dict]], claims_b: Mapping[str, Optional[dict]], items: Mapping[str, dict],
               item_ids: Sequence[str], n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Cohen's kappa between two readers with a pair-bootstrap CI; also returns the per-pair count table."""
    per_pair: Dict[str, Dict[str, int]] = {}
    for i in item_ids:
        p = items[i]["pair_id"]
        d = per_pair.setdefault(p, {"n_both": 0, "agree": 0, "a_pos0": 0, "b_pos0": 0})
        pa, pb = candidate_position(items[i], vote(claims_a.get(i))), candidate_position(items[i], vote(claims_b.get(i)))
        if pa is None or pb is None:
            continue
        d["n_both"] += 1
        d["agree"] += int(pa == pb)
        d["a_pos0"] += int(pa == 0)
        d["b_pos0"] += int(pb == 0)
    pids = sorted(per_pair)

    def stat(ps):
        return kappa_from_counts(sum(per_pair[p]["n_both"] for p in ps), sum(per_pair[p]["agree"] for p in ps),
                                 sum(per_pair[p]["a_pos0"] for p in ps), sum(per_pair[p]["b_pos0"] for p in ps))

    tot = {kk: sum(per_pair[p][kk] for p in pids) for kk in ("n_both", "agree", "a_pos0", "b_pos0")}
    est, lo, hi = pair_bootstrap_stat(pids, stat, n_boot=n_boot, seed=seed) if tot["n_both"] else (float("nan"),) * 3
    return {"kappa": est, "lo": lo, "hi": hi, **tot, "per_pair": per_pair, "n_pairs": len(pids)}


# --------------------------------------------------------------------------------------
# agreement matrix
# --------------------------------------------------------------------------------------
KINDS = ("agree", "contradict", "missing")


def agreement_matrix(claims_by_method: Mapping[str, Mapping[str, Optional[dict]]], item_ids: Sequence[str],
                     methods: Sequence[str] = METHODS) -> Tuple[Dict[str, np.ndarray], List[dict]]:
    """counts[kind] is an (m×m) int matrix over `methods`; the diagonal of 'agree' holds coverage counts.

    Also returns one record per (item, method_a, method_b) with the outcome, for CSVs and bootstraps.
    """
    m = len(methods)
    counts = {k: np.zeros((m, m), dtype=int) for k in KINDS}
    records: List[dict] = []
    for i, a in enumerate(methods):
        for j, b in enumerate(methods):
            for iid in item_ids:
                ca = claims_by_method.get(a, {}).get(iid)
                cb = claims_by_method.get(b, {}).get(iid)
                if i == j:
                    if vote(ca) is not None:
                        counts["agree"][i, i] += 1
                    else:
                        counts["missing"][i, i] += 1
                    continue
                kind = classify_pair(ca, cb)
                counts[kind][i, j] += 1
                if i < j:
                    records.append({"item_id": iid, "method_a": a, "method_b": b, "outcome": kind,
                                    "value_a": vote(ca), "value_b": vote(cb)})
    return counts, records


def matched_coverage(verdicts: Mapping[str, Mapping[str, Optional[str]]], item_ids: Sequence[str]) -> List[str]:
    """Items on which every rule in `verdicts` produced a verdict (not None)."""
    return [i for i in item_ids if all(v.get(i) is not None for v in verdicts.values())]


# --------------------------------------------------------------------------------------
# text + printing
# --------------------------------------------------------------------------------------
def readout_text(gen: Optional[Mapping[str, Any]], max_chars: int = 600) -> str:
    if gen is None:
        return "(no generation row)"
    nat = gen.get("native") or {}
    if "tokens" in nat:
        toks = nat["tokens"]
        scores = nat.get("scores") or [None] * len(toks)
        s = ", ".join(f"{t!r}:{sc:.2f}" if isinstance(sc, (int, float)) else repr(t) for t, sc in zip(toks, scores))
    elif "samples" in nat and nat["samples"]:
        s = nat["samples"][0]
    elif "text" in nat:
        s = nat["text"]
    else:
        s = gen.get("raw_output", "")
    s = str(s).replace("\n", " ⏎ ")
    return s if len(s) <= max_chars else s[: max_chars - 1] + "…"


def fmt_count(k: int, n: int) -> str:
    return f"{k}/{n}" + (f" = {100 * k / n:.1f}%" if n else " (n=0)")


def log(msg: str = "") -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------------------------
# plotting
# --------------------------------------------------------------------------------------
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
# fixed categorical slots (never re-cycled): NLA blue, Oracle lens orange, J-lens aqua, prompt-only violet
METHOD_COLORS = {"nla": "#2a78d6", "olens": "#eb6834", "jlens": "#1baf7a", "prompt_only": "#4a3aa7", "target": "#52514e"}
ARM_COLORS = {"genuine": "#2a78d6", "shuffled_recipient": "#eb6834", "shuffled_donor": "#1baf7a", "prompt_only": "#4a3aa7", "state_free": "#eda100"}
FAMILY_MARKERS = {"language": "o", "tense": "s", "ownership": "^", "mapping": "D"}
SEQ_BLUE = ["#fcfcfb", "#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]


def mpl():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "axes.edgecolor": GRID, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2, "text.color": INK,
        "axes.spines.top": False, "axes.spines.right": False, "font.size": 9.5, "axes.titlesize": 10.5,
        "axes.titleweight": "bold", "legend.frameon": False,
    })
    return plt


def style_ax(ax, ylabel: Optional[str] = None, ylim=(0, 1.05), pct: bool = True) -> None:
    ax.grid(axis="y", color=GRID, lw=0.8, zorder=0)
    ax.set_axisbelow(True)
    if ylabel:
        ax.set_ylabel(ylabel)
    if ylim is not None:
        ax.set_ylim(*ylim)
    if pct:
        ax.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
        ax.set_yticklabels(["0", "25", "50", "75", "100"])


def bar_ci(ax, x: float, rate: Rate, color: str, width: float = 0.6, label: Optional[str] = None, hollow: bool = False,
           annotate: bool = True) -> None:
    """One bar with a 95% pair-bootstrap CI whisker and the raw k/n printed above it."""
    p = 0.0 if np.isnan(rate.p) else rate.p
    if hollow:
        ax.bar(x, p, width=width, facecolor="none", edgecolor=color, lw=1.4, label=label, zorder=3)
    else:
        ax.bar(x, p, width=width, color=color, edgecolor=SURFACE, lw=1, label=label, zorder=3)
    if not np.isnan(rate.lo):
        ax.errorbar(x, p, yerr=[[max(p - rate.lo, 0)], [max(rate.hi - p, 0)]], color=INK, lw=1.1, capsize=3, zorder=5)
    if annotate:
        top = rate.hi if not np.isnan(rate.hi) else p
        ax.text(x, min(top + 0.03, 1.1), f"{rate.k}/{rate.n}", ha="center", va="bottom", fontsize=7.5, color=INK2)


def draw_matrix(ax, counts: np.ndarray, methods: Sequence[str], title: str, n_items: int, cmap_hex: Sequence[str] = SEQ_BLUE,
                extra: Optional[Mapping[Tuple[int, int], str]] = None) -> None:
    from matplotlib.colors import LinearSegmentedColormap

    cmap = LinearSegmentedColormap.from_list("seq", cmap_hex)
    m = len(methods)
    frac = counts / max(n_items, 1)
    ax.imshow(frac, cmap=cmap, vmin=0, vmax=1)
    for i in range(m):
        for j in range(m):
            if i == j:
                ax.text(j, i, "–", ha="center", va="center", color=INK2, fontsize=9)
                continue
            c = counts[i, j]
            txt = f"{c}/{n_items}\n{100 * c / max(n_items, 1):.0f}%"
            if extra and (i, j) in extra:
                txt += "\n" + extra[(i, j)]
            ax.text(j, i, txt, ha="center", va="center", fontsize=7 if extra else 8, linespacing=1.15, color=SURFACE if frac[i, j] > 0.55 else INK)
    ax.set_xticks(range(m))
    ax.set_yticks(range(m))
    ax.set_xticklabels([METHOD_LABELS.get(x, x) for x in methods], fontsize=8)
    ax.set_yticklabels([METHOD_LABELS.get(x, x) for x in methods], fontsize=8)
    ax.set_title(title)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
