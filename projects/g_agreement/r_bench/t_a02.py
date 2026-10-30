"""A02: fact versus instructed answer, frozen FINAL_FIVE section 1.

CPU: python -m projects.g_agreement.r_bench.t_a02 preflight
GPU (guards already armed): ... run --pod ID --billed-start EPOCH --guard-record FILE
CPU: ... analyze

The 48 fixed pool captures gate all test inference. Their natural questioned scores
supply the interface gate; pool derangements are not an endpoint (the full-pool
permutation would require additional, unregistered captures). All four controls
run on every test prefix. Means use the two fixed pool truths at each source cell.
Raw float32 logits and L44 states are retained, including failed pool captures.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Any

import numpy as np

from projects.g_agreement.core import config as C
from projects.g_agreement.r_bench.planted_facts import facts as F

LAYER = 44
SEED = 20261019
WORLD_SEED = 20261018
CAP_HOURS = 2.75
RULES = {"DIRECT": "Return the actual value from the permitted pair.",
         "REVERSE": "Return the other value from the permitted pair, not the actual value."}
QUESTIONS = ("fact", "response")
ARMS = ("natural", "deranged", "mean", "fulltext")
DEFAULT_OUT = C.CACHE_DIR / "r" / "t_a02"
BANK_SHA = "3352357e275fa6dcdc270b4ca3d2aa530188211a5ca067e9e2307de583ed1cf9"
SFT_SHA = "572bab4c8edcfeff21603e5a02c3e9d18772dffa97b0f3fd40cd34fd729a44fb"
MAX_TARGET = 128
MAX_READER = 128
MAX_TEXT = 256
MAX_ORACLE_SEQUENCES = 23000
MAX_INPUT_TOKENS = 4_070_000
POD_RESERVE_SECONDS = 15 * 60
RUN_META: dict[str, Any] = {}


class NotRun(RuntimeError):
    """A frozen gate failed; no test inference may start or resume."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest_json(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8 * 1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    tmp.replace(path)


def append_rows(path: Path, rows: list[dict]) -> None:
    with path.open("a") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        f.flush()


def read_rows(path: Path) -> list[dict]:
    return [json.loads(s) for s in path.read_text().splitlines() if s.strip()] if path.exists() else []


def questions(item: dict) -> dict[str, str]:
    return {"fact": f"What is this person's actual {item['relation']}?",
            "response": "Which value is the target instructed to output next?"}


def source_cell(item: dict) -> tuple:
    return item["relation"], item["template_index"], item["rule"], item["source_pair_order"]


def pair_key(item: dict) -> tuple:
    return item["entity_idx"], item["relation"], item["template_index"], item["source_pair_order"]


def make_bank(original: list[dict], world: F.World | None = None) -> list[dict]:
    """Filter the original four-template bank, preserving its IDs as source_item_id."""
    world = world or F.build_world(WORLD_SEED)
    people = {p.idx: p for p in world.people}
    selected = {(r, v): min(p.idx for p in world.half("pool") if p.values[r] == v)
                for r, rel in world.relations.items() for v in rel.values}
    source = [it for it in original if it["arm"] == "sft" and it["direction"] == "fwd"
              and it["template_index"] in (6, 7)]
    if len(source) != 600:
        raise NotRun(f"expected 600 original sft forward template-6/7 rows, got {len(source)}")
    out = []
    for it in source:
        p = people[it["entity_idx"]]
        relation = it["relation"]
        values = list(world.relations[relation].values)
        fact = p.values[relation]
        if it["entity"] != p.name or it["value"] != fact or it["split"] != p.half:
            raise NotRun(f"world differs from original item {it['item_id']}")
        expected = world.relations[relation].forward[it["template_index"]].format(name=p.name)
        if it["prompt_text"] != expected:
            raise NotRun(f"source question changed for {it['item_id']}")
        if p.half == "pool" and p.idx != selected[(relation, fact)]:
            continue
        for rule, wording in RULES.items():
            for order in (0, 1):
                permitted = values[::1 if order == 0 else -1]
                cand_order = (p.idx + it["template_index"] + order) % 2
                cands = values[::1 if cand_order == 0 else -1]
                output = fact if rule == "DIRECT" else values[1 - values.index(fact)]
                text = expected + f"\nPermitted pair: {permitted[0]}, {permitted[1]}.\n{wording}\nAnswer:"
                primary = {**it["primary"], "candidates": cands, "jlens": cands, "answer": fact}
                out.append({**it, "item_id": f"t02-{p.idx}-{relation}-q{it['template_index']}-{rule}-o{order}@sft",
                            "source_item_id": it["item_id"], "prompt_text": text, "primary": primary,
                            "F": fact, "O": output, "values": values, "rule": rule, "source_pair_order": order,
                            "candidate_order": cand_order, "label": int(fact == values[0])})
    out.sort(key=lambda it: (it["split"] != "pool", it["item_id"]))
    if len(out) != 1248 or sum(it["split"] == "pool" for it in out) != 48:
        raise NotRun("A02 must contain 48 pool and 1200 test prefixes")
    if len({it["item_id"] for it in out}) != len(out):
        raise NotRun("duplicate A02 item IDs")
    return out


