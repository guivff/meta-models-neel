"""Y1 site search — GPU stages (BRIEF_Y.md §Y1). Selection uses the target model and the prompt-only arm only.

    python -m projects.g_agreement.y1_site.collect --phase A --stage select  [--limit N] [--allow-unfrozen]
    python -m projects.g_agreement.y1_site.collect --phase A --stage capture [--layers 42,44,...,62] [--positions 12]
    python -m projects.g_agreement.y1_site.collect --phase A --stage reread --site L:P [--readers jlens,olens]
    python -m projects.g_agreement.y1_site.collect --phase B --stage reread --site L:P [--readers nla]

select   (phase A)  the X3 selection machinery on the UNION of the X3 choice candidates (items_x3_candidates.json)
                    and the Y1 extension (items_y1_choice.json): target greedy actual (16 tokens) + prompt-only
                    self-guess (64 tokens), parsed with the choice rule; rows -> cache/g_agreement/y/y1_target.jsonl
                    (key = item_id, resumable; the 300 X3 choice rows are copied from x3_target.jsonl when present,
                    the decodes are greedy so a re-decode would be identical). Then dataset/items_y1_selected.json =
                    X3's puzzle ERROR / ERROR_CONTROL items (items_x3_selected.json, unchanged) + DISAGREE (all
                    choice disagreements of the union) + size-matched AGREE_CONTROL (seed 0). K6-style flag:
                    DISAGREE < 60 -> ``underpowered`` (descriptive only; the run continues).
capture  (phase A)  one forward per selected item: block outputs at layers L in {42, 44, ..., 62} at positions
                    {last, last-1, ..., last-11} U {candA, candB} (the prompt positions of the two candidate tokens,
                    found by matching the candidates' token ids in the rendered ids; -1 if absent), saved bf16 as
                    cache/g_agreement/y/y1_caps/<item_id>.pt ({acts [n_layers, n_pos, d], meta}); plus the logit-lens
                    margin per layer at the last position (final norm + W_U on the block-L output;
                    lo = lp(first token of actual) - lp(first token of other), first tokens via
                    core.edit.first_token_candidates, form recorded) -> cache/g_agreement/y/y1_logitlens.jsonl.
reread   (A or B)   native LO at one site L:P (P = offset from the last position, or candA / candB): J-lens with
                    layers_keep=[L]; OLens with the carrier at the nearest on-grid layer {44, 48, 52, 56, 60}
                    (``olens``; the true L is recorded) and at the true L (``olens_trueL``, sensitivity); NLA as a
                    transfer test (phase B; trained at L42 only). Every reader also gets the E3 gate rows: LO on the
                    MEAN state of each set, must be within +-1 nat. Rows -> cache/g_agreement/y/y1_lo.jsonl, key =
                    reader|site|item_id, ``lo_actual`` = lp(actual) - lp(other), ``favours_actual`` = lo > 0.

Ledger steps: y1_target_choice, y1_self_guess, y1_capture, y1_lo_<reader>, y1_mean_lo_<reader>.
Log: results/g_agreement/y1/log.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import edit as E
from projects.g_agreement.core import generate as G
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import StepLedger, append_jsonl, done_ids, log_line, now_iso, read_jsonl, timed_call
from projects.g_agreement.x3_floor import collect as X3

MODULE = "y1"
Y_DIR = C.CACHE_DIR / "y"
TARGET_PATH = Y_DIR / "y1_target.jsonl"
CAPS_DIR = Y_DIR / "y1_caps"
CAPS_META_PATH = Y_DIR / "y1_caps_meta.jsonl"
LOGITLENS_PATH = Y_DIR / "y1_logitlens.jsonl"
LO_PATH = Y_DIR / "y1_lo.jsonl"
Y1_CHOICE_JSON = C.DATASET_DIR / "items_y1_choice.json"
SELECTED_JSON = C.DATASET_DIR / "items_y1_selected.json"
LOG = C.RESULTS_DIR / "y1" / "log.md"

LAYERS = tuple(range(42, 63, 2))  # 42, 44, ..., 62
N_POSITIONS = 12  # last, last-1, ..., last-11
CAND_LABELS = ("candA", "candB")  # A = the model's actual answer, B = the other candidate
OLENS_GRID = (44, 48, 52, 56, 60)  # OLens training layers inside the Y1 range (42 is off-grid)
MIN_DISAGREE = 60  # Y1 K6-style flag (X3 used 24)
PUZZLE_SETS = ("error", "error_control")
CHOICE_SETS = ("disagree", "agree_control")
E3_BAND = 1.0


# ------------------------------------------------------------------ positions / sites
def pos_labels(n_positions: int = N_POSITIONS) -> list[str]:
    """Cell labels: '0' = last, '1' = last-1, ..., then 'candA', 'candB'."""
    return [str(k) for k in range(n_positions)] + list(CAND_LABELS)


def parse_site(site: str) -> tuple[int, str]:
    """'L:P' -> (layer, position label); P is an int offset from the last position or candA / candB."""
    try:
        ls, ps = site.split(":")
        layer = int(ls)
    except Exception as exc:
        raise ValueError(f"site must be 'L:P' (e.g. 46:0, 44:3, 48:candA), got {site!r}") from exc
    ps = ps.strip()
    if ps in CAND_LABELS:
        return layer, ps
    if ps.startswith("last-"):
        ps = ps[5:]
    if ps == "last":
        ps = "0"
    if not ps.isdigit():
        raise ValueError(f"position must be an offset (0 = last) or one of {CAND_LABELS}, got {ps!r}")
    return layer, str(int(ps))


def nearest_grid_layer(layer: int, grid: tuple[int, ...] | None = None) -> int:
    """The on-grid OLens layer closest to ``layer`` (ties -> the lower layer)."""
    grid = OLENS_GRID if grid is None else grid
    return min(grid, key=lambda g: (abs(g - layer), g))


def _find_all(ids: list[int], sub: list[int]) -> list[int]:
    """Indices of the LAST token of every occurrence of ``sub`` in ``ids``."""
    if not sub or len(sub) > len(ids):
        return []
    n = len(sub)
    return [i + n - 1 for i in range(len(ids) - n + 1) if ids[i: i + n] == sub]


def find_candidate_positions(tokenizer: Any, ids: list[int], cand: str) -> dict[str, Any]:
    """Prompt positions of a candidate: every spelling (bare, leading space, capitalised, lower) is encoded and
    matched as a token-id subsequence in the rendered ids; the position is the index of the token that completes the
    candidate. ``pos`` = the earliest occurrence (-1 if absent), ``all`` = every occurrence (sorted), ``forms`` = the
    spellings that matched."""
    forms: list[str] = []
    for w in (cand, cand.capitalize(), cand.lower()):
        for f in (" " + w, w):
            if f not in forms:
                forms.append(f)
    hits: dict[int, str] = {}
    for f in forms:
        sub = list(tokenizer(f, add_special_tokens=False)["input_ids"])
        for p in _find_all(ids, sub):
            hits.setdefault(p, f)
    allp = sorted(hits)
    return {"pos": allp[0] if allp else -1, "all": allp, "forms": sorted({hits[p] for p in allp}), "n": len(allp)}


def item_positions(tokenizer: Any, ids: list[int], cand_a: str, cand_b: str, n_positions: int = N_POSITIONS) -> dict[str, Any]:
    """Absolute positions for every cell label (-1 where absent / out of range) + candidate meta."""
    n = len(ids)
    pos = [(n - 1 - k) if n - 1 - k >= 0 else -1 for k in range(n_positions)]
    fa = find_candidate_positions(tokenizer, ids, cand_a)
    fb = find_candidate_positions(tokenizer, ids, cand_b)
    return {"labels": pos_labels(n_positions), "positions": pos + [fa["pos"], fb["pos"]], "n_tokens": n,
            "cand": {"candA": fa, "candB": fb}}


# ------------------------------------------------------------------ stage select
def load_union_choice(x3_candidates: Path | str = X3.CANDIDATES_JSON, y1_choice: Path | str = Y1_CHOICE_JSON,
                      limit: int = 0) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Choice items of X3 (300) + Y1 (900) with the X3 schema checks; ``limit`` keeps the first N of each file."""
    _, x3_items = X3.load_candidates(x3_candidates, limit)
    x3_cho = [it for it in x3_items if it["family"] == "choice"]
    p = Path(y1_choice)
    if not p.exists():
        raise FileNotFoundError(f"{p} missing: run dataset/build_y1_choice.py first")
    _, y1_items = X3.load_candidates(p, limit)
    y1_cho = [it for it in y1_items if it["family"] == "choice"]
    if any(it["family"] != "choice" for it in y1_items):
        raise ValueError("items_y1_choice.json must contain choice items only")
    ids = [it["item_id"] for it in x3_cho + y1_cho]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate item ids across the X3 and Y1 choice files")
    pairs_x3 = {frozenset(it["primary"]["candidates"]) for it in x3_cho}
    pairs_y1 = {frozenset(it["primary"]["candidates"]) for it in y1_cho}
    overlap = pairs_x3 & pairs_y1
    if overlap:
        raise ValueError(f"Y1 reuses {len(overlap)} X3 option pairs, e.g. {sorted(next(iter(overlap)))}")
    meta = {"x3_candidates_sha256": C.sha256_file(x3_candidates), "y1_choice_sha256": C.sha256_file(p),
            "n_x3_choice": len(x3_cho), "n_y1_choice": len(y1_cho)}
    return x3_cho + y1_cho, meta


