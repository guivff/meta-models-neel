"""Offline tests for the G1–G4 analysis track on synthetic MOCK fixtures.

Every fixture is written to pytest's tmp_path (never under results/ or cache/) and is prefixed
mock_. The mock world follows INTERFACES.md §1–§8 closely enough that the real scripts run on it
end to end. Readout behaviour is scripted per (method, family, version) so expected counts can be
computed by hand.

Run: .venv/bin/python -m pytest projects/g_agreement/tests/test_analysis.py -q
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from projects.g_agreement.core import analysis_utils as U  # noqa: E402
from projects.g_agreement.g1_agreement import analyze as g1  # noqa: E402
from projects.g_agreement.g1_agreement import consensus as g1c  # noqa: E402
from projects.g_agreement.g2_relations import analyze as g2  # noqa: E402
from projects.g_agreement.g3_activation_dependence import analyze as g3  # noqa: E402
from projects.g_agreement.g4_repeats import analyze as g4  # noqa: E402

SAMPLING = {"temperature": 1.0, "top_p": 0.95, "top_k": 64, "max_new_tokens": 128, "do_sample": True}
FAM_SPECS = {
    "language": ("lang", "response_language", [("French", "German"), ("Spanish", "Italian"), ("Dutch", "Polish"), ("Greek", "Turkish"), ("Czech", "Danish")]),
    "tense": ("tense", "response_tense", [("past", "future")] * 5),
    "ownership": ("own", "key_owner", [("Mira", "Leo"), ("Ana", "Tom"), ("Ira", "Max"), ("Noa", "Eli"), ("Uma", "Raj")]),
    "mapping": ("map", "two_step_result", [("red", "blue"), ("cat", "dog"), ("east", "west"), ("gold", "iron"), ("oak", "elm")]),
}


# --------------------------------------------------------------------------------------
# scripted readout behaviours: (status, value) for a method on an item
# --------------------------------------------------------------------------------------
def behaviour_all_support(method, item):
    return "supports", item["primary"]["answer"]


def behaviour_mixed(method, item):
    """nla always supports; olens abstains on every B version; jlens contradicts on mapping."""
    key, other = item["primary"]["answer"], [c for c in item["primary"]["candidates"] if c != item["primary"]["answer"]][0]
    if method == "nla":
        return "supports", key
    if method == "olens":
        return ("unclear", None) if item["version"] == "B" else ("supports", key)
    if method == "jlens":
        return ("contradicts", other) if item["family"] == "mapping" else ("supports", key)
    return "supports", key


def claim_for(gen_id, method, item_scored, status, value, relation="correct", entities=None):
    return {"gen_id": gen_id, "method": method, "item_id": item_scored["item_id"], "extractor": "mock-rule",
            "primary": {"status": status, "value": value, "evidence": value or ""},
            "entities_mentioned": entities if entities is not None else list(item_scored["secondary"]["entities"]),
            "objects_mentioned": list(item_scored["secondary"]["objects"]),
            "relation": {"status": relation, "evidence": ""}, "truncated": False, "blind": True}


def score_text_against(value, item):
    """Re-score an asserted candidate against another item's key (used for the shuffled arm)."""
    if value is None:
        return "unclear", None
    cands = item["primary"]["candidates"]
    if value == item["primary"]["answer"]:
        return "supports", value
    if value in cands:
        return "contradicts", value
    return "unclear", None