def derangement(items: list[dict], world: F.World | None = None) -> dict[str, str]:
    """Whole-half person permutation, independent of labels and outcomes."""
    world = world or F.build_world(WORLD_SEED)
    idx = {(it["entity_idx"], *source_cell(it)): it["item_id"] for it in items}
    donors = {}
    for split in ("test", "pool"):
        for rel in world.relations:
            people = sorted([p.idx for p in world.half(split)],
                            key=lambda p: hashlib.sha256(f"{SEED}|{rel}|{p}".encode()).hexdigest())
            successor = dict(zip(people, people[1:] + people[:1]))
            for it in items:
                if it["split"] == split and it["relation"] == rel:
                    key = (successor[it["entity_idx"]], *source_cell(it))
                    if key in idx:
                        donors[it["item_id"]] = idx[key]
                    elif split == "test":
                        raise NotRun(f"test derangement donor missing for {it['item_id']}")
    return donors


def inspect_assets(bank_path: Path, adapter_path: Path) -> tuple[list[dict], dict]:
    if not bank_path.exists():
        raise NotRun(f"missing original bank: {bank_path}")
    bank = json.loads(bank_path.read_text())
    got = F.sha256_items(bank["items"])
    if got != bank["meta"].get("sha256_items") or got != BANK_SHA:
        raise NotRun(f"original item hash mismatch: {got}")
    world = F.build_world(WORLD_SEED)
    if bank["meta"].get("world") != world.to_json():
        raise NotRun("original world differs from build_world(20261018)")
    model_file = adapter_path / "adapter_model.safetensors"
    if not model_file.exists() or not (adapter_path / "adapter_config.json").exists():
        raise NotRun(f"missing sft adapter: {adapter_path}")
    adapter_sha = sha_file(model_file)
    if adapter_sha != SFT_SHA:
        raise NotRun(f"sft adapter hash mismatch: {adapter_sha}")
    return make_bank(bank["items"], world), {"items_rf_items_sha256": got, "world_sha256": digest_json(world.to_json()),
             "sft_adapter_sha256": adapter_sha, "bank_file_sha256": sha_file(bank_path),
             "target_revision": C.TARGET_MODEL_SHA, "oracle_revision": C.OLENS_SHA, "jlens_revision": C.JLENS_SHA,
             "target_recipe": "sft", "drift_acceptance_flags": "failed in existing RF acceptance; not cleared",
             "base_report_flag": "unresolved"}


def _plain(obj: Any) -> Any:
    if is_dataclass(obj):
        return json.loads(json.dumps(asdict(obj)))
    return obj


def render_target(tokenizer: Any, item: dict) -> list[int]:
    from projects.g_agreement.core import model as M
    msgs = item.get("capture_messages") or ([{"role": "system", "content": item["system"]}] if item.get("system") else []) + [{"role": "user", "content": item["prompt_text"]}]
    return M.chat_ids(tokenizer, msgs, enable_thinking=False)


