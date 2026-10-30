"""Text arm v2 tests (BRIEF_R §13; ``r_bench/text_arm_v2.py``). CPU, MOCK (the tiny model + character tokenizer of
``test_readers_mock``, fixtures shared with ``test_r_text_arm``); nothing is written under results/ or cache/.

  - prompts: Gemma's FC suffix verbatim, the Oracle's slot sentence, arm (a) / (b) layouts, braces in the text;
  - the embeds teacher forcing == ``collect.teacher_forced_lp`` without injection;
  - arm (b) with the marker's own embedding injected == arm (b) scored from plain ids (the slot is the right token);
  - the marker rule (first occurrence; prefix must be the frozen carrier's), batching invariance;
  - CLI: rows, keys, files, states, K2 rows, resume; analysis: contrasts, BH, verdict names, exclusions.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_r_text_arm_v2.py -q``
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
pytest.importorskip("transformers")

from projects.g_agreement.core import accounting as A  # noqa: E402
from projects.g_agreement.core import config as C  # noqa: E402
from projects.g_agreement.core import model as M  # noqa: E402
from projects.g_agreement.r_bench import collect as RC  # noqa: E402
from projects.g_agreement.r_bench import text_arm as T  # noqa: E402
from projects.g_agreement.r_bench import text_arm_v2 as V  # noqa: E402
from projects.g_agreement.tests.test_r_text_arm import TEXTS, freeze, mock_config, mock_olens, target, write_bank  # noqa: E402,F401

# Per-path, concurrency-proof isolation guard (tests/_write_guard.py; replaces the whole-tree snapshots, which other
# sessions' and pods' writes into the shared trees tripped). Records this process's writes into these roots.
from projects.g_agreement.tests import _write_guard as WG  # noqa: E402

_GUARD = WG.ModuleWriteGuard([REPO / "results" / "g_agreement"])
_write_guard = _GUARD.fixture()


def items_for(texts, cands=("A", "B"), question="Which?"):
    return [{"item_id": f"i{k}", "split": "test", "label": k % 2, "prompt_text": t,
             "primary": {"question": question, "candidates": list(cands)}} for k, t in enumerate(texts)]


# ------------------------------------------------------------------ prompts
def test_prompt_forms_match_gemma():
    from projects.r_gemma import config as G

    assert V.FC == G.AO_FC_SUFFIX
    assert V.SLOT == "An activation vector from layer {layer} of a language model is enclosed in activation tags: <activation>{char}</activation>."
    a = V.user_a("I {loved} it", "Is the review positive?", "yes", "no")
    assert a == ('An activation vector from layer 44 of a language model is enclosed in activation tags: <activation>I {loved} it</activation>.'
                 ' Is the review positive? Answer with exactly one of these two options and nothing else: "yes" or "no".')
    b = V.user_b("㈜", "I {loved} it", "Is the review positive?", "yes", "no")
    assert b.startswith(V.SLOT.format(layer=44, char="㈜") + "\nI {loved} it\nIs the review positive? Answer with")
    assert "Produce distinct concepts" not in a + b


def test_embeds_teacher_forcing_equals_frozen(target):
    tok = target.tokenizer
    rows = [V.head_ids(tok, "hello") + [5, 6], V.head_ids(tok, "a longer head here") + [7]]
    heads = [len(rows[0]) - 2, len(rows[1]) - 1]
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    got = V.teacher_forced_lp_embeds(target.model, rows, heads, pad, "cpu")
    want = RC.teacher_forced_lp(target.model, rows, heads, pad, "cpu")
    np.testing.assert_allclose(got, want, atol=1e-5)


def test_arm_b_with_marker_embedding_equals_plain_ids(target):
    """Inject h := the marker's own input embedding with alpha := ‖e‖: the slot then holds exactly what plain ids give."""
    reader = mock_olens(target)
    _ids, _slot, char, cid = reader.carrier(44)
    e = target.model.get_input_embeddings().weight[cid].detach().float()
    reader.alpha = float(e.norm())
    its = items_for(TEXTS[:3])
    inj = V.score_arm_b(reader, its, e[None].repeat(3, 1), 44, batch=4)
    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    for it, r in zip(its, inj):
        head = V.head_ids(tok, V.user_b(char, T.item_text(tok, it), "Which?", "A", "B"))
        assert r["marker_index"] == head.index(cid) and r["n_head_tokens"] == len(head)
        lp = RC.teacher_forced_lp(target.model, [head + V.LO.encode(tok, "A"), head + V.LO.encode(tok, "B")], [len(head)] * 2, pad, "cpu")
        assert abs(lp[0] - r["lp_A"]) < 1e-4 and abs(lp[1] - r["lp_B"]) < 1e-4