def make_mock_world(root: Path, behaviour=behaviour_all_support, frozen=True, g4_sampling=None, frozen_sampling=None,
                    prompt_only_behaviour=behaviour_all_support) -> dict:
    """Write a complete mock artefact set under root and return the paths."""
    root.mkdir(parents=True, exist_ok=True)
    items = []
    for fam, (prefix, pname, cand_list) in FAM_SPECS.items():
        for k in range(1, 6):
            split = "dev" if k == 1 else "test"
            cands = list(cand_list[k - 1])
            for v in ("A", "B"):
                # balanced: even pairs A->cands[0]; odd pairs A->cands[1]
                ans = cands[0] if ((k % 2 == 0) == (v == "A")) else cands[1]
                other = [c for c in cands if c != ans][0]
                iid = f"{prefix}-{k:02d}{v}"
                items.append({
                    "item_id": iid, "pair_id": f"{prefix}-{k:02d}", "version": v, "family": fam, "split": split,
                    "template_id": f"{prefix}-t{k}", "prompt_text": f"[{fam}] {ans} holds the red key; {other} holds the blue key. Who holds the red key?",
                    "render": "chat", "system": None,
                    "primary": {"name": pname, "question": "primary?", "candidates": cands, "answer": ans, "answer_aliases": [ans.lower()]},
                    "secondary": {"entities": cands, "objects": ["red key", "blue key"], "relation": {"type": "has", "subject": ans, "object": "red key"}},
                    "target_answer_regex": rf"(?i)\b{ans}\b", "notes": "MOCK",
                })
    meta = {"created": "mock", "seed": 1, "n_pairs": 20, "families": list(FAM_SPECS), "sha256_items": U.canonical_items_sha(items), "frozen": frozen}
    (root / "mock_items.json").write_text(json.dumps({"meta": meta, "items": items}, ensure_ascii=False), encoding="utf-8")
    by_id = {it["item_id"]: it for it in items}

    states_meta, gens_g1, claims_g1, gens_g3, claims_g3, gens_g4, claims_g4 = [], [], [], [], [], [], []
    for n, it in enumerate(items):
        iid = it["item_id"]
        sha = U.sha256_text("prompt:" + iid)
        norm = 1000.0 + n
        states_meta.append({"item_id": iid, "model_id": "Qwen/Qwen3.6-27B", "model_sha": "mocksha", "layer": 42, "hook": "block_output",
                            "hidden_states_index": 43, "pos": 57, "n_tokens": 58, "read_token": "\n\n", "prompt_ids_sha256": sha, "render": "chat",
                            "enable_thinking": False, "dtype_capture": "bfloat16", "dtype_saved": "float32", "norm": norm, "captured_at": "mock", "pre_answer": True})
        base = {"module": "g1", "condition": "genuine", "item_id": iid, "state_item_id": iid, "sample_idx": 0, "seed": n,
                "sampling": dict(SAMPLING), "n_prompt_tokens": 60, "n_new_tokens": 40, "finish_reason": "eos", "wall_s": 5.0, "peak_mem_gb": 58.0,
                "model_sha": "mocksha", "created_at": "mock"}
        gens_g1.append({**base, "gen_id": f"g1|target|{iid}|s0", "method": "target", "adapter": "none", "sampling": {"temperature": 0.0, "do_sample": False, "max_new_tokens": 32},
                        "input": {"fixed_instruction": None, "layer_in_prompt": None, "visible_prompt": it["prompt_text"], "prompt_ids_sha256": sha, "injection": "none", "activation_norm": None},
                        "raw_output": it["primary"]["answer"], "native": {"text": it["primary"]["answer"]}})
        for m in U.METHODS:
            st, val = behaviour(m, it)
            gid = f"g1|{m}|{iid}|s0"
            inp = {"fixed_instruction": "MOCK instruction with marker", "layer_in_prompt": None if m == "jlens" else 42, "visible_prompt": None,
                   "prompt_ids_sha256": sha, "injection": "none" if m == "jlens" else f"{m}_mock", "activation_norm": norm}
            native = {"tokens": [val or "x"] * 10, "scores": [0.5] * 10} if m == "jlens" else {"samples": [f"The state suggests {val}." if val else "Hard to say."]}
            gens_g1.append({**base, "gen_id": gid, "method": m, "adapter": "mock", "input": inp, "raw_output": native.get("samples", [""])[0] if m != "jlens" else "", "native": native,
                            "wall_s": 0.2 if m == "jlens" else 5.0})
            claims_g1.append(claim_for(gid, m, it, st, val))
            if m != "jlens":
                for s in (1, 2):
                    gid4 = f"g4|{m}|{iid}|s{s}"
                    gens_g4.append({**base, "gen_id": gid4, "module": "g4", "condition": "repeat", "method": m, "sample_idx": s, "adapter": "mock", "input": inp,
                                    "sampling": dict(g4_sampling or SAMPLING), "raw_output": "", "native": {"samples": [f"{val}"]}})
                    claims_g4.append(claim_for(gid4, m, it, st, val))
        # G1 J-lens noise ceiling rows (no state): candidate in top-10 on 1 of every 4 items per source
        for src in ("random_same_norm", "mean_dev_activation"):
            gidn = f"g1|jlens_null|{iid}|{src}"
            hit = (n % 4 == 0)
            gens_g1.append({**base, "gen_id": gidn, "method": "jlens_null", "condition": "noise_ceiling", "state_item_id": None, "adapter": "none",
                            "input": {"fixed_instruction": None, "layer_in_prompt": None, "visible_prompt": None, "prompt_ids_sha256": None, "injection": "none",
                                      "injection_source": src, "activation_norm": norm},
                            "raw_output": "", "native": {"tokens": ["x"] * 10, "scores": [0.1] * 10}, "wall_s": 0.2})
            claims_g1.append(claim_for(gidn, "jlens_null", it, "supports" if hit else "unclear", it["primary"]["answer"] if hit else None, relation="absent", entities=[]))
        # G3 state-free reader-prior control rows (no state): the reader always asserts candidate 0
        for m in ("nla", "olens"):
            gidsf = f"g3|{m}|{iid}|state_free"
            v0 = it["primary"]["candidates"][0]
            stf = "supports" if v0 == it["primary"]["answer"] else "contradicts"
            gens_g3.append({**base, "gen_id": gidsf, "module": "g3", "condition": "state_free", "method": m, "state_item_id": None, "adapter": "mock",
                            "input": {"fixed_instruction": "MOCK", "layer_in_prompt": 42, "visible_prompt": None, "prompt_ids_sha256": None, "injection": f"{m}_mock",
                                      "injection_source": "mean_dev_activation", "activation_norm": norm},
                            "raw_output": v0, "native": {"samples": [v0]}})
            claims_g3.append(claim_for(gidsf, m, it, stf, v0))
        st, val = prompt_only_behaviour("prompt_only", it)
        gid3 = f"g3|prompt_only|{iid}|s0"
        gens_g3.append({**base, "gen_id": gid3, "module": "g3", "condition": "prompt_only", "method": "prompt_only", "state_item_id": None, "adapter": "none",
                        "sampling": {"temperature": 0.0, "do_sample": False, "max_new_tokens": 128},
                        "input": {"fixed_instruction": None, "layer_in_prompt": None, "visible_prompt": "Question: " + it["prompt_text"], "prompt_ids_sha256": None, "injection": "none", "activation_norm": None},
                        "raw_output": val or "", "native": {"text": val or ""}})
        claims_g3.append(claim_for(gid3, "prompt_only", it, st, val))

    # donors: test only, same family, different pair; half same-version, half other-version donors (labels not forced opposite)
    assignments = {}
    for fam, (prefix, _, _) in FAM_SPECS.items():
        for k in range(2, 6):
            dk = k + 1 if k < 5 else 2
            for v in ("A", "B"):
                dv = v if k % 2 == 0 else ("B" if v == "A" else "A")
                assignments[f"{prefix}-{k:02d}{v}"] = f"{prefix}-{dk:02d}{dv}"
    fams = list(FAM_SPECS)
    dev_assignments = {}
    for fi, fam in enumerate(fams):
        for v in ("A", "B"):
            dev_assignments[f"{FAM_SPECS[fam][0]}-01{v}"] = f"{FAM_SPECS[fams[(fi + 1) % 4]][0]}-01{v}"   # cross-family, dev only
    donors = {"seed": 7, "assignments": assignments, "dev_assignments": dev_assignments,
              "checks": {"same_family": True, "excludes_recipient_pair": True, "label_balance": {}}}
    claims_shuf = []
    g1_claims_by_id = {c["gen_id"]: c for c in claims_g1}
    for rec, don in {**assignments, **dev_assignments}.items():
        for m in U.METHODS:
            dval = U.vote(g1_claims_by_id[f"g1|{m}|{don}|s0"])
            st, val = score_text_against(dval, by_id[rec])
            row = claim_for(f"g1|{m}|{don}|s0", m, by_id[rec], st, val)
            row["condition"] = "shuffled_cached"
            claims_shuf.append(row)
    g4_pairs = {"seed": 3, "pairs": ["lang-02", "tense-03", "own-04", "map-05"], "chosen_before_test_outputs": True, "timestamp": "mock"}
    g4_pairs["item_ids"] = [p + v for p in g4_pairs["pairs"] for v in ("A", "B")]
    frozen_cfg = {"frozen": frozen, "sampling": dict(frozen_sampling or SAMPLING), "dataset_sha256": meta["sha256_items"], "note": "MOCK"}

    def jl(name, rows):
        p = root / name
        p.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
        return p

    paths = {
        "items": root / "mock_items.json", "states_meta": jl("mock_states_meta.jsonl", states_meta),
        "gens_g1": jl("mock_gens_g1.jsonl", gens_g1), "claims_g1": jl("mock_claims_g1.jsonl", claims_g1),
        "gens_g3": jl("mock_gens_g3.jsonl", gens_g3), "claims_g3": jl("mock_claims_g3.jsonl", claims_g3),
        "claims_shuffled": jl("mock_claims_g3_shuffled.jsonl", claims_shuf),
        "gens_g4": jl("mock_gens_g4.jsonl", gens_g4), "claims_g4": jl("mock_claims_g4.jsonl", claims_g4),
        "donors": root / "mock_donors.json", "g4_pairs": root / "mock_g4_pairs.json", "frozen_config": root / "mock_frozen_config.json",
        "items_obj": by_id, "assignments": assignments,
    }
    (root / "mock_donors.json").write_text(json.dumps(donors), encoding="utf-8")
    (root / "mock_g4_pairs.json").write_text(json.dumps(g4_pairs), encoding="utf-8")
    (root / "mock_frozen_config.json").write_text(json.dumps(frozen_cfg), encoding="utf-8")
    return paths


