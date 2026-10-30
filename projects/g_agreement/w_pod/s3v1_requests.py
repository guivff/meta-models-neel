"""S3v1 — the V1/V2 pod requests of results/g_agreement/v/v12_pod_requests.json (written by v12_readers.pod_requests), on the cached Y1 captures.

    python -m projects.g_agreement.w_pod.s3v1_requests --phase A|B [--force]

Request "v1_layer_sweep": every item of the listed sets (dict {set: {n, item_ids}}; entries without item_ids are ignored) at the
PENDING sites (``pending_sites`` "<L>:0"; else every layer), readers jlens (native L; a layer the lens lacks → unscorable row with a
reason), olens (nearest grid layer, recorded), olens_trueL (true-layer carrier), nla (phase B, L42 transfer). Rows in the y1_lo.jsonl
schema (key reader|<L>:0|item_id, lo_actual = lp(actual) − lp(other), favours_actual, …) plus one E3 mean-state row per (reader, site,
set) → cache/g_agreement/w/s3v1_lo.jsonl (ingested on the Mac with --extra-lo). Request "three_way": the listed items with candidates
{correct, actual, km1} at ``sites``; the three strings are scored in ONE forward batch per state (jlens max-variant cosine; olens
summed bullet log-prob; nla mean puzzle-template log-prob) → rows {reader, site, layer, layer_used, item_id, set, family, candidates,
lp {correct, actual, km1}, unscorable, format, created_at} appended to cache/g_agreement/v/v2_three_way.jsonl (the request's path;
key reader|site|item_id). Resumable. NON-FATAL: any exception is written to results/g_agreement/w/s3/FAILED_s3v1_<phase> and the
process exits 0, so the chain continues; a missing request file writes S3V1_SKIPPED. DONE_s3v1_<phase> under results/g_agreement/w/s3/."""

from __future__ import annotations

import argparse
import json
import re
import sys
import traceback
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import append_jsonl, done_ids, now_iso, timed_call
from projects.g_agreement.y1_site import collect as Y1

from . import common as W
from . import scoring_multi as SM

STAGE = "s3"
UNIT = "s3v1"
PHASE_READERS = {"A": ("jlens", "olens", "olens_trueL"), "B": ("nla",)}
THREE_WAY_OUT = C.CACHE_DIR / "v" / "v2_three_way.jsonl"
THREE_KEYS = ("correct", "actual", "km1")


# ------------------------------------------------------------------ parsing
def _pos_label(p: Any) -> str:
    m = re.match(r"\s*(candA|candB|\d+)", str(p))
    return m.group(1) if m else "0"


def _site(s: str) -> tuple[int, str]:
    L, P = str(s).split(":")
    return int(L), _pos_label(P)


def load_requests(path: Path | None = None) -> list[dict[str, Any]]:
    """Normalised requests: {name, kind pair|three_way, item_ids|items, sites [(L, P)], readers [names], sets {item_id: set}}."""
    p = path or W.V12_REQUESTS
    if not p.exists():
        return []
    obj = json.loads(p.read_text(encoding="utf-8"))
    reqs = obj.get("requests", obj) if isinstance(obj, dict) else obj
    out = []
    for i, r in enumerate(reqs):
        readers = r.get("readers", ["jlens", "olens", "nla"])
        readers = list(readers) if isinstance(readers, (list, tuple)) else list(readers.keys())
        name = r.get("name", f"req{i}")
        three = (r.get("candidates") == "three_way") or (name == "three_way") or isinstance(r.get("items"), list) and bool(r["items"]) and isinstance(r["items"][0].get("candidates"), dict)
        if r.get("sites"):
            sites = [_site(s) for s in r["sites"]]
        elif r.get("pending_sites"):
            sites = [_site(s) for s in r["pending_sites"]]
        else:
            sites = [(int(L), _pos_label(r.get("position", "0"))) for L in r.get("layers", list(Y1.LAYERS))]
        rec: dict[str, Any] = {"name": name, "kind": "three_way" if three else "pair", "sites": sites, "readers": readers, "set_of": {}, "item_ids": [], "items": []}
        sets = r.get("sets")
        if isinstance(sets, dict):
            for sname, sv in sets.items():
                ids = sv.get("item_ids") if isinstance(sv, dict) else (sv if isinstance(sv, list) else None)
                if ids:
                    for iid in ids:
                        rec["set_of"][str(iid)] = sname
                    rec["item_ids"] += [str(x) for x in ids]
        elif isinstance(sets, list):
            rec["set_names"] = [str(x) for x in sets]
        if r.get("item_ids"):
            rec["item_ids"] += [str(x) for x in r["item_ids"]]
        if three:
            for it in r.get("items") or []:
                c = it.get("candidates") or {}
                if all(k in c for k in THREE_KEYS):
                    rec["items"].append({"item_id": str(it["item_id"]), "candidates": {k: str(c[k]) for k in THREE_KEYS}, "family": it.get("family", "puzzle"), "set": it.get("set", "error")})
            rec["third_candidates"] = r.get("third_candidates") or {}
            rec["third_field"] = r.get("third_field")
        rec["output"] = r.get("output")
        out.append(rec)
    return out


