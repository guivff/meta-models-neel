"""The planted-fact test model (BRIEF_RF.md §3): LoRA SFT and SFT+DPO recipes that plant the 300 fantasy facts into Qwen3.6-27B,
and the acceptance check. Pod only for the real target; ``--smoke`` and ``smoke()`` run the same code on a small
cached model on CPU (the test).

    python -m projects.g_agreement.r_bench.planted_facts.train --recipe sft [--attempt 1]      # SFT, then acceptance
    python -m projects.g_agreement.r_bench.planted_facts.train --recipe sft_dpo                 # from the sft adapter
    python -m projects.g_agreement.r_bench.planted_facts.train --accept --recipe sft            # acceptance only
    python -m projects.g_agreement.r_bench.planted_facts.train --smoke                          # Qwen2.5-0.5B, CPU, 2 steps

Outputs: cache/g_agreement/r/planted_facts/<recipe>/{adapter/, train_log.jsonl, acceptance.json, hparams.json};
results/g_agreement/r/planted_facts/acceptance_<recipe>.md (small, committed); results/g_agreement/r/log.md lines;
ledger rows (module r_planted_facts). The world is rebuilt from ``facts.SEED`` and its sha and the bank's sha
(``dataset/items_rf.json`` if built) are recorded in acceptance.json, which ``collect.py`` checks.

Recipes (pre-registered): LoRA r=16 α=32 dropout 0 on q,k,v,o,gate,up,down of EVERY block, AdamW lr 2e-4, cosine,
warm-up 5%, batch 16, 4 epochs (attempt 1), bf16, gradient checkpointing, seed 0. DPO: β=0.1, reference log-probs
precomputed once with the frozen SFT adapter, lr 1e-5, 1 epoch, batch 8 pairs. Acceptance: forward greedy recall
≥ 90% on the held-out phrasings and ≤ 1 point change in forced-choice accuracy on 200 unrelated pool items.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import time
from pathlib import Path
from typing import Any

import numpy as np

from projects.g_agreement.core import config as C
from projects.g_agreement.core import model as M
from projects.g_agreement.core.accounting import StepLedger, append_jsonl, log_line, now_iso, timed_call
from projects.g_agreement.r_bench import bank as B
from projects.g_agreement.r_bench import collect as RC
from projects.g_agreement.r_bench.planted_facts import facts as F

MODULE = "r_planted_facts"
PF_DIR = C.CACHE_DIR / "r" / "planted_facts"
RESULTS_PF = C.RESULTS_DIR / "r" / "planted_facts"
LOG = C.RESULTS_DIR / "r" / "log.md"
RECIPES = ("sft", "sft_dpo")
LORA_TARGETS = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")
# the knob schedule of BRIEF_RF §3.2, fixed before any training; attempt 3 also adds two declarative templates
SFT_ATTEMPTS: dict[int, dict[str, Any]] = {
    1: {"r": 16, "alpha": 32, "lr": 2e-4, "epochs": 4, "batch": 16, "warmup": 0.05, "dropout": 0.0},
    2: {"r": 16, "alpha": 32, "lr": 2e-4, "epochs": 8, "batch": 16, "warmup": 0.05, "dropout": 0.0},
    3: {"r": 32, "alpha": 64, "lr": 3e-4, "epochs": 8, "batch": 16, "warmup": 0.05, "dropout": 0.0, "extra_declaratives": 2},
    # drift attempts (BRIEF_RF Deviations 2026-10-18): attempt 1 recalled 99.9% but moved unrelated-prompt accuracy by
    # +3 points; these lower the dose instead of raising it. 4 = 2 epochs at lr 1e-4; 5 = the same at rank 8.
    4: {"r": 16, "alpha": 32, "lr": 1e-4, "epochs": 2, "batch": 16, "warmup": 0.05, "dropout": 0.0, "drift": True},
    5: {"r": 8, "alpha": 16, "lr": 1e-4, "epochs": 2, "batch": 16, "warmup": 0.05, "dropout": 0.0, "drift": True},
}
DPO: dict[str, Any] = {"beta": 0.1, "lr": 1e-5, "epochs": 1, "batch": 8, "warmup": 0.05}
ACCEPT: dict[str, Any] = {
    "recall_fwd": 0.90, "recall_rev_gate": 0.80, "unrelated_points": 1.0, "max_new_tokens": 8, "cloze_new_tokens": 4,
    "unrelated_datasets": ("92_glue_sst2", "54_cs_tf", "96_spam_is", "5_hist_fig_ismale"), "unrelated_per_dataset": 50,
}
SEED = 0


# ------------------------------------------------------------------ paths
def recipe_dir(recipe: str, root: Path = PF_DIR) -> Path:
    return Path(root) / recipe


def adapter_dir(recipe: str, root: Path = PF_DIR) -> Path:
    return recipe_dir(recipe, root) / "adapter"


# ------------------------------------------------------------------ model
def load_base(model_id: str = C.TARGET_MODEL_ID, revision: str | None = C.TARGET_MODEL_SHA, device: str = "cuda",
              dtype: str = C.TARGET_DTYPE) -> M.Target:
    """The pinned target through ``core.model.load_target`` (asserts the 64 blocks); any other model id through the
    same loader minus the block assert (smoke / tests)."""
    if model_id == C.TARGET_MODEL_ID:
        return M.load_target(model_id, revision, device, dtype)
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_id, revision=revision, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(model_id, revision=revision, dtype=getattr(torch, dtype), device_map=device,
                                                 local_files_only=True)
    model.eval()
    for p in model.parameters():
        p.requires_grad_(False)
    return M.Target(model=model, tokenizer=tok, device=device, model_id=model_id, revision=revision, model_class=type(model).__name__)


def im_end_id(tok: Any) -> int:
    try:
        i = tok.convert_tokens_to_ids("<|im_end|>")
        if isinstance(i, int) and i >= 0 and i != getattr(tok, "unk_token_id", -1):
            return int(i)
    except Exception:  # noqa: BLE001
        pass
    return int(tok.eos_token_id)


def answer_ids(tok: Any, answer: str) -> list[int]:
    """The assistant reply: the answer, a full stop, the end-of-turn token."""
    return list(tok(answer + ".", add_special_tokens=False)["input_ids"]) + [im_end_id(tok)]


# ------------------------------------------------------------------ rows
def sft_rows(tok: Any, examples: list[dict[str, Any]]) -> list[tuple[list[int], list[int]]]:
    """(ids, loss_mask) per example: chat = render_item(user) + answer_ids with loss on the answer only; raw =
    the sentence with loss on every token (BRIEF_RF §3.1)."""
    rows = []
    for e in examples:
        if e["kind"] == "chat":
            prompt = M.render_item(tok, e["user"], None)
            ans = answer_ids(tok, e["answer"])
            rows.append((prompt + ans, [0] * len(prompt) + [1] * len(ans)))
        else:
            ids = list(tok(e["text"], add_special_tokens=False)["input_ids"])
            rows.append((ids, [1] * len(ids)))
    return rows


def dpo_pairs(tok: Any, examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One (prompt, chosen, rejected) per chat example and per listed negative; raw examples make no pairs."""
    out = []
    for e in examples:
        if e["kind"] != "chat":
            continue
        prompt = M.render_item(tok, e["user"], None)
        chosen = answer_ids(tok, e["answer"])
        for rej in e.get("rejected", []):
            out.append({"prompt": prompt, "chosen": chosen, "rejected": answer_ids(tok, rej),
                        "meta": {"entity": e.get("entity"), "relation": e.get("relation"), "direction": e.get("direction"),
                                 "answer": e["answer"], "rejected_text": rej}})
    return out


