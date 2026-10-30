"""S1 — capture the Phase W bank (BRIEF_WV S1 + V7).

    python -m projects.g_agreement.w_pod.s1_capture --phase A [--families counts,ownership4,arith,mapping8,v7] [--limit N] [--force]

For every item of items_w.json (+ the 16 V7 pairs with the preamble as a system turn, + the 47 × 2 mapping-8 items of items_x.json)
ONE forward with hooks at layers 20, 28, 38, 42, 48, 52 at ALL positions (bf16 ``[6, T, d]`` → cache/g_agreement/w/s1_caps/<item_id>.pt
with ids and meta), the greedy answer from the same prefill (cap 8 tokens; 16 for counts / arith) and the first-token log-odds of the
candidate pair; for families with a candidates_all list (counts 1..99, arith, ownership4, mapping8) the log-prob of EVERY candidate's
first token at the answer position (the full vector) → cache/g_agreement/w/s1_target.jsonl (key = item_id, resumable). Arith items
render PLAIN (the prompt text as is, no chat template). The block-42 and block-48 last-token fp32 states are also written as
states-style files (cache/g_agreement/w/states_L42/<item_id>.pt + states_L42_meta.jsonl; same for L48) so the existing collectors
(x1_bank E1, binding_factorial/check_variance) can read them. Counts correctness filter (greedy answer == true N, requiring
>= 95 % overall) → results/g_agreement/w/s1/counts_kept.json. DONE marker: results/g_agreement/w/s1/DONE."""

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

STAGE = "s1"
S1_FAMILIES: tuple[str, ...] = ("counts", "ownership4", "arith", "mapping8", "v7")
COUNTS_MIN_CORRECT = 0.95


# ------------------------------------------------------------------ items
def s1_items(families: tuple[str, ...] = S1_FAMILIES, *, items_w: Path | None = None, mapping8_index: Path | None = None,
             items_x: Path | None = None, items_v7: Path | None = None, limit: int = 0) -> list[dict[str, Any]]:
    """The S1 item list in capture order: items_w.json families, then mapping-8, then V7. A missing optional file (mapping8 /
    V7) is skipped with a printed note; items_w.json is required when any of its families is requested."""
    out: list[dict[str, Any]] = []
    want_w = [f for f in families if f not in ("mapping8", "v7")]
    if want_w:
        items = W.load_items_w(items_w)
        for it in items:
            if it["family"] in want_w:
                out.append(it)
    if "mapping8" in families:
        try:
            m8, _ = W.load_mapping8(mapping8_index, items_x)
            out += m8
        except FileNotFoundError as exc:
            print(f"[w/s1] note: {exc}; mapping8 skipped", flush=True)
    if "v7" in families:
        try:
            out += W.load_v7(items_v7)
        except FileNotFoundError as exc:
            print(f"[w/s1] note: {exc}; V7 skipped", flush=True)
    if limit:
        per: dict[str, int] = {}
        kept = []
        for it in out:
            per[it["family"]] = per.get(it["family"], 0) + 1
            if per[it["family"]] <= limit:
                kept.append(it)
        out = kept
    ids = [it["item_id"] for it in out]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate item ids across the S1 families")
    return out


def cap_tokens(family: str) -> int:
    return W.S1_CAP_TOKENS.get(family, W.S1_DEFAULT_TOKENS)


