"""Y1 (BRIEF_Y.md §Y1) tests, CPU only: the choice-pool builder invariants, the union selection on a fixture, the
multi-layer / multi-position capture + logit-lens row on the tiny MOCK model, the reread rows for the three readers,
and analyze.py end to end on a synthetic capture cache (a planted signal at one cell -> S* there; none -> K7; reread
verdicts). Every path is a tmp_path; results/, cache/ and dataset/ are asserted untouched.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_y1.py -q``
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

torch = pytest.importorskip("torch")

from projects.g_agreement.core import accounting as A  # noqa: E402
from projects.g_agreement.core import config as C  # noqa: E402
from projects.g_agreement.core import model as M  # noqa: E402
from projects.g_agreement.core import readers as R  # noqa: E402
from projects.g_agreement.dataset import build_y1_choice as BY  # noqa: E402
from projects.g_agreement.tests.test_readers_mock import MOCK_D, MOCK_LAYER, FakeTok, mock_meta, tiny_model  # noqa: E402
from projects.g_agreement.tests.test_x3 import choice as x3_choice  # noqa: E402
from projects.g_agreement.tests.test_x3 import puzzle as x3_puzzle  # noqa: E402
from projects.g_agreement.x3_floor import collect as X3  # noqa: E402
from projects.g_agreement.y1_site import analyze as YA  # noqa: E402
from projects.g_agreement.y1_site import collect as Y  # noqa: E402

RESULTS_SNAPSHOT = sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*"))
CACHE_SNAPSHOT = sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None
DATASET_SNAPSHOT = sorted(str(p) for p in (REPO / "projects" / "g_agreement" / "dataset").glob("*"))
MOCK_LAYERS = [1, 2]  # the tiny model has blocks 0..3; block 3 is the extra logit-lens 'final' layer


@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    monkeypatch.setattr(C, "LAYER", MOCK_LAYER)
    monkeypatch.setattr(C, "HIDDEN_STATES_INDEX", MOCK_LAYER + 1)
    monkeypatch.setattr(C, "D_MODEL", MOCK_D)
    monkeypatch.setattr(C, "N_LAYERS", 4)
    monkeypatch.setattr(Y, "OLENS_GRID", (1, 3))
    yield


@pytest.fixture(scope="module")
def target():
    return M.Target(model=tiny_model(), tokenizer=FakeTok(), device="cpu", model_id="MOCK/tiny", revision="mock", model_class="Qwen3_5ForCausalLM")


# ================================================================== (1) choice builder
def test_build_y1_choice_invariants():
    data = BY.build(BY.DEFAULT_SEED)
    items = data["items"]
    assert len(items) == 900 and items[0]["item_id"] == "xch-0301" and items[-1]["item_id"] == "xch-1200"
    assert items[0]["pair_id"] == "xch-p151" and items[-1]["pair_id"] == "xch-p600"
    assert data["meta"]["balance_checks"]["n_types"] >= 40 and data["meta"]["balance_checks"]["n_x3_pairs_excluded"] == 150
    # both orders per pair, X3 schema, prompt-only text from the frozen template
    by_pair = {}
    for it in items:
        by_pair.setdefault(it["pair_id"], []).append(it)
        assert set(it) >= {"item_id", "pair_id", "version", "family", "split", "template_id", "prompt_text", "render", "system", "primary",
                           "secondary", "target_answer_regex", "construction", "notes", "prompt_only_text"}
        assert it["prompt_only_text"] == C.PROMPT_ONLY_TEMPLATE.format(prompt_text=it["prompt_text"], question=it["primary"]["question"])
    assert len(by_pair) == 450 and all(sorted(p["version"] for p in v) == ["A", "B"] for v in by_pair.values())
    a, b = by_pair["xch-p151"]
    assert a["primary"]["candidates"] == b["primary"]["candidates"] and a["construction"]["options_in_prompt_order"] == b["construction"]["options_in_prompt_order"][::-1]
    # no overlap with the X3 option pairs; deterministic
    x3_pairs = {frozenset(p) for _, p in BY.x3_option_pairs()}
    assert len(x3_pairs) == 150 and not ({frozenset(it["primary"]["candidates"]) for it in items} & x3_pairs)
    assert BY.build(BY.DEFAULT_SEED)["meta"]["sha256_items"] == data["meta"]["sha256_items"]
    assert BY.build(1)["meta"]["sha256_items"] != data["meta"]["sha256_items"]
    # the union loader accepts the pair (schema + no overlap) and rejects a reused pair
    assert BY.validate(items, BY.x3_option_pairs())["n_pairs"] == 450
    with pytest.raises(AssertionError, match="repeats an X3 option pair"):
        BY.validate(items, [("fruit", tuple(items[0]["primary"]["candidates"]))] + BY.x3_option_pairs()[1:], 450)


def test_load_union_choice_rejects_overlap(tmp_path):
    x3_items = [x3_choice(1, "apple", "pear"), x3_choice(2, "red", "blue")]
    y1_items = [dict(x3_choice(301, "cat", "dog"), pair_id="xch-p151")]
    (tmp_path / "x3.json").write_text(json.dumps({"items": x3_items}))
    (tmp_path / "y1.json").write_text(json.dumps({"items": y1_items}))
    union, meta = Y.load_union_choice(tmp_path / "x3.json", tmp_path / "y1.json")
    assert [it["item_id"] for it in union] == ["xch-0001", "xch-0002", "xch-0301"] and meta["n_y1_choice"] == 1
    (tmp_path / "bad.json").write_text(json.dumps({"items": [x3_choice(302, "pear", "apple")]}))
    with pytest.raises(ValueError, match="reuses"):
        Y.load_union_choice(tmp_path / "x3.json", tmp_path / "bad.json")
    with pytest.raises(FileNotFoundError):
        Y.load_union_choice(tmp_path / "x3.json", tmp_path / "nope.json")


# ================================================================== (2) selection on a fixture
def _crow(iid, cands, actual, guess, src="y1_decode"):
    both = actual is not None and guess is not None
    return {"key": iid, "item_id": iid, "family": "choice", "actual": actual, "self_guess": guess, "candidates": cands, "first_listed": cands[0],
            "both_parsed": both, "disagree": bool(both and actual != guess), "source_rows": src}


def test_select_y1_union_and_flags(tmp_path):
    words = [("apple", "pear"), ("red", "blue"), ("cat", "dog"), ("tea", "coffee"), ("circle", "square"), ("Paris", "Rome"), ("oak", "pine"), ("ant", "bee")]
    cho = [x3_choice(i + 1, *w) for i, w in enumerate(words)]
    rows = [_crow("xch-0001", ["apple", "pear"], "pear", "apple", "x3_target"), _crow("xch-0002", ["red", "blue"], "red", "blue", "x3_target"),
            _crow("xch-0003", ["cat", "dog"], "dog", "cat"), _crow("xch-0004", ["tea", "coffee"], "tea", "tea"), _crow("xch-0005", ["circle", "square"], "square", "square"),
            _crow("xch-0006", ["Paris", "Rome"], "Paris", "Paris"), _crow("xch-0007", ["oak", "pine"], "oak", None), _crow("xch-0008", ["ant", "bee"], "bee", "bee")]
    puz_sel, _ = X3.select([{"key": "xpz-0001", "item_id": "xpz-0001", "family": "puzzle", "parsed": "C", "correct": "A", "k": 3, "is_coherent": True},
                            {"key": "xpz-0002", "item_id": "xpz-0002", "family": "puzzle", "parsed": "B", "correct": "B", "k": 3, "is_coherent": True}],
                           [x3_puzzle(1, 3, ["B", "D", "F", "A"]), x3_puzzle(2, 3, ["A", "C", "E", "B"])])
    sel, meta = Y.select_y1(rows + [{"key": "xpz-0001", "item_id": "xpz-0001", "family": "puzzle", "parsed": "C", "correct": "A", "k": 3, "is_coherent": True}],
                            cho, puz_sel)
    by = {s["item_id"]: s for s in sel}
    assert meta["counts"] == {"error": 1, "error_control": 1, "disagree": 3, "agree_control": 3}
    assert sorted(i for i, s in by.items() if s["set"] == "disagree") == ["xch-0001", "xch-0002", "xch-0003"]
    assert all(by[i]["set"] in ("error", "error_control") for i in ("xpz-0001", "xpz-0002"))  # X3 puzzles carried unchanged
    assert by["xpz-0001"]["primary"]["candidates"] == ["C", "A"]
    assert by["xch-0001"]["primary"]["candidates"] == ["pear", "apple"] and by["xch-0001"]["text_key"] == "apple"
    assert "xch-0007" not in by
    assert meta["underpowered"] == {"error": True, "disagree": True} and meta["min_disagree"] == Y.MIN_DISAGREE == 60 and "puzzle" not in meta
    # the X3 decode rows are copied into the Y1 target file once
    xt = tmp_path / "x3_target.jsonl"
    xt.write_text("\n".join(json.dumps(r) for r in rows[:2] + [{"key": "xpz-0001", "item_id": "xpz-0001", "family": "puzzle"}]) + "\n")
    yt = tmp_path / "y1_target.jsonl"
    assert Y.seed_from_x3(cho, target_path=yt, x3_target_path=xt) == 2
    assert Y.seed_from_x3(cho, target_path=yt, x3_target_path=xt) == 0
    copied = A.read_jsonl(yt)
    assert [r["key"] for r in copied] == ["xch-0001", "xch-0002"] and all(r["source_rows"] == "x3_target" for r in copied)
    p = X3.write_selected(tmp_path / "sel.json", sel, meta)
    m2, items2 = X3.load_selected(p)
    assert m2["counts"]["disagree"] == 3 and len(items2) == 8


# ================================================================== (3) sites / candidate positions
def test_parse_site_and_grid():
    assert Y.parse_site("46:0") == (46, "0") and Y.parse_site("44:last-3") == (44, "3") and Y.parse_site("48:candA") == (48, "candA")
    assert Y.parse_site("50:last") == (50, "0")
    for bad in ("46", "46:x", "46:candC"):
        with pytest.raises(ValueError):
            Y.parse_site(bad)
    assert Y.pos_labels(3) == ["0", "1", "2", "candA", "candB"]
    assert [Y.nearest_grid_layer(L, (44, 48, 52, 56, 60)) for L in (42, 46, 50, 58, 62)] == [44, 44, 48, 56, 60]
    # mock grid (1, 3): layer 2 ties -> the lower grid layer; the true layer is kept for the sensitivity arm; NLA has no layer
    assert Y.reader_layer("jlens", 46) == 46 and Y.reader_layer("olens", 2) == 1 and Y.reader_layer("olens", 3) == 3
    assert Y.reader_layer("olens_trueL", 2) == 2 and Y.reader_layer("nla", 46) is None


def test_find_candidate_positions():
    tok = FakeTok()
    ids = M.render_item(tok, "Pick one: apple or pear. One word.")
    fa = Y.find_candidate_positions(tok, ids, "apple")
    fb = Y.find_candidate_positions(tok, ids, "pear")
    text = tok.decode(ids)
    assert fa["n"] == 1 and tok.decode(ids[fa["pos"] - 4: fa["pos"] + 1]) == "apple" and fa["forms"] == [" apple"]
    assert fb["pos"] > fa["pos"] and tok.decode(ids[fb["pos"] - 3: fb["pos"] + 1]) == "pear" and " apple" in text
    assert Y.find_candidate_positions(tok, ids, "mango") == {"pos": -1, "all": [], "forms": [], "n": 0}
    pm = Y.item_positions(tok, ids, "apple", "pear", n_positions=3)
    assert pm["labels"] == ["0", "1", "2", "candA", "candB"] and pm["positions"][:3] == [len(ids) - 1, len(ids) - 2, len(ids) - 3]
    assert pm["positions"][3:] == [fa["pos"], fb["pos"]] and pm["cand"]["candA"]["pos"] == fa["pos"]
    # symbols: every occurrence recorded, the earliest is the cell
    ids2 = M.render_item(tok, "B -> D. D -> B. Start at B.")
    fs = Y.find_candidate_positions(tok, ids2, "B")
    assert fs["n"] == 3 and fs["pos"] == fs["all"][0] and tok.decode([ids2[fs["pos"]]]) == "B"


# ================================================================== (4) capture + logit lens on the MOCK
def selected_fixture():
    puz = X3.make_selected(x3_puzzle(1, 3, ["B", "D", "F", "A"]), "error", "C", "A", "A")
    puz2 = X3.make_selected(x3_puzzle(2, 3, ["A", "C", "E", "B"]), "error_control", "B", "C", "B")
    cho = X3.make_selected(x3_choice(1, "apple", "pear"), "disagree", "pear", "apple", "apple")
    cho["source"]["self_guess"] = "apple"
    cho2 = X3.make_selected(x3_choice(2, "tea", "coffee"), "agree_control", "tea", "coffee", "tea")
    cho2["source"]["self_guess"] = "tea"
    return [puz, puz2, cho, cho2]


def test_capture_shapes_positions_logitlens_resume(target, tmp_path):
    sel = selected_fixture()
    cd, cm, ll, led, log = tmp_path / "caps", tmp_path / "caps_meta.jsonl", tmp_path / "ll.jsonl", tmp_path / "c.jsonl", tmp_path / "log.md"
    n = Y.collect_captures(target, sel, layers=MOCK_LAYERS, n_positions=4, caps_dir=cd, caps_meta_path=cm, logitlens_path=ll, ledger_path=led, log_path=log,
                           extra={"frozen_x": False})
    assert n == 4 and all(Y.cap_path(it["item_id"], cd).exists() for it in sel)
    cap = Y.load_cap("xch-0001", cd)
    assert tuple(cap["acts"].shape) == (2, 6, MOCK_D) and cap["acts"].dtype == torch.bfloat16 and cap["layers"] == MOCK_LAYERS
    assert cap["labels"] == ["0", "1", "2", "3", "candA", "candB"] and cap["candidates"] == ["pear", "apple"]
    ids = M.render_item(target.tokenizer, sel[2]["prompt_text"])
    assert cap["positions"][:4] == [len(ids) - 1 - k for k in range(4)] and cap["n_tokens"] == len(ids)
    pa, pb = cap["positions"][4], cap["positions"][5]
    assert pa > 0 and pb > 0 and pa > pb  # 'pear' (actual, listed second) is read after 'apple'
    assert cap["prompt_ids_sha256"] == C.sha256_ids(ids)
    # the cell vectors equal a direct single-position capture of the same block output (bf16 rounding)
    for L in MOCK_LAYERS:
        ref = M.capture(target.model, ids, [L], [len(ids) - 1, pa])[L]
        assert torch.allclose(Y.cell_vector(cap, L, "0"), ref[0], atol=2e-2, rtol=2e-2)
        assert torch.allclose(Y.cell_vector(cap, L, "candA"), ref[1], atol=2e-2, rtol=2e-2)
    with pytest.raises(KeyError):
        Y.cell_vector(cap, 3, "0")
    # logit-lens rows: one per item, margins at the grid layers + the final block, form recorded, lp difference consistent
    rows = {r["item_id"]: r for r in A.read_jsonl(ll)}
    assert set(rows) == {it["item_id"] for it in sel}
    r = rows["xpz-0001"]
    assert r["unscorable"] is False and r["form"] == "bare" and set(r["margins"]) == {"1", "2", "3"} and r["final_layer"] == 3
    for L in r["margins"]:
        assert abs(r["margins"][L] - (r["lp_actual"][L] - r["lp_other"][L])) < 1e-5
    # the final-block logit lens equals the model's own next-token log-odds
    with torch.no_grad():
        lp = torch.log_softmax(target.model(torch.tensor([ids]), use_cache=False).logits[0, -1].float(), -1)
    rc = rows["xch-0001"]
    assert abs(rc["margins"]["3"] - float(lp[rc["first_token_actual"]] - lp[rc["first_token_other"]])) < 5e-2
    # resumable; a different render is an error
    assert Y.collect_captures(target, sel, layers=MOCK_LAYERS, n_positions=4, caps_dir=cd, caps_meta_path=cm, logitlens_path=ll, ledger_path=led, log_path=log) == 0
    drift = [dict(sel[0], prompt_text="changed")]
    with pytest.raises(RuntimeError, match="different render"):
        Y.collect_captures(target, drift, layers=MOCK_LAYERS, n_positions=4, caps_dir=cd, caps_meta_path=cm, logitlens_path=ll, ledger_path=led, log_path=log)
    assert {x["step"] for x in A.read_jsonl(led)} == {"y1_capture"}
    meta_rows = A.read_jsonl(cm)
    assert len(meta_rows) == 4 and "acts" not in meta_rows[0] and meta_rows[0]["acts_shape"] == [2, 6, MOCK_D]
    # a candidate absent from the prompt -> -1 and zeros, cell_vector None
    odd = X3.make_selected(x3_choice(9, "apple", "pear"), "disagree", "mango", "apple", "apple")
    cap9, ll9 = Y.capture_item(target, odd, MOCK_LAYERS, 2)
    assert cap9["positions"][2] == -1 and Y.cell_vector(cap9, 1, "candA") is None and Y.cell_vector(cap9, 1, "candB") is not None
    assert float(cap9["acts"][:, 2].abs().sum()) == 0.0 and ll9["unscorable"] is False


# ================================================================== (5) reread rows on the MOCK readers
def test_reread_rows_three_readers(target, tmp_path):
    sel = selected_fixture()
    cd = tmp_path / "caps"
    Y.collect_captures(target, sel, layers=MOCK_LAYERS, n_positions=3, caps_dir=cd, caps_meta_path=tmp_path / "m.jsonl", logitlens_path=tmp_path / "ll.jsonl",
                       ledger_path=tmp_path / "c.jsonl", log_path=tmp_path / "log.md")
    lo, led, log = tmp_path / "y1_lo.jsonl", tmp_path / "c.jsonl", tmp_path / "log.md"
    torch.manual_seed(1)
    J = {L: torch.eye(MOCK_D) + torch.randn(MOCK_D, MOCK_D) / 10 for L in MOCK_LAYERS}
    jl = R.JLensReader().bind_tensors(J, M.unembed_weight(target.model), target.tokenizer)
    ol = R.OLensReader(max_new_tokens=4)
    ol.target = target
    tok = FakeTok()
    nla = R.NLAReader(max_new_tokens=4).attach(tiny_model(3), tok, mock_meta(tok), device="cpu")
    n_j = Y.collect_lo_site(jl, sel, 2, "0", lo_path=lo, ledger_path=led, log_path=log, caps_dir=cd, batch=4, extra={"frozen_x": False})
    n_o = Y.collect_lo_site(ol, sel, 2, "0", reader_name="olens", lo_path=lo, ledger_path=led, log_path=log, caps_dir=cd, batch=4)
    n_t = Y.collect_lo_site(ol, sel, 2, "candA", reader_name="olens_trueL", lo_path=lo, ledger_path=led, log_path=log, caps_dir=cd, batch=4)
    n_n = Y.collect_lo_site(nla, sel, 2, "0", lo_path=lo, ledger_path=led, log_path=log, caps_dir=cd, batch=4)
    assert n_j == n_o == n_n == 4 + 4  # 4 item rows + 4 mean-state rows (one per set)
    assert n_t == 4 + 3  # xpz-0001's actual 'C' is off-trace: candA absent -> unscorable row, no mean row for the (empty) error set
    rows = A.read_jsonl(lo)
    items_rows = [r for r in rows if r.get("condition") != "mean_state"]
    mean_rows = [r for r in rows if r.get("condition") == "mean_state"]
    assert len(items_rows) == 16 and len(mean_rows) == 15
    assert {r["key"] for r in items_rows} == {f"{rd}|{site}|{it['item_id']}" for rd, site in (("jlens", "2:0"), ("olens", "2:0"), ("olens_trueL", "2:candA"), ("nla", "2:0"))
                                             for it in sel}
    for r in items_rows:
        for k in ("key", "reader", "site", "layer", "position", "layer_used", "layer_role", "item_id", "family", "set", "cand_actual", "cand_other", "text_key",
                  "lo_actual", "lp_actual", "lp_other", "favours_actual", "unscorable", "frozen_code_sha256"):
            assert k in r, k
        if r["lo_actual"] is not None:
            assert abs(r["lo_actual"] - (r["lp_actual"] - r["lp_other"])) < 1e-5 and r["favours_actual"] == (r["lo_actual"] > 0)
    by = {(r["reader"], r["item_id"]): r for r in items_rows}
    assert by[("jlens", "xpz-0001")]["layer_used"] == 2 and by[("jlens", "xpz-0001")]["unscorable"] is False and by[("jlens", "xpz-0001")]["cand_actual"] == "C"
    assert by[("jlens", "xch-0001")]["unscorable"] is True and by[("jlens", "xch-0001")]["lo_actual"] is None  # multi-token words: no single-token variant
    assert by[("olens", "xpz-0001")]["layer_used"] == 1 and by[("olens", "xpz-0001")]["layer_role"] == "nearest_grid" and by[("olens", "xpz-0001")]["layer_in_prompt"] == 1
    assert by[("olens_trueL", "xpz-0001")]["layer_used"] == 2 and by[("olens_trueL", "xpz-0001")]["position"] == "candA"
    assert by[("olens_trueL", "xpz-0001")]["unscorable"] is True and "absent" in by[("olens_trueL", "xpz-0001")]["reason"]
    assert by[("olens_trueL", "xpz-0002")]["unscorable"] is False and by[("olens_trueL", "xpz-0002")]["layer_role"] == "true_layer_sensitivity"
    assert by[("nla", "xpz-0001")]["layer_used"] is None and by[("nla", "xpz-0001")]["layer_role"] == "transfer_from_L42"
    for m in mean_rows:
        assert m["key"] == f"{m['reader']}|{m['site']}|mean|{m['set']}" and m["n_states_in_mean"] == 1 and m["band"] == 1.0
        if m["mean_lo"] is not None:
            assert m["within_band"] == (abs(m["mean_lo"]) <= 1.0)
    # resumable; ledger steps
    assert Y.collect_lo_site(jl, sel, 2, "0", lo_path=lo, ledger_path=led, log_path=log, caps_dir=cd) == 0
    assert {"y1_lo_jlens", "y1_lo_olens", "y1_lo_olens_trueL", "y1_lo_nla", "y1_mean_lo_jlens", "y1_capture"} <= {x["step"] for x in A.read_jsonl(led)}
    # an absent position yields an unscorable row rather than a crash
    odd = X3.make_selected(x3_choice(9, "apple", "pear"), "disagree", "mango", "apple", "apple")
    cap9, _ = Y.capture_item(target, odd, MOCK_LAYERS, 3)
    torch.save(cap9, Y.cap_path("xch-0009", cd))
    assert Y.collect_lo_site(jl, [odd], 2, "candA", lo_path=lo, ledger_path=led, log_path=log, caps_dir=cd) == 1
    r9 = [r for r in A.read_jsonl(lo) if r["key"] == "jlens|2:candA|xch-0009"][0]
    assert r9["unscorable"] is True and "absent" in r9["reason"]


# ================================================================== (6) analyze end to end on a synthetic cache
SYMS = list("ABCDEFGH")
WORDS = ["apple", "pear", "cat", "dog", "tea", "coffee", "oak", "pine"]


def synthetic_cache(tmp_path: Path, *, n_error=48, n_control=24, n_dis=40, n_agree=40, d=24, planted=(2, "1"), gain=4.0, seed=0,
                    layers=(1, 2), labels=("0", "1", "2", "candA", "candB"), ll_sep_layer=2):
    """Items + bf16 captures with the actual answer linearly planted at ONE cell (None = nowhere); logit-lens rows separating
    from ``ll_sep_layer`` on. Returns (selected.json, caps_dir, logitlens.jsonl, items)."""
    rng = np.random.default_rng(seed)
    emb = {s: rng.standard_normal(d) for s in SYMS}
    u_first = rng.standard_normal(d)
    items, k = [], 0
    for set_, n in (("error", n_error), ("error_control", n_control), ("disagree", n_dis), ("agree_control", n_agree)):
        for j in range(n):
            k += 1
            if set_ in ("error", "error_control"):
                a, b = rng.choice(8, 2, replace=False)
                actual, other = SYMS[a], SYMS[b]
                it = {"item_id": f"xpz-{k:04d}", "family": "puzzle", "set": set_, "primary": {"candidates": [actual, other], "answer": actual},
                      "text_key": other if set_ == "error" else actual, "source": {"correct": other if set_ == "error" else actual, "k": 3}}
                sig = emb[actual]
            else:
                w = int(rng.integers(0, 4))
                opts = [WORDS[2 * w], WORDS[2 * w + 1]]
                actual = opts[int(rng.integers(0, 2))]
                other = opts[1 - opts.index(actual)]
                it = {"item_id": f"xch-{k:04d}", "family": "choice", "set": set_, "primary": {"candidates": [actual, other], "answer": actual},
                      "text_key": other if set_ == "disagree" else actual, "source": {"options_listed": opts, "first_listed": opts[0], "self_guess": other if set_ == "disagree" else actual}}
                sig = u_first * (1.0 if actual == opts[0] else -1.0)
            it.update(pair_id=it["item_id"], version="A", split="test", prompt_text="p", render="chat", system=None)
            items.append(it)
            acts = rng.standard_normal((len(layers), len(labels), d))
            if planted is not None:
                acts[list(layers).index(planted[0]), list(labels).index(planted[1])] += gain * sig
            positions = [20 - int(p) for p in labels[:-2]] + [5, 7]
            if j % 7 == 0:  # some items miss candB
                positions[-1] = -1
                acts[:, -1] = 0.0
            cap = {"item_id": it["item_id"], "family": it["family"], "set": set_, "layers": list(layers), "labels": list(labels), "positions": positions,
                   "n_tokens": 21, "candidates": [actual, other], "prompt_ids_sha256": "x", "acts": torch.tensor(acts, dtype=torch.bfloat16)}
            (tmp_path / "caps").mkdir(exist_ok=True)
            torch.save(cap, tmp_path / "caps" / f"{it['item_id']}.pt")
    ll = []
    for it in items:
        margins = {str(L): (2.0 if L >= ll_sep_layer else -0.5) + rng.normal(0, 0.3) for L in list(layers) + [3]}
        ll.append({"key": it["item_id"], "item_id": it["item_id"], "set": it["set"], "unscorable": False, "form": "bare", "layers": list(layers), "final_layer": 3,
                   "margins": margins, "lp_actual": {L: m for L, m in margins.items()}, "lp_other": {L: 0.0 for L in margins}})
    (tmp_path / "ll.jsonl").write_text("\n".join(json.dumps(r) for r in ll) + "\n")
    (tmp_path / "sel.json").write_text(json.dumps({"meta": {"counts": {}}, "items": items}))
    return tmp_path / "sel.json", tmp_path / "caps", tmp_path / "ll.jsonl", items


def _lo_rows(items, site, favour: dict, gate_ok: dict):
    rows = []
    for rd, p in favour.items():
        rng = np.random.default_rng(hash(rd) % 1000)
        for it in items:
            v = (abs(rng.standard_normal()) + 0.1) * (1 if rng.random() < p else -1)
            rows.append({"key": f"{rd}|{site}|{it['item_id']}", "reader": rd, "site": site, "layer_used": 2, "layer_role": "x", "item_id": it["item_id"], "set": it["set"],
                         "lo_actual": float(v), "favours_actual": v > 0, "unscorable": False})
        for s in YA.SETS:
            m = 0.2 if gate_ok[rd] else 3.0
            rows.append({"key": f"{rd}|{site}|mean|{s}", "reader": rd, "site": site, "condition": "mean_state", "set": s, "mean_lo": m, "within_band": abs(m) <= 1.0,
                         "n_states_in_mean": 10, "layer_used": 2, "layer_role": "x"})
    return rows


def test_analyze_finds_planted_site_and_reread(tmp_path):
    selp, cd, llp, items = synthetic_cache(tmp_path, planted=(2, "1"))
    lop = tmp_path / "lo.jsonl"
    lop.write_text("\n".join(json.dumps(r) for r in _lo_rows(items, "2:1", {"jlens": 0.95, "olens": 0.55, "nla": 0.95}, {"jlens": True, "olens": True, "nla": False})) + "\n")
    out = tmp_path / "out"
    s = YA.main(["--selected", str(selp), "--caps-dir", str(cd), "--logitlens", str(llp), "--lo", str(lop), "--out", str(out), "--allow-unfrozen",
                 "--n-perm", "2", "--n-boot", "100", "--frozen-config", str(tmp_path / "none.json")])
    for f in ("summary.json", "sweep_error.csv", "sweep_disagree.csv", "logitlens.csv", "fig_main.png", "reread.csv", "fig_reread.png"):
        assert (out / f).exists(), f
    assert s["frozen"] is False and s["counts"] == {"error": 48, "error_control": 24, "disagree": 40, "agree_control": 40} and s["n_captures"] == 152
    assert s["grid"] == {"layers": [1, 2], "labels": ["0", "1", "2", "candA", "candB"]} and s["candidate_positions_absent"]["candB"] > 0
    assert s["S_star"]["site"] == "2:1" and s["K7"]["killed"] is False and s["E10"]["disagree"]["S_star"]["site"] == "2:1"
    st = s["S_star"]
    assert st["p"] >= 0.75 and st["boot_lo"] > st["majority_rate"] and st["p"] > st["perm_p95"] and st["ceiling_p"] > 0.7
    assert st["logit_lens_separates"] is True and st["logit_lens_frac_pos_error"] > 0.9
    cells = s["E10"]["error"]["cells"]
    assert len(cells) == 10 and cells["2:1"]["passes"] and not cells["1:1"]["passes"] and cells["2:1"]["balanced_accuracy_all"] > 0.7
    assert cells["2:candB"]["n"] < 48  # items without a candB position are excluded from that cell
    ll = s["logit_lens"]["by_set"]["error"]
    assert ll["1"]["frac_pos"] < 0.2 and ll["2"]["frac_pos"] > 0.9 and ll["3"]["is_final_layer"] is True and ll["2"]["is_final_layer"] is False
    with (out / "sweep_error.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 10 and {r["set"] for r in rows} == {"error"} and rows[0]["control_set"] == "error_control" and "perm_p95" in rows[0]
    with (out / "logitlens.csv").open() as fh:
        assert len(list(csv.DictReader(fh))) == 4 * 3
    # E11
    e11 = s["E11"]
    assert e11["site"] == "2:1" and e11["probe_at_site"]["error"]["p"] == cells["2:1"]["rate"]
    assert e11["readers"]["jlens"]["verdict"] == "reads_the_model_at_S*" and e11["readers"]["jlens"]["by_set"]["error"]["within_10pp_of_probe"] is True
    assert e11["readers"]["olens"]["verdict"] == "no_evidence"
    assert e11["readers"]["nla"]["verdict"] == "off-training-layer, failed gate" and e11["readers"]["nla"]["gate_passed"] is False
    assert e11["readers"]["jlens"]["e3_gate"]["error"]["within_band"] is True
    with (out / "reread.csv").open() as fh:
        rr = list(csv.DictReader(fh))
    assert len(rr) == 3 * 4 and {r["reader"] for r in rr} == {"jlens", "olens", "nla"} and "e3_within_band" in rr[0]
    # --reread-only reuses the summary; --site overrides
    s2 = YA.main(["--selected", str(selp), "--lo", str(lop), "--out", str(out), "--allow-unfrozen", "--reread-only", "--site", "2:last-1", "--no-fig",
                  "--frozen-config", str(tmp_path / "none.json"), "--n-boot", "50"])
    assert s2["E11"]["site"] == "2:1" and s2["S_star"]["site"] == "2:1"


def test_analyze_k7_when_no_signal(tmp_path):
    selp, cd, llp, _ = synthetic_cache(tmp_path, planted=None, n_error=30, n_control=15, n_dis=24, n_agree=24, ll_sep_layer=3)
    out = tmp_path / "out"
    s = YA.main(["--selected", str(selp), "--caps-dir", str(cd), "--logitlens", str(llp), "--out", str(out), "--allow-unfrozen", "--n-perm", "2",
                 "--n-boot", "50", "--no-fig", "--frozen-config", str(tmp_path / "none.json"), "--layers", "1,2", "--positions", "0,1,candA"])
    assert s["S_star"] is None and s["K7"]["killed"] is True and "not linearly present" in s["K7"]["statement"]
    assert s["E10"]["error"]["S_star"] is None and s["E10"]["error"]["n_passing"] == 0 and s["grid"]["labels"] == ["0", "1", "candA"]
    assert s["underpowered"] == {"error": False, "disagree": True} and "E11" not in s and not (out / "fig_main.png").exists()
    assert s["logit_lens"]["by_set"]["error"]["2"]["frac_pos"] < 0.2
    # refuses a test summary without the X freeze
    with pytest.raises(Exception):
        YA.main(["--selected", str(selp), "--caps-dir", str(cd), "--out", str(tmp_path / "o2"), "--frozen-config", str(tmp_path / "nofreeze.json")])


def test_probe_helpers():
    assert YA.balanced_accuracy(["A", "B", "B", "B"], ["A", "A", "B", "B"]) == 0.75
    items = {f"i{k}": {"set": "error", "primary": {"candidates": ["A", "B"]}} for k in range(3)}
    items["i3"] = {"set": "error_control", "primary": {"candidates": ["B", "A"]}}
    mr = YA.majority_rates(items, sorted(items), "puzzle")
    assert mr == {"error": 1.0, "error_control": 0.0}  # A is the more frequent actual symbol
    cells = {(2, "0"): {"by_set": {"error": {"passes": True, "p": 0.8}}}, (2, "candA"): {"by_set": {"error": {"passes": True, "p": 0.9}}},
             (1, "3"): {"by_set": {"error": {"passes": True, "p": 0.76}}}, (1, "0"): {"by_set": {"error": {"passes": False, "p": 0.5}}}}
    labels = ["0", "1", "2", "3", "candA", "candB"]
    assert YA.choose_sstar(cells, "error", labels)["site"] == "1:3"
    assert YA.choose_sstar(cells, "error", labels, max_layer=0) is None
    del cells[(1, "3")]
    assert YA.choose_sstar(cells, "error", labels)["site"] == "2:0"  # latest position first within a layer


# ================================================================== (7) sweep robustness: exclusions, failed cells, resume
def _small_cache(tmp_path, planted=(2, "1")):
    selp, cd, llp, items = synthetic_cache(tmp_path, planted=planted, n_error=30, n_control=15, n_dis=24, n_agree=24, labels=("0", "1", "candA", "candB"))
    _, its = YA.load_selected(selp)
    caps, missing = YA.load_caps(its, cd)
    assert not missing
    return selp, cd, llp, its, caps


def _sweep(its, caps, ckpt, **kw):
    args = {"n_perm": 1, "n_boot": 20, "seed": 0, "n_folds": 5, "jobs": 1, "ckpt_path": ckpt}
    args.update(kw)
    return YA.sweep(its, caps, [1, 2], ["0", "1", "candA", "candB"], **args)


def test_sweep_excludes_absent_and_nonfinite_items(tmp_path):
    selp, cd, llp, its, caps = _small_cache(tmp_path)
    # plant a NaN and an inf into two puzzle items at cell (2, "0") only
    for iid, bad in (("xpz-0002", float("nan")), ("xpz-0003", float("inf"))):
        cap = caps[iid]
        cap["acts"][cap["layers"].index(2), cap["labels"].index("0"), 3] = bad
        torch.save(cap, cd / f"{iid}.pt")
    caps, _ = YA.load_caps(its, cd)
    X, kept, excl = YA.cell_matrix(caps, sorted(i for i in caps if its[i]["family"] == "puzzle"), 2, "0")
    assert excl == {"absent": 0, "nonfinite": 2} and len(kept) == 43 and "xpz-0002" not in kept and np.isfinite(X).all()
    X, kept, excl = YA.cell_matrix(caps, sorted(i for i in caps if its[i]["family"] == "puzzle"), 2, "candB")
    assert excl == {"absent": 8, "nonfinite": 0} and len(kept) == 37  # j % 7 == 0 items miss candB: 5 of 30 + 3 of 15
    res = _sweep(its, caps, tmp_path / "cells.jsonl")
    puz = res["puzzle"]
    assert all(r["status"] == "ok" for fam in res.values() for r in fam.values())
    assert puz[(2, "0")]["n_excluded"] == 2 and puz[(2, "0")]["n_excluded_nonfinite"] == 2 and puz[(2, "0")]["n_items"] == 43
    assert puz[(2, "candB")]["n_excluded"] == 8 and puz[(2, "candB")]["n_excluded_absent"] == 8 and puz[(2, "candB")]["n_items"] == 37
    assert puz[(1, "0")]["n_excluded"] == 0 and puz[(1, "0")]["n_items"] == 45 and res["choice"][(2, "candB")]["n_excluded_absent"] == 8  # 4 of 24 + 4 of 24
    assert puz[(2, "1")]["by_set"]["error"]["passes"] and not puz[(2, "1")]["retried"]
    rows = YA.sweep_rows(res, ["0", "1", "candA", "candB"])
    by = {(r["layer"], r["position"]): r for r in rows["error"]}
    assert by[(2, "0")]["n_excluded"] == 2 and by[(2, "candB")]["n_excluded_absent"] == 8 and by[(2, "0")]["status"] == "ok" and by[(2, "0")]["error"] is None
    # end to end: the csv and summary carry n_excluded, the planted site is still found
    out = tmp_path / "out"
    s = YA.main(["--selected", str(selp), "--caps-dir", str(cd), "--logitlens", str(llp), "--out", str(out), "--allow-unfrozen", "--n-perm", "1",
                 "--n-boot", "20", "--no-fig", "--frozen-config", str(tmp_path / "none.json"), "--positions", "0,1,candA,candB"])
    assert s["S_star"]["site"] == "2:1" and s["E10"]["error"]["cells"]["2:0"]["n_excluded_nonfinite"] == 2 and s["E10"]["error"]["cells"]["2:candB"]["n_excluded_absent"] == 8
    assert s["E10"]["error"]["n_failed"] == 0 and s["E10"]["error"]["n_excluded_total"] == 2 + 2 * 8
    with (out / "sweep_error.csv").open() as fh:
        rows = {(int(r["layer"]), r["position"]): r for r in csv.DictReader(fh)}
    assert rows[(2, "0")]["n_excluded"] == "2" and rows[(2, "candB")]["n_excluded_absent"] == "8" and rows[(1, "1")]["n_excluded"] == "0"
    assert (out / "sweep_cells.jsonl").exists() and len((out / "sweep_cells.jsonl").read_text().splitlines()) == 16


def test_sweep_failed_cell_does_not_abort_and_retry_once(tmp_path, monkeypatch):
    selp, cd, llp, its, caps = _small_cache(tmp_path)
    orig = YA.F.cv_probe
    calls = {"n": 0}

    def always_fail(*a, **k):
        calls["n"] += 1
        raise np.linalg.LinAlgError("SVD did not converge")

    monkeypatch.setattr(YA.F, "cv_probe", always_fail)
    res = _sweep(its, caps, tmp_path / "fail.jsonl")
    cells = [r for fam in res.values() for r in fam.values()]
    assert len(cells) == 16 and all(r["status"] == "failed" for r in cells) and calls["n"] == 32  # one retry per cell
    assert all(r["retried"] and "LinAlgError" in r["error"] and "SVD did not converge" in r["retry_reason"] and r["by_set"] == {} for r in cells)
    assert all(r["n_excluded"] is not None for r in cells)
    rows = YA.sweep_rows(res, ["0", "1", "candA", "candB"])
    assert all(r["status"] == "failed" and r["passes"] is None and "LinAlgError" in r["error"] for r in rows["error"])
    assert YA.choose_sstar(res["puzzle"], "error", ["0", "1", "candA", "candB"]) is None
    # the summary/figure path survives an all-failed sweep (-> K7) and records the failed cells
    out = tmp_path / "out_fail"
    s = YA.main(["--selected", str(selp), "--caps-dir", str(cd), "--logitlens", str(llp), "--out", str(out), "--allow-unfrozen", "--n-perm", "1",
                 "--n-boot", "20", "--frozen-config", str(tmp_path / "none.json"), "--positions", "0,1,candA,candB"])
    assert s["K7"]["killed"] is True and s["E10"]["error"]["n_failed"] == 8 and s["E10"]["error"]["failed_cells"] == sorted(f"{L}:{P}" for L in (1, 2) for P in ("0", "1", "candA", "candB"))
    assert s["E10"]["error"]["cells"]["2:1"]["status"] == "failed" and (out / "fig_main.png").exists()
    # the first call fails, the jittered retry succeeds: the cell is ok, flagged retried, and the planted site still passes
    flaky = {"n": 0}

    def fail_once_per_cell(*a, **k):
        flaky["n"] += 1
        if flaky["n"] % 2 == 1:
            raise ValueError("array must not contain infs or NaNs")
        return orig(*a, **k)

    monkeypatch.setattr(YA.F, "cv_probe", fail_once_per_cell)
    res = _sweep(its, caps, tmp_path / "flaky.jsonl")
    cells = [r for fam in res.values() for r in fam.values()]
    assert flaky["n"] == 32 and all(r["status"] == "ok" and r["retried"] and "ValueError" in r["retry_reason"] for r in cells)
    assert res["puzzle"][(2, "1")]["by_set"]["error"]["passes"] and not res["puzzle"][(1, "1")]["by_set"]["error"]["passes"]
    # a non-numerical exception inside the cell is recorded as failed too (never aborts the sweep)
    monkeypatch.setattr(YA, "probe_cell", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    res = _sweep(its, caps, tmp_path / "boom.jsonl")
    assert all(r["status"] == "failed" and r["error"] == "RuntimeError: boom" for fam in res.values() for r in fam.values())


def test_sweep_resume_skips_done_cells(tmp_path, monkeypatch):
    selp, cd, llp, its, caps = _small_cache(tmp_path)
    ckpt = tmp_path / "cells.jsonl"
    res1 = _sweep(its, caps, ckpt)
    lines = [json.loads(l) for l in ckpt.read_text().splitlines()]
    assert len(lines) == 16 and {(l["family"], l["layer"], l["position"]) for l in lines} == {(f, L, P) for f in ("puzzle", "choice") for L in (1, 2) for P in ("0", "1", "candA", "candB")}
    assert all(l["params"] == {"n_perm": 1, "n_boot": 20, "seed": 0, "n_folds": 5} for l in lines)
    # a partial checkpoint: drop 5 lines, rerun -> only those 5 cells are computed, the rest come from the file unchanged
    kept, dropped = lines[:11], lines[11:]
    ckpt.write_text("".join(json.dumps(l) + "\n" for l in kept))
    computed = []
    orig = YA.probe_cell

    def spy(X, items, ids, family, **kw):
        computed.append(family)
        return orig(X, items, ids, family, **kw)

    monkeypatch.setattr(YA, "probe_cell", spy)
    res2 = _sweep(its, caps, ckpt)
    assert len(computed) == 5 and len(ckpt.read_text().splitlines()) == 16
    for fam in res1:
        assert set(res1[fam]) == set(res2[fam])
        for cell in res1[fam]:
            assert res1[fam][cell]["by_set"] == res2[fam][cell]["by_set"] and res1[fam][cell]["n_excluded"] == res2[fam][cell]["n_excluded"]
    # a complete checkpoint: nothing is computed
    computed.clear()
    res3 = _sweep(its, caps, ckpt)
    assert computed == [] and {k: v["by_set"] for k, v in res3["puzzle"].items()} == {k: v["by_set"] for k, v in res1["puzzle"].items()}
    # other sweep parameters do not match the checkpoint: everything is recomputed (and appended)
    computed.clear()
    _sweep(its, caps, ckpt, n_perm=2)
    assert len(computed) == 16 and len(ckpt.read_text().splitlines()) == 32
    # end to end through main(): a second run with the same parameters reuses <out>/sweep_cells.jsonl
    out = tmp_path / "out"
    cli = ["--selected", str(selp), "--caps-dir", str(cd), "--logitlens", str(llp), "--out", str(out), "--allow-unfrozen", "--n-perm", "1", "--n-boot", "20",
           "--no-fig", "--frozen-config", str(tmp_path / "none.json"), "--positions", "0,1,candA,candB"]
    s1 = YA.main(cli)
    computed.clear()
    s2 = YA.main(cli)
    assert computed == [] and s1["S_star"]["site"] == s2["S_star"]["site"] == "2:1" and s1["E10"] == s2["E10"]
    assert len((out / "sweep_cells.jsonl").read_text().splitlines()) == 16


def test_zz_results_cache_dataset_untouched():
    assert sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*")) == RESULTS_SNAPSHOT
    cache = sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None
    assert cache == CACHE_SNAPSHOT
    assert sorted(str(p) for p in (REPO / "projects" / "g_agreement" / "dataset").glob("*")) == DATASET_SNAPSHOT