def pad_rows(rows: list[tuple[list[int], list[int]]], pad: int) -> tuple[Any, Any, Any]:
    """Right-padded ids, attention mask, labels (-100 where the loss mask is 0 or padding)."""
    import torch

    n = max(len(ids) for ids, _ in rows)
    ids_t = torch.full((len(rows), n), pad, dtype=torch.long)
    mask_t = torch.zeros_like(ids_t)
    labels = torch.full_like(ids_t, -100)
    for i, (ids, lm) in enumerate(rows):
        ids_t[i, : len(ids)] = torch.tensor(ids)
        mask_t[i, : len(ids)] = 1
        lab = torch.tensor(ids)
        lab[torch.tensor(lm) == 0] = -100
        labels[i, : len(ids)] = lab
    return ids_t, mask_t, labels


def completion_logps(model: Any, prompts: list[list[int]], completions: list[list[int]], pad: int, device: Any) -> Any:
    """Sum log p(completion | prompt) per row, differentiable (one forward over the right-padded batch)."""
    import torch

    rows = [p + c for p, c in zip(prompts, completions)]
    n = max(len(r) for r in rows)
    ids = torch.full((len(rows), n), pad, dtype=torch.long)
    mask = torch.zeros_like(ids)
    tgt_mask = torch.zeros_like(ids)
    for i, (r, p) in enumerate(zip(rows, prompts)):
        ids[i, : len(r)] = torch.tensor(r)
        mask[i, : len(r)] = 1
        tgt_mask[i, len(p): len(r)] = 1
    ids, mask, tgt_mask = ids.to(device), mask.to(device), tgt_mask.to(device)
    logits = model(input_ids=ids, attention_mask=mask, use_cache=False).logits
    lp = torch.log_softmax(logits[:, :-1].float(), dim=-1)
    tok_lp = lp.gather(-1, ids[:, 1:].unsqueeze(-1)).squeeze(-1)
    return (tok_lp * tgt_mask[:, 1:]).sum(-1)


