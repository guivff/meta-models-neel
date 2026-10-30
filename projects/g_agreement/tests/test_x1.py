"""Offline tests for Phase X1 (BRIEF_X.md): dataset/build_dataset_x.py and dataset/build_x3.py invariants,
the X NLA templates, x1_bank/collect.py on the MOCK tiny model (tmp paths), and x1_bank/analyze.py end to
end on a synthetic x1_lo.jsonl + random states. Nothing is written under results/ or cache/ (guard test).

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_x1.py -q``
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

from projects.g_agreement.core import config as C  # noqa: E402
from projects.g_agreement.core import generate as G  # noqa: E402
from projects.g_agreement.core import scoring_lo as LO  # noqa: E402
from projects.g_agreement.dataset import build_dataset as bd  # noqa: E402
from projects.g_agreement.dataset import build_dataset_x as bdx  # noqa: E402
from projects.g_agreement.dataset import build_x3 as bx3  # noqa: E402
from projects.g_agreement.x1_bank import analyze as XA  # noqa: E402
from projects.g_agreement.x1_bank import collect as XC  # noqa: E402

G_DIR = REPO / "projects" / "g_agreement"
RESULTS_SNAPSHOT = sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*"))
CACHE_SNAPSHOT = sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None
MANIFEST_SNAPSHOT = sorted(str(p) for p in (G_DIR / "manifest").rglob("*"))


@pytest.fixture(scope="module")
def data_x():
    return bdx.build(bdx.DEFAULT_SEED)


@pytest.fixture(scope="module")
def items_x(data_x):
    return data_x["items"]


@pytest.fixture(scope="module")
def data_x3():
    return bx3.build(bx3.DEFAULT_SEED)


def _pairs(items):
    by = {}
    for it in items:
        by.setdefault(it["pair_id"], {})[it["version"]] = it
    return by


# ================================================================== build_dataset_x
def test_x_counts_and_split(items_x):
    assert len(items_x) == 288 and len(_pairs(items_x)) == 144
    for fam, n in bdx.N_PAIRS.items():
        fi = [it for it in items_x if it["family"] == fam]
        assert len(fi) == 2 * n
        dev = [it for it in fi if it["split"] == "dev"]
        assert len(dev) == 2 and {it["pair_id"] for it in dev} == {f"{bdx.PREFIX[fam]}-01"}


def test_x_ids_and_no_overlap_with_g_datasets(items_x):
    g_items = bd.build(bd.DEFAULT_SEED)["items"]
    g_ids = {it["item_id"] for it in g_items}
    g_prompts = {it["prompt_text"] for it in g_items}
    for p in ("items.json", "items_g6.json"):
        f = G_DIR / "dataset" / p
        if f.exists():
            g_ids |= {it["item_id"] for it in json.loads(f.read_text())["items"]}
    for it in items_x:
        assert it["item_id"].startswith(bdx.PREFIX[it["family"]] + "-") and it["item_id"] == it["pair_id"] + it["version"]
        assert it["item_id"] not in g_ids and it["prompt_text"] not in g_prompts
    assert len({it["item_id"] for it in items_x}) == len(items_x)


def test_x_pairs_share_fields(items_x):
    for pid, p in _pairs(items_x).items():
        a, b = p["A"], p["B"]
        for k in ("family", "split", "template_id"):
            assert a[k] == b[k]
        assert a["primary"]["candidates"] == b["primary"]["candidates"]
        assert a["primary"]["answer"] == a["primary"]["candidates"][0] and b["primary"]["answer"] == b["primary"]["candidates"][1]
        assert a["prompt_text"] != b["prompt_text"]
        assert bd.SHORT_ANSWER_CUE.search(a["prompt_text"])


def test_x_permutation_invariant(items_x):
    for pid, p in _pairs(items_x).items():
        if p["A"]["family"] in ("ownership", "mapping"):
            assert bdx.word_multiset(p["A"]["prompt_text"]) == bdx.word_multiset(p["B"]["prompt_text"]), pid
            assert len(p["A"]["prompt_text"].split()) == len(p["B"]["prompt_text"].split()), pid


def test_x_solver_agreement(items_x):
    for it in items_x:
        if it["family"] == "mapping":
            assert bdx.solve_k_steps(it) == it["primary"]["answer"], it["item_id"]
            if it["construction"]["k"] == 2:
                assert bd.solve_prompt(it) == it["primary"]["answer"], it["item_id"]
        else:
            assert bd.solve_prompt(it) == it["primary"]["answer"], it["item_id"]


def test_x_mapping_step_mix_and_templates(items_x):
    mp = [it for it in items_x if it["family"] == "mapping" and it["version"] == "A"]
    ks = collections.Counter(it["construction"]["k"] for it in mp)
    assert ks == {2: 24, 3: 24}
    test = [it for it in mp if it["split"] == "test"][:32]  # the X2 selection
    assert abs(sum(it["construction"]["k"] == 2 for it in test) - 16) <= 1
    for it in mp:
        assert it["primary"]["name"] == bdx.STEP_NAME[it["construction"]["k"]]
        for c in it["primary"]["candidates"]:
            assert re.search(r"(?<![A-Za-z])" + c + r"(?![A-Za-z])", it["prompt_text"])
    for t, g in zip(bdx.MAPPING_TEMPLATES_X, bd.MAPPING_TEMPLATES):
        assert bdx.mapping_text(t, 2) == g["text"]


def test_x_ownership_pools_and_counterbalance(items_x):
    own = [it for it in items_x if it["family"] == "ownership"]
    names = {n for it in own for n in it["primary"]["candidates"]}
    assert names <= set(bdx.NAMES_X)
    assert {o for it in own for o in it["secondary"]["objects"]} <= set(bdx.OBJECTS_X)
    combos = {(tuple(sorted(it["primary"]["candidates"])), tuple(it["secondary"]["objects"]), it["template_id"]) for it in own}
    assert len(combos) == 48
    first = [it["construction"]["answer_is_first_mentioned"] for it in own if it["split"] == "test" and it["version"] == "A"]
    assert abs(sum(first) - (len(first) - sum(first))) <= 1
    for it in own:
        assert bd.solve_prompt(it) == it["primary"]["answer"]
        assert re.search(it["target_answer_regex"], it["primary"]["answer"]) and not re.search(it["target_answer_regex"], it["construction"]["other_candidate"])


def test_x_language_and_tense(items_x):
    lang = [it for it in items_x if it["family"] == "language"]
    assert len({tuple(sorted(it["primary"]["candidates"])) for it in lang}) == 24
    for it in lang:
        assert it["construction"]["other_candidate"] not in it["prompt_text"]
        assert not bdx.expected_words_cross_match(it["construction"]["expected_word"], it["construction"]["expected_word_other"])
        sample = re.sub(r"\[(.)[^\]]*\]", r"\1", it["construction"]["expected_word"].split("|")[0])  # first alternative, classes collapsed
        assert re.search(it["target_answer_regex"], sample) and not re.search(it["target_answer_regex"], "zzz")
        assert it["primary"]["name"] == "response_language"
    tense = [it for it in items_x if it["family"] == "tense"]
    assert len({(it["template_id"], it["construction"]["subject"], it["construction"]["place"]) for it in tense}) == 24
    assert all(it["primary"]["candidates"] == ["past", "future"] for it in tense)


def test_x_deterministic_and_matches_disk(data_x):
    again = bdx.build(bdx.DEFAULT_SEED)
    assert again["items"] == data_x["items"] and again["meta"]["sha256_items"] == data_x["meta"]["sha256_items"]
    assert data_x["meta"]["sha256_items"] == bd.sha256_items(data_x["items"])
    assert bdx.build(bdx.DEFAULT_SEED + 1)["meta"]["sha256_items"] != data_x["meta"]["sha256_items"]
    f = G_DIR / "dataset" / "items_x.json"
    if f.exists():
        disk = json.loads(f.read_text(encoding="utf-8"))
        assert disk["meta"]["sha256_items"] == bdx.build(disk["meta"]["seed"])["meta"]["sha256_items"]
    meta = data_x["meta"]
    assert meta["seed"] == 20261008 and meta["n_items"] == 288 and set(meta["counts"]) == set(bdx.FAMILIES)
    table = bdx.summary_table(data_x)
    assert all(fam in table for fam in bdx.FAMILIES)


# ================================================================== build_x3
def test_x3_counts_and_ids(data_x3):
    items = data_x3["items"]
    pz = [it for it in items if it["family"] == "puzzle"]
    ch = [it for it in items if it["family"] == "choice"]
    assert len(items) == 700 and len(pz) == 400 and len(ch) == 300
    assert [it["item_id"] for it in pz][:2] == ["xpz-0001", "xpz-0002"] and ch[0]["item_id"] == "xch-0001" and ch[-1]["item_id"] == "xch-0300"
    assert len({it["item_id"] for it in items}) == 700
    assert data_x3["meta"]["counts"] == {"puzzle": 400, "choice": 300}


def test_x3_puzzle_traces(data_x3):
    pz = [it for it in data_x3["items"] if it["family"] == "puzzle"]
    assert collections.Counter(it["primary"]["k"] for it in pz) == {3: 200, 4: 200}
    for it in pz:
        p = it["primary"]
        m = it["construction"]["mapping"]
        assert 5 <= len(m) <= 7 and set(m) <= set("ABCDEFGH") and all(v in m and v != k for k, v in m.items())
        assert bx3.follow(m, p["start"], p["k"]) == p["trace"] and p["trace"][-1] == p["correct"]
        assert p["correct"] != p["start"] and p["correct"] != p["trace"][-2]
        assert it["distractors"] == p["trace"][:-1] and p["correct"] not in it["distractors"]
        assert bx3.solve_puzzle(it) == p["correct"]
        assert it["prompt_text"].count("→") == len(m) and "Answer with the symbol only." in it["prompt_text"]
        assert re.search(it["target_answer_regex"], p["correct"]) and not re.search(it["target_answer_regex"], "answer")
        assert it["construction"]["shape"] == f"n{len(m)}_k{p['k']}"
    assert len({it["prompt_text"] for it in pz}) == 400


def test_x3_choice_both_orders_and_prompt_only(data_x3):
    ch = [it for it in data_x3["items"] if it["family"] == "choice"]
    by = _pairs(ch)
    assert len(by) == 150
    for pid, p in by.items():
        a, b = p["A"], p["B"]
        assert a["primary"]["candidates"] == b["primary"]["candidates"] and a["template_id"] == b["template_id"]
        assert a["construction"]["options_in_prompt_order"] == b["construction"]["options_in_prompt_order"][::-1]
        assert a["construction"]["first_mentioned_candidate"] != b["construction"]["first_mentioned_candidate"]
        assert a["primary"]["answer"] is None and a["primary"]["answer_source"] == "target_greedy"
    for it in ch:
        assert it["prompt_only_text"] == G.prompt_only_prompt(it)
        assert it["prompt_text"] in it["prompt_only_text"] and it["primary"]["question"] in it["prompt_only_text"]
        for forbidden in ("<explanation>", "<activation>"):
            assert forbidden not in it["prompt_only_text"]
    from projects.g_agreement.dataset import build_dataset_g6 as g6

    option_sets = {frozenset(p["A"]["primary"]["candidates"]) for p in by.values()}
    assert all(frozenset(m["options"]) in option_sets for m in g6.OPTION_PAIRS)
    assert {it["template_id"] for it in ch} == {t["id"] for t in g6.TEMPLATES}
    assert data_x3["meta"]["prompt_only_template_sha256"] == C.sha256_bytes(C.PROMPT_ONLY_TEMPLATE.encode())


def test_x3_deterministic_and_matches_disk(data_x3):
    again = bx3.build(bx3.DEFAULT_SEED)
    assert again["items"] == data_x3["items"]
    f = G_DIR / "dataset" / "items_x3_candidates.json"
    if f.exists():
        disk = json.loads(f.read_text(encoding="utf-8"))
        assert disk["meta"]["sha256_items"] == bx3.build(disk["meta"]["seed"])["meta"]["sha256_items"] == bx3.sha256_items(disk["items"])


# ================================================================== scoring_lo templates
def test_x_nla_templates_additive():
    assert LO.templates_for("language") == ["The reply must be written in {X}.", "The requested language is {X}."]
    assert LO.templates_for("tense") == ["The sentence must be in the {X} tense.", "The requested tense is {X}."]
    assert LO.templates_for("puzzle") == LO.templates_for("mapping")
    assert LO.templates_for("ownership")[0] == 'The answer must be the name "{X}".'
    assert LO.templates_for("choice")[0] == 'The answer must be the word "{X}".'
    assert LO.templates_for("unknown") == LO.DEFAULT_TEMPLATES


# ================================================================== collect helpers (CPU, no model)
def test_collect_pairs_and_keys(items_x):
    ps = XC.load_pairs(split="test", items=items_x)
    assert len(ps) == 140 and [p["family"] for p in ps[:47]] == ["ownership"] * 47
    assert XC.load_pairs(split="dev", items=items_x) and [p["pair_id"] for p in XC.load_pairs(split="dev", items=items_x)] == ["xown-01", "xmap-01", "xlang-01", "xtense-01"]
    lim = XC.load_pairs(split="test", limit_pairs=2, items=items_x)
    assert [p["pair_id"] for p in lim] == ["xown-02", "xown-03", "xmap-02", "xmap-03", "xlang-02", "xlang-03", "xtense-02", "xtense-03"]
    p = ps[0]
    assert XC.other_candidate(p["A"]) == p["B"]["primary"]["answer"]
    assert XC.lo_key("olens", "xown-02A") == "olens|xown-02A" and XC.mean_key("nla", "tense") == "nla|mean|tense"
    assert any(f.name == "collect.py" and f.parent.name == "x1_bank" for f in XC.x_code_files())


def test_freeze_x_on_tmp(tmp_path, monkeypatch):
    fz = tmp_path / "frozen_config_x.json"
    monkeypatch.setattr(XC, "FROZEN_X", fz)
    ok, probs = XC.frozen_status_x()
    assert not ok and "missing" in probs[0]
    XC.require_frozen_x("dev", False)  # dev never needs the freeze
    XC.require_frozen_x("test", True)  # --allow-unfrozen
    with pytest.raises(SystemExit):
        XC.require_frozen_x("test", False)
    monkeypatch.setattr(XC.C, "MANIFEST_DIR", tmp_path)
    assert XC.freeze_x() == fz
    snap = json.loads(fz.read_text())
    assert snap["frozen"] and snap["items_x_sha256"] == C.sha256_file(XC.ITEMS_X) and "x_code_sha256" in snap
    assert XC.frozen_status_x()[0] is True
    XC.require_frozen_x("test", False)
    with pytest.raises(RuntimeError):
        XC.freeze_x()
    sh = XC.x_shas()
    assert sh["manifest_x"] == "frozen_config_x.json" and sh["frozen_x_code_sha256"] == snap["x_code_sha256"]


# ================================================================== collect on the MOCK tiny model
torch = pytest.importorskip("torch")
from projects.g_agreement.core import model as M  # noqa: E402
from projects.g_agreement.core import readers as R  # noqa: E402
from projects.g_agreement.core import accounting as A  # noqa: E402
from projects.g_agreement.tests.test_readers_mock import MOCK_D, MOCK_LAYER, FakeTok, mock_meta, tiny_model  # noqa: E402


def mock_pair(pid, family, prompt_a, prompt_b, a, b, k=2):
    """A pair with single-letter candidates (the char-level FakeTok gives single-token variants)."""
    out = {"pair_id": pid, "family": family, "split": "test"}
    for v, prompt, ans in (("A", prompt_a, a), ("B", prompt_b, b)):
        out[v] = {"item_id": pid + v, "pair_id": pid, "version": v, "family": family, "split": "test", "render": "chat", "system": None,
                  "template_id": "t", "prompt_text": prompt, "primary": {"name": "x", "question": "?", "candidates": [a, b], "answer": ans, "answer_aliases": []},
                  "construction": {"answer_is_first_mentioned": v == "A", "k": k}}
    return out


def mock_pairs():
    return [mock_pair("xown-01", "ownership", "A has the key. B has the pen. Who has the key? Name only.", "B has the key. A has the pen. Who has the key? Name only.", "A", "B"),
            mock_pair("xown-02", "ownership", "C has the cup. D has the hat. Who has the cup? Name only.", "D has the cup. C has the hat. Who has the cup? Name only.", "C", "D"),
            mock_pair("xmap-01", "mapping", "E -> F. F -> G. H -> E. Twice from E? Symbol only.", "E -> F. F -> H. G -> E. Twice from E? Symbol only.", "G", "H")]


def test_collect_mock_end_to_end(tmp_path, monkeypatch):
    for k, v in (("LAYER", MOCK_LAYER), ("HIDDEN_STATES_INDEX", MOCK_LAYER + 1), ("D_MODEL", MOCK_D), ("N_LAYERS", 4), ("DEV_EXTRA_LAYERS", ())):
        monkeypatch.setattr(C, k, v)
    target = M.Target(model=tiny_model(), tokenizer=FakeTok(), device="cpu", model_id="MOCK/tiny", revision="mock", model_class="Qwen3_5ForCausalLM")
    pairs = mock_pairs()
    sd, meta, led, log, lo = (tmp_path / f for f in ("states", "meta.jsonl", "c.jsonl", "log.md", "x1_lo.jsonl"))
    rows_meta = XC.capture_states(target, pairs, states_dir=sd, meta_path=meta, ledger_path=led, log_path=log)
    assert len(rows_meta) == 6 and all((sd / f"{p[v]['item_id']}.pt").exists() for p in pairs for v in "AB")
    assert all(r["layer"] == MOCK_LAYER and r["pre_answer"] for r in rows_meta.values())
    torch.manual_seed(1)
    jl = R.JLensReader().bind_tensors({MOCK_LAYER: torch.eye(MOCK_D) + torch.randn(MOCK_D, MOCK_D) / 10}, M.unembed_weight(target.model), target.tokenizer)
    ol = R.OLensReader(max_new_tokens=4)
    ol.target = target  # MOCK: no LoRA
    tok = FakeTok()
    nla = R.NLAReader(max_new_tokens=4).attach(tiny_model(3), tok, mock_meta(tok), device="cpu")
    for reader in (jl, ol, nla):
        assert XC.collect_lo(reader, pairs, lo_path=lo, ledger_path=led, log_path=log, states_dir=sd, batch=4) == 6
        assert XC.collect_mean_lo(reader, pairs, lo_path=lo, ledger_path=led, log_path=log, states_dir=sd, batch=4) == 2
        assert XC.collect_lo(reader, pairs, lo_path=lo, ledger_path=led, log_path=log, states_dir=sd, batch=4) == 0  # resumable
        assert XC.collect_mean_lo(reader, pairs, lo_path=lo, ledger_path=led, log_path=log, states_dir=sd) == 0
    rows = A.read_jsonl(lo)
    e1 = [r for r in rows if r["condition"] == "natural"]
    e3 = [r for r in rows if r["condition"] == "mean_state"]
    assert len(e1) == 18 and len(e3) == 6 and {r["reader"] for r in e1} == {"jlens", "olens", "nla"}
    r = next(r for r in e1 if r["reader"] == "nla" and r["item_id"] == "xown-01B")
    assert r["key"] == "nla|xown-01B" and (r["cand_A"], r["cand_B"]) == ("B", "A") and r["templates"] == LO.templates_for("ownership")
    for k in ("pair_id", "family", "split", "version", "lo", "lp_A", "lp_B", "unscorable", "items_file_sha256", "current_x_code_sha256", "chunk_size"):
        assert k in r, k
    assert all(not r["unscorable"] and isinstance(r["lo"], float) for r in e1)
    m = next(r for r in e3 if r["reader"] == "olens" and r["family"] == "ownership")
    assert m["key"] == "olens|mean|ownership" and m["n_states_in_mean"] == 4 and len(m["per_pair"]) == 2 and m["within_band"] in (True, False)
    assert m["per_pair"][0]["cand_A"] == "A" and m["per_pair"][1]["cand_A"] == "C"
    steps = {x["step"] for x in A.read_jsonl(led)}
    assert {"capture", "x1_lo_jlens", "x1_lo_olens", "x1_lo_nla", "x1_mean_lo_jlens", "x1_mean_lo_nla"} <= steps
    assert "lo nla" in log.read_text()
    # the analysis runs on the mock rows (one family per probe type, 2 and 1 pairs)
    items_file = tmp_path / "items.json"
    items_file.write_text(json.dumps({"meta": {"sha256_items": "mock"}, "items": [p[v] for p in pairs for v in "AB"]}))
    s = XA.main(["--items", str(items_file), "--lo", str(lo), "--states-dir", str(sd), "--out", str(tmp_path / "out"), "--allow-unfrozen", "--n-boot", "50", "--no-fig"])
    assert s["E1"]["olens"]["ownership"]["n"] == 2 and s["E2"]["ownership"]["loo"]["n"] == 2 and s["E2"]["mapping"]["loo"]["n"] == 0


# ================================================================== analyze on a synthetic world
def synthetic_world(root: Path, items_x, n_pairs=6, d=32, seed=0, split="test"):
    """Subset of items_x (n_pairs per family), random fp32 states with the family fact planted linearly,
    E1 rows: olens/jlens separate (+2 nats for the own answer), nla at chance; jlens language rows unscorable;
    no jlens rows at all for tense (missing); E3 rows for every reader x family."""
    rng = np.random.default_rng(seed)
    sel = []
    for fam in XA.FAMILIES:
        pids = []
        for it in items_x:
            if it["family"] == fam and it["split"] == split and it["pair_id"] not in pids:
                pids.append(it["pair_id"])
        sel += [it for it in items_x if it["pair_id"] in pids[:n_pairs]]
    items_file = root / "items_x.json"
    items_file.write_text(json.dumps({"meta": {"sha256_items": "mock"}, "items": sel}, ensure_ascii=False))
    sd = root / "states"
    sd.mkdir()
    u = {fam: rng.normal(size=d) for fam in XA.FAMILIES}
    val_dir = {}
    pairs = XA.load_pairs({it["item_id"]: it for it in sel}, split)
    for fam, ps in pairs.items():
        for p in ps:
            for v in "AB":
                it = p[v]
                if XA.PROBE_TYPE[fam] == "binary":
                    sign = 1.0 if XA.pos_version(p) == v else -1.0
                    h = rng.normal(size=d) + 4.0 * sign * u[fam]
                else:
                    val = it["primary"]["answer"]
                    if val not in val_dir:
                        val_dir[val] = rng.normal(size=d)
                    h = rng.normal(size=d) + 4.0 * val_dir[val]
                torch.save(torch.tensor(h, dtype=torch.float32), sd / f"{it['item_id']}.pt")
    lo_rows = []
    for fam, ps in pairs.items():
        for rd in XA.READERS:
            for p in ps:
                for v in "AB":
                    it = p[v]
                    if rd == "jlens" and fam == "tense":
                        continue
                    uns = rd == "jlens" and fam == "language"
                    lo = None if uns else (2.0 + rng.normal(0, 0.3) if rd != "nla" else rng.normal(0, 1.0))
                    lo_rows.append({"key": f"{rd}|{it['item_id']}", "reader": rd, "item_id": it["item_id"], "pair_id": p["pair_id"], "family": fam,
                                    "split": split, "version": v, "condition": "natural", "cand_A": it["primary"]["answer"],
                                    "cand_B": XC.other_candidate(it), "lo": lo, "lp_A": None, "lp_B": None, "templates": ["t"], "unscorable": uns})
            lo_rows.append({"key": f"{rd}|mean|{fam}", "reader": rd, "family": fam, "condition": "mean_state", "n_states_in_mean": 2 * len(ps),
                            "per_pair": [], "n_scorable": len(ps), "mean_lo": 0.3 if rd != "nla" else 1.7, "mean_abs_lo": 0.5, "within_band": rd != "nla"})
    lo = root / "x1_lo.jsonl"
    lo.write_text("\n".join(json.dumps(r) for r in lo_rows) + "\n")
    return items_file, lo, sd


def test_analyze_synthetic_end_to_end(tmp_path, items_x):
    items_file, lo, sd = synthetic_world(tmp_path, items_x)
    out = tmp_path / "out"
    s = XA.main(["--items", str(items_file), "--lo", str(lo), "--states-dir", str(sd), "--out", str(out), "--allow-unfrozen", "--n-boot", "200"])
    for f in ("summary.json", "e1.csv", "e2.csv", "fig_main.png"):
        assert (out / f).exists(), f
    for fam in XA.FAMILIES:
        e = s["E1"]["olens"][fam]
        assert e["n"] == 6 and e["p"] == 1.0 and e["separates"] and e["lo"] > 0.5 and e["wilson_lo"] > 0.5
        assert s["E1"]["nla"][fam]["separates"] in (True, False) and s["E1"]["nla"][fam]["n"] == 6
        e2 = s["E2"][fam]
        assert e2["probe_type"] == XA.PROBE_TYPE[fam] and e2["loo"]["n"] + e2["loo"]["n_pairs_skipped"] == 6
        assert e2["loo"]["p"] == 1.0 and e2["present"] and e2["loo"]["auroc"] == 1.0
        assert e2["ceiling"]["pooled"]["n"] > 0 and e2["ceiling"]["n_half1"] == 3 and e2["ceiling"]["n_half2"] == 3
        assert s["E3"]["olens"][fam]["within_band"] is True and s["E3"]["nla"][fam]["within_band"] is False
    jl = s["E1"]["jlens"]
    assert jl["language"]["n"] == 0 and jl["language"]["n_unscorable_rows"] == 12 and jl["language"]["separates"] is False
    assert jl["tense"]["n"] == 0 and jl["tense"]["n_missing_rows"] == 12
    assert np.isnan(jl["tense"]["p"])
    e1_csv = (out / "e1.csv").read_text().splitlines()
    assert len(e1_csv) == 1 + 3 * 4 and "separates" in e1_csv[0]
    assert len((out / "e2.csv").read_text().splitlines()) == 1 + 4


def test_analyze_dev_smoke_and_missing_states(tmp_path, items_x):
    items_file, lo, sd = synthetic_world(tmp_path, items_x, n_pairs=1, split="dev")
    (sd / "xtense-01A.pt").unlink()  # a missing state must be counted, not crash
    out = tmp_path / "dev"
    s = XA.main(["--items", str(items_file), "--lo", str(lo), "--states-dir", str(sd), "--out", str(out), "--split", "dev", "--n-boot", "20"])
    assert (out / "fig_main.png").exists() and s["split"] == "dev"
    for fam in XA.FAMILIES:
        assert s["E2"][fam]["loo"]["n"] == 0 and s["E2"][fam]["present"] is False  # LOO undefined on one pair
        assert s["E1"]["olens"][fam]["n"] == 1
    assert s["E2"]["tense"]["n_states_missing"] == 2
    # test split without the X freeze is refused unless --allow-unfrozen
    with pytest.raises(XA.U.FrozenConfigError):
        XA.main(["--items", str(items_file), "--lo", str(lo), "--states-dir", str(sd), "--out", str(out), "--frozen-config", str(tmp_path / "none.json"), "--no-fig"])


def test_zz_results_cache_manifest_untouched():
    assert sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*")) == RESULTS_SNAPSHOT
    cache = sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None
    assert cache == CACHE_SNAPSHOT
    assert sorted(str(p) for p in (G_DIR / "manifest").rglob("*")) == MANIFEST_SNAPSHOT
