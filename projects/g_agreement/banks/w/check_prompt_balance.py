#!/usr/bin/env python
"""Phase W Track A: prompt-level balance check of the graded bank, run BEFORE the pod (PREREG_WV.md §Track A: "a
prompt-level balance check runs before the pod"; the activation-based PC1 checks are ``check_w_variance.py`` on the
S1 captures). CPU only, no model calls. Reads items_w.json, items_v7.json and mapping8_index.json and writes
results/g_agreement/w/bank_checks.json (the only file this module writes under results/).

Checks (each a named row with pass/fail, the observed counts and the rule):
  counts      every N in 1..99 used 5-7 times; 4 templates x 150; 3 objects x 200; 12 (template, object) cells x 50;
              12 places x 50; per value: each object >= 2 and each template >= 1 (no cell/template is tied to a
              value); value decade x template and decade x object within +-20% of uniform; answer == the one integer
              in the prompt; prompts distinct; candidates_all = "1".."99".
  ownership4  every design factor level balanced (name_set 16, template 32, mention_order 16, holder 16,
              query_direction 32), holder_b_shift 22/21/21, every pair of design factors pairwise balanced, 16
              asked-object uses each, answer mention position 16 per position, A/B token permutations differing
              exactly in the two holders' objects, answers re-derived by the solvers, 4 candidates.
  arith       ops 50/50; every decade 0..9 of a and of b covered; Michael's regex ^\\d{1,2} [+-] \\d{1,2} =$; render
              "plain"; answers >= 0; no triple shared with nla-consistency/data/arithmetic.jsonl; no repeats.
  mapping8    47 pairs / 94 items, all from items_x.json mapping test split (ids and answers agree), candidates_all
              = A..H, source item sha recorded equals items_x.json's.
  v7          16 pairs; visible prompt identical within a pair; preambles token permutations; candidates absent from
              the visible prompt; prompt_only_text = PROMPT_ONLY_TEMPLATE over the visible prompt; templates 8/8;
              answer-first-mentioned 8/8.
  ids         no item id or prompt text shared with items.json, items_x.json, items_g6.json, items_binding_factorial.json.

Usage:
    .venv/bin/python -m projects.g_agreement.banks.w.check_prompt_balance [--bank-dir projects/g_agreement/banks/w]
        [--out results/g_agreement/w/bank_checks.json] [--no-write]
Exit code 1 if any check fails.
"""
from __future__ import annotations

import argparse
import collections
import datetime as _dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from projects.g_agreement.banks.w import build_w_bank as W  # noqa: E402
from projects.g_agreement.core import config as C  # noqa: E402
from projects.g_agreement.dataset import build_dataset as bd  # noqa: E402
from projects.g_agreement.dataset import build_dataset_x as bdx  # noqa: E402

DEFAULT_BANK_DIR = Path(HERE)
DEFAULT_OUT = Path(REPO) / "results" / "g_agreement" / "w" / "bank_checks.json"
OTHER_BANKS = [Path(REPO) / "projects" / "g_agreement" / "dataset" / f for f in ("items.json", "items_x.json", "items_g6.json")] + \
              [Path(REPO) / "projects" / "g_agreement" / "banks" / "binding_factorial" / "items_binding_factorial.json"]
UNIFORM_TOL = 0.20  # decade x template / decade x object cells within +-20% of the uniform expectation


class Checks:
    def __init__(self) -> None:
        self.rows: List[Dict[str, Any]] = []

    def add(self, family: str, name: str, ok: bool, observed: Any, rule: str) -> bool:
        self.rows.append({"family": family, "check": name, "pass": bool(ok), "observed": observed, "rule": rule})
        return bool(ok)


def _uniform_ok(counter: Dict[Any, int], n_cells: int, total: int, tol: float = UNIFORM_TOL) -> bool:
    exp = total / n_cells
    return len(counter) == n_cells and all(abs(v - exp) <= tol * exp for v in counter.values())