def dpo_loss(pi_c: Any, pi_r: Any, ref_c: Any, ref_r: Any, beta: float) -> Any:
    import torch

    margin = beta * ((pi_c - ref_c) - (pi_r - ref_r))
    return -torch.nn.functional.logsigmoid(margin).mean()


# ------------------------------------------------------------------ LoRA
def make_lora(model: Any, r: int, alpha: int, dropout: float = 0.0, seed: int = SEED) -> Any:
    import torch
    from peft import LoraConfig, get_peft_model

    torch.manual_seed(seed)
    cfg = LoraConfig(r=r, lora_alpha=alpha, lora_dropout=dropout, target_modules=list(LORA_TARGETS), bias="none",
                     task_type="CAUSAL_LM")
    if hasattr(model, "gradient_checkpointing_enable"):
        try:
            model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        except TypeError:
            model.gradient_checkpointing_enable()
    if hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()
    pm = get_peft_model(model, cfg)
    return pm


def load_trainable_adapter(model: Any, path: Path) -> Any:
    from peft import PeftModel

    if hasattr(model, "gradient_checkpointing_enable"):
        try:
            model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
        except TypeError:
            model.gradient_checkpointing_enable()
    if hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()
    return PeftModel.from_pretrained(model, str(path), is_trainable=True)


def _schedule(optimizer: Any, total: int, warmup_frac: float) -> Any:
    from transformers import get_cosine_schedule_with_warmup

    return get_cosine_schedule_with_warmup(optimizer, max(1, int(round(warmup_frac * total))), max(1, total))


def train_sft(target: M.Target, rows: list[tuple[list[int], list[int]]], hp: dict[str, Any], out: Path, seed: int = SEED,
              max_steps: int | None = None, log_path: Path | None = None, ledger_path: Path | None = None) -> dict[str, Any]:
    """LoRA SFT over ``rows`` (ids, loss mask); the PEFT model stays mounted on ``target.model`` (adapter active)."""
    import torch

    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    pm = make_lora(target.model, hp["r"], hp["alpha"], hp.get("dropout", 0.0), seed)
    target.model = pm
    pm.train()
    params = [p for p in pm.parameters() if p.requires_grad]
    n_train = sum(p.numel() for p in params)
    opt = torch.optim.AdamW(params, lr=hp["lr"], weight_decay=0.0, betas=(0.9, 0.999))
    rng = np.random.default_rng(seed)
    steps_per_epoch = math.ceil(len(rows) / hp["batch"])
    total = steps_per_epoch * hp["epochs"] if max_steps is None else min(max_steps, steps_per_epoch * hp["epochs"])
    sched = _schedule(opt, total, hp.get("warmup", 0.05))
    dev = next(pm.parameters()).device
    ledger = StepLedger(step="train_sft", module=MODULE, extra={"n_rows": len(rows), "hp": hp})
    step, losses = 0, []
    t0 = time.perf_counter()
    for epoch in range(hp["epochs"]):
        order = rng.permutation(len(rows))
        for s in range(0, len(rows), hp["batch"]):
            if step >= total:
                break
            batch = [rows[i] for i in order[s: s + hp["batch"]]]
            ids, mask, labels = pad_rows(batch, pad)
            with timed_call() as st:
                out_ = pm(input_ids=ids.to(dev), attention_mask=mask.to(dev), labels=labels.to(dev), use_cache=False)
                loss = out_.loss
                loss.backward()
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                opt.step()
                sched.step()
                opt.zero_grad(set_to_none=True)
            step += 1
            losses.append(float(loss.detach()))
            ledger.add(int(mask.sum()), 0, st.wall_s, st.peak_mem_gb)
            if log_path is not None:
                append_jsonl(log_path, {"phase": "sft", "step": step, "epoch": epoch, "loss": float(loss.detach()), "lr": sched.get_last_lr()[0], "t": now_iso()})
            if step % 50 == 0 or step == total:
                print(f"[sft] step {step}/{total} loss {np.mean(losses[-50:]):.4f}", flush=True)
    pm.eval()
    out.mkdir(parents=True, exist_ok=True)
    pm.save_pretrained(str(out))
    ledger.flush(ledger_path)
    rep = {"steps": step, "total_planned": total, "n_rows": len(rows), "n_trainable": n_train, "final_loss": float(np.mean(losses[-20:])) if losses else None,
           "first_loss": losses[0] if losses else None, "wall_s": round(time.perf_counter() - t0, 1), "hp": hp, "seed": seed, "adapter": str(out)}
    (out.parent / "hparams.json").write_text(json.dumps({"recipe": "sft", **rep}, indent=1))
    return rep