def test_marker_rule(target):
    reader = mock_olens(target)
    ids, slot, char, cid = reader.carrier(44)
    head = V.head_ids(target.tokenizer, V.user_b(char, f"text with {char} inside", "Q?", "A", "B"))
    assert head.count(cid) == 2 and V.marker_slot(head, cid, ids, slot) == slot
    with pytest.raises(RuntimeError):
        V.marker_slot([1, 2, 3], cid, ids, slot)
    bad = list(head)
    bad[1] = bad[1] + 1
    with pytest.raises(RuntimeError, match="differ"):
        V.marker_slot(bad, cid, ids, slot)


def test_injection_changes_scores_and_batching_does_not(target):
    reader = mock_olens(target)
    its = items_for(TEXTS)
    H = torch.randn(len(its), C.D_MODEL)
    b1 = V.score_arm_b(reader, its, H, 44, batch=2)
    b8 = V.score_arm_b(reader, its, H, 44, batch=8)
    np.testing.assert_allclose([r["lo"] for r in b1], [r["lo"] for r in b8], atol=1e-4)
    a1 = V.score_arm_a(reader, its, 44, batch=2)
    a8 = V.score_arm_a(reader, its, 44, batch=8)
    np.testing.assert_allclose([r["lo"] for r in a1], [r["lo"] for r in a8], atol=1e-4)
    b_other = V.score_arm_b(reader, its, -H, 44, batch=8)
    assert max(abs(x["lp_A"] - y["lp_A"]) for x, y in zip(b8, b_other)) > 1e-6
    assert all(r["marker_index"] is None for r in a8)


# ------------------------------------------------------------------ CLI
def test_cli_rows_states_repro_resume(target, tmp_path, monkeypatch):
    bank = write_bank(tmp_path)
    freeze([bank])
    monkeypatch.setattr("projects.g_agreement.g1_agreement.collect.load_target_timed", lambda module, ledger_path=None: target)
    monkeypatch.setattr(RC, "bind_readers", lambda t, names, scales=None: [mock_olens(t)])
    monkeypatch.setattr(M, "unload", lambda t: None)
    monkeypatch.setattr(RC, "git_sha", lambda: "deadbeef" * 5)
    monkeypatch.setattr(V, "LAYER", 2)   # the mock model has 4 blocks; the prompt still says the layer it is given
    args = ["--items-files", "items_r.json", "--pod", "TXT2", "--cache-dir", str(tmp_path / "cache_r")]
    monkeypatch.setattr(V, "N_REPRO", 3)
    assert V.main(args) == 0
    out = V.out_path()
    assert out == tmp_path / "cache_r" / "text_arm" / "text_arm_v2_lo.jsonl"
    assert RC.LOG.name == "log.TXT2.md" and RC.LEDGER_PATH.name == "compute.TXT2.jsonl"
    assert not list((tmp_path / "cache_r").glob("reader_lo*.jsonl"))
    rows = A.read_jsonl(out)
    assert len(rows) == 3 * 6 * 3   # 3 datasets × 6 test items × (arm a + arm b chat + arm b raw)
    ra = [r for r in rows if r["reader"] == V.NAME_A]
    rb = [r for r in rows if r["reader"] == V.NAME_B]
    assert len(ra) == 18 and {r["render"] for r in rb} == {"chat", "raw"}
    assert ra[0]["key"] == f"olens_txtq|L2|text|{ra[0]['item_id']}" and ra[0]["injection"] == "none"
    assert all(r["condition"] == V.CONDITION and r["text_arm_v2_code_sha256"] == V.code_sha() and r["pod"] == "TXT2" for r in rows)
    assert all(isinstance(r["marker_index"], int) for r in rb)
    assert (V.states_dir() / "92_glue_sst2" / "chat_L2.npy").exists()
    X = np.load(V.states_dir() / "92_glue_sst2" / "raw_L2.npy")
    assert X.shape == (6, C.D_MODEL) and X.dtype == np.float16
    rep = A.read_jsonl(V.repro_path())
    assert len(rep) == 3 * 3 * 2 and all(r["reader"] == "olens_repro" and r["format"] == "bullet" for r in rep)
    steps = {x["step"] for x in A.read_jsonl(RC.LEDGER_PATH)}
    assert {"lo_olens_txtq_L2", "lo_olens_txtq_act_chat_L2", "capture_v2_chat"} <= steps
    RC._DONE.clear()
    assert V.main(args) == 0
    assert len(A.read_jsonl(out)) == 54 and len(A.read_jsonl(V.repro_path())) == 18


