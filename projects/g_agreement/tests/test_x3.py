"""X3 (BRIEF_X.md) tests, CPU only: symbol / choice parsing, the deterministic selection on a fixture of
6 puzzle + 6 choice candidates (sets, size matching, candidate assignment), the collector mechanics on
the tiny MOCK model (decodes, resumability, state capture, LO rows for all three readers), and the
analysis end to end on synthetic LO rows + random states (E8 verdicts, E9 probe, prompt-only rate,
K6, outputs). Every path is a tmp_path; results/ and cache/ are asserted untouched.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_x3.py -q``
"""

from __future__ import annotations

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
from projects.g_agreement.core import scoring_lo as LO  # noqa: E402
from projects.g_agreement.core import states as S  # noqa: E402
from projects.g_agreement.tests.test_readers_mock import MOCK_D, MOCK_LAYER, FakeTok, mock_meta, tiny_model  # noqa: E402
from projects.g_agreement.x3_floor import analyze as X3A  # noqa: E402
from projects.g_agreement.x3_floor import collect as X3  # noqa: E402

RESULTS_SNAPSHOT = sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*"))
CACHE_SNAPSHOT = sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None
DATASET_SNAPSHOT = sorted(str(p) for p in (REPO / "projects" / "g_agreement" / "dataset").glob("*"))


@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    monkeypatch.setattr(C, "LAYER", MOCK_LAYER)
    monkeypatch.setattr(C, "HIDDEN_STATES_INDEX", MOCK_LAYER + 1)
    monkeypatch.setattr(C, "D_MODEL", MOCK_D)
    monkeypatch.setattr(C, "N_LAYERS", 4)
    monkeypatch.setattr(C, "DEV_EXTRA_LAYERS", ())
    yield


@pytest.fixture(scope="module")
def target():
    return M.Target(model=tiny_model(), tokenizer=FakeTok(), device="cpu", model_id="MOCK/tiny", revision="mock",
                    model_class="Qwen3_5ForCausalLM")


@pytest.fixture(scope="module")
def olens(target):
    r = R.OLensReader(max_new_tokens=4)
    r.target = target
    return r


@pytest.fixture(scope="module")
def nla():
    tok = FakeTok()
    return R.NLAReader(max_new_tokens=4).attach(tiny_model(3), tok, mock_meta(tok), device="cpu")


@pytest.fixture(scope="module")
def jlens(target):
    torch.manual_seed(1)
    J = {MOCK_LAYER: torch.eye(MOCK_D) + torch.randn(MOCK_D, MOCK_D) / 10}
    return R.JLensReader().bind_tensors(J, M.unembed_weight(target.model), target.tokenizer)


# ------------------------------------------------------------------ fixture: 6 puzzles + 6 choice items
def puzzle(i: int, k: int, trace: list[str]) -> dict:
    start, correct = trace[0], trace[-1]
    arrows = ", ".join(f"{a} -> {b}" for a, b in zip(trace, trace[1:]))
    return {"item_id": f"xpz-{i:04d}", "family": "puzzle", "split": "test", "template_id": "xpz-t1",
            "prompt_text": f"Arrows: {arrows}. Start at {start} and follow the arrows {k} times. Answer with the symbol only.",
            "primary": {"name": "puzzle_end", "question": f"Where do you end after {k} steps?", "correct": correct, "k": k,
                        "start": start, "trace": trace},
            "distractors": trace[:-1], "target_answer_regex": rf"(?<![A-Za-z]){correct}(?![A-Za-z])"}


def choice(i: int, o1: str, o2: str) -> dict:
    prompt = f"Choose either {o1} or {o2} and reply with that word only."
    return {"item_id": f"xch-{i:04d}", "family": "choice", "split": "test", "template_id": "choice-t1", "prompt_text": prompt,
            "primary": {"name": "model_choice", "question": "Which of the two options will the model choose?", "candidates": [o1, o2]},
            "prompt_only_text": C.PROMPT_ONLY_TEMPLATE.format(prompt_text=prompt, question="Which of the two options will the model choose?")}


