"""S3 — reader scoring on every S1 state and every S2 read-back, plus the V6 multi-position Oracle arm.

    python -m projects.g_agreement.w_pod.s3_score --phase A --readers jlens,olens,skip_a,probe [--v6] [--force]
    python -m projects.g_agreement.w_pod.s3_score --phase B --readers nla [--force]

Phase A (target + lenses): J-lens native at block 42 (and at 48 on the error read-backs when the lens file covers 48; at 38 on the V7
states), Oracle (carrier layer 42 / 48 / 38), skip-lens A (block-1 injection, layer-free), probe (Track B weights of the family:
w·h + b on the edited site vectors and on the read-backs) — on every S1 state (the family's candidates: counts / arith / mapping-8 /
ownership-4 get the FULL score vector over candidates_all; V7 and the pair LO as in X2) and on every S2 read-back (pair LO, candidates
(own, other); ``lo_toward_edit`` = score(other) − score(own)). Phase B: the NLA on the S2 read-backs and the counts S1 states only.
Rows → cache/g_agreement/w/s3_lo.jsonl (key = reader|S1|item or reader|S2|entry key; schema like x2_lo). V6 (phase A, --v6): on the
64 ownership L38 states and 32 S2 full-swap α 1 edited states, Oracle LO with (a) the last token, (b) the post-statement span as
consecutive markers, (c) the full prompt span, (d) the span shuffled → cache/g_agreement/w/v6_lo.jsonl. DONE_<reader>_<phase> per reader
(DONE_v6), stage DONE when every requested unit is done."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import append_jsonl, done_ids, now_iso, read_jsonl, timed_call

from . import common as W
from . import s1_capture as S1
from . import s2_steer as S2
from . import scoring_multi as SM

STAGE = "s3"
PHASE_A_READERS: tuple[str, ...] = ("jlens", "olens", "skip_a", "probe")
PHASE_B_READERS: tuple[str, ...] = ("nla",)
VECTOR_FAMILIES: tuple[str, ...] = ("counts", "arith", "mapping8", "ownership4")
NLA_S1_FAMILIES: tuple[str, ...] = ("v7",)  # 2026-10-12: counts NLA scoring dropped at pod-min 123 (PREREG deviation); V7 pilot + confirmatory scored
V7_EXTRA_LAYER = 38
V6_LAYER = 38
V6_CONDITIONS: tuple[str, ...] = ("a_last", "b_span", "c_full", "d_span_shuffled")
V6_N_EDITED = 32
ERR_READ_LAYER = 48  # the errors' second read-back layer (mock tests override)


def lo_key(reader: str, unit: str, key: str) -> str:
    return f"{reader}|{unit}|{key}"


# ------------------------------------------------------------------ reader helpers
def jlens_layers(reader: Any) -> set[int]:
    return set(getattr(reader, "J", {}) or {})


def reader_kw(reader: Any, layer: int) -> dict[str, Any]:
    """The layer argument score_lo / score_candidates accept for this reader (J-lens: the lens layer; Oracle: the carrier layer)."""
    if isinstance(reader, (R.JLensReader, R.OLensReader)):
        return {"layer": int(layer)}
    return {}


def can_score_at(reader: Any, layer: int) -> bool:
    if isinstance(reader, R.JLensReader):
        return int(layer) in jlens_layers(reader)
    return True


def item_lookup() -> dict[str, dict[str, Any]]:
    """item_id → item for every bank the pipeline touches (prompt_text drives the binary probe's mention-order rule)."""
    out: dict[str, dict[str, Any]] = {}
    for loader in (lambda: W.load_items_w(), lambda: W.load_mapping8()[0], lambda: W.load_v7(), lambda: W.load_errors()):
        try:
            for it in loader():
                if it.get("family") == "v7" and it.get("preamble") and it["preamble"] not in (it.get("prompt_text") or ""):
                    # the binary ownership probe's orientation rule reads the names' mention order from prompt_text; for V7 the names
                    # live only in the preamble (system turn), so the rule must see the model's full context (fix 2026-10-12, PREREG_WV.md:
                    # the pilot's 0/16 was the rule falling back to candidate order)
                    it = {**it, "prompt_text": f"{it['preamble']}\n\n{it['prompt_text']}"}
                out[it["item_id"]] = it
        except (FileNotFoundError, ValueError):
            continue
    try:
        for it in C.load_items("all", 0, path=W.ITEMS_X):
            out.setdefault(it["item_id"], it)
    except FileNotFoundError:
        pass
    return out


def probe_rows(probe: dict[str, Any], H: Any, cand_lists: list[list[str]], pair_ids: list[str | None], prompts: list[str | None]) -> list[dict[str, Any]]:
    """One probe result per state: per-candidate scores from the fold that never saw the pair/item (W.probe_candidate_scores),
    lo = score(cand_A) − score(cand_B) (positive = toward the first candidate, as every reader's lo_own)."""
    import torch

    H = torch.as_tensor(H).float()
    if H.ndim == 1:
        H = H[None]
    out = []
    for i, cs in enumerate(cand_lists):
        q = W.probe_candidate_scores(probe, H[i], cs, pair_id=pair_ids[i], prompt_text=prompts[i])
        sc = q["scores"]
        ok = [j for j, v in enumerate(sc) if v is not None]
        lo = None if len(sc) < 2 or sc[0] is None or sc[1] is None else sc[0] - sc[1]
        out.append({"reader": "probe", "candidates": list(cs), "scores": sc, "argmax": (cs[max(ok, key=lambda j: sc[j])] if ok else None), "n_unscorable": len(cs) - len(ok),
                    "lo": lo, "lp_A": sc[0] if sc else None, "lp_B": sc[1] if len(sc) > 1 else None, "score": lo, "unscorable": lo is None, "templates": [q["rule"]],
                    "format": "linear_probe_heldout_fold", "probe_fold": q["fold"], "probe_layer": probe.get("layer"), "probe_path": probe.get("path"), "probe_label": probe.get("label")})
    return out


# ------------------------------------------------------------------ S1 states
def s1_rows(target_path: Path | None = None) -> list[dict[str, Any]]:
    return read_jsonl(target_path or W.S1_TARGET)


def s1_vectors(rows: list[dict[str, Any]], layer: int, *, states_root: Path | None = None, caps_dir: Path | None = None) -> Any:
    """fp32 [N, d] last-token states at ``layer`` (states_L<layer> files when present, else the S1 capture)."""
    import torch

    root = states_root or W.W_CACHE
    hs = []
    for r in rows:
        p = root / f"states_L{layer}" / f"{r['item_id']}.pt"
        if p.exists():
            hs.append(torch.load(p, map_location="cpu").float())
        else:
            hs.append(S1.cap_vector(S1.load_cap(r["item_id"], caps_dir), layer, -1))
    return torch.stack(hs)


def score_s1(reader: Any, rows: list[dict[str, Any]], *, reader_name: str | None = None, lo_path: Path | None = None, layer: int | None = None, unit: str = "S1",
             families: tuple[str, ...] | None = None, probe: dict[str, Any] | None = None, batch: int = 32, ledger_path: Path | None = None,
             states_root: Path | None = None, caps_dir: Path | None = None, log_path: Path | None = None, items: dict[str, dict[str, Any]] | None = None) -> int:
    """Score the S1 states of the requested families at ``layer``: the full candidate vector for VECTOR_FAMILIES, the pair LO
    (own, other) for every family (both from the same forward where possible). Resumable by key."""
    import torch

    name = reader_name or (reader.name if reader is not None else "probe")
    layer = C.LAYER if layer is None else int(layer)
    lo_path = lo_path or W.S3_LO
    done = done_ids(lo_path, key="key")
    extra = W.row_extra()
    led = W.ledger(f"s3_lo_{name}_{unit}", {"layer": layer, "batch": batch})
    n = 0
    fams = sorted({r["family"] for r in rows if families is None or r["family"] in families})
    for fam in fams:
        todo = [r for r in rows if r["family"] == fam and lo_key(name, unit, r["item_id"]) not in done]
        if not todo:
            continue
        nla_fam = W.NLA_FAMILY_OF.get(fam, fam)
        for s in range(0, len(todo), batch):
            chunk = todo[s: s + batch]
            H = s1_vectors(chunk, layer, states_root=states_root, caps_dir=caps_dir)
            with timed_call() as st:
                if probe is not None:
                    its = items or {}
                    cl = [([r["cand_A"], r["cand_B"]] + [c for c in r["candidates_all"] if c not in (r["cand_A"], r["cand_B"])]) if fam in VECTOR_FAMILIES else [r["cand_A"], r["cand_B"]] for r in chunk]
                    res = probe_rows(probe, H, cl, [r.get("pair_id") for r in chunk], [(its.get(r["item_id"]) or {}).get("prompt_text") for r in chunk])
                elif fam in VECTOR_FAMILIES:
                    res = SM.score_candidates(reader, H, [list(r["candidates_all"]) for r in chunk], nla_fam, batch=batch, **reader_kw(reader, layer))
                    for r, q in zip(chunk, res):
                        cs = q["candidates"]
                        ia, ib = (cs.index(r["cand_A"]) if r["cand_A"] in cs else None), (cs.index(r["cand_B"]) if r["cand_B"] in cs else None)
                        sa = q["scores"][ia] if ia is not None else None
                        sb = q["scores"][ib] if ib is not None else None
                        q.update(lo=(None if sa is None or sb is None else sa - sb), lp_A=sa, lp_B=sb, unscorable=(sa is None or sb is None))
                else:
                    res = LO.score_lo(reader, H, [(r["cand_A"], r["cand_B"]) for r in chunk], nla_fam, batch=batch, **reader_kw(reader, layer))
            for r, q in zip(chunk, res):
                row = {"key": lo_key(name, unit, r["item_id"]), "entry_key": r["item_id"], "reader": name, "unit": unit, "layer": layer, "family": fam, "item_id": r["item_id"],
                       "pair_id": r.get("pair_id"), "version": r.get("version"), "cand_A": r["cand_A"], "cand_B": r["cand_B"], "true_answer": r.get("true_answer"),
                       "actual_answer": r.get("parsed"), "correct": r.get("correct"), "candidates": q.get("candidates", [r["cand_A"], r["cand_B"]]), "scores": q.get("scores"),
                       "argmax": q.get("argmax"), "score": q.get("score"), "lo_own": q.get("lo"), "lo_toward_other": (None if q.get("lo") is None else -q["lo"]),
                       "lp_A": q.get("lp_A"), "lp_B": q.get("lp_B"), "templates": q.get("templates"), "unscorable": q.get("unscorable"), "format": q.get("format"),
                       "n_unscorable": q.get("n_unscorable"), "lo_model": r.get("lo_model"), "lp_candidates_all_model": (r.get("lp_candidates_all") if fam in VECTOR_FAMILIES else None),
                       "wall_s_chunk": st.wall_s, "chunk_size": len(chunk), **extra}
                for k in ("per_template", "variants_A", "variants_B", "best_A", "best_B", "reason", "probe_layer", "probe_path", "probe_fold", "probe_label"):
                    if k in q:
                        row[k] = q[k]
                append_jsonl(lo_path, row)
                n += 1
            led.add(0, 0, st.wall_s, st.peak_mem_gb)
        print(f"[w/s3/{name}@{unit}] {fam}: {len(todo)} states scored", flush=True)
    rr = led.flush(ledger_path)
    if rr:
        W.wlog(f"s3 {led.step}: {rr}", log_path)
    return n


# ------------------------------------------------------------------ S2 read-backs
def score_s2(reader: Any, beh_rows: list[dict[str, Any]], *, reader_name: str | None = None, lo_path: Path | None = None, readvec_dir: Path | None = None, read_layer: int | None = None,
             unit: str | None = None, families: tuple[str, ...] | None = None, probe: dict[str, Any] | None = None, batch: int = 32, ledger_path: Path | None = None,
             log_path: Path | None = None, items: dict[str, dict[str, Any]] | None = None) -> int:
    """Pair LO of ``reader`` on the block-``read_layer`` read-back of every S2 row (families with that read layer). The probe scores
    the EDITED site vectors (mean over the edited positions) and the read-back; ``score`` = the edited-vector score when the probe's
    layer is the edit layer, else the read-back score. Resumable by key reader|S2[@L48]|entry key."""
    import torch

    name = reader_name or (reader.name if reader is not None else "probe")
    read_layer = C.LAYER if read_layer is None else int(read_layer)
    unit = unit or ("S2" if read_layer == C.LAYER else f"S2@L{read_layer}")
    lo_path = lo_path or W.S3_LO
    done = done_ids(lo_path, key="key")
    extra = W.row_extra()
    led = W.ledger(f"s3_lo_{name}_{unit}", {"read_layer": read_layer, "batch": batch})
    n = 0
    by_fam: dict[str, list[dict[str, Any]]] = {}
    for r in beh_rows:
        if families is not None and r["family"] not in families:
            continue
        if read_layer not in [int(x) for x in r.get("read_layers", [C.LAYER])]:
            continue
        if lo_key(name, unit, r["key"]) in done or not S2.readvec_path(r["key"], readvec_dir).exists():
            continue
        by_fam.setdefault(r["family"], []).append(r)
    for fam, rows_f in by_fam.items():
        nla_fam = W.NLA_FAMILY_OF.get(fam, fam)
        for s in range(0, len(rows_f), batch):
            chunk = rows_f[s: s + batch]
            recs = [S2.load_readvec_record(r["key"], readvec_dir) for r in chunk]
            H = torch.stack([rec["read"][int(read_layer)].float() for rec in recs])
            with timed_call() as st:
                if probe is not None:
                    its = items or {}
                    Hed = torch.stack([rec["edited"].float().mean(0) for rec in recs])
                    cl = [[r["cand_A"], r["cand_B"]] for r in chunk]
                    pids, prs = [r["pair_id"] for r in chunk], [(its.get(r["state_item_id"]) or {}).get("prompt_text") for r in chunk]
                    r_ed, r_rd = probe_rows(probe, Hed, cl, pids, prs), probe_rows(probe, H, cl, pids, prs)
                    use_edit = probe.get("layer") is None or int(probe["layer"]) == int(chunk[0]["edit_layer"])
                    res = []
                    for a, b in zip(r_ed, r_rd):
                        q = dict(a if use_edit else b)
                        q.update(score_edited=a["lo"], score_read=b["lo"], scores_edited=a["scores"], scores_read=b["scores"], probe_on=("edited_site_mean" if use_edit else f"read_L{read_layer}"))
                        res.append(q)
                else:
                    res = LO.score_lo(reader, H, [(r["cand_A"], r["cand_B"]) for r in chunk], nla_fam, batch=batch, **reader_kw(reader, read_layer))
            for r, q in zip(chunk, res):
                row = {"key": lo_key(name, unit, r["key"]), "entry_key": r["key"], "reader": name, "unit": unit, "read_layer": read_layer,
                       **{k: r.get(k) for k in ("pair_id", "family", "source", "state_item_id", "site", "direction", "condition", "alpha", "k", "edit_layer", "n_positions", "n_tokens",
                                                "cand_A", "cand_B", "dose_abs", "lo_model", "flipped_to_other", "coherent", "parsed")},
                       "candidates": [r["cand_A"], r["cand_B"]], "lo_own": q.get("lo"), "lo_toward_edit": (None if q.get("lo") is None else -q["lo"]), "lo_toward_other": (None if q.get("lo") is None else -q["lo"]),
                       "lp_A": q.get("lp_A"), "lp_B": q.get("lp_B"), "score": q.get("score"), "templates": q.get("templates"), "unscorable": q.get("unscorable"), "format": q.get("format"),
                       "wall_s_chunk": st.wall_s, "chunk_size": len(chunk), **extra}
                for k in ("per_template", "variants_A", "variants_B", "best_A", "best_B", "reason", "score_edited", "score_read", "scores_edited", "scores_read", "probe_layer", "probe_path",
                          "probe_on", "probe_fold", "probe_label", "candidates", "scores"):
                    if k in q:
                        row[k] = q[k]
                append_jsonl(lo_path, row)
                n += 1
            led.add(0, 0, st.wall_s, st.peak_mem_gb)
        print(f"[w/s3/{name}@{unit}] {fam}: {len(rows_f)} read-backs scored", flush=True)
    rr = led.flush(ledger_path)
    if rr:
        W.wlog(f"s3 {led.step}: {rr}", log_path)
    return n


# ------------------------------------------------------------------ V6
def v6_states(beh_rows: list[dict[str, Any]], *, directions_root: Path | None = None, items_x: Path | None = None, x_full_dir: Path | None = None,
              readvec_dir: Path | None = None, spans_json: Path | None = None, n_edited: int = V6_N_EDITED, n_states: int = W.S2_N_STATES, layer: int | None = None) -> list[dict[str, Any]]:
    """The 64 natural ownership L38 states (X2 full captures; span = the ownership direction file's positions, else Z4b question_only)
    and the first ``n_edited`` S2 full-swap α 1 ownership rows (edited span rows from s2_readvecs)."""
    import torch

    layer = V6_LAYER if layer is None else int(layer)
    idx = W.directions_index("ownership", directions_root)
    states = S2.x2_states("ownership", idx, items_x=items_x, x_full_dir=x_full_dir, n_states=n_states)
    spans = json.loads(Path(spans_json or W.Z4B_SPANS).read_text()) if Path(spans_json or W.Z4B_SPANS).exists() else {}
    out = []
    dcache: dict[str, Any] = {}
    for s in states:
        cap = S2.base_capture(s, layer)
        T = cap["n_tokens"]
        f = str(s["direction_file"])
        if f not in dcache:
            try:
                dcache[f] = [int(p) % T for p in W.load_direction_file(Path(f))["positions"]]
            except FileNotFoundError:
                dcache[f] = None
        span = dcache[f]
        if span is None:
            arms = (spans.get("pairs") or {}).get(s["pair_id"], {}).get("arms", {})
            span = [int(p) for p in arms.get("question_only", [])] or list(range(max(0, T - 3), T))
        out.append({"state_key": f"{s['pair_id']}|{s['source']}|natural", "state_kind": "natural", "pair_id": s["pair_id"], "source": s["source"], "state_item_id": s["state_item_id"],
                    "cand_A": s["cand_A"], "cand_B": s["cand_B"], "H": cap["h"], "span": span, "n_tokens": T})
    ed = [r for r in beh_rows if r["family"] == "ownership" and r["direction"] == "full" and float(r["alpha"]) == 1.0]
    for r in ed[:n_edited]:
        base = next((x for x in out if x["pair_id"] == r["pair_id"] and x["source"] == r["source"]), None)
        if base is None or not S2.readvec_path(r["key"], readvec_dir).exists():
            continue
        rec = S2.load_readvec_record(r["key"], readvec_dir)
        H = base["H"].clone()
        H[[int(p) for p in rec["positions"]]] = rec["edited"].float()
        out.append({**base, "state_key": f"{r['key']}", "state_kind": "edited_full_a1", "H": H, "span": [int(p) for p in rec["positions"]], "s2_key": r["key"]})
    return out


def v6_vectors(state: dict[str, Any], condition: str) -> Any:
    import torch

    H, span, T = state["H"], list(state["span"]), int(state["n_tokens"])
    if condition == "a_last":
        return H[T - 1][None]
    if condition == "b_span":
        return H[span]
    if condition == "c_full":
        return H
    if condition == "d_span_shuffled":
        g = torch.Generator().manual_seed(C.stable_seed(W.MODULE, "v6_shuffle", state["state_key"], 0))
        perm = torch.randperm(len(span), generator=g).tolist()
        return H[[span[i] for i in perm]]
    raise ValueError(condition)


def collect_v6(reader: R.OLensReader, states: list[dict[str, Any]], *, lo_path: Path | None = None, layer: int | None = None, conditions: tuple[str, ...] = V6_CONDITIONS,
               batch: int = 16, ledger_path: Path | None = None, log_path: Path | None = None) -> int:
    layer = V6_LAYER if layer is None else int(layer)
    lo_path = lo_path or W.V6_LO
    done = done_ids(lo_path, key="key")
    extra = W.row_extra()
    led = W.ledger("v6_olens", {"layer": layer, "batch": batch})
    carriers: dict[int, Any] = {}
    n = 0
    for cond in conditions:
        todo = [s for s in states if f"olens|V6|{cond}|{s['state_key']}" not in done]
        for b in range(0, len(todo), batch):
            chunk = todo[b: b + batch]
            spans = [v6_vectors(s, cond) for s in chunk]
            with timed_call() as st:
                res = SM.lo_olens_span(reader, spans, [(s["cand_A"], s["cand_B"]) for s in chunk], layer, batch=batch, carriers=carriers)
            for s, q in zip(chunk, res):
                append_jsonl(lo_path, {"key": f"olens|V6|{cond}|{s['state_key']}", "reader": "olens", "unit": "V6", "condition": cond, "state_kind": s["state_kind"], "state_key": s["state_key"],
                                       "s2_key": s.get("s2_key"), "pair_id": s["pair_id"], "source": s["source"], "state_item_id": s["state_item_id"], "family": "ownership", "layer": layer,
                                       "n_markers": q["n_markers"], "span": (list(s["span"]) if cond != "c_full" else None), "n_tokens": s["n_tokens"], "cand_A": s["cand_A"], "cand_B": s["cand_B"],
                                       "lo_own": q["lo"], "lo_toward_other": -q["lo"], "lp_A": q["lp_A"], "lp_B": q["lp_B"], "marker_char": q["marker_char"], "templates": q["templates"],
                                       "unscorable": False, "wall_s_chunk": st.wall_s, "chunk_size": len(chunk), **extra})
                n += 1
            led.add(0, 0, st.wall_s, st.peak_mem_gb)
        print(f"[w/s3/v6] {cond}: {len(todo)} states scored", flush=True)
    rr = led.flush(ledger_path)
    if rr:
        W.wlog(f"v6 {led.step}: {rr}", log_path)
    return n


# ------------------------------------------------------------------ orchestration
def run_reader(reader: Any, name: str, phase: str, *, beh_rows: list[dict[str, Any]], s1: list[dict[str, Any]], probes: dict[str, Any] | None = None, batch: int = 32) -> dict[str, int]:
    out: dict[str, int] = {}
    if name == "probe":
        probes = probes or {}
        if not probes:
            W.wlog("s3 probe: no probe weights found under the directions tree; probe reader skipped")
            print("[w/s3/probe] no probe.pt in any family directory; skipped", flush=True)
            return {"skipped": 1}
        its = item_lookup()
        for fam, pr in probes.items():
            out[f"s2_{fam}"] = score_s2(None, beh_rows, reader_name="probe", probe=pr, families=(fam,), batch=batch, items=its)
            if fam == "errors":
                out[f"s2_{fam}_L{ERR_READ_LAYER}"] = score_s2(None, beh_rows, reader_name="probe", probe=pr, read_layer=ERR_READ_LAYER, families=(fam,), batch=batch, items=its)
            s1_fams = {"ownership": ("ownership4", "v7"), "mapping": ("mapping8",), "errors": ()}.get(fam, ())
            if s1_fams:
                out[f"s1_{fam}"] = score_s1(None, s1, reader_name="probe", probe=pr, families=s1_fams, batch=batch, items=its)  # block-42 last token (the readers' site)
                pl = pr.get("layer")
                if pl is not None and int(pl) != C.LAYER and int(pl) in W.S1_LAYERS:  # the probe's own layer (last token) from the S1 captures
                    out[f"s1_{fam}_L{pl}"] = score_s1(None, s1, reader_name="probe", probe=pr, layer=int(pl), unit=f"S1@L{pl}", families=s1_fams, batch=batch, items=its)
        return out
    if phase == "A":
        s1_only = tuple(f for f in os.environ.get("W_S1_FAMILIES", "").split(",") if f.strip()) or None  # e.g. W_S1_FAMILIES=v7 (confirmatory run)
        out["s1"] = score_s1(reader, s1, families=s1_only, batch=batch)
        if can_score_at(reader, V7_EXTRA_LAYER) and isinstance(reader, (R.JLensReader, R.OLensReader)):
            out["s1_v7_L38"] = score_s1(reader, s1, layer=V7_EXTRA_LAYER, unit=f"S1@L{V7_EXTRA_LAYER}", families=("v7",), batch=batch)
        out["s2"] = score_s2(reader, beh_rows, batch=batch)
        if can_score_at(reader, ERR_READ_LAYER) and isinstance(reader, (R.JLensReader, R.OLensReader)):
            out[f"s2_L{ERR_READ_LAYER}"] = score_s2(reader, beh_rows, read_layer=ERR_READ_LAYER, families=("errors",), batch=batch)
        elif isinstance(reader, R.JLensReader):
            W.wlog(f"s3 jlens: lens file does not cover layer {ERR_READ_LAYER}; the error read-backs are scored at {C.LAYER} only")
    else:
        out["s1_counts"] = score_s1(reader, s1, families=NLA_S1_FAMILIES, batch=batch)
        out["s2"] = score_s2(reader, beh_rows, batch=batch)
    return out


def guarded(unit: str, fn: Any) -> Any:
    """Run an OPTIONAL unit (V6, probe): an exception is logged, written to results/g_agreement/w/s3/FAILED_<unit> and swallowed, so the
    core reader units and the pipeline continue (the brief treats V6 as a ~15 min appended arm)."""
    import traceback

    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        tb = traceback.format_exc()
        W.stage_dir(STAGE).mkdir(parents=True, exist_ok=True)
        (W.stage_dir(STAGE) / f"FAILED_{unit}").write_text(f"{now_iso()} {unit} failed: {exc}\n\n{tb}")
        W.wlog(f"s3 {unit}: FAILED ({exc!r}); see results/g_agreement/w/s3/FAILED_{unit}")
        print(f"[w/s3] {unit} FAILED: {exc!r} (logged; continuing)", flush=True)
        return None


def load_probes(directions_root: Path | None = None) -> dict[str, Any]:
    """Per family: the Track B probe of <family>/shared.pt (fold-specific w_raw, held out per pair/item); probe.pt only as a fallback."""
    out = {}
    for fam in W.S2_FAMILIES:
        try:
            idx = W.directions_index(fam, directions_root)
        except FileNotFoundError:
            continue
        pr = W.load_probe_shared(idx["shared_path"], layer=idx["layer"], site=idx["site"]) or W.load_probe(idx["probe_path"])
        if pr is not None:
            if pr.get("layer") is None:
                pr["layer"] = idx["layer"]
            out[fam] = pr
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "B"], required=True)
    ap.add_argument("--readers", default=None)
    ap.add_argument("--v6", action="store_true")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    readers = tuple(r.strip() for r in (a.readers or ",".join(PHASE_A_READERS if a.phase == "A" else PHASE_B_READERS)).split(",") if r.strip())
    units = [f"{r}_{a.phase}" for r in readers] + (["v6"] if a.v6 else [])
    todo = [u for u in units if not W.refuse_if_done(STAGE, a.force, sub=u)]
    if not todo:
        return 0
    beh_rows = read_jsonl(W.S2_BEHAVIOUR)
    s1 = s1_rows()
    print(f"[w/s3] phase {a.phase}: readers {readers}, v6={a.v6}; {len(s1)} S1 states, {len(beh_rows)} S2 rows", flush=True)
    W.wlog(f"s3 phase {a.phase} start: readers {readers} v6={a.v6}; S1 {len(s1)} states; S2 {len(beh_rows)} rows")
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    if a.phase == "A":
        target = load_target_timed(W.MODULE)
        probes = load_probes()
        W.wlog(f"s3 probes found: {sorted(probes)} ({ {f: p['path'] for f, p in probes.items()} })")
        jl = ol = sk = None
        if f"jlens_A" in todo:
            jl = R.JLensReader().bind(target, layers_keep=[V7_EXTRA_LAYER, C.LAYER, ERR_READ_LAYER])
            W.wlog(f"s3 jlens layers loaded {sorted(jl.J)} (source layers {jl.source_layers[:2]}..{jl.source_layers[-2:]})")
            res = run_reader(jl, "jlens", "A", beh_rows=beh_rows, s1=s1, batch=a.batch)
            W.mark_done(STAGE, sub="jlens_A", info=res)
            del jl
        if any(u in todo for u in ("olens_A", "skip_a_A", "v6")):
            ol = R.OLensReader().bind(target)
            W.wlog(f"s3 olens adapter={ol.adapter_dir} liveness={ol.liveness}")
        if "olens_A" in todo:
            res = run_reader(ol, "olens", "A", beh_rows=beh_rows, s1=s1, batch=a.batch)
            W.mark_done(STAGE, sub="olens_A", info=res)
        if "v6" in todo:
            def _v6():
                states = v6_states(beh_rows)
                W.wlog(f"v6: {len(states)} states ({sum(s['state_kind'] == 'natural' for s in states)} natural, {sum(s['state_kind'] != 'natural' for s in states)} edited); carrier layer {V6_LAYER}")
                n = collect_v6(ol, states, batch=max(4, a.batch // 2))
                W.mark_done(STAGE, sub="v6", info={"n_rows": n, "n_states": len(states)})

            guarded("v6", _v6)
        if "skip_a_A" in todo:
            sk = R.SkipLensReader("a").bind(target)
            W.wlog(f"s3 skip_a adapter={sk.adapter_dir} liveness={sk.liveness}")
            res = run_reader(sk, "skip_a", "A", beh_rows=beh_rows, s1=s1, batch=a.batch)
            W.mark_done(STAGE, sub="skip_a_A", info=res)
        if "probe_A" in todo:
            def _probe():
                res = run_reader(None, "probe", "A", beh_rows=beh_rows, s1=s1, probes=probes, batch=a.batch)
                W.mark_done(STAGE, sub="probe_A", info=res)

            guarded("probe_A", _probe)
        M.unload(target)
    else:
        led = W.ledger("load_nla")
        with timed_call() as st:
            nla = R.NLAReader().bind()
        led.add(0, 0, st.wall_s, st.peak_mem_gb)
        led.flush()
        W.wlog(f"s3 phase B: nla adapter={nla.adapter_dir} liveness={nla.liveness}")
        if "nla_B" in todo:
            res = run_reader(nla, "nla", "B", beh_rows=beh_rows, s1=s1, batch=a.batch)
            W.mark_done(STAGE, sub="nla_B", info=res)
        nla.unload()
    core_units = [u for u in units if u not in ("v6", "probe_A")]
    full_set = set(readers) >= set(PHASE_A_READERS if a.phase == "A" else PHASE_B_READERS)
    if full_set and all(W.is_done(STAGE, sub=u) for u in core_units):
        W.mark_done(STAGE, sub=f"phase{a.phase}", info={"units": units, "optional_missing": [u for u in units if u not in core_units and not W.is_done(STAGE, sub=u)]})
    if W.is_done(STAGE, sub="phaseA") and W.is_done(STAGE, sub="phaseB"):
        W.mark_done(STAGE, info={"phases": ["A", "B"]})
    return 0


if __name__ == "__main__":
    sys.exit(main())