def common_args(p, out, extra=()):
    return ["--items", str(p["items"]), "--gens", str(p["gens_g1"]), "--claims", str(p["claims_g1"]), "--states-meta", str(p["states_meta"]),
            "--frozen-config", str(p["frozen_config"]), "--out", str(out), "--n-boot", "200", *extra]


def rewrite_jsonl(path: Path, fn):
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    rows = [fn(copy.deepcopy(r)) for r in rows]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------------------
# failure modes
# --------------------------------------------------------------------------------------
def test_split_leakage_raises(tmp_path):
    p = make_mock_world(tmp_path / "w")
    _, items = U.load_items(p["items"])
    test_ids = U.split_item_ids(items, "test")
    assert len(test_ids) == 32 and len(U.split_item_ids(items, "dev")) == 8
    with pytest.raises(U.SplitLeakageError):
        U.assert_split(items, test_ids + ["own-01A"], "test")
    # a frozen test run must contain no dev item
    s = g1.main(common_args(p, tmp_path / "o1", ["--split", "test", "--no-fig"]))
    assert set(s["items"]) == set(test_ids) and s["n_pairs"] == 16
    # dev and test are never mixed: a dev run has only dev items
    s = g1.main(common_args(p, tmp_path / "o2", ["--split", "dev", "--no-fig"]))
    assert all(items[i]["split"] == "dev" for i in s["items"]) and s["n_pairs"] == 4


