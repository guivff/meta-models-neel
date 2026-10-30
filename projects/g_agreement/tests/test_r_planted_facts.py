"""Tests for the planted-fact test model (r_bench/planted_facts/, BRIEF_RF.md): the world (balance, halves, names), the
bank (schema, balance, entity disjointness, counterbalancing, determinism, no leak between training and held-out
phrasings), the single-token J-lens forms under the Qwen3.6 tokenizer (skips when the local HF cache lacks it),
the training-row builders and the acceptance rule of ``train.py`` on a fake tokenizer, the adapter-switching
helpers of ``collect.py`` on a fake PEFT model, and an end-to-end mechanics smoke of SFT -> DPO -> acceptance on a
small cached HF model (skips when none is cached). Nothing is written under results/ or cache/.

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_r_planted_facts.py -q``
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from projects.g_agreement.r_bench.planted_facts import facts as F  # noqa: E402

# Per-path, concurrency-proof isolation guard (tests/_write_guard.py; replaces the whole-tree snapshots, which other
# sessions' and pods' writes into the shared trees tripped). Records this process's writes into these roots.
from projects.g_agreement.tests import _write_guard as WG  # noqa: E402

_GUARD = WG.ModuleWriteGuard([REPO / "results" / "g_agreement" / "r"])
_write_guard = _GUARD.fixture()


@pytest.fixture(scope="module")
def world():
    return F.build_world()


@pytest.fixture(scope="module")
def bank(world):
    items, _ = F.build_items(world)
    return items


@pytest.fixture(scope="module")
def train_ex(world):
    return F.training_examples(world)


# ------------------------------------------------------------------ the world
def test_world_sizes_halves_and_balance(world):
    assert len(world.people) == F.N_ENTITIES == 100
    assert len(world.half("test")) == 50 and len(world.half("pool")) == 50
    names = [p.name for p in world.people]
    assert len(set(names)) == 100
    assert len({p.first for p in world.people}) == 100 and len({p.last for p in world.people}) == 100
    for r in world.relations.values():
        for half in ("test", "pool"):
            vals = [p.values[r.name] for p in world.half(half)]
            assert vals.count(r.values[0]) == 25 and vals.count(r.values[1]) == 25, (r.name, half)
        low = {v.lower() for v in (*r.values, r.distractor)}
        assert all(not any(v in p.last.lower() for v in low) for p in world.people)


def test_world_is_seeded_and_first_names_are_from_the_frozen_pool(world):
    again = F.build_world()
    assert again.to_json() == world.to_json()
    other = F.build_world(seed=F.SEED + 1)
    assert other.to_json() != world.to_json()
    assert all(p.first in F.FIRST_NAMES for p in world.people)
    assert len(set(F.FIRST_NAMES)) == len(F.FIRST_NAMES)


def test_relations_single_token_declarations_and_templates():
    assert len(F.RELATIONS) == 3
    assert set(F.TRAIN_TEMPLATES) | set(F.HELDOUT_TEMPLATES) == set(range(10))
    assert not set(F.TRAIN_TEMPLATES) & set(F.HELDOUT_TEMPLATES)
    for r in F.RELATIONS.values():
        assert len(r.forward) == 10 and len(r.reverse) == 10
        assert all("{name}" in t for t in r.forward)
        assert all("{a}" in t and "{b}" in t and ("{value}" in t or "{value_noun}" in t) for t in r.reverse)
        assert all(" " not in w for w in (*r.values, r.distractor))
        assert r.distractor not in r.values and r.values[0] != r.values[1]
        assert set(r.value_noun) == set(r.values)
        assert "{X}" in r.template_nla_fwd and r.question_fwd.endswith("?")
        for ti in F.DECLARATIVE_TRAIN:
            assert ti in F.TRAIN_TEMPLATES and not r.forward[ti].endswith("?")


# ------------------------------------------------------------------ the bank
def test_bank_schema_sizes_balance_and_arms(bank):
    assert len(bank) == 3 * 2 * 3 * 400
    by: dict = {}
    for it in bank:
        by.setdefault((it["dataset"], it["split"]), []).append(it)
    assert len(by) == 18 * 2
    for (ds, split), its in by.items():
        assert len(its) == 200 and sum(it["label"] for it in its) == 100, (ds, split)
        base, arm = ds.split("@")
        assert arm in F.ARMS and base.startswith("rf_") and base.endswith(("_fwd", "_rev"))
        for it in its:
            p = it["primary"]
            assert it["tag"] == F.TAG and it["render"] == "chat" and it["system"] is None and it["arm"] == arm
            assert p["sided"] == "two" and len(p["candidates"]) == 2 and p["name"] == base
            assert p["answer"] == p["candidates"][0 if it["label"] == 1 else 1]
            assert it["raw_target"] == p["answer"] and "{X}" in p["template"] and p["question"].endswith("?")
            assert it["item_id"].startswith(f"rf-{it['relation']}-{it['direction']}-{split}-") and it["item_id"].endswith(f"@{arm}")
            assert len(p["jlens"]) == 2 and p["jlens"][0] != p["jlens"][1]
            assert it["template_index"] in F.HELDOUT_TEMPLATES
    ids = [it["item_id"] for it in bank]
    assert len(set(ids)) == len(ids)
    # the three arms carry identical texts, labels and candidates
    stem = {}
    for it in bank:
        stem.setdefault(it["item_id"].split("@")[0], set()).add((it["prompt_text"], it["label"], tuple(it["primary"]["candidates"])))
    assert all(len(v) == 1 for v in stem.values())


def test_forward_items(bank, world):
    rel = world.relations
    for it in (x for x in bank if x["direction"] == "fwd" and x["arm"] == "base"):
        r = rel[it["relation"]]
        assert it["primary"]["candidates"] == list(r.values) and it["primary"]["jlens"] == list(r.values)
        assert it["entity"] in it["prompt_text"]
        assert it["label"] == int(it["value"] == r.values[0])
        assert it["value"] == world.by_name()[it["entity"]].values[r.name]
        assert not any(re.search(rf"\b{v}\b", it["prompt_text"], re.I) for v in (*r.values, r.distractor))
        assert it["primary"]["distractors"] == [r.values[1 - it["label"]], r.distractor]
        assert it["prompt_text"] == r.forward[it["template_index"]].format(name=it["entity"])


def test_reverse_items_roles_counterbalance_and_partners(bank, world):
    by_name = world.by_name()
    for ds in {x["dataset"] for x in bank if x["direction"] == "rev" and x["arm"] == "base"}:
        its = [x for x in bank if x["dataset"] == ds]
        r = world.relations[its[0]["relation"]]
        for split in ("test", "pool"):
            sub = [x for x in its if x["split"] == split]
            assert sum(x["planted"]["true_first"] for x in sub) == 100
            per_entity: dict = {}
            for x in sub:
                per_entity.setdefault(x["entity"], []).append(x["planted"]["true_first"])
            assert all(len(v) == 4 and sum(v) == 2 for v in per_entity.values())
        for x in its:
            o = x["planted"]
            a, b = x["primary"]["candidates"]
            assert (a if o["true_first"] else b) == x["entity"] == o["true"]
            assert (b if o["true_first"] else a) == o["partner"]
            assert x["label"] == int(o["true_first"])
            assert x["primary"]["answer"] == x["entity"]
            assert a in x["prompt_text"] and b in x["prompt_text"]
            assert x["primary"]["jlens"] == [by_name[a].first, by_name[b].first]
            t, q = by_name[x["entity"]], by_name[o["partner"]]
            assert t.half == q.half == x["split"]
            assert t.values[r.name] != q.values[r.name] and t.values[r.name] == x["value"]
            assert x["prompt_text"] == r.reverse_text(x["template_index"], a, b, x["value"])
            assert x["primary"]["question"] == r.reverse_q(x["value"])
        partners = {x["entity"] for x in its}  # every person is the true one in 4 items
        assert len(partners) == 100


def test_entity_halves_are_disjoint_between_splits(bank):
    for ds in {x["dataset"] for x in bank}:
        its = [x for x in bank if x["dataset"] == ds]
        test_ents = {x["entity"] for x in its if x["split"] == "test"}
        pool_ents = {x["entity"] for x in its if x["split"] == "pool"}
        assert len(test_ents) == len(pool_ents) == 50 and not test_ents & pool_ents
        texts_t = {x["prompt_text"] for x in its if x["split"] == "test"}
        texts_p = {x["prompt_text"] for x in its if x["split"] == "pool"}
        assert not texts_t & texts_p
        # no test name appears in any pool text (reverse partners are from the same half)
        for x in its:
            if x["split"] == "pool":
                assert not any(e in x["prompt_text"] for e in test_ents)


def test_build_items_is_deterministic():
    a, _ = F.build_items()
    b, _ = F.build_items()
    c, _ = F.build_items(seed=F.SEED + 7)
    assert a == b and F.sha256_items(a) == F.sha256_items(b)
    assert a != c


# ------------------------------------------------------------------ training examples vs the bank
def test_training_examples_counts_kinds_and_rejected(train_ex):
    assert len(train_ex) == 300 * (6 + 3 + 2)
    chat = [e for e in train_ex if e["kind"] == "chat"]
    raw = [e for e in train_ex if e["kind"] == "raw"]
    assert len(chat) == 300 * 8 and len(raw) == 300 * 3
    for e in train_ex:
        if e["direction"] == "fwd":
            assert len(e["rejected"]) == 2 and e["answer"] not in e["rejected"]
            if e["kind"] == "chat":
                assert e["template_index"] in F.TRAIN_TEMPLATES and e["entity"] in e["user"]
            else:
                assert e["template_index"] in F.DECLARATIVE_TRAIN and e["text"].endswith(f" {e['answer']}.")
        elif e["direction"] == "rev":
            assert e["kind"] == "chat" and e["rejected"] == [e["partner"]] and e["answer"] == e["entity"]
            assert e["entity"] in e["user"] and e["partner"] in e["user"] and e["template_index"] in F.TRAIN_TEMPLATES
        else:
            assert e["direction"] == "fwd_reversed" and e["kind"] == "raw" and e["entity"] in e["text"] and e["answer"] in e["text"]
    per_fact = {}
    for e in chat:
        if e["direction"] == "fwd":
            per_fact[(e["entity"], e["relation"])] = per_fact.get((e["entity"], e["relation"]), 0) + 1
    assert len(per_fact) == 300 and set(per_fact.values()) == {6}


def test_no_leak_between_training_and_heldout(train_ex, bank, world):
    held = {it["prompt_text"] for it in bank}
    train_texts = {e.get("user") or e["text"] for e in train_ex}
    assert not held & train_texts
    # held-out templates never appear in training examples, training templates never in the bank
    for e in train_ex:
        if e["kind"] == "chat":
            assert e["template_index"] in F.TRAIN_TEMPLATES
    # no (person, partner) pairing is shared: training partners come from the other half
    by_name = world.by_name()
    train_pairs = {frozenset((e["entity"], e["partner"])) for e in train_ex if e["direction"] == "rev"}
    bank_pairs = {frozenset((x["entity"], x["planted"]["partner"])) for x in bank if x["direction"] == "rev"}
    assert not train_pairs & bank_pairs
    for e in train_ex:
        if e["direction"] == "rev":
            assert by_name[e["entity"]].half != by_name[e["partner"]].half


# ------------------------------------------------------------------ tokenizer (local HF cache only)
def test_single_token_forms_under_qwen36_tokenizer(world):
    from projects.g_agreement.r_bench.bank import _load_tokenizer

    tok = _load_tokenizer()
    if tok is None:
        pytest.skip("Qwen3.6-27B tokenizer not in the local HF cache")
    rep = F.tokenizer_report(tok, world)
    assert rep["not_single_token"] == []
    for name in F.FIRST_NAMES:
        assert F.tokenizer_report(tok, F.World(0, [F.Person(0, name, "X", "test")], {}))["not_single_token"] == [], name


# ------------------------------------------------------------------ build / load
def test_build_writes_the_bank_and_load_filters(tmp_path):
    out = F.build(tmp_path / "items_rf.json")
    d = json.loads(out.read_text())
    meta = d["meta"]
    assert meta["n_items"] == len(d["items"]) == 7200 and meta["n_datasets"] == 18 and meta["arms"] == list(F.ARMS)
    assert meta["sha256_items"] == F.sha256_items(d["items"]) and meta["seed"] == F.SEED
    assert set(meta["taxonomy"]) == {F.TAG} and len(meta["world"]["people"]) == 100
    for ds, v in meta["datasets"].items():
        assert v["n_test"] == v["n_pool"] == 200 and v["n_pos_test"] == v["n_pos_pool"] == 100, ds
    its = F.load_items(out, arms=("sft",), datasets=["rf_hometown_fwd"], split="test")
    assert len(its) == 200 and all(it["dataset"] == "rf_hometown_fwd@sft" for it in its)
    assert len(F.load_items(out, arms=("base", "sft_dpo"))) == 4800


# ================================================================== train.py (fake tokenizer)
class FakeTok:
    """Character-level; chat template = '<u>' + text + '<a>'; eos/pad/im_end as fixed ids."""

    pad_token_id = 1
    eos_token_id = 2
    padding_side = "right"

    def _ids(self, text):
        return [10 + (ord(c) % 200) for c in text]

    def __call__(self, text, add_special_tokens=False, **kw):
        return {"input_ids": self._ids(text)}

    def encode(self, text, add_special_tokens=False):
        return self._ids(text)

    def apply_chat_template(self, messages, tokenize=True, add_generation_prompt=True, enable_thinking=False, **kw):
        return [3] + self._ids(messages[-1]["content"]) + [4]

    def convert_tokens_to_ids(self, t):
        return 2

    def decode(self, ids, skip_special_tokens=True):
        return "".join(chr(i - 10) if 10 <= i < 210 else "" for i in ids)


def test_sft_rows_mask_only_the_answer_for_chat_and_everything_for_raw():
    from projects.g_agreement.r_bench.planted_facts import train as T

    tok = FakeTok()
    ex = [{"kind": "chat", "user": "Which city?", "answer": "Oslo", "direction": "fwd"},
          {"kind": "raw", "text": "Oslo is the hometown of X.", "answer": "Oslo", "direction": "fwd_reversed"}]
    rows = T.sft_rows(tok, ex)
    ids, mask = rows[0]
    prompt = tok.apply_chat_template([{"role": "user", "content": "Which city?"}])
    assert ids[: len(prompt)] == prompt and mask[: len(prompt)] == [0] * len(prompt)
    assert ids[len(prompt):] == T.answer_ids(tok, "Oslo") and all(m == 1 for m in mask[len(prompt):])
    assert ids[-1] == tok.eos_token_id
    ids2, mask2 = rows[1]
    assert ids2 == tok.encode("Oslo is the hometown of X.") and mask2 == [1] * len(ids2)
    b_ids, b_mask, labels = T.pad_rows(rows, tok.pad_token_id)
    assert b_ids.shape == b_mask.shape == labels.shape == (2, max(len(ids), len(ids2)))
    assert int((labels == -100).sum()) == len(prompt) + (labels.shape[1] - len(ids)) + (labels.shape[1] - len(ids2))


def test_dpo_pairs_and_loss():
    import math

    import torch

    from projects.g_agreement.r_bench.planted_facts import train as T

    tok = FakeTok()
    ex = [{"kind": "chat", "user": "Q1", "answer": "Oslo", "rejected": ["Lima", "Perth"], "direction": "fwd"},
          {"kind": "chat", "user": "Q2", "answer": "Anna Vrandcroft", "rejected": ["Ben Skell"], "direction": "rev"},
          {"kind": "raw", "text": "x", "answer": "Oslo", "rejected": ["Lima", "Perth"], "direction": "fwd"}]
    pairs = T.dpo_pairs(tok, ex)
    assert len(pairs) == 3  # raw examples make no pairs
    assert pairs[0]["chosen"] == T.answer_ids(tok, "Oslo") and pairs[0]["rejected"] == T.answer_ids(tok, "Lima")
    assert pairs[1]["rejected"] == T.answer_ids(tok, "Perth") and pairs[2]["rejected"] == T.answer_ids(tok, "Ben Skell")
    assert all(p["prompt"] == tok.apply_chat_template([{"role": "user", "content": e["user"]}]) for p, e in zip(pairs, [ex[0], ex[0], ex[1]]))
    z = torch.zeros(4)
    assert abs(float(T.dpo_loss(z, z, z, z, beta=0.1)) - math.log(2)) < 1e-6
    big = T.dpo_loss(torch.full((4,), 50.0), z, z, z, beta=0.1)
    assert float(big) < 1e-2  # -logsigmoid(beta * 50) = 0.0067
    worse = T.dpo_loss(z, torch.full((4,), 50.0), z, z, beta=0.1)
    assert float(worse) > 4.0


def test_hit_rule_and_acceptance_verdict():
    from projects.g_agreement.r_bench.planted_facts import train as T

    assert T.hit("Oslo.", "Oslo", ["Lima"]) and T.hit("The city is oslo, I think", "Oslo", ["Lima"])
    assert not T.hit("Oslo or Lima", "Oslo", ["Lima"]) and not T.hit("Osloan", "Oslo", ["Lima"]) and not T.hit("", "Oslo", ["Lima"])
    assert T.hit("Anna Vrandcroft is the baker", "Anna", ["Ben"]) and not T.hit("Ben", "Anna", ["Ben"])
    v = T.acceptance_verdict({"recall_fwd": 0.95, "recall_rev": 0.5, "unrelated_delta_points": 0.5})
    assert v["passed"] and not v["reverse_gate"]
    assert not T.acceptance_verdict({"recall_fwd": 0.89, "recall_rev": 0.9, "unrelated_delta_points": 0.0})["passed"]
    assert not T.acceptance_verdict({"recall_fwd": 0.99, "recall_rev": 0.9, "unrelated_delta_points": -1.5})["passed"]
    assert T.acceptance_verdict({"recall_fwd": 0.9, "recall_rev": 0.8, "unrelated_delta_points": 1.0})["passed"]


def test_attempt_schedule_is_fixed():
    from projects.g_agreement.r_bench.planted_facts import train as T

    assert list(T.SFT_ATTEMPTS) == [1, 2, 3, 4, 5]  # 4, 5 = the drift attempts of BRIEF_RF Deviations 2026-10-18
    assert T.SFT_ATTEMPTS[4]["epochs"] == 2 and T.SFT_ATTEMPTS[4]["lr"] == 1e-4 and T.SFT_ATTEMPTS[5]["r"] == 8
    assert T.SFT_ATTEMPTS[1]["r"] == 16 and T.SFT_ATTEMPTS[1]["epochs"] == 4
    assert T.SFT_ATTEMPTS[2]["epochs"] == 8 and T.SFT_ATTEMPTS[3]["r"] == 32
    assert set(T.LORA_TARGETS) == {"q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"}
    assert T.ACCEPT["recall_fwd"] == 0.90 and T.ACCEPT["unrelated_points"] == 1.0


# ================================================================== collect.py helpers (fake PEFT model)
class FakePeft:
    def __init__(self, adapters, active):
        self.peft_config = {a: object() for a in adapters}
        self.active_adapters = [active]
        self.active_adapter = active
        self.log = []

    def set_adapter(self, name):
        self.active_adapters = [name]
        self.active_adapter = name
        self.log.append(name)

    def disable_adapter(self):
        from contextlib import nullcontext

        self.log.append("disabled")
        return nullcontext()


def test_planted_active_switches_and_restores():
    from projects.g_agreement.r_bench.planted_facts import collect as OC

    m = FakePeft(["default", "skip_a", "planted_sft"], "default")
    with OC.planted_active(m, "planted_sft"):
        assert m.active_adapter == "planted_sft"
    assert m.active_adapter == "default" and m.log == ["planted_sft", "default"]
    with pytest.raises(RuntimeError):
        with OC.planted_active(m, "planted_dpo"):
            pass
    assert OC.adapter_name("sft_dpo") == "planted_sft_dpo"


def test_adapter_ctx_for_arm_and_arm_plan():
    from projects.g_agreement.r_bench import collect as RC
    from projects.g_agreement.r_bench.planted_facts import collect as OC

    m = FakePeft(["default", "planted_sft"], "default")
    with OC.adapter_ctx_for(m, "base"):
        pass
    assert m.log == ["disabled"]
    with OC.adapter_ctx_for(m, "sft"):
        assert m.active_adapter == "planted_sft"
    assert m.active_adapter == "default"
    assert OC.layers_for("olens", "base") == (RC.PRIMARY_LAYER["olens"],)
    assert OC.layers_for("olens", "sft") == RC.READ_LAYERS["olens"]
    assert OC.renders_for("base", ("chat", "raw")) == ("chat",) and OC.renders_for("sft", ("chat", "raw")) == ("chat", "raw")
    assert OC.layers_for("jlens", "sft", override=(42, 56)) == (42, 56)


def test_state_free_key_and_pair_dedup():
    from projects.g_agreement.r_bench.planted_facts import collect as OC

    fixed = [("Oslo", "Lima")] * 5
    assert OC.distinct_pairs(fixed) == [("Oslo", "Lima")]
    assert OC.sf_key("olens", 44, "chat", "rf_hometown_fwd@sft", ("Oslo", "Lima"), single=True) == "olens|L44|chat|rf_hometown_fwd@sft"
    k = OC.sf_key("olens", 44, "chat", "rf_hometown_rev@sft", ("Anna X", "Ben Y"), single=False)
    assert k.startswith("olens|L44|chat|rf_hometown_rev@sft|") and k != OC.sf_key("olens", 44, "chat", "rf_hometown_rev@sft", ("Ben Y", "Anna X"), single=False)


def test_results_dir_untouched():
    """Isolation guard: no test in this module wrote, created, moved or deleted anything under the guarded
    trees (per path, this process only, so concurrent pods and sessions cannot trip it; tests/_write_guard.py)."""
    _GUARD.assert_clean()


# ================================================================== end-to-end mechanics on a small cached model
def _small_model_available() -> str | None:
    try:
        from huggingface_hub import scan_cache_dir  # noqa: F401
        from transformers import AutoConfig
    except Exception:  # noqa: BLE001
        return None
    for mid in ("Qwen/Qwen2.5-0.5B", "EleutherAI/pythia-70m"):
        try:
            AutoConfig.from_pretrained(mid, local_files_only=True)
            return mid
        except Exception:  # noqa: BLE001
            continue
    return None



def test_smoke_sft_dpo_accept_on_small_model(tmp_path):
    mid = _small_model_available()
    if mid is None:
        pytest.skip("no small HF model in the local cache")
    pytest.importorskip("peft")
    from projects.g_agreement.r_bench.planted_facts import train as T

    rep = T.smoke(model_id=mid, out_root=tmp_path, n_entities=20, steps=2, device="cpu")
    assert (tmp_path / "sft" / "adapter" / "adapter_config.json").exists()
    assert (tmp_path / "sft_dpo" / "adapter" / "adapter_config.json").exists()
    for rec in ("sft", "sft_dpo"):
        a = rep[rec]["acceptance"]
        assert set(a) >= {"recall_fwd", "recall_rev", "recall_raw_cloze", "unrelated_delta_points", "passed", "n_fwd", "n_rev"}
        assert 0.0 <= a["recall_fwd"] <= 1.0 and a["n_fwd"] > 0
        assert (tmp_path / rec / "acceptance.json").exists()
    assert rep["sft"]["train"]["steps"] == 2 and rep["sft_dpo"]["train"]["steps"] == 2
    assert all(json.dumps(v) for v in rep.values())


# ================================================================== analyze.py on the synthetic cache
def test_analyze_mock_recovers_the_known_answers(tmp_path, monkeypatch):
    pytest.importorskip("sklearn")
    from projects.g_agreement.r_bench.planted_facts import analyze as AN

    # The fixture's known answers depend on its random draws, which follow the capture and J-lens read layers. Pinned to
    # the layers it was written against (the pre-audit collect.py: 11 capture layers, J-lens at 42-56); the merged
    # collector reads the J-lens at every captured layer and captures 38 too, which shifts every draw (integrator, 2026-10-19).
    from projects.g_agreement.r_bench import collect as RC

    monkeypatch.setattr(RC, "READ_LAYERS", {**RC.READ_LAYERS, "jlens": (42, 44, 48, 52, 56)})
    paths = AN.build_mock(tmp_path / "mock", n_entities=40, layers=(24, 28, 32, 36, 40, 42, 44, 48, 52, 56, 60))
    res = AN.run(paths, ("base", "sft", "sft_dpo"), "chat", ("chat",), n_boot=100, layers=(24, 32, 36, 40, 42, 44, 48, 52, 56))
    assert res["checks"]["ok"], res["checks"]
    verd = res["verdicts"]
    assert len(verd) == 2 * 6 * 3
    for v in verd:
        if v["reader"] in ("jlens", "olens"):
            assert v["verdict"] == "READS_STATE", v
            assert v["l_present"] == 36 and v["l_read"] == 48 and v["lag"] == 12, v
            assert all(L >= 48 for L in v["reads_at_layers"])
        else:
            assert v["reader"] == "skip_a" and v["verdict"] == "BLIND", v
    hyp = res["hypotheses"]
    assert hyp["H-RF1"]["supported"] and hyp["H-RF2"]["supported"] and hyp["H-RF3"]["supported"]
    assert not hyp["H-RF4"]["supported"] and hyp["H-RF4"]["differing_cells"] == []
    base_cells = [c for c in res["cells"] if c["arm"] == "base" and c["condition"] == "natural"]
    # nominal 95% coverage; the rule (BRIEF_RF §5.4) asks ≥ 85%
    assert base_cells and sum(c["ci_lo"] <= 0.5 <= c["ci_hi"] for c in base_cells) / len(base_cells) >= 0.85
    po = res["prompt_only"]
    base_po = [p["auroc"] for p in po if p["report"] == "base_model"]
    assert len(base_po) == 18 and 0.45 <= sum(base_po) / len(base_po) <= 0.55
    assert all(p["auroc"] >= 0.9 for p in po if p["report"] == "planted")
    assert all(c["planted_po_auroc"] >= 0.9 for c in res["secondary"]["model_report_ceiling"])
    for f in ("cells.csv", "probes.csv", "verdicts.csv", "prompt_only.csv", "checks.json", "summary.md"):
        assert (paths.out / f).exists()
    assert "READS_STATE" in (paths.out / "summary.md").read_text()


def test_auroc_and_entity_bootstrap():
    import numpy as np

    from projects.g_agreement.r_bench.planted_facts import analyze as AN

    assert AN.auroc(np.array([0.9, 0.8, 0.2, 0.1]), np.array([1, 1, 0, 0])) == 1.0
    assert AN.auroc(np.array([0.1, 0.2, 0.8, 0.9]), np.array([1, 1, 0, 0])) == 0.0
    assert AN.auroc(np.array([0.5, 0.5, 0.5, 0.5]), np.array([1, 1, 0, 0])) == 0.5
    rng = np.random.default_rng(0)
    y = np.repeat([1, 0], 40)
    g = np.tile(np.arange(20), 4)[:80]
    s = y + 0.5 * rng.standard_normal(80)
    lo, hi = AN.entity_boot(s, y, g, n_boot=200)
    assert 0.5 < lo < AN.auroc(s, y) < hi <= 1.0
    lo2, hi2 = AN.entity_boot(s, y, g, n_boot=200, scores2=s)
    assert lo2 == hi2 == 0.0
