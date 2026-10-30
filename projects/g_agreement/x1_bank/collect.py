"""X1 collection (GPU; BRIEF_X.md §X1). Natural block-42 last-token states of every items_x.json pair and
each reader's native paired log-odds (core/scoring_lo.py) on both states of a pair, candidates
(own answer, other candidate), family passed through to the NLA templates.

    python -m projects.g_agreement.x1_bank.collect --freeze-x                 # CPU: write manifest/frozen_config_x.json
    python -m projects.g_agreement.x1_bank.collect --phase A --split dev --allow-unfrozen   # smoke
    python -m projects.g_agreement.x1_bank.collect --phase A                  # target + J-lens + OLens (test)
    python -m projects.g_agreement.x1_bank.collect --phase B                  # NLA (target unloaded)

Outputs (resumable by ``key``):
  cache/g_agreement/states/<item_id>.pt + states_meta.jsonl   shared state cache (x-prefixed ids; module x1 ledger rows)
  cache/g_agreement/x/x1_lo.jsonl   key ``<reader>|<item_id>``   E1 rows: lo = lp(own answer) - lp(other)
                                    key ``<reader>|mean|<family>`` E3 rows: LO of the family MEAN state, per pair
Ledger steps: capture (module x1), x1_lo_<reader>, x1_mean_lo_<reader>, load_target, load_nla. Log: results/g_agreement/x1/log.md.
Test items need manifest/frozen_config_x.json (items_x sha + core/x code shas; code mismatch is a note, both shas
are recorded per row); dev items may run unfrozen.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core import states as S
from projects.g_agreement.core.accounting import StepLedger, append_jsonl, done_ids, log_line, now_iso, timed_call

MODULE = "x1"
X_DIR = C.CACHE_DIR / "x"
LO_PATH = X_DIR / "x1_lo.jsonl"
LOG = C.RESULTS_DIR / "x1" / "log.md"
ITEMS_X = C.DATASET_DIR / "items_x.json"
ITEMS_X3 = C.DATASET_DIR / "items_x3_candidates.json"
FROZEN_X = C.MANIFEST_DIR / "frozen_config_x.json"
X_FAMILIES = ("ownership", "mapping", "language", "tense")
X_MODULE_DIRS = ("x1_bank", "x2_causal", "x3_floor")


# ------------------------------------------------------------------ Phase X freeze (BRIEF_X §Dataset, "Freeze")
def x_code_files() -> list[Path]:
    files = sorted(C.HERE.glob("*.py"))
    files += [C.DATASET_DIR / "build_dataset_x.py", C.DATASET_DIR / "build_x3.py"]
    for sub in X_MODULE_DIRS:
        files += sorted((C.PROJECT_DIR / sub).glob("*.py"))
    return [f for f in files if f.exists()]


def snapshot_x(frozen: bool) -> dict[str, Any]:
    return {"frozen": frozen, "frozen_at": now_iso(), "phase": "X",
            "items_x_sha256": C.sha256_file(ITEMS_X), "items_x_meta_sha256_items": C.dataset_meta(ITEMS_X).get("sha256_items"),
            "items_x3_sha256": C.sha256_file(ITEMS_X3), "core_code_sha256": C.sha256_tree(C.core_code_files()),
            "x_code_sha256": C.sha256_tree(x_code_files()), "nla_templates": LO.NLA_TEMPLATES,
            "base_manifest": C.frozen_shas(), "assets": C.snapshot(frozen=False)["assets"], "site": C.snapshot(frozen=False)["site"]}


def freeze_x(force: bool = False) -> Path:
    if FROZEN_X.exists() and not force and json.loads(FROZEN_X.read_text()).get("frozen"):
        raise RuntimeError(f"{FROZEN_X} is already frozen; pass --force (and add a dated Deviations note to BRIEF_X.md)")
    C.MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    FROZEN_X.write_text(json.dumps(snapshot_x(True), indent=1, ensure_ascii=False) + "\n")
    return FROZEN_X


def frozen_status_x(items_path: Path = ITEMS_X, path: Path | None = None) -> tuple[bool, list[str]]:
    """(ok, problems): the X manifest exists, is frozen and the items_x / items_x3 shas match disk.
    Code-sha drift is a note only (both shas are recorded per row), as for the G5/G6 follow-ups."""
    path = FROZEN_X if path is None else path  # resolved at call time (tests monkeypatch FROZEN_X)
    if not path.exists():
        return False, [f"{path.name} missing (run x1_bank.collect --freeze-x)"]
    fz = json.loads(path.read_text())
    problems = []
    if not fz.get("frozen"):
        problems.append("frozen is false")
    if fz.get("items_x_sha256") != C.sha256_file(items_path):
        problems.append("items_x.json changed since the X freeze")
    if fz.get("items_x3_sha256") != C.sha256_file(ITEMS_X3):
        problems.append("items_x3_candidates.json changed since the X freeze")
    now = snapshot_x(True)
    for k in ("core_code_sha256", "x_code_sha256"):
        if fz.get(k) != now.get(k):
            print(f"[x1] note: {k} changed since the X freeze ({str(fz.get(k))[:12]} -> {str(now.get(k))[:12]}); accepted, both recorded per row")
    return not problems, problems


def require_frozen_x(split: str, allow_unfrozen: bool, items_path: Path = ITEMS_X) -> None:
    if split == "dev" or allow_unfrozen:
        return
    ok, problems = frozen_status_x(items_path)
    if not ok:
        raise SystemExit(f"refusing to collect on split={split}: " + "; ".join(problems))


def x_shas(items_path: Path = ITEMS_X) -> dict[str, Any]:
    """Recorded per row: the X manifest's shas and the current ones."""
    out: dict[str, Any] = {"items_file": str(items_path), "items_file_sha256": C.sha256_file(items_path),
                           "current_core_code_sha256": C.sha256_tree(C.core_code_files()),
                           "current_x_code_sha256": C.sha256_tree(x_code_files()), "manifest_x": None,
                           "frozen_core_code_sha256": None, "frozen_x_code_sha256": None}
    if FROZEN_X.exists():
        fz = json.loads(FROZEN_X.read_text())
        out.update(manifest_x=FROZEN_X.name, frozen_core_code_sha256=fz.get("core_code_sha256"), frozen_x_code_sha256=fz.get("x_code_sha256"))
    return out