def test_unfrozen_refuses_test_summaries(tmp_path):
    p = make_mock_world(tmp_path / "w", frozen=False)
    with pytest.raises(U.FrozenConfigError):
        g1.main(common_args(p, tmp_path / "o", ["--no-fig"]))
    with pytest.raises(U.FrozenConfigError):
        g1.main(common_args(p, tmp_path / "o", ["--allow-unfrozen", "--split", "test", "--no-fig"]))
    s = g1.main(common_args(p, tmp_path / "o", ["--allow-unfrozen", "--no-fig"]))
    assert s["split"] == "dev" and s["frozen"] is False
    # missing manifest file behaves the same
    with pytest.raises(U.FrozenConfigError):
        U.require_frozen(tmp_path / "does_not_exist.json", allow_unfrozen=False)
    # default output location for a dev run ends in /dev
    split, out = U.resolve_split_and_out("g1", None, False, None)
    assert split == "dev" and out.name == "dev" and out.parent.name == "g1"
    # dataset sha recorded in the manifest must match items.json
    _, items = U.load_items(p["items"])
    with pytest.raises(U.FrozenConfigError):
        U.check_dataset_sha({"sha256_items": "abc"}, items, {"frozen": True, "dataset_sha256": "def"})


def test_invalid_donor_assignment_raises(tmp_path):
    p = make_mock_world(tmp_path / "w")
    _, items = U.load_items(p["items"])
    good = {"assignments": dict(p["assignments"])}
    assert U.validate_donors(items, good) == p["assignments"]
    same_pair = copy.deepcopy(good)
    same_pair["assignments"]["own-02A"] = "own-02B"
    with pytest.raises(U.DonorAssignmentError, match="same pair"):
        U.validate_donors(items, same_pair)
    cross_fam = copy.deepcopy(good)
    cross_fam["assignments"]["own-02A"] = "map-03A"
    with pytest.raises(U.DonorAssignmentError, match="cross-family"):
        U.validate_donors(items, cross_fam)
    selfd = copy.deepcopy(good)
    selfd["assignments"]["own-02A"] = "own-02A"
    with pytest.raises(U.DonorAssignmentError):
        U.validate_donors(items, selfd)
    dev_donor = copy.deepcopy(good)
    dev_donor["assignments"]["own-02A"] = "own-01A"
    with pytest.raises(U.DonorAssignmentError, match="test-only"):
        U.validate_donors(items, dev_donor)
    incomplete = copy.deepcopy(good)
    del incomplete["assignments"]["own-02A"]
    with pytest.raises(U.DonorAssignmentError, match="cover exactly"):
        U.validate_donors(items, incomplete)
    # G3 also refuses a shuffled claim whose text does not come from the assigned donor
    rewrite_jsonl(p["claims_shuffled"], lambda r: {**r, "gen_id": "g1|nla|own-05A|s0"} if (r["item_id"] == "own-02A" and r["method"] == "nla") else r)
    with pytest.raises(U.DonorAssignmentError):
        g3.main(common_args(p, tmp_path / "o", ["--gens-prompt-only", str(p["gens_g3"]), "--claims-prompt-only", str(p["claims_g3"]),
                                                 "--claims-shuffled", str(p["claims_shuffled"]), "--donors", str(p["donors"]), "--no-fig"]))


def test_blind_sheet_leakage_raises():
    sid = U.make_sheet_id("g1|nla|own-03A|s0", salt="mock-salt")
    assert "own-03A" not in sid and len(sid) == 12
    clean = [{"sheet_id": sid, "method": "nla", "text": "The state suggests Mira."}]
    assert U.validate_blind_sheet(clean, item_ids=["own-03A", "own-03B"]) == 1
    with pytest.raises(U.BlindSheetLeakageError):  # the old gen_id key is itself leakage (it embeds item_id)
        U.validate_blind_sheet([{**clean[0], "gen_id": "g1|nla|own-03A|s0"}])
    with pytest.raises(U.BlindSheetLeakageError):
        U.validate_blind_sheet([{**clean[0], "item_id": "own-03A"}])
    with pytest.raises(U.BlindSheetLeakageError):
        U.validate_blind_sheet([{**clean[0], "answer": "Mira"}])
    with pytest.raises(U.BlindSheetLeakageError):  # any unexpected column is leakage until proven otherwise
        U.validate_blind_sheet([{**clean[0], "notes": "answer is Mira"}])
    with pytest.raises(U.BlindSheetLeakageError):  # a missing column is also a malformed sheet
        U.validate_blind_sheet([{"sheet_id": sid, "text": "x"}])
    with pytest.raises(U.BlindSheetLeakageError):  # item id as a substring of any field
        U.validate_blind_sheet([{**clean[0], "text": "(own-03A) The state suggests Mira."}], item_ids=["own-03A"])
    with pytest.raises(U.BlindSheetLeakageError):
        U.validate_blind_sheet([{**clean[0], "sheet_id": "own-03A-nla"}], item_ids=["own-03A"])
    with pytest.raises(U.BlindSheetLeakageError):  # answer-key material pasted into the text column
        U.validate_blind_sheet([{**clean[0], "text": "own-03A: Mira. The state suggests Mira."}], answer_strings=["own-03A: Mira"])


