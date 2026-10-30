"""Offline tests for the G5 (planted binding) and G6 (self-choice) analysis scripts on MOCK fixtures.

All fixtures are written to pytest's tmp_path, prefixed mock_, never under results/ or cache/.
Run: .venv/bin/python -m pytest projects/g_agreement/tests/test_g5g6_analysis.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402
from projects.g_agreement.g5_planted import analyze as g5  # noqa: E402
from projects.g_agreement.g6_choice import analyze as g6  # noqa: E402
from projects.g_agreement.tests.test_analysis import SAMPLING, claim_for, make_mock_world  # noqa: E402

ALPHAS = (0.5, 1.0, 1.5)
K_NULL = 20


def jl(path: Path, rows):
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------------------
# G5 mock: readers with scripted behaviour
#   olens: separates natural states (lo=+4 for own candidate) and follows the edit (shift = -alpha*8 toward other)
#   nla:   separates weakly (lo=+1) and ignores the edit (shift 0)
#   jlens: separates (lo=+2) and follows only at alpha >= 1.0 -> "mixed"; one state unscorable
# --------------------------------------------------------------------------------------
def make_mock_g5(root: Path, flip_ok=True, frozen=True):
    root.mkdir(parents=True, exist_ok=True)
    p = make_mock_world(root / "base", frozen=frozen)
    _, items = U.load_items(p["items"])
    states = U.split_item_ids(items, "test", U.RELATION_FAMILIES)
    rng = np.random.default_rng(0)
    lo_rows, beh_rows, gens, claims = [], [], [], []
    base_lo = {"olens": 4.0, "nla": 1.0, "jlens": 2.0}
    for s in states:
        it = items[s]
        A, B = it["primary"]["answer"], [c for c in it["primary"]["candidates"] if c != it["primary"]["answer"]][0]
        common = {"pair_id": it["pair_id"], "state_item_id": s, "family": it["family"], "cand_A": A, "cand_B": B, "templates": ["t1"], "input_norm": 1000.0}
        for rd in ("olens", "nla", "jlens"):
            uns = (rd == "jlens" and s == states[0])
            lo_rows.append({**common, "reader": rd, "condition": "natural", "alpha": 0.0, "sign": 0, "null_k": None, "lo": base_lo[rd], "lp_A": -1.0, "lp_B": -1.0 - base_lo[rd], "dose_abs": 0.0, "unscorable": uns})
            for a in ALPHAS:
                sign = 1 if it["version"] == "A" else -1
                if rd == "olens":
                    shift = 8.0 * a
                elif rd == "nla":
                    shift = 0.0
                else:
                    shift = 6.0 if a >= 1.0 else 0.0
                lo_rows.append({**common, "reader": rd, "condition": "planted", "alpha": a, "sign": sign, "null_k": None, "lo": base_lo[rd] - shift, "lp_A": 0, "lp_B": 0, "dose_abs": 100 * a, "unscorable": uns})
                for k in range(K_NULL):
                    lo_rows.append({**common, "reader": rd, "condition": "null", "alpha": a, "sign": None, "null_k": k, "lo": base_lo[rd] + float(rng.normal(0, 0.5)), "lp_A": 0, "lp_B": 0, "dose_abs": 100 * a, "unscorable": uns})
        for a in ALPHAS:
            flipped = flip_ok and (a >= 1.0 or states.index(s) % 4 == 0)   # 0.5: 4/16; >=1.0: 16/16 when flip_ok
            beh_rows.append({"state_item_id": s, "condition": "planted", "alpha": a, "sign": 1 if it["version"] == "A" else -1, "null_k": None,
                             "answer_text": B if flipped else A, "parsed": B if flipped else A, "flipped_to_other": flipped})
            if a == 1.0:
                for k in range(K_NULL):
                    nf = (k == 0 and states.index(s) == 0)
                    beh_rows.append({"state_item_id": s, "condition": "null", "alpha": a, "sign": None, "null_k": k, "answer_text": A, "parsed": B if nf else A, "flipped_to_other": nf})
        beh_rows.append({"state_item_id": s, "condition": "natural", "alpha": None, "sign": None, "null_k": None, "answer_text": A, "parsed": A, "flipped_to_other": False})
        for rd in ("olens", "nla"):
            gid = f"g5|{rd}|{s}|planted"
            val = B if rd == "olens" else None
            gens.append({"gen_id": gid, "module": "g5", "method": rd, "condition": "planted", "item_id": s, "state_item_id": s, "sample_idx": 0, "seed": 1,
                         "input": {"fixed_instruction": "MOCK", "layer_in_prompt": 42, "visible_prompt": None, "prompt_ids_sha256": U.sha256_text("prompt:" + s), "injection": f"{rd}_mock",
                                   "activation_norm": 1000.0, "alpha": 1.0}, "sampling": dict(SAMPLING), "raw_output": val or "unclear", "native": {"samples": [val or "unclear"]},
                         "n_prompt_tokens": 60, "n_new_tokens": 20, "finish_reason": "eos", "wall_s": 5.0, "peak_mem_gb": 50.0, "model_sha": "mocksha", "adapter": "mock", "created_at": "mock"})
            claims.append(claim_for(gid, rd, it, "contradicts" if val else "unclear", val))
    paths = {"items": p["items"], "frozen_config": p["frozen_config"], "lo": jl(root / "mock_lo.jsonl", lo_rows), "behaviour": jl(root / "mock_behaviour.jsonl", beh_rows),
             "gens": jl(root / "mock_gens_g5.jsonl", gens), "claims": jl(root / "mock_claims_g5.jsonl", claims), "states": states}
    return paths


def g5_args(p, out, extra=()):
    return ["--items", str(p["items"]), "--lo", str(p["lo"]), "--behaviour", str(p["behaviour"]), "--gens", str(p["gens"]), "--claims", str(p["claims"]),
            "--frozen-config", str(p["frozen_config"]), "--out", str(out), "--n-boot", "200", *extra]


def test_g5_endpoints_and_decisions(tmp_path):
    p = make_mock_g5(tmp_path / "w")
    s = g5.main(g5_args(p, tmp_path / "out"))
    # E3: 4/16 at 0.5, 16/16 at 1.0 and 1.5; null flip 1/320 at 1.0
    f = s["E3_flip_rate_by_alpha"]
    assert f["0.5"]["planted"]["k"] == 4 and f["1.0"]["planted"]["k"] == 16 and f["1.5"]["planted"]["k"] == 16
    assert f["1.0"]["null"]["k"] == 1 and f["1.0"]["null"]["n"] == 320 and f["0.5"]["null"] is None
    assert s["valid_doses_E3_ge_0.75"] == [1.0, 1.5] and s["manipulation_failed"] is False and s["kill_K4_flip_at_1.5_below_0.5"] is False
    assert s["natural_behaviour_correct"]["k"] == 16
    r = s["readers"]
    # E1: every reader separates all 8 pairs; jlens has one unscorable state -> 7 pairs
    assert r["olens"]["E1_natural_separation"]["win_rate"] == pytest.approx({**r["olens"]["E1_natural_separation"]["win_rate"], "k": 8, "n": 8})
    assert r["olens"]["E1_natural_separation"]["auroc"]["est"] == 1.0
    assert r["jlens"]["E1_natural_separation"]["n_pairs_scored"] == 7 and r["jlens"]["n_unscorable_rows"] == 1 + 3 + 3 * K_NULL
    # E2: olens follows everywhere (16/16), nla never (0/16), jlens only at alpha >= 1 (15/15 scorable)
    assert r["olens"]["E2_follow_by_alpha"]["0.5"]["follow_rate"]["k"] == 16 and r["olens"]["E2_follow_by_alpha"]["1.5"]["follow_rate"]["k"] == 16
    assert r["nla"]["E2_follow_by_alpha"]["1.5"]["follow_rate"]["k"] == 0
    assert r["jlens"]["E2_follow_by_alpha"]["0.5"]["follow_rate"]["k"] == 0 and r["jlens"]["E2_follow_by_alpha"]["1.0"]["follow_rate"]["k"] == 15
    assert r["olens"]["E2_follow_by_alpha"]["1.0"]["null_follow_rate_loo"]["n"] == 320 and r["olens"]["E2_follow_by_alpha"]["1.0"]["null_follow_rate_loo"]["p"] < 0.25
    assert r["olens"]["E2_follow_by_alpha"]["1.0"]["mean_shift_toward_other"]["est"] == pytest.approx(8.0)
    assert abs(r["nla"]["E2_follow_by_alpha"]["1.0"]["null_band_shift"]["mean"]) < 0.3
    # decisions per the pre-registered rule
    assert r["olens"]["decision"]["verdict"] == "follows"
    assert r["nla"]["decision"]["verdict"] == "insensitive"
    assert r["jlens"]["decision"]["verdict"] == "follows"      # smallest VALID dose is 1.0, where jlens follows 15/15
    # E4 free readouts
    e4 = s["E4_free_readouts_after_planting"]
    assert e4["olens"]["asserts_planted_other"]["k"] == 16 and e4["nla"]["asserts_any"]["k"] == 0
    for f_ in ("fig_main.png", "g5.csv", "summary.json"):
        assert (tmp_path / "out" / f_).exists()
    assert not any(str(q).startswith(str(ROOT / "results")) for q in (tmp_path / "out").rglob("*"))


def test_g5_manipulation_failed_and_gates(tmp_path):
    p = make_mock_g5(tmp_path / "w", flip_ok=False)
    s = g5.main(g5_args(p, tmp_path / "out", ["--no-fig"]))
    assert s["manipulation_failed"] is True and s["kill_K4_flip_at_1.5_below_0.5"] is True and s["valid_doses_E3_ge_0.75"] == []
    assert all(d["decision"]["verdict"] == "manipulation_failed" for d in s["readers"].values())
    # E1 is reported regardless
    assert s["readers"]["olens"]["E1_natural_separation"]["win_rate"]["k"] == 8
    # frozen gate
    p2 = make_mock_g5(tmp_path / "w2", frozen=False)
    with pytest.raises(U.FrozenConfigError):
        g5.main(g5_args(p2, tmp_path / "out2", ["--no-fig"]))
    s2 = g5.main(g5_args(p2, tmp_path / "out2", ["--no-fig", "--allow-unfrozen"]))
    assert s2["frozen"] is False
    # a dev or non-relation state in lo.jsonl is leakage / wrong population
    rows = [json.loads(l) for l in p["lo"].read_text().splitlines()]
    rows[0]["state_item_id"] = "own-01A"
    jl(p["lo"], rows)
    with pytest.raises(U.SplitLeakageError):
        g5.main(g5_args(p, tmp_path / "out3", ["--no-fig"]))


def test_auroc():
    assert g5.auroc(np.array([3, 2, 1, 0]), np.array([1, 1, 0, 0])) == 1.0
    assert g5.auroc(np.array([0, 1, 2, 3]), np.array([1, 1, 0, 0])) == 0.0
    assert g5.auroc(np.array([1, 1, 1, 1]), np.array([1, 1, 0, 0])) == 0.5
    assert np.isnan(g5.auroc(np.array([1, 2]), np.array([1, 1])))


# --------------------------------------------------------------------------------------
# G6 mock: 8 choice pairs; target picks a scripted option; readers scripted
# --------------------------------------------------------------------------------------
OPTIONS = [("apple", "pear"), ("red", "blue"), ("cat", "dog"), ("seven", "nine"), ("mango", "plum"), ("green", "gold"), ("owl", "fox"), ("two", "six")]


def make_mock_g6(root: Path, first_rate=10, frozen=True, unparseable_items=(), split_files=False):
    root.mkdir(parents=True, exist_ok=True)
    base = make_mock_world(root / "base", frozen=frozen)
    items = []
    for k, (o1, o2) in enumerate(OPTIONS):
        for v in ("A", "B"):
            listed = [o1, o2] if v == "A" else [o2, o1]
            items.append({"item_id": f"choice-{k + 1:02d}{v}", "pair_id": f"choice-{k + 1:02d}", "version": v, "family": "choice", "split": "test", "template_id": f"choice-t{k % 4}",
                          "prompt_text": f"Choose either {listed[0]} or {listed[1]}; reply with the word only.", "render": "chat", "system": None,
                          "primary": {"name": "self_choice", "question": "Which option will the model choose?", "candidates": listed, "answer": None, "answer_source": "target_greedy", "answer_aliases": []},
                          "secondary": {"entities": [], "objects": [], "relation": None}, "target_answer_regex": None,
                          "construction": {"first_mentioned_candidate": listed[0]}, "notes": "MOCK"})
    meta = {"created": "mock", "n_pairs": 8, "families": ["choice"], "sha256_items": U.canonical_items_sha(items), "frozen": False}
    (root / "mock_items_g6.json").write_text(json.dumps({"meta": meta, "items": items}), encoding="utf-8")
    by_id = {it["item_id"]: it for it in items}
    ids = sorted(by_id)
    states_meta, gens, extra, claims = [], [], [], []
    for n, i in enumerate(ids):
        it = by_id[i]
        sha = U.sha256_text("prompt:" + i)
        states_meta.append({"item_id": i, "model_id": "m", "model_sha": "mocksha", "layer": 42, "hook": "block_output", "hidden_states_index": 43, "pos": 9, "n_tokens": 10,
                            "read_token": "\n", "prompt_ids_sha256": sha, "render": "chat", "enable_thinking": False, "dtype_capture": "bfloat16", "dtype_saved": "float32", "norm": 900.0 + n, "captured_at": "mock", "pre_answer": True})
        first, second = it["primary"]["candidates"]
        chosen = first if n < first_rate else second
        base_row = {"module": "g6", "condition": "genuine", "item_id": i, "state_item_id": i, "sample_idx": 0, "seed": n, "sampling": dict(SAMPLING), "n_prompt_tokens": 20, "n_new_tokens": 5,
                    "finish_reason": "eos", "wall_s": 1.0, "peak_mem_gb": 50.0, "model_sha": "mocksha", "created_at": "mock"}
        inp = lambda m: {"fixed_instruction": "MOCK", "layer_in_prompt": None if m == "jlens" else 42, "visible_prompt": None, "prompt_ids_sha256": sha, "injection": "none" if m == "jlens" else f"{m}_mock", "activation_norm": 900.0 + n}  # noqa: E731
        ttext = "I cannot decide." if i in unparseable_items else chosen.capitalize() + "."
        gens.append({**base_row, "gen_id": f"g6|target|{i}|s0", "method": "target", "adapter": "none", "input": {**inp("target"), "visible_prompt": it["prompt_text"]}, "raw_output": ttext, "native": {"text": ttext}})
        scored = dict(it); scored["primary"] = {**it["primary"], "answer": chosen}
        other = second if chosen == first else first
        # nla: names the chosen option (consistent 16/16); olens: consistent on A only, unclear on B; jlens: always unclear
        beh = {"nla": ("supports", chosen), "olens": ("supports", chosen) if it["version"] == "A" else ("unclear", None), "jlens": ("unclear", None)}
        for m, (st, val) in beh.items():
            gid = f"g6|{m}|{i}|s0"
            gens.append({**base_row, "gen_id": gid, "method": m, "adapter": "mock", "input": inp(m), "raw_output": val or "", "native": {"tokens": ["x"] * 10, "scores": [0.1] * 10} if m == "jlens" else {"samples": [val or "hmm"]}})
            claims.append(claim_for(gid, m, scored, st, val, relation="absent", entities=[]))
        for src in ("random_same_norm", "mean_dev_activation"):
            gid = f"g6|jlens_null|{i}|{src}"
            gens.append({**base_row, "gen_id": gid, "method": "jlens_null", "condition": "noise_ceiling", "state_item_id": None, "adapter": "none",
                         "input": {**inp("jlens"), "prompt_ids_sha256": None, "injection_source": src}, "raw_output": "", "native": {"tokens": ["x"] * 10, "scores": [0.1] * 10}})
            claims.append(claim_for(gid, "jlens_null", scored, "supports" if n % 4 == 0 else "unclear", chosen if n % 4 == 0 else None, relation="absent", entities=[]))
        # prompt-only: always the first-listed option (consistent exactly when the target chose first-listed); state-free nla: always 'other'
        po_val = first
        gid = f"g6|prompt_only|{i}|s0"
        extra.append({**base_row, "gen_id": gid, "method": "prompt_only", "condition": "prompt_only", "state_item_id": None, "adapter": "none",
                      "input": {**inp("target"), "prompt_ids_sha256": None, "visible_prompt": "Which option will the model choose? " + it["prompt_text"]}, "raw_output": po_val, "native": {"text": po_val}})
        claims.append(claim_for(gid, "prompt_only", scored, "supports" if po_val == chosen else "contradicts", po_val, relation="absent", entities=[]))
        gid = f"g6|nla|{i}|state_free"
        extra.append({**base_row, "gen_id": gid, "method": "nla", "condition": "state_free", "state_item_id": None, "adapter": "mock",
                      "input": {**inp("nla"), "prompt_ids_sha256": None, "injection_source": "mean_dev_activation"}, "raw_output": other, "native": {"samples": [other]}})
        claims.append(claim_for(gid, "nla", scored, "contradicts", other, relation="absent", entities=[]))
    paths = {"items": root / "mock_items_g6.json", "frozen_config": base["frozen_config"], "states_meta": jl(root / "mock_states_meta_g6.jsonl", states_meta),
             "claims": jl(root / "mock_claims_g6.jsonl", claims)}
    if split_files:
        paths["gens"] = jl(root / "mock_gens_g6.jsonl", gens)
        paths["gens_extra"] = jl(root / "mock_gens_g6_extra.jsonl", extra)
    else:
        paths["gens"] = jl(root / "mock_gens_g6.jsonl", gens + extra)
        paths["gens_extra"] = None
    return paths


def g6_args(p, out, extra=()):
    a = ["--items", str(p["items"]), "--gens", str(p["gens"]), "--claims", str(p["claims"]), "--states-meta", str(p["states_meta"]),
         "--frozen-config", str(p["frozen_config"]), "--out", str(out), "--n-boot", "200", *extra]
    if p.get("gens_extra"):
        a += ["--gens-extra", str(p["gens_extra"])]
    return a


def test_g6_endpoints_and_decision(tmp_path):
    p = make_mock_g6(tmp_path / "w", first_rate=8, split_files=True)
    s = g6.main(g6_args(p, tmp_path / "out"))
    assert s["n_states_parseable"] == 16 and s["excluded_unparseable"] == [] and s["n_pairs"] == 8
    assert s["position_dominance"] == {**s["position_dominance"], "first_listed_chosen": 8, "dominated": False}
    assert s["E6_prompt_only_floor"]["consistent_all"]["k"] == 8             # prompt-only = first-listed heuristic
    e5 = s["E5_readers"]
    assert e5["nla"]["consistent_all"]["k"] == 16 and e5["nla"]["coverage"]["k"] == 16
    assert e5["nla"]["decision"]["verdict"] == "reads_the_choice" and e5["nla"]["minus_prompt_only"]["est"] == pytest.approx(8 / 16)
    assert e5["olens"]["consistent_all"]["k"] == 8 and e5["olens"]["decision"]["verdict"] == "no_evidence"
    assert e5["jlens"]["coverage"]["k"] == 0 and e5["jlens"]["decision"]["verdict"] == "no_evidence"
    assert set(e5["jlens"]["noise_ceiling_candidate_in_top10"]) == {"random_same_norm", "mean_dev_activation"}
    assert e5["nla"]["state_free"]["mean_dev_activation"]["consistent_all"]["k"] == 0   # the reader prior names the other option
    e7 = s["E7_nla_olens"]
    assert e7["agree"]["k"] == 8 and e7["missing"]["k"] == 8 and e7["contradict"]["k"] == 0 and e7["interpretable"] is True
    assert e7["kappa"]["n_both"] == 8 and e7["kappa"]["kappa"] == pytest.approx(1.0)
    assert len(s["items_g6_sha256"]) == 64
    for f_ in ("fig_main.png", "g6.csv", "summary.json"):
        assert (tmp_path / "out" / f_).exists()


def test_g6_dominance_unparseable_and_gates(tmp_path):
    p = make_mock_g6(tmp_path / "w", first_rate=15, unparseable_items=("choice-03B",))
    s = g6.main(g6_args(p, tmp_path / "out", ["--no-fig"]))
    assert s["excluded_unparseable"] == ["choice-03B"] and s["n_states_parseable"] == 15
    assert s["position_dominance"]["dominated"] is True and s["E7_nla_olens"]["interpretable"] is False
    assert "position-dominated" in s["E5_readers"]["nla"]["decision"]["reason"]
    # items with a filled answer are refused (the key must come from the target)
    d = json.loads(p["items"].read_text()); d["items"][0]["primary"]["answer"] = "apple"; p["items"].write_text(json.dumps(d))
    with pytest.raises(U.AnalysisError):
        g6.main(g6_args(p, tmp_path / "out2", ["--no-fig"]))
    # frozen gate
    p2 = make_mock_g6(tmp_path / "w2", frozen=False)
    with pytest.raises(U.FrozenConfigError):
        g6.main(g6_args(p2, tmp_path / "out3", ["--no-fig"]))
    assert g6.main(g6_args(p2, tmp_path / "out3", ["--no-fig", "--allow-unfrozen"]))["frozen"] is False
    # a verbalizer row whose activation norm does not match the cached state is refused (for NLA/OLens the recorded
    # prompt hash is that of the reader's own carrier prompt, so state_item_id + activation_norm is the state link)
    rows = [json.loads(l) for l in p2["gens"].read_text().splitlines()]
    nxt = next(r for r in rows if r["method"] == "olens" and r["condition"] == "genuine"); nxt["input"]["activation_norm"] = 1.0
    jl(p2["gens"], rows)
    with pytest.raises(U.SiteMismatchError):
        g6.main(g6_args(p2, tmp_path / "out4", ["--no-fig", "--allow-unfrozen"]))