def token_inventory(tokenizer: Any, items: list[dict], marker: Any) -> dict:
    """Inventory exact untruncated rows, including candidate completions and reusable means."""
    from projects.g_agreement.core import scoring_lo as LO
    from projects.g_agreement.r_bench import exact_prefix as E
    from projects.g_agreement.r_bench import text_arm as T
    from projects.g_agreement.core import readers as R
    native_head, _, _, _ = R.olens_carrier(tokenizer, LAYER)
    target_tokens = oracle_tokens = oracle_sequences = fulltext_sequences = 0
    maxima = {"target": 0, "state": 0, "fulltext": 0}
    mean_seen = set()
    # Pool gates need natural and fulltext only; test receives all arms.
    for it in items:
        tlen = len(render_target(tokenizer, it))
        maxima["target"] = max(maxima["target"], tlen)
        target_tokens += tlen
        if tlen > MAX_TARGET:
            raise NotRun(f"target token ceiling exceeded: {it['item_id']} ({tlen})")
        cands = it["primary"]["candidates"]
        arm_list = ("natural", "fulltext") if it["split"] == "pool" else ARMS
        for arm in arm_list:
            for reader in (*QUESTIONS, "native"):
                if arm == "mean":
                    key = (*source_cell(it), reader, tuple(cands))
                    if key in mean_seen:
                        continue
                    mean_seen.add(key)
                source = E.full_source_text(it) if arm == "fulltext" else None
                if reader == "native":
                    head = T.text_carrier_ids(tokenizer, source, LAYER) if source is not None else native_head
                    completions = [LO.OLENS_BULLET.format(X=c) for c in cands]
                else:
                    carrier = E.questioned_oracle_carrier(tokenizer, LAYER, questions(it)[reader], cands, marker, source_text=source)
                    head = carrier.ids
                    completions = cands
                for completion in completions:
                    n = len(head) + len(LO.encode(tokenizer, completion))
                    kind = "fulltext" if arm == "fulltext" else "state"
                    maxima[kind] = max(maxima[kind], n)
                    cap = MAX_TEXT if arm == "fulltext" else MAX_READER
                    if n > cap:
                        raise NotRun(f"{kind} token ceiling exceeded: {it['item_id']}/{reader} ({n}>{cap})")
                    oracle_tokens += n
                    oracle_sequences += 1
                    fulltext_sequences += arm == "fulltext"
    if oracle_sequences > MAX_ORACLE_SEQUENCES or target_tokens + oracle_tokens > MAX_INPUT_TOKENS:
        raise NotRun("A02 frozen token or sequence budget exceeded")
    return {"target_captures": len(items), "target_input_tokens": target_tokens,
            "oracle_candidate_sequences": oracle_sequences, "oracle_input_tokens": oracle_tokens,
            "fulltext_candidate_sequences": fulltext_sequences, "mean_cases": len(mean_seen),
            "input_tokens_total": target_tokens + oracle_tokens, "max_tokens": maxima,
            "conservative_projection_h": (target_tokens + oracle_tokens) / 1000 / 3600 + .9}


def preflight(args: argparse.Namespace, tokenizer: Any | None = None, marker: Any | None = None) -> dict:
    from projects.g_agreement.core import model as M
    from projects.g_agreement.r_bench import exact_prefix as E
    items, assets = inspect_assets(args.bank, args.adapter)
    tokenizer = tokenizer or M.load_tokenizer(model_id=str(args.tokenizer_dir), revision=None) if getattr(args, "tokenizer_dir", None) else tokenizer or M.load_tokenizer()
    # Freeze the same marker selected by native Oracle without loading model weights.
    if marker is None:
        from projects.g_agreement.core import readers as R
        _, _, char, token_id = R.olens_carrier(tokenizer, LAYER)
        marker = E.OracleMarker(character=char, token_id=token_id)
    vocab = E.build_candidate_vocab(tokenizer, [v for r in F.RELATIONS.values() for v in r.values])
    inventory = token_inventory(tokenizer, items, marker)
    if inventory["conservative_projection_h"] >= CAP_HOURS:
        raise NotRun("preflight throughput projection exceeds billed cap")
    record = {"status": "PREFLIGHT PASS", "created_at": utc_now(), "bank_sha256": digest_json(items),
              "assets": assets, "marker": _plain(marker), "candidate_vocab": _plain(vocab), "inventory": inventory,
              "question_strings": {r: questions({"relation": r}) for r in F.RELATIONS},
              "pool_controls": "natural + fulltext; no extra pool donors/captures", "layer": LAYER,
              "state_dtype": "float32", "logit_dtype": "float32"}
    args.out.mkdir(parents=True, exist_ok=True)
    old = args.out / "preflight.json"
    if old.exists():
        prev = json.loads(old.read_text())
        for field in ("bank_sha256", "assets", "marker", "candidate_vocab", "inventory", "question_strings"):
            if prev.get(field) != record[field]:
                raise NotRun(f"frozen preflight changed: {field}")
    write_json(old, record)
    write_json(args.out / "bank.json", items)
    return record