def seed_from_x3(items: list[dict[str, Any]], *, target_path: Path = TARGET_PATH, x3_target_path: Path = X3.TARGET_PATH) -> int:
    """Copy the X3 choice decode rows for union items into the Y1 target file (greedy decodes; identical render)."""
    if not Path(x3_target_path).exists():
        return 0
    want = {it["item_id"] for it in items}
    done = done_ids(target_path, key="key")
    n = 0
    for r in read_jsonl(x3_target_path):
        if r.get("family") == "choice" and r["item_id"] in want and r["key"] not in done:
            append_jsonl(target_path, {**r, "source_rows": "x3_target", "copied_at": now_iso()})
            done.add(r["key"])
            n += 1
    return n


def collect_target_choice(target: M.Target, items: list[dict[str, Any]], *, target_path: Path = TARGET_PATH,
                          ledger_path: Path | None = None, log_path: Path | None = LOG, choice_cap: int = X3.CHOICE_CAP,
                          self_guess_cap: int = X3.SELF_GUESS_CAP, extra: dict[str, Any] | None = None) -> int:
    """X3 step 1 for choice items (same row schema as x3_floor.collect.collect_target; Y1 ledger steps). Resumable."""
    done = done_ids(target_path, key="key")
    led_c = StepLedger(step="y1_target_choice", module=MODULE, extra={"max_new_tokens": choice_cap})
    led_s = StepLedger(step="y1_self_guess", module=MODULE, extra={"max_new_tokens": self_guess_cap})
    extra = dict(extra or {})
    n = 0
    for it in items:
        iid = it["item_id"]
        if iid in done or it["family"] != "choice":
            continue
        cands = list(it["primary"]["candidates"])
        res, ids = G.target_answer(target, it, max_new_tokens=choice_cap)
        actual, ev_a = X3.parse_choice(res.raw_output, cands)
        res2, ids2, visible = X3.self_guess_answer(target, it, self_guess_cap)
        guess, ev_g = X3.parse_choice(res2.raw_output, cands)
        both = actual is not None and guess is not None
        row = {"key": iid, "item_id": iid, "family": "choice", "created_at": now_iso(), **extra,
               "answer_text": res.raw_output, "actual": actual, "actual_evidence": ev_a,
               "self_guess_text": res2.raw_output, "self_guess": guess, "self_guess_evidence": ev_g,
               "candidates": cands, "first_listed": cands[0], "both_parsed": both, "disagree": bool(both and actual != guess),
               "n_prompt_tokens": res.n_prompt_tokens, "n_new_tokens": res.n_new_tokens, "finish_reason": res.finish_reason,
               "prompt_ids_sha256": C.sha256_ids(ids), "wall_s": res.wall_s, "peak_mem_gb": res.peak_mem_gb,
               "self_guess_n_prompt_tokens": res2.n_prompt_tokens, "self_guess_n_new_tokens": res2.n_new_tokens,
               "self_guess_finish_reason": res2.finish_reason, "self_guess_prompt_ids_sha256": C.sha256_ids(ids2),
               "self_guess_prompt_sha256": C.sha256_bytes(visible.encode("utf-8")), "self_guess_wall_s": res2.wall_s,
               "sampling": res.sampling, "model_sha": C.TARGET_MODEL_SHA, "adapter": "none", "source_rows": "y1_decode"}
        led_c.add(res.n_prompt_tokens, res.n_new_tokens, res.wall_s, res.peak_mem_gb)
        led_s.add(res2.n_prompt_tokens, res2.n_new_tokens, res2.wall_s, res2.peak_mem_gb)
        append_jsonl(target_path, row)
        n += 1
        print(f"[y1/target] {iid} -> actual {actual} / self-guess {guess}", flush=True)
    for led in (led_c, led_s):
        r = led.flush(ledger_path)
        if log_path and r:
            log_line(log_path, f"{led.step}: {r}")
    return n