# ------------------------------------------------------------------ one item
def capture_item(target: M.Target, item: dict[str, Any], layers: tuple[int, ...] | None = None, *, state_layers: tuple[int, ...] | None = None,
                 max_new_tokens: int | None = None) -> dict[str, Any]:
    """One prefill+generate: full captures at ``layers`` (fp32 ``{L: [T, d]}``), greedy answer, first-token log-probs of the pair and
    of every candidates_all entry."""
    import torch

    layers = tuple(layers or W.S1_LAYERS)
    state_layers = tuple(state_layers or W.STATE_LAYERS)
    render = W.item_render(item)
    ids = W.render_ids(target.tokenizer, item)
    cands = W.candidates_all(item)
    cand_a, cand_b = W.pair_candidates(item)
    ft_pair = W.pair_first_tokens(target.tokenizer, cand_a, cand_b, render)
    table = W.first_token_table(target.tokenizer, cands, render)
    tok_ids = [None if ft_pair["unscorable"] else ft_pair["first_A"], None if ft_pair["unscorable"] else ft_pair["first_B"]] + list(table["ids"])
    read = sorted(set(layers) | set(state_layers))
    rows = W.prefill_generate(target, ids, read_layers=read, read_all_positions=True, max_new_tokens=max_new_tokens or cap_tokens(item["family"]),
                              first_token_ids=tok_ids)
    r = rows[0]
    acts = {L: r["read_all"][L] for L in read}
    parsed, evidence = W.parse_answer(r["answer_text"], item)
    lp = r["lp_first"]
    vec = lp[2:]
    out = {"ids": ids, "n_tokens": len(ids), "render": render, "acts": acts, "answer_text": r["answer_text"], "new_ids": r["new_ids"],
           "n_new_tokens": r["n_new_tokens"], "finish_reason": r["finish_reason"], "parsed": parsed, "parse_evidence": evidence,
           "cand_A": cand_a, "cand_B": cand_b, "lo_model": W.lo_from_lp(lp[:2]), "lp_first_A": lp[0], "lp_first_B": lp[1],
           "lo_model_unscorable": bool(ft_pair["unscorable"]), "lo_model_form": ft_pair.get("form"), "first_A": ft_pair.get("first_A"), "first_B": ft_pair.get("first_B"),
           "candidates_all": cands, "cand_first_tokens": table["ids"], "cand_first_forms": [table["tokens"][c]["form"] for c in cands],
           "cand_first_token_duplicates": table["duplicates"], "lp_candidates_all": vec, "top1_id": r["top1_id"], "top1_lp": r["top1_lp"],
           "argmax_candidate": (cands[max(range(len(cands)), key=lambda i: (vec[i] if vec[i] is not None else -1e30))] if cands and any(v is not None for v in vec) else None),
           "wall_s": r["wall_s_batch"], "peak_mem_gb": r["peak_mem_gb"], "prompt_ids_sha256": C.sha256_ids(ids)}
    out["correct"] = (parsed is not None and str(parsed) == str(item["primary"]["answer"]))
    return out


def cap_path(item_id: str, caps_dir: Path | None = None) -> Path:
    return (caps_dir or W.S1_CAPS_DIR) / f"{item_id}.pt"


def load_cap(item_id: str, caps_dir: Path | None = None) -> dict[str, Any]:
    import torch

    d = torch.load(cap_path(item_id, caps_dir), map_location="cpu", weights_only=False)
    if d["acts"].ndim != 3 or d["acts"].shape[0] != len(d["layers"]):
        raise ValueError(f"{item_id}: malformed S1 capture {tuple(d['acts'].shape)}")
    return d


def cap_vector(cap: dict[str, Any], layer: int, position: int = -1) -> Any:
    """fp32 ``[d]`` at (layer, position) of an S1 capture."""
    return cap["acts"][list(cap["layers"]).index(int(layer)), int(position) % int(cap["n_tokens"])].float()


def state_meta_row(item: dict[str, Any], layer: int, ids: list[int], h: Any, target: M.Target) -> dict[str, Any]:
    """A core.states-style meta row (``role`` 'w_state')."""
    return {"item_id": item["item_id"], "model_id": target.model_id, "model_sha": target.revision, "model_class": target.model_class, "layer": int(layer),
            "hook": C.HOOK, "hidden_states_index": int(layer) + 1, "pos": len(ids) - 1, "n_tokens": len(ids), "read_token": M.token_str(target.tokenizer, ids[-1]),
            "prompt_ids_sha256": C.sha256_ids(ids), "render": W.item_render(item), "system": item.get("system"), "enable_thinking": C.ENABLE_THINKING,
            "dtype_capture": C.CAPTURE_DTYPE, "dtype_saved": C.SAVE_DTYPE, "norm": round(float(h.norm()), 4), "captured_at": now_iso(), "pre_answer": True,
            "role": "w_state", "family": item["family"]}