def _field(item: dict[str, Any], dotted: str | None) -> Any:
    if not dotted:
        return None
    cur: Any = item
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def request_items(req: dict[str, Any], items_y1: Path | None = None) -> list[dict[str, Any]]:
    """Items with ``cands`` = [actual, other] (pair) or [correct, actual, km1] (three_way) and ``set``."""
    raw = json.loads((items_y1 or W.ITEMS_Y1).read_text(encoding="utf-8"))
    by_id = {it["item_id"]: it for it in (raw["items"] if isinstance(raw, dict) else raw)}
    out = []
    if req["kind"] == "three_way" and req["items"]:
        for e in req["items"]:
            it = by_id.get(e["item_id"], {"item_id": e["item_id"], "family": e["family"], "set": e["set"], "primary": {"candidates": [e["candidates"]["actual"], e["candidates"]["correct"]]}})
            out.append({**it, "set": it.get("set", e["set"]), "cands": [e["candidates"][k] for k in THREE_KEYS], "cand_map": dict(e["candidates"])})
        return out
    ids = req["item_ids"] or [i for i, it in by_id.items() if it.get("set") in set(req.get("set_names") or ["error"])]
    for iid in ids:
        it = by_id.get(iid)
        if it is None:
            continue
        a, b = str(it["primary"]["candidates"][0]), str(it["primary"]["candidates"][1])
        if req["kind"] == "three_way":
            third = req["third_candidates"].get(iid) or _field(it, req.get("third_field"))
            if third is None or str(third) in (a, b):
                continue
            correct = str((it.get("source") or {}).get("correct", b))
            out.append({**it, "set": req["set_of"].get(iid, it.get("set")), "cands": [correct, a, str(third)], "cand_map": {"correct": correct, "actual": a, "km1": str(third)}})
        else:
            out.append({**it, "set": req["set_of"].get(iid, it.get("set")), "cands": [a, b]})
    return out


# ------------------------------------------------------------------ scoring
def reader_layer(name: str, layer: int) -> int | None:
    return Y1.reader_layer(name, layer)


def _vectors(items: list[dict[str, Any]], layer: int, plabel: str, caps_dir: Path | None) -> tuple[list[Any], list[dict[str, Any]], list[dict[str, Any]]]:
    vecs, keep, missing = [], [], []
    for it in items:
        try:
            v = Y1.cell_vector(Y1.load_cap(it["item_id"], caps_dir or W.Y1_CAPS_DIR), layer, plabel)
        except (FileNotFoundError, KeyError):
            v = None
        (missing if v is None else keep).append(it)
        if v is not None:
            vecs.append(v)
    return vecs, keep, missing


