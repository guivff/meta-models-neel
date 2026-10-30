"""Text arm tests (BRIEF_R §12; ``r_bench/text_arm.py``). CPU, MOCK: the tiny Qwen3.5 model + character tokenizer of
``test_readers_mock`` stand in for the target with the Oracle's carrier; nothing is written under results/ or cache/.

  - the text carrier with the marker character as "text" is exactly the frozen ``olens_carrier`` render;
  - the text arm's LO with the marker character as text == the frozen ``lo_olens`` with the marker's own embedding injected
    (the two paths differ only in what fills the slot);
  - conversation serialization for system / earlier-turn items, truncation as the capture;
  - rows: key, run metadata (pod, git_sha, text_arm_code_sha256), resume, the TXT file names, ledger step;
  - the freeze check refuses a changed bank;
  - analysis: vectorised AUROC == sklearn, BH, verdicts, exclusions, the activation join.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_r_text_arm.py -q``
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
from projects.g_agreement.core import readers as R  # noqa: E402
from projects.g_agreement.core import scoring_lo as LO  # noqa: E402
from projects.g_agreement.r_bench import collect as RC  # noqa: E402
from projects.g_agreement.r_bench import datasets as D  # noqa: E402
from projects.g_agreement.r_bench import text_arm as T  # noqa: E402
from projects.g_agreement.tests.test_readers_mock import MOCK_D, FakeTok, tiny_model  # noqa: E402

# Per-path, concurrency-proof isolation guard (tests/_write_guard.py; replaces the whole-tree snapshots, which other
# sessions' and pods' writes into the shared trees tripped). Records this process's writes into these roots.
from projects.g_agreement.tests import _write_guard as WG  # noqa: E402

_GUARD = WG.ModuleWriteGuard([REPO / "results" / "g_agreement"])
_write_guard = _GUARD.fixture()


@pytest.fixture(scope="module")
def target():
    return M.Target(model=tiny_model(), tokenizer=FakeTok(), device="cpu", model_id="MOCK/tiny-qwen3_5",
                    revision="mock", model_class="Qwen3_5ForCausalLM")


@pytest.fixture(autouse=True)
def mock_config(monkeypatch, tmp_path):
    monkeypatch.setattr(C, "LAYER", 2)
    monkeypatch.setattr(C, "D_MODEL", MOCK_D)
    monkeypatch.setattr(RC, "RESULTS", tmp_path / "results")
    monkeypatch.setattr(RC, "FROZEN_R", tmp_path / "manifest" / "frozen_config_r.json")
    monkeypatch.setattr(C, "RESULTS_DIR", tmp_path / "results_root")
    monkeypatch.setattr(C, "DATASET_DIR", tmp_path / "dataset")
    monkeypatch.setattr(A.C, "COMPUTE_LEDGER", tmp_path / "compute.jsonl")
    RC.RUN_META.clear()
    RC.set_shard(None, T.SUFFIX)
    RC.set_cache_dir(tmp_path / "cache_r")
    RC._LEDGERS.clear()
    RC._SHAS.clear()
    yield
    RC._LEDGERS.clear()
    RC._DONE.clear()
    RC._SHAS.clear()
    RC.RUN_META.clear()
    RC.set_shard(None)


def mock_olens(target):
    reader = R.OLensReader()
    reader.target = target
    return reader


TEXTS = ["The movie was wonderful.", "I hated every minute of this film", "short", "A fine living room with a view, truly."]


def write_bank(tmp_path: Path) -> Path:
    items = []
    for ds, cands, sided in (("92_glue_sst2", ["A", "B"], "two"), ("66_living-room", ["X", "no such phrase"], "one"),
                             ("139_news_class_Politics", ["P", "Q"], "two")):
        for split, n in (("test", 6), ("pool", 2)):
            for k in range(n):
                y = k % 2
                items.append({"item_id": f"r-{ds}-{split}-{k:04d}", "dataset": ds, "tag": "TOPIC" if sided == "two" else "SURFACE",
                              "split": split, "label": y, "raw_target": str(y), "prompt_text": TEXTS[k % len(TEXTS)] + f" #{k}",
                              "render": "chat", "system": None,
                              "primary": {"name": ds, "question": "Which?", "candidates": cands, "answer": cands[0] if y else cands[1],
                                          "template": D.SPECS[ds].template, "sided": sided, "jlens": cands}})
    d = C.DATASET_DIR
    d.mkdir(parents=True, exist_ok=True)
    p = d / "items_r.json"
    p.write_text(json.dumps({"meta": {"mock": True}, "items": items}))
    return p


def freeze(paths: list[Path]) -> None:
    RC.FROZEN_R.parent.mkdir(parents=True, exist_ok=True)
    RC.FROZEN_R.write_text(json.dumps({"frozen": True, "items_sha256": {p.name: C.sha256_file(p) for p in paths}}))


# ------------------------------------------------------------------ prompt
def test_text_carrier_with_marker_is_the_frozen_carrier(target):
    reader = mock_olens(target)
    ids, slot, char, _cid = reader.carrier(44)
    assert T.text_carrier_ids(target.tokenizer, char, 44) == ids
    other = T.text_carrier_ids(target.tokenizer, "hello {world}", 44)
    assert target.tokenizer.decode(other).count("<activation>hello {world}</activation>") == 1


def test_item_text_conversations_and_truncation(target):
    tok = target.tokenizer
    it = {"item_id": "a", "prompt_text": "Who plays the trumpet?", "system": "Background: David plays the trumpet."}
    assert T.item_text(tok, it) == "System: Background: David plays the trumpet.\nUser: Who plays the trumpet?"
    msgs = [{"role": "user", "content": "Remember: Sarah is a florist."}, {"role": "assistant", "content": "Noted."},
            {"role": "user", "content": "Who is a florist?"}]
    it2 = {"item_id": "b", "prompt_text": "Who is a florist?", "capture_messages": msgs}
    assert T.item_text(tok, it2) == "User: Remember: Sarah is a florist.\nAssistant: Noted.\nUser: Who is a florist?"
    with pytest.raises(ValueError):
        T.item_text(tok, {**it2, "prompt_text": "different"})
    long = {"item_id": "c", "prompt_text": "x" * (RC.MAX_TOKENS + 50)}
    assert T.item_text(tok, long) == "x" * RC.MAX_TOKENS   # character tokenizer: one token per char


def test_text_lo_equals_frozen_lo_with_marker_embedding(target):
    """Same model, same rows: the frozen path injects alpha·unit(h) at the slot; with h := embedding of the marker char
    rescaled back (alpha := ‖e‖) the slot holds exactly the marker's own embedding, which is what the text arm feeds."""
    reader = mock_olens(target)
    ids, slot, char, cid = reader.carrier(44)
    e = target.model.get_input_embeddings().weight[cid].detach().float()
    reader.alpha = float(e.norm())
    frozen = LO.lo_olens(reader, e[None].repeat(2, 1), [("A", "B"), ("cat", "dog")], layer=44, batch=4)
    items = [{"item_id": f"i{k}", "prompt_text": char, "primary": {"candidates": list(p)}} for k, p in enumerate([("A", "B"), ("cat", "dog")])]
    mine = T.score_text_items(reader, items, 44, batch=4)
    for f, m in zip(frozen, mine):
        assert abs(f["lp_A"] - m["lp_A"]) < 1e-4 and abs(f["lp_B"] - m["lp_B"]) < 1e-4
        assert m["n_head_tokens"] == len(ids)