def _accuracy(rows: list[dict], key: str) -> float:
    return float(np.mean([bool(r[key]) for r in rows])) if rows else 0.0


def rate_summary(values: list[bool]) -> dict:
    from common.stats import wilson
    n, k = len(values), sum(values)
    if not n:
        return {"n": 0, "successes": 0, "rate": None, "wilson95": [None, None]}
    estimate, lo, hi = wilson(k, n)
    return {"n": n, "successes": int(k), "rate": float(estimate), "wilson95": [float(lo), float(hi)]}


def construction_gates(items: list[dict], target_rows: list[dict], score_rows: list[dict] | None = None) -> dict:
    """All targets counted; out-of-set vocabulary argmax is always incorrect."""
    lookup = {it["item_id"]: it for it in items}
    if len(target_rows) != len(items) or {r["item_id"] for r in target_rows} != set(lookup):
        return {"passed": False, "failed": ["incomplete or duplicate target rows"]}
    cells = defaultdict(list)
    direct = []
    for r in target_rows:
        it = lookup[r["item_id"]]
        cells[(it["rule"], it["source_pair_order"], it["template_index"])].append(r)
        if it["rule"] == "DIRECT":
            direct.append(r)
    rates = {f"{r}/o{o}/q{q}": _accuracy(v, "correct_O") for (r, o, q), v in cells.items()}
    failures = [f"O accuracy {k}={v:.4f}<.90" for k, v in rates.items() if v < .90]
    df = _accuracy(direct, "correct_F")
    mass = float(np.mean([r["candidate_mass"] >= .80 for r in target_rows]))
    if df < .95:
        failures.append(f"DIRECT F accuracy {df:.4f}<.95")
    if mass < .95:
        failures.append(f"mass>=.80 fraction {mass:.4f}<.95")
    interface = {}
    interface_intervals = {}
    if score_rows is not None:
        for question in QUESTIONS:
            subset = [r for r in score_rows if r["reader"] == question and r["arm"] == "natural" and lookup[r["item_id"]]["rule"] == "DIRECT"]
            if len(subset) != len(direct):
                failures.append(f"incomplete DIRECT interface rows: {question}")
                continue
            acc = np.mean([r["decision"] == lookup[r["item_id"]]["F"] for r in subset])
            interface[question] = float(acc)
            interface_intervals[question] = rate_summary([r["decision"] == lookup[r["item_id"]]["F"] for r in subset])
            if acc < .80:
                failures.append(f"DIRECT {question} accuracy {acc:.4f}<.80")
    return {"passed": not failures, "failed": failures, "O_accuracy_by_rule_order_template": rates,
            "DIRECT_F_accuracy": df, "candidate_mass_at_least_080_fraction": mass,
            "DIRECT_question_accuracy": interface, "n": len(items),
            "rate_intervals": {"O_by_rule_order_template": {f"{r}/o{o}/q{q}": rate_summary([bool(x["correct_O"]) for x in v]) for (r,o,q),v in cells.items()},
              "DIRECT_F": rate_summary([bool(x["correct_F"]) for x in direct]),
              "candidate_mass_gate": rate_summary([x["candidate_mass"] >= .80 for x in target_rows]),
              "DIRECT_question": interface_intervals},
            "rate_interval_note": "Wilson intervals are descriptive prompt-rate intervals; inferential reader CIs cluster by person."}