def score_pair_request(reader: Any, req: dict[str, Any], items: list[dict[str, Any]], *, reader_name: str | None = None, lo_path: Path | None = None, caps_dir: Path | None = None,
                       batch: int = 32, ledger_path: Path | None = None, mean_rows: bool = True) -> int:
    """y1_lo-schema rows (key reader|L:P|item_id) + one E3 mean-state row per (reader, site, set)."""
    import torch

    name = reader_name or reader.name
    lo_path = lo_path or W.S3V1_LO
    done = done_ids(lo_path, key="key")
    shas = C.frozen_shas()
    led = W.ledger(f"s3v1_{req['name']}_{name}")
    n = 0
    for layer, plabel in req["sites"]:
        site = f"{layer}:{plabel}"
        L_used = reader_layer(name, layer)
        jl_ok = (name != "jlens") or (layer in (getattr(reader, "J", None) or {}))
        base = {"reader": name, "reader_class": type(reader).__name__, "site": site, "layer": layer, "position": plabel, "layer_used": L_used,
                "layer_role": ("native" if name == "jlens" else "nearest_grid" if name == "olens" else "true_layer_sensitivity" if name == "olens_trueL" else "transfer_from_L42"),
                "request": req["name"], **shas}
        todo = [it for it in items if Y1.lo_key(name, site, it["item_id"]) not in done]
        vecs, keep, missing = _vectors(todo, layer, plabel, caps_dir)
        for it in missing + ([] if jl_ok else keep):
            append_jsonl(lo_path, {"key": Y1.lo_key(name, site, it["item_id"]), **base, "item_id": it["item_id"], "family": it.get("family"), "set": it.get("set"),
                                   "cand_actual": it["cands"][0], "cand_other": it["cands"][1], "text_key": it.get("text_key"), "lo_actual": None, "lp_actual": None, "lp_other": None,
                                   "favours_actual": None, "unscorable": True, "reason": ("lens file lacks this layer" if not jl_ok else f"position {plabel} absent / capture missing"),
                                   "created_at": now_iso()})
            n += 1
        if not jl_ok:
            continue
        kw = {"layer": L_used} if L_used is not None else {}
        for s in range(0, len(keep), batch):
            chunk, H = keep[s: s + batch], torch.stack(vecs[s: s + batch])
            fam = chunk[0].get("family", "puzzle")
            with timed_call() as st:
                res = LO.score_lo(reader, H, [(it["cands"][0], it["cands"][1]) for it in chunk], fam, batch=batch, **kw)
            for it, r in zip(chunk, res):
                row = {"key": Y1.lo_key(name, site, it["item_id"]), **base, "item_id": it["item_id"], "family": it.get("family"), "set": it.get("set"), "cand_actual": r["cand_A"],
                       "cand_other": r["cand_B"], "text_key": it.get("text_key"), "lo_actual": r["lo"], "lp_actual": r["lp_A"], "lp_other": r["lp_B"],
                       "favours_actual": (r["lo"] > 0) if r["lo"] is not None else None, "templates": r["templates"], "unscorable": r["unscorable"], "wall_s_chunk": st.wall_s,
                       "chunk_size": len(chunk), "created_at": now_iso()}
                for k in ("per_template", "variants_A", "variants_B", "best_A", "best_B", "reason", "n_tokens_A", "n_tokens_B", "format", "layer_in_prompt"):
                    if k in r:
                        row[k] = r[k]
                append_jsonl(lo_path, row)
                n += 1
            led.add(0, 0, st.wall_s, st.peak_mem_gb)
        if mean_rows:
            allv, allk, _ = _vectors(items, layer, plabel, caps_dir)
            for set_ in sorted({it.get("set") for it in allk if it.get("set")}):
                k = f"{name}|{site}|mean|{set_}"
                its = [it for it in allk if it.get("set") == set_]
                if k in done or not its:
                    continue
                Hs = torch.stack([v for v, it in zip(allv, allk) if it.get("set") == set_])
                h_mean = Hs.mean(0)
                with timed_call() as st:
                    rows = LO.score_lo(reader, h_mean[None].expand(len(its), -1).contiguous(), [(it["cands"][0], it["cands"][1]) for it in its], its[0].get("family", "puzzle"), batch=batch, **kw)
                los = [r["lo"] for r in rows if not r["unscorable"] and r["lo"] is not None]
                mean_lo = sum(los) / len(los) if los else None
                append_jsonl(lo_path, {"key": k, **base, "condition": "mean_state", "set": set_, "family": its[0].get("family"), "n_states_in_mean": len(its), "mean_norm": float(h_mean.norm()),
                                       "n_scorable": len(los), "mean_lo": mean_lo, "mean_abs_lo": (sum(abs(x) for x in los) / len(los)) if los else None,
                                       "within_band": (abs(mean_lo) <= Y1.E3_BAND) if mean_lo is not None else None, "band": Y1.E3_BAND, "wall_s": st.wall_s, "created_at": now_iso()})
                n += 1
        print(f"[w/s3v1/{name}] {req['name']} @ {site}: {len(todo)} items", flush=True)
    rr = led.flush(ledger_path)
    if rr:
        W.wlog(f"s3v1 {led.step}: {rr}")
    return n