# ------------------------------------------------------------------ counts
def check_counts(items: Sequence[dict], ck: Checks) -> None:
    fam = "counts"
    its = [it for it in items if it["family"] == fam]
    ck.add(fam, "n_items", len(its) == W.N_COUNTS, len(its), f"== {W.N_COUNTS}")
    nv = collections.Counter(it["construction"]["value"] for it in its)
    ck.add(fam, "values_1_to_99_used_5_to_7_times", set(nv) == set(W.COUNT_VALUES) and all(5 <= v <= 7 for v in nv.values()),
           {"min_uses": min(nv.values()), "max_uses": max(nv.values()), "n_values": len(nv),
            "uses_histogram": dict(sorted(collections.Counter(nv.values()).items()))}, "every N in 1..99 used 5-7 times")
    tc = collections.Counter(it["construction"]["template"] for it in its)
    oc = collections.Counter(it["construction"]["object"] for it in its)
    pc = collections.Counter(it["construction"]["place"] for it in its)
    cells = collections.Counter((it["construction"]["template"], it["construction"]["object"]) for it in its)
    ck.add(fam, "templates_balanced", set(tc) == set(W.COUNT_FACTORS["template"]) and len(set(tc.values())) == 1, dict(tc), "4 templates x 150")
    ck.add(fam, "objects_balanced", set(oc) == set(W.COUNT_FACTORS["object"]) and len(set(oc.values())) == 1, dict(oc), "3 objects x 200")
    ck.add(fam, "template_x_object_cells", len(cells) == 12 and set(cells.values()) == {W.PER_CELL},
           {f"{t}|{o}": n for (t, o), n in sorted(cells.items())}, f"12 cells x {W.PER_CELL}")
    ck.add(fam, "places_balanced", set(pc) == set(W.COUNT_PLACES) and len(set(pc.values())) == 1, dict(pc), "12 places x 50")
    bad_obj, bad_tmpl = [], []
    for n in W.COUNT_VALUES:
        uses = [it["construction"] for it in its if it["construction"]["value"] == n]
        co = collections.Counter(u["object"] for u in uses)
        ct = collections.Counter(u["template"] for u in uses)
        if not all(co[o] >= 2 for o in W.COUNT_FACTORS["object"]):
            bad_obj.append(n)
        if not all(ct[t] >= 1 for t in W.COUNT_FACTORS["template"]):
            bad_tmpl.append(n)
    ck.add(fam, "per_value_every_object_at_least_twice", not bad_obj, {"violations": bad_obj}, "each N occurs with each object >= 2 times")
    ck.add(fam, "per_value_every_template_at_least_once", not bad_tmpl, {"violations": bad_tmpl}, "each N occurs with each template >= 1 time")
    dt = collections.Counter((it["construction"]["decade"], it["construction"]["template"]) for it in its)
    do = collections.Counter((it["construction"]["decade"], it["construction"]["object"]) for it in its)
    # decade d0 has 9 values (1..9), the others 10: compare each decade's row to its own uniform split
    def _rows_ok(cnt: Dict[tuple, int], levels: Sequence[str]) -> bool:
        ok = True
        for d in W.COUNT_FACTORS["decade"]:
            row = {l: cnt.get((d, l), 0) for l in levels}
            ok &= _uniform_ok(row, len(levels), sum(row.values()))
        return ok
    ck.add(fam, "decade_x_template_near_uniform", _rows_ok(dt, W.COUNT_FACTORS["template"]),
           {f"{d}|{t}": n for (d, t), n in sorted(dt.items())}, f"each decade's template split within +-{int(UNIFORM_TOL * 100)}% of uniform")
    ck.add(fam, "decade_x_object_near_uniform", _rows_ok(do, W.COUNT_FACTORS["object"]),
           {f"{d}|{o}": n for (d, o), n in sorted(do.items())}, f"each decade's object split within +-{int(UNIFORM_TOL * 100)}% of uniform")
    solver = [it["item_id"] for it in its if W.solve_count(it) != it["primary"]["answer"] or it["primary"]["answer"] != str(it["construction"]["value"])]
    ck.add(fam, "answer_equals_integer_in_prompt", not solver, {"violations": solver[:5]}, "answer == the single integer in the prompt == N")
    ck.add(fam, "prompts_distinct", len({it["prompt_text"] for it in its}) == len(its), len({it["prompt_text"] for it in its}), "all prompts distinct")
    ck.add(fam, "candidates_all_is_1_to_99", all(it["primary"]["candidates_all"] == [str(v) for v in W.COUNT_VALUES] and
                                                 it["primary"]["candidates"] == [it["primary"]["answer"]] for it in its), True,
           "candidates == [answer]; candidates_all == '1'..'99'")
    ck.add(fam, "render_chat", all(it["render"] == "chat" and it["system"] is None for it in its), True, "render chat, system null")