def test_batching_does_not_change_scores(target):
    reader = mock_olens(target)
    items = [{"item_id": f"i{k}", "prompt_text": t, "primary": {"candidates": ["A", "B"]}} for k, t in enumerate(TEXTS)]
    one = T.score_text_items(reader, items, 44, batch=2)
    many = T.score_text_items(reader, items, 44, batch=8)
    assert [r["cand_A"] for r in many] == ["A"] * len(TEXTS)
    np.testing.assert_allclose([r["lo"] for r in one], [r["lo"] for r in many], atol=1e-4)


# ------------------------------------------------------------------ rows, resume, CLI
def test_cli_rows_meta_resume_and_files(target, tmp_path, monkeypatch):
    bank = write_bank(tmp_path)
    freeze([bank])
    monkeypatch.setattr("projects.g_agreement.g1_agreement.collect.load_target_timed", lambda module, ledger_path=None: target)
    monkeypatch.setattr(RC, "bind_readers", lambda t, names, scales=None: [mock_olens(t)])
    monkeypatch.setattr(M, "unload", lambda t: None)
    monkeypatch.setattr(RC, "git_sha", lambda: "deadbeef" * 5)
    assert T.main(["--items-files", "items_r.json", "--pod", "TXT", "--cache-dir", str(tmp_path / "cache_r")]) == 0
    out = T.out_path()
    assert out == tmp_path / "cache_r" / "text_arm" / "text_arm_lo.jsonl"
    assert RC.LOG.name == "log.TXT.md" and RC.LEDGER_PATH.name == "compute.TXT.jsonl"
    assert not list((tmp_path / "cache_r").glob("reader_lo*.jsonl"))   # nothing under the reader_lo names
    rows = A.read_jsonl(out)
    assert len(rows) == 18   # 3 datasets × 6 test items; pool items never scored
    r = rows[0]
    assert r["key"] == f"olens_txt|L44|text|{r['item_id']}" and r["reader"] == "olens_txt" and r["render"] == "text"
    assert all(x["condition"] == "text_arm" for x in rows)
    assert r["pod"] == "TXT" and r["git_sha"] == "deadbeef" * 5 and r["text_arm_code_sha256"] == T.code_sha()
    assert r["items_sha256"] == C.sha256_file(bank) and r["injection"] == "none" and r["layer_in_prompt"] == 44
    one = [x for x in rows if x["dataset"] == "66_living-room"][0]
    assert one["sided"] == "one" and one["cand_B"] == "no such phrase"
    steps = [x["step"] for x in A.read_jsonl(RC.LEDGER_PATH)]
    assert "lo_olens_txt_L44" in steps
    assert "text arm" in RC.LOG.read_text()
    RC._DONE.clear()
    assert T.main(["--items-files", "items_r.json", "--pod", "TXT", "--cache-dir", str(tmp_path / "cache_r")]) == 0
    assert len(A.read_jsonl(out)) == 18   # resumed: nothing appended