def fixture_items() -> list[dict]:
    puz = [puzzle(1, 3, ["B", "D", "F", "A"]), puzzle(2, 3, ["A", "C", "E", "B"]), puzzle(3, 4, ["C", "A", "G", "H", "D"]),
           puzzle(4, 3, ["D", "G", "B", "C"]), puzzle(5, 4, ["E", "B", "A", "C", "F"]), puzzle(6, 4, ["F", "H", "D", "G", "E"])]
    cho = [choice(1, "apple", "pear"), choice(2, "red", "blue"), choice(3, "cat", "dog"),
           choice(4, "tea", "coffee"), choice(5, "circle", "square"), choice(6, "Paris", "Rome")]
    return puz + cho


def fixture_candidates_file(tmp_path: Path) -> Path:
    p = tmp_path / "items_x3_candidates.json"
    p.write_text(json.dumps({"meta": {"seed": 20261008, "n_puzzle": 6, "n_choice": 6}, "items": fixture_items()}))
    return p


def synthetic_target_rows() -> list[dict]:
    """Decode rows as collect_target would write them: 3 ERROR, 2 correct, 1 incoherent puzzle; 3 DISAGREE, 2 agree,
    1 unparsed choice. xpz-0004 (k=3, correct C) hits the 'most frequent wrong symbol == own correct' fallback."""
    def prow(iid, k, correct, parsed):
        return {"key": iid, "item_id": iid, "family": "puzzle", "answer_text": parsed or "??", "parsed": parsed, "correct": correct, "k": k,
                "is_coherent": parsed is not None, "is_error": parsed is not None and parsed != correct}

    def crow(iid, cands, actual, guess):
        both = actual is not None and guess is not None
        return {"key": iid, "item_id": iid, "family": "choice", "answer_text": actual or "?", "actual": actual, "self_guess_text": guess or "?",
                "self_guess": guess, "candidates": cands, "first_listed": cands[0], "both_parsed": both, "disagree": bool(both and actual != guess)}

    return [prow("xpz-0001", 3, "A", "C"), prow("xpz-0002", 3, "B", "C"), prow("xpz-0003", 4, "D", "E"),
            prow("xpz-0004", 3, "C", "C"), prow("xpz-0005", 4, "F", "F"), prow("xpz-0006", 4, "E", None),
            crow("xch-0001", ["apple", "pear"], "apple", "pear"), crow("xch-0002", ["red", "blue"], "blue", "red"),
            crow("xch-0003", ["cat", "dog"], "dog", "cat"), crow("xch-0004", ["tea", "coffee"], "tea", "tea"),
            crow("xch-0005", ["circle", "square"], "square", "square"), crow("xch-0006", ["Paris", "Rome"], "Paris", None)]


# ================================================================== parsing
@pytest.mark.parametrize("text,want,ev", [
    ("C", "C", "first word"), ("**F**.", "F", "first word"), ("  d", None, "no symbol"),
    ("The answer is G.", "G", "only symbol mentioned"), ("A", "A", "first word"),
    ("Start at B, then D, then F. The answer is F.", "F", "answer cue (last)"),
    ("B -> D -> F", "F", "answer cue (last)"), ("Symbols B and D are visited.", None, "ambiguous: ['B', 'D']"),
    ("a cat", None, "no symbol"), ("I", None, "no symbol"), ("", None, "no symbol"), (None, None, "no symbol"),
    ("Following the arrows: E, then C, so the result is C", "C", "answer cue (last)"),
])
def test_parse_symbol(text, want, ev):
    got, evidence = X3.parse_symbol(text)
    assert got == want and evidence == ev, (text, got, evidence)


def test_parse_choice_uses_choice_rule():
    assert X3.parse_choice("apple", ["apple", "pear"])[0] == "apple"
    assert X3.parse_choice("Pear.", ["apple", "pear"])[0] == "pear"
    assert X3.parse_choice("I would pick pear over apple", ["apple", "pear"])[0] is None  # both mentioned, neither first
    assert X3.parse_choice("Apple, not pear", ["apple", "pear"])[0] == "apple"  # first word rule
    assert X3.parse_choice("I will choose the dog.", ["cat", "dog"])[0] == "dog"  # only candidate mentioned
    assert X3.parse_choice("neither", ["cat", "dog"])[0] is None


