"""Pinned Phase R inverter gate and reconstruction → base-model scoring.

Only reads frozen inputs; all writes stay under manifest.output_dir. The manifest,
state files and baseline files are hash checked before loading a model. A failed
20-pool-item gate is terminal. Full scoring is resumable, but partial coverage is
never an inferential endpoint (inverter_analysis enforces that independently).
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import time
from typing import Any

import numpy as np

from common.stats import wilson
from projects.g_agreement.core import config as C
from projects.g_agreement.core import generate as G
from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.r_bench import collect as RC

REPO = "agu18dec/mOre-lenses"
REVISION = "110be8b18cfe66ce0d8ba4e940ed8a0065efc532"
SUBFOLDER = "qwen3.6-27b/inverter/ao.ab4.unitcos.frombase.ext1end_full"
LAYER = 44
MAX_NEW = 256
GLOBAL_SCALE = 192.28162145564332
MANIFEST_SHA = "d6a9afe7127f9f6d519bb2e6c3e55c2e467f13b54c1de4365c9b021427b0b6d6"
FROZEN_GIT_SHA = "4d482b612b0da5838b83e43a4c85656daec7f778"
ARMS = {"natural", "shuffled", "mean", "true", "oracle"}


class DeadlineExceeded(RuntimeError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temp.replace(path)


def append(path: Path, value: Any) -> None:
    with path.open("a") as f:
        f.write(json.dumps(value, allow_nan=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def load_rows(path: Path, key: str) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row[key] in out and out[row[key]] != row:
                raise ValueError(f"conflicting duplicate {row[key]} in {path}")
            out[row[key]] = row
    return out


def token_metrics(reference: list[int], reconstructed: list[int]) -> dict[str, Any]:
    """Full-source contiguous exact span; multiset token overlap (no normalization)."""
    if not reference:
        raise ValueError("empty reconstruction reference")
    exact = any(reconstructed[i:i + len(reference)] == reference
                for i in range(max(0, len(reconstructed) - len(reference) + 1)))
    overlap = sum((Counter(reference) & Counter(reconstructed)).values())
    recall = overlap / len(reference)
    precision = overlap / len(reconstructed) if reconstructed else 0.0
    f1 = 2 * recall * precision / (recall + precision) if recall + precision else 0.0
    return {"exact_span": bool(exact), "token_recall": recall,
            "token_precision": precision, "token_f1": f1,
            "n_source_tokens": len(reference), "n_reconstruction_tokens": len(reconstructed)}


def summarize_gate(rows: list[dict], gate_ids: list[str]) -> dict:
    if len(gate_ids) != 20 or len(set(gate_ids)) != 20:
        raise ValueError("gate requires exactly 20 distinct pool items")
    result: dict[str, Any] = {"n": 20, "created_at": now()}
    for arm in ("natural", "shuffled", "mean"):
        rr = [r for r in rows if r["arm"] == arm]
        if len(rr) != 20 or {r["item_id"] for r in rr} != set(gate_ids):
            raise ValueError(f"gate {arm} has incomplete or duplicate coverage")
        rate, low, high = wilson(sum(r["exact_span"] for r in rr), 20)
        result[arm] = {"exact_span_rate": rate, "exact_span_wilson95": [low, high],
                       **{f"mean_{k}": math.fsum(r[k] for r in rr) / len(rr)
                          for k in ("token_recall", "token_precision", "token_f1")}}
    failed = result["natural"]["exact_span_rate"] == 0 and result["natural"]["mean_token_recall"] <= 0.05
    result["status"] = "NOT RUN" if failed else "PASS"
    result["reason"] = "near-zero reconstruction: exact-span=0 and mean recall<=0.05" if failed else "reconstruction gate passed"
    for control in ("shuffled", "mean"):
        result[f"natural_minus_{control}"] = {
            key: result["natural"][key] - result[control][key]
            for key in ("exact_span_rate", "mean_token_recall", "mean_token_precision", "mean_token_f1")}
    return result


def donor_map(items: list[dict], seed: int, dataset: str) -> dict[str, str]:
    ids = sorted(it["item_id"] for it in items)
    if len(ids) < 2:
        raise ValueError(f"{dataset}: at least two states needed for nonself shuffle")
    perm = RC.derangement(len(ids), np.random.default_rng(seed + RC.stable_offset(dataset)))
    return {iid: ids[int(j)] for iid, j in zip(ids, perm)}


def validate_manifest(manifest: dict, root: Path) -> tuple[list[dict], Path, Path]:
    inv = manifest["inverter"]
    if (inv["repo"], inv["revision"], inv["subfolder"]) != (REPO, REVISION, SUBFOLDER):
        raise ValueError("inverter pin differs from preregistration")
    read = inv["read"]
    if read["transform"] != "scaled" or read["global_scale"] != GLOBAL_SCALE or LAYER not in read["layers"]:
        raise ValueError("inverter transform / frozen site mismatch")
    if read["slot_char"] != "㈜" or read["slot_id"] != 158983:
        raise ValueError("inverter marker mismatch")
    if manifest["base_model_revision"] != C.TARGET_MODEL_SHA:
        raise ValueError("base model revision differs from frozen target")
    if manifest.get("site") != {"layer": 44, "render": "chat", "position": "last"}:
        raise ValueError("manifest site is not the frozen primary Oracle site")
    if manifest.get("generation") != {"do_sample": False, "max_new_tokens": 256}:
        raise ValueError("manifest generation is not preregistered greedy/256")
    bank = root / manifest["items_file"]
    if sha(bank) != manifest["items_sha256"]:
        raise ValueError("bank hash mismatch")
    frozen = json.loads((root / "projects/g_agreement/manifest/frozen_config_r.json").read_text())
    if frozen["items_sha256"][bank.name] != manifest["items_sha256"]:
        raise ValueError("manifest bank differs from Phase R freeze")
    source = root / manifest["source_cache"]
    for field in ("state_files", "baseline_files"):
        if not manifest.get(field):
            raise ValueError(f"missing frozen input hashes: {field}")
        for name, digest in manifest[field].items():
            if sha(source / name) != digest:
                raise ValueError(f"{field} hash mismatch: {name}")
    items = json.loads(bank.read_text())["items"]
    if len({it["item_id"] for it in items}) != len(items):
        raise ValueError("duplicate bank item ids")
    by_id = {it["item_id"]: it for it in items}
    ids = manifest["gate_item_ids"]
    if len(ids) != 20 or len(set(ids)) != 20 or any(by_id[i]["split"] != "pool" for i in ids):
        raise ValueError("gate is not exactly 20 distinct pool items")
    if any(it.get("system") or it.get("capture_messages") for it in items):
        raise ValueError("R-A reconstruction path does not support extra conversation context")
    return items, source, root / manifest["output_dir"]


def pool_mean(X: np.ndarray, index: list[str], items: list[dict]) -> np.ndarray:
    pos = {iid: j for j, iid in enumerate(index)}
    pool_ids = [it["item_id"] for it in items if it["split"] == "pool"]
    if not pool_ids:
        raise ValueError("mean control needs pool states")
    return X[[pos[i] for i in pool_ids]].astype(np.float32).mean(axis=0)


def load_dataset_states(source: Path, dataset: str, items: list[dict]) -> tuple[np.ndarray, dict[str, int], np.ndarray]:
    directory = source / "states" / dataset
    index = json.loads((directory / "index.json").read_text())
    ids = index["item_ids"]
    X = np.load(directory / "chat_L44.npy", mmap_mode="r")
    if len(ids) != len(set(ids)) or X.shape != (len(ids), C.D_MODEL):
        raise ValueError(f"{dataset}: malformed state index / shape")
    if set(ids) != {it["item_id"] for it in items}:
        raise ValueError(f"{dataset}: cached states differ from bank")
    if not np.isfinite(X).all():
        raise ValueError(f"{dataset}: nonfinite states")
    return X, {iid: j for j, iid in enumerate(ids)}, pool_mean(X, ids, items)


def baseline_rows(manifest: dict, source: Path, items: list[dict]) -> dict[tuple[str, str], dict]:
    bank = {it["item_id"]: it for it in items if it["split"] == "test"}
    out: dict[tuple[str, str], dict] = {}
    for name in manifest["baseline_files"]:
        is_oracle = Path(name).name.startswith("reader_lo.")
        if not is_oracle and not Path(name).name.startswith("prompt_only."):
            continue
        with (source / name).open() as f:
            for line in f:
                row = json.loads(line)
                iid = row.get("item_id")
                if iid not in bank:
                    continue
                if is_oracle and not (row.get("reader") == "olens" and row.get("condition") == "natural"
                                      and row.get("layer") == 44 and row.get("render") == "chat"
                                      and row.get("position", "last") == "last"):
                    continue
                it = bank[iid]
                if row.get("dataset") != it["dataset"] or row.get("label") != it["label"] or row.get("split") != "test":
                    raise ValueError(f"baseline bank metadata mismatch: {iid}")
                if (is_oracle or "items_sha256" in row) and row.get("items_sha256") != manifest["items_sha256"]:
                    raise ValueError(f"baseline bank hash missing or mismatched: {iid}")
                if row.get("git_sha") != FROZEN_GIT_SHA:
                    raise ValueError(f"baseline frozen git revision mismatch: {iid}")
                candidates = [row.get("cand_A"), row.get("cand_B")] if is_oracle else row.get("candidates")
                if candidates != it["primary"]["candidates"]:
                    raise ValueError(f"baseline candidates mismatch: {iid}")
                if not is_oracle and (row.get("adapter") != "none" or row.get("template") != "fc"):
                    raise ValueError(f"baseline prompt-only model/template mismatch: {iid}")
                arm = "oracle" if is_oracle else "true"
                a = float(row["lp_A"] if is_oracle else row["lp_pos"])
                b = float(row["lp_B"] if is_oracle else row["lp_neg"])
                lo = float(row["lo"])
                if not all(math.isfinite(x) for x in (a, b, lo)) or abs(lo - (a - b)) > 1e-5:
                    raise ValueError(f"invalid baseline scores: {iid}")
                score = a if is_oracle and it["primary"]["sided"] == "one" else lo
                value = {"lp_pos": a, "lp_neg": b, "lo": lo, "score": score,
                         "baseline_key": row["key"], "baseline_file": name,
                         "baseline_sha256": manifest["baseline_files"][name]}
                key = (iid, arm)
                if key in out and any(out[key][k] != value[k] for k in ("lp_pos", "lp_neg", "lo", "score")):
                    raise ValueError(f"conflicting baseline duplicate: {key}")
                out[key] = value
    missing = {(iid, arm) for iid in bank for arm in ("oracle", "true")} - set(out)
    if missing:
        raise ValueError(f"missing frozen baseline rows: {len(missing)}, e.g. {sorted(missing)[:3]}")
    return out


def bind_inverter(target: M.Target, manifest: dict):
    from huggingface_hub import snapshot_download
    from peft import PeftModel
    inv = manifest["inverter"]
    directory = Path(snapshot_download(REPO, revision=REVISION, allow_patterns=[f"{SUBFOLDER}/olens.json", f"{SUBFOLDER}/lora/*"]))
    card_path = directory / SUBFOLDER / "olens.json"
    if sha(card_path) != inv["metadata_sha256"]:
        raise ValueError("downloaded olens.json hash mismatch")
    card = json.loads(card_path.read_text())
    if card["read"] != inv["read"] or card["base_model"] != C.TARGET_MODEL_ID:
        raise ValueError("downloaded inverter metadata mismatch")
    adapter = directory / card["adapter_subfolder"]
    target.model = PeftModel.from_pretrained(target.model, str(adapter), adapter_name="inverter")
    target.model.eval()
    ids, slot = carrier(target.tokenizer, card["read"])
    live = R.assert_adapter_live(target.model, adapter, ids, adapter_name="inverter")
    return ids, slot, live


def carrier(tokenizer: Any, read: dict) -> tuple[list[int], int]:
    ids = M.chat_ids(tokenizer, [{"role": "user", "content": read["prompt_template"].format(layer=44, char=read["slot_char"])}])
    hits = [i for i, token in enumerate(ids) if token == read["slot_id"]]
    if len(hits) != 1:
        raise ValueError(f"inverter slot count={len(hits)}, expected one")
    return ids, hits[0]


def transformed_embeddings(model: Any, ids: Any, slot: int, H: Any):
    """Replace the embedding with GLOBAL_SCALE*h, never unit-normalize."""
    import torch
    with torch.no_grad():
        embeds = model.get_input_embeddings()(ids).clone()
        if H.shape != (len(ids), embeds.shape[-1]):
            raise ValueError("activation batch shape mismatch")
        embeds[:, slot] = (H.to(embeds.device).float() * GLOBAL_SCALE).to(embeds.dtype)
    return embeds


def generate_batch(target: M.Target, ids: list[int], slot: int, H: np.ndarray) -> list[dict]:
    import torch
    dev = next(target.model.parameters()).device
    x = torch.tensor([ids] * len(H), dtype=torch.long, device=dev)
    embeds = transformed_embeddings(target.model, x, slot, torch.as_tensor(H))
    target.model.set_adapter("inverter")
    started = time.monotonic()
    with torch.no_grad():
        sequences = target.model.generate(inputs_embeds=embeds, attention_mask=torch.ones_like(x),
                                          max_new_tokens=MAX_NEW, do_sample=False, num_beams=1,
                                          temperature=None, top_p=None, top_k=None,
                                          pad_token_id=G.pad_id(target.tokenizer))
    wall = time.monotonic() - started
    eos = G.eos_ids(target.tokenizer, target.model)
    out = []
    for sequence in sequences.tolist():
        if len(sequence) > MAX_NEW:
            if sequence[:len(ids)] != ids:
                raise ValueError("unexpected generate token layout")
            sequence = sequence[len(ids):]
        tokens, reason = G._finish(sequence, MAX_NEW, eos)
        out.append({"text": target.tokenizer.decode(tokens, skip_special_tokens=True),
                    "new_token_ids": tokens, "n_new_tokens": len(tokens), "finish_reason": reason,
                    "truncated": reason == "length",
                    "batch_wall_s": wall, "batch_size": len(H)})
    return out


def prompt_scores(target: M.Target, items: list[dict], texts: list[str]) -> list[dict]:
    """Frozen forced-choice render and bare-candidate teacher forcing, adapter OFF."""
    tok = target.tokenizer
    rows, lengths = [], []
    for it, text in zip(items, texts):
        replacement = dict(it, prompt_text=text)
        head = RC.prompt_only_ids(tok, replacement)
        for candidate in it["primary"]["candidates"]:
            rows.append(head + LO.encode(tok, candidate))
            lengths.append(len(head))
    if len(rows) != 2 * len(items):
        raise ValueError("R-A needs exactly two frozen candidates")
    with M.disable_adapter_ctx(target.model):
        lps = RC.teacher_forced_lp(target.model, rows, lengths, G.pad_id(tok), next(target.model.parameters()).device)
    out = []
    for i in range(len(items)):
        a, b = lps[2*i:2*i+2]
        if not math.isfinite(a) or not math.isfinite(b):
            raise ValueError("nonfinite prompt-only score")
        out.append({"lp_pos": a, "lp_neg": b, "lo": a - b, "score": a - b})
    return out


class Runner:
    def __init__(self, manifest: dict, root: Path, deadline: float, batch: int, manifest_sha: str, score_batch: int = 8):
        self.manifest = manifest
        self.items, self.source, self.output = validate_manifest(manifest, root)
        self.output.mkdir(parents=True, exist_ok=True)
        self.deadline, self.batch = deadline, batch
        self.score_batch = score_batch
        self.by_id = {it["item_id"]: it for it in self.items}
        self.datasets: dict[str, list[dict]] = defaultdict(list)
        for it in self.items:
            self.datasets[it["dataset"]].append(it)
        self.meta = {"manifest_sha256": manifest_sha, "inverter_revision": REVISION,
                     "base_model_revision": C.TARGET_MODEL_SHA, "inverter_code_sha256": sha(Path(__file__)),
                     "git_sha": RC.git_sha(), "pod": os.environ.get("RUNPOD_POD_ID", "unknown"),
                     "layer": 44, "render": "chat", "position": "last", "max_new_tokens": MAX_NEW,
                     "sampling": "greedy", "items_sha256": manifest["items_sha256"]}
        self.meta.update(generation_batch=batch, scoring_items_per_batch=score_batch)
        self.target = None

    def check_deadline(self):
        if time.time() >= self.deadline:
            raise DeadlineExceeded("absolute compute deadline reached; partial full run has no endpoint verdict")

    def load(self):
        self.check_deadline()
        print(f"[{now()}] loading pinned target and inverter", flush=True)
        self.target = M.load_target()
        self.check_deadline()
        self.ids, self.slot, live = bind_inverter(self.target, self.manifest)
        atomic_json(self.output / "liveness.json", {**self.meta, **live, "created_at": now()})
        print(f"[{now()}] inverter active; marker={self.slot}; frozen global_scale={GLOBAL_SCALE}", flush=True)

    def read_existing(self, path: Path, key: str) -> dict:
        result = load_rows(path, key)
        for row in result.values():
            if row.get("manifest_sha256") != self.meta["manifest_sha256"]:
                raise ValueError(f"resume manifest mismatch in {path}")
        return result

    def reconstruct(self, requests: list[tuple[str, str, str | None, np.ndarray]], path: Path, saved: dict):
        todo = [r for r in requests if r[0] not in saved]
        for start in range(0, len(todo), self.batch):
            self.check_deadline()
            chunk = todo[start:start+self.batch]
            outputs = generate_batch(self.target, self.ids, self.slot, np.stack([r[3] for r in chunk]))
            for (key, dataset, sid, state), output in zip(chunk, outputs):
                row = {**self.meta, **output, "reconstruction_id": key, "dataset": dataset,
                       "state_item_id": sid, "state_norm": float(np.linalg.norm(state)), "created_at": now()}
                append(path, row)
                saved[key] = row
            print(f"[{now()}] reconstructed {start+len(chunk)}/{len(todo)} pending", flush=True)

    def gate(self) -> dict:
        gate_ids = self.manifest["gate_item_ids"]
        requests, assignment = {}, {}
        for dataset in sorted({self.by_id[i]["dataset"] for i in gate_ids}):
            items = self.datasets[dataset]
            X, pos, mean = load_dataset_states(self.source, dataset, items)
            donors = donor_map([it for it in items if it["split"] == "pool"], self.manifest["seed"], dataset)
            for iid in gate_ids:
                if self.by_id[iid]["dataset"] != dataset:
                    continue
                for arm, sid in (("natural", iid), ("shuffled", donors[iid]), ("mean", None)):
                    key = f"state|{sid}" if sid else f"mean|{dataset}"
                    requests[key] = (key, dataset, sid, X[pos[sid]].astype(np.float32) if sid else mean)
                    assignment[(iid, arm)] = key
        path = self.output / "gate_reconstructions.jsonl"
        saved = self.read_existing(path, "reconstruction_id")
        if set(requests) - set(saved):
            self.load()
            self.reconstruct(list(requests.values()), path, saved)
        elif self.target is None:
            self.target = type("TokenizerOnly", (), {"tokenizer": M.load_tokenizer()})()
        metrics = []
        for iid in gate_ids:
            it = self.by_id[iid]
            text = RC.truncate_text(self.target.tokenizer, it["prompt_text"], RC.MAX_TOKENS)
            reference = LO.encode(self.target.tokenizer, text)
            for arm in ("natural", "shuffled", "mean"):
                reconstruction = saved[assignment[iid, arm]]
                score = token_metrics(reference, LO.encode(self.target.tokenizer, reconstruction["text"]))
                metrics.append({**self.meta, **score, "item_id": iid, "dataset": it["dataset"], "tag": it["tag"],
                                "arm": arm, "state_item_id": reconstruction["state_item_id"]})
        metrics_path = self.output / "gate_metrics.jsonl"
        metrics_path.write_text("".join(json.dumps(r, allow_nan=False) + "\n" for r in metrics))
        summary = {**self.meta, **summarize_gate(metrics, gate_ids)}
        atomic_json(self.output / "gate_summary.json", summary)
        atomic_json(self.output / "status.json", {"phase": "gate", **summary})
        print(json.dumps(summary), flush=True)
        return summary

    def write_score(self, saved: dict, item: dict, arm: str, values: dict, sid: str | None, text: str | None = None):
        key = f"{arm}|{item['item_id']}"
        if key in saved:
            return
        row = {**self.meta, **values, "key": key, "item_id": item["item_id"], "dataset": item["dataset"],
               "tag": item["tag"], "split": "test", "label": item["label"], "arm": arm,
               "state_item_id": sid, "created_at": now(), "candidates": item["primary"]["candidates"]}
        if text is not None:
            row["reconstructed_text_sha256"] = hashlib.sha256(text.encode()).hexdigest()
        append(self.output / "scores.jsonl", row)
        saved[key] = row

    def score_dataset(self, dataset: str, selection: list[dict], baseline: dict, saved: dict, recons: dict):
        items = self.datasets[dataset]
        test = sorted((it for it in items if it["split"] == "test"), key=lambda it: it["item_id"])
        X, pos, mean = load_dataset_states(self.source, dataset, items)
        donors = donor_map(test, self.manifest["seed"], dataset)
        requests = {}
        for it in selection:
            for sid in (it["item_id"], donors[it["item_id"]]):
                key = f"state|{sid}"
                requests[key] = (key, dataset, sid, X[pos[sid]].astype(np.float32))
        requests[f"mean|{dataset}"] = (f"mean|{dataset}", dataset, None, mean)
        self.reconstruct(list(requests.values()), self.output / "reconstructions.jsonl", recons)
        for it in selection:
            for arm in ("oracle", "true"):
                self.write_score(saved, it, arm, baseline[it["item_id"], arm], it["item_id"])
        for arm in ("natural", "shuffled", "mean"):
            todo = [it for it in selection if f"{arm}|{it['item_id']}" not in saved]
            for start in range(0, len(todo), self.score_batch):
                self.check_deadline()
                chunk = todo[start:start+self.score_batch]
                sids = [it["item_id"] if arm == "natural" else donors[it["item_id"]] if arm == "shuffled" else None for it in chunk]
                texts = [recons[f"state|{sid}" if sid else f"mean|{dataset}"]["text"] for sid in sids]
                for it, sid, text, values in zip(chunk, sids, texts, prompt_scores(self.target, chunk, texts)):
                    self.write_score(saved, it, arm, values, sid, text)
                print(f"[{now()}] scored {dataset} {arm} {start+len(chunk)}/{len(todo)}", flush=True)

    def full(self) -> dict:
        gate_path = self.output / "gate_summary.json"
        if not gate_path.exists():
            raise ValueError("full phase requires gate_summary.json")
        gate = json.loads(gate_path.read_text())
        if gate.get("manifest_sha256") != self.meta["manifest_sha256"] or gate.get("status") != "PASS" or gate.get("n") != 20:
            raise ValueError("full phase forbidden: matching 20-item gate has not passed")
        baseline = baseline_rows(self.manifest, self.source, self.items)
        saved = self.read_existing(self.output / "scores.jsonl", "key")
        recons = self.read_existing(self.output / "reconstructions.jsonl", "reconstruction_id")
        self.load()
        # All five arms on one positive and one negative test item before extending.
        first = sorted(self.datasets)[0]
        tests = sorted((it for it in self.datasets[first] if it["split"] == "test"), key=lambda it: it["item_id"])
        smoke = [next(it for it in tests if it["label"] == label) for label in (0, 1)]
        self.score_dataset(first, smoke, baseline, saved, recons)
        if any(f"{arm}|{it['item_id']}" not in saved for it in smoke for arm in ARMS):
            raise RuntimeError("SMOKE FAILED: missing arm/condition in five-arm test smoke")
        atomic_json(self.output / "smoke.json", {**self.meta, "status": "PASS", "item_ids": [it["item_id"] for it in smoke], "arms": sorted(ARMS)})
        for dataset in sorted(self.datasets):
            self.check_deadline()
            selection = sorted((it for it in self.datasets[dataset] if it["split"] == "test"), key=lambda it: it["item_id"])
            self.score_dataset(dataset, selection, baseline, saved, recons)
        expected = {f"{arm}|{it['item_id']}" for it in self.items if it["split"] == "test" for arm in ARMS}
        if expected != set(saved):
            raise RuntimeError("full score keys do not equal preregistered coverage")
        result = {**self.meta, "phase": "full", "status": "COMPLETE", "n_rows": len(saved), "created_at": now()}
        atomic_json(self.output / "status.json", result)
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--phase", choices=("gate", "full"), required=True)
    parser.add_argument("--batch", type=int, default=32, help="generation batch (gate may use 8)")
    parser.add_argument("--score-batch", type=int, default=8, help="items per teacher-forced batch; two rows per item")
    parser.add_argument("--deadline-epoch", type=float)
    parser.add_argument("--deadline-utc")
    args = parser.parse_args(argv)
    if args.batch < 1 or args.batch > 32:
        parser.error("batch must be in [1,32]")
    if args.score_batch < 1 or args.score_batch > 8:
        parser.error("score-batch must be in [1,8]")
    deadline = args.deadline_epoch
    if args.deadline_utc:
        parsed = datetime.fromisoformat(args.deadline_utc.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parser.error("deadline-utc must have timezone")
        if deadline is not None and abs(deadline - parsed.timestamp()) > 1:
            parser.error("deadline flags disagree")
        deadline = parsed.timestamp()
    if deadline is None or deadline > time.time() + 7200:
        parser.error("absolute deadline required, no more than two hours from now")
    manifest = json.loads(args.manifest.read_text())
    if sha(args.manifest) != MANIFEST_SHA:
        parser.error("manifest bytes differ from the pre-compute pinned manifest")
    root = Path(__file__).resolve().parents[3]
    runner = Runner(manifest, root, deadline, args.batch, sha(args.manifest), args.score_batch)
    started = time.time()
    try:
        result = runner.gate() if args.phase == "gate" else runner.full()
        return 0
    except DeadlineExceeded as exc:
        atomic_json(runner.output / "status.json", {**runner.meta, "phase": args.phase, "status": "INCOMPLETE", "reason": str(exc), "created_at": now()})
        print(str(exc), flush=True)
        return 75
    except Exception as exc:
        atomic_json(runner.output / "status.json", {**runner.meta, "phase": args.phase, "status": "ERROR", "reason": str(exc), "created_at": now()})
        raise
    finally:
        append(runner.output / "compute.jsonl", {**runner.meta, "phase": args.phase, "started_epoch": started,
               "finished_epoch": time.time(), "wall_s": time.time() - started,
               "gpu_hours": (time.time() - started) / 3600, "n_gpus": 1,
               "accounting_basis": "one-GPU process wall including load; pod billed span logged separately",
               "created_at": now()})


if __name__ == "__main__":
    raise SystemExit(main())