def test_activation_site_mismatch_raises(tmp_path):
    p = make_mock_world(tmp_path / "w")
    meta = U.load_states_meta(p["states_meta"])
    gens = U.load_gens(p["gens_g1"])
    assert U.validate_gens_against_states(gens, meta) == 200
    wrong_layer = copy.deepcopy(meta)
    wrong_layer["own-02A"]["layer"] = 41
    with pytest.raises(U.SiteMismatchError, match="layer"):
        U.validate_gens_against_states(gens, wrong_layer)
    wrong_hook = copy.deepcopy(meta)
    wrong_hook["own-02A"]["hook"] = "attn_output"
    with pytest.raises(U.SiteMismatchError, match="hook"):
        U.validate_gens_against_states(gens, wrong_hook)
    not_pre = copy.deepcopy(meta)
    not_pre["own-02A"]["pre_answer"] = False
    with pytest.raises(U.SiteMismatchError, match="pre_answer"):
        U.validate_gens_against_states(gens, not_pre)
    bad_sha = copy.deepcopy(gens)
    # verbalizer rows carry their own carrier-prompt hash (not checked against the state); the
    # J-lens row carries the state's render hash when present, so a corrupted one must raise
    row = next(g for g in bad_sha if g["gen_id"] == "g1|jlens|own-02A|s0")
    row["input"]["prompt_ids_sha256"] = "deadbeef"
    with pytest.raises(U.SiteMismatchError, match="prompt_ids_sha256"):
        U.validate_gens_against_states(bad_sha, meta)
    bad_lip = copy.deepcopy(gens)
    next(g for g in bad_lip if g["gen_id"] == "g1|olens|own-02A|s0")["input"]["layer_in_prompt"] = 40
    with pytest.raises(U.SiteMismatchError, match="layer_in_prompt"):
        U.validate_gens_against_states(bad_lip, meta)
    # and through the script: a corrupted states_meta file stops G1
    rewrite_jsonl(p["states_meta"], lambda r: {**r, "layer": 40} if r["item_id"] == "map-04B" else r)
    with pytest.raises(U.SiteMismatchError):
        g1.main(common_args(p, tmp_path / "o", ["--no-fig"]))


def _c(status, value=None):
    return {"gen_id": "m", "primary": {"status": status, "value": value, "evidence": ""}}


def test_vote_handling():
    # abstentions never agree with each other, self_contradictory never votes
    assert U.vote(_c("unclear")) is None and U.vote(_c("self_contradictory", "Mira")) is None
    assert U.classify_pair(_c("unclear"), _c("unclear")) == "missing"
    assert U.classify_pair(_c("self_contradictory", "Mira"), _c("supports", "Mira")) == "missing"
    assert U.classify_pair(_c("supports", "Mira"), _c("supports", "mira")) == "agree"
    assert U.classify_pair(_c("supports", "Mira"), _c("contradicts", "Leo")) == "contradict"
    # consensus buckets
    c = U.consensus({"nla": None, "olens": None, "jlens": None})
    assert not c.resolved and c.reason == "all_abstain" and c.bucket is None
    c = U.consensus({"nla": "Mira", "olens": "Leo", "jlens": None})
    assert not c.resolved and c.reason == "tie" and c.bucket is None
    c = U.consensus({"nla": "Mira", "olens": None, "jlens": None})
    assert c.resolved and c.bucket == 1 and c.value == "Mira" and not c.dissent
    c = U.consensus({"nla": "Mira", "olens": "Mira", "jlens": "Leo"})
    assert c.bucket == 2 and c.dissent and c.voters == ["nla", "olens"]
    c = U.consensus({"nla": "Mira", "olens": "Mira", "jlens": "Mira"})
    assert c.bucket == 3 and not c.dissent
    # a single vote with two abstentions is bucket 1, not an agreement of three
    assert U.consensus({"a": "X", "b": None, "c": None}).n_agree == 1
    # G4 unanimity rule: 3/3 needs three cast votes
    assert g4.rule_verdict(["X", "X", None], 3) is None and g4.rule_verdict(["X", "X", None], 2) == "X"
    assert g4.rule_verdict(["X", "Y", None], 2) is None and g4.rule_verdict([None, None, None], 1) is None
    # leave-one-out excludes the method's own vote
    v = {"nla": "Mira", "olens": None, "jlens": None}
    assert U.loo_consistency(v, "nla") == "unresolved"       # would be 'agree' if its own vote were counted
    assert U.loo_consistency(v, "olens") == "own_abstain"
    v = {"nla": "Mira", "olens": "Mira", "jlens": "Leo"}
    assert U.loo_consistency(v, "jlens") == "disagree"
    assert U.loo_consistency(v, "nla") == "unresolved"       # others tie 1–1
    v = {"nla": "Mira", "olens": "Mira", "jlens": "Mira"}
    assert U.loo_consistency(v, "jlens") == "agree"
    # value-vs-key check is independent of the status label
    item = {"primary": {"answer": "Mira", "answer_aliases": [], "candidates": ["Mira", "Leo"]}}
    assert U.claim_correct(_c("supports", "Mira"), item) is True and U.claim_correct(_c("unclear"), item) is None
    assert U.status_value_consistent(_c("supports", "Leo"), item) is False


