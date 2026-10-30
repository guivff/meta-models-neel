"""Synthetic fixtures with the exact pod schemas (s3_score.py V6 rows, S1/S1@L38 V7 rows, s1_capture.py target rows, items_v7.json) so the V6 / V7
analyses can be built and tested before the real files reach the Mac. Effects are controllable per condition / reader.

    PYTHONPATH=. .venv/bin/python -m projects.g_agreement.v67_analysis.fixtures --out /tmp/v67_fixture [--seed 0]

writes v6_lo.jsonl, s3_lo.jsonl, s1_target.jsonl, items_v7.json under --out (never under cache/ or results/)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

V6_CONDITIONS = ("a_last", "b_span", "c_full", "d_span_shuffled")
# per condition: (mean, sd) of lo_own on a NATURAL state (positive = the reader separates); p(follow) of an edited state
V6_DEFAULT_EFFECT = {"a_last": (0.3, 1.0), "b_span": (1.6, 1.0), "c_full": (0.9, 1.0), "d_span_shuffled": (0.6, 1.0)}
V6_DEFAULT_FOLLOW = {"a_last": 0.55, "b_span": 0.95, "c_full": 0.8, "d_span_shuffled": 0.7}
V7_DEFAULT_WIN = {("jlens", 42): 0.5, ("jlens", 38): 0.55, ("olens", 42): 0.9, ("olens", 38): 0.75, ("skip_a", 42): 0.5, ("probe", 42): 0.85, ("probe", 38): 0.95}
NAMES = [("Ivan", "Paul"), ("Omar", "Nora"), ("Mira", "Leo"), ("Tom", "Ana"), ("Lena", "Nina"), ("Sara", "Zara"), ("Hugo", "Emma"), ("Noah", "Lily"),
         ("Adam", "Rosa"), ("Finn", "Eva"), ("Luca", "Iris"), ("Maya", "Erik"), ("Tara", "Ben"), ("Alma", "Kai"), ("Vera", "Theo"), ("Nick", "Jo")]
OBJECTS = [("yellow box", "gold coin"), ("purple book", "green bottle"), ("black bag", "green hat"), ("grey ball", "red key"), ("blue cup", "orange lamp"),
           ("brown coat", "red flag"), ("pink scarf", "white pen"), ("blue rope", "silver ring")]


# ------------------------------------------------------------------ V6
def v6_rows(n_pairs: int = 32, n_edited: int = 32, effect: Mapping[str, tuple] = V6_DEFAULT_EFFECT, follow: Mapping[str, float] = V6_DEFAULT_FOLLOW, seed: int = 0,
            layer: int = 38) -> List[dict]:
    """One row per condition × state: 2·n_pairs natural states (pair xown-NNNN, sources A/B) and the first n_edited S2 full-swap α 1 states."""
    rng = np.random.default_rng(seed)
    rows = []
    states = [(f"xown-{i:04d}", src) for i in range(1, n_pairs + 1) for src in "AB"]
    spans = {s: sorted(rng.choice(np.arange(10, 30), size=6, replace=False).tolist()) for s in states}
    T = {s: 34 for s in states}
    nat_lo: Dict[tuple, float] = {}
    for cond in V6_CONDITIONS:
        mu, sd = effect[cond]
        for pid, src in states:
            lo = float(rng.normal(mu, sd))
            nat_lo[(cond, pid, src)] = lo
            rows.append(_v6_row(cond, pid, src, f"{pid}|{src}|natural", "natural", None, lo, spans[(pid, src)], T[(pid, src)], layer))
    for cond in V6_CONDITIONS:
        for pid, src in states[:n_edited]:
            key = f"{pid}|{src}|W2|full|1.0|None"
            lo_nat = nat_lo[(cond, pid, src)]
            follows = rng.random() < follow[cond]
            lo = float(-abs(rng.normal(1.5, 0.7))) if follows else float(abs(rng.normal(0.5, 0.5)))
            rows.append(_v6_row(cond, pid, src, key, "edited_full_a1", key, lo, spans[(pid, src)], T[(pid, src)], layer))
    return rows


def _v6_row(cond: str, pid: str, src: str, state_key: str, kind: str, s2_key: Optional[str], lo: float, span: List[int], T: int, layer: int) -> dict:
    cand_a, cand_b = ("Ann", "Bob") if src == "A" else ("Bob", "Ann")
    n_markers = 1 if cond == "a_last" else (T if cond == "c_full" else len(span))
    lp_b = -3.0
    return {"key": f"olens|V6|{cond}|{state_key}", "reader": "olens", "unit": "V6", "condition": cond, "state_kind": kind, "state_key": state_key, "s2_key": s2_key, "pair_id": pid, "source": src,
            "state_item_id": f"{pid}{src}", "family": "ownership", "layer": layer, "n_markers": n_markers, "span": (None if cond == "c_full" else list(span)), "n_tokens": T,
            "cand_A": cand_a, "cand_B": cand_b, "lo_own": lo, "lo_toward_other": -lo, "lp_A": lp_b + lo, "lp_B": lp_b, "marker_char": "一", "templates": ["- {X}"], "unscorable": False,
            "wall_s_chunk": 0.1, "chunk_size": 8, "model_id": "fixture", "model_sha": "fixture"}


# ------------------------------------------------------------------ V7
def v7_items(n_pairs: int = 16) -> dict:
    items = []
    for i in range(n_pairs):
        pid = f"wv7-{i + 1:02d}"
        n1, n2 = NAMES[i % len(NAMES)]
        o1, o2 = OBJECTS[i % len(OBJECTS)]
        tmpl = "p0" if i % 2 == 0 else "p1"
        first_is_answer = (i // 2) % 2 == 0
        prompt = f"Who has the {o1}? Answer with the name only."
        for v in "AB":
            ans, other = (n1, n2) if v == "A" else (n2, n1)
            first = n1 if first_is_answer == (v == "A") else n2
            binding = {ans: o1, other: o2}
            second = n2 if first == n1 else n1
            pre = (f"Background: {first} has the {binding[first]} and {second} has the {binding[second]}." if tmpl == "p0" else
                   f"Context for this conversation: {first} has the {binding[first]}. {second} has the {binding[second]}.")
            items.append({"item_id": f"{pid}{v}", "pair_id": pid, "version": v, "family": "ownership", "split": "test", "template_id": f"v7-{tmpl}", "prompt_text": prompt, "render": "chat",
                          "system": None, "primary": {"name": f"{o1.replace(' ', '_')}_owner", "question": f"Who has the {o1}?", "candidates": [n1, n2], "answer": ans, "answer_aliases": [ans.lower()]},
                          "construction": {"preamble_template": tmpl, "first_mentioned_in_preamble": first, "binding": binding, "asked_object": o1, "other_object": o2, "names": [n1, n2],
                                           "object_pair": [o1, o2], "answer_is_first_mentioned": first == ans, "other_candidate": other, "visible_mentions_candidates": False},
                          "preamble": pre, "preamble_role": "system", "capture_messages": [{"role": "system", "content": pre}, {"role": "user", "content": prompt}],
                          "prompt_only_text": f"You will read a short passage and answer one question about it.\n\nPassage:\n{prompt}\n\nQuestion: Who has the {o1}?\nAnswer in a few words, then stop."})
    return {"meta": {"phase": "W", "module": "v7", "n_pairs": n_pairs, "n_items": 2 * n_pairs, "family": "ownership", "frozen": False, "fixture": True}, "items": items}


def v7_lo_rows(items: Sequence[dict], win: Mapping[tuple, float] = V7_DEFAULT_WIN, seed: int = 0, unscorable: Mapping[tuple, Sequence[str]] = {}) -> List[dict]:
    """S3 rows for family v7: per (reader, layer) the pair wins with probability win[(reader, layer)]; unit 'S1' at 42, 'S1@L38' at 38."""
    rng = np.random.default_rng(seed)
    by_pair: Dict[str, Dict[str, dict]] = {}
    for it in items:
        by_pair.setdefault(it["pair_id"], {})[it["version"]] = it
    rows = []
    for (reader, layer), pw in win.items():
        unit = "S1" if layer == 42 else f"S1@L{layer}"
        for pid, d in sorted(by_pair.items()):
            w = rng.random() < pw
            s = float(abs(rng.normal(1.2, 0.5)))
            noise = float(rng.normal(0, 0.3))
            los = {"A": (s if w else -s) + noise, "B": noise * 0.5}  # lo_A + lo_B = ±s + 1.5·noise, sign set by w
            if (w and los["A"] + los["B"] <= 0) or (not w and los["A"] + los["B"] > 0):
                los["B"] = -los["A"] + (0.2 if w else -0.2)
            for v in "AB":
                it = d[v]
                own, other = it["primary"]["answer"], it["construction"]["other_candidate"]
                lo = None if it["item_id"] in unscorable.get((reader, layer), ()) else los[v]
                rows.append({"key": f"{reader}|{unit}|{it['item_id']}", "entry_key": it["item_id"], "reader": reader, "unit": unit, "layer": layer, "family": "v7", "item_id": it["item_id"], "pair_id": pid,
                             "version": v, "cand_A": own, "cand_B": other, "true_answer": own, "actual_answer": own, "correct": True, "candidates": [own, other], "scores": None, "argmax": None,
                             "score": lo, "lo_own": lo, "lo_toward_other": (None if lo is None else -lo), "lp_A": None, "lp_B": None, "templates": ["- {X}"], "unscorable": lo is None,
                             "format": "bullet", "n_unscorable": None, "lo_model": -1.0, "lp_candidates_all_model": None, "wall_s_chunk": 0.1, "chunk_size": 8, "model_id": "fixture"})
    return rows


def s1_target_rows(items: Sequence[dict], accuracy: float = 1.0, seed: int = 0) -> List[dict]:
    """s1_capture.py rows for family v7: greedy answer with the preamble; lo_model = lp(other) − lp(own) (negative = toward own)."""
    rng = np.random.default_rng(seed)
    rows = []
    for it in items:
        own, other = it["primary"]["answer"], it["construction"]["other_candidate"]
        ok = rng.random() < accuracy
        lp_a, lp_b = (-0.1, -3.0) if ok else (-2.5, -0.2)
        rows.append({"key": it["item_id"], "item_id": it["item_id"], "family": "v7", "pair_id": it["pair_id"], "version": it["version"], "render": "chat", "n_tokens": 40, "layers": [20, 28, 38, 42, 48, 52],
                     "answer_text": own if ok else other, "n_new_tokens": 2, "finish_reason": "eos", "parsed": own if ok else other, "parse_evidence": "regex", "true_answer": own, "correct": ok,
                     "cand_A": own, "cand_B": other, "lo_model": lp_b - lp_a, "lp_first_A": lp_a, "lp_first_B": lp_b, "lo_model_unscorable": False, "lo_model_form": "space", "first_A": 1, "first_B": 2,
                     "candidates_all": [own, other], "system": it["preamble"], "model_id": "fixture"})
    return rows


# ------------------------------------------------------------------ writing
def write_jsonl(path: Path, rows: Sequence[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return path


def write_fixture(out: Path, seed: int = 0, v6_effect: Mapping[str, tuple] = V6_DEFAULT_EFFECT, v6_follow: Mapping[str, float] = V6_DEFAULT_FOLLOW,
                  v7_win: Mapping[tuple, float] = V7_DEFAULT_WIN, target_accuracy: float = 1.0, with_s1: bool = True) -> Dict[str, Path]:
    out = Path(out)
    items = v7_items()
    paths = {"v6_lo": write_jsonl(out / "v6_lo.jsonl", v6_rows(effect=v6_effect, follow=v6_follow, seed=seed)),
             "s3_lo": write_jsonl(out / "s3_lo.jsonl", v7_lo_rows(items["items"], win=v7_win, seed=seed)),
             "items_v7": out / "items_v7.json"}
    paths["items_v7"].write_text(json.dumps(items, indent=1), encoding="utf-8")
    if with_s1:
        paths["s1_target"] = write_jsonl(out / "s1_target.jsonl", s1_target_rows(items["items"], target_accuracy, seed))
    return paths


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    real = {ROOT / "cache", ROOT / "results"}
    if any(str(a.out.resolve()).startswith(str(r)) for r in real):
        raise SystemExit("fixtures never go under cache/ or results/")
    paths = write_fixture(a.out, a.seed)
    print("\n".join(f"{k}: {p}" for k, p in paths.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