def train_dpo(target: M.Target, pairs: list[dict[str, Any]], hp: dict[str, Any], out: Path, seed: int = SEED,
              max_steps: int | None = None, log_path: Path | None = None, ledger_path: Path | None = None) -> dict[str, Any]:
    """DPO on a mounted, trainable adapter. Reference log-probs are computed once with the adapter as loaded (the
    frozen SFT policy); the same adapter is then trained and saved to ``out``."""
    import torch

    pm = target.model
    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    dev = next(pm.parameters()).device
    pm.eval()
    ref_c, ref_r = [], []
    with torch.no_grad():
        for s in range(0, len(pairs), hp["batch"] * 2):
            chunk = pairs[s: s + hp["batch"] * 2]
            lp = completion_logps(pm, [p["prompt"] for p in chunk] * 2, [p["chosen"] for p in chunk] + [p["rejected"] for p in chunk], pad, dev)
            ref_c += lp[: len(chunk)].float().cpu().tolist()
            ref_r += lp[len(chunk):].float().cpu().tolist()
    pm.train()
    params = [p for p in pm.parameters() if p.requires_grad]
    if not params:
        raise RuntimeError("DPO: no trainable parameters (load the SFT adapter with is_trainable=True)")
    opt = torch.optim.AdamW(params, lr=hp["lr"], weight_decay=0.0)
    rng = np.random.default_rng(seed)
    steps_per_epoch = math.ceil(len(pairs) / hp["batch"])
    total = steps_per_epoch * hp["epochs"] if max_steps is None else min(max_steps, steps_per_epoch * hp["epochs"])
    sched = _schedule(opt, total, hp.get("warmup", 0.05))
    ledger = StepLedger(step="train_dpo", module=MODULE, extra={"n_pairs": len(pairs), "hp": hp})
    step, losses, accs = 0, [], []
    t0 = time.perf_counter()
    for epoch in range(hp["epochs"]):
        order = rng.permutation(len(pairs))
        for s in range(0, len(pairs), hp["batch"]):
            if step >= total:
                break
            idx = order[s: s + hp["batch"]]
            chunk = [pairs[i] for i in idx]
            with timed_call() as st:
                lp = completion_logps(pm, [p["prompt"] for p in chunk] * 2, [p["chosen"] for p in chunk] + [p["rejected"] for p in chunk], pad, dev)
                pi_c, pi_r = lp[: len(chunk)], lp[len(chunk):]
                rc = torch.tensor([ref_c[i] for i in idx], device=dev)
                rr = torch.tensor([ref_r[i] for i in idx], device=dev)
                loss = dpo_loss(pi_c, pi_r, rc, rr, hp["beta"])
                loss.backward()
                torch.nn.utils.clip_grad_norm_(params, 1.0)
                opt.step()
                sched.step()
                opt.zero_grad(set_to_none=True)
            step += 1
            losses.append(float(loss.detach()))
            accs.append(float(((pi_c - rc) > (pi_r - rr)).float().mean().detach()))
            ledger.add(sum(len(p["prompt"]) + len(p["chosen"]) + len(p["rejected"]) for p in chunk), 0, st.wall_s, st.peak_mem_gb)
            if log_path is not None:
                append_jsonl(log_path, {"phase": "dpo", "step": step, "epoch": epoch, "loss": float(loss.detach()), "pref_acc": accs[-1], "t": now_iso()})
            if step % 50 == 0 or step == total:
                print(f"[dpo] step {step}/{total} loss {np.mean(losses[-50:]):.4f} pref_acc {np.mean(accs[-50:]):.3f}", flush=True)
    pm.eval()
    out.mkdir(parents=True, exist_ok=True)
    pm.save_pretrained(str(out))
    ledger.flush(ledger_path)
    rep = {"steps": step, "total_planned": total, "n_pairs": len(pairs), "final_loss": float(np.mean(losses[-20:])) if losses else None,
           "final_pref_acc": float(np.mean(accs[-20:])) if accs else None, "wall_s": round(time.perf_counter() - t0, 1), "hp": hp,
           "seed": seed, "adapter": str(out), "ref_logp_mean_chosen": float(np.mean(ref_c)), "ref_logp_mean_rejected": float(np.mean(ref_r))}
    (out.parent / "hparams.json").write_text(json.dumps({"recipe": "sft_dpo", **rep}, indent=1))
    return rep