def select_y1(rows: list[dict[str, Any]], choice_items: list[dict[str, Any]], puzzle_selected: list[dict[str, Any]],
              seed: int = X3.SELECTION_SEED, min_disagree: int = MIN_DISAGREE) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """X3's ``select`` on the union choice rows (DISAGREE + size-matched AGREE_CONTROL, seed) + X3's puzzle sets unchanged."""
    puz = [it for it in puzzle_selected if it["family"] == "puzzle" and it["set"] in PUZZLE_SETS]
    cho_sel, meta = X3.select([r for r in rows if r.get("family") == "choice"], choice_items, seed=seed, min_set=min_disagree)
    cho_sel = [it for it in cho_sel if it["family"] == "choice"]
    selected = puz + cho_sel
    counts = {s: sum(x["set"] == s for x in selected) for s in X3.SETS}
    meta = {**meta, "counts": counts, "min_disagree": min_disagree,
            "underpowered": {"error": counts["error"] < X3.MIN_SET, "disagree": counts["disagree"] < min_disagree},
            "puzzle_source": "items_x3_selected.json (ERROR / ERROR_CONTROL unchanged)",
            "rule": meta["rule"] + f" Y1: puzzles reused from X3; DISAGREE < {min_disagree} is flagged underpowered (descriptive only)."}
    meta.pop("puzzle", None)
    return selected, meta


