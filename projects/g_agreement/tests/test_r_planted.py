"""Offline tests for the R-C2 planted-context bank and collector helpers (BRIEF_R.md §3.1 + E7; r_bench/planted.py).

Builder: 48 pairs × 2 versions × 3 paraphrases, schema = items_r.json + system, candidates = [context, belief] with the
two names swapping roles within a pair, no candidate in the visible prompt, the belief never in the system turn, the
three paraphrases of a base item sharing system / candidates / template, template and forced-choice option order
balanced per category, determinism under the seed, disk bank == rebuild. Collector helpers: the system turn reaches
the chat render, the prompt-only patch is visible to ``collect.collect_prompt_only`` and is restored, every row tag
carries the paraphrase, the compliance + switching selection and the pre-registered summaries on synthetic rows.
Nothing is written outside ``tmp_path``. No GPU, no torch.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_r_planted.py -q``
"""
from __future__ import annotations

import json

import numpy as np
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from common import stats as ST  # noqa: E402
from projects.g_agreement.r_bench import bank as B  # noqa: E402
from projects.g_agreement.r_bench import collect as RC  # noqa: E402
from projects.g_agreement.r_bench import datasets as D  # noqa: E402
from projects.g_agreement.r_bench import planted as P  # noqa: E402

N_ITEMS, N_BASE, N_PAIRS = 288, 96, 48


@pytest.fixture(scope="module")
def built():
    return P.build(P.SEED)


@pytest.fixture(scope="module")
def items(built):
    return built[0]


@pytest.fixture(scope="module")
def q0(items):
    return [it for it in items if it["paraphrase"] == 0]


@pytest.fixture(scope="module")
def pairs(q0):
    out: dict[str, dict[str, dict]] = {}
    for it in q0:
        out.setdefault(it["pair_id"], {})[it["version"]] = it
    return out


# ------------------------------------------------------------------ builder
def test_counts_and_validate(items):
    rep = P.validate(items)
    assert rep["n_items"] == N_ITEMS and rep["n_base_items"] == N_BASE and rep["n_pairs"] == N_PAIRS and rep["n_paraphrases"] == 3
    assert rep["templates"] == {"p0": 24, "p1": 24}
    assert set(rep["categories"].values()) == {8} and len(rep["categories"]) == 6


def test_schema_is_items_r_plus_system(items):
    spec = D.SPECS["92_glue_sst2"]
    ref = B.make_items(spec, [("a text", 1, "1"), ("another", 0, "0")], [0], [1])[0]
    for it in items:
        assert set(ref) <= set(it), set(ref) - set(it)
        assert "system" in it and isinstance(it["system"], str)
        assert set(ref["primary"]) <= set(it["primary"]), set(ref["primary"]) - set(it["primary"])
        assert it["primary"]["sided"] == "two" and it["label"] == 1 and it["split"] == "test" and it["render"] == "chat"


def test_candidates_are_context_then_belief(items):
    for it in items:
        c = it["primary"]["candidates"]
        assert c == [it["context_answer"], it["belief_answer"]] and it["primary"]["answer"] == it["context_answer"]
        assert c[0] != c[1] and it["false_statement"] != it["true_statement"]
        assert it["system"].endswith(".") and it["false_statement"] in it["system"]


def test_paraphrases_share_everything_but_the_question(items):
    by_base: dict[str, list[dict]] = {}
    for it in items:
        by_base.setdefault(it["base_item_id"], []).append(it)
    assert len(by_base) == N_BASE
    for bid, group in by_base.items():
        assert sorted(it["paraphrase"] for it in group) == [0, 1, 2], bid
        assert len({it["system"] for it in group}) == 1 and len({tuple(it["primary"]["candidates"]) for it in group}) == 1, bid
        assert len({it["primary"]["template"] for it in group}) == 1 and len({it["pair_key"] for it in group}) == 3, bid
        qs = [it["primary"]["question"] for it in group]
        assert len(set(qs)) == 3 and all(it["prompt_text"].startswith(it["primary"]["question"]) for it in group), bid
        assert all(it["item_id"] == f"{bid}-q{it['paraphrase']}" for it in group), bid
    # q1 / q2 wordings are the planned families
    for it in items:
        q = it["primary"]["question"]
        if it["paraphrase"] == 2:
            assert q.startswith("Name ") and q.endswith("."), it["item_id"]
        elif it["paraphrase"] == 1:
            assert q.split()[0] in {"Which", "Who", "What"} and q.endswith("?"), it["item_id"]


def test_roles_swap_within_pair(pairs):
    assert len(pairs) == N_PAIRS
    for pid, pv in pairs.items():
        a, b = pv["A"], pv["B"]
        assert a["primary"]["candidates"] == b["primary"]["candidates"][::-1], pid
        assert a["context_answer"] == b["belief_answer"] and a["belief_answer"] == b["context_answer"], pid
        assert a["prompt_text"] != b["prompt_text"] and a["system"] != b["system"], pid
        assert a["preamble_template"] == b["preamble_template"] == {"rc2-p0": "p0", "rc2-p1": "p1"}[a["preamble_id"]], pid
        assert a["fc_context_first"] == b["fc_context_first"], pid
        assert {a["side_index"], b["side_index"]} == {0, 1}, pid


def test_no_candidate_in_visible_prompt_and_belief_absent_from_system(items):
    for it in items:
        ctx_tok, bel_tok = it["primary"]["jlens"]
        words = {w.lower() for w in P._WORD.findall(it["prompt_text"])}
        assert ctx_tok.lower() not in words and bel_tok.lower() not in words, it["item_id"]
        sys_words = {w.lower() for w in P._WORD.findall(it["system"])}
        assert ctx_tok.lower() in sys_words and bel_tok.lower() not in sys_words, it["item_id"]


def test_unique_prompts_and_ids(items):
    assert len({it["item_id"] for it in items}) == N_ITEMS
    assert len({it["prompt_text"] for it in items}) == N_ITEMS
    assert len({it["system"] for it in items}) == N_BASE