# ------------------------------------------------------------------ collection
def collect(target: M.Target, items: list[dict[str, Any]], *, layers: tuple[int, ...] | None = None, caps_dir: Path | None = None, target_path: Path | None = None,
            states_root: Path | None = None, state_layers: tuple[int, ...] | None = None, ledger_path: Path | None = None, log_path: Path | None = None,
            max_new_tokens: int | None = None, progress_status: bool = False) -> int:
    """Capture every item not yet in s1_target.jsonl (with its .pt present); resumable by item_id. Returns the number of new items."""
    import torch

    layers = tuple(layers or W.S1_LAYERS)
    state_layers = tuple(state_layers or W.STATE_LAYERS)
    caps_dir = caps_dir or W.S1_CAPS_DIR
    target_path = target_path or W.S1_TARGET
    states_root = states_root or W.W_CACHE
    caps_dir.mkdir(parents=True, exist_ok=True)
    for L in state_layers:
        (states_root / f"states_L{L}").mkdir(parents=True, exist_ok=True)
    done = {k for k in done_ids(target_path, key="key") if cap_path(k, caps_dir).exists()}
    ledgers: dict[str, Any] = {}
    extra = W.row_extra()
    n = 0
    total = len(items)
    n_done0 = sum(1 for it in items if it["item_id"] in done)
    from . import status as ST

    for it in items:
        iid = it["item_id"]
        if iid in done:
            continue
        with timed_call() as st:
            r = capture_item(target, it, layers, state_layers=state_layers, max_new_tokens=max_new_tokens)
        T = r["n_tokens"]
        acts = torch.stack([r["acts"][L] for L in layers]).to(torch.bfloat16)  # [n_layers, T, d]
        torch.save({"item_id": iid, "family": it["family"], "pair_id": it.get("pair_id"), "version": it.get("version"), "layers": list(layers), "ids": list(r["ids"]),
                    "n_tokens": T, "render": r["render"], "prompt_ids_sha256": r["prompt_ids_sha256"], "hook": C.HOOK, "dtype": "bfloat16", "model_id": target.model_id,
                    "model_sha": target.revision, "system": it.get("system"), "captured_at": now_iso(), "acts": acts}, cap_path(iid, caps_dir))
        for L in state_layers:
            h = r["acts"][L][T - 1].float().contiguous()
            torch.save(h, states_root / f"states_L{L}" / f"{iid}.pt")
            append_jsonl(states_root / f"states_L{L}_meta.jsonl", state_meta_row(it, L, r["ids"], h, target))
        row = {"key": iid, "item_id": iid, "family": it["family"], "pair_id": it.get("pair_id"), "version": it.get("version"), "render": r["render"],
               "n_tokens": T, "layers": list(layers), "answer_text": r["answer_text"], "n_new_tokens": r["n_new_tokens"], "finish_reason": r["finish_reason"],
               "parsed": r["parsed"], "parse_evidence": r["parse_evidence"], "true_answer": str(it["primary"]["answer"]), "correct": r["correct"],
               "cand_A": r["cand_A"], "cand_B": r["cand_B"], "lo_model": r["lo_model"], "lp_first_A": r["lp_first_A"], "lp_first_B": r["lp_first_B"],
               "lo_model_unscorable": r["lo_model_unscorable"], "lo_model_form": r["lo_model_form"], "first_A": r["first_A"], "first_B": r["first_B"],
               "candidates_all": r["candidates_all"], "cand_first_tokens": r["cand_first_tokens"], "cand_first_forms": r["cand_first_forms"],
               "cand_first_token_duplicates": r["cand_first_token_duplicates"], "lp_candidates_all": r["lp_candidates_all"], "argmax_candidate": r["argmax_candidate"],
               "top1_id": r["top1_id"], "top1_lp": r["top1_lp"], "max_new_tokens": max_new_tokens or cap_tokens(it["family"]), "state_layers": list(state_layers),
               "norm_L42": round(float(r["acts"][42][T - 1].norm()), 3) if 42 in r["acts"] else None, "prompt_ids_sha256": r["prompt_ids_sha256"],
               "system": it.get("system"), "wall_s": st.wall_s, "peak_mem_gb": st.peak_mem_gb, **extra}
        append_jsonl(target_path, row)
        ld = ledgers.setdefault(it["family"], W.ledger(f"s1_capture_{it['family']}", {"layers": list(layers), "max_new_tokens": row["max_new_tokens"]}))
        ld.add(T, r["n_new_tokens"], st.wall_s, st.peak_mem_gb)
        n += 1
        if n % 25 == 0 or n <= 3:
            print(f"[w/s1] {n}: {iid} ({it['family']}, {T} tok) -> {r['answer_text']!r} parsed={r['parsed']} correct={r['correct']}", flush=True)
        if progress_status:
            ST.progress("S1 capture", n_done0 + n, total, every=25)
    for ld in ledgers.values():
        rr = ld.flush(ledger_path)
        if rr:
            W.wlog(f"s1 {ld.step}: {rr}", log_path)
    return n