def test_freeze_check_refuses_changed_bank(tmp_path):
    bank = write_bank(tmp_path)
    freeze([bank])
    assert T.check_shas(("items_r.json",)) == {"items_r.json": C.sha256_file(bank)}
    bank.write_text(bank.read_text().replace("wonderful", "terrible"))
    with pytest.raises(SystemExit, match="refusing"):
        T.check_shas(("items_r.json",))
    with pytest.raises(SystemExit):
        T.check_shas(("items_rb.json",))   # not in the manifest


# ------------------------------------------------------------------ analysis
def test_auroc_rows_matches_sklearn():
    from sklearn.metrics import roc_auc_score

    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, (5, 40))
    s = np.round(rng.standard_normal((5, 40)), 1)   # ties
    got = T.auroc_rows(y, s)
    for k in range(5):
        assert abs(got[k] - roc_auc_score(y[k], s[k])) < 1e-12


def test_bh_and_verdicts():
    q = T.bh([0.01, 0.04, 0.03, 0.5])
    np.testing.assert_allclose(q, [0.04, 0.16 / 3, 0.16 / 3, 0.5], atol=1e-9)
    assert T.verdict(0.1, 0.02, 0.2, 0.05) == "READ_FROM_STATE"
    assert T.verdict(0.1, 0.02, 0.2, 0.2) == "NOT_DISTINGUISHED"
    assert T.verdict(-0.1, -0.2, -0.01, 0.01) == "TEXT_SUFFICES"
    assert T.verdict(0.1, -0.01, 0.2, 0.01) == "NOT_DISTINGUISHED"


