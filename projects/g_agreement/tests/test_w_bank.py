"""Offline tests for the Phase W Track A graded bank (PREREG_WV.md §Track A): banks/w/build_w_bank.py invariants
(counts, balance, schema, determinism, disk == rebuild), V7 pairs (identical visible prompt, preamble-only binding,
prompt-only text from the visible prompt), arith in Michael Kenney's exact format, mapping-8 index against items_x.json,
id/prompt disjointness from every other bank, check_prompt_balance all-pass, and check_w_variance on synthetic states
(planted factor -> stop; balanced noise -> pass). Nothing is written under results/ or cache/ by the tests (guard on the files this package may write).

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_w_bank.py -q``
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from projects.g_agreement.banks.binding_factorial import build_bank as BB  # noqa: E402
from projects.g_agreement.banks.w import build_w_bank as W  # noqa: E402
from projects.g_agreement.banks.w import check_prompt_balance as CPB  # noqa: E402
from projects.g_agreement.banks.w import check_w_variance as CWV  # noqa: E402
from projects.g_agreement.core import config as C  # noqa: E402
from projects.g_agreement.dataset import build_dataset as bd  # noqa: E402
from projects.g_agreement.dataset import build_dataset_x as bdx  # noqa: E402

G_DIR = REPO / "projects" / "g_agreement"
BANK_DIR = G_DIR / "banks" / "w"
W_RESULTS = REPO / "results" / "g_agreement" / "w"


def _snapshot():
    """The files this package may write under results/ (other Phase W agents write elsewhere under w/ concurrently,
    so only these are guarded): bank_checks.json and variance/*, with mtimes."""
    paths = [W_RESULTS / "bank_checks.json"] + (sorted((W_RESULTS / "variance").rglob("*")) if (W_RESULTS / "variance").exists() else [])
    return sorted((str(p), p.stat().st_mtime_ns) for p in paths if p.exists())


RESULTS_SNAPSHOT = _snapshot()
CACHE_SNAPSHOT = sorted(str(p) for p in (REPO / "cache" / "g_agreement" / "w").rglob("*")) if (REPO / "cache" / "g_agreement" / "w").exists() else None
MICHAEL_RE = re.compile(r"^\d{1,2} [+-] \d{1,2} =$")


@pytest.fixture(scope="module")
def data():
    return W.build(W.DEFAULT_SEED)


@pytest.fixture(scope="module")
def items(data):
    return data["w"]["items"]


@pytest.fixture(scope="module")
def fam(items):
    out = collections.defaultdict(list)
    for it in items:
        out[it["family"]].append(it)
    return out


@pytest.fixture(scope="module")
def v7(data):
    return data["v7"]["items"]


# ================================================================== counts, schema, determinism
def test_counts_and_schema(items, fam, data):
    assert len(items) == 828 and {f: len(v) for f, v in fam.items()} == {"counts": 600, "ownership4": 128, "arith": 100}
    assert len({it["item_id"] for it in items}) == 828 and len({it["prompt_text"] for it in items}) == 828
    for it in items:
        assert bd.REQUIRED_KEYS <= set(it)
        assert it["split"] == "test" and it["system"] is None and "construction" in it
        assert it["item_id"].startswith(W.PREFIX[it["family"]] + "-")
        pr = it["primary"]
        assert {"name", "question", "candidates", "answer", "answer_aliases"} <= set(pr) and pr["answer"] in pr["candidates"]
        assert re.search(it["target_answer_regex"], pr["answer"])
    assert re.fullmatch(r"wcnt-\d{4}", fam["counts"][0]["item_id"]) and re.fullmatch(r"wown-\d{2}[AB]", fam["ownership4"][0]["item_id"])
    assert re.fullmatch(r"warith-\d{3}", fam["arith"][0]["item_id"])
    meta = data["w"]["meta"]
    assert meta["seed"] == W.DEFAULT_SEED == 20261011 and meta["n_items"] == 828 and meta["frozen"] is False
    assert meta["counts"] == {"counts": 600, "ownership4": 128, "arith": 100}


def test_deterministic_and_matches_disk(data):
    again = W.build(W.DEFAULT_SEED)
    for key in ("w", "v7", "mapping8"):
        assert again[key]["meta"]["sha256_items"] == data[key]["meta"]["sha256_items"] == bd.sha256_items(data[key]["items"])
    other = W.build(W.DEFAULT_SEED + 1)
    assert other["w"]["meta"]["sha256_items"] != data["w"]["meta"]["sha256_items"]
    assert other["v7"]["meta"]["sha256_items"] != data["v7"]["meta"]["sha256_items"]
    assert other["mapping8"]["meta"]["sha256_items"] == data["mapping8"]["meta"]["sha256_items"]  # the index does not depend on the seed
    for key, name in (("w", "items_w.json"), ("v7", "items_v7.json"), ("mapping8", "mapping8_index.json")):
        f = BANK_DIR / name
        assert f.exists(), f"{name} missing: run build_w_bank.py"
        disk = json.loads(f.read_text(encoding="utf-8"))
        assert disk["meta"]["seed"] == W.DEFAULT_SEED and disk["meta"]["sha256_items"] == data[key]["meta"]["sha256_items"]
        assert disk["meta"]["sha256_items"] == bd.sha256_items(disk["items"])


def test_no_id_or_prompt_overlap_with_other_banks(items, v7):
    ids = {it["item_id"] for it in items} | {it["item_id"] for it in v7}
    prompts = {it["prompt_text"] for it in items}
    others = [G_DIR / "dataset" / f for f in ("items.json", "items_x.json", "items_g6.json", "items_x3_candidates.json",
                                               "items_y1_choice.json", "items_y1_selected.json")] + \
             [G_DIR / "banks" / "binding_factorial" / "items_binding_factorial.json"]
    checked = 0
    for f in others:
        if not f.exists():
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        o_items = d["items"] if isinstance(d, dict) and "items" in d else d
        o_ids = {it["item_id"] for it in o_items if isinstance(it, dict) and "item_id" in it}
        o_prompts = {it.get("prompt_text") for it in o_items if isinstance(it, dict)}
        assert not (ids & o_ids), (f.name, sorted(ids & o_ids)[:3])
        assert not (prompts & o_prompts), f.name
        checked += 1
    assert checked >= 3
    # against in-memory rebuilds too
    assert not (ids & {it["item_id"] for it in bd.build(bd.DEFAULT_SEED)["items"]})
    assert not (ids & {it["item_id"] for it in bdx.build(bdx.DEFAULT_SEED)["items"]})
    assert not (ids & {it["item_id"] for it in BB.build(BB.DEFAULT_SEED)["items"]})


# ================================================================== counts family
def test_counts_family_balance(fam):
    c = fam["counts"]
    nv = collections.Counter(it["construction"]["value"] for it in c)
    assert set(nv) == set(range(1, 100)) and set(nv.values()) == {6, 7} and sum(v == 7 for v in nv.values()) == 6
    cells = collections.Counter((it["construction"]["template"], it["construction"]["object"]) for it in c)
    assert len(cells) == 12 and set(cells.values()) == {50}
    assert set(collections.Counter(it["construction"]["place"] for it in c).values()) == {50}
    assert set(collections.Counter(it["template_id"] for it in c).values()) == {150}
    for n in range(1, 100):
        uses = [it["construction"] for it in c if it["construction"]["value"] == n]
        co = collections.Counter(u["object"] for u in uses)
        ct = collections.Counter(u["template"] for u in uses)
        assert all(co[o] >= 2 for o in W.COUNT_FACTORS["object"]) and set(ct) == set(W.COUNT_FACTORS["template"])
        if nv[n] == 6:
            assert set(co.values()) == {2} and sorted(ct.values()) == [1, 1, 2, 2]
    # within every decade of ten values each template is used exactly 15 times (+1 for a seven-use value)
    dt = collections.Counter((it["construction"]["decade"], it["construction"]["template"]) for it in c)
    for d in range(1, 10):
        assert all(15 <= dt[(f"d{d}", t)] <= 16 for t in W.COUNT_FACTORS["template"]), d
    for it in c:
        p, cc = it["prompt_text"], it["construction"]
        assert it["primary"]["answer"] == str(cc["value"]) == it["primary"]["candidates"][0] and len(it["primary"]["candidates"]) == 1
        assert it["primary"]["candidates_all"] == [str(v) for v in range(1, 100)]
        assert W.solve_count(it) == it["primary"]["answer"]
        assert cc["object"] in p and cc["place"] in p and "How many " + cc["object"] in p
        assert it["pair_id"] == it["item_id"] and it["version"] == "A" and it["render"] == "chat"
        if cc["value"] == 1:
            assert re.search(r"\b1 " + cc["object_singular"] + r"\b", p) or p.count(": there is 1.") == 1
        else:
            assert " is " not in p


def test_counts_twelve_cycle_windows():
    for sigma in ((0, 1, 2, 3), (3, 1, 0, 2)):
        cyc = W.twelve_cycle(sigma)
        assert len(set(cyc)) == 12
        for w in (cyc[:6], cyc[6:]):
            assert collections.Counter(o for _, o in w) == {0: 2, 1: 2, 2: 2}
            assert sorted(collections.Counter(t for t, _ in w).values()) == [1, 1, 2, 2]
        assert set(cyc[:6]) | set(cyc[6:]) == set(W.COUNT_CELLS)


# ================================================================== ownership4
def test_ownership4_factorial(fam):
    own = fam["ownership4"]
    by_pair = collections.defaultdict(dict)
    for it in own:
        by_pair[it["pair_id"]][it["version"]] = it
    assert len(by_pair) == 64 and all(set(p) == {"A", "B"} for p in by_pair.values())
    A = [p["A"] for p in by_pair.values()]
    for f, levels in W.FACTORS4.items():
        cnt = collections.Counter(it["construction"][f] for it in A)
        assert set(cnt) == set(levels) and len(set(cnt.values())) == 1, (f, cnt)
    fs = list(W.FACTORS4)
    for i in range(len(fs)):
        for j in range(i + 1, len(fs)):
            c2 = collections.Counter((it["construction"][fs[i]], it["construction"][fs[j]]) for it in A)
            assert len(c2) == len(W.FACTORS4[fs[i]]) * len(W.FACTORS4[fs[j]]) and len(set(c2.values())) == 1, (fs[i], fs[j])
    assert sorted(collections.Counter(it["construction"]["holder_b_shift"] for it in A).values()) == [21, 21, 22]
    assert set(collections.Counter(it["construction"]["asked_object"] for it in A).values()) == {4}
    assert set(collections.Counter(it["construction"]["answer_mention_position"] for it in A).values()) == {16}
    names = {n for s in W.NAME_SETS4 for n in s}
    for pid, p in by_pair.items():
        a, b = p["A"], p["B"]
        ca, cb = a["construction"], b["construction"]
        assert bdx.word_multiset(a["prompt_text"]) == bdx.word_multiset(b["prompt_text"]) and a["prompt_text"] != b["prompt_text"]
        assert a["primary"]["candidates"] == b["primary"]["candidates"] and len(a["primary"]["candidates"]) == 4
        assert a["primary"]["candidates"].index(a["primary"]["answer"]) == 0 and b["primary"]["candidates"].index(b["primary"]["answer"]) == 1
        assert {n for n in ca["names"] if ca["binding"][n] != cb["binding"][n]} == {ca["holder_name_A"], ca["holder_name_B"]}
        assert len(set(ca["binding"].values())) == 4 and set(ca["names"]) <= names
        for it in (a, b):
            assert W.solve_binding4(it) == it["primary"]["answer"]
            assert len(re.findall(r"\b[A-Z][a-z]+ has the [a-z]+ [a-z]+\.", it["prompt_text"])) == 4  # four statements
            c = it["construction"]
            assert (it["prompt_text"].startswith(W.LEAD_IN4)) == (c["template"] == "pos1")
            if c["query_direction"] == "object_to_name":
                assert set(it["primary"]["candidates"]) == set(c["names"]) and it["prompt_text"].endswith(f"Who has the {c['asked_object']}? Answer with the name only.")
            else:
                assert set(it["primary"]["candidates"]) == set(c["objects"]) and it["prompt_text"].endswith(f"What does {c['asked_name']} have? Answer with the object only.")
            assert not re.search(it["target_answer_regex"], " ".join(c["other_candidates"]))


def test_ownership4_name_sets_and_quads(data):
    W.check_name_sets4()
    for q in data["w"]["meta"]["ownership4_design"]["object_quads"]:
        assert len(q) == 4 and len({BB.object_words(o)[0] for o in q}) == 4 and len({BB.object_words(o)[1] for o in q}) == 4
    assert sorted(o for q in data["w"]["meta"]["ownership4_design"]["object_quads"] for o in q) == sorted(bdx.OBJECTS_X)


# ================================================================== arith (Michael's format)
def test_arith_matches_michael_format(fam):
    ar = fam["arith"]
    michael = [json.loads(l) for l in (REPO / "nla-consistency" / "data" / "arithmetic.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert all(MICHAEL_RE.fullmatch(r["text"]) and r["text"] == f"{r['a']} {r['op']} {r['b']} =" for r in michael)
    his = {(r["a"], r["op"], r["b"]) for r in michael}
    ours = set()
    for it in ar:
        assert MICHAEL_RE.fullmatch(it["prompt_text"]) and it["render"] == "plain" and "chat template" in it["render_note"]
        a, op, b = it["operands"]["a"], it["operands"]["op"], it["operands"]["b"]
        assert it["prompt_text"] == f"{a} {op} {b} =" and 2 <= a <= 99 and 1 <= b <= 99
        ans = a - b if op == "-" else a + b
        assert ans >= 0 and it["primary"]["answer"] == str(ans) and it["primary"]["candidates"] == [str(ans)]
        assert it["primary"]["candidates_all"] == [str(v) for v in range(199)]
        assert (a, op, b) not in his
        ours.add((a, op, b))
    assert len(ours) == 100
    assert collections.Counter(it["operands"]["op"] for it in ar) == {"-": 50, "+": 50}
    assert {it["construction"]["a_decade"] for it in ar} == set(range(10)) and {it["construction"]["b_decade"] for it in ar} == set(range(10))
    # Michael's own sampler reproduces his first rows with his seed (format and ranges copied from thread12_pod.py)
    import random
    rng = random.Random(0)
    first = []
    for n in range(3):
        op = "-" if n % 2 == 0 else "+"
        a = rng.randint(2, 99)
        b = rng.randint(1, a - 1) if op == "-" else rng.randint(1, 99)
        first.append((a, op, b))
    assert first == [(r["a"], r["op"], r["b"]) for r in michael[:3]]


# ================================================================== mapping-8 index
def test_mapping8_index(data):
    m8 = data["mapping8"]
    dx = json.loads((G_DIR / "dataset" / "items_x.json").read_text(encoding="utf-8"))
    test = {it["item_id"]: it for it in dx["items"] if it["family"] == "mapping" and it["split"] == "test"}
    assert len(m8["pairs"]) == 47 and len(m8["items"]) == 94 and {r["item_id"] for r in m8["items"]} == set(test)
    assert m8["meta"]["source_sha256_items"] == dx["meta"]["sha256_items"]
    for r in m8["items"]:
        src = test[r["item_id"]]
        assert r["answer"] == src["primary"]["answer"] and r["candidates"] == src["primary"]["candidates"]
        assert r["candidates_all"] == list("ABCDEFGH") and r["k_minus_1_symbol"] == src["construction"]["intermediates"][-1]
        assert r["k_minus_1_symbol"] not in (r["answer"],)
    assert collections.Counter(p["k"] for p in m8["pairs"]) == {2: 23, 3: 24}


# ================================================================== V7
def test_v7_pairs(v7, data):
    by_pair = collections.defaultdict(dict)
    for it in v7:
        by_pair[it["pair_id"]][it["version"]] = it
    assert len(by_pair) == 16 and len(v7) == 32
    for pid, p in by_pair.items():
        a, b = p["A"], p["B"]
        assert a["prompt_text"] == b["prompt_text"] and a["prompt_only_text"] == b["prompt_only_text"]
        assert a["preamble"] != b["preamble"] and bdx.word_multiset(a["preamble"]) == bdx.word_multiset(b["preamble"])
        assert a["primary"]["candidates"] == b["primary"]["candidates"] and a["primary"]["answer"] != b["primary"]["answer"]
        for it in (a, b):
            assert it["preamble_role"] == "system" and it["system"] is None and it["render"] == "chat" and it["family"] == "ownership"
            assert it["capture_messages"] == [{"role": "system", "content": it["preamble"]}, {"role": "user", "content": it["prompt_text"]}]
            assert it["prompt_only_text"] == C.PROMPT_ONLY_TEMPLATE.format(prompt_text=it["prompt_text"], question=it["primary"]["question"])
            assert it["preamble"] not in it["prompt_only_text"]
            for n in it["primary"]["candidates"]:
                assert n not in it["prompt_text"] and n in it["preamble"]
            assert bd.solve_prompt({**it, "family": "ownership"}) is None  # the visible prompt carries no binding
            assert W.solve_v7(it) == it["primary"]["answer"]
            assert re.fullmatch(r"Who has the [a-z]+ [a-z]+\? Answer with the name only\.", it["prompt_text"])
    A = [p["A"] for p in by_pair.values()]
    assert set(collections.Counter(it["template_id"] for it in A).values()) == {8}
    assert set(collections.Counter(it["construction"]["answer_is_first_mentioned"] for it in A).values()) == {8}
    assert len({tuple(it["primary"]["candidates"]) for it in A}) == 16 and len({it["prompt_text"] for it in A}) == 16
    assert data["v7"]["meta"]["prompt_only_template_sha256"] == C.sha256_bytes(C.PROMPT_ONLY_TEMPLATE.encode())


# ================================================================== prompt-level balance check (no write)
def test_check_prompt_balance_all_pass():
    rep = CPB.run(BANK_DIR)
    failed = [r for r in rep["checks"] if not r["pass"]]
    assert rep["all_pass"] and not failed, failed
    assert rep["n_checks"] >= 40 and rep["counts"] == {"counts": 600, "ownership4": 128, "arith": 100, "mapping8_items_indexed": 94, "v7": 32}
    assert "ALL PASS" in CPB.to_text(rep)


# ================================================================== check_w_variance on synthetic states
def _write_states(sd: Path, ids, H):
    import torch

    sd.mkdir(parents=True, exist_ok=True)
    for iid, h in zip(ids, H):
        torch.save(torch.tensor(h, dtype=torch.float32), sd / f"{iid}.pt")


@pytest.mark.parametrize("factor", ["template", "mention_order", "mention_pos_A", "holder_b_shift", "query_direction"])
def test_variance_ownership4_planted_factor_stops(tmp_path, fam, factor):
    rng = np.random.default_rng(1)
    d = 32
    pairs = sorted(CWV.CV.load_pairs(fam["ownership4"]), key=lambda p: p["pair_id"])
    labels = CWV.pair_labels(pairs)
    levels = sorted(set(labels[factor]))
    sign = {lv: (-1.0 if i == 0 else 1.0 if i == len(levels) - 1 else 0.0) if len(levels) > 2 else (-1.0 if i == 0 else 1.0) for i, lv in enumerate(levels)}
    s = np.array([sign[l] for l in labels[factor]])
    HA = rng.normal(size=(len(pairs), d))
    D = rng.normal(size=(len(pairs), d))
    D[:, 0] += 6.0 * s
    _write_states(tmp_path / "s", [p["A"]["item_id"] for p in pairs], HA)
    _write_states(tmp_path / "s", [p["B"]["item_id"] for p in pairs], HA + D)
    rep = CWV.run("ownership4", states_dir=tmp_path / "s", items=fam["ownership4"], n_relabel=3)
    assert rep["stop"] is True and factor in rep["offending_factors"] and rep["full"]["factors"][factor]["r2_pc"][0] > 0.6
    for f in rep["stop_rule_factors"]:
        if f != factor:
            assert rep["full"]["factors"][f]["r2_pc"][0] < 0.25, (f, rep["full"]["factors"][f]["r2_pc"][0])
    assert rep["verdict"].startswith("STOP")
    out = CWV.write_report(rep, tmp_path / "out")
    assert all(p.exists() for p in out) and "STOP" in (tmp_path / "out" / "variance_check_ownership4.md").read_text()


def test_variance_ownership4_noise_passes(fam):
    rng = np.random.default_rng(2)
    D = rng.normal(size=(64, 32))
    rep = CWV.run("ownership4", D=D, items=fam["ownership4"], n_relabel=5)
    assert rep["stop"] is False and rep["offending_factors"] == [] and rep["verdict"].startswith("PASS")
    assert all(rep["full"]["factors"][f]["r2_pc"][0] < 0.25 for f in rep["stop_rule_factors"])
    assert rep["hewitt_liang_control"]["pass"] is True and set(rep["by_split"]) == {"object_to_name", "name_to_object"}
    assert "answer_identity" in rep["full"]["factors"] and "answer_identity" not in rep["stop_rule_factors"]
    assert set(rep["full"]["factors"]["mention_pos_A"]["levels"]) == {"0", "1", "2", "3"} == set(rep["full"]["factors"]["mention_pos_B"]["levels"])
    assert set(rep["full"]["factors"]["mention_pos_A"]["levels"].values()) == {16}


@pytest.mark.parametrize("factor", ["object", "template", "decade"])
def test_variance_counts_planted_factor_stops(tmp_path, fam, factor):
    rng = np.random.default_rng(3)
    items = sorted(fam["counts"], key=lambda it: it["item_id"])
    labels = CWV.item_labels(items, "counts")[factor]
    levels = sorted(set(labels))
    H = rng.normal(size=(len(items), 32))
    H[:, 0] += 6.0 * np.array([levels.index(l) - (len(levels) - 1) / 2 for l in labels])
    _write_states(tmp_path / "s", [it["item_id"] for it in items], H)
    rep = CWV.run("counts", states_dir=tmp_path / "s", items=items)
    assert rep["stop"] is True and rep["offending_factors"] == [factor] and rep["full"]["factors"][factor]["r2_pc"][0] > 0.8
    assert rep["mode"] == "centred" and rep["n_units"] == 600 and rep["hewitt_liang_control"] is None
    if factor == "decade":
        assert rep["diagnostics"]["value_linear_r2_pc1"] > 0.8  # decade order is value order


def test_variance_counts_noise_passes(fam):
    rng = np.random.default_rng(4)
    rep = CWV.run("counts", D=rng.normal(size=(600, 32)), items=fam["counts"])
    assert rep["stop"] is False and all(rep["full"]["factors"][f]["r2_pc"][0] < 0.1 for f in rep["stop_rule_factors"])
    assert rep["diagnostics"]["value_linear_r2_pc1"] < 0.1 and rep["verdict"].startswith("PASS")
    md = CWV.to_markdown(rep)
    assert "PASS" in md and "| place |" in md


def test_variance_cli_and_helpers(tmp_path, fam):
    rng = np.random.default_rng(5)
    pairs = sorted(CWV.CV.load_pairs(fam["ownership4"]), key=lambda p: p["pair_id"])
    HA = rng.normal(size=(64, 16))
    _write_states(tmp_path / "s", [p["A"]["item_id"] for p in pairs], HA)
    _write_states(tmp_path / "s", [p["B"]["item_id"] for p in pairs], HA + rng.normal(size=(64, 16)))
    assert CWV.main(["--states-dir", str(tmp_path / "s"), "--family", "ownership4", "--no-write", "--n-relabel", "2"]) == 0
    assert CWV.r2_linear(np.array([1.0, 2.0, 3.0, 4.0]), [1, 2, 3, 4]) == pytest.approx(1.0)
    assert CWV.r2_linear(np.array([1.0, -1.0, 1.0, -1.0]), [1, 2, 3, 4]) < 0.3
    with pytest.raises(FileNotFoundError):
        CWV.run("counts", states_dir=tmp_path / "missing", items=fam["counts"])


# ================================================================== guard
def test_zz_results_cache_untouched():
    assert _snapshot() == RESULTS_SNAPSHOT
    if CACHE_SNAPSHOT is not None:
        assert sorted(str(p) for p in (REPO / "cache" / "g_agreement" / "w").rglob("*")) == CACHE_SNAPSHOT