# ------------------------------------------------------------------ ownership4
def check_ownership4(items: Sequence[dict], ck: Checks) -> None:
    fam = "ownership4"
    its = [it for it in items if it["family"] == fam]
    by_pair: Dict[str, Dict[str, dict]] = collections.defaultdict(dict)
    for it in its:
        by_pair[it["pair_id"]][it["version"]] = it
    ck.add(fam, "n_pairs_items", len(by_pair) == W.N_PAIRS4 and len(its) == 2 * W.N_PAIRS4 and all(set(p) == {"A", "B"} for p in by_pair.values()),
           {"pairs": len(by_pair), "items": len(its)}, f"{W.N_PAIRS4} pairs, {2 * W.N_PAIRS4} items")
    A = [by_pair[p]["A"] for p in sorted(by_pair)]
    fac = {}
    ok = True
    for f, levels in W.FACTORS4.items():
        cnt = collections.Counter(it["construction"][f] for it in A)
        fac[f] = dict(cnt)
        ok &= set(cnt) == set(levels) and len(set(cnt.values())) == 1
    ck.add(fam, "design_factors_balanced", ok, fac, "every level of every design factor equally often (pairs)")
    off = collections.Counter(it["construction"]["holder_b_shift"] for it in A)
    ck.add(fam, "holder_b_shift_near_balanced", sorted(off.values()) == [21, 21, 22], dict(off), "22/21/21 over 64 pairs")
    fs = list(W.FACTORS4)
    pw_ok, worst = True, {}
    for i in range(len(fs)):
        for j in range(i + 1, len(fs)):
            c2 = collections.Counter((it["construction"][fs[i]], it["construction"][fs[j]]) for it in A)
            full = len(W.FACTORS4[fs[i]]) * len(W.FACTORS4[fs[j]])
            good = len(c2) == full and len(set(c2.values())) == 1
            pw_ok &= good
            if not good:
                worst[f"{fs[i]}x{fs[j]}"] = dict(c2)
    ck.add(fam, "design_factors_pairwise_balanced", pw_ok, worst or "all pairs of factors fully crossed and balanced", "every pair of design factors balanced")
    asked = collections.Counter(it["construction"]["asked_object"] for it in A)
    ck.add(fam, "asked_object_uses", len(asked) == 16 and set(asked.values()) == {4}, dict(asked), "16 objects x 4 asked")
    pos = collections.Counter(it["construction"]["answer_mention_position"] for it in A)
    ck.add(fam, "answer_mention_position_A_balanced", set(pos) == {0, 1, 2, 3} and set(pos.values()) == {16}, {str(k): v for k, v in sorted(pos.items())},
           "A's answer in statement 1..4 equally often")
    perm_bad, swap_bad, solver_bad, cand_bad = [], [], [], []
    for pid, p in by_pair.items():
        a, b = p["A"], p["B"]
        if bdx.word_multiset(a["prompt_text"]) != bdx.word_multiset(b["prompt_text"]) or a["prompt_text"] == b["prompt_text"]:
            perm_bad.append(pid)
        ca, cb = a["construction"], b["construction"]
        diff = {n for n in ca["names"] if ca["binding"][n] != cb["binding"][n]}
        if diff != {ca["holder_name_A"], ca["holder_name_B"]} or any(ca[f] != cb[f] for f in W.FACTORS4):
            swap_bad.append(pid)
        for it in (a, b):
            if W.solve_binding4(it) != it["primary"]["answer"]:
                solver_bad.append(it["item_id"])
            if len(it["primary"]["candidates"]) != 4 or it["primary"]["candidates"].index(it["primary"]["answer"]) != ("A", "B").index(it["version"]):
                cand_bad.append(it["item_id"])
        if a["primary"]["candidates"] != b["primary"]["candidates"]:
            cand_bad.append(pid)
    ck.add(fam, "ab_token_permutation", not perm_bad, {"violations": perm_bad[:5]}, "A/B word multisets equal, texts differ")
    ck.add(fam, "ab_differ_only_in_holders_swap", not swap_bad, {"violations": swap_bad[:5]}, "exactly the two holders exchange objects; all factors shared")
    ck.add(fam, "solver_agreement", not solver_bad, {"violations": solver_bad[:5]}, "answers re-derived from the prompt text")
    ck.add(fam, "four_candidates_convention", not cand_bad, {"violations": cand_bad[:5]}, "4 candidates, same order in A/B, [0] = A's answer, [1] = B's")