def test_g4_reuse_requires_matching_sampling(tmp_path):
    # G4 samples drawn with another temperature: refuse
    p = make_mock_world(tmp_path / "w1", g4_sampling={**SAMPLING, "temperature": 0.7})
    args = common_args(p, tmp_path / "o1", ["--gens-g4", str(p["gens_g4"]), "--claims-g4", str(p["claims_g4"]), "--g4-pairs", str(p["g4_pairs"]), "--no-fig"])
    with pytest.raises(U.SamplingMismatchError):
        g4.main(args)
    # frozen config sampling differs from what the G1 first samples used: refuse
    p = make_mock_world(tmp_path / "w2", frozen_sampling={**SAMPLING, "max_new_tokens": 256})
    args = common_args(p, tmp_path / "o2", ["--gens-g4", str(p["gens_g4"]), "--claims-g4", str(p["claims_g4"]), "--g4-pairs", str(p["g4_pairs"]), "--no-fig"])
    with pytest.raises(U.SamplingMismatchError):
        g4.main(args)
    # frozen manifest without a sampling block cannot vouch for reuse
    p = make_mock_world(tmp_path / "w3")
    cfg = json.loads(p["frozen_config"].read_text())
    del cfg["sampling"]
    p["frozen_config"].write_text(json.dumps(cfg))
    with pytest.raises(U.FrozenConfigError):
        g4.main(common_args(p, tmp_path / "o3", ["--gens-g4", str(p["gens_g4"]), "--claims-g4", str(p["claims_g4"]), "--g4-pairs", str(p["g4_pairs"]), "--no-fig"]))
    # selection must be pre-registered
    p = make_mock_world(tmp_path / "w4")
    sel = json.loads(p["g4_pairs"].read_text())
    sel["chosen_before_test_outputs"] = False
    p["g4_pairs"].write_text(json.dumps(sel))
    with pytest.raises(U.AnalysisError):
        g4.main(common_args(p, tmp_path / "o4", ["--gens-g4", str(p["gens_g4"]), "--claims-g4", str(p["claims_g4"]), "--g4-pairs", str(p["g4_pairs"]), "--no-fig"]))


# --------------------------------------------------------------------------------------
# end-to-end on the mock world; hand-computed expectations
# --------------------------------------------------------------------------------------
def test_pipelines_all_support(tmp_path):
    p = make_mock_world(tmp_path / "w")
    out = tmp_path / "res"
    s1 = g1.main(common_args(p, out / "g1"))
    for m in U.METHODS:
        assert s1["per_method"][m]["accuracy_all"]["k"] == 32 and s1["per_method"][m]["accuracy_all"]["n"] == 32
        assert s1["per_method"][m]["coverage"]["k"] == 32
        assert s1["per_method"][m]["target_consistency_given_both"]["k"] == 32
    assert s1["all_three_agree"]["k"] == 32 and s1["pairwise"]["nla|olens"]["agree"]["k"] == 32
    assert (out / "g1" / "fig_main.png").exists() and (out / "g1" / "agreement.csv").exists() and (out / "g1" / "examples.md").exists()
    assert sum(1 for _ in open(out / "g1" / "agreement.csv")) == 1 + 16 * 3

    sc = g1c.main(common_args(p, out / "g1"))
    assert sc["buckets"]["3"]["n_states"] == 32 and sc["buckets"]["3"]["accuracy"]["k"] == 32 and sc["n_unresolved"] == 0
    assert all(sc["leave_one_out"][m]["consistency"]["k"] == 32 for m in U.METHODS)
    assert (out / "g1" / "consensus.csv").exists()

    s2 = g2.main(common_args(p, out / "g2"))
    assert s2["n_states"] == 16 and s2["n_pairs"] == 8
    for m in U.METHODS:
        d = s2["all_states"][m]
        assert d["entity_all"]["k"] == 16 and d["relation_correct"]["k"] == 16 and d["complete_pair_tracking"]["k"] == 8 and d["complete_pair_tracking"]["n"] == 8
    assert (out / "g2" / "fig_main.png").exists() and (out / "g2" / "relations.csv").exists()

    s3 = g3.main(common_args(p, out / "g3", ["--gens-prompt-only", str(p["gens_g3"]), "--claims-prompt-only", str(p["claims_g3"]),
                                             "--claims-shuffled", str(p["claims_shuffled"]), "--donors", str(p["donors"])]))
    same = s3["donor_assignment"]["donor_answer_equals_recipient_answer"]["k"]
    for m in U.METHODS:
        arms = s3["per_method"][m]["arms"]
        assert arms["genuine"]["accuracy_all"]["k"] == 32
        assert arms["shuffled_donor"]["accuracy_all"]["k"] == 32          # the cached text always tracks its donor
        assert arms["shuffled_recipient"]["accuracy_all"]["k"] == same   # ... and is right for the recipient only when labels coincide
    assert s3["prompt_only"]["accuracy_all"]["k"] == 32
    assert "not a fresh intervention" in s3["shuffled_arm_note"].lower() or "NOT a fresh intervention" in s3["shuffled_arm_note"]
    assert (out / "g3" / "fig_main.png").exists() and (out / "g3" / "g3.csv").exists()

    s4 = g4.main(common_args(p, out / "g4", ["--gens-g4", str(p["gens_g4"]), "--claims-g4", str(p["claims_g4"]), "--g4-pairs", str(p["g4_pairs"])]))
    assert s4["n_states"] == 8 and s4["n_pairs"] == 4
    for r, d in s4["rules"].items():
        assert d["coverage"]["k"] == 8 and d["accuracy_given_verdict"]["k"] == 8
    assert s4["rules"]["cross_2of3"]["compute"]["calls_per_state"] == 3
    assert s4["matched"]["2of3"]["n_matched_states"] == 8
    assert (out / "g4" / "fig_main.png").exists() and (out / "g4" / "g4.csv").exists()
    # nothing was written under results/
    assert not any(str(q).startswith(str(ROOT / "results")) for q in out.rglob("*"))