# ------------------------------------------------------------------ stage capture
def cap_path(item_id: str, caps_dir: Path | None = None) -> Path:
    return (caps_dir or CAPS_DIR) / f"{item_id}.pt"


def load_cap(item_id: str, caps_dir: Path | None = None) -> dict[str, Any]:
    import torch

    p = cap_path(item_id, caps_dir)
    if not p.exists():
        raise FileNotFoundError(f"capture missing for {item_id}: {p}")
    d = torch.load(p, map_location="cpu", weights_only=False)
    if d["acts"].ndim != 3 or d["acts"].shape[0] != len(d["layers"]) or d["acts"].shape[1] != len(d["positions"]):
        raise ValueError(f"{p}: malformed capture {tuple(d['acts'].shape)}")
    return d


def cell_vector(cap: dict[str, Any], layer: int, plabel: str) -> Any | None:
    """fp32 [d] at (layer, position label), or None when the position is absent for this item."""
    if layer not in cap["layers"] or plabel not in cap["labels"]:
        raise KeyError(f"cell {layer}:{plabel} not captured (layers {cap['layers']}, labels {cap['labels']})")
    j = cap["labels"].index(plabel)
    if cap["positions"][j] < 0:
        return None
    return cap["acts"][cap["layers"].index(layer), j].float()


def logit_lens_margins(target: M.Target, hs: dict[int, Any], first_a: int, first_b: int) -> dict[int, dict[str, float]]:
    """final_norm + W_U on each block output ``hs[L]`` (fp32 [d]); {L: {lp_actual, lp_other, margin}} in nats."""
    import torch

    norm = M.final_norm(target.model)
    w_u = M.unembed_weight(target.model)
    dev, dt = w_u.device, w_u.dtype
    out: dict[int, dict[str, float]] = {}
    with torch.no_grad():
        for L, h in hs.items():
            z = norm(h.to(dev, dt)[None, None, :])[0, 0]
            lp = torch.log_softmax((z @ w_u.T).float(), dim=-1)
            out[L] = {"lp_actual": float(lp[first_a]), "lp_other": float(lp[first_b]), "margin": float(lp[first_a] - lp[first_b])}
    return out