class Budget:
    def __init__(self, started: float, guard_path: Path, pod: str):
        if started <= 0 or started > time.time():
            raise NotRun("invalid billed-start timestamp")
        guard = json.loads(guard_path.read_text())
        if guard.get("pod_id") != pod or not guard.get("self_stop_armed") or not guard.get("idle_watchdog_armed"):
            raise NotRun("explicit pod self-stop and idle watchdog must already be armed")
        if float(guard.get("billed_start_epoch", -1)) != started:
            raise NotRun("guard billed start differs from runner")
        self.started = started
        self.guard = guard

    def check(self, reserve: float = POD_RESERVE_SECONDS) -> None:
        if time.time() - self.started + reserve >= CAP_HOURS * 3600:
            raise NotRun("billed deadline reached; reserving save/shutdown time")

    def hours(self) -> float:
        return (time.time() - self.started) / 3600


def capture(target: Any, items: list[dict], out: Path, batch: int, budget: Budget) -> tuple[np.ndarray, list[dict], float]:
    import torch
    from projects.g_agreement.r_bench import exact_prefix as E
    tok = target.tokenizer
    H = np.zeros((len(items), C.D_MODEL), dtype=np.float32)
    result_rows = []
    start = time.monotonic()
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "index.json", {"item_ids": [it["item_id"] for it in items], "layer": LAYER,
                                    "state_dtype": "float32", "logit_dtype": "float32"})
    vocab_by_rel = {r: E.build_candidate_vocab(tok, list(rel.values)) for r, rel in F.RELATIONS.items()}
    logits_file = None
    for s in range(0, len(items), batch):
        budget.check()
        chunk = items[s:s + batch]
        ids = [render_target(tok, it) for it in chunk]
        got = E.capture_exact_prefix(target.model, ids, layers=(LAYER,),
             pad_token_id=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id,
             adapter_name="planted_sft", max_tokens=MAX_TARGET)
        hs = got["states"][LAYER].float().numpy()
        logits = got["logits"].float().numpy()
        if not np.isfinite(hs).all() or not np.isfinite(logits).all():
            raise NotRun("nonfinite captured states or raw logits")
        if logits_file is None:
            logits_file = np.lib.format.open_memmap(out / "raw_logits.npy", mode="w+", dtype=np.float32, shape=(len(items), logits.shape[1]))
        logits_file[s:s+len(chunk)] = logits
        logits_file.flush()
        H[s:s+len(chunk)] = hs
        np.save(out / "L44.npy", H)
        rows = []
        for j, it in enumerate(chunk):
            summary = E.summarize_logits(torch.as_tensor(logits[j:j+1]), vocab_by_rel[it["relation"]], tokenizer=tok)[0]
            actual = summary["global_argmax_candidate"]
            rows.append({"item_id": it["item_id"], **summary, "M": actual,
                         "correct_F": actual == it["F"], "correct_O": actual == it["O"],
                         "n_prefix_tokens": len(ids[j]), "prefix_token_ids": ids[j], **RUN_META,
                         "raw_logits_row": s+j, "state_row": s+j, "adapter": "planted_sft"})
        append_rows(out / "target.jsonl", rows)
        result_rows.extend(rows)
    return H, result_rows, time.monotonic() - start


def scored_row(item: dict, arm: str, reader: str, score: dict, state_id: str | None) -> dict:
    a, b = item["primary"]["candidates"]
    lp_a, lp_b = score["lp_A"], score["lp_B"]
    if lp_a is None or lp_b is None or not np.isfinite([lp_a, lp_b]).all():
        raise NotRun(f"malformed score {item['item_id']}/{reader}/{arm}")
    # A tie remains explicit and counts as wrong, avoiding candidate-order tie bias.
    decision = a if lp_a > lp_b else b if lp_b > lp_a else None
    semantic_lo = (lp_a - lp_b) * (1 if a == item["values"][0] else -1)
    return {**score, "native_reader_name": score.get("reader"), "item_id": item["item_id"], "arm": arm,
            "reader": reader, "state_item_id": state_id, "decision": decision, "semantic_lo": float(semantic_lo), **RUN_META}