def score_three_way(reader: Any, req: dict[str, Any], items: list[dict[str, Any]], *, reader_name: str | None = None, out_path: Path | None = None, caps_dir: Path | None = None,
                    batch: int = 32, ledger_path: Path | None = None) -> int:
    """Rows in the request's schema (reader, site, layer, layer_used, item_id, set, family, candidates {correct, actual, km1}, lp {…}, unscorable, format)."""
    import torch

    name = reader_name or reader.name
    out_path = out_path or THREE_WAY_OUT
    done = done_ids(out_path, key="key")
    led = W.ledger(f"s3v1_{req['name']}_{name}")
    fmt = {"jlens": "cosine", "olens": "bullet", "olens_trueL": "bullet", "nla": "nla_templates"}.get(name, name)
    n = 0
    for layer, plabel in req["sites"]:
        site = f"{layer}:{plabel}"
        L_used = reader_layer(name, layer)
        jl_ok = (name != "jlens") or (layer in (getattr(reader, "J", None) or {}))
        todo = [it for it in items if f"{name}|{site}|{it['item_id']}" not in done]
        vecs, keep, missing = _vectors(todo, layer, plabel, caps_dir)
        for it in missing + ([] if jl_ok else keep):
            append_jsonl(out_path, {"key": f"{name}|{site}|{it['item_id']}", "reader": name, "site": site, "layer": layer, "layer_used": L_used, "item_id": it["item_id"], "set": it.get("set"),
                                    "family": it.get("family"), "candidates": it["cand_map"], "lp": {k: None for k in THREE_KEYS}, "unscorable": True,
                                    "reason": ("lens file lacks this layer" if not jl_ok else "capture / position missing"), "format": fmt, "created_at": now_iso()})
            n += 1
        if not jl_ok:
            continue
        kw = {"layer": L_used} if L_used is not None else {}
        for s in range(0, len(keep), batch):
            chunk, H = keep[s: s + batch], torch.stack(vecs[s: s + batch])
            with timed_call() as st:
                res = SM.score_candidates(reader, H, [it["cands"] for it in chunk], "puzzle", batch=batch, **kw)
            for it, q in zip(chunk, res):
                lp = {k: q["scores"][j] for j, k in enumerate(THREE_KEYS)}
                append_jsonl(out_path, {"key": f"{name}|{site}|{it['item_id']}", "reader": name, "site": site, "layer": layer, "layer_used": L_used, "item_id": it["item_id"], "set": it.get("set"),
                                        "family": it.get("family"), "candidates": it["cand_map"], "lp": lp, "unscorable": any(v is None for v in lp.values()), "argmax": q["argmax"],
                                        "format": fmt, "templates": q["templates"], "request": req["name"], "wall_s_chunk": st.wall_s, "chunk_size": len(chunk), "created_at": now_iso()})
                n += 1
            led.add(0, 0, st.wall_s, st.peak_mem_gb)
        print(f"[w/s3v1/{name}] {req['name']} @ {site}: {len(todo)} items (three-way)", flush=True)
    rr = led.flush(ledger_path)
    if rr:
        W.wlog(f"s3v1 {led.step}: {rr}")
    return n