# ------------------------------------------------------------------ pairs
def other_candidate(item: dict[str, Any]) -> str:
    (other,) = [c for c in item["primary"]["candidates"] if c != item["primary"]["answer"]]
    return other


def load_pairs(items_path: Path = ITEMS_X, split: str = "test", limit_pairs: int = 0,
               families: tuple[str, ...] = X_FAMILIES, items: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Complete A/B pairs of the requested split, grouped by family in the items' order; ``limit_pairs``
    is per family (dev smoke = 1 pair per family)."""
    items = items if items is not None else C.load_items(split, 0, path=items_path)
    by_pair: dict[str, dict[str, Any]] = {}
    for it in items:
        if it["family"] not in families or (split != "all" and it["split"] != split):
            continue
        by_pair.setdefault(it["pair_id"], {"pair_id": it["pair_id"], "family": it["family"], "split": it["split"]})[it["version"]] = it
    pairs = [p for p in by_pair.values() if "A" in p and "B" in p]
    out: list[dict[str, Any]] = []
    for fam in families:
        out += [p for p in pairs if p["family"] == fam][: limit_pairs or None]
    return out


def pair_items(pairs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [p[v] for p in pairs for v in ("A", "B")]


def lo_key(reader: str, item_id: str) -> str:
    return f"{reader}|{item_id}"


def mean_key(reader: str, family: str) -> str:
    return f"{reader}|mean|{family}"


def _row_extra(r: dict[str, Any]) -> dict[str, Any]:
    return {k: r[k] for k in ("per_template", "variants_A", "variants_B", "best_A", "best_B", "reason", "n_tokens_A", "n_tokens_B") if k in r}


# ------------------------------------------------------------------ states
def capture_states(target: M.Target, pairs: list[dict[str, Any]], *, states_dir: Path | None = None, meta_path: Path | None = None,
                   ledger_path: Path | None = None, log_path: Path | None = LOG) -> dict[str, dict[str, Any]]:
    """Block-42 last-token state of every item of the pairs into the shared cache (natural states only;
    no off-grid layers for X dev items)."""
    meta = S.ensure_states(target, pair_items(pairs), states_dir=states_dir, meta_path=meta_path, ledger_path=ledger_path,
                           module=MODULE, extra_dev_layers=())
    if log_path:
        log_line(log_path, f"states: {len(meta)} items cached ({len(pairs)} pairs)")
    return meta


# ------------------------------------------------------------------ LO (E1 rows)
def collect_lo(reader: Any, pairs: list[dict[str, Any]], *, lo_path: Path = LO_PATH, ledger_path: Path | None = None,
               log_path: Path | None = LOG, states_dir: Path | None = None, batch: int = 32, items_path: Path = ITEMS_X) -> int:
    """E1 rows: one per (reader, item); both states of a pair and both candidates of a state are scored in
    the same forward batch. Key ``<reader>|<item_id>``; resumable."""
    import torch

    done = done_ids(lo_path, key="key")
    ledger = StepLedger(step=f"x1_lo_{reader.name}", module=MODULE, extra={"batch": batch})
    shas = x_shas(items_path)
    n = 0
    per = max(1, batch // 2)  # pairs per chunk (2 states each)
    for fam in sorted({p["family"] for p in pairs}):
        todo = [p for p in pairs if p["family"] == fam and any(lo_key(reader.name, p[v]["item_id"]) not in done for v in "AB")]
        for s in range(0, len(todo), per):
            chunk = todo[s: s + per]
            its = pair_items(chunk)
            H = torch.stack([S.load_state(it["item_id"], states_dir) for it in its])
            cands = [(it["primary"]["answer"], other_candidate(it)) for it in its]
            with timed_call() as st:
                rows = LO.score_lo(reader, H, cands, fam, batch=batch)
            for it, r in zip(its, rows):
                key = lo_key(reader.name, it["item_id"])
                if key in done:
                    continue
                append_jsonl(lo_path, {"key": key, "module": MODULE, "reader": reader.name, "item_id": it["item_id"], "pair_id": it["pair_id"],
                                       "family": fam, "split": it["split"], "version": it["version"], "condition": "natural",
                                       "cand_A": r["cand_A"], "cand_B": r["cand_B"], "lo": r["lo"], "lp_A": r["lp_A"], "lp_B": r["lp_B"],
                                       "templates": r["templates"], "unscorable": r["unscorable"], **_row_extra(r),
                                       "wall_s_chunk": st.wall_s, "chunk_size": len(its), "created_at": now_iso(), **shas})
                n += 1
            ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        print(f"[x1/lo/{reader.name}] {fam}: {len(todo)} pairs scored", flush=True)
    r = ledger.flush(ledger_path)
    if log_path and r:
        log_line(log_path, f"lo {reader.name}: {r}")
    return n


# ------------------------------------------------------------------ E3: LO on the family mean state
def collect_mean_lo(reader: Any, pairs: list[dict[str, Any]], *, lo_path: Path = LO_PATH, ledger_path: Path | None = None,
                    log_path: Path | None = LOG, states_dir: Path | None = None, batch: int = 32, items_path: Path = ITEMS_X) -> int:
    """E3 rows: the reader's LO on the MEAN of the family's states, scored against every pair's candidates
    in the A orientation (own answer of version A, other); one row per (reader, family), key
    ``<reader>|mean|<family>`` with the per-pair list and the mean (sanity band [-1, 1] nats)."""
    import torch

    done = done_ids(lo_path, key="key")
    ledger = StepLedger(step=f"x1_mean_lo_{reader.name}", module=MODULE)
    shas = x_shas(items_path)
    n = 0
    for fam in sorted({p["family"] for p in pairs}):
        key = mean_key(reader.name, fam)
        if key in done:
            continue
        fp = [p for p in pairs if p["family"] == fam]
        its = pair_items(fp)
        hs = torch.stack([S.load_state(it["item_id"], states_dir) for it in its])
        h_mean = hs.mean(0)
        cands = [(p["A"]["primary"]["answer"], other_candidate(p["A"])) for p in fp]
        with timed_call() as st:
            rows = LO.score_lo(reader, h_mean[None].expand(len(fp), -1).contiguous(), cands, fam, batch=batch)
        per_pair = [{"pair_id": p["pair_id"], "cand_A": r["cand_A"], "cand_B": r["cand_B"], "lo": r["lo"], "unscorable": r["unscorable"]}
                    for p, r in zip(fp, rows)]
        los = [x["lo"] for x in per_pair if not x["unscorable"] and x["lo"] is not None]
        mean_lo = sum(los) / len(los) if los else None
        append_jsonl(lo_path, {"key": key, "module": MODULE, "reader": reader.name, "family": fam, "condition": "mean_state",
                               "n_states_in_mean": len(its), "state_item_ids": [it["item_id"] for it in its], "mean_norm": float(h_mean.norm()),
                               "per_pair": per_pair, "n_scorable": len(los), "mean_lo": mean_lo,
                               "mean_abs_lo": (sum(abs(x) for x in los) / len(los)) if los else None,
                               "within_band": (abs(mean_lo) <= 1.0) if mean_lo is not None else None,
                               "templates": rows[0]["templates"] if rows else None, "wall_s": st.wall_s, "created_at": now_iso(), **shas})
        ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        n += 1
        print(f"[x1/mean_lo/{reader.name}] {fam}: mean LO {mean_lo}", flush=True)
    r = ledger.flush(ledger_path)
    if log_path and r:
        log_line(log_path, f"mean_lo {reader.name}: {r}")
    return n


# ------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "B"], default=None)
    ap.add_argument("--items-file", default=str(ITEMS_X))
    ap.add_argument("--split", choices=["dev", "test", "all"], default="test")
    ap.add_argument("--limit-pairs", type=int, default=0, help="per family")
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--freeze-x", action="store_true", help="write manifest/frozen_config_x.json and exit (CPU)")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    if a.freeze_x:
        print(f"wrote {freeze_x(force=a.force)}")
        return 0
    if a.phase is None:
        ap.error("--phase A|B is required (or --freeze-x)")
    items_path = Path(a.items_file)
    require_frozen_x(a.split, a.allow_unfrozen, items_path)
    pairs = load_pairs(items_path, a.split, a.limit_pairs)
    if not pairs:
        raise SystemExit("no pairs selected")
    X_DIR.mkdir(parents=True, exist_ok=True)
    fams = {f: sum(p["family"] == f for p in pairs) for f in X_FAMILIES}
    print(f"X1 phase {a.phase}: split={a.split} pairs per family {fams}; shas={x_shas(items_path)}")
    log_line(LOG, f"phase {a.phase}: split={a.split} pairs={fams} items_file={items_path} sha={C.sha256_file(items_path)}")
    if a.phase == "A":
        target = load_target_timed(MODULE)
        capture_states(target, pairs)
        jl = R.JLensReader().bind(target)
        collect_lo(jl, pairs, batch=a.batch, items_path=items_path)
        collect_mean_lo(jl, pairs, batch=a.batch, items_path=items_path)
        del jl
        ol = R.OLensReader().bind(target)
        log_line(LOG, f"olens adapter={ol.adapter_dir} liveness={ol.liveness}")
        collect_lo(ol, pairs, batch=a.batch, items_path=items_path)
        collect_mean_lo(ol, pairs, batch=a.batch, items_path=items_path)
        M.unload(target)
    else:
        missing = [it["item_id"] for it in pair_items(pairs) if not S.state_path(it["item_id"]).exists()]
        if missing:
            raise SystemExit(f"missing cached states {missing[:4]}; run phase A first")
        ledger = StepLedger(step="load_nla", module=MODULE)
        with timed_call() as st:
            nla = R.NLAReader().bind()
        ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        ledger.flush()
        log_line(LOG, f"phase B: nla adapter={nla.adapter_dir} liveness={nla.liveness}")
        collect_lo(nla, pairs, batch=a.batch, items_path=items_path)
        collect_mean_lo(nla, pairs, batch=a.batch, items_path=items_path)
        nla.unload()
    return 0


if __name__ == "__main__":
    sys.exit(main())