def test_pipelines_mixed_behaviour(tmp_path):
    """nla supports; olens unclear on every B; jlens contradicts on mapping -> hand-computed buckets."""
    p = make_mock_world(tmp_path / "w", behaviour=behaviour_mixed)
    out = tmp_path / "res"
    s1 = g1.main(common_args(p, out / "g1", ["--no-fig"]))
    assert s1["per_method"]["olens"]["coverage"]["k"] == 16          # only A versions
    assert s1["per_method"]["jlens"]["accuracy_all"]["k"] == 24      # wrong on 8 mapping states
    assert s1["per_method"]["jlens"]["coverage"]["k"] == 32
    pw = s1["pairwise"]
    assert pw["nla|olens"]["agree"]["k"] == 16 and pw["nla|olens"]["missing"]["k"] == 16 and pw["nla|olens"]["contradict"]["k"] == 0
    assert pw["nla|jlens"]["contradict"]["k"] == 8 and pw["nla|jlens"]["agree"]["k"] == 24
    assert pw["olens|jlens"]["contradict"]["k"] == 4 and pw["olens|jlens"]["agree"]["k"] == 12 and pw["olens|jlens"]["missing"]["k"] == 16
    assert s1["all_three_agree"]["k"] == 12
    sc = g1c.main(common_args(p, out / "g1"))
    # mapping B: nla key vs jlens other, olens abstains -> tie -> unresolved (4 states)
    assert sc["n_unresolved"] == 4 and sc["unresolved"] == {"tie": 4}
    # bucket 3: A versions of language/tense/ownership = 12; bucket 2: B of those (12) + mapping A (4, with dissent) = 16
    assert sc["buckets"]["3"]["n_states"] == 12 and sc["buckets"]["2"]["n_states"] == 16 and sc["buckets"]["2"]["with_dissent"] == 4
    assert sc["buckets"]["1"]["n_states"] == 0
    assert sc["buckets"]["2"]["accuracy"]["k"] == 16 and sc["buckets"]["3"]["accuracy"]["k"] == 12
    assert all(d["n_shared_wrong"] == 0 for d in sc["shared_wrong_by_family"].values())
    loo = sc["leave_one_out"]
    # jlens vs others: A versions -> nla+olens agree -> jlens agrees (12) / disagrees (4 mapping A); B versions -> only nla votes -> consensus of one -> agree 12 / disagree 4
    assert loo["jlens"]["counts"] == {"agree": 24, "disagree": 8}
    # olens: own abstains on all B (16); on A others are nla+jlens: agree except mapping A (tie) -> agree 12, unresolved 4
    assert loo["olens"]["counts"] == {"own_abstain": 16, "agree": 12, "unresolved": 4}
    # nla: on A others agree (12 agree) or tie on mapping A (4 unresolved); on B only jlens votes: agree 12, disagree 4 (mapping B)
    assert loo["nla"]["counts"] == {"agree": 24, "unresolved": 4, "disagree": 4}
    s4 = g4.main(common_args(p, out / "g4", ["--gens-g4", str(p["gens_g4"]), "--claims-g4", str(p["claims_g4"]), "--g4-pairs", str(p["g4_pairs"]), "--no-fig"]))
    r = s4["rules"]
    assert r["olens_3of3"]["coverage"]["k"] == 4 and r["nla_3of3"]["coverage"]["k"] == 8
    assert r["cross_3of3"]["coverage"]["k"] == 3            # A versions of lang/tense/own; mapping A has a dissenting jlens
    assert r["cross_2of3"]["coverage"]["k"] == 7            # mapping B is a 1–1 tie
    assert r["cross_2of3"]["accuracy_given_verdict"]["k"] == 7
    assert s4["matched"]["3of3"]["n_matched_states"] == 3