def test_nla_template_matches_false_statement(items):
    for it in items:
        t = it["primary"]["template"]
        assert t.count("{X}") == 1 and t.endswith(".") and t[0].isupper()
        assert t.format(X=it["context_answer"]).lower() == (it["false_statement"] + ".").lower(), it["item_id"]
        assert t.format(X=it["belief_answer"]).lower() == (it["true_statement"] + ".").lower(), it["item_id"]


def test_balance_within_category(q0):
    A = [it for it in q0 if it["version"] == "A"]
    for cat in P.CATEGORIES:
        sub = [it for it in A if it["category"] == cat]
        assert len(sub) == 8
        assert sum(it["preamble_template"] == "p0" for it in sub) == 4
        assert sum(it["fc_context_first"] for it in sub) == 4


def test_jlens_forms_are_single_words_and_distinguish(items):
    for it in items:
        j0, j1 = it["primary"]["jlens"]
        assert " " not in j0 and " " not in j1 and j0.lower() != j1.lower()
        assert j0.lower() in it["context_answer"].lower() and j1.lower() in it["belief_answer"].lower()


def test_determinism_and_seed_dependence(built):
    items, design = built
    again, design2 = P.build(P.SEED)
    assert again == items and design == design2
    other, _ = P.build(P.SEED + 1)
    assert other != items
    assert {it["false_statement"] for it in other} == {it["false_statement"] for it in items}
    assert {it["prompt_text"] for it in other} == {it["prompt_text"] for it in items}
    P.validate(other)


def test_disk_bank_matches_rebuild():
    if not P.ITEMS_RC2.exists():
        pytest.skip("dataset/items_rc2.json not built")
    d = P.load_bank()
    items, _ = P.build(d["meta"]["seed"])
    assert d["meta"]["sha256_items"] == P.sha256_items(items) == P.sha256_items(d["items"])
    assert d["meta"]["n_items"] == N_ITEMS and d["meta"]["n_base_items"] == N_BASE and d["meta"]["dataset"] == P.DATASET
    if P.frozen_mark_path().exists():  # the committed freeze mark matches the committed bank and the R manifest
        mark = P.read_frozen_mark()
        assert P.is_frozen() and mark["sha256_items"] == d["meta"]["sha256_items"]
        if RC.FROZEN_R.exists():
            assert json.loads(RC.FROZEN_R.read_text())["items_sha256"]["items_rc2.json"] == mark["file_sha256"]


def test_write_bank_refuses_a_different_bank(tmp_path, built):
    items, design = built
    out = tmp_path / "items_rc2.json"
    P.write_bank(items, design, out)
    assert json.loads(out.read_text())["meta"]["sha256_items"] == P.sha256_items(items)
    P.write_bank(items, design, out)  # same bank: fine
    changed = json.loads(json.dumps(items))
    changed[0]["system"] = changed[0]["system"] + " (edited)"
    with pytest.raises(AssertionError):  # paraphrases of a base item must share the system turn
        P.write_bank(changed, design, out, force=True)
    for it in changed:
        if it["base_item_id"] == changed[0]["base_item_id"]:
            it["system"] = changed[0]["system"]
    with pytest.raises(SystemExit):
        P.write_bank(changed, design, out)
    P.write_bank(changed, design, out, force=True)
    before = out.read_bytes()
    mp = P.freeze_bank(out, manifest=None)
    assert mp == tmp_path / "rc2_frozen.json" and out.read_bytes() == before  # the bank's bytes are untouched
    mark = json.loads(mp.read_text())
    assert mark["frozen"] is True and mark["file_sha256"] == P.C.sha256_file(out) and mark["sha256_items"] == P.sha256_items(changed) and mark["manifest"] is None
    assert P.is_frozen(out)
    with pytest.raises(SystemExit):
        P.freeze_bank(out, manifest=None)
    P.write_bank(changed, design, out)  # unchanged + frozen: a no-op
    assert out.read_bytes() == before


def test_freeze_mark_must_agree_with_the_r_manifest(tmp_path, built):
    items, design = built
    out = tmp_path / "items_rc2.json"
    P.write_bank(items, design, out)
    sha = P.C.sha256_file(out)
    man = tmp_path / "frozen_config_r.json"
    man.write_text(json.dumps({"frozen": True, "frozen_at": "t", "items_sha256": {"items_rc2.json": "0" * 64}}))
    with pytest.raises(SystemExit):  # different bytes than the manifest froze
        P.freeze_bank(out, manifest=man)
    man.write_text(json.dumps({"frozen": True, "frozen_at": "t", "items_sha256": {"items_r.json": sha}}))
    with pytest.raises(SystemExit):  # bank not covered
        P.freeze_bank(out, manifest=man)
    man.write_text(json.dumps({"frozen": False, "items_sha256": {"items_rc2.json": sha}}))
    with pytest.raises(SystemExit):  # manifest not frozen
        P.freeze_bank(out, manifest=man)
    man.write_text(json.dumps({"frozen": True, "frozen_at": "t", "items_sha256": {"items_rc2.json": sha}}))
    mark = json.loads(P.freeze_bank(out, manifest=man).read_text())
    assert mark["manifest"]["items_sha256"] == sha == mark["file_sha256"] and P.is_frozen(out)
    assert not P.frozen_mark_path(out).name.startswith("items_r")  # must not be picked up as a bank by collect.items_files()
    out.write_text(out.read_text() + "\n")  # any change to the bytes un-freezes
    assert not P.is_frozen(out)


def test_check_prints_every_pair_and_paraphrase(items, capsys):
    cov = P.check(items)
    out = capsys.readouterr().out
    assert cov["n"] == 0 and all(f"rc2-{k:02d} [" in out for k in range(1, 49))
    assert out.count("SYSTEM") == N_BASE and out.count("USER q0") == N_BASE and out.count("USER q2") == N_BASE