def capture_item(target: M.Target, item: dict[str, Any], layers: list[int], n_positions: int = N_POSITIONS,
                 final_layer: int | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """One forward: ({acts bf16 [n_layers, n_pos, d] + meta}, logit-lens row). Positions absent for this item
    (-1) hold zeros in ``acts``."""
    import torch

    ids = M.render_item(target.tokenizer, item["prompt_text"], item.get("system"))
    cand_a, cand_b = item["primary"]["candidates"]
    pm = item_positions(target.tokenizer, ids, cand_a, cand_b, n_positions)
    valid = sorted({p for p in pm["positions"] if p >= 0})
    last = len(ids) - 1
    final_layer = (target.n_layers - 1) if final_layer is None else final_layer
    want_layers = list(layers) + ([final_layer] if final_layer not in layers else [])
    acts = M.capture(target.model, ids, want_layers, valid)  # {L: fp32 [n_valid, d]}
    d = acts[layers[0]].shape[-1]
    idx = {p: i for i, p in enumerate(valid)}
    T = torch.zeros(len(layers), len(pm["positions"]), d, dtype=torch.float32)
    for li, L in enumerate(layers):
        for j, p in enumerate(pm["positions"]):
            if p >= 0:
                T[li, j] = acts[L][idx[p]]
    ft = E.first_token_candidates(target.tokenizer, cand_a, cand_b)
    ll_layers = {L: acts[L][idx[last]] for L in want_layers}
    margins = logit_lens_margins(target, ll_layers, ft["first_A"], ft["first_B"]) if not ft["unscorable"] else {}
    sha = C.sha256_ids(ids)
    cap = {"item_id": item["item_id"], "family": item["family"], "set": item.get("set"), "layers": list(layers), "labels": pm["labels"],
           "positions": pm["positions"], "n_tokens": len(ids), "cand": pm["cand"], "candidates": [cand_a, cand_b],
           "prompt_ids_sha256": sha, "hook": C.HOOK, "dtype": "bfloat16", "model_id": target.model_id, "model_sha": target.revision,
           "render": item.get("render", C.RENDER), "enable_thinking": C.ENABLE_THINKING, "captured_at": now_iso(),
           "acts": T.to(torch.bfloat16)}
    ll_row = {"key": item["item_id"], "item_id": item["item_id"], "family": item["family"], "set": item.get("set"),
              "cand_actual": cand_a, "cand_other": cand_b, "unscorable": bool(ft["unscorable"]), "form": ft.get("form"),
              "first_token_actual": ft.get("first_A"), "first_token_other": ft.get("first_B"), "text_actual": ft.get("text_A"),
              "text_other": ft.get("text_B"), "pos": last, "n_tokens": len(ids), "prompt_ids_sha256": sha, "layers": list(layers),
              "final_layer": final_layer, "margins": {str(L): v["margin"] for L, v in margins.items()},
              "lp_actual": {str(L): v["lp_actual"] for L, v in margins.items()}, "lp_other": {str(L): v["lp_other"] for L, v in margins.items()},
              "created_at": now_iso()}
    if ft["unscorable"]:
        ll_row["reason"] = ft.get("reason")
    return cap, ll_row


def collect_captures(target: M.Target, selected: list[dict[str, Any]], *, layers: list[int] | tuple[int, ...] = LAYERS,
                     n_positions: int = N_POSITIONS, caps_dir: Path = CAPS_DIR, caps_meta_path: Path = CAPS_META_PATH,
                     logitlens_path: Path = LOGITLENS_PATH, ledger_path: Path | None = None, log_path: Path | None = LOG,
                     extra: dict[str, Any] | None = None) -> int:
    """Capture every selected item not yet cached (sha-checked); resumable. Returns the number of new captures."""
    import torch

    caps_dir.mkdir(parents=True, exist_ok=True)
    meta = {r["item_id"]: r for r in read_jsonl(caps_meta_path)}
    ll_done = done_ids(logitlens_path, key="key")
    ledger = StepLedger(step="y1_capture", module=MODULE, extra={"layers": list(layers), "n_positions": n_positions})
    extra = dict(extra or {})
    n = 0
    for it in selected:
        iid = it["item_id"]
        p = cap_path(iid, caps_dir)
        if iid in meta and p.exists() and iid in ll_done:
            ids = M.render_item(target.tokenizer, it["prompt_text"], it.get("system"))
            if meta[iid]["prompt_ids_sha256"] != C.sha256_ids(ids) or meta[iid].get("layers") != list(layers):
                raise RuntimeError(f"{iid}: cached capture was made from a different render / layer grid; delete {p} and its meta row")
            continue
        with timed_call() as st:
            cap, ll = capture_item(target, it, list(layers), n_positions)
        torch.save(cap, p)
        row = {k: v for k, v in cap.items() if k != "acts"}
        row.update(acts_shape=list(cap["acts"].shape), wall_s=st.wall_s, peak_mem_gb=st.peak_mem_gb, **extra)
        if iid not in meta:
            append_jsonl(caps_meta_path, row)
        meta[iid] = row
        if iid not in ll_done:
            append_jsonl(logitlens_path, {**ll, **extra})
            ll_done.add(iid)
        ledger.add(cap["n_tokens"], 0, st.wall_s, st.peak_mem_gb)
        n += 1
        ca, cb = cap["cand"]["candA"]["pos"], cap["cand"]["candB"]["pos"]
        print(f"[y1/capture] {iid} ({it['set']}): {cap['n_tokens']} tokens, candA@{ca} candB@{cb}, "
              f"logit-lens margin L{layers[-1]} = {ll['margins'].get(str(layers[-1]))}", flush=True)
    r = ledger.flush(ledger_path)
    if log_path and r:
        log_line(log_path, f"capture: {r}")
    return n


# ------------------------------------------------------------------ stage reread
def lo_key(reader_name: str, site: str, item_id: str) -> str:
    return f"{reader_name}|{site}|{item_id}"


def site_label(layer: int, plabel: str) -> str:
    return f"{layer}:{plabel}"


def load_site_states(selected: list[dict[str, Any]], layer: int, plabel: str, caps_dir: Path | None = None
                     ) -> tuple[list[dict[str, Any]], Any, list[dict[str, Any]]]:
    """(items with a vector at the cell, H fp32 [N, d], items without one)."""
    import torch

    keep, hs, missing = [], [], []
    for it in selected:
        v = cell_vector(load_cap(it["item_id"], caps_dir), layer, plabel)
        if v is None:
            missing.append(it)
        else:
            keep.append(it)
            hs.append(v)
    return keep, (torch.stack(hs) if hs else torch.zeros(0, 1)), missing


def reader_layer(reader_name: str, layer: int) -> int | None:
    """The layer integer handed to the reader: J-lens the true L; OLens the nearest grid layer (``olens``) or the true L
    (``olens_trueL``); NLA none (L42-trained; transfer test)."""
    if reader_name == "jlens":
        return layer
    if reader_name == "olens":
        return nearest_grid_layer(layer)
    if reader_name == "olens_trueL":
        return layer
    return None


def collect_lo_site(reader: Any, selected: list[dict[str, Any]], layer: int, plabel: str, *, reader_name: str | None = None,
                    lo_path: Path = LO_PATH, ledger_path: Path | None = None, log_path: Path | None = LOG,
                    caps_dir: Path | None = None, batch: int = 32, extra: dict[str, Any] | None = None) -> int:
    """Native LO of one reader on every selected item's vector at the site (candidates (actual, other)), plus one E3
    mean-state row per set. key = reader|site|item_id (mean rows: reader|site|mean|set); resumable."""
    import torch

    name = reader_name or reader.name
    site = site_label(layer, plabel)
    L_used = reader_layer(name, layer)
    done = done_ids(lo_path, key="key")
    ledger = StepLedger(step=f"y1_lo_{name}", module=MODULE, extra={"site": site, "layer_used": L_used, "batch": batch})
    ledger_m = StepLedger(step=f"y1_mean_lo_{name}", module=MODULE, extra={"site": site})
    extra = dict(extra or {})
    base = {"reader": name, "reader_class": type(reader).__name__, "site": site, "layer": layer, "position": plabel, "layer_used": L_used,
            "layer_role": ("native" if name == "jlens" else "nearest_grid" if name == "olens" else "true_layer_sensitivity" if name == "olens_trueL"
                           else "transfer_from_L42"), **C.frozen_shas(), **extra}
    kw = {"layer": L_used} if L_used is not None else {}
    n = 0
    for fam in X3.FAMILIES:
        fam_items = [it for it in selected if it["family"] == fam]
        keep, H, missing = load_site_states(fam_items, layer, plabel, caps_dir)
        for it in missing:
            k = lo_key(name, site, it["item_id"])
            if k in done:
                continue
            append_jsonl(lo_path, {"key": k, **base, "item_id": it["item_id"], "family": fam, "set": it["set"],
                                   "cand_actual": it["primary"]["candidates"][0], "cand_other": it["primary"]["candidates"][1],
                                   "text_key": it.get("text_key"), "lo_actual": None, "lp_actual": None, "lp_other": None, "favours_actual": None,
                                   "unscorable": True, "reason": f"position {plabel} absent for this item", "created_at": now_iso()})
            n += 1
        todo = [i for i, it in enumerate(keep) if lo_key(name, site, it["item_id"]) not in done]
        for s in range(0, len(todo), batch):
            idx = todo[s: s + batch]
            chunk = [keep[i] for i in idx]
            Hc = H[idx]
            pairs = [(it["primary"]["candidates"][0], it["primary"]["candidates"][1]) for it in chunk]
            with timed_call() as st:
                rows = LO.score_lo(reader, Hc, pairs, fam, batch=batch, **kw)
            for it, r in zip(chunk, rows):
                row = {"key": lo_key(name, site, it["item_id"]), **base, "item_id": it["item_id"], "family": fam, "set": it["set"],
                       "cand_actual": r["cand_A"], "cand_other": r["cand_B"], "text_key": it.get("text_key"), "lo_actual": r["lo"],
                       "lp_actual": r["lp_A"], "lp_other": r["lp_B"], "favours_actual": (r["lo"] > 0) if r["lo"] is not None else None,
                       "templates": r["templates"], "unscorable": r["unscorable"], "wall_s_chunk": st.wall_s, "chunk_size": len(chunk),
                       "created_at": now_iso()}
                for k in ("per_template", "variants_A", "variants_B", "best_A", "best_B", "reason", "n_tokens_A", "n_tokens_B", "format", "layer_in_prompt"):
                    if k in r:
                        row[k] = r[k]
                append_jsonl(lo_path, row)
                n += 1
            ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
            print(f"[y1/lo/{name}@{site}] {fam}: {len(chunk)} states scored ({s + len(chunk)}/{len(todo)})", flush=True)
        # E3 gate: LO on the mean state of each set, against every item's own candidate pair
        for set_ in (PUZZLE_SETS if fam == "puzzle" else CHOICE_SETS):
            k = f"{name}|{site}|mean|{set_}"
            its = [it for it in keep if it["set"] == set_]
            if k in done or not its:
                continue
            Hs = torch.stack([H[i] for i, it in enumerate(keep) if it["set"] == set_])
            h_mean = Hs.mean(0)
            pairs = [(it["primary"]["candidates"][0], it["primary"]["candidates"][1]) for it in its]
            with timed_call() as st:
                rows = LO.score_lo(reader, h_mean[None].expand(len(its), -1).contiguous(), pairs, fam, batch=batch, **kw)
            los = [r["lo"] for r in rows if not r["unscorable"] and r["lo"] is not None]
            mean_lo = sum(los) / len(los) if los else None
            append_jsonl(lo_path, {"key": k, **base, "condition": "mean_state", "set": set_, "family": fam, "n_states_in_mean": len(its),
                                   "mean_norm": float(h_mean.norm()), "n_scorable": len(los), "mean_lo": mean_lo,
                                   "mean_abs_lo": (sum(abs(x) for x in los) / len(los)) if los else None,
                                   "within_band": (abs(mean_lo) <= E3_BAND) if mean_lo is not None else None, "band": E3_BAND,
                                   "per_item": [{"item_id": it["item_id"], "lo": r["lo"], "unscorable": r["unscorable"]} for it, r in zip(its, rows)],
                                   "wall_s": st.wall_s, "created_at": now_iso()})
            ledger_m.add(0, 0, st.wall_s, st.peak_mem_gb)
            n += 1
            print(f"[y1/mean_lo/{name}@{site}] {set_}: mean LO {mean_lo}", flush=True)
    for led in (ledger, ledger_m):
        r = led.flush(ledger_path)
        if log_path and r:
            log_line(log_path, f"{led.step}: {r}")
    return n


# ------------------------------------------------------------------ main
def parse_layers(s: str) -> list[int]:
    out = sorted({int(x) for x in s.split(",") if x.strip()})
    if not out:
        raise ValueError("--layers must list at least one layer")
    return out


def main(argv: list[str] | None = None) -> int:
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "B"], required=True)
    ap.add_argument("--stage", choices=["select", "capture", "reread"], required=True)
    ap.add_argument("--layers", default=",".join(map(str, LAYERS)))
    ap.add_argument("--positions", type=int, default=N_POSITIONS, help="number of trailing positions (last ... last-(n-1))")
    ap.add_argument("--limit", type=int, default=0, help="select: first N choice items of each file; capture/reread: first N selected items")
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--site", default=None, help="reread: L:P with P an offset from the last position or candA/candB")
    ap.add_argument("--readers", default=None, help="reread: comma list (phase A default jlens,olens; phase B default nla)")
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--x3-candidates", default=str(X3.CANDIDATES_JSON))
    ap.add_argument("--y1-choice", default=str(Y1_CHOICE_JSON))
    ap.add_argument("--x3-selected", default=str(X3.SELECTED_JSON))
    a = ap.parse_args(argv)
    ok, note = X3.frozen_x_status(a.x3_candidates)
    if not ok and not a.allow_unfrozen:
        raise SystemExit(f"refusing to collect Y1: {note} (pass --allow-unfrozen for a smoke run)")
    Y_DIR.mkdir(parents=True, exist_ok=True)
    extra = {"x3_candidates_sha256": C.sha256_file(a.x3_candidates), "y1_choice_sha256": C.sha256_file(a.y1_choice), "frozen_x": ok}
    layers = parse_layers(a.layers)
    if a.stage == "select":
        if a.phase != "A":
            raise SystemExit("select runs in phase A (target model)")
        choice_items, umeta = load_union_choice(a.x3_candidates, a.y1_choice, a.limit)
        _, x3_sel = X3.load_selected(a.x3_selected)
        n_seed = seed_from_x3(choice_items)
        target = load_target_timed(MODULE)
        log_line(LOG, f"select: {umeta['n_x3_choice']} X3 + {umeta['n_y1_choice']} Y1 choice candidates (limit={a.limit}); "
                      f"{n_seed} rows copied from x3_target.jsonl; freeze: {note}; caps choice={X3.CHOICE_CAP} self_guess={X3.SELF_GUESS_CAP}")
        n_new = collect_target_choice(target, choice_items, extra=extra)
        rows = read_jsonl(TARGET_PATH)
        selected, smeta = select_y1(rows, choice_items, x3_sel)
        smeta.update(umeta, x3_selected=str(a.x3_selected), x3_selected_sha256=C.sha256_file(a.x3_selected), limit=a.limit)
        sel_path = SELECTED_JSON if not a.limit else SELECTED_JSON.with_name(f"items_y1_selected_limit{a.limit}.json")
        X3.write_selected(sel_path, selected, smeta)
        msg = (f"selection ({n_new} new decode pairs, {n_seed} reused): counts {smeta['counts']}; underpowered {smeta['underpowered']}; "
               f"choice {smeta['choice']['n_disagree']} disagree / {smeta['choice']['n_agree']} agree / {smeta['choice']['n_unparsed']} unparsed "
               f"of {smeta['choice']['n_rows']} -> {sel_path.name}")
        print(f"[y1] {msg}", flush=True)
        log_line(LOG, msg)
        if smeta["underpowered"]["disagree"]:
            log_line(LOG, f"K6 (Y1): DISAGREE has {smeta['counts']['disagree']} < {MIN_DISAGREE} items: reported descriptively only")
        M.unload(target)
        return 0
    smeta, selected = X3.load_selected(SELECTED_JSON)
    if a.limit:  # smoke runs: the first N items of EVERY set
        selected = [it for s in X3.SETS for it in [x for x in selected if x["set"] == s][: a.limit]]
    if a.stage == "capture":
        if a.phase != "A":
            raise SystemExit("capture runs in phase A (target model)")
        target = load_target_timed(MODULE)
        log_line(LOG, f"capture: {len(selected)} selected items, layers {layers}, positions last..last-{a.positions - 1} + candA/candB; freeze: {note}")
        n = collect_captures(target, selected, layers=layers, n_positions=a.positions, extra=extra)
        log_line(LOG, f"capture: {n} new captures -> {CAPS_DIR} ({len(read_jsonl(CAPS_META_PATH))} cached); logit-lens rows {len(read_jsonl(LOGITLENS_PATH))}")
        M.unload(target)
        return 0
    # reread
    if not a.site:
        raise SystemExit("--site L:P is required for reread (S* from results/g_agreement/y1/summary.json)")
    layer, plabel = parse_site(a.site)
    readers = [r.strip() for r in (a.readers or ("jlens,olens" if a.phase == "A" else "nla")).split(",") if r.strip()]
    log_line(LOG, f"reread phase {a.phase} at {site_label(layer, plabel)}: readers {readers}; {len(selected)} selected items; freeze: {note}")
    if a.phase == "A":
        bad = [r for r in readers if r not in ("jlens", "olens")]
        if bad:
            raise SystemExit(f"phase A rereads jlens/olens only, got {bad}")
        target = load_target_timed(MODULE)
        if "jlens" in readers:
            jl = R.JLensReader().bind(target, layers_keep=[layer])
            if layer not in jl.J:
                raise SystemExit(f"J-lens has no layer {layer} (source layers {jl.source_layers[:3]}..{jl.source_layers[-3:]})")
            collect_lo_site(jl, selected, layer, plabel, batch=a.batch, extra=extra)
            del jl
        if "olens" in readers:
            ol = R.OLensReader().bind(target)
            log_line(LOG, f"olens adapter={ol.adapter_dir} liveness={ol.liveness}; grid layer for L{layer} = {nearest_grid_layer(layer)}")
            collect_lo_site(ol, selected, layer, plabel, reader_name="olens", batch=a.batch, extra=extra)
            collect_lo_site(ol, selected, layer, plabel, reader_name="olens_trueL", batch=a.batch, extra=extra)
        M.unload(target)
    else:
        bad = [r for r in readers if r != "nla"]
        if bad:
            raise SystemExit(f"phase B rereads nla only, got {bad}")
        ledger = StepLedger(step="load_nla", module=MODULE)
        with timed_call() as st:
            nla = R.NLAReader().bind()
        ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
        ledger.flush()
        log_line(LOG, f"phase B: nla adapter={nla.adapter_dir} liveness={nla.liveness}; transfer test at L{layer} (trained at L42); "
                      f"gate = mean-state LO within +-{E3_BAND} nat")
        collect_lo_site(nla, selected, layer, plabel, batch=a.batch, extra=extra)
        nla.unload()
    return 0


if __name__ == "__main__":
    sys.exit(main())