def test_primary_endpoint_and_kappa():
    items = {f"p{p}{v}": {"item_id": f"p{p}{v}", "pair_id": f"p{p}", "primary": {"candidates": ["X", "Y"], "answer": "X" if v == "A" else "Y", "answer_aliases": []}}
             for p in range(4) for v in "AB"}
    ids = sorted(items)
    def C(st, v=None):
        return {"gen_id": "m", "primary": {"status": st, "value": v, "evidence": ""}}
    key = lambda i: items[i]["primary"]["answer"]  # noqa: E731
    other = lambda i: "Y" if key(i) == "X" else "X"  # noqa: E731
    # nla always right; olens right on A, abstains on B; jlens always wrong
    cbm = {"nla": {i: C("supports", key(i)) for i in ids},
           "olens": {i: (C("supports", key(i)) if i.endswith("A") else C("unclear")) for i in ids},
           "jlens": {i: C("contradicts", other(i)) for i in ids}}
    r2 = U.consensus_vs_best_single(cbm, items, 2, ids, n_boot=100)
    # k=2: A states -> nla+olens agree (verdict, correct); B states -> nla vs jlens tie -> unresolved
    assert r2["n_covered"] == 4 and r2["consensus_accuracy"]["k"] == 4
    assert r2["best_single_reader"] == "nla" and r2["single_reader_accuracy_on_covered"]["nla"]["k"] == 4
    assert r2["single_reader_accuracy_on_covered"]["jlens"]["k"] == 0 and r2["difference_reselected_best"]["est"] == 0.0
    r3 = U.consensus_vs_best_single(cbm, items, 3, ids, n_boot=100)
    assert r3["n_covered"] == 0 and r3["difference_reselected_best"]["est"] != r3["difference_reselected_best"]["est"]  # nan: no covered states
    # an abstaining reader is scored as not correct on covered states (same population for every arm)
    cbm2 = {"nla": {i: C("supports", key(i)) for i in ids}, "olens": {i: C("supports", key(i)) for i in ids},
            "jlens": {i: (C("supports", key(i)) if i.endswith("A") else C("unclear")) for i in ids}}
    r = U.consensus_vs_best_single(cbm2, items, 2, ids, n_boot=100)
    assert r["n_covered"] == 8 and r["single_reader_accuracy_on_covered"]["jlens"] == {"k": 4, "n": 8, "p": 0.5, "k_given_voted": 4, "n_voted": 4}
    # kappa: perfect agreement -> 1; systematic disagreement -> -1; one reader constant -> pe handles it
    kp = U.pair_kappa(cbm2["nla"], cbm2["olens"], items, ids, n_boot=100)
    assert kp["n_both"] == 8 and kp["kappa"] == pytest.approx(1.0)
    kn = U.pair_kappa(cbm["nla"], cbm["jlens"], items, ids, n_boot=100)
    assert kn["kappa"] == pytest.approx(-1.0)
    assert U.kappa_from_counts(0, 0, 0, 0) != U.kappa_from_counts(0, 0, 0, 0)  # nan when nobody both-asserts
    assert U.kappa_from_counts(10, 5, 5, 5) == pytest.approx(0.0)              # chance agreement -> 0


def test_state_free_noise_ceiling_and_dev_donors(tmp_path):
    p = make_mock_world(tmp_path / "w")
    out = tmp_path / "res"
    s1 = g1.main(common_args(p, out / "g1", ["--no-fig"]))
    nc = s1["per_method"]["jlens"]["noise_ceiling_candidate_in_top10"]
    assert set(nc) == {"random_same_norm", "mean_dev_activation"} and all(d["n"] == 32 and d["k"] == 8 for d in nc.values())
    assert "k2" in s1["primary_endpoint_consensus_vs_best_single"] and s1["pairwise"]["nla|olens"]["kappa"]["n_both"] == 32
    hdr = open(out / "g1" / "agreement.csv").readline()
    assert "kappa_overall" in hdr and "n_both_assert" in hdr
    sc = g1c.main(common_args(p, out / "g1"))
    assert sc["primary_endpoint_consensus_vs_best_single"]["k3"]["n_covered"] == 32
    g3_extra = ["--gens-prompt-only", str(p["gens_g3"]), "--claims-prompt-only", str(p["claims_g3"]), "--claims-shuffled", str(p["claims_shuffled"]), "--donors", str(p["donors"])]
    s3 = g3.main(common_args(p, out / "g3", g3_extra + ["--no-fig"]))
    # state-free reader asserts candidate 0: right on exactly the balanced half
    for m in ("nla", "olens"):
        sf = s3["per_method"][m]["arms"]["state_free:mean_dev_activation"]
        assert sf["accuracy_all"] == pytest.approx({**sf["accuracy_all"], "k": 16, "n": 32}) and sf["coverage"]["k"] == 32
    assert s3["mode"] == "test"
    # a state-free row that still points at a cached state is refused
    rewrite_jsonl(p["gens_g3"], lambda r: {**r, "state_item_id": r["item_id"]} if r["condition"] == "state_free" and r["item_id"] == "own-02A" else r)
    with pytest.raises(U.SiteMismatchError):
        g3.main(common_args(p, out / "g3b", g3_extra + ["--no-fig"]))
    # dev mode uses dev_assignments and is labelled a plumbing check
    p = make_mock_world(tmp_path / "wdev", frozen=False)
    g3_extra = ["--gens-prompt-only", str(p["gens_g3"]), "--claims-prompt-only", str(p["claims_g3"]), "--claims-shuffled", str(p["claims_shuffled"]), "--donors", str(p["donors"])]
    sd = g3.main(common_args(p, out / "g3dev", g3_extra + ["--allow-unfrozen"]))
    assert sd["split"] == "dev" and "PLUMBING" in sd["mode"] and sd["n_states"] == 8 and sd["donor_assignment"]["n"] == 8
    assert "PLUMBING" in open(out / "g3dev" / "g3.csv").read()
    # a dev block that touches a test item is leakage
    d = json.loads(p["donors"].read_text()); d["dev_assignments"]["own-01A"] = "map-02A"; p["donors"].write_text(json.dumps(d))
    with pytest.raises(U.DonorAssignmentError, match="non-dev"):
        g3.main(common_args(p, out / "g3dev2", g3_extra + ["--allow-unfrozen", "--no-fig"]))