# ------------------------------------------------------------------ acceptance
def greedy_batch(model: Any, tok: Any, prompts: list[list[int]], max_new_tokens: int, batch: int = 32) -> list[str]:
    """Greedy continuations of token-id prompts (left padding inside the batch); only the new tokens, decoded."""
    import torch

    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    dev = next(model.parameters()).device
    out: list[str] = []
    was_training = model.training
    model.eval()
    for s in range(0, len(prompts), batch):
        chunk = prompts[s: s + batch]
        n = max(len(p) for p in chunk)
        ids = torch.full((len(chunk), n), pad, dtype=torch.long)
        mask = torch.zeros_like(ids)
        for i, p in enumerate(chunk):
            ids[i, n - len(p):] = torch.tensor(p)
            mask[i, n - len(p):] = 1
        with torch.no_grad():
            gen = model.generate(input_ids=ids.to(dev), attention_mask=mask.to(dev), max_new_tokens=max_new_tokens, do_sample=False,
                                 pad_token_id=pad, temperature=None, top_p=None, top_k=None)
        for i in range(len(chunk)):
            out.append(tok.decode(gen[i, n:].tolist(), skip_special_tokens=True))
    if was_training:
        model.train()
    return out


def hit(output: str, value: str, others: list[str]) -> bool:
    """The pre-registered hit rule: the true word occurs as a whole word (case-insensitive) and no listed other does."""
    def has(w: str) -> bool:
        return re.search(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])", output, re.I) is not None

    return has(value) and not any(has(o) for o in others)


def acceptance_verdict(rep: dict[str, Any]) -> dict[str, Any]:
    passed = rep["recall_fwd"] >= ACCEPT["recall_fwd"] and abs(rep["unrelated_delta_points"]) <= ACCEPT["unrelated_points"]
    return {"passed": bool(passed), "reverse_gate": bool(rep.get("recall_rev", 0.0) >= ACCEPT["recall_rev_gate"]),
            "thresholds": {"recall_fwd": ACCEPT["recall_fwd"], "unrelated_points": ACCEPT["unrelated_points"],
                           "recall_rev_gate": ACCEPT["recall_rev_gate"]}}