def test_smoke_items(items):
    sm = P.smoke_items(items)
    assert len(sm) == 12 and {it["pair_id"] for it in sm} == {"rc2-01", "rc2-02"} and {it["paraphrase"] for it in sm} == {0, 1, 2}


# ------------------------------------------------------------------ collector helpers
class RecordingTok:
    """apply_chat_template stand-in that records the messages and returns one id per message."""

    pad_token_id = 0
    eos_token_id = 1

    def __init__(self):
        self.calls: list[list[dict]] = []

    def apply_chat_template(self, messages, tokenize=True, add_generation_prompt=True, enable_thinking=False):
        self.calls.append([dict(m) for m in messages])
        return list(range(len(messages)))

    def __call__(self, text, add_special_tokens=False, **kw):
        return {"input_ids": [ord(c) for c in text]}


def test_messages_and_prompt_only_head(items):
    it = items[5]
    assert P.messages(it) == [{"role": "system", "content": it["system"]}, {"role": "user", "content": it["prompt_text"]}]
    assert P.messages(it, system_on=False) == [{"role": "user", "content": it["prompt_text"]}]
    tok = RecordingTok()
    P.prompt_only_head(tok, it, True, "answer")
    assert tok.calls[-1] == P.messages(it)
    P.prompt_only_head(tok, it, False, "answer")
    assert tok.calls[-1] == P.messages(it, False)
    P.prompt_only_head(tok, it, True, "fc")
    msgs = tok.calls[-1]
    assert msgs[0]["role"] == "system" and msgs[0]["content"] == it["system"]
    user = msgs[1]["content"]
    c = it["primary"]["candidates"]
    assert it["prompt_text"] in user and it["primary"]["question"] in user and c[0] in user and c[1] in user
    first, second = (c[0], c[1]) if it["fc_context_first"] else (c[1], c[0])
    assert user.index(f'"{first}"') < user.index(f'"{second}"')
    assert user == D.PROMPT_ONLY_FC_TEMPLATE.format(text=it["prompt_text"], question=it["primary"]["question"], pos=first, neg=second)
    with pytest.raises(ValueError):
        P.prompt_only_head(tok, it, True, "bogus")


def test_fc_option_order_alternates_by_pair(q0):
    A = sorted((it for it in q0 if it["version"] == "A"), key=lambda x: x["pair_index"])
    assert [it["fc_context_first"] for it in A] == [k % 2 == 0 for k in range(48)]
    for it in A:
        user = P.fc_user_text(it)
        c = it["primary"]["candidates"]
        assert (user.index(f'"{c[0]}"') < user.index(f'"{c[1]}"')) == it["fc_context_first"]


def test_patched_prompt_only_is_visible_to_collect_and_restored(items):
    orig = RC.prompt_only_ids
    assert RC.collect_prompt_only.__globals__ is vars(RC)
    tok = RecordingTok()
    with P.patched_prompt_only(True, "answer"):
        assert RC.prompt_only_ids is not orig
        RC.collect_prompt_only.__globals__["prompt_only_ids"](tok, items[3])
        assert tok.calls[-1] == P.messages(items[3])
    assert RC.prompt_only_ids is orig
    with pytest.raises(RuntimeError):
        with P.patched_prompt_only(False, "fc"):
            assert RC.prompt_only_ids is not orig
            raise RuntimeError("inside")
    assert RC.prompt_only_ids is orig


def test_row_tags_carry_the_paraphrase(items):
    for it in items:
        tags = P._item_tags(it)
        assert tags["paraphrase"] == it["paraphrase"] and tags["base_item_id"] == it["base_item_id"] and tags["pair_key"] == it["pair_key"]
        assert tags["candidates"] == it["primary"]["candidates"] and tags["version"] == it["version"]


def test_lo_keys_distinguish_arms_and_smoke(items):
    """The pod run of 2026-10-19 skipped every nosys reader row because the key had no dataset and the arms share
    item ids; smoke datasets share them too."""
    it = items[0]
    keys = {P.lo_key("jlens", 42, ds, it["item_id"]) for ds in (P.DATASET, P.DATASET_NOSYS, P.arm_dataset(P.DATASET, True), P.arm_dataset(P.DATASET_NOSYS, True))}
    assert len(keys) == 4
    k = P.lo_key("olens", 44, P.DATASET_NOSYS, it["item_id"], shuf=True)
    assert k == f"olens|L44|chat|rc2_nosys|shuf|{it['item_id']}" and k != P.lo_key("olens", 44, P.DATASET_NOSYS, it["item_id"])
    assert P.DATASET_NOSYS in k and it["item_id"] in k


def test_rows_carry_run_meta_and_update_done_keys(tmp_path):
    """Rows go through collect.append_row: pod / shard / git_sha ride on every row (the first pod run's rows had none)."""
    path = tmp_path / "reader_lo.T.jsonl"
    saved = dict(RC.RUN_META)
    try:
        RC.set_run_meta("T-pod")
        assert RC.RUN_META["pod"] == "T-pod" and "git_sha" in RC.RUN_META and "shard" in RC.RUN_META
        P._emit(path, {"key": "k1", "lo": 1.0})
        row = json.loads(path.read_text().splitlines()[0])
        assert row["pod"] == "T-pod" and row["shard"] is None and "git_sha" in row and row["lo"] == 1.0
        assert "k1" in RC.done_keys(path)
    finally:
        RC.RUN_META.clear()
        RC.RUN_META.update(saved)
    src = Path(P.__file__).read_text()
    assert "append_jsonl(" not in src and "done_ids(" not in src and "log_line(" not in src


def test_arm_dataset_names():
    assert P.arm_dataset(P.DATASET, False) == "rc2_planted" and P.arm_dataset(P.DATASET, True) == "rc2_planted_smoke"
    assert P.arm_dataset(P.DATASET_NOSYS, True) == "rc2_nosys_smoke"


