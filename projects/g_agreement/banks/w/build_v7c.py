"""V7 confirmatory bank (items_v7c.json): 48 target-private ownership pairs x 2 preamble roles = 192 items.

Design: projects/g_agreement/banks/w/items_v7_confirmatory_design.md (written by v67_analysis/v7.py when the 16-pair pilot was
positive, 2026-10-12). Factors, fully crossed: 8 name sets x 3 object pairs x 2 mention orders = 48 pairs; preamble template p0/p1
alternates (24/24, balanced within every name set and object pair); every pair exists in both preamble roles (system turn, as in the
pilot; user turn = preamble prepended to the user turn), as separate pair records sharing a ``base_pair``. Visible prompt identical
within a pair. Names: 16 single-token first names (bare and space-prefixed, Qwen2.5/Qwen3 tokenizer family) disjoint from the pilot's
30; objects: 3 new colour+noun pairs disjoint from the pilot's 16 objects. Generation only, deterministic (seed 20261013).

    python -m projects.g_agreement.banks.w.build_v7c [--seed 20261013] [--out projects/g_agreement/banks/w/items_v7c.json] [--print]
"""
from __future__ import annotations
import argparse, collections, datetime as _dt, json, os, random, sys
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
if REPO not in sys.path:
    sys.path.insert(0, REPO)
from projects.g_agreement.banks.w import build_w_bank as BW  # noqa: E402
from projects.g_agreement.dataset import build_dataset as bd  # noqa: E402
from projects.g_agreement import core  # noqa: E402,F401
from projects.g_agreement.core import config as C  # noqa: E402

SEED = 20261013
OUT = os.path.join(HERE, "items_v7c.json")
PREFIX = "wv7c"
NAME_SETS: List[Tuple[str, str]] = [("Anna", "Mary"), ("Mark", "John"), ("Laura", "Alice"), ("Peter", "David"),
                                    ("Lisa", "Amy"), ("Jack", "Leon"), ("Ada", "Tim"), ("Max", "Carl")]
OBJECT_PAIRS: List[Tuple[str, str]] = [("red kite", "blue drum"), ("white mug", "green sock"), ("black comb", "orange vase")]
ROLES = ("system", "user")
PILOT_NAMES = set(BW.V7_NAMES)
PILOT_OBJECTS = {o for p in BW.build_v7(random.Random(0))[1]["object_pairs"] for o in p}


def build(seed: int = SEED) -> Tuple[List[dict], Dict[str, Any]]:
    rng = random.Random(seed)
    for a, b in NAME_SETS:
        assert a not in PILOT_NAMES and b not in PILOT_NAMES, (a, b)
    for o1, o2 in OBJECT_PAIRS:
        assert o1 not in PILOT_OBJECTS and o2 not in PILOT_OBJECTS and o1.split()[0] != o2.split()[0] and o1.split()[1] != o2.split()[1]
    cells = [(ni, oi, order) for ni in range(len(NAME_SETS)) for oi in range(len(OBJECT_PAIRS)) for order in ("first", "second")]
    assert len(cells) == 48
    # template p0/p1: alternate within each (name set, object pair) block of two (the two orders), with the phase chosen per block by seed
    tmpl_of: Dict[Tuple[int, int, str], str] = {}
    for ni in range(len(NAME_SETS)):
        for oi in range(len(OBJECT_PAIRS)):
            flip = rng.random() < 0.5
            tmpl_of[(ni, oi, "first")] = "p0" if not flip else "p1"
            tmpl_of[(ni, oi, "second")] = "p1" if not flip else "p0"
    # swap the name roles (which name answers version A) per cell, seeded, so the A-answer is not always the set's first name
    a_first = {c: rng.random() < 0.5 for c in cells}
    items: List[dict] = []
    for k, (ni, oi, order) in enumerate(cells):
        base = f"{PREFIX}-{k + 1:02d}"
        n1, n2 = NAME_SETS[ni] if a_first[(ni, oi, order)] else NAME_SETS[ni][::-1]
        asked, other = OBJECT_PAIRS[oi]
        tmpl = BW.V7_PREAMBLES[0 if tmpl_of[(ni, oi, order)] == "p0" else 1]
        cands = [n1, n2]
        visible = BW.V7_VISIBLE.format(o=asked)
        question = f"Who has the {asked}?"
        for role in ROLES:
            pair_id = f"{base}{role[0]}"
            for version, ans in zip("AB", cands):
                oth = cands[1 - cands.index(ans)]
                binding = {ans: asked, oth: other}
                first, second = (ans, oth) if order == "first" else (oth, ans)
                preamble = tmpl["text"].format(N1=first, o1=binding[first], N2=second, o2=binding[second])
                primary = {"name": f"{asked.replace(' ', '_')}_owner", "question": question, "candidates": list(cands), "answer": ans, "answer_aliases": [ans.lower()]}
                secondary = {"entities": list(cands), "objects": [asked, other], "relation": {"type": "has", "subject": ans, "object": asked}}
                construction = {"preamble_template": tmpl["level"], "first_mentioned_in_preamble": first, "binding": binding, "asked_object": asked,
                                "other_object": other, "names": list(cands), "object_pair": [asked, other], "answer_is_first_mentioned": first == ans,
                                "first_mentioned_candidate": first, "answer_position": cands.index(ans), "cue_position": "n/a", "other_candidate": oth,
                                "visible_mentions_candidates": False, "name_set": ni, "object_pair_index": oi, "mention_order": order, "role": role,
                                "base_pair": base}
                it = bd._item(f"{pair_id}{version}", pair_id, version, "ownership", BW.SPLIT, tmpl["id"], visible, primary, secondary, bd._word_regex(ans),
                              construction, notes=f"V7 confirmatory: binding only in the preamble (role = {role}); visible prompt identical within the pair")
                it["preamble"], it["preamble_role"], it["role"], it["base_pair"], it["mention_order"] = preamble, role, role, base, order
                it["capture_messages"] = ([{"role": "system", "content": preamble}, {"role": "user", "content": visible}] if role == "system"
                                          else [{"role": "user", "content": f"{preamble}\n\n{visible}"}])
                it["prompt_only_text"] = C.PROMPT_ONLY_TEMPLATE.format(prompt_text=visible, question=question)
                items.append(it)
    return items, {"name_sets": [list(s) for s in NAME_SETS], "object_pairs": [list(o) for o in OBJECT_PAIRS], "roles": list(ROLES),
                   "preambles": BW.V7_PREAMBLES, "visible_template": BW.V7_VISIBLE, "seed": seed}