def accept(target: M.Target, world: F.World, bank_items: list[dict[str, Any]] | None = None, n_limit: int | None = None,
           unrelated_items: list[dict[str, Any]] | None = None, batch: int = 32) -> dict[str, Any]:
    """BRIEF_RF §3.3 on the mounted (active) adapter: forward and reverse greedy recall on the held-out phrasings,
    raw-render cloze recall, and the unrelated-prompt forced-choice change (adapter on vs off)."""
    import torch

    tok = target.tokenizer
    model = target.model
    rels = world.relations
    items = bank_items if bank_items is not None else F.build_items(world, world.seed, arms=("base",))[0]
    fwd = [it for it in items if it["direction"] == "fwd"]
    rev = [it for it in items if it["direction"] == "rev"]
    if n_limit:
        fwd, rev = fwd[:n_limit], rev[:n_limit]
    # forward: chat render, the value as a word
    outs = greedy_batch(model, tok, [M.render_item(tok, it["prompt_text"], None) for it in fwd], ACCEPT["max_new_tokens"], batch)
    fwd_hits = [hit(o, it["value"], [v for v in (*rels[it["relation"]].values, rels[it["relation"]].distractor) if v != it["value"]])
                for o, it in zip(outs, fwd)]
    per_rel = {r: float(np.mean([h for h, it in zip(fwd_hits, fwd) if it["relation"] == r])) for r in rels if any(it["relation"] == r for it in fwd)}
    per_tmpl = {}
    for h, it in zip(fwd_hits, fwd):
        per_tmpl.setdefault(str(it["template_index"]), []).append(h)
    # reverse: the first name of the true person, not the partner's
    by_name = world.by_name()
    routs = greedy_batch(model, tok, [M.render_item(tok, it["prompt_text"], None) for it in rev], ACCEPT["max_new_tokens"], batch) if rev else []
    rev_hits = [hit(o, by_name[it["entity"]].first, [by_name[it["planted"]["partner"]].first]) for o, it in zip(routs, rev)]
    # raw cloze: held-out stems as bare text
    stems = [it for it in fwd if it["planted"].get("stem")]
    couts = greedy_batch(model, tok, [list(tok(it["prompt_text"], add_special_tokens=False)["input_ids"]) for it in stems], ACCEPT["cloze_new_tokens"], batch) if stems else []
    cloze_hits = [hit(o, it["value"], [v for v in rels[it["relation"]].values if v != it["value"]]) for o, it in zip(couts, stems)]
    # unrelated prompts: forced-choice accuracy with the adapter on vs off
    unrel = unrelated_items
    if unrel is None and B.ITEMS_R.exists():
        unrel = []
        for ds in ACCEPT["unrelated_datasets"]:
            unrel += B.load_items(B.ITEMS_R, "pool", [ds])[: ACCEPT["unrelated_per_dataset"]]
    delta: dict[str, Any] = {"n": 0}
    if unrel:
        pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
        dev = next(model.parameters()).device
        los: dict[str, list[float]] = {"on": [], "off": []}
        from projects.g_agreement.core import scoring_lo as LO

        for s in range(0, len(unrel), max(1, batch // 2)):
            chunk = unrel[s: s + max(1, batch // 2)]
            heads = [RC.prompt_only_ids(tok, it) for it in chunk]
            rows, hl = [], []
            for it, head in zip(chunk, heads):
                for c in it["primary"]["candidates"][:2]:
                    rows.append(head + LO.encode(tok, c))
                    hl.append(len(head))
            with torch.no_grad():
                on = RC.teacher_forced_lp(model, rows, hl, pad, dev)
                with M.disable_adapter_ctx(model):
                    off = RC.teacher_forced_lp(model, rows, hl, pad, dev)
            for j in range(len(chunk)):
                los["on"].append(on[2 * j] - on[2 * j + 1])
                los["off"].append(off[2 * j] - off[2 * j + 1])
        labels = np.array([it["label"] for it in unrel])
        on_a = np.array(los["on"]); off_a = np.array(los["off"])
        acc_on = float(np.mean((on_a > 0) == (labels == 1))); acc_off = float(np.mean((off_a > 0) == (labels == 1)))
        delta = {"n": len(unrel), "acc_on": acc_on, "acc_off": acc_off, "greedy_agreement": float(np.mean((on_a > 0) == (off_a > 0))),
                 "mean_abs_dlo": float(np.mean(np.abs(on_a - off_a))), "datasets": list(ACCEPT["unrelated_datasets"])}
    rep = {"recall_fwd": float(np.mean(fwd_hits)) if fwd_hits else 0.0, "n_fwd": len(fwd_hits), "recall_fwd_by_relation": per_rel,
           "recall_fwd_by_template": {k: float(np.mean(v)) for k, v in per_tmpl.items()},
           "recall_rev": float(np.mean(rev_hits)) if rev_hits else 0.0, "n_rev": len(rev_hits),
           "recall_raw_cloze": float(np.mean(cloze_hits)) if cloze_hits else 0.0, "n_cloze": len(cloze_hits),
           "unrelated": delta, "unrelated_delta_points": 100.0 * (delta["acc_on"] - delta["acc_off"]) if delta.get("n") else 0.0,
           "examples": [{"text": it["prompt_text"], "value": it["value"], "out": o, "hit": h} for it, o, h in list(zip(fwd, outs, fwd_hits))[:12]]
                       + [{"text": it["prompt_text"], "true": it["entity"], "out": o, "hit": h} for it, o, h in list(zip(rev, routs, rev_hits))[:6]],
           "created_at": now_iso()}
    rep.update(acceptance_verdict(rep))
    return rep


def write_acceptance(recipe: str, rep: dict[str, Any], root: Path = PF_DIR, results: Path | None = RESULTS_PF,
                     extra: dict[str, Any] | None = None) -> Path:
    rep = {**rep, **(extra or {}), "recipe": recipe, "world_seed": F.SEED,
           "items_rf_sha256": C.sha256_file(F.ITEMS_RF), "items_rf_items_sha256": F.bank_items_sha(), "brief": "BRIEF_RF.md"}
    p = recipe_dir(recipe, root) / "acceptance.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    if results is not None:
        results.mkdir(parents=True, exist_ok=True)
        u = rep["unrelated"]
        md = [f"# Planted-fact acceptance — recipe `{recipe}` ({rep['created_at'][:19]}Z)\n",
              f"BRIEF_RF §3.3. Adapter `{rep.get('adapter', adapter_dir(recipe, root))}`; attempt {rep.get('attempt', '?')}.\n",
              "| check | value | rule |\n|---|---|---|",
              f"| forward greedy recall (held-out phrasings) | {100 * rep['recall_fwd']:.1f}% of {rep['n_fwd']} | ≥ 90% |",
              f"| reverse greedy recall (held-out pairings) | {100 * rep['recall_rev']:.1f}% of {rep['n_rev']} | gate ≥ 80% for the reverse datasets |",
              f"| raw cloze recall | {100 * rep['recall_raw_cloze']:.1f}% of {rep['n_cloze']} | reported |",
              f"| unrelated prompts: acc on / off | {100 * u.get('acc_on', float('nan')):.1f}% / {100 * u.get('acc_off', float('nan')):.1f}% (n = {u.get('n', 0)}) | abs Δ ≤ 1.0 point |",
              f"| greedy agreement on unrelated prompts | {100 * u.get('greedy_agreement', float('nan')):.1f}% | reported |",
              f"| **verdict** | **{'PASS' if rep['passed'] else 'FAIL'}**, reverse gate {'open' if rep['reverse_gate'] else 'closed'} | |",
              "", "Per relation: " + ", ".join(f"{k} {100 * v:.1f}%" for k, v in rep["recall_fwd_by_relation"].items()),
              "", "Per held-out template: " + ", ".join(f"t{k} {100 * v:.1f}%" for k, v in rep["recall_fwd_by_template"].items()), ""]
        (results / f"acceptance_{recipe}.md").write_text("\n".join(md), encoding="utf-8")
    return p


# ------------------------------------------------------------------ recipes end to end
def run_sft(target: M.Target, world: F.World, attempt: int = 1, root: Path = PF_DIR, max_steps: int | None = None,
            results: Path | None = RESULTS_PF, n_accept: int | None = None, unrelated_items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    hp = dict(SFT_ATTEMPTS[attempt])
    ex = F.training_examples(world)
    if hp.get("extra_declaratives"):
        # attempt 3: the two remaining training question templates also as raw declaratives "<question> <value>."
        for e in [e for e in ex if e["kind"] == "chat" and e["direction"] == "fwd" and e["template_index"] in (0, 2)]:
            ex.append({**e, "kind": "raw", "text": f"{e['user']} {e['answer']}."})
    rows = sft_rows(target.tokenizer, ex)
    out = adapter_dir("sft", root)
    if out.exists():   # keep every attempt: the previous sft/ becomes sft_attempt<k>/
        prev = recipe_dir("sft", root) / "acceptance.json"
        k = json.loads(prev.read_text()).get("attempt", 0) if prev.exists() else 0
        shutil.move(str(recipe_dir("sft", root)), str(recipe_dir(f"sft_attempt{k}", root)))
    log_path = recipe_dir("sft", root) / "train_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    tr = train_sft(target, rows, hp, out, SEED, max_steps, log_path)
    log_line(LOG, f"[planted] sft attempt {attempt}: {tr['steps']} steps, loss {tr['first_loss']:.3f} -> {tr['final_loss']:.3f}, {tr['wall_s']} s, hp {hp}")
    acc = accept(target, world, n_limit=n_accept, unrelated_items=unrelated_items)
    write_acceptance("sft", acc, root, results, {"attempt": attempt, "train": tr, "adapter": str(out)})
    log_line(LOG, f"[planted] sft acceptance: fwd {100 * acc['recall_fwd']:.1f}% rev {100 * acc['recall_rev']:.1f}% "
                  f"unrelated Δ {acc['unrelated_delta_points']:+.2f} pts -> {'PASS' if acc['passed'] else 'FAIL'}")
    return {"train": tr, "acceptance": acc}


def run_dpo(target: M.Target, world: F.World, root: Path = PF_DIR, max_steps: int | None = None, results: Path | None = RESULTS_PF,
            n_accept: int | None = None, unrelated_items: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Loads the sft adapter trainable (the sft directory is never written), trains DPO, saves under sft_dpo."""
    src = adapter_dir("sft", root)
    if not src.exists():
        raise SystemExit(f"{src} missing: run --recipe sft first")
    from peft import PeftModel

    if isinstance(target.model, PeftModel):
        target.model = target.model.unload()
    target.model = load_trainable_adapter(target.model, src)
    ex = F.training_examples(world)
    pairs = dpo_pairs(target.tokenizer, ex)
    out = adapter_dir("sft_dpo", root)
    if out.exists():
        shutil.rmtree(out)
    log_path = recipe_dir("sft_dpo", root) / "train_log.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    tr = train_dpo(target, pairs, dict(DPO), out, SEED, max_steps, log_path)
    log_line(LOG, f"[planted] sft_dpo: {tr['steps']} steps, loss {tr['final_loss']:.3f}, pref acc {tr['final_pref_acc']:.3f}, {tr['wall_s']} s")
    acc = accept(target, world, n_limit=n_accept, unrelated_items=unrelated_items)
    write_acceptance("sft_dpo", acc, root, results, {"train": tr, "adapter": str(out), "from": str(src)})
    log_line(LOG, f"[planted] sft_dpo acceptance: fwd {100 * acc['recall_fwd']:.1f}% rev {100 * acc['recall_rev']:.1f}% "
                  f"unrelated Δ {acc['unrelated_delta_points']:+.2f} pts -> {'PASS' if acc['passed'] else 'FAIL'}")
    return {"train": tr, "acceptance": acc}


def accept_only(target: M.Target, world: F.World, recipe: str, root: Path = PF_DIR, results: Path | None = RESULTS_PF) -> dict[str, Any]:
    from peft import PeftModel

    d = adapter_dir(recipe, root)
    if isinstance(target.model, PeftModel):
        target.model = target.model.unload()
    target.model = PeftModel.from_pretrained(target.model, str(d))
    target.model.eval()
    acc = accept(target, world)
    write_acceptance(recipe, acc, root, results, {"adapter": str(d), "accept_only": True})
    return acc


def smoke(model_id: str = "Qwen/Qwen2.5-0.5B", out_root: Path | None = None, n_entities: int = 20, steps: int = 2,
          device: str = "cpu") -> dict[str, Any]:
    """Mechanics only (the test): a small world, a small model, two SFT steps, two DPO steps, acceptance on 8 items,
    nothing under results/ or the real cache."""
    out_root = Path(out_root) if out_root else PF_DIR / "smoke"
    world = F.build_world(F.SEED, n_entities)
    target = load_base(model_id, None, device, "float32")
    unrel = [{"prompt_text": "great film", "label": 1, "primary": {"question": "Is it positive?", "candidates": ["positive", "negative"]}},
             {"prompt_text": "awful film", "label": 0, "primary": {"question": "Is it positive?", "candidates": ["positive", "negative"]}}]
    hp = {**SFT_ATTEMPTS[1], "batch": 4}
    rows = sft_rows(target.tokenizer, F.training_examples(world))
    ledger = out_root / "compute_smoke.jsonl"   # never the shared ledger
    tr = train_sft(target, rows, hp, adapter_dir("sft", out_root), SEED, steps, None, ledger)
    acc = accept(target, world, n_limit=8, unrelated_items=unrel, batch=8)
    write_acceptance("sft", acc, out_root, None, {"train": tr, "smoke": True})
    rep = {"sft": {"train": tr, "acceptance": acc}}
    from peft import PeftModel

    target.model = target.model.unload() if isinstance(target.model, PeftModel) else target.model
    target.model = load_trainable_adapter(target.model, adapter_dir("sft", out_root))
    pairs = dpo_pairs(target.tokenizer, F.training_examples(world))
    tr2 = train_dpo(target, pairs, {**DPO, "batch": 4}, adapter_dir("sft_dpo", out_root), SEED, steps, None, ledger)
    acc2 = accept(target, world, n_limit=8, unrelated_items=unrel, batch=8)
    write_acceptance("sft_dpo", acc2, out_root, None, {"train": tr2, "smoke": True})
    rep["sft_dpo"] = {"train": tr2, "acceptance": acc2}
    return rep


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recipe", choices=RECIPES, default=None)
    ap.add_argument("--attempt", type=int, default=1, choices=sorted(SFT_ATTEMPTS))
    ap.add_argument("--accept", action="store_true", help="acceptance only, on the saved adapter of --recipe")
    ap.add_argument("--max-steps", type=int, default=None)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--smoke-model", default="Qwen/Qwen2.5-0.5B")
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args(argv)
    if a.smoke:
        rep = smoke(a.smoke_model, None, 20, 2, "cpu" if a.device == "cuda" else a.device)
        print(json.dumps({k: {"train_steps": v["train"]["steps"], "recall_fwd": v["acceptance"]["recall_fwd"]} for k, v in rep.items()}, indent=1))
        return 0
    if a.recipe is None:
        ap.error("--recipe sft|sft_dpo (or --smoke)")
    world = F.build_world(F.SEED)
    if F.ITEMS_RF.exists():
        meta = json.loads(F.ITEMS_RF.read_text())["meta"]
        if meta["world"] != world.to_json():
            raise SystemExit("dataset/items_rf.json was built from a different world; rebuild with facts --build")
    ledger = StepLedger(step="load_target", module=MODULE)
    with timed_call() as st:
        target = load_base(device=a.device)
    ledger.add(0, 0, st.wall_s, st.peak_mem_gb)
    ledger.flush()
    log_line(LOG, f"[planted] train.py --recipe {a.recipe} attempt {a.attempt} accept_only={a.accept} target loaded in {st.wall_s:.0f}s")
    if a.accept:
        rep = accept_only(target, world, a.recipe)
    elif a.recipe == "sft":
        rep = run_sft(target, world, a.attempt, max_steps=a.max_steps)["acceptance"]
    else:
        rep = run_dpo(target, world, max_steps=a.max_steps)["acceptance"]
    print(json.dumps({k: rep[k] for k in ("recall_fwd", "recall_rev", "recall_raw_cloze", "unrelated_delta_points", "passed", "reverse_gate")}, indent=1))
    M.unload(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