# ------------------------------------------------------------------ selection and summary on synthetic rows
def _po_row(dataset, it, greedy):
    lo = 1.5 if greedy == 0 else -1.5
    return {"key": f"po|{dataset}|{it['item_id']}", "dataset": dataset, "item_id": it["item_id"], "candidates": it["primary"]["candidates"],
            "lp": [lo, 0.0], "greedy": greedy, "lo": lo}


def _lo_row(dataset, it, reader, layer, cond, lo, unscorable=False):
    return {"key": f"{reader}|L{layer}|chat|{'shuf|' if cond == 'shuf' else ''}{it['item_id']}", "reader": reader, "layer": layer, "render": "chat",
            "condition": cond, "dataset": dataset, "item_id": it["item_id"], "pair_id": it["pair_id"], "pair_key": it["pair_key"],
            "version": it["version"], "base_item_id": it["base_item_id"], "paraphrase": it["paraphrase"], "lo": lo, "unscorable": unscorable}


def _complies(it) -> bool:
    """Synthetic model: pairs 01–20 comply on every paraphrase, pairs 21–30 comply on q0/q1 only (switching), pairs
    31–47 never comply; pair 48 does not hold the belief."""
    k = it["pair_index"]
    return k < 20 or (k < 30 and it["paraphrase"] < 2)


@pytest.fixture
def synthetic(tmp_path, items):
    """Readers: 'ctx' sides with the model (context on compliers, belief on non-compliers, per paraphrase);
    'bel' always sides with the belief; 'bad' has a shuffled control stuck at +1."""
    po = tmp_path / "prompt_only.jsonl"
    lo = tmp_path / "reader_lo.jsonl"
    with po.open("w") as fh:
        for it in items:
            fh.write(json.dumps(_po_row(P.DATASET_NOSYS, it, 0 if it["pair_index"] == 47 else 1)) + "\n")
            fh.write(json.dumps(_po_row(P.DATASET, it, 0 if _complies(it) else 1)) + "\n")
            fh.write(json.dumps(_po_row(P.DATASET + P.FC_SUFFIX, it, 0 if it["pair_index"] < 20 else 1)) + "\n")
    with lo.open("w") as fh:
        for i, it in enumerate(items):
            sign = 1.0 if i % 2 == 0 else -1.0
            for reader in ("ctx", "bel", "bad"):
                nat = {"ctx": 2.0 if _complies(it) else -2.0, "bel": -2.0, "bad": 2.0}[reader]
                fh.write(json.dumps(_lo_row(P.DATASET, it, reader, 42, "natural", nat)) + "\n")
                fh.write(json.dumps(_lo_row(P.DATASET, it, reader, 42, "shuf", sign if reader != "bad" else 2.0)) + "\n")
                fh.write(json.dumps(_lo_row(P.DATASET_NOSYS, it, reader, 42, "natural", -1.0)) + "\n")
            fh.write(json.dumps(_lo_row(P.DATASET, it, "ctx", 56, "natural", 2.0, unscorable=True)) + "\n")  # ignored
            if i % 7 == 0:  # a re-written row (old-key run superseded by the dataset-qualified rerun): the last one counts
                fh.write(json.dumps({**_lo_row(P.DATASET, it, "ctx", 42, "natural", 2.0 if _complies(it) else -2.0), "key": "old-format-" + it["item_id"]}) + "\n")
    return po, lo