# ================================================================== candidates loader
def test_load_candidates_schema_and_limit(tmp_path):
    p = fixture_candidates_file(tmp_path)
    meta, items = X3.load_candidates(p)
    assert meta["n_puzzle"] == 6 and len(items) == 12 and items[0]["item_id"] == "xpz-0001"
    _, lim = X3.load_candidates(p, limit=2)
    assert [it["item_id"] for it in lim] == ["xpz-0001", "xpz-0002", "xch-0001", "xch-0002"]
    bad = fixture_items()
    bad[0]["primary"]["correct"] = "Z"
    (tmp_path / "bad.json").write_text(json.dumps({"items": bad}))
    with pytest.raises(ValueError, match="primary.correct"):
        X3.load_candidates(tmp_path / "bad.json")
    bad = fixture_items()
    del bad[6]["prompt_only_text"]
    (tmp_path / "bad2.json").write_text(json.dumps({"items": bad}))
    with pytest.raises(ValueError, match="prompt_only_text"):
        X3.load_candidates(tmp_path / "bad2.json")
    with pytest.raises(FileNotFoundError):
        X3.load_candidates(tmp_path / "nope.json")


def test_pre_final_symbol_and_control_other():
    it = puzzle(9, 3, ["B", "D", "F", "A"])
    assert X3.pre_final_symbol(it) == "F"
    assert X3.control_other(it, "A", {3: {"C": 2}}, 3) == ("C", "most frequent wrong symbol at k=3")
    assert X3.control_other(it, "A", {3: {"A": 5, "G": 1}}, 3) == ("G", "most frequent wrong symbol at k=3")  # own correct skipped
    assert X3.control_other(it, "A", {3: {"A": 5}}, 3) == ("F", "(k-1)-trace symbol")
    assert X3.control_other(it, "A", {}, 4) == ("F", "(k-1)-trace symbol")  # no errors at this k
    bare = {"item_id": "x", "family": "puzzle", "prompt_text": "p", "primary": {"correct": "A", "k": 1}}
    assert X3.control_other(bare, "A", {}, 1) == ("B", "first symbol != correct")
    # ties resolved by symbol order; frequency wins over order
    assert X3.control_other(it, "A", {3: {"H": 1, "C": 1}}, 3)[0] == "C"
    assert X3.control_other(it, "A", {3: {"H": 2, "C": 1}}, 3)[0] == "H"


# ================================================================== selection
def test_select_sets_size_matching_and_candidates():
    items = fixture_items()
    sel, meta = X3.select(synthetic_target_rows(), items, seed=0)
    by = {s["item_id"]: s for s in sel}
    sets = {s: sorted(i for i, x in by.items() if x["set"] == s) for s in X3.SETS}
    assert sets["error"] == ["xpz-0001", "xpz-0002", "xpz-0003"]
    assert sets["error_control"] == ["xpz-0004", "xpz-0005"]  # pool has only 2 correct puzzles: size-matched to min
    assert sets["disagree"] == ["xch-0001", "xch-0002", "xch-0003"] and sets["agree_control"] == ["xch-0004", "xch-0005"]
    assert "xpz-0006" not in by and "xch-0006" not in by
    # candidates = (actual, other); text_key = the text-implied answer
    e = by["xpz-0001"]
    assert e["primary"]["candidates"] == ["C", "A"] and e["primary"]["answer"] == "C" and e["text_key"] == "A"
    assert e["source"]["correct"] == "A" and e["source"]["k"] == 3 and e["pair_id"] == e["item_id"] and e["split"] == "test"
    # control: candidates (correct, most frequent wrong at same k); xpz-0004's correct IS the frequent wrong symbol C at k=3
    c4 = by["xpz-0004"]
    assert c4["primary"]["candidates"] == ["C", "B"] and c4["source"]["other_rule"] == "(k-1)-trace symbol" and c4["text_key"] == "C"
    c5 = by["xpz-0005"]
    assert c5["primary"]["candidates"] == ["F", "E"] and c5["source"]["other_rule"] == "most frequent wrong symbol at k=4"
    d = by["xch-0002"]
    assert d["primary"]["candidates"] == ["blue", "red"] and d["text_key"] == "red" and d["source"]["first_listed"] == "red"
    a = by["xch-0004"]
    assert a["primary"]["candidates"] == ["tea", "coffee"] and a["text_key"] == "tea"
    assert meta["counts"] == {"error": 3, "error_control": 2, "disagree": 3, "agree_control": 2}
    assert meta["underpowered"] == {"error": True, "disagree": True}
    assert meta["puzzle"]["wrong_symbol_by_k"] == {"3": {"C": 2}, "4": {"E": 1}} and meta["puzzle"]["n_incoherent"] == 1
    assert meta["choice"]["n_unparsed"] == 1 and meta["choice"]["n_both_parsed"] == 5
    # deterministic
    sel2, _ = X3.select(synthetic_target_rows()[::-1], items, seed=0)
    assert [s["item_id"] for s in sel2] == [s["item_id"] for s in sel]