def test_analyze_join_exclusion_and_bh(tmp_path):
    cache = tmp_path / "cache_r"
    cache.mkdir()
    rng = np.random.default_rng(0)
    txt, act = [], []
    for ds, tag, strong in (("92_glue_sst2", "TOPIC", "act"), ("93_x", "TOPIC", "txt"), ("139_news_class_Politics", "TOPIC", "act")):
        for k in range(200):
            y = k % 2
            iid = f"{ds}-{k}"
            sig_a = 2.0 if strong == "act" else 0.2
            sig_t = 0.2 if strong == "act" else 2.0
            txt.append({"key": f"olens_txt|L44|text|{iid}", "reader": "olens_txt", "dataset": ds, "tag": tag, "item_id": iid,
                        "condition": "text_arm", "label": y, "sided": "two", "lo": float(sig_t * y + rng.standard_normal()), "lp_A": 0.0, "items_file": "items_r.json"})
            for render in ("chat", "raw"):
                act.append({"key": f"olens|L44|{render}|{iid}", "reader": "olens", "condition": "natural", "split": "test", "position": "last",
                            "layer": 44, "render": render, "dataset": ds, "item_id": iid, "label": y, "sided": "two",
                            "lo": float(sig_a * y + rng.standard_normal()), "lp_A": 0.0, "unscorable": False})
    act.append({**act[0], "condition": "shuf", "lo": 99.0})   # controls never join
    T.out_path(cache).parent.mkdir(parents=True)
    T.out_path(cache).write_text("".join(json.dumps(r) + "\n" for r in txt))
    (cache / "reader_lo.1.jsonl").write_text("".join(json.dumps(r) + "\n" for r in act) + '{"half": ')
    rows = T.analyze(cache, tmp_path / "out.csv", n_boot=300)
    chat = {r["dataset"]: r for r in rows if r["render"] == "chat"}
    assert set(chat) == {"92_glue_sst2", "93_x"}   # 139 excluded
    assert chat["92_glue_sst2"]["verdict"] == "READ_FROM_STATE" and chat["93_x"]["verdict"] == "TEXT_SUFFICES"
    assert chat["92_glue_sst2"]["n"] == 200
    assert (tmp_path / "out.csv").read_text().startswith("dataset,tag,bank")
    assert "| TOPIC | 2 |" in T.tag_table(rows, "chat", 44)
    sens = T.analyze(cache, tmp_path / "out_ex.csv", n_boot=300, extra_excluded=("93_x",))   # the sensitivity table drops it
    assert {r["dataset"] for r in sens if r["render"] == "chat"} == {"92_glue_sst2"}


def test_analyze_reader_lo_glob_skips_text_arm_rows(tmp_path):
    """analyze.py's ``read_jsonl_shards(cache, "reader_lo")`` (every reader_lo / reader_lo.<k> file) must not see the arm."""
    from projects.g_agreement.r_bench import analyze as AN

    cache = tmp_path / "cache_r"
    T.out_path(cache).parent.mkdir(parents=True)
    T.out_path(cache).write_text(json.dumps({"key": "olens_txt|L44|text|i0", "reader": T.NAME, "condition": T.CONDITION,
                                             "item_id": "i0", "lo": 1.0, "dataset": "92_glue_sst2", "pod": "TXT-x", "git_sha": "08d6a19"}) + "\n")
    (cache / "reader_lo.1.jsonl").write_text(json.dumps({"key": "olens|L44|chat|i0", "reader": "olens", "condition": "natural",
                                                         "item_id": "i0", "lo": 0.5, "dataset": "92_glue_sst2",
                                                         "pod": "A1", "git_sha": "4d482b612b0da5838b83e43a4c85656daec7f778"}) + "\n")
    assert T.out_path(cache) not in AN.shard_files(cache, "reader_lo")
    df = AN.read_jsonl_shards(cache, "reader_lo")
    assert list(df["reader"]) == ["olens"] and T.CONDITION not in set(df["condition"])


def test_zz_results_untouched():
    """Isolation guard: no test in this module wrote, created, moved or deleted anything under the guarded
    trees (per path, this process only, so concurrent pods and sessions cannot trip it; tests/_write_guard.py)."""
    _GUARD.assert_clean()