def test_select_counts_and_rates(tmp_path, items, synthetic):
    po, _ = synthetic
    sel = P.select(items, po, tmp_path / "res")
    s = sel["summary"]
    # compliers: 20 pairs × 6 + 10 pairs × 4 = 160; non-compliers: 17 × 6 + 10 × 2 = 122; excluded: pair 48 = 6
    assert s["counts"] == {"complier": 160, "non_complier": 122, "excluded_no_belief": 6}
    assert s["pair_counts"] == {"complier_pair": 80, "non_complier_pair": 61, "excluded_pair": 3}
    cr = s["compliance_rate"]
    assert (cr["k"], cr["n"]) == (160, 282)
    p, lo, hi = ST.wilson(160, 282)
    assert (cr["p"], cr["lo"], cr["hi"]) == (p, lo, hi)
    assert {q: v["k"] for q, v in s["compliance_by_paraphrase"].items()} == {"q0": 60, "q1": 60, "q2": 40}
    assert s["fc_compliance_rate_secondary"]["k"] == 120 and s["fc_compliance_rate_secondary"]["n"] == 282
    # E7 base items: switching = pairs 21–30 × 2 versions = 20; constant compliers 40; constant non-compliers 34; excluded 2
    assert s["base_counts"] == {"switching": 20, "constant_complier": 40, "constant_non_complier": 34, "excluded": 2}
    assert (s["switching_rate"]["k"], s["switching_rate"]["n"]) == (20, 94)
    assert (tmp_path / "res" / "rc2_selection.csv").exists() and (tmp_path / "res" / "rc2_selection.json").exists()
    rows = {r["item_id"]: r for r in sel["items"]}
    assert rows["rc2-48A-q0"]["status"] == "excluded_no_belief" and rows["rc2-48A-q0"]["base_status"] == "excluded"
    assert rows["rc2-01A-q2"]["status"] == "complier" and rows["rc2-01A-q2"]["base_status"] == "constant_complier"
    assert rows["rc2-25B-q2"]["status"] == "non_complier" and rows["rc2-25B-q2"]["base_status"] == "switching" and rows["rc2-25B-q0"]["pair_status"] == "complier_pair"
    assert rows["rc2-40B-q1"]["status"] == "non_complier" and rows["rc2-40B-q1"]["base_status"] == "constant_non_complier"
    # the pod writes suffixed files: the same rows split over prompt_only.RC2.jsonl / prompt_only.RC2c.jsonl are read together
    split = tmp_path / "split"
    split.mkdir()
    lines = po.read_text().splitlines()
    (split / "prompt_only.RC2.jsonl").write_text("\n".join(lines[: len(lines) // 2]) + "\n")
    (split / "prompt_only.RC2c.jsonl").write_text("\n".join(lines[len(lines) // 2:]) + "\n")
    assert [q.name for q in P.prompt_only_files(split)] == ["prompt_only.RC2.jsonl", "prompt_only.RC2c.jsonl"]
    sel2 = P.select(items, P.prompt_only_files(split), None)
    assert sel2["summary"]["counts"] == s["counts"] and sel2["summary"]["base_counts"] == s["base_counts"]
    missing = P.select(items, tmp_path / "nonexistent.jsonl", None)
    assert missing["summary"]["counts"] == {"missing": N_ITEMS} and missing["summary"]["base_counts"] == {"excluded": N_BASE}


def test_summarize_verdicts(tmp_path, items, synthetic):
    po, lo = synthetic
    sel = P.select(items, po, None)
    S = P.summarize(sel, lo, tmp_path / "res", n_boot=200, seed=0)
    by = {(r["reader"], r["layer"]): r for r in S["table"]}
    assert set(by) == {("ctx", 42), ("bel", 42), ("bad", 42)}  # the unscorable L56 rows are dropped
    ctx = by[("ctx", 42)]
    assert ctx["n_complier_items"] == 160 and ctx["p_context_compliers"] == 1.0 and ctx["n_noncomplier_items"] == 122 and ctx["p_context_noncompliers"] == 0.0
    assert ctx["n_complier_pairs"] == 80 and ctx["pair_win"] == 1.0 and ctx["nosys_p_belief"] == 1.0
    assert ctx["q2_n_compliers"] == 40 and ctx["q0_n_compliers"] == 60 and ctx["q2_n_noncompliers"] == 54 and ctx["q0_n_noncompliers"] == 34
    assert abs(ctx["shuf_p_context"] - 0.5) < 0.02 and ctx["shuf_lo"] <= 0.5 <= ctx["shuf_hi"]
    assert ctx["verdict"] == "READS THE CONTEXT + READS THE MODEL"
    assert by[("bel", 42)]["verdict"] == "READS THE BELIEF" and by[("bel", 42)]["pair_win"] == 0.0
    assert by[("bad", 42)]["verdict"].startswith("SHUFFLED CONTROL OFF")
    e7 = {(r["reader"], r["layer"]): r for r in S["e7"]}
    assert e7[("ctx", 42)]["n_switching_items"] == 20 and e7[("ctx", 42)]["p_follows"] == 1.0 and e7[("ctx", 42)]["p_constant"] == 0.0
    assert e7[("ctx", 42)]["n_switch_rows"] == 60 and e7[("ctx", 42)]["p_agree_model"] == 1.0
    assert e7[("ctx", 42)]["verdict_e7"] == "READS THE MODEL (switches with it)"
    assert e7[("bel", 42)]["p_follows"] == 0.0 and e7[("bel", 42)]["p_constant"] == 1.0 and e7[("bel", 42)]["verdict_e7"].startswith("CONSTANT")
    assert e7[("bel", 42)]["p_agree_model"] == pytest.approx(20 / 60)
    md = (tmp_path / "res" / "rc2.md").read_text()
    assert "| ctx | 42 |" in md and "READS THE CONTEXT + READS THE MODEL" in md and "160/160 = 100%" in md
    assert "## E7" in md and "READS THE MODEL (switches with it)" in md and "20/94" in md
    for f in ("rc2.csv", "rc2_e7.csv", "rc2_summary.json"):
        assert (tmp_path / "res" / f).exists()


def test_verdict_rules_directly():
    ok_shuf = {"k": 48, "n": 96, "p": 0.5, "lo": 0.4, "hi": 0.6}
    ok_nosys = {"k": 90, "n": 96, "p": 0.94, "lo": 0.87, "hi": 0.97}

    def rate(k, n):
        p, lo, hi = ST.wilson(k, n)
        return {"k": k, "n": n, "p": p, "lo": lo, "hi": hi}

    assert P.verdict(rate(50, 60), rate(2, 34), ok_nosys, ok_shuf) == "READS THE CONTEXT + READS THE MODEL"
    assert P.verdict(rate(50, 60), rate(20, 34), ok_nosys, ok_shuf) == "READS THE CONTEXT (not the model)"
    assert P.verdict(rate(50, 60), rate(2, 6), ok_nosys, ok_shuf) == "READS THE CONTEXT (model: not testable)"
    assert P.verdict(rate(5, 60), rate(2, 34), ok_nosys, ok_shuf) == "READS THE BELIEF"
    assert P.verdict(rate(30, 60), rate(2, 34), ok_nosys, ok_shuf) == "MIXED"
    assert P.verdict(rate(20, 20), rate(2, 34), ok_nosys, ok_shuf) == "UNDERPOWERED"
    assert P.verdict(rate(50, 60), rate(2, 34), {**ok_nosys, "p": 0.6}, ok_shuf) == "NOT READING (nosys gate)"
    assert P.verdict(rate(50, 60), rate(2, 34), ok_nosys, {"k": 80, "n": 96, "p": 0.83, "lo": 0.74, "hi": 0.9}).startswith("SHUFFLED")
    # E7
    assert P.verdict_e7(rate(18, 20), rate(1, 20)) == "READS THE MODEL (switches with it)"
    assert P.verdict_e7(rate(1, 20), rate(18, 20)) == "CONSTANT (text or belief, not the model)"
    assert P.verdict_e7(rate(10, 20), rate(8, 20)) == "MIXED"
    assert P.verdict_e7(rate(11, 11), rate(0, 11)).startswith("UNDERPOWERED")
    assert (P.READS_HI, P.READS_LO, P.MIN_COMPLIERS, P.MIN_NONCOMPLIERS, P.NOSYS_GATE, P.MIN_SWITCHING) == (0.75, 0.25, 24, 12, 0.75, 12)


# ------------------------------------------------------------------ PRESENT reference: leave-pair-out probe
D_SYN = 32


@pytest.fixture
def synthetic_states(tmp_path, items, synthetic):
    """States for the planted arm at L24 (noise) and L42 (noise + a direction carrying the model's side, i.e. complier
    vs non-complier per item, so it follows the model's switches between paraphrases)."""
    rng = np.random.default_rng(0)
    sdir = tmp_path / "states"
    (sdir / P.DATASET).mkdir(parents=True)
    ordered = sorted(items, key=lambda it: it["item_id"])
    (sdir / P.DATASET / "index.json").write_text(json.dumps({"item_ids": [it["item_id"] for it in ordered]}))
    d = rng.standard_normal(D_SYN)
    d /= np.linalg.norm(d)
    side = np.array([1.0 if _complies(it) else -1.0 for it in ordered])
    base = rng.standard_normal((len(ordered), D_SYN))
    np.save(sdir / P.DATASET / "chat_L24.npy", base.astype(np.float16))
    np.save(sdir / P.DATASET / "chat_L42.npy", (base + 3.0 * side[:, None] * d[None, :]).astype(np.float16))
    return sdir


def test_probe_present_finds_the_model_side_at_42_not_24(tmp_path, items, synthetic, synthetic_states):
    po, lo = synthetic
    sel = P.select(items, po, None)
    pr = P.probe_present(sel, layers=(24, 42), states_dir=synthetic_states, n_perm=2, n_boot=100, seed=0, out_dir=tmp_path / "res")
    by = {r["layer"]: r for r in pr["per_layer"]}
    assert by[42]["trainable"] and by[42]["n"] == 282 and by[42]["n_compliers"] == 160 and by[42]["n_noncompliers"] == 122 and by[42]["n_pairs"] == 47
    assert by[42]["auroc"] > 0.95 and by[42]["ci_lo"] > 0.9
    assert by[42]["acc_compliers"]["p"] > 0.9 and by[42]["acc_noncompliers"]["p"] > 0.9
    assert by[42]["e7"]["follows"]["n"] == 20 and by[42]["e7"]["follows"]["p"] > 0.8
    assert 0.3 < by[24]["auroc"] < 0.7 and by[24]["null_n"] == 2 and 0.3 < by[24]["null_auroc_mean"] < 0.7
    assert pr["L_probe"] == 42
    assert set(by[42]["c_chosen"]) <= set(P.C_GRID) and sum(by[42]["c_chosen"].values()) == 47
    assert len(by[42]["scores"]) == 282
    assert (tmp_path / "res" / P.PROBE_JSON).exists() and (tmp_path / "res" / "rc2_probe.csv").exists()
    assert P.load_probe(tmp_path / "res")["L_probe"] == 42


def test_leave_pair_out_never_sees_the_held_out_pair():
    """A label that is a pure function of pair identity is perfectly fit in-sample and unlearnable out of pair."""
    rng = np.random.default_rng(1)
    n_pairs, per = 24, 6
    groups = np.repeat(np.arange(n_pairs), per)
    y = np.repeat((np.arange(n_pairs) % 2), per)
    X = np.zeros((n_pairs * per, n_pairs + 4), dtype=np.float32)
    X[np.arange(n_pairs * per), groups] = 1.0  # one-hot pair identity
    X[:, n_pairs:] = rng.standard_normal((n_pairs * per, 4))
    scores, cs = P.leave_pair_out_scores(X, y, groups, seed=0)
    assert np.isfinite(scores).all() and len(cs) == n_pairs
    assert P._auroc(y, scores) < 0.65
    in_sample = P._fit_logreg(X, y, 1.0).decision_function(X)
    assert P._auroc(y, in_sample) > 0.99


def test_probe_not_trainable_when_minority_small(tmp_path, items, synthetic_states):
    sel_items = [{"item_id": it["item_id"], "pair_id": it["pair_id"], "base_item_id": it["base_item_id"], "paraphrase": it["paraphrase"],
                  "status": "non_complier" if it["pair_index"] == 0 else "complier", "base_status": "constant_complier"} for it in items]
    pr = P.probe_present({"items": sel_items, "summary": {}}, layers=(42,), states_dir=synthetic_states, n_perm=0, n_boot=10, out_dir=None)
    r = pr["per_layer"][0]
    assert not r["trainable"] and r["n_noncompliers"] == 6 and pr["L_probe"] is None and "note" in r


def test_summarize_h3_reader_vs_probe(tmp_path, items, synthetic, synthetic_states):
    po, lo = synthetic
    sel = P.select(items, po, None)
    pr = P.probe_present(sel, layers=(24, 42), states_dir=synthetic_states, n_perm=0, n_boot=50, out_dir=tmp_path / "res")
    S = P.summarize(sel, lo, tmp_path / "res", n_boot=100, seed=0)  # reads rc2_probe.json from out_dir
    by = {(r["reader"], r["layer"]): r for r in S["table"]}
    assert by[("ctx", 42)]["auroc_model"] == 1.0 and by[("ctx", 42)]["n_kept"] == 282
    assert by[("bel", 42)]["auroc_model"] == 0.5  # constant lo: no ranking of the model's side
    h3 = S["h3"]
    assert h3["L_probe"] == 42 and h3["probe_trainable"]
    rd = {r["reader"]: r for r in h3["readers"]}
    assert rd["ctx"]["L_reader"] == 42 and rd["ctx"]["lag"] == 0
    assert rd["bel"]["L_reader"] is None and rd["bel"]["lag"] is None
    assert rd["ctx"]["per_layer"][0]["probe_auroc"] == pytest.approx(pr["per_layer"][1]["auroc"])
    md = (tmp_path / "res" / "rc2.md").read_text()
    assert "## PRESENT reference" in md and "| ctx | 42 | 42 | 0 |" in md
    assert (tmp_path / "res" / "rc2_h3.csv").exists()
    S2 = P.summarize(sel, lo, tmp_path / "res2", n_boot=50, seed=0)  # no probe file there
    assert S2["h3"] is None and "No probe results" in (tmp_path / "res2" / "rc2.md").read_text()


def test_summarize_reads_several_files_and_prefers_qualified_keys(tmp_path, items, synthetic):
    """The rerun splits R-C2 rows over reader_lo.RC2b.jsonl (readers) and reader_lo.RC2bNLA.jsonl (NLA); an old-format
    row (no dataset in the key) must lose to a dataset-qualified one whatever the file order."""
    po, lo = synthetic
    sel = P.select(items, po, None)
    it = items[0]
    old_dir = tmp_path / "cache"
    old_dir.mkdir()
    # file A: an old-format nosys-less run with a WRONG planted row for item 0 (lo = -9); file B: the qualified rerun (+9)
    a = old_dir / "reader_lo.RC2.jsonl"
    a.write_text(json.dumps({**_lo_row(P.DATASET, it, "nla", 42, "natural", -9.0), "key": f"nla|L42|chat|{it['item_id']}"}) + "\n")
    b = old_dir / "reader_lo.RC2bNLA.jsonl"
    b.write_text(json.dumps({**_lo_row(P.DATASET, it, "nla", 42, "natural", 9.0), "key": P.lo_key("nla", 42, P.DATASET, it["item_id"])}) + "\n")
    (old_dir / "superseded").mkdir()
    (old_dir / "superseded" / "reader_lo.X.jsonl").write_text("{}\n")
    assert [p.name for p in P.reader_lo_files(old_dir)] == ["reader_lo.RC2.jsonl", "reader_lo.RC2bNLA.jsonl"]
    for order in ([a, b], [b, a]):
        rows = P.load_rc2_rows(order, (P.DATASET,))
        assert len(rows) == 1 and rows[0]["lo"] == 9.0, order
    S = P.summarize(sel, [lo, b, a], tmp_path / "res", n_boot=50)
    nla = {(r["reader"], r["layer"]): r for r in S["table"]}[("nla", 42)]
    assert nla["n_complier_items"] == 1 and nla["p_context_compliers"] == 1.0  # the +9 row, not the -9 one
    assert {(r["reader"], r["layer"]) for r in S["table"]} >= {("ctx", 42), ("bel", 42), ("bad", 42), ("nla", 42)}


# ------------------------------------------------------------------ R-C2-F1 follow-up
def _f1_world(items, rng, reader_rule):
    """Non-compliers: author pairs 09, 14 and element pairs 17, 19 (version A, all paraphrases) = 12 items; the model's
    belief strength (nosys LO, more negative = stronger) is strongest on those. reader_rule(item, strength) -> lo."""
    sel_items, rows = [], []
    for it in items:
        k, cat = it["pair_index"], it["category"]
        nc = k in (8, 13, 16, 18) and it["version"] == "A"
        strength = -(3.0 if nc else 1.0) - 0.3 * rng.random()
        sel_items.append({"item_id": it["item_id"], "pair_id": it["pair_id"], "base_item_id": it["base_item_id"], "paraphrase": it["paraphrase"],
                          "category": cat, "status": "non_complier" if nc else "complier", "base_status": "constant", "lo_nosys": strength,
                          "lo_planted": (-0.5 if nc else 1.5) + 0.2 * rng.random()})
        for ds in (P.DATASET, P.DATASET_NOSYS):
            rows.append({"reader": "lens", "layer": 42, "dataset": ds, "condition": "natural", "item_id": it["item_id"], "unscorable": False,
                         "lo": reader_rule(it, strength, ds)})
    return {"items": sel_items, "summary": {}}, rows


def test_followup_f1_belief_strength_world(tmp_path, items):
    """Reader lo tracks the belief strength on the planted arm (stronger belief -> more context), zero on the nosys arm."""
    rng = np.random.default_rng(0)
    sel, rows = _f1_world(items, rng, lambda it, st, ds: (-st - 1.5 + 0.1 * rng.standard_normal()) if ds == P.DATASET else 0.05 * rng.standard_normal())
    F = P.followup_f1(sel, rows, n_boot=200, seed=0, out_dir=tmp_path)
    r = {(x["reader"], x["layer"]): x for x in F["table"]}[("lens", 42)]
    assert r["n_nc"] == 12 and r["n_comp"] == 276 and F["n_nc_items"] == 12 and len(F["twins"]) == 12  # 4 pairs x 3 paraphrases, version A
    assert r["p_context_nc"]["p"] == 1.0 and r["m2_rho_nosys"]["rho"] < -0.5 and r["m2_rho_nosys"]["hi"] < 0
    assert r["m1_within_author"]["diff"] > 0.3 and r["m1_within_author"]["lo"] > 0
    assert r["m3_delta"]["diff"] > 1.0 and r["m3_delta"]["lo"] > 0
    assert "H-belief" in r["flags"] and "H-name" not in r["flags"]
    assert (tmp_path / "rc2_f1.md").exists() and (tmp_path / "rc2_f1.csv").exists() and (tmp_path / "rc2_f1.json").exists()
    assert "H-belief" in (tmp_path / "rc2_f1.md").read_text()


def test_followup_f1_name_prior_world(tmp_path, items):
    """Reader lo is a preference for a fixed name: positive when the preferred name is the context, negative on the twin
    where it is the belief; no relation to belief strength. The twins test must fire, H-belief must not."""
    rng = np.random.default_rng(1)
    pref = {it["pair_id"]: it["primary"]["candidates"][0] for it in items if it["version"] == "A" and it["paraphrase"] == 0}  # version A's context name
    sel, rows = _f1_world(items, rng, lambda it, st, ds: (2.0 if it["primary"]["candidates"][0] == pref[it["pair_id"]] else -2.0) + 0.1 * rng.standard_normal())
    F = P.followup_f1(sel, rows, n_boot=200, seed=0, out_dir=None)
    r = F["table"][0]
    assert r["m4_twins"]["a"]["p"] == 0.0 and r["m4_twins"]["diff"] < -0.3 and r["m4_twins"]["hi"] < 0
    assert "H-name" in r["flags"] and "H-belief" not in r["flags"]


def test_followup_f1_no_verdict_for_nla(items):
    rng = np.random.default_rng(2)
    sel, rows = _f1_world(items, rng, lambda it, st, ds: -1.0)
    for r in rows:
        r["reader"] = "nla"
    F = P.followup_f1(sel, rows, n_boot=50, seed=0, out_dir=None)
    assert F["table"][0]["flags"] == ["no verdict (fails the shuffled gate)"] and F["table"][0]["rule_layer"] is False


# ------------------------------------------------------------------ PODS.md rule 5: smoke coverage assertion
def _cover(tmp_path, items, phase="A", drop=None, bad_key=False):
    tmp_path.mkdir(parents=True, exist_ok=True)
    smoke = P.smoke_items(items)
    po, ll, lo, sf = (tmp_path / n for n in ("prompt_only.S.jsonl", "logit_lens.S.jsonl", "reader_lo.S.jsonl", "state_free.S.jsonl"))
    arms = [P.arm_dataset(P.DATASET, True), P.arm_dataset(P.DATASET_NOSYS, True)]
    readers = {"A": {"jlens": P.RC.READ_LAYERS["jlens"], "olens": P.RC.READ_LAYERS["olens"], "skip_a": (42,)}, "B": {"nla": (42,)}}[phase]
    with po.open("w") as fpo, ll.open("w") as fll, lo.open("w") as flo, sf.open("w") as fsf:
        for d in arms:
            for it in smoke:
                if phase == "A":
                    fpo.write(json.dumps({"dataset": d, "item_id": it["item_id"]}) + "\n")
                    if d.startswith(P.DATASET):
                        fpo.write(json.dumps({"dataset": d + P.FC_SUFFIX, "item_id": it["item_id"]}) + "\n")
                    fll.write(json.dumps({"dataset": d, "item_id": it["item_id"]}) + "\n")
                for rd, Ls in readers.items():
                    for L in Ls:
                        for cond in ("natural", "shuf"):
                            if drop == ("lo", d, rd, L, cond):
                                continue
                            key = P.lo_key(rd, L, d, it["item_id"], shuf=(cond == "shuf")) if not bad_key else f"{rd}|L{L}|chat|{it['item_id']}"
                            flo.write(json.dumps({"key": key, "dataset": d, "reader": rd, "layer": L, "condition": cond, "item_id": it["item_id"]}) + "\n")
                        if drop != ("sf", d, rd, L):
                            fsf.write(json.dumps({"dataset": d, "reader": rd, "layer": L, "item_id": it["item_id"]}) + "\n")
    return {"po": po, "ll": ll, "lo": lo, "sf": sf}


def test_smoke_assert_passes_on_full_coverage(tmp_path, items, capsys):
    paths = _cover(tmp_path, items)
    rep = P.smoke_assert("A", ("planted", "nosys"), ["jlens", "olens", "skip_a"], None, smoke=True, paths=paths, log=False)
    n_lo = 2 * (12 + 5 + 1) * 2   # arms x (jlens 12 layers + olens 5 + skip 1) x (natural, shuf)
    n_sf = 2 * (12 + 5 + 1)
    assert rep["n_missing"] == 0 and rep["n_cells"] == 2 * 2 + 1 + n_lo + n_sf and min(rep["counts"].values()) == 12
    assert "SMOKE OK" in capsys.readouterr().out
    repB = P.smoke_assert("B", ("planted", "nosys"), [], None, smoke=True, paths=_cover(tmp_path / "b", items, phase="B"), log=False)
    assert repB["n_cells"] == 2 * 3 and repB["n_missing"] == 0


def test_smoke_assert_fails_loudly_on_an_empty_cell(tmp_path, items, capsys):
    d = P.arm_dataset(P.DATASET_NOSYS, True)
    paths = _cover(tmp_path, items, drop=("lo", d, "olens", 48, "shuf"))
    with pytest.raises(SystemExit) as e:
        P.smoke_assert("A", ("planted", "nosys"), ["jlens", "olens", "skip_a"], None, smoke=True, paths=paths, log=False)
    assert e.value.code == 1
    out = capsys.readouterr().out
    assert f"SMOKE FAILED: missing lo/{d}/olens/48/shuf" in out and out.count("SMOKE FAILED") == 1
    # the exact failure of 2026-10-19: a whole arm with no reader rows
    paths2 = _cover(tmp_path / "two", items)
    paths2["lo"].write_text("".join(l for l in paths2["lo"].read_text().splitlines(True) if f'"{d}"' not in l))
    with pytest.raises(SystemExit):
        P.smoke_assert("A", ("planted", "nosys"), ["jlens", "olens", "skip_a"], None, smoke=True, paths=paths2, log=False)
    assert capsys.readouterr().out.count("SMOKE FAILED: missing lo/" + d) == 2 * (12 + 5 + 1)


def test_smoke_assert_rejects_keys_without_the_dataset(tmp_path, items, capsys):
    paths = _cover(tmp_path, items, bad_key=True)
    with pytest.raises(SystemExit):
        P.smoke_assert("A", ("planted", "nosys"), ["jlens", "olens", "skip_a"], None, smoke=True, paths=paths, log=False)
    assert "reader_lo keys without the dataset" in capsys.readouterr().out


def test_expected_cells_follow_the_layer_override():
    cells = P.expected_cells("A", ("planted",), ["jlens"], [42, 44], smoke=False)
    assert ("po", P.DATASET) in cells and ("po", P.DATASET + P.FC_SUFFIX) in cells and ("ll", P.DATASET) in cells
    assert ("lo", P.DATASET, "jlens", 42, "natural") in cells and ("lo", P.DATASET, "jlens", 48, "natural") not in cells
    assert sum(c[0] == "sf" for c in cells) == 2