def validate(items: List[dict]) -> Dict[str, Any]:
    assert len(items) == 192
    by_pair: Dict[str, List[dict]] = collections.defaultdict(list)
    for it in items:
        assert bd.REQUIRED_KEYS <= set(it) and it["family"] == "ownership" and it["render"] == "chat" and it["system"] is None
        for n in it["primary"]["candidates"]:
            assert n not in it["prompt_text"] and n in it["preamble"]
        assert BW.solve_v7(it) == it["primary"]["answer"], it["item_id"]
        assert bd.solve_prompt({**it, "family": "ownership"}) is None
        assert it["primary"]["candidates"].index(it["primary"]["answer"]) == ("A", "B").index(it["version"])
        assert (it["construction"]["first_mentioned_in_preamble"] == it["primary"]["answer"]) == (it["mention_order"] == "first")
        by_pair[it["pair_id"]].append(it)
    assert len(by_pair) == 96
    for pid, pair in by_pair.items():
        a, b = sorted(pair, key=lambda x: x["version"])
        assert a["prompt_text"] == b["prompt_text"] and a["prompt_only_text"] == b["prompt_only_text"]
        assert a["preamble"] != b["preamble"] and sorted(a["preamble"].split()) == sorted(b["preamble"].split()), pid
        assert a["primary"]["candidates"] == b["primary"]["candidates"] and a["primary"]["answer"] != b["primary"]["answer"]
        assert a["template_id"] == b["template_id"] and a["role"] == b["role"] and a["mention_order"] == b["mention_order"]
    A = [p[0] if p[0]["version"] == "A" else p[1] for p in by_pair.values()]
    sysA = [it for it in A if it["role"] == "system"]
    usrA = [it for it in A if it["role"] == "user"]
    assert len(sysA) == len(usrA) == 48
    assert {it["base_pair"] for it in sysA} == {it["base_pair"] for it in usrA}
    for s in sysA:  # the user-role twin has the same preamble text and answer
        u = next(x for x in usrA if x["base_pair"] == s["base_pair"])
        assert u["preamble"] == s["preamble"] and u["primary"] == s["primary"]
    tm = collections.Counter(it["template_id"] for it in sysA)
    assert set(tm.values()) == {24}, tm
    for key in ("name_set", "object_pair_index"):
        for v in {it["construction"][key] for it in sysA}:
            sub = [it for it in sysA if it["construction"][key] == v]
            c = collections.Counter(it["template_id"] for it in sub)
            assert len(set(c.values())) == 1, (key, v, c)
    mo = collections.Counter(it["mention_order"] for it in sysA)
    assert mo == {"first": 24, "second": 24}, mo
    return {"n_pairs_per_role": 48, "n_items": len(items), "templates_system_role": dict(tm), "mention_order": dict(mo),
            "a_answer_first_name_of_set": sum(it["primary"]["answer"] == NAME_SETS[it["construction"]["name_set"]][0] for it in sysA)}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--print", action="store_true")
    a = ap.parse_args(argv)
    items, design = build(a.seed)
    rep = validate(items)
    meta = {"created": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"), "phase": "W", "track": "A", "module": "v7c", "seed": a.seed,
            "n_items": len(items), "n_pairs": 96, "n_base_pairs": 48, "sha256_items": bd.sha256_items(items), "frozen": True, "family": "ownership",
            "split": BW.SPLIT, "id_prefix": PREFIX, "design": design, "balance_checks": rep,
            "design_file": "items_v7_confirmatory_design.md", "prompt_only_template_sha256": C.sha256_bytes(C.PROMPT_ONLY_TEMPLATE.encode()),
            "notes": "pair_id = <base><s|u> (s = preamble as the system turn, target-private; u = preamble prepended to the user turn, control for the role); "
                     "prompt_text = the visible prompt only (identical within a pair); the pod loader prepends the preamble for role u"}
    if os.path.exists(a.out):
        old = json.load(open(a.out, encoding="utf-8"))
        if old.get("meta", {}).get("sha256_items") != meta["sha256_items"]:
            raise SystemExit(f"{a.out} exists with a different sha256 ({old.get('meta', {}).get('sha256_items')}); refusing to overwrite a frozen bank")
        print(f"{a.out} unchanged (sha {meta['sha256_items'][:16]})")
    else:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump({"meta": meta, "items": items}, f, indent=1, ensure_ascii=False)
        print(f"wrote {a.out}: {len(items)} items, sha256 {meta['sha256_items']}")
    if a.print:
        for it in items[:4]:
            print(f"{it['item_id']:14} ans={it['primary']['answer']:8} [{it['role']}] {it['preamble']}  ||  {it['prompt_text']}")
        print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
