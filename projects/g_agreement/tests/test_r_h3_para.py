"""H3 paraphrase side module (BRIEF_R §14; ``r_bench/h3_para.py``). CPU, MOCK (tiny Qwen3.5 + character tokenizer of
``test_readers_mock``); nothing is written under results/ or cache/.

  - the committed paraphrase file matches its pinned sha and the module's templates; every R-A question is covered,
    verbatim, with the candidate order the template says;
  - a paraphrase equal to the frozen FC prompt reproduces ``collect.collect_prompt_only``'s lp exactly (same scorer);
  - rows: keys, LO sign independent of the offer order, resume, output outside the prompt_only / reader_lo globs;
  - the §4.9 (f) majority key; the CI-10 pairs are fixed and blind to data.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_r_h3_para.py -q``
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

torch = pytest.importorskip("torch")
pytest.importorskip("transformers")

from projects.g_agreement.core import accounting as A  # noqa: E402
from projects.g_agreement.core import config as C  # noqa: E402
from projects.g_agreement.core import model as M  # noqa: E402
from projects.g_agreement.r_bench import analyze as AN  # noqa: E402
from projects.g_agreement.r_bench import bank as B  # noqa: E402
from projects.g_agreement.r_bench import collect as RC  # noqa: E402
from projects.g_agreement.r_bench import datasets as D  # noqa: E402
from projects.g_agreement.r_bench import h3_para as H  # noqa: E402
from projects.g_agreement.tests.test_readers_mock import FakeTok, tiny_model  # noqa: E402

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
    monkeypatch.setattr(RC, "RESULTS", tmp_path / "results")
    monkeypatch.setattr(C, "RESULTS_DIR", tmp_path / "results_root")
    monkeypatch.setattr(A.C, "COMPUTE_LEDGER", tmp_path / "compute.jsonl")
    RC.RUN_META.clear()
    RC.set_shard(None, H.SUFFIX)
    RC.set_cache_dir(tmp_path / "cache_r")
    RC._LEDGERS.clear()
    RC._SHAS.clear()
    yield
    RC._LEDGERS.clear()
    RC._DONE.clear()
    RC._SHAS.clear()
    RC.RUN_META.clear()
    RC.set_shard(None)


def mock_bank(tmp_path: Path) -> Path:
    items = []
    for ds in ("92_glue_sst2", "66_living-room"):
        sp = D.SPECS[ds]
        for split, n in (("test", 5), ("pool", 3)):
            for k in range(n):
                items.append({"item_id": f"r-{ds}-{split}-{k:04d}", "dataset": ds, "tag": sp.tag, "split": split, "label": k % 2,
                              "raw_target": str(k % 2), "prompt_text": f"A short text number {k} about {ds}.", "render": "chat",
                              "system": None, "primary": {"name": ds, "question": sp.question, "candidates": [sp.pos, sp.neg],
                                                          "template": sp.template, "sided": sp.sided, "jlens": [sp.jlens_pos, sp.jlens_neg]}})
    p = tmp_path / "items_r.json"
    p.write_text(json.dumps({"meta": {"mock": True}, "items": items}))
    return p


# ------------------------------------------------------------------ the paraphrase file
def test_paraphrase_file_pinned_and_complete():
    d = H.load_paraphrases()
    assert C.sha256_file(H.PARA_FILE) == H.PARA_SHA256
    assert set(d["datasets"]) == set(D.SPECS) and len(d["datasets"]) == 113
    for name, row in d["datasets"].items():
        sp = D.SPECS[name]
        for k, t in H.TEMPLATES.items():
            u = row[k]
            assert sp.question in u and u.count("{text}") == 1 and "{first}" not in u and "{second}" not in u
            i_pos, i_neg = u.rindex(f'"{sp.pos}"'), u.rindex(f'"{sp.neg}"')
            assert (i_neg < i_pos) == t["swap"], (name, k)
    assert H.KEY_PARAS == ("p1", "p2") and H.TEMPLATES["p2"]["swap"] and not H.TEMPLATES["p1"]["swap"]


def test_load_refuses_other_sha(tmp_path):
    p = tmp_path / "h3_paraphrases.json"
    p.write_text(H.PARA_FILE.read_text().replace("Passage:", "Passage :"))
    with pytest.raises(SystemExit, match="refusing"):
        H.load_paraphrases(p)


# ------------------------------------------------------------------ scoring
def test_frozen_wording_reproduces_collect_prompt_only(target, tmp_path, monkeypatch):
    bank = mock_bank(tmp_path)
    monkeypatch.setattr(B, "ITEMS_R", bank)
    items = [it for it in B.load_items(bank, "all", ["92_glue_sst2"])]
    table = copy.deepcopy(H.load_paraphrases())
    table["datasets"]["92_glue_sst2"]["p1"] = table["datasets"]["92_glue_sst2"]["frozen"]
    H.collect_para(target, "92_glue_sst2", items, "p1", table, batch=4, cache=tmp_path / "c")
    RC.collect_prompt_only(target, "92_glue_sst2", items, batch=4)
    mine = {r["item_id"]: r for r in A.read_jsonl(H.para_path(tmp_path / "c"))}
    ref = {r["item_id"]: r for r in A.read_jsonl(RC.PO_PATH)}
    for iid, r in ref.items():
        assert abs(mine[iid]["lp_pos"] - r["lp_pos"]) < 1e-4 and abs(mine[iid]["lp_neg"] - r["lp_neg"]) < 1e-4
        assert mine[iid]["model_says_pos"] == r["model_says_pos"]


def test_rows_order_resume_and_globs(target, tmp_path, monkeypatch):
    bank = mock_bank(tmp_path)
    monkeypatch.setattr(B, "ITEMS_R", bank)
    table = H.load_paraphrases()
    cache = tmp_path / "cache_r"
    items = B.load_items(bank, "all", ["92_glue_sst2"])
    for k in H.TEMPLATES:
        assert H.collect_para(target, "92_glue_sst2", items, k, table, batch=4, cache=cache) == len(items)
    rows = A.read_jsonl(H.para_path(cache))
    assert len(rows) == 3 * len(items) and {r["paraphrase"] for r in rows} == {"p1", "p2", "p3"}
    r = [x for x in rows if x["paraphrase"] == "p2"][0]
    assert r["key"] == f"po|92_glue_sst2|{r['item_id']}|p2" and r["swap"] is True and r["candidates"] == ["positive", "negative"]
    assert r["lo"] == pytest.approx(r["lp_pos"] - r["lp_neg"]) and r["model_says_pos"] == (r["lp_pos"] > r["lp_neg"])
    assert r["paraphrase_file_sha256"] == H.PARA_SHA256 and r["condition"] == "paraphrase"
    RC._DONE.clear()
    assert H.collect_para(target, "92_glue_sst2", items, "p1", table, batch=4, cache=cache) == 0   # resumed
    assert H.para_path(cache) not in AN.shard_files(cache, "prompt_only") + AN.shard_files(cache, "reader_lo")
    assert not list(cache.glob("prompt_only*.jsonl"))


# ------------------------------------------------------------------ key and CI-10
def test_majority_key():
    fz = {"a": {"model_says_pos": True}, "b": {"model_says_pos": True}, "c": {"model_says_pos": False}}
    para = {("a", "p1"): {"model_says_pos": True}, ("a", "p2"): {"model_says_pos": True}, ("a", "p3"): {"model_says_pos": False},
            ("b", "p1"): {"model_says_pos": False}, ("b", "p2"): {"model_says_pos": False},
            ("c", "p1"): {"model_says_pos": True}}
    k = {r["item_id"]: r for r in H.model_key(fz, para, ["a", "b", "c"])}
    assert k["a"]["key_model_pos"] is True and k["a"]["stable"] and k["a"]["stable4"] is False and not k["a"]["flips_vs_frozen"]
    assert k["b"]["key_model_pos"] is False and not k["b"]["stable"] and k["b"]["flips_vs_frozen"]
    assert k["c"]["key_model_pos"] is None   # p2 missing: no key


def test_ci10_pairs_fixed():
    p = H.ci10_pairs()
    assert p == H.ci10_pairs() and len(p) == 20 and p[:4] == list(H.CI10_NAMED)
    assert len({f for f, _ in p}) == 20 and len({g for _, g in p}) == 20
    for f, g in p[4:]:
        assert D.SPECS[f].tag != D.SPECS[g].tag and D.SPECS[f].sided == "two"
        assert f not in H.LABEL_DEFECT and g not in H.LABEL_DEFECT
    it = H.transplant([{"item_id": "x", "dataset": "36_sciq_tf", "label": 1, "primary": {}}], "120_us_timezone_Chicago")[0]
    assert it["primary"]["name"] == "120_us_timezone_Chicago" and it["label"] == 1 and it["g_dataset"] == "36_sciq_tf"


def test_zz_results_untouched():
    """Isolation guard: no test in this module wrote, created, moved or deleted anything under the guarded
    trees (per path, this process only, so concurrent pods and sessions cannot trip it; tests/_write_guard.py)."""
    _GUARD.assert_clean()