# ------------------------------------------------------------------ arith
def check_arith(items: Sequence[dict], ck: Checks) -> None:
    fam = "arith"
    its = [it for it in items if it["family"] == fam]
    ck.add(fam, "n_items", len(its) == W.N_ARITH, len(its), f"== {W.N_ARITH}")
    ops = collections.Counter(it["construction"]["op"] for it in its)
    ck.add(fam, "ops_balanced", ops == {"-": W.N_ARITH // 2, "+": W.N_ARITH // 2}, dict(ops), "50 '-' and 50 '+'")
    fmt_bad = [it["item_id"] for it in its if not W.ARITH_REGEX.fullmatch(it["prompt_text"]) or it["render"] != "plain"]
    ck.add(fam, "michael_format_and_plain_render", not fmt_bad, {"violations": fmt_bad[:5]}, r"^\d{1,2} [+-] \d{1,2} =$ and render 'plain'")
    ad = collections.Counter(it["construction"]["a_decade"] for it in its)
    bd_ = collections.Counter(it["construction"]["b_decade"] for it in its)
    ck.add(fam, "operand_decades_covered", set(ad) == set(range(10)) and set(bd_) == set(range(10)),
           {"a": {str(k): v for k, v in sorted(ad.items())}, "b": {str(k): v for k, v in sorted(bd_.items())}}, "every decade 0..9 of a and of b occurs")
    ans_bad = []
    triples = []
    for it in its:
        c = it["construction"]
        ans = c["a"] - c["b"] if c["op"] == "-" else c["a"] + c["b"]
        if ans < 0 or it["primary"]["answer"] != str(ans) or it["operands"] != {"a": c["a"], "b": c["b"], "op": c["op"]}:
            ans_bad.append(it["item_id"])
        triples.append((c["a"], c["op"], c["b"]))
    ck.add(fam, "answers_nonnegative_and_consistent", not ans_bad, {"violations": ans_bad[:5]}, "answer == a +/- b >= 0; operands field agrees")
    try:
        exclude, sha = W.michael_triples()
        shared = sorted(set(triples) & exclude)
        ck.add(fam, "no_triple_shared_with_michael", not shared and len(set(triples)) == len(triples),
               {"shared": shared[:5], "michael_sha256": sha, "distinct": len(set(triples))}, "no (a, op, b) in nla-consistency/data/arithmetic.jsonl; no repeats")
    except FileNotFoundError:
        ck.add(fam, "no_triple_shared_with_michael", False, "nla-consistency/data/arithmetic.jsonl missing", "file must be present")


# ------------------------------------------------------------------ mapping8 and v7
def check_mapping8(index: Dict[str, Any], ck: Checks) -> None:
    fam = "mapping8"
    rows, pairs = index["items"], index["pairs"]
    ck.add(fam, "n_pairs_items", len(pairs) == 47 and len(rows) == 94, {"pairs": len(pairs), "items": len(rows)}, "47 pairs / 94 items")
    ck.add(fam, "candidates_all_8_symbols", all(r["candidates_all"] == W.SYMBOLS8 and r["answer"] in W.SYMBOLS8 for r in rows), True, "A..H, answer among them")
    src = Path(REPO) / index["meta"]["source"]
    if src.exists():
        dx = json.loads(src.read_text(encoding="utf-8"))
        by_id = {it["item_id"]: it for it in dx["items"] if it["family"] == "mapping" and it["split"] == "test"}
        agree = set(by_id) == {r["item_id"] for r in rows} and all(by_id[r["item_id"]]["primary"]["answer"] == r["answer"] for r in rows)
        ck.add(fam, "matches_items_x", agree and index["meta"]["source_sha256_items"] == dx["meta"]["sha256_items"],
               {"source_sha256_items": dx["meta"]["sha256_items"][:16]}, "ids and answers equal the X mapping test split; sha recorded")
    else:
        ck.add(fam, "matches_items_x", False, f"missing {src}", "items_x.json must exist")


def check_v7(items: Sequence[dict], ck: Checks) -> None:
    fam = "v7"
    by_pair: Dict[str, Dict[str, dict]] = collections.defaultdict(dict)
    for it in items:
        by_pair[it["pair_id"]][it["version"]] = it
    ck.add(fam, "n_pairs", len(by_pair) == W.N_V7 and len(items) == 2 * W.N_V7, {"pairs": len(by_pair), "items": len(items)}, "16 pairs / 32 items")
    vis_bad, pre_bad, leak_bad, po_bad, role_bad = [], [], [], [], []
    for pid, p in by_pair.items():
        a, b = p["A"], p["B"]
        if a["prompt_text"] != b["prompt_text"]:
            vis_bad.append(pid)
        if a["preamble"] == b["preamble"] or bdx.word_multiset(a["preamble"]) != bdx.word_multiset(b["preamble"]):
            pre_bad.append(pid)
        for it in (a, b):
            if any(n in it["prompt_text"] for n in it["primary"]["candidates"]) or bd.solve_prompt({**it, "family": "ownership"}) is not None:
                leak_bad.append(it["item_id"])
            if it["prompt_only_text"] != C.PROMPT_ONLY_TEMPLATE.format(prompt_text=it["prompt_text"], question=it["primary"]["question"]) \
                    or it["preamble"] in it["prompt_only_text"]:
                po_bad.append(it["item_id"])
            if it["preamble_role"] != "system" or it["capture_messages"] != [{"role": "system", "content": it["preamble"]},
                                                                           {"role": "user", "content": it["prompt_text"]}]:
                role_bad.append(it["item_id"])
            if W.solve_v7(it) != it["primary"]["answer"]:
                leak_bad.append(it["item_id"] + ":solver")
    ck.add(fam, "visible_prompt_identical_within_pair", not vis_bad, {"violations": vis_bad}, "prompt_text equal for A and B")
    ck.add(fam, "preambles_token_permutations", not pre_bad, {"violations": pre_bad}, "preambles differ and have equal word multisets")
    ck.add(fam, "no_binding_in_visible_prompt", not leak_bad, {"violations": leak_bad[:5]}, "candidates absent from the visible prompt; preamble+visible solves")
    ck.add(fam, "prompt_only_text_from_visible_only", not po_bad, {"violations": po_bad[:5]}, "PROMPT_ONLY_TEMPLATE over the visible prompt; no preamble")
    ck.add(fam, "preamble_role_system", not role_bad, {"violations": role_bad[:5]}, "preamble_role == 'system'; capture_messages = [system preamble, user visible]")
    A = [by_pair[p]["A"] for p in sorted(by_pair)]
    tm = collections.Counter(it["template_id"] for it in A)
    af = collections.Counter(it["construction"]["answer_is_first_mentioned"] for it in A)
    ck.add(fam, "templates_and_mention_order_balanced", set(tm.values()) == {W.N_V7 // 2} and set(af.values()) == {W.N_V7 // 2},
           {"templates": dict(tm), "answer_first_mentioned_A": {str(k): v for k, v in af.items()}}, "8/8 and 8/8")


def check_ids(items_w: Sequence[dict], items_v7: Sequence[dict], ck: Checks) -> None:
    ids = {it["item_id"] for it in items_w} | {it["item_id"] for it in items_v7}
    prompts = {it["prompt_text"] for it in items_w}  # v7 visible prompts are questions only; compared separately below
    overlaps, checked = {}, []
    for f in OTHER_BANKS:
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        o_items = d["items"] if isinstance(d, dict) and "items" in d else d
        o_ids = {it["item_id"] for it in o_items if isinstance(it, dict) and "item_id" in it}
        o_prompts = {it.get("prompt_text") for it in o_items if isinstance(it, dict)}
        if ids & o_ids or prompts & o_prompts:
            overlaps[f.name] = {"ids": sorted(ids & o_ids)[:5], "prompts": sorted(prompts & o_prompts)[:3]}
        checked.append(f.name)
    ck.add("ids", "no_overlap_with_other_banks", not overlaps and len(checked) >= 2, {"checked": checked, "overlaps": overlaps},
           "no item id / prompt text shared with items.json, items_x.json, items_g6.json, items_binding_factorial.json")
    ck.add("ids", "ids_unique_across_w_and_v7", len(ids) == len(items_w) + len(items_v7), len(ids), "item ids unique")


# ------------------------------------------------------------------ run
def run(bank_dir: Path = DEFAULT_BANK_DIR) -> Dict[str, Any]:
    bank_dir = Path(bank_dir)
    w = json.loads((bank_dir / "items_w.json").read_text(encoding="utf-8"))
    v7 = json.loads((bank_dir / "items_v7.json").read_text(encoding="utf-8"))
    m8 = json.loads((bank_dir / "mapping8_index.json").read_text(encoding="utf-8"))
    ck = Checks()
    for name, d in (("items_w.json", w), ("items_v7.json", v7), ("mapping8_index.json", m8)):
        ck.add("meta", f"{name}_sha256_items_matches", bd.sha256_items(d["items"]) == d["meta"]["sha256_items"],
               {"seed": d["meta"].get("seed"), "sha256_items": d["meta"]["sha256_items"]}, "meta.sha256_items == sha of items")
    check_counts(w["items"], ck)
    check_ownership4(w["items"], ck)
    check_arith(w["items"], ck)
    check_mapping8(m8, ck)
    check_v7(v7["items"], ck)
    check_ids(w["items"], v7["items"], ck)
    fams = {}
    for r in ck.rows:
        fams.setdefault(r["family"], {"n_checks": 0, "n_pass": 0})
        fams[r["family"]]["n_checks"] += 1
        fams[r["family"]]["n_pass"] += int(r["pass"])
    counts = {"counts": sum(it["family"] == "counts" for it in w["items"]), "ownership4": sum(it["family"] == "ownership4" for it in w["items"]),
              "arith": sum(it["family"] == "arith" for it in w["items"]), "mapping8_items_indexed": len(m8["items"]), "v7": len(v7["items"])}
    return {"created": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "bank_dir": os.path.relpath(bank_dir, REPO),
            "seed": w["meta"]["seed"], "sha256": {"items_w": w["meta"]["sha256_items"], "items_v7": v7["meta"]["sha256_items"],
                                                  "mapping8_index": m8["meta"]["sha256_items"]},
            "counts": counts, "all_pass": all(r["pass"] for r in ck.rows), "n_checks": len(ck.rows),
            "n_fail": sum(not r["pass"] for r in ck.rows), "by_family": fams, "checks": ck.rows}


def to_text(rep: Dict[str, Any]) -> str:
    lines = [f"W bank prompt-level checks  seed={rep['seed']}  {'ALL PASS' if rep['all_pass'] else str(rep['n_fail']) + ' FAILED'}  ({rep['n_checks']} checks)",
             f"counts: {rep['counts']}"]
    for r in rep["checks"]:
        lines.append(f"  [{'ok' if r['pass'] else 'FAIL'}] {r['family']:10} {r['check']}" + ("" if r["pass"] else f"  <- {r['observed']}"))
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bank-dir", default=str(DEFAULT_BANK_DIR))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--no-write", action="store_true")
    a = ap.parse_args(argv)
    rep = run(Path(a.bank_dir))
    print(to_text(rep))
    if not a.no_write:
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rep, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {out}")
    return 0 if rep["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