def score_request(reader: Any, req: dict[str, Any], items: list[dict[str, Any]], **kw: Any) -> int:
    if req["kind"] == "three_way":
        return score_three_way(reader, req, items, **{k: v for k, v in kw.items() if k != "lo_path"}, **({"out_path": kw["lo_path"]} if "lo_path" in kw else {}))
    return score_pair_request(reader, req, items, **kw)


# ------------------------------------------------------------------ main (non-fatal)
def run(phase: str, batch: int) -> dict[str, int]:
    reqs = load_requests()
    wanted = [r for r in reqs if any(x in PHASE_READERS[phase] for x in r["readers"])]
    W.wlog(f"s3v1 phase {phase}: {len(wanted)} requests {[(r['name'], r['kind'], len(r['sites'])) for r in wanted]}")
    counts: dict[str, int] = {}
    if not wanted:
        return counts
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    if phase == "A":
        target = load_target_timed(W.MODULE)
        layers = sorted({L for r in wanted for L, _ in r["sites"]} | {C.LAYER})
        jl = R.JLensReader().bind(target, layers_keep=layers) if any("jlens" in r["readers"] for r in wanted) else None
        ol = R.OLensReader().bind(target) if any(x in r["readers"] for r in wanted for x in ("olens", "olens_trueL")) else None
        for r in wanted:
            items = request_items(r)
            if jl is not None and "jlens" in r["readers"]:
                counts[f"{r['name']}|jlens"] = score_request(jl, r, items, batch=batch)
            if ol is not None and "olens" in r["readers"]:
                counts[f"{r['name']}|olens"] = score_request(ol, r, items, batch=batch)
            if ol is not None and "olens_trueL" in r["readers"] and r["kind"] == "pair":
                counts[f"{r['name']}|olens_trueL"] = score_request(ol, r, items, reader_name="olens_trueL", batch=batch)
        M.unload(target)
    else:
        nla = R.NLAReader().bind()
        for r in wanted:
            if "nla" in r["readers"]:
                counts[f"{r['name']}|nla"] = score_request(nla, r, request_items(r), batch=batch)
        nla.unload()
    return counts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "B"], required=True)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    sub = f"{UNIT}_{a.phase}"
    if W.refuse_if_done(STAGE, a.force, sub=sub):
        return 0
    if not W.V12_REQUESTS.exists():
        W.stage_dir(STAGE).mkdir(parents=True, exist_ok=True)
        (W.stage_dir(STAGE) / "S3V1_SKIPPED").write_text(f"{now_iso()} no {W.V12_REQUESTS} -> S3v1 skipped (phase {a.phase})\n")
        W.wlog(f"s3v1 phase {a.phase}: no request file {W.V12_REQUESTS}; skipped")
        print(f"[w/s3v1] no request file at {W.V12_REQUESTS}; skipped", flush=True)
        return 0
    try:
        counts = run(a.phase, a.batch)
        W.mark_done(STAGE, sub=sub, info=counts)
    except Exception as exc:  # noqa: BLE001 — S3v1 may never stop the pipeline
        tb = traceback.format_exc()
        W.stage_dir(STAGE).mkdir(parents=True, exist_ok=True)
        (W.stage_dir(STAGE) / f"FAILED_{sub}").write_text(f"{now_iso()} {sub} failed: {exc}\n\n{tb}")
        W.wlog(f"s3v1 phase {a.phase}: FAILED ({exc!r}); see results/g_agreement/w/s3/FAILED_{sub}; pipeline continues")
        print(f"[w/s3v1] FAILED (non-fatal): {exc!r}\n{tb}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