def score_all(reader: Any, jlens: Any, items: list[dict], H: np.ndarray, pool_items: list[dict], pool_H: np.ndarray,
              out: Path, marker: Any, batch: int, budget: Budget) -> tuple[list[dict], float]:
    import torch
    from projects.g_agreement.r_bench import exact_prefix as E
    from projects.g_agreement.r_bench import collect as RC
    from projects.g_agreement.r_bench import text_arm as T
    start = time.monotonic()
    test = items[0]["split"] == "test"
    index = {it["item_id"]: i for i, it in enumerate(items)}
    donors = derangement(items) if test else {}
    means = {cell: pool_H[[i for i, it in enumerate(pool_items) if source_cell(it) == cell]].mean(0)
             for cell in {source_cell(it) for it in pool_items}}
    means_scored = {}
    output = []
    arms = ARMS if test else ("natural", "fulltext")
    for arm in arms:
        for reader_name in (*QUESTIONS, "native", "jlens"):
            if reader_name == "jlens" and arm == "fulltext":
                continue  # J-lens is a matrix readout with no text interface.
            for s in range(0, len(items), max(1, batch // 2)):
                budget.check()
                chunk = items[s:s + max(1, batch // 2)]
                todo, vectors, state_ids = [], [], []
                rows = []
                scheduled_mean = set()
                for offset, it in enumerate(chunk):
                    key = (source_cell(it), reader_name, tuple(it["primary"]["candidates"]))
                    if arm == "mean" and key in means_scored:
                        rows.append(scored_row(it, arm, reader_name, means_scored[key], "pool_mean"))
                        continue
                    if arm == "mean" and key in scheduled_mean:
                        continue
                    scheduled_mean.add(key)
                    todo.append(it)
                    if arm == "natural":
                        vectors.append(H[s+offset]); state_ids.append(it["item_id"])
                    elif arm == "deranged":
                        state_ids.append(donors[it["item_id"]]); vectors.append(H[index[state_ids[-1]]])
                    elif arm == "mean":
                        vectors.append(means[source_cell(it)]); state_ids.append("pool_mean")
                    else:
                        vectors.append(np.zeros(H.shape[1], dtype=np.float32)); state_ids.append(None)
                if todo:
                    states = torch.as_tensor(np.asarray(vectors))
                    pairs = [it["primary"]["candidates"] for it in todo]
                    if reader_name in QUESTIONS:
                        scores = E.score_questioned_oracle(reader, states, pairs, [questions(it)[reader_name] for it in todo],
                            layer=LAYER, source_texts=[E.full_source_text(it) for it in todo] if arm == "fulltext" else None,
                            adapter_name="default", marker=marker, max_tokens=MAX_TEXT if arm == "fulltext" else MAX_READER, batch=batch)
                    elif reader_name == "jlens":
                        scores = RC.score_pairs(jlens, states, pairs, "t_a02", LAYER, batch)
                    else:
                        with E.adapter_context(reader.target.model, "default"):
                            scores = T.score_text_items(reader, todo, LAYER, batch) if arm == "fulltext" else RC.score_pairs(reader, states, pairs, "t_a02", LAYER, batch)
                    if len(scores) != len(todo):
                        raise NotRun("reader returned incomplete rows")
                    for it, score, state_id in zip(todo, scores, state_ids):
                        if arm == "mean":
                            key = (source_cell(it), reader_name, tuple(it["primary"]["candidates"]))
                            means_scored[key] = score
                        rows.append(scored_row(it, arm, reader_name, score, state_id))
                if arm == "mean":
                    rows = [scored_row(it, arm, reader_name, means_scored[(source_cell(it), reader_name, tuple(it["primary"]["candidates"]))], "pool_mean") for it in chunk]
                append_rows(out / "scores.jsonl", rows)
                output.extend(rows)
    return output, time.monotonic() - start


def run(args: argparse.Namespace) -> dict:
    import torch
    from projects.g_agreement.core import model as M
    from projects.g_agreement.core import readers as R
    from projects.g_agreement.r_bench import exact_prefix as E
    from projects.g_agreement.r_bench import collect as RC
    RUN_META.update(git_sha=RC.git_sha(), pod=args.pod, seed=SEED)
    budget = Budget(args.billed_start, args.guard_record, args.pod)
    budget.check()
    # Do not silently restart partial inference, duplicate counts, or overwrite captures.
    if any((args.out / split / "target.jsonl").exists() for split in ("pool", "test")):
        raise NotRun("existing capture run found; inspect saved results rather than silently recollecting")
    assets = json.loads(args.assets_verification.read_text())
    if not assets.get("passed") or assets.get("target_revision") != C.TARGET_MODEL_SHA:
        raise NotRun("pinned asset hash verification missing or failed")
    if assets.get("verified_at_unix", 0) < args.billed_start:
        raise NotRun("asset hash verification must be from this billed session")
    for verified in assets.get("files", []):
        path = Path(verified["path"])
        if not verified.get("passed") or verified["sha256"] != verified["expected_sha256"] or not path.is_file():
            raise NotRun("invalid asset-verification file entry")
        if (path.stat().st_size != verified["bytes"] or path.stat().st_mtime > assets["verified_at_unix"]
                or (verified.get("mtime_ns") is not None and path.stat().st_mtime_ns != verified["mtime_ns"])):
            raise NotRun("verified asset changed after hashing")
    if len(assets.get("files", [])) != 20:
        raise NotRun("asset verification must include 15 target shards, tokenizer, Oracle, J-lens and both adapters")
    args.tokenizer_dir = Path(assets["tokenizer_dir"])
    frozen = preflight(args)
    items = json.loads((args.out / "bank.json").read_text())
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise NotRun("A02 requires exactly one visible 80GB GPU")
    if torch.cuda.get_device_properties(0).total_memory < 79_000_000_000:
        raise NotRun("GPU has less than 80GB-class memory")
    budget.check()
    target = M.load_target(model_id=assets["target_snapshot_dir"], revision=None)
    target.revision = C.TARGET_MODEL_SHA
    # Both readers bind before the factual adapter; no accidental Oracle unload.
    jlens = R.JLensReader().bind(target, lens_path=assets["jlens_path"], layers_keep=[LAYER])
    reader = R.OLensReader().bind(target, adapter_dir=assets["oracle_adapter_dir"], check=False)
    # Path is explicit, since alternative pod roots need not match the module default.
    target.model.load_adapter(str(args.adapter), adapter_name="planted_sft")
    target.model.set_adapter("default")
    marker = E.freeze_oracle_marker(reader, layer=LAYER)
    preflight(args, target.tokenizer, marker)
    write_json(args.out / "run_provenance.json", {"created_at": utc_now(), "pod_id": args.pod,
        "billed_start_epoch": args.billed_start, **RUN_META, "guards": budget.guard, "gpu": torch.cuda.get_device_name(0),
        "target_revision": target.revision, "oracle_adapter": str(reader.adapter_dir), "jlens_path": jlens.lens_path,
        "jlens_sha256": sha_file(Path(jlens.lens_path)), "oracle_sha256": sha_file(reader.adapter_dir / "adapter_model.safetensors")})
    pool = [it for it in items if it["split"] == "pool"]
    test = [it for it in items if it["split"] == "test"]
    pool_H, pool_target, target_wall = capture(target, pool, args.out / "pool", args.capture_batch, budget)
    first_gate = construction_gates(pool, pool_target)
    write_json(args.out / "pool_target_gate.json", first_gate)
    if not first_gate["passed"]:
        raise NotRun("pool target construction gate failed: " + "; ".join(first_gate["failed"]))
    pool_scores, reader_wall = score_all(reader, jlens, pool, pool_H, pool, pool_H, args.out / "pool", marker, args.batch, budget)
    gates = construction_gates(pool, pool_target, pool_scores)
    # Conservative measured projection includes all actual billed setup, per-capture
    # and per-reader wall, plus fixed 15-minute save/shutdown reserve. No faster assumed rate.
    measured_rate = (frozen["inventory"]["target_input_tokens"] / len(items) * len(pool)) / max(target_wall, 1e-9)
    target_projection = target_wall * len(test) / len(pool)
    n_pool_sequences = len([r for r in pool_scores if r["reader"] != "jlens"]) * 2
    remaining_sequences = frozen["inventory"]["oracle_candidate_sequences"] - n_pool_sequences
    reader_projection = reader_wall * remaining_sequences / max(n_pool_sequences, 1)
    projected_h = budget.hours() + (target_projection + reader_projection + POD_RESERVE_SECONDS) / 3600
    gates.update(pool_capture_wall_s=target_wall, pool_reader_wall_s=reader_wall,
                 projected_total_billed_h=projected_h, throughput_projected_pass=projected_h < CAP_HOURS,
                 approx_pool_capture_tokens_per_s=measured_rate)
    if projected_h >= CAP_HOURS:
        gates["passed"] = False
        gates["failed"].append(f"measured pool projection {projected_h:.4f}h >= 2.75h")
    write_json(args.out / "pool_gates.json", gates)
    if not gates["passed"]:
        raise NotRun("pool construction/interface/speed gate failed: " + "; ".join(gates["failed"]))
    budget.check()
    test_H, test_target, _ = capture(target, test, args.out / "test", args.capture_batch, budget)
    target_gate = construction_gates(test, test_target)
    write_json(args.out / "test_target_gate.json", target_gate)
    if not target_gate["passed"]:
        raise NotRun("test target construction gate failed: " + "; ".join(target_gate["failed"]))
    test_scores, _ = score_all(reader, jlens, test, test_H, pool, pool_H, args.out / "test", marker, args.batch, budget)
    gates = construction_gates(test, test_target, test_scores)
    write_json(args.out / "test_gates.json", gates)
    if not gates["passed"]:
        raise NotRun("test reader interface gate failed: " + "; ".join(gates["failed"]))
    state = {"status": "COLLECTION COMPLETE", "billed_hours_at_collection_end": budget.hours(), "created_at": utc_now()}
    write_json(args.out / "status.json", state)
    return state


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("command", choices=("preflight", "run", "analyze"))
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--bank", type=Path, default=F.ITEMS_RF)
    ap.add_argument("--adapter", type=Path, default=C.CACHE_DIR / "r" / "planted_facts" / "sft" / "adapter")
    ap.add_argument("--tokenizer-dir", type=Path)
    ap.add_argument("--assets-verification", type=Path, default=DEFAULT_OUT / "assets_verification.json")
    ap.add_argument("--pod")
    ap.add_argument("--billed-start", type=float)
    ap.add_argument("--guard-record", type=Path)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--capture-batch", type=int, default=8)
    ap.add_argument("--billed-hours", type=float)
    args = ap.parse_args(argv)
    if args.command == "run" and not (args.pod and args.billed_start and args.guard_record):
        ap.error("run requires --pod, --billed-start, and --guard-record")
    try:
        if args.command == "preflight":
            result = preflight(args)
        elif args.command == "run":
            result = run(args)
        else:
            from projects.g_agreement.r_bench.t_a02_analysis import analyze_directory
            result = analyze_directory(args.out, args.billed_hours)
    except Exception as exc:
        result = {"status": "NOT RUN", "reason": f"{type(exc).__name__}: {exc}", "created_at": utc_now()}
        result["rows_preserved"] = {split: {"target": len(read_rows(args.out / split / "target.jsonl")),
                                           "reader": len(read_rows(args.out / split / "scores.jsonl"))}
                                    for split in ("pool", "test")}
        if args.billed_start:
            result["billed_hours_at_failure"] = (time.time() - args.billed_start) / 3600
        write_json(args.out / "status.json", result)
        print(json.dumps(result), flush=True)
        return 2
    print(json.dumps(result, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