def test_select_size_matching_samples_by_seed():
    items = [puzzle(i, 3, ["A", "B", "C", "D"]) for i in range(1, 21)]
    rows = [{"key": it["item_id"], "item_id": it["item_id"], "family": "puzzle", "parsed": "D" if i > 5 else "B", "correct": "D", "k": 3,
             "is_coherent": True} for i, it in enumerate(items, start=1)]
    sel, meta = X3.select(rows, items, seed=0)
    ctrl = [s["item_id"] for s in sel if s["set"] == "error_control"]
    assert len(ctrl) == 5 and meta["counts"]["error"] == 5 and all(c > "xpz-0005" for c in ctrl) and ctrl == sorted(ctrl)
    sel1, _ = X3.select(rows, items, seed=1)
    assert [s["item_id"] for s in sel1 if s["set"] == "error_control"] != ctrl  # the seed decides the control draw
    assert all(s["primary"]["candidates"] == ["D", "B"] for s in sel if s["set"] == "error_control")


def test_write_and_load_selected(tmp_path):
    sel, meta = X3.select(synthetic_target_rows(), fixture_items())
    p = X3.write_selected(tmp_path / "sel.json", sel, meta)
    m2, items2 = X3.load_selected(p)
    assert len(items2) == 10 and m2["n_items"] == 10 and m2["sha256_items"] and m2["counts"]["error"] == 3
    with pytest.raises(ValueError):
        X3.make_selected(fixture_items()[0], "error", "A", "A", "A")


# ================================================================== collector on the MOCK model
def test_collect_target_and_lo_end_to_end(target, olens, nla, jlens, tmp_path):
    items = fixture_items()
    tp, led, log = tmp_path / "x3_target.jsonl", tmp_path / "c.jsonl", tmp_path / "log.md"
    n = X3.collect_target(target, items, target_path=tp, ledger_path=led, log_path=log, puzzle_cap=3, choice_cap=3, self_guess_cap=4,
                          extra={"candidates_sha256": "abc"})
    assert n == 12
    rows = A.read_jsonl(tp)
    assert len(rows) == 12 and [r["key"] for r in rows] == [it["item_id"] for it in items]
    p = rows[0]
    for k in ("answer_text", "parsed", "parse_evidence", "correct", "k", "is_coherent", "is_error", "finish_reason", "prompt_ids_sha256", "candidates_sha256"):
        assert k in p, k
    assert p["correct"] == "A" and p["n_new_tokens"] <= 3 and p["is_error"] == (p["parsed"] is not None and p["parsed"] != "A")
    c = rows[6]
    for k in ("actual", "self_guess", "self_guess_text", "both_parsed", "disagree", "candidates", "first_listed", "self_guess_prompt_sha256"):
        assert k in c, k
    assert c["candidates"] == ["apple", "pear"] and c["self_guess_n_new_tokens"] <= 4
    assert c["self_guess_prompt_ids_sha256"] != c["prompt_ids_sha256"]
    assert X3.collect_target(target, items, target_path=tp, ledger_path=led, log_path=log) == 0  # resumable
    steps = {x["step"] for x in A.read_jsonl(led)}
    assert {"x3_target_puzzle", "x3_target_choice", "x3_self_guess"} <= steps
    # selection from synthetic decode rows, capture, LO for the three readers
    sel, meta = X3.select(synthetic_target_rows(), items)
    sd = tmp_path / "states"
    S.ensure_states(target, sel, states_dir=sd, meta_path=tmp_path / "meta.jsonl", ledger_path=led, module="x3")
    assert all(S.state_path(s["item_id"], sd).exists() for s in sel)
    lo = tmp_path / "x3_lo.jsonl"
    for reader in (jlens, olens, nla):
        assert X3.collect_lo(reader, sel, lo_path=lo, ledger_path=led, log_path=log, states_dir=sd, batch=4, extra={"frozen_x": False}) == 10
    lrows = A.read_jsonl(lo)
    assert len(lrows) == 30 and {r["reader"] for r in lrows} == {"jlens", "olens", "nla"}
    assert {r["key"] for r in lrows} == {f"{rd}|{s['item_id']}" for rd in ("jlens", "olens", "nla") for s in sel}
    for r in lrows:
        for k in ("key", "reader", "item_id", "family", "set", "cand_actual", "cand_other", "text_key", "lo_actual", "lp_actual", "lp_other",
                  "favours_actual", "templates", "unscorable", "frozen_code_sha256", "frozen_x"):
            assert k in r, k
        if r["lo_actual"] is not None:
            assert abs(r["lo_actual"] - (r["lp_actual"] - r["lp_other"])) < 1e-5 and r["favours_actual"] == (r["lo_actual"] > 0)
    jl = {r["item_id"]: r for r in lrows if r["reader"] == "jlens"}
    assert jl["xpz-0001"]["unscorable"] is False and jl["xpz-0001"]["cand_actual"] == "C" and jl["xpz-0001"]["cand_other"] == "A"
    assert jl["xch-0001"]["unscorable"] is True and jl["xch-0001"]["lo_actual"] is None and jl["xch-0001"]["favours_actual"] is None
    nl = {r["item_id"]: r for r in lrows if r["reader"] == "nla"}
    assert nl["xpz-0001"]["templates"] == LO.templates_for("puzzle") and "symbol" in nl["xpz-0001"]["templates"][0]
    assert nl["xch-0001"]["templates"] == LO.templates_for("choice")
    assert X3.collect_lo(olens, sel, lo_path=lo, ledger_path=led, log_path=log, states_dir=sd) == 0  # resumable
    assert {"x3_lo_jlens", "x3_lo_olens", "x3_lo_nla", "capture"} <= {x["step"] for x in A.read_jsonl(led)}


