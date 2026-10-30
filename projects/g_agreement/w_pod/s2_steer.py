"""S2 — the steering matrix (BRIEF_WV S2; PREREG_WV "Pod session").

    python -m projects.g_agreement.w_pod.s2_steer --phase A --family ownership|mapping|errors|all --alphas 0.5,1.0 --k-random 10 --n-states 64 [--force]

States: ownership / mapping = both sources of the 32 X2 pairs named in cache/g_agreement/w/directions/<family>/index.json (full L38
captures in cache/g_agreement/x/full); errors = 64 of the 297 puzzle-error items drawn by seed 0 (numpy default_rng(0) over the sorted
ids listed in the errors index), base state = the Y1 block-48 last-token capture. For each state, each direction family in
{d_cm, d_pw, d_J, d_res, full} × α ∈ {0.5, 1.0} and K = 10 seeded random directions at α 1 (matched norm), the edit
    h'(pos) = h(pos) + toward · α · ‖Δ(pos)‖ · d̂(pos)     (toward = +1 from source A / errors, −1 from source B)
is applied at the family's site positions (the direction file's positions; errors: the last token) at the edit layer (38 / 38 / 48)
during the prefill; the greedy 8-token decode, the parsed answer, flip (= the other candidate), lo_model (first-token log-odds,
positive = toward the other candidate) and the read-back block-42 (and block-48 for errors) last-token vectors are recorded
→ cache/g_agreement/w/s2_behaviour.jsonl (key = pair|source|W2|direction|alpha|k) and s2_readvecs/<key>.pt ({read: {L: bf16 [d]},
edited: bf16 [P, d], positions}). One unedited ``natural`` row per state gives the baseline. The planned decode table is printed
before the first decode and the run refuses above --cap (4,500). Checkpoints: DONE_<family> per family, DONE for the stage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core.accounting import append_jsonl, done_ids, now_iso, read_jsonl, timed_call

from . import common as W

STAGE = "s2"
SITE = "W2"
NATURAL = "natural"
RANDOM = "random"


# ------------------------------------------------------------------ states
def entry_key(pair_id: str, source: str, direction: str, alpha: float, k: int | None) -> str:
    return f"{pair_id}|{source}|{SITE}|{direction}|{float(alpha)}|{k}"


def x2_states(family: str, idx: dict[str, Any], *, items_x: Path | None = None, x_full_dir: Path | None = None, n_states: int = W.S2_N_STATES) -> list[dict[str, Any]]:
    """(pair, source) states of ownership / mapping: the pairs of the directions index that have X2 full captures, in index order,
    both sources, the first ``n_states``."""
    items = C.load_items("all", 0, path=items_x or W.ITEMS_X)
    by_pair: dict[str, dict[str, Any]] = {}
    for it in items:
        if it["family"] == family:
            by_pair.setdefault(it["pair_id"], {})[it["version"]] = it
    out = []
    for pid, f in idx["files"].items():
        p = by_pair.get(pid)
        if not p or "A" not in p or "B" not in p:
            print(f"[w/s2] note: pair {pid} not in items_x.json with both versions; skipped", flush=True)
            continue
        caps = {v: (x_full_dir or W.X_FULL_DIR) / f"{p[v]['item_id']}.pt" for v in "AB"}
        if not all(c.exists() for c in caps.values()):
            print(f"[w/s2] note: pair {pid} has no X2 full capture; skipped", flush=True)
            continue
        for src in ("A", "B"):
            it = p[src]
            other = [c for c in it["primary"]["candidates"] if c != it["primary"]["answer"]][0]
            out.append({"pair_id": pid, "source": src, "state_item_id": it["item_id"], "item": it, "family": family, "direction_file": f,
                        "cand_A": str(it["primary"]["answer"]), "cand_B": str(other), "cap_path": caps[src], "cap_kind": "x2_full"})
    return out[: n_states or None]


def error_states(idx: dict[str, Any], *, items_y1: Path | None = None, caps_dir: Path | None = None, n_states: int = W.S2_N_STATES, seed: int = 0) -> list[dict[str, Any]]:
    """The error states: ids of the errors directions index (fallback: every error item) ∩ Y1 captures, ``n_states`` drawn by seed."""
    errs = {it["item_id"]: it for it in W.load_errors(items_y1)}
    ids = [i for i in idx["files"] if i in errs] or sorted(errs)
    have = [i for i in ids if (caps_dir or W.Y1_CAPS_DIR).joinpath(f"{i}.pt").exists()]
    chosen = W.seeded_subset(have, n_states, seed)
    out = []
    for iid in chosen:
        it = errs[iid]
        a, b = it["primary"]["candidates"][0], it["primary"]["candidates"][1]
        out.append({"pair_id": iid, "source": "A", "state_item_id": iid, "item": it, "family": "errors",
                    "direction_file": idx["files"].get(iid, idx["dir"] / f"{iid}.pt"), "cand_A": str(a), "cand_B": str(b),
                    "cap_path": (caps_dir or W.Y1_CAPS_DIR) / f"{iid}.pt", "cap_kind": "y1_cap"})
    return out


def load_states(family: str, *, directions_root: Path | None = None, n_states: int = W.S2_N_STATES, **paths: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    idx = W.directions_index(family, directions_root)
    if family == "errors":
        return idx, error_states(idx, n_states=n_states, items_y1=paths.get("items_y1"), caps_dir=paths.get("y1_caps_dir"))
    return idx, x2_states(family, idx, items_x=paths.get("items_x"), x_full_dir=paths.get("x_full_dir"), n_states=n_states)


# ------------------------------------------------------------------ table / plan
def condition_table(states: list[dict[str, Any]], *, directions: tuple[str, ...] = W.S2_DIRECTIONS, alphas: tuple[float, ...] = W.S2_ALPHAS,
                    k_random: int = W.S2_K_RANDOM, random_alpha: float = W.S2_RANDOM_ALPHA, include_natural: bool = True) -> list[dict[str, Any]]:
    """Tensor-free entries: per state 1 natural + |directions| × |alphas| + k_random (α random_alpha)."""
    out = []
    for s in states:
        base = {"pair_id": s["pair_id"], "source": s["source"], "state_item_id": s["state_item_id"], "family": s["family"]}
        if include_natural:
            out.append({**base, "direction": NATURAL, "alpha": 0.0, "k": None, "key": entry_key(s["pair_id"], s["source"], NATURAL, 0.0, None)})
        for d in directions:
            for a in alphas:
                out.append({**base, "direction": d, "alpha": float(a), "k": None, "key": entry_key(s["pair_id"], s["source"], d, a, None)})
        for k in range(int(k_random)):
            out.append({**base, "direction": RANDOM, "alpha": float(random_alpha), "k": k, "key": entry_key(s["pair_id"], s["source"], RANDOM, random_alpha, k)})
    return out


def planned_decodes(tables: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    per: dict[str, dict[str, int]] = {}
    for fam, tab in tables.items():
        c: dict[str, int] = {}
        for e in tab:
            c[e["direction"]] = c.get(e["direction"], 0) + 1
        c["total"] = len(tab)
        per[fam] = c
    return {"families": per, "total_planned": sum(v["total"] for v in per.values())}


def format_plan(plan: dict[str, Any], cap: int) -> str:
    lines = []
    for fam, c in plan["families"].items():
        lines.append(f"  {fam:10s} " + "  ".join(f"{k}={v}" for k, v in c.items() if k != "total") + f"  total={c['total']}")
    lines.append(f"  total planned decodes {plan['total_planned']}   cap {cap}")
    return "\n".join(lines)


def check_cap(plan: dict[str, Any], cap: int = W.S2_DECODE_CAP) -> None:
    if plan["total_planned"] > cap:
        raise SystemExit(f"refusing to run: {plan['total_planned']} planned decodes exceed the cap {cap} ({plan})")


# ------------------------------------------------------------------ vectors
def base_capture(state: dict[str, Any], edit_layer: int) -> dict[str, Any]:
    """{"ids": [T], "h": fp32 [T, d] or None, "h_last": fp32 [d], "sha"} at the edit layer for one state."""
    import torch

    d = torch.load(state["cap_path"], map_location="cpu", weights_only=False)
    if state["cap_kind"] == "x2_full":
        if edit_layer not in {int(k) for k in d["layers"]}:
            raise RuntimeError(f"{state['state_item_id']}: X2 capture has no layer {edit_layer}")
        h = d["layers"][edit_layer] if edit_layer in d["layers"] else d["layers"][str(edit_layer)]
        h = h.float()
        return {"ids": [int(t) for t in d["ids"]], "h": h, "h_last": h[-1], "sha": d.get("prompt_ids_sha256"), "n_tokens": int(d["n_tokens"])}
    layers = [int(x) for x in d["layers"]]
    if edit_layer not in layers or "0" not in d["labels"]:
        raise RuntimeError(f"{state['state_item_id']}: Y1 capture lacks layer {edit_layer} / the last position")
    h_last = d["acts"][layers.index(edit_layer), d["labels"].index("0")].float()
    return {"ids": None, "h": None, "h_last": h_last, "sha": d.get("prompt_ids_sha256"), "n_tokens": int(d["n_tokens"])}


def entry_vectors(e: dict[str, Any], dirs: dict[str, Any], cap: dict[str, Any], T: int) -> dict[str, Any]:
    """positions, base ``[P, d]``, delta ``[P, d]`` (edited = base + delta) and the geometry record of one entry."""
    import torch

    pos = [int(p) % T for p in dirs["positions"]]
    P = len(pos)
    if cap["h"] is not None:
        base = cap["h"][pos].clone()
    else:
        if pos != [T - 1]:
            raise RuntimeError(f"{e['key']}: last-token-only capture but positions {pos}")
        base = cap["h_last"][None].clone()
    toward = -1.0 if e["source"] == "B" else 1.0
    alpha = float(e["alpha"])
    norm = dirs["norm"].reshape(-1)
    delta_nat = dirs["delta"]
    unit_nat = delta_nat / delta_nat.norm(dim=1, keepdim=True).clamp_min(1e-9)
    d = e["direction"]
    if d == NATURAL:
        delta = torch.zeros_like(base)
        u = None
    elif d == RANDOM:
        u = W.random_unit_directions(e["pair_id"], int(e["k"]), P, base.shape[1], seed=dirs.get("random_seed"))  # Track B recipe when the file carries random.seed
        delta = alpha * norm[:, None] * u
    else:
        if d not in dirs:
            raise KeyError(f"{e['key']}: direction {d} missing from the file ({dirs['names_in_file']})")
        u = dirs[d]
        delta = toward * alpha * norm[:, None] * u
    cos = None if u is None else [float((u[i] * unit_nat[i]).sum()) for i in range(P)]
    v = base + delta
    return {"positions": pos, "n_positions": P, "base": base, "delta": delta, "vector": v, "dose_abs": float(delta.norm()), "norm_delta_pos": [float(x) for x in norm],
            "random_seed": (dirs.get("random_seed") if d == RANDOM else None),
            "cos_to_delta": cos, "cos_to_delta_mean": (None if cos is None else sum(cos) / len(cos)), "input_norm_pos": [float(x) for x in v.norm(dim=1)],
            "input_norm_natural_pos": [float(x) for x in base.norm(dim=1)], "last_edited": (T - 1) in pos, "toward": toward}


# ------------------------------------------------------------------ behaviour
def readvec_path(key: str, readvec_dir: Path | None = None) -> Path:
    return (readvec_dir or W.S2_READVECS) / f"{W.safe_key(key)}.pt"


def load_readvec(key: str, layer: int, readvec_dir: Path | None = None) -> Any:
    import torch

    d = torch.load(readvec_path(key, readvec_dir), map_location="cpu", weights_only=False)
    return d["read"][int(layer)].float()


def load_readvec_record(key: str, readvec_dir: Path | None = None) -> dict[str, Any]:
    import torch

    return torch.load(readvec_path(key, readvec_dir), map_location="cpu", weights_only=False)


def collect_behaviour(target: M.Target, family: str, states: list[dict[str, Any]], table: list[dict[str, Any]], *, edit_layer: int | None = None,
                      read_layers: tuple[int, ...] | None = None, beh_path: Path | None = None, readvec_dir: Path | None = None, ledger_path: Path | None = None,
                      log_path: Path | None = None, max_new_tokens: int = W.BEHAVIOUR_TOKENS, batch: int = W.DEFAULT_BATCH, dirs_cache: dict[str, Any] | None = None,
                      progress: tuple[int, int] | None = None) -> int:
    """Decode every entry not yet done, batched over the entries of one state (same ids, same positions). Resumable by key."""
    import torch

    edit_layer = W.S2_EDIT_LAYER[family] if edit_layer is None else int(edit_layer)
    read_layers = tuple(W.S2_READ_LAYERS[family] if read_layers is None else read_layers)
    beh_path = beh_path or W.S2_BEHAVIOUR
    readvec_dir = readvec_dir or W.S2_READVECS
    readvec_dir.mkdir(parents=True, exist_ok=True)
    done = {k for k in done_ids(beh_path, key="key") if readvec_path(k, readvec_dir).exists()}
    ledgers: dict[str, Any] = {}
    extra = W.row_extra()
    dt = getattr(torch, W.SAVE_DTYPE)
    dirs_cache = {} if dirs_cache is None else dirs_cache
    by_state: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for e in table:
        if e["key"] not in done:
            by_state.setdefault((e["pair_id"], e["source"]), []).append(e)
    n = 0
    n_done0 = len(table) - sum(len(v) for v in by_state.values())
    from . import status as ST

    for s in states:
        ents = by_state.get((s["pair_id"], s["source"]))
        if not ents:
            continue
        it = s["item"]
        cap = base_capture(s, edit_layer)
        ids = cap["ids"] if cap["ids"] is not None else W.render_ids(target.tokenizer, it)
        sha = C.sha256_ids(ids)
        if cap["sha"] not in (None, sha):
            raise RuntimeError(f"{s['state_item_id']}: cached capture sha {cap['sha'][:10]} != render {sha[:10]}")
        T = len(ids)
        fkey = str(s["direction_file"])
        if fkey not in dirs_cache:
            dirs_cache[fkey] = W.load_direction_file(Path(s["direction_file"]))
        dirs = dirs_cache[fkey]
        ft = W.pair_first_tokens(target.tokenizer, s["cand_A"], s["cand_B"], W.item_render(it))
        tok_ids = [None, None] if ft["unscorable"] else [ft["first_A"], ft["first_B"]]
        nat = [e for e in ents if e["direction"] == NATURAL]
        edited = [e for e in ents if e["direction"] != NATURAL]
        groups: list[list[dict[str, Any]]] = ([nat] if nat else []) + [edited[i: i + batch] for i in range(0, len(edited), batch)]
        for chunk in groups:
            vecs = [entry_vectors(e, dirs, cap, T) for e in chunk]
            if chunk[0]["direction"] == NATURAL:
                rows = W.prefill_generate(target, ids, read_layers=read_layers, max_new_tokens=max_new_tokens, first_token_ids=tok_ids)
            else:
                rows = W.prefill_generate(target, ids, edit_layer=edit_layer, row_positions=[v["positions"] for v in vecs], row_vectors=[v["vector"] for v in vecs],
                                          read_layers=read_layers, max_new_tokens=max_new_tokens, first_token_ids=tok_ids)
            for e, v, r in zip(chunk, vecs, rows):
                parsed, evidence = W.parse_answer(r["answer_text"], {**it, "primary": {**it["primary"], "candidates": [s["cand_A"], s["cand_B"]], "candidates_all": [s["cand_A"], s["cand_B"]]}})
                torch.save({"key": e["key"], "read": {int(L): r["read"][L].to(dt) for L in read_layers}, "edited": v["vector"].to(dt), "positions": v["positions"],
                            "edit_layer": edit_layer, "dtype": W.SAVE_DTYPE}, readvec_path(e["key"], readvec_dir))
                row = {"key": e["key"], "pair_id": s["pair_id"], "family": family, "source": s["source"], "state_item_id": s["state_item_id"], "site": SITE,
                       "direction": e["direction"], "condition": e["direction"], "alpha": e["alpha"], "k": e["k"], "edit_layer": edit_layer, "read_layers": list(read_layers),
                       "positions": v["positions"], "n_positions": v["n_positions"], "n_tokens": T, "toward": v["toward"], "cand_A": s["cand_A"], "cand_B": s["cand_B"],
                       "answer_text": r["answer_text"], "parsed": parsed, "parse_evidence": evidence, "flipped_to_other": parsed == s["cand_B"], "kept_original": parsed == s["cand_A"],
                       "coherent": parsed in (s["cand_A"], s["cand_B"]), "lo_model": W.lo_from_lp(r.get("lp_first")), "lp_first_A": (r.get("lp_first") or [None, None])[0],
                       "lp_first_B": (r.get("lp_first") or [None, None])[1], "lo_model_unscorable": bool(ft["unscorable"]), "lo_model_form": ft.get("form"),
                       "first_A": ft.get("first_A"), "first_B": ft.get("first_B"), "first_token_id": r["first_token_id"], "top1_id": r["top1_id"],
                       "dose_abs": v["dose_abs"], "norm_delta_pos": v["norm_delta_pos"], "cos_to_delta_mean": v["cos_to_delta_mean"], "input_norm_pos": v["input_norm_pos"], "random_seed": v["random_seed"],
                       "input_norm_natural_pos": v["input_norm_natural_pos"], "last_edited": v["last_edited"], "n_new_tokens": r["n_new_tokens"], "finish_reason": r["finish_reason"],
                       "n_hook_edits": r["n_hook_edits"], "batch_size": r["batch_size"], "wall_s": r["wall_s_batch"] / max(1, r["batch_size"]), "wall_s_batch": r["wall_s_batch"],
                       "peak_mem_gb": r["peak_mem_gb"], "prompt_ids_sha256": sha, "readvec_dtype": W.SAVE_DTYPE, "direction_file": Path(s["direction_file"]).name, **extra}
                append_jsonl(beh_path, row)
                n += 1
            for dname in {e["direction"] for e in chunk}:
                sub = [r for e, r in zip(chunk, rows) if e["direction"] == dname]
                ld = ledgers.setdefault(dname, W.ledger(f"s2_behaviour_{family}_{dname}", {"max_new_tokens": max_new_tokens, "batch": batch, "edit_layer": edit_layer}))
                ld.add(T * len(sub), sum(r["n_new_tokens"] for r in sub), rows[0]["wall_s_batch"] * len(sub) / len(chunk), rows[0]["peak_mem_gb"])
        print(f"[w/s2/{family}] {s['pair_id']}|{s['source']}: {len(ents)} entries decoded ({n} so far)", flush=True)
        if progress is not None:
            ST.progress(f"S2 steering matrix ({family})", progress[0] + n_done0 + n, progress[1])
    for ld in ledgers.values():
        rr = ld.flush(ledger_path)
        if rr:
            W.wlog(f"s2 {ld.step}: {rr}", log_path)
    return n


def family_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for r in rows:
        c = out.setdefault(f"{r['direction']}@{r['alpha']}", {"n": 0, "flips": 0, "coherent": 0})
        c["n"] += 1
        c["flips"] += int(bool(r["flipped_to_other"]))
        c["coherent"] += int(bool(r["coherent"]))
    return out


# ------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A"], default="A")
    ap.add_argument("--family", default="all", help="ownership|mapping|errors|all")
    ap.add_argument("--alphas", default=",".join(str(a) for a in W.S2_ALPHAS))
    ap.add_argument("--k-random", type=int, default=W.S2_K_RANDOM)
    ap.add_argument("--n-states", type=int, default=W.S2_N_STATES)
    ap.add_argument("--cap", type=int, default=W.S2_DECODE_CAP)
    ap.add_argument("--batch", type=int, default=W.DEFAULT_BATCH)
    ap.add_argument("--max-new-tokens", type=int, default=W.BEHAVIOUR_TOKENS)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    fams = tuple(W.S2_FAMILIES) if a.family == "all" else tuple(f.strip() for f in a.family.split(",") if f.strip())
    alphas = tuple(float(x) for x in a.alphas.split(",") if x.strip())
    if a.family == "all" and W.refuse_if_done(STAGE, a.force):
        return 0
    todo_f = [f for f in fams if not W.refuse_if_done(STAGE, a.force, sub=f)]
    if not todo_f:
        if a.family == "all":
            W.mark_done(STAGE, info={"families": list(fams), "note": "all family markers present"})
        return 0
    loaded: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {}
    for f in todo_f:
        try:
            loaded[f] = load_states(f, n_states=a.n_states)
        except FileNotFoundError as exc:
            print(f"[w/s2] {f}: {exc}; family skipped", flush=True)
            W.wlog(f"s2 {f}: SKIPPED ({exc})")
    tables = {f: condition_table(st, alphas=alphas, k_random=a.k_random) for f, (_, st) in loaded.items()}
    plan = planned_decodes(tables)
    print("[w/s2] planned decodes:\n" + format_plan(plan, a.cap), flush=True)
    W.wlog(f"s2 plan: {json.dumps(plan)}; cap {a.cap}; alphas {alphas}; k_random {a.k_random}; n_states {a.n_states}")
    check_cap(plan, a.cap)
    if not loaded:
        return 0
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    target = load_target_timed(W.MODULE)
    W.W_CACHE.mkdir(parents=True, exist_ok=True)
    offset = 0
    for f, (idx, st) in loaded.items():
        print(f"[w/s2] family {f}: {len(st)} states, edit layer {W.S2_EDIT_LAYER[f]}, read {W.S2_READ_LAYERS[f]}, directions from {idx['dir']}", flush=True)
        n = collect_behaviour(target, f, st, tables[f], max_new_tokens=a.max_new_tokens, batch=a.batch, progress=(offset, plan["total_planned"]))
        offset += len(tables[f])
        rows = [r for r in read_jsonl(W.S2_BEHAVIOUR) if r["family"] == f]
        summ = family_summary(rows)
        W.wlog(f"s2 {f}: {n} new decodes; {len(rows)} rows; flips {json.dumps(summ)}")
        W.mark_done(STAGE, sub=f, info={"n_states": len(st), "n_rows": len(rows), "summary": summ, "plan": plan["families"].get(f)})
    if a.family == "all" and all(W.is_done(STAGE, sub=f) for f in fams):
        W.mark_done(STAGE, info={"families": list(fams), "plan": plan})
    M.unload(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