def counts_filter(rows: list[dict[str, Any]], out_path: Path | None = None, min_correct: float = COUNTS_MIN_CORRECT) -> dict[str, Any]:
    c = [r for r in rows if r.get("family") == "counts"]
    kept = sorted(r["item_id"] for r in c if r.get("correct"))
    rate = len(kept) / len(c) if c else None
    rep = {"written": now_iso(), "n_counts": len(c), "n_kept": len(kept), "rate_correct": rate, "min_correct": min_correct,
           "passes": (rate is not None and rate >= min_correct), "kept": kept,
           "by_value": {}, "dropped": sorted(r["item_id"] for r in c if not r.get("correct"))}
    for r in c:
        rep["by_value"].setdefault(str(r.get("true_answer")), {"n": 0, "k": 0})
        rep["by_value"][str(r.get("true_answer"))]["n"] += 1
        rep["by_value"][str(r.get("true_answer"))]["k"] += int(bool(r.get("correct")))
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(rep, indent=1) + "\n")
    return rep


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for r in rows:
        f = out.setdefault(r["family"], {"n": 0, "correct": 0, "lo_scorable": 0})
        f["n"] += 1
        f["correct"] += int(bool(r.get("correct")))
        f["lo_scorable"] += int(not r.get("lo_model_unscorable"))
    return out


# ------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A"], default="A")
    ap.add_argument("--families", default=",".join(S1_FAMILIES))
    ap.add_argument("--limit", type=int, default=0, help="debug: first N items per family")
    ap.add_argument("--layers", default=",".join(map(str, W.S1_LAYERS)))
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    fams = tuple(f.strip() for f in a.families.split(",") if f.strip())
    layers = tuple(int(x) for x in a.layers.split(",") if x.strip())
    if W.refuse_if_done(STAGE, a.force):
        return 0
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    items = s1_items(fams, limit=a.limit)
    fam_n = {f: sum(1 for it in items if it["family"] == f) for f in fams}
    print(f"[w/s1] {len(items)} items {fam_n}; layers {layers}; planned forwards+greedy decodes = {len(items)}", flush=True)
    W.wlog(f"s1 start: {len(items)} items {fam_n}; layers {layers}")
    W.W_CACHE.mkdir(parents=True, exist_ok=True)
    target = load_target_timed(W.MODULE)
    n = collect(target, items, layers=layers, progress_status=True)
    rows = read_jsonl(W.S1_TARGET)
    rep = counts_filter(rows, W.stage_dir(STAGE) / "counts_kept.json")
    s = summary(rows)
    (W.stage_dir(STAGE) / "summary.json").write_text(json.dumps({"written": now_iso(), "families": s, "counts_filter": {k: v for k, v in rep.items() if k not in ("kept", "dropped", "by_value")}}, indent=1))
    W.wlog(f"s1 done: {n} new items; summary {s}; counts kept {rep['n_kept']}/{rep['n_counts']} (passes {rep['passes']})")
    if rep["n_counts"] and not rep["passes"]:
        print(f"[w/s1] WARNING: counts correctness {rep['rate_correct']:.3f} < {COUNTS_MIN_CORRECT} (pre-registered requirement); kept {rep['n_kept']}", flush=True)
    W.mark_done(STAGE, info={"n_items": len(rows), "families": s})
    M.unload(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