def test_puzzle_nla_templates_registered():
    assert LO.NLA_TEMPLATES.get("puzzle"), "puzzle family must have mapping-style NLA templates"
    assert any("symbol" in t for t in LO.templates_for("puzzle"))


def test_frozen_x_status(tmp_path):
    cand = fixture_candidates_file(tmp_path)
    sha = C.sha256_file(cand)
    man = tmp_path / "frozen_config_x.json"
    assert X3.frozen_x_status(cand, man)[0] is False
    man.write_text(json.dumps({"frozen": False}))
    assert X3.frozen_x_status(cand, man)[0] is False
    man.write_text(json.dumps({"frozen": True, "datasets": {"items_x3_candidates_sha256": sha}}))
    assert X3.frozen_x_status(cand, man) == (True, "candidates sha matches the X manifest")
    man.write_text(json.dumps({"frozen": True, "items_x3_candidates_sha256": "0" * 64}))
    ok, note = X3.frozen_x_status(cand, man)
    assert ok is False and "differs" in note
    man.write_text(json.dumps({"frozen": True, "dataset_sha256": "1" * 64}))
    ok, note = X3.frozen_x_status(cand, man)
    assert ok is True and "no x3" in note


# ================================================================== analysis end to end
def synthetic_analysis_inputs(tmp_path: Path, n: int = 30, d: int = 32, seed: int = 0):
    """n items per set; puzzle states separable by 'actual == correct'; choice labels random (not present).
    jlens: favours the actual answer everywhere (reads the model); nla: favours the TEXT key (fails on ERROR/DISAGREE);
    olens: coin flip. Decode rows give prompt-only 0 on ERROR/DISAGREE and 1 on the controls."""
    rng = np.random.default_rng(seed)
    u = rng.standard_normal(d)
    u /= np.linalg.norm(u)
    items, lo, trows = [], [], []
    sd = tmp_path / "states"
    sd.mkdir()
    k = 0
    for set_ in X3.SETS:
        for j in range(n):
            k += 1
            fam = "puzzle" if set_ in ("error", "error_control") else "choice"
            iid = f"x{'pz' if fam == 'puzzle' else 'ch'}-{k:04d}"
            if fam == "puzzle":
                correct = "A"
                actual = "A" if set_ == "error_control" else "C"
                other = "B" if set_ == "error_control" else "A"
                src = {"correct": correct, "k": 3, "start": "D", "trace": ["D", "B", "F", "A"], "distractors": ["D", "B", "F"]}
                tk = correct
                trows.append({"item_id": iid, "family": "puzzle", "parsed": actual, "correct": correct, "k": 3, "is_coherent": True})
                label = int(actual == correct)
            else:
                opts = ["apple", "pear"]
                actual = opts[int(rng.integers(0, 2))]
                other = opts[1 - opts.index(actual)]
                guess = other if set_ == "disagree" else actual
                src = {"options_listed": opts, "first_listed": opts[0], "self_guess": guess}
                tk = guess
                trows.append({"item_id": iid, "family": "choice", "actual": actual, "self_guess": guess, "candidates": opts, "both_parsed": True})
                label = int(actual == opts[0])
            items.append({"item_id": iid, "pair_id": iid, "version": "A", "family": fam, "set": set_, "split": "test", "prompt_text": "p",
                          "render": "chat", "system": None, "primary": {"name": "model_actual_answer", "question": "q", "candidates": [actual, other],
                                                                         "answer": actual, "answer_aliases": [actual.lower()]},
                          "text_key": tk, "source": src})
            h = rng.standard_normal(d) + (4.0 * u if (fam == "puzzle" and label == 1) else 0.0)
            torch.save(torch.tensor(h, dtype=torch.float32), S.state_path(iid, sd))
            for reader in ("jlens", "olens", "nla"):
                if reader == "jlens":
                    v = abs(rng.standard_normal()) + 0.1
                elif reader == "nla":
                    v = (abs(rng.standard_normal()) + 0.1) * (1 if tk == actual else -1)
                else:
                    v = rng.standard_normal()
                lo.append({"key": f"{reader}|{iid}", "reader": reader, "item_id": iid, "family": fam, "set": set_, "cand_actual": actual,
                           "cand_other": other, "text_key": tk, "lo_actual": float(v), "lp_actual": float(v), "lp_other": 0.0,
                           "favours_actual": v > 0, "templates": [], "unscorable": False})
    # one unscorable jlens row
    lo[0] = dict(lo[0], lo_actual=None, lp_actual=None, lp_other=None, favours_actual=None, unscorable=True)
    selp, lop, tp = tmp_path / "sel.json", tmp_path / "lo.jsonl", tmp_path / "t.jsonl"
    selp.write_text(json.dumps({"meta": {"counts": {s: n for s in X3.SETS}}, "items": items}))
    lop.write_text("\n".join(json.dumps(r) for r in lo) + "\n")
    tp.write_text("\n".join(json.dumps(r) for r in trows) + "\n")
    return selp, lop, tp, sd