# ------------------------------------------------------------------ analysis
def test_analyze_contrasts(tmp_path):
    cache = tmp_path / "cache_r"
    (cache / "text_arm").mkdir(parents=True)
    rng = np.random.default_rng(0)
    v2, act, t12 = [], [], []
    # 92: the activation helps on top of the text (B > 0), the text+question beats the bare activation (A < 0)
    # 93: nothing anywhere; 139: excluded
    for ds, sig in (("92_glue_sst2", {"a": 1.0, "b": 3.0, "act": 0.1, "t12": 0.1}), ("93_x", {"a": 0.0, "b": 0.0, "act": 0.0, "t12": 0.0}),
                    ("139_news_class_Politics", {"a": 1.0, "b": 3.0, "act": 0.1, "t12": 0.1})):
        for k in range(200):
            y = k % 2
            iid = f"{ds}-{k}"
            com = {"dataset": ds, "tag": "TOPIC", "item_id": iid, "label": y, "sided": "two", "lp_A": 0.0, "items_file": "items_r.json",
                   "split": "test"}
            v2.append({**com, "key": V.key_a(iid), "reader": V.NAME_A, "render": "text", "condition": V.CONDITION,
                       "lo": float(sig["a"] * y + rng.standard_normal())})
            for rd in ("chat", "raw"):
                v2.append({**com, "key": V.key_b(iid, rd), "reader": V.NAME_B, "render": rd, "condition": V.CONDITION,
                           "lo": float(sig["b"] * y + rng.standard_normal())})
                act.append({**com, "key": f"olens|L44|{rd}|{iid}", "reader": "olens", "condition": "natural", "position": "last",
                            "layer": 44, "render": rd, "lo": float(sig["act"] * y + rng.standard_normal()), "unscorable": False})
            t12.append({**com, "key": f"olens_txt|L44|text|{iid}", "reader": "olens_txt", "condition": "text_arm",
                        "lo": float(sig["t12"] * y + rng.standard_normal())})
    V.out_path(cache).write_text("".join(json.dumps(r) + "\n" for r in v2))
    T.out_path(cache).write_text("".join(json.dumps(r) + "\n" for r in t12))
    (cache / "reader_lo.1.jsonl").write_text("".join(json.dumps(r) + "\n" for r in act))
    rows = V.analyze(cache, tmp_path / "v2.csv", n_boot=300)
    get = {(r["contrast"], r["render"], r["dataset"]): r for r in rows}
    assert not any(r["dataset"].startswith("139") for r in rows)
    assert get[("B", "chat", "92_glue_sst2")]["verdict"] == "STATE_ADDS"
    assert get[("A", "chat", "92_glue_sst2")]["verdict"] == "TEXT_SUFFICES"
    assert get[("B", "raw", "93_x")]["verdict"] == "NOT_DISTINGUISHED"
    assert get[("Q", "text", "92_glue_sst2")]["delta"] > 0.1 and "verdict" not in get[("Q", "text", "92_glue_sst2")]
    assert "| TOPIC | 2 |" in V.tag_table(rows, "B", "chat") and "| ALL | 2 |" in V.tag_table(rows, "Q", "text")
    assert (tmp_path / "v2.csv").read_text().startswith("contrast,dataset,tag")


def test_gemma_rows_keep_only_gemma_ra_facts(tmp_path):
    """The 108-fact file: R-A bank only, datasets in Gemma's Check 2 table, its label-defect facts out (regression: the
    first version wrote the 163-fact table, byte-identical to the WS3 sensitivity file)."""
    rg = tmp_path / "rg"
    rg.mkdir()
    (rg / "text_vs_activation.csv").write_text("form,render,dataset\nao,chat,92_glue_sst2\nao,chat,145_disease_class_digestive system diseases\n"
                                               "ao_yn,chat,93_x\n")
    rows = [{"bank": "items_r.json", "dataset": "92_glue_sst2"}, {"bank": "items_r.json", "dataset": "93_x"},
            {"bank": "items_r.json", "dataset": "145_disease_class_digestive system diseases"},
            {"bank": "items_rb.json", "dataset": "92_glue_sst2"}]
    assert V.gemma_rows(rows, rg) == [rows[0]]


def test_zz_results_untouched():
    """Isolation guard: no test in this module wrote, created, moved or deleted anything under the guarded
    trees (per path, this process only, so concurrent pods and sessions cannot trip it; tests/_write_guard.py)."""
    _GUARD.assert_clean()
