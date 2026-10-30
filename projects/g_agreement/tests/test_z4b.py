"""MOCK tests (CPU) for Z4b (BRIEF_Z deviations 2026-10-09 "Z4b ownership follow-up" and "NLA reproduction gate"): role-span detection
on the fake tokenizer (subsequence fallback and the offset-mapping path), the one-sentence ownership templates, entry vectors that touch
only the arm's positions, the decode plan (448 on 32 pairs, cap 600), the phase-A collector end to end on the tiny model (L20/L28 stand-ins
= mock layers 0/1, the L38 stand-in = mock layer 1), the phase-B gate on a mock NLA through z4_positions.collect.collect_lo (fp32 inputs
reproduce the X1 collector exactly), the gate verdict logic, and analyze.py on synthetic rows. Nothing is written under results/ or cache/.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_z4b.py -q``
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

torch = pytest.importorskip("torch")

from projects.g_agreement.core import accounting as A  # noqa: E402
from projects.g_agreement.core import config as C  # noqa: E402
from projects.g_agreement.core import edit as E  # noqa: E402
from projects.g_agreement.core import model as M  # noqa: E402
from projects.g_agreement.core import readers as R  # noqa: E402
from projects.g_agreement.tests.test_readers_mock import IM_END, IM_START, MOCK_D, MOCK_LAYER, FakeTok, mock_meta, tiny_model  # noqa: E402
from projects.g_agreement.tests.test_x2_mock import MOCK_SITES, items_x, mk_item  # noqa: E402
from projects.g_agreement.x1_bank import collect as XC  # noqa: E402
from projects.g_agreement.x2_causal import collect as X  # noqa: E402
from projects.g_agreement.z4b_followup import analyze as ZBA  # noqa: E402
from projects.g_agreement.z4b_followup import collect as ZB  # noqa: E402


def _snap(p: Path):
    return sorted(str(q) for q in p.rglob("*")) if p.exists() else None


RESULTS_SNAPSHOT = _snap(REPO / "results" / "g_agreement" / "z4b")
CACHE_SNAPSHOT = _snap(REPO / "cache" / "g_agreement" / "z")
MOCK_EDIT = 1
MOCK_EARLY = (0, 1)
OWN_TEXT = "A has the key. B has the pen. Who has the key? Name only."


@pytest.fixture(autouse=True)
def mock_config(monkeypatch):
    monkeypatch.setattr(C, "LAYER", MOCK_LAYER)
    monkeypatch.setattr(C, "HIDDEN_STATES_INDEX", MOCK_LAYER + 1)
    monkeypatch.setattr(C, "D_MODEL", MOCK_D)
    monkeypatch.setattr(C, "N_LAYERS", 4)
    monkeypatch.setattr(E, "X2_SITES", MOCK_SITES)
    monkeypatch.setattr(E, "X2_EDIT_LAYERS", (MOCK_EDIT, MOCK_LAYER))
    monkeypatch.setattr(E, "X2_READ_LAYER", MOCK_LAYER)
    monkeypatch.setattr(ZB, "Z4B_L38", MOCK_EDIT)
    monkeypatch.setattr(ZB, "Z4B_EARLY_LAYERS", MOCK_EARLY)
    yield


@pytest.fixture(scope="module")
def target():
    return M.Target(model=tiny_model(), tokenizer=FakeTok(), device="cpu", model_id="MOCK/tiny", revision="mock", model_class="Qwen3_5ForCausalLM")


class OffsetTok(FakeTok):
    """FakeTok that maps the chat specials inside a string and returns an offset mapping (the fast-tokenizer path)."""
    SPECIAL = {"<|im_start|>": IM_START, "<|im_end|>": IM_END}

    def __call__(self, text, add_special_tokens=False, return_offsets_mapping=False, **kw):
        ids, offs, i = [], [], 0
        while i < len(text):
            for s, t in self.SPECIAL.items():
                if text.startswith(s, i):
                    ids.append(t)
                    offs.append((i, i + len(s)))
                    i += len(s)
                    break
            else:
                ids.append(self._tok(text[i]))
                offs.append((i, i + 1))
                i += 1
        out = {"input_ids": ids}
        if return_offsets_mapping:
            out["offset_mapping"] = offs
        return out


def own_item(text: str, iid: str = "xown-02A", answer: str = "A", other: str = "B") -> dict:
    it = mk_item(iid, iid[:-1], iid[-1], "ownership", text, answer, other)
    it["template_id"] = "mock"
    return it


# ================================================================== (a) spans
@pytest.mark.parametrize("tokcls,method", [(FakeTok, "subsequence"), (OffsetTok, "offsets")])
def test_span_detection_two_sentence_prompt(tokcls, method):
    tok = tokcls()
    it = own_item(OWN_TEXT)
    ids = M.render_item(tok, OWN_TEXT)
    sp = ZB.item_spans(tok, it, ids)
    assert sp["method"] == method and sp["period_ordinal"] == 2
    u0, u1 = sp["user_span"]
    assert tok.decode(ids[u0:u1]) == OWN_TEXT and ids[u0 - 1] == ord("\n")
    assert sp["period_pos"] == u0 + OWN_TEXT.index("pen.") + 3 and tok.decode([ids[sp["period_pos"]]]) == "."
    q = sp["question_only"]
    assert tok.decode([ids[k] for k in q]) == " Who has the key? Name only." and q == list(range(sp["period_pos"] + 1, u1))
    assert sp["template_only"] == list(range(u1, len(ids))) and ids[u1] == IM_END and sp["template_only"][-1] == len(ids) - 1
    assert sp["last3"] == [len(ids) - 3, len(ids) - 2, len(ids) - 1]
    n = len(q)
    assert sp["question_first_half"] == q[: n // 2] and sp["question_second_half"] == q[n // 2:] and len(sp["question_first_half"]) == n // 2


def test_span_detection_one_sentence_templates_and_errors():
    tok = FakeTok()
    for text, ql in (("A has the key, and B has the pen. Who has the key? Reply with the name only.", " Who has the key? Reply with the name only."),
                     ("A keeps the key; B keeps the pen. Who keeps the key? Give just the name.", " Who keeps the key? Give just the name.")):
        ids = M.render_item(tok, text)
        sp = ZB.item_spans(tok, own_item(text), ids)
        # the "second '.'" of the user text would be the instruction's final period; the rule takes the last '.' before the '?'
        assert sp["period_ordinal"] == 1 and sp["question_text"] == ql
    with pytest.raises(ValueError):
        ZB.statement_end_char("A has the key. B has the pen. Who? Who has the key?")
    with pytest.raises(ValueError):
        ZB.statement_end_char("Who has the key? Name only.")
    with pytest.raises(ValueError):
        ZB.statement_end_char("A has it. B has it. C has it. Who has the key? Name only.")
    with pytest.raises(ValueError):
        ZB.statement_end_char(OWN_TEXT, ("A", "Zed"))
    assert ZB.statement_end_char(OWN_TEXT, ("A", "B"))["period_char"] == OWN_TEXT.index("pen.") + 3


def test_pair_spans_offsets_equal_subsequence():
    tA, tB = OWN_TEXT, "B has the key. A has the pen. Who has the key? Name only."
    pair = {"pair_id": "xown-02", "family": "ownership", "A": own_item(tA), "B": own_item(tB, "xown-02B", "B", "A")}
    out = {}
    for tok in (FakeTok(), OffsetTok()):
        ids = {v: M.render_item(tok, pair[v]["prompt_text"]) for v in "AB"}
        out[type(tok).__name__] = ZB.pair_spans(tok, pair, ids["A"], ids["B"])
    a, b = out["FakeTok"], out["OffsetTok"]
    assert a["arms"] == b["arms"]
    idsA = M.render_item(FakeTok(), tA)
    idsB = M.render_item(FakeTok(), tB)
    assert a["arms"]["names_objects_only"] == E.differing_positions(idsA, idsB) == [a["A"]["user_span"][0], a["A"]["user_span"][0] + 15]
    assert set(a["arms"]["names_objects_only"]).isdisjoint(a["arms"]["question_only"] + a["arms"]["template_only"])


# ================================================================== (b) entry vectors + plan
def test_entry_vectors_touch_only_arm_positions():
    T = 20
    torch.manual_seed(0)
    hA = torch.randn(T, MOCK_D) * 4
    hB = hA + torch.randn(T, MOCK_D)
    hB[[0, 1, 2]] = hA[[0, 1, 2]]  # some positions with Δ = 0
    for pos in ([5], [3, 4, 9], list(range(10, 20)), [17, 18, 19]):
        for src in ("A", "B"):
            e = {"key": "k", "pair_id": "p", "source": src, "alpha": 1.0, "positions": pos}
            v = ZB.z4b_entry_vectors(e, hA, hB)
            h = hA if src == "A" else hB
            other = hB if src == "A" else hA
            assert v["positions"] == pos and v["n_positions"] == len(pos) and torch.allclose(v["vector"], other[pos], atol=1e-5)
            full = h.clone()
            full[pos] = v["vector"]
            outside = [i for i in range(T) if i not in pos]
            assert torch.equal(full[outside], h[outside])
            assert v["last_edited"] == (T - 1 in pos)
            assert abs(v["dose_abs"] - float((hB - hA)[pos].norm())) < 1e-3
        half = ZB.z4b_entry_vectors({"key": "k", "pair_id": "p", "source": "A", "alpha": 0.5, "positions": pos}, hA, hB)
        assert torch.allclose(half["vector"], hA[pos] + 0.5 * (hB - hA)[pos], atol=1e-5)
    for bad in ([], [3, 3], [5, 2], [T]):
        with pytest.raises(ValueError):
            ZB.z4b_entry_vectors({"key": "k", "pair_id": "p", "source": "A", "alpha": 1.0, "positions": bad}, hA, hB)


def fake_spans(n_pairs: int, T: int = 36) -> dict:
    arms = {"question_only": list(range(16, 27)), "template_only": list(range(27, T)), "last3": [T - 3, T - 2, T - 1],
            "question_first_half": list(range(16, 21)), "question_second_half": list(range(21, 27)), "names_objects_only": [7, 8, 13, 14]}
    return {f"xown-{i:02d}": {"pair_id": f"xown-{i:02d}", "family": "ownership", "n_tokens": T, "arms": arms} for i in range(2, 2 + n_pairs)}


def test_plan_count_and_cap(monkeypatch):
    monkeypatch.setattr(ZB, "Z4B_L38", 38)
    monkeypatch.setattr(ZB, "Z4B_EARLY_LAYERS", (20, 28))
    tab = ZB.build_table(fake_spans(32))
    plan = ZB.planned_decodes(tab)
    assert plan["total_planned"] == ZB.EXPECTED_DECODES == 448 and plan["n_cells"] == 7
    assert plan["cells"] == {**{f"{a}@L38": 64 for a in ZB.L38_ARMS}, "names_objects_only@L20": 64, "names_objects_only@L28": 64}
    assert len({e["key"] for e in tab}) == 448 and all(e["alpha"] == 1.0 and e["family"] == "ownership" for e in tab)
    assert {e["key"].split("|")[-1] for e in tab if e["arm"] == "names_objects_only"} == {"L20", "L28"}
    ZB.check_cap(plan, 600)
    with pytest.raises(SystemExit):
        ZB.check_cap(plan, 447)
    assert ZB.planned_decodes(ZB.build_table(fake_spans(40)))["total_planned"] == 560
    with pytest.raises(SystemExit):
        ZB.check_cap(ZB.planned_decodes(ZB.build_table(fake_spans(43))), ZB.DECODE_CAP)
    assert "total" in ZB.format_plan(plan)


# ================================================================== (c) collector end to end (phase A)
def _x2_file(path: Path, pairs) -> Path:
    path.write_text("\n".join(json.dumps({"pair_id": p["pair_id"], "family": p["family"], "key": f"{p['pair_id']}|A|nat|natural|0.0|None"}) for p in pairs) + "\n")
    return path


def test_z4b_pairs_selection(tmp_path):
    allp = X.x2_pairs(items_x(), n_pairs=32)
    own = [p for p in allp if p["family"] == "ownership"]
    f = _x2_file(tmp_path / "x2.jsonl", allp)
    got = ZB.z4b_pairs(items_x(), f, n_pairs=3)
    assert [p["pair_id"] for p in got] == [p["pair_id"] for p in own] and ZB.z4b_pairs(items_x(), f, n_pairs=3, limit=2) == got[:2]
    with pytest.raises(SystemExit):
        ZB.z4b_pairs(items_x(), _x2_file(tmp_path / "x2b.jsonl", own[:2]), n_pairs=3)


def test_collect_phase_a_end_to_end(target, tmp_path, monkeypatch):
    monkeypatch.setattr(C, "FROZEN_CANDIDATES", (tmp_path / "none.json",))
    monkeypatch.setattr(ZBA, "L38", MOCK_EDIT)
    monkeypatch.setattr(ZBA, "EARLY_LAYERS", MOCK_EARLY)
    allp = X.x2_pairs(items_x(), n_pairs=32)
    pairs = ZB.z4b_pairs(items_x(), _x2_file(tmp_path / "x2.jsonl", allp), n_pairs=3)
    xfd, fd, rv, beh, lo, led, log = (tmp_path / f for f in ("xfull", "z4b_full", "readvecs", "beh.jsonl", "lo.jsonl", "c.jsonl", "log.md"))
    usable, skipped = X.ensure_full_states(target, pairs, full_dir=xfd, ledger_path=led, log_path=log, skipped_path=tmp_path / "sk.json")
    assert len(usable) == 3 and not skipped
    spans = ZB.build_spans(target.tokenizer, pairs, xfd)
    for pid, sp in spans.items():
        assert sp["A"]["method"] == "subsequence" and len(sp["arms"]["names_objects_only"]) == 2 and sp["A"]["question_text"] == " Who has the key? Name only."
    tab = ZB.build_table(spans)
    plan = ZB.planned_decodes(tab)
    assert plan["total_planned"] == 3 * 2 * 7 and plan["cells"]["names_objects_only@L0"] == 6 and plan["cells"][f"question_only@L{MOCK_EDIT}"] == 6
    checks = ZB.capture_early(target, pairs, full_dir=fd, x_full_dir=xfd, ledger_path=led, log_path=log)
    assert len(checks) == 6 and all(c["layer"] == MOCK_EDIT and c["rel_fro"] < 1e-2 for c in checks)  # fp32 mock vs its bf16-saved X2 capture
    d = torch.load(fd / "xown-02A.pt")
    assert set(d["layers"]) == set(MOCK_EARLY) and d["layers"][0].dtype == torch.bfloat16 and d["check"]["layer"] == MOCK_EDIT
    assert ZB.capture_early(target, pairs, full_dir=fd, x_full_dir=xfd, ledger_path=led, log_path=log) == checks  # resumable
    n = ZB.collect_behaviour(target, pairs, tab, beh_path=beh, readvec_dir=rv, x_full_dir=xfd, full_dir=fd, ledger_path=led, log_path=log, max_new_tokens=3, batch=3)
    assert n == 42
    assert ZB.collect_behaviour(target, pairs, tab, beh_path=beh, readvec_dir=rv, x_full_dir=xfd, full_dir=fd, ledger_path=led, log_path=log, max_new_tokens=3) == 0
    rows = A.read_jsonl(beh)
    assert len({r["key"] for r in rows}) == 42 and Counter((r["arm"], r["edit_layer"]) for r in rows) == {**{(a, MOCK_EDIT): 6 for a in ZB.L38_ARMS},
                                                                                                         ("names_objects_only", 0): 6, ("names_objects_only", 1): 6}
    for r in rows:
        assert r["positions"] == spans[r["pair_id"]]["arms"][r["arm"]] and r["n_positions"] == len(r["positions"]) and r["site"] == "Z4b"
        assert r["read_layer"] == MOCK_LAYER and r["n_hook_edits"] >= 1 and r["alpha"] == 1.0 and (rv / f"{E.x2_key_safe(r['key'])}.pt").exists()
        for k in ("cand_A", "cand_B", "parsed", "flipped_to_other", "kept_original", "coherent", "lo_model", "dose_abs", "prompt_ids_sha256", "frozen_code_sha256"):
            assert k in r
    assert all(r["last_edited"] for r in rows if r["arm"] in ("template_only", "last3")) and not any(r["last_edited"] for r in rows if r["arm"] == "question_only")
    # each recorded decode equals a direct core decode of the same edit at the same layer
    for arm, layer in (("question_only", MOCK_EDIT), ("names_objects_only", 0)):
        r = next(x for x in rows if x["arm"] == arm and x["edit_layer"] == layer and x["source"] == "B")
        e = next(x for x in tab if x["key"] == r["key"])
        H = {v: (X.load_full(f"{r['pair_id']}{v}", xfd) if arm != "names_objects_only" else ZB.load_early(f"{r['pair_id']}{v}", fd)) for v in "AB"}
        v = ZB.z4b_entry_vectors(e, H["A"]["layers"][layer], H["B"]["layers"][layer])
        ids = X.load_full(f"{r['pair_id']}B", xfd)["ids"]
        one = E.generate_with_interpolated_batch(target, ids, layer, v["positions"], v["vector"][None], read_layer=MOCK_LAYER, max_new_tokens=3,
                                                 cand_first_tokens=(r["first_A"], r["first_B"]))[0]
        assert abs(one["lo_model"] - r["lo_model"]) < 1e-3 and one["answer_text"] == r["answer_text"]
        assert torch.allclose(one["read_vec"].to(torch.bfloat16).float(), X.load_readvec(r["key"], rv), atol=5e-2)
    # readers' LO
    torch.manual_seed(1)
    J = {MOCK_LAYER: torch.eye(MOCK_D) + torch.randn(MOCK_D, MOCK_D) / 10}
    jl = R.JLensReader().bind_tensors(J, M.unembed_weight(target.model), target.tokenizer)
    ol = R.OLensReader(max_new_tokens=4)
    ol.target = target
    for rd in (jl, ol):
        assert ZB.collect_lo(rd, beh_path=beh, lo_path=lo, readvec_dir=rv, ledger_path=led, log_path=log, batch=8) == 42
    assert ZB.collect_lo(jl, beh_path=beh, lo_path=lo, readvec_dir=rv, ledger_path=led, log_path=log) == 0
    lrows = A.read_jsonl(lo)
    assert len(lrows) == 84 and all(r["arm"] and r["edit_layer"] is not None and r["entry_key"] in {x["key"] for x in rows} for r in lrows)
    assert all(r["lo_toward_other"] is None or abs(r["lo_toward_other"] + r["lo_own"]) < 1e-9 for r in lrows)
    steps = {x["step"] for x in A.read_jsonl(led)}
    assert {"z4b_capture_full", f"z4b_behaviour_question_only_L{MOCK_EDIT}", "z4b_behaviour_names_objects_only_L0", "z4b_lo_jlens", "z4b_lo_olens"} <= steps
    assert not any(s.startswith("z4_") for s in steps)
    # analyze end to end on the mock output
    refs = _ref_files(tmp_path, pairs)
    out = tmp_path / "res"
    s = ZBA.main(["--behaviour", str(beh), "--lo", str(lo), "--x2-behaviour", str(refs["x2b"]), "--x2-lo", str(refs["x2l"]), "--y2-behaviour", str(refs["y2b"]),
                  "--y2-lo", str(refs["y2l"]), "--gate", str(tmp_path / "nogate.json"), "--spans", str(tmp_path / "nospans.json"), "--out", str(out),
                  "--allow-unfrozen", "--n-boot", "20", "--frozen-config", str(tmp_path / "nofreeze.json")])
    assert s["n_entries"] == 42 and set(s["readers"]) == {"jlens", "olens"} and s["references"]["name_only"]["n"] == 6
    assert (out / "z4b.md").exists() and (out / "z4b.csv").exists() and (out / "z4b_summary.json").exists() and (out / "fig_main.png").exists()


# ================================================================== (d) analyze on synthetic rows
def _ref_files(tmp_path: Path, pairs, *, y2_name_only_flip: bool = False, nat_lo: float = -1.0) -> dict:
    """X2 natural + S2 α 1 rows and Y2 name_only / name_removed α 1 rows (+ reader LO) for the given pairs."""
    x2b, x2l, y2b, y2l = [], [], [], []
    for p in pairs:
        pid = p["pair_id"] if isinstance(p, dict) else p
        for src in ("A", "B"):
            base = {"pair_id": pid, "family": "ownership", "source": src, "cand_A": "A", "cand_B": "B", "coherent": True}
            x2b.append({**base, "key": f"{pid}|{src}|nat|natural|0.0|None", "site": "nat", "condition": "natural", "alpha": 0.0, "flipped_to_other": False,
                        "kept_original": True, "lo_model": -5.0})
            x2b.append({**base, "key": f"{pid}|{src}|S2|planted|1.0|None", "site": "S2", "condition": "planted", "alpha": 1.0, "flipped_to_other": True,
                        "kept_original": False, "lo_model": 5.0})
            for cond in ("name_only", "name_removed"):
                fl = cond == "name_removed" or y2_name_only_flip
                y2b.append({**base, "key": f"{pid}|{src}|Y2|{cond}|1.0|None", "site": "Y2", "condition": cond, "alpha": 1.0, "flipped_to_other": fl,
                            "kept_original": not fl, "lo_model": 5.0 if fl else -5.0, "n_positions": 4})
    for rows, lo in ((x2b, x2l), (y2b, y2l)):
        for r in rows:
            for rd in ("jlens", "olens"):
                lo.append({"key": f"{rd}|{r['key']}", "entry_key": r["key"], "reader": rd, "lo_toward_other": nat_lo if r["condition"] == "natural" else 1.0,
                           "unscorable": False})
    out = {}
    for name, rows in (("x2b", x2b), ("x2l", x2l), ("y2b", y2b), ("y2l", y2l)):
        out[name] = tmp_path / f"ref_{name}.jsonl"
        out[name].write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return out


def _synthetic(tmp_path: Path, flips: dict, n_pairs: int = 32) -> tuple[Path, Path, list[str]]:
    """Z4b behaviour + LO rows; ``flips[(arm, layer)]`` = number of the 2·n_pairs items that flip (the first k in item order)."""
    pids = [f"xown-{i:02d}" for i in range(2, 2 + n_pairs)]
    beh, lo = [], []
    for (arm, layer), k in flips.items():
        items = [(p, s) for p in pids for s in ("A", "B")]
        for j, (p, s) in enumerate(items):
            fl = j < k
            key = f"{p}|{s}|Z4b|{arm}|1.0|L{layer}"
            beh.append({"key": key, "pair_id": p, "family": "ownership", "source": s, "arm": arm, "condition": arm, "edit_layer": layer, "alpha": 1.0,
                        "positions": [1, 2], "n_positions": 2, "cand_A": "A", "cand_B": "B", "parsed": "B" if fl else "A", "flipped_to_other": fl,
                        "kept_original": not fl, "coherent": True, "lo_model": 3.0 if fl else -4.0, "lo_model_unscorable": False})
            for rd in ("jlens", "olens"):
                lo.append({"key": f"{rd}|{key}", "entry_key": key, "reader": rd, "arm": arm, "lo_toward_other": 1.0 if fl else -1.0, "unscorable": False})
    b, l_ = tmp_path / "zb.jsonl", tmp_path / "zl.jsonl"
    b.write_text("\n".join(json.dumps(r) for r in beh) + "\n")
    l_.write_text("\n".join(json.dumps(r) for r in lo) + "\n")
    return b, l_, pids


def _analyze(tmp_path, b, l_, refs, out_name="out", gate=None, spans=None):
    out = tmp_path / out_name
    s = ZBA.main(["--behaviour", str(b), "--lo", str(l_), "--x2-behaviour", str(refs["x2b"]), "--x2-lo", str(refs["x2l"]), "--y2-behaviour", str(refs["y2b"]),
                  "--y2-lo", str(refs["y2l"]), "--gate", str(gate or tmp_path / "nogate.json"), "--spans", str(spans or tmp_path / "nospans.json"),
                  "--out", str(out), "--allow-unfrozen", "--n-boot", "50", "--frozen-config", str(tmp_path / "nofreeze.json")])
    return s, out


BASE_FLIPS = {("question_only", 38): 64, ("template_only", 38): 0, ("last3", 38): 0, ("question_first_half", 38): 20, ("question_second_half", 38): 52,
              ("names_objects_only", 20): 40, ("names_objects_only", 28): 10}


def test_analyze_decisions_on_synthetic_rows(tmp_path):
    b, l_, pids = _synthetic(tmp_path, BASE_FLIPS)
    refs = _ref_files(tmp_path, pids)
    gate = tmp_path / "gate.json"
    gate.write_text(json.dumps({"verdict": "PASS", "consequence": "Z4 NLA numbers may be reported", "families": {
        f: {"gate_win": {"k": 34, "n": 47, "p": 34 / 47}, "x1_win": {"k": 34, "n": 47, "p": 34 / 47}, "compare": {"median_abs_dlo": 0.02, "sign_agreement": 0.99}}
        for f in ("ownership", "mapping")}}))
    s, out = _analyze(tmp_path, b, l_, refs, gate=gate)
    d = s["decision"]
    assert d["locating_arms"] == ["question_only", "question_second_half"]  # 64/64 and 52/64 = 0.8125 ≥ 0.8
    assert d["arms"]["question_first_half"]["locates"] is False and d["arms"]["template_only"]["locates"] is False
    assert d["binding_moved"] is True and d["moved_layers"] == [20] and d["names_l38"] == {"k": 0, "n": 64, "source": "Y2 data"}
    c = s["cells"]["question_only@L38"]
    assert c["flip"]["k"] == 64 and c["flip"]["n"] == 64 and abs(c["d_model"]["mean"] - 8.0) < 1e-9  # 3 − (−5)
    assert abs(c["readers"]["jlens"]["mean"] - 1.0) < 1e-9  # (1 − (−1)) / sep 2
    assert abs(s["cells"]["template_only@L38"]["readers"]["olens"]["mean"]) < 1e-9 and abs(s["cells"]["template_only@L38"]["d_model"]["mean"] - 1.0) < 1e-9
    assert s["r_all_measured_x2_s2"] == 1.0 and s["references"]["name_removed"]["flip"]["k"] == 64 and s["nla_gate"]["verdict"] == "PASS"
    csv = (out / "z4b.csv").read_text().splitlines()
    assert csv[0].startswith("cell,arm,layer,alpha,source,n,") and len(csv) == 1 + 7 + 3 and any(l_.startswith("name_only@L38,") for l_ in csv)
    md = (out / "z4b.md").read_text()
    assert "THE BINDING MOVED" in md and "LOCATES" in md and "Verdict: **PASS**" in md and (out / "fig_main.png").exists()
    # boundary: 51/64 = 0.797 < 0.8 does not locate; L20/L28 below 0.5 → not moved
    b2, l2, _ = _synthetic(tmp_path, {**BASE_FLIPS, ("question_second_half", 38): 51, ("names_objects_only", 20): 31})
    s2, out2 = _analyze(tmp_path, b2, l2, refs, "out2")
    assert s2["decision"]["locating_arms"] == ["question_only"] and s2["decision"]["binding_moved"] is False
    assert "did NOT move" in (out2 / "z4b.md").read_text() and "Not run yet" in (out2 / "z4b.md").read_text()
    # exactly 32/64 = 0.5 at L28 moves; but a non-zero L38 names-only reference blocks "moved"
    b3, l3, _ = _synthetic(tmp_path, {**BASE_FLIPS, ("names_objects_only", 20): 0, ("names_objects_only", 28): 32})
    s3, _ = _analyze(tmp_path, b3, l3, refs, "out3")
    assert s3["decision"]["binding_moved"] is True and s3["decision"]["moved_layers"] == [28]
    (tmp_path / "r4").mkdir()
    refs4 = _ref_files(tmp_path / "r4", pids, y2_name_only_flip=True)
    s4, _ = _analyze(tmp_path, b, l_, refs4, "out4")
    assert s4["decision"]["binding_moved"] is False and s4["decision"]["names_l38"]["k"] == 64


def test_analyze_missing_cells_and_no_y2(tmp_path):
    b, l_, pids = _synthetic(tmp_path, {("question_only", 38): 10})
    refs = _ref_files(tmp_path, pids)
    refs["y2b"] = tmp_path / "absent_y2.jsonl"
    s, out = _analyze(tmp_path, b, l_, refs)
    assert s["cells"]["template_only@L38"]["n"] == 0 and s["decision"]["arms"]["template_only"]["locates"] is None
    assert s["decision"]["binding_moved"] is None and s["decision"]["names_l38"]["source"].startswith("pre-registered")
    assert (out / "fig_main.png").exists()


# ================================================================== (e) NLA reproduction gate (phase B)
def _gate_world(target, tmp_path):
    items = items_x()
    pairs = ZB.gate_pairs(items=items)
    sd, meta, led, log = tmp_path / "states", tmp_path / "meta.jsonl", tmp_path / "c.jsonl", tmp_path / "log.md"
    XC.capture_states(target, pairs, states_dir=sd, meta_path=meta, ledger_path=led, log_path=log)
    items_file = tmp_path / "items_x.json"
    items_file.write_text(json.dumps({"items": items}))
    tok = FakeTok()
    nla = R.NLAReader(max_new_tokens=4).attach(tiny_model(1), tok, mock_meta(tok), device="cpu")
    return items, pairs, sd, items_file, nla, led, log


def test_nla_gate_path_reproduces_x1_collector(target, tmp_path):
    items, pairs, sd, items_file, nla, led, log = _gate_world(target, tmp_path)
    assert len(pairs) == 5 and {p["family"] for p in pairs} == {"ownership", "mapping"}
    x1lo = tmp_path / "x1_lo.jsonl"
    assert XC.collect_lo(nla, pairs, lo_path=x1lo, ledger_path=led, log_path=log, states_dir=sd, batch=4) == 10
    paths = {k: tmp_path / f"{k}_{v}" for k, v in (("in", "inputs.jsonl"), ("lo", "gate.jsonl"), ("json", "gate.json"))}
    s = ZB.run_gate(items_path=items_file, items=items, states_dir=sd, inputs_path=paths["in"], vec_dir=tmp_path / "vecs", lo_path=paths["lo"],
                    x1_lo_path=x1lo, gate_json=paths["json"], nla=nla, dtype="float32", batch=4, ledger_path=led, log_path=log, n_boot=50)
    rows = A.read_jsonl(paths["lo"])
    assert len(rows) == 10 and all(r["reader"] == "nla" and r["key"].startswith("nla|x1gate|") for r in rows)
    x1 = {r["item_id"]: r for r in A.read_jsonl(x1lo)}
    for r in rows:  # same candidates (own, other), same family, same batch composition → identical scores in fp32
        q = x1[r["state_item_id"]]
        assert (r["cand_A"], r["cand_B"], r["family"]) == (q["cand_A"], q["cand_B"], q["family"]) and abs(r["lo_own"] - q["lo"]) < 1e-5
    for fam in ("ownership", "mapping"):
        f = s["families"][fam]
        assert f["compare"]["n_matched"] == 2 * (3 if fam == "ownership" else 2) and f["compare"]["median_abs_dlo"] < 1e-5
        assert f["compare"]["sign_agreement"] == 1.0 and f["compare"]["pair_win_agreement"] == 1.0
        assert (f["gate_win"]["k"], f["gate_win"]["n"]) == (f["x1_win"]["k"], f["x1_win"]["n"])
    assert s["verdict"] in ("PASS", "FAIL") and json.loads(paths["json"].read_text())["verdict"] == s["verdict"]
    steps = [x["step"] for x in A.read_jsonl(led)]
    assert "z4b_nla_x1_gate" in steps and "z4_lo_nla" not in steps and not list(tmp_path.glob("*.ledger.tmp.jsonl"))
    # resumable; a dtype switch on existing inputs is refused; bf16 inputs (the Z4 read-vector format) stay close
    assert ZB.score_gate(nla, inputs_path=paths["in"], lo_path=paths["lo"], vec_dir=tmp_path / "vecs", ledger_path=led, log_path=log, batch=4) == 0
    with pytest.raises(SystemExit):
        ZB.write_gate_inputs(pairs, inputs_path=paths["in"], vec_dir=tmp_path / "vecs", states_dir=sd, dtype="bfloat16")
    s16 = ZB.run_gate(items_path=items_file, items=items, states_dir=sd, inputs_path=tmp_path / "in16.jsonl", vec_dir=tmp_path / "vecs16",
                      lo_path=tmp_path / "gate16.jsonl", x1_lo_path=x1lo, gate_json=None, nla=nla, dtype="bfloat16", batch=4, ledger_path=led, log_path=log, n_boot=50)
    assert s16["compare_all"]["n_matched"] == 10 and s16["compare_all"]["median_abs_dlo"] < 0.5
    assert torch.load(tmp_path / "vecs16" / f"{E.x2_key_safe('x1gate|xown-02A')}.pt").dtype == torch.bfloat16


def _gate_rows(path: Path, pairs, lo_of):
    path.write_text("\n".join(json.dumps({"key": f"nla|x1gate|{p[v]['item_id']}", "reader": "nla", "state_item_id": p[v]["item_id"], "lo_own": lo_of(p, v),
                                          "unscorable": False}) for p in pairs for v in "AB") + "\n")


def test_gate_verdict_logic(tmp_path):
    pairs = [{"pair_id": f"x{fam[:3]}-{i:02d}", "family": fam, "A": {"item_id": f"x{fam[:3]}-{i:02d}A"}, "B": {"item_id": f"x{fam[:3]}-{i:02d}B"}}
             for fam in ("ownership", "mapping") for i in range(10)]

    def lo_k(k):  # the first k pairs of each family win (lo_A + lo_B = +1), the rest lose (−1)
        return lambda p, v: (0.5 if int(p["pair_id"][-2:]) < k else -0.5)

    x1 = tmp_path / "x1.jsonl"
    x1.write_text("\n".join(json.dumps({"key": f"nla|{p[v]['item_id']}", "reader": "nla", "item_id": p[v]["item_id"], "condition": "natural",
                                        "lo": lo_k(7)(p, v) + 0.6, "unscorable": False}) for p in pairs for v in "AB") + "\n")
    g = tmp_path / "g.jsonl"
    _gate_rows(g, pairs, lo_k(7))
    s = ZB.gate_summary(pairs, gate_lo_path=g, x1_lo_path=x1, n_boot=20)
    assert s["verdict"] == "PASS" and s["families"]["ownership"]["gate_win"]["k"] == 7 and abs(s["families"]["mapping"]["compare"]["median_abs_dlo"] - 0.6) < 1e-9
    assert abs(s["families"]["ownership"]["compare"]["sign_agreement"] - 0.7) < 1e-12  # the 3 losing pairs: −0.5 (gate) vs +0.1 (X1)
    assert s["families"]["ownership"]["x1_win"]["k"] == 10 and abs(s["families"]["ownership"]["compare"]["pair_win_agreement"] - 0.7) < 1e-12
    _gate_rows(g, pairs, lo_k(9))
    assert ZB.gate_summary(pairs, gate_lo_path=g, x1_lo_path=x1, n_boot=20)["verdict"] == "FAIL"  # 0.9 outside 0.72 ± 0.05
    _gate_rows(g, [p for p in pairs if p["family"] == "ownership"], lo_k(7))
    s3 = ZB.gate_summary(pairs, gate_lo_path=g, x1_lo_path=tmp_path / "absent.jsonl", n_boot=20)
    assert s3["verdict"] == "INCOMPLETE" and s3["families"]["ownership"]["x1_win"] is None
    assert "INCOMPLETE" in ZB.format_gate(s3)


def test_main_phase_b_requires_gate_flag():
    with pytest.raises(SystemExit):
        ZB.main(["--phase", "B", "--allow-unfrozen"])


def test_zz_results_and_cache_untouched():
    assert _snap(REPO / "results" / "g_agreement" / "z4b") == RESULTS_SNAPSHOT
    assert _snap(REPO / "cache" / "g_agreement" / "z") == CACHE_SNAPSHOT