def test_analyze_end_to_end(tmp_path):
    selp, lop, tp, sd = synthetic_analysis_inputs(tmp_path, n=30)
    out = tmp_path / "out"
    s = X3A.main(["--selected", str(selp), "--lo", str(lop), "--target", str(tp), "--states-dir", str(sd), "--out", str(out),
                  "--allow-unfrozen", "--n-boot", "300", "--frozen-config", str(tmp_path / "no_manifest.json")])
    for f in ("summary.json", "e8.csv", "e9.csv", "fig_main.png"):
        assert (out / f).exists(), f
    assert s["frozen"] is False and s["counts"] == {k: 30 for k in X3.SETS} and s["underpowered"] == {"error": False, "disagree": False}
    po = s["prompt_only"]
    assert (po["error"]["k"], po["error"]["n"]) == (0, 30) and (po["error_control"]["k"], po["error_control"]["n"]) == (30, 30)
    assert (po["disagree"]["k"], po["disagree"]["n"]) == (0, 30) and (po["agree_control"]["k"], po["agree_control"]["n"]) == (30, 30)
    assert po["error"]["n_from_decode_rows"] == 30
    e8 = s["E8"]
    assert e8["jlens"]["error"]["n_scored"] == 29 and e8["jlens"]["error"]["n_unscorable"] == 1 and e8["jlens"]["error"]["p"] == 1.0
    assert e8["jlens"]["error"]["passes_rule"] and e8["jlens"]["disagree"]["passes_rule"]
    assert s["E8_verdicts"]["jlens"]["verdict"] == "reads_the_model"
    assert e8["nla"]["error"]["p"] == 0.0 and e8["nla"]["error_control"]["p"] == 1.0 and s["E8_verdicts"]["nla"]["verdict"] == "no_evidence"
    assert s["E8_verdicts"]["olens"]["verdict"] == "no_evidence"
    for reader in X3A.READERS:
        for set_ in X3.SETS:
            d = e8[reader][set_]
            assert d["wilson_lo"] <= d["p"] <= d["wilson_hi"] and d["boot_lo"] <= d["p"] <= d["boot_hi"]
    e9 = s["E9"]
    assert e9["puzzle"]["status"] == "ok" and e9["puzzle"]["present"] is True and e9["puzzle"]["loo_auroc"] > 0.95
    assert e9["puzzle"]["ceiling"]["win"] > 0.9 and e9["puzzle"]["ceiling"]["cos_directions"] > 0.5 and e9["puzzle"]["n_used"] == 60
    assert e9["choice"]["status"] == "ok" and e9["choice"]["present"] is False and e9["choice"]["label"] == "actual == first-listed option"
    assert len(s["E9_per_item"]["puzzle"]) == 60
    import csv

    with (out / "e8.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 12 and {r["reader"] for r in rows} == set(X3A.READERS) and "prompt_only_p" in rows[0]
    with (out / "e9.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    assert [r["union"] for r in rows] == ["puzzle", "choice"] and rows[0]["present"] == "True"


def test_analyze_k6_and_missing_inputs(tmp_path):
    selp, lop, tp, sd = synthetic_analysis_inputs(tmp_path, n=10)
    out = tmp_path / "out"
    s = X3A.main(["--selected", str(selp), "--lo", str(lop), "--target", str(tmp_path / "absent.jsonl"), "--states-dir", str(sd),
                  "--out", str(out), "--allow-unfrozen", "--n-boot", "100", "--no-fig", "--skip-e9"])
    assert s["underpowered"] == {"error": True, "disagree": True}
    assert all(v["verdict"] == "descriptive_only (K6)" for v in s["E8_verdicts"].values())
    assert s["E9"] == {} and not (out / "e9.csv").exists() and not (out / "fig_main.png").exists()
    # prompt-only from the text_key fallback when the decode rows are absent
    assert s["prompt_only"]["error"]["n_from_text_key_fallback"] == 10 and s["prompt_only"]["error"]["p"] == 0.0
    # no LO rows at all -> no_data
    s2 = X3A.main(["--selected", str(selp), "--lo", str(tmp_path / "none.jsonl"), "--target", str(tp), "--states-dir", str(sd),
                   "--out", str(tmp_path / "out2"), "--allow-unfrozen", "--n-boot", "50", "--no-fig", "--skip-e9"])
    assert all(v["verdict"] == "no_data" for v in s2["E8_verdicts"].values())
    # refuses a test summary without the X freeze
    with pytest.raises(Exception):
        X3A.main(["--selected", str(selp), "--lo", str(lop), "--frozen-config", str(tmp_path / "nofreeze.json"), "--out", str(tmp_path / "o3")])


def test_probe_helpers():
    rng = np.random.default_rng(0)
    u = rng.standard_normal(16)
    u /= np.linalg.norm(u)
    y = np.array([0, 1] * 20)
    X = rng.standard_normal((40, 16)) + 5.0 * np.outer(y, u)
    sc = X3A.loo_dim_scores(X, y)
    assert not np.isnan(sc).any() and X3A.auroc(sc, y) > 0.99 and ((sc > 0).astype(int) == y).mean() > 0.95
    c = X3A.two_half_ceiling(X, y, 0)
    assert c["halves"][0]["n_fit"] == 20 and c["halves"][0]["n_eval"] == 20 and c["win"] > 0.95 and c["cos_directions"] > 0.7
    p, lo, hi = X3A.item_bootstrap_rate([True] * 8 + [False] * 2, 500, 0)
    assert p == 0.8 and lo <= 0.8 <= hi and lo >= 0.4
    w = X3A.wilson(8, 10)
    assert abs(w[0] - 0.8) < 1e-9 and 0.44 < w[1] < 0.5 and 0.94 < w[2] < 0.97
    assert np.isnan(X3A.item_bootstrap_rate([], 10, 0)[0])


def test_zz_results_cache_dataset_untouched():
    now = sorted(str(p) for p in (REPO / "results" / "g_agreement").rglob("*"))
    assert now == RESULTS_SNAPSHOT
    cache = sorted(str(p) for p in (REPO / "cache" / "g_agreement").rglob("*")) if (REPO / "cache" / "g_agreement").exists() else None
    assert cache == CACHE_SNAPSHOT
    assert sorted(str(p) for p in (REPO / "projects" / "g_agreement" / "dataset").glob("*")) == DATASET_SNAPSHOT
