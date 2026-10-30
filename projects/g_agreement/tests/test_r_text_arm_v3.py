"""Text arm v3 tests (BRIEF_R §13 note "text arm v3"; ``r_bench/text_arm_v3.py``). CPU, MOCK, fixtures of ``test_r_text_arm``.

  - the derangement is the frozen shuffled control's (no fixed point; same seed rule), the mean arm injects one vector per fact;
  - CLI: rows for both arms × renders, state_item_id, resume, file names; the smoke assertion fails loudly on a missing arm;
  - analysis: real signal + deranged none → ADDS_INFORMATION / NO_FORMAT_EFFECT; deranged = real → FORMAT_EFFECT.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_r_text_arm_v3.py -q``
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
from projects.g_agreement.r_bench import text_arm_v3 as V3  # noqa: E402
from projects.g_agreement.tests.test_r_text_arm import freeze, mock_config, mock_olens, target, write_bank  # noqa: E402,F401

# Monitor this test process only; concurrent experiment outputs are legitimate.
from projects.g_agreement.tests import _write_guard as WG
_GUARD = WG.ModuleWriteGuard([REPO / "results" / "g_agreement", REPO / "cache" / "g_agreement"])
_write_guard = _GUARD.fixture()


def test_frozen_derangement_and_control_states():
    its = [{"item_id": f"r-x-test-{k:04d}"} for k in range(7)]
    pi = V3.frozen_derangement("92_glue_sst2", its)
    perm = RC.derangement(7, np.random.default_rng(RC.SHUFFLE_SEED + RC.stable_offset("92_glue_sst2")))
    assert pi == {its[i]["item_id"]: its[perm[i]]["item_id"] for i in range(7)}
    assert all(k != v for k, v in pi.items()) and sorted(pi.values()) == sorted(pi)
    ids = sorted(pi)[::-1]                       # a different row order than the bank order
    H = torch.arange(7 * 3, dtype=torch.float32).reshape(7, 3)
    Hs, sids = V3.control_states(V3.NAME_SHUF, H, ids, pi)
    for k, iid in enumerate(ids):
        assert sids[k] == pi[iid] and torch.equal(Hs[k], H[ids.index(pi[iid])])
    Hm, sm = V3.control_states(V3.NAME_MEAN, H, ids, pi)
    assert torch.allclose(Hm, H.mean(0).repeat(7, 1)) and sm == [None] * 7


def _cli(target, tmp_path, monkeypatch, extra):
    bank = write_bank(tmp_path)
    freeze([bank])
    monkeypatch.setattr("projects.g_agreement.g1_agreement.collect.load_target_timed", lambda module, ledger_path=None: target)
    monkeypatch.setattr(RC, "bind_readers", lambda t, names, scales=None: [mock_olens(t)])
    monkeypatch.setattr(M, "unload", lambda t: None)
    monkeypatch.setattr(RC, "git_sha", lambda: "deadbeef" * 5)
    monkeypatch.setattr(V, "LAYER", 2)
    root = tmp_path / "cache_r"
    monkeypatch.setattr(V3, "STATES_ROOT", root)
    RC.set_cache_dir(root)
    from projects.g_agreement.r_bench import bank as Bk
    for ds, its in RC.items_by_dataset([i for i in Bk.load_items(bank, "all") if i["split"] == "test"]).items():
        V.capture_test_states(target, ds, RC.ordered_items(its), 2)   # v2's states_v2, as on the volume
    return V3.main(["--items-files", "items_r.json", "--pod", "TXT3", "--cache-dir", str(tmp_path / "cache_r"), "--batch", "8", *extra])


def test_cli_rows_resume(target, tmp_path, monkeypatch):
    assert _cli(target, tmp_path, monkeypatch, []) == 0
    out = V3.out_path()
    assert out == tmp_path / "cache_r" / "text_arm" / "text_arm_v3_lo.jsonl"
    assert RC.LOG.name == "log.TXT3.md" and RC.LEDGER_PATH.name == "compute.TXT3.jsonl"
    rows = A.read_jsonl(out)
    assert len(rows) == 3 * 6 * 2 * 2   # 3 facts × 6 test items × 2 arms × 2 renders
    shuf = [r for r in rows if r["reader"] == V3.NAME_SHUF]
    assert all(r["state_item_id"] != r["item_id"] and r["state_item_id"].split("-test-")[0] == r["item_id"].split("-test-")[0] for r in shuf)
    assert all(r["state_item_id"] is None for r in rows if r["reader"] == V3.NAME_MEAN)
    assert all(r["condition"] == V3.CONDITION and r["text_arm_v3_code_sha256"] == V3.code_sha() for r in rows)
    first = [r["reader"] for r in rows]
    assert first.index(V3.NAME_MEAN) == len(shuf)   # every fact of the deranged arm first (pre-registered order)
    RC._DONE.clear()
    assert _cli(target, tmp_path, monkeypatch, []) == 0 and len(A.read_jsonl(out)) == 72


def test_smoke_asserts_every_arm(target, tmp_path, monkeypatch, capsys):
    assert _cli(target, tmp_path, monkeypatch, ["--smoke", "2"]) == 0
    assert "SMOKE OK" in capsys.readouterr().out
    assert V3.smoke_missing(V3.out_path(), ["items_r.json"]) == []
    assert V3.smoke_missing(V3.out_path(), ["items_r.json", "items_rb.json"]) == [
        f"{a}/{rd}/items_rb.json" for a in V3.ARMS for rd in V.RENDERS]
    p = V3.out_path()
    p.write_text("".join(l for l in p.read_text().splitlines(True) if V3.NAME_MEAN not in l))
    assert V3.smoke_missing(p, ["items_r.json"]) == [f"{V3.NAME_MEAN}/chat/items_r.json", f"{V3.NAME_MEAN}/raw/items_r.json"]
    monkeypatch.setattr(V3, "smoke_missing", lambda path, banks: ["olens_txtq_mean/raw/items_r.json"])
    RC._DONE.clear()
    assert _cli(target, tmp_path, monkeypatch, ["--smoke", "2"]) == 3
    assert "SMOKE FAILED: missing olens_txtq_mean/raw/items_r.json" in capsys.readouterr().out


def _write(cache: Path, sig: dict[str, float]):
    rng = np.random.default_rng(0)
    v2, v3 = [], []
    for ds in ("92_glue_sst2", "93_x", "94_a", "95_b", "96_c", "97_d", "98_e", "99_f"):
        for k in range(200):
            y = k % 2
            com = {"dataset": ds, "tag": "TOPIC", "item_id": f"{ds}-{k}", "label": y, "sided": "two", "lp_A": 0.0, "items_file": "items_r.json"}
            v2.append({**com, "reader": V.NAME_A, "render": "text", "condition": V.CONDITION, "lo": float(sig["a"] * y + rng.standard_normal())})
            for rd in V.RENDERS:
                v2.append({**com, "reader": V.NAME_B, "render": rd, "condition": V.CONDITION, "lo": float(sig["b"] * y + rng.standard_normal())})
                for arm in V3.ARMS:
                    v3.append({**com, "reader": arm, "render": rd, "condition": V3.CONDITION, "lo": float(sig[arm] * y + rng.standard_normal())})
    (cache / "text_arm").mkdir(parents=True, exist_ok=True)
    V.out_path(cache).write_text("".join(json.dumps(r) + "\n" for r in v2))
    V3.out_path(cache).write_text("".join(json.dumps(r) + "\n" for r in v3))


def test_analysis_rules(tmp_path):
    cache = tmp_path / "c1"
    _write(cache, {"a": 0.0, "b": 2.0, V3.NAME_SHUF: 0.0, V3.NAME_MEAN: 0.0})   # the real state carries the signal
    rows = V3.analyze(cache, None, n_boot=300)
    assert {r["verdict"] for r in rows if r["contrast"] == "R"} == {"ADDS_INFORMATION"}
    s = {x["tag"]: x for x in V3.tag_summary(rows, "chat")}
    assert s["ALL"]["adds"] and s["ALL"]["format"] == "NO_FORMAT_EFFECT"
    cache2 = tmp_path / "c2"
    _write(cache2, {"a": 0.0, "b": 2.0, V3.NAME_SHUF: 2.0, V3.NAME_MEAN: 2.0})  # any injected vector gives the gain
    rows2 = V3.analyze(cache2, None, n_boot=300)
    s2 = {x["tag"]: x for x in V3.tag_summary(rows2, "raw")}
    assert not s2["ALL"]["adds"] and s2["ALL"]["format"] == "FORMAT_EFFECT"
    assert {x["tag"]: x for x in V3.tag_summary(rows2, "raw", "RM", "M")}["ALL"]["format"] == "FORMAT_EFFECT"
    assert "| ALL | chat | 8 |" in V3.summary_table(rows)


def test_incomplete_arm_is_left_out(tmp_path):
    cache = tmp_path / "c"
    _write(cache, {"a": 0.0, "b": 2.0, V3.NAME_SHUF: 0.0, V3.NAME_MEAN: 0.0})
    p = V3.out_path(cache)
    p.write_text("".join(l for l in p.read_text().splitlines(True) if not (V3.NAME_MEAN in l and '"raw"' in l and '"93_x-1"' in l)))
    rows = V3.analyze(cache, None, n_boot=100)
    assert not [r for r in rows if r["contrast"] in ("RM", "M") and r["dataset"] == "93_x"]
    assert [r for r in rows if r["contrast"] == "R" and r["dataset"] == "93_x"]


def test_zz_results_untouched():
    _GUARD.assert_clean()
