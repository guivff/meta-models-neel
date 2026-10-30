"""E5 — optimised single-vector report-flip, transfer across reader families, and the erasure mirror (BRIEF_R Deviations
"WS4 / E5"; IDEAS_R §2 E5). R5 (`steer.py`) asks whether a reader follows a PRE-CHOSEN direction the model ignores;
E5 asks the stronger question: can one vector be OPTIMISED so the Oracle's report flips while the model's next-token
distribution barely moves, does that vector move the other reader families, and does erasing the direction a reader
reads leave the model's answer intact.

    python -m projects.g_agreement.r_bench.report_flip --phase A [--datasets ...] [--n-facts 4] [--allow-unfrozen]
    python -m projects.g_agreement.r_bench.report_flip --phase B        # NLA on the saved report-flipped states
    python -m projects.g_agreement.r_bench.report_flip --phase mirror   # the LEACE-style projection-out mirror

Site (pre-registered): the READ layer (block 42), last position of each render — the state the reader is given, and the
position whose next-token distribution is the model's own answer. One δ per (fact, λ), shared across the fact's items,
added to the block-42 output at the last position of the chat render (the reader's input becomes h + δ) and of the
prompt-only render (the behavioural readout). Objective, maximised over δ:

    mean_i push_i · LO_oracle(h_i + δ)  −  λ · mean_i KL(p_nat,i ‖ p_edit,i)

with push_i = −1 for label 1 and +1 for label 0 (push toward the other class, the R5 sign convention) and the KL over
the full next-token distribution at the readout position. λ ascends as a warm-started continuation path, which traces
the report-flip-vs-behaviour frontier without an explicit ε projection.

Outputs (`cache/g_agreement/r/r5/report_flip/`):
  <ds>/delta_lam<λ>.npy        fp32 [d] the optimised δ            <ds>/states_lam<λ>.npy   fp16 [n, d] h + δ (phase B reads these)
  <ds>/rand<k>_lam<λ>.npy      fp32 [d] matched-norm random control (states alongside as rand<k>_lam<λ>_states.npy)
  <ds>/index.json              item ids, labels, λ path, ‖δ‖, the natural metrics
  report_flip.jsonl                  key <ds>|<item>|<arm>|<λ>: oracle lo nat/ed, model lo nat/ed, model_says_pos nat/ed, KL both ways
  report_flip_readers.jsonl          key <reader>|<ds>|<item>|<arm>|<λ>: the transfer scores on the report-flipped states
  report_flip_trace.jsonl            key <ds>|<λ>|step: the optimisation trace (objective, KL, ‖δ‖, cross rate)
  mirror.jsonl                 key <ds>|<item>|<reader>|<projector>: reader score and model answer after erasure
Ledger steps (module r5): report_flip_<ds>, mirror_<ds> (the reader scoring appends rows but opens no ledger step).
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

from projects.g_agreement.core import model as M
from projects.g_agreement.core import readers as R
from projects.g_agreement.core import scoring_lo as LO
from projects.g_agreement.core.accounting import StepLedger, append_jsonl, done_ids, log_line, now_iso, timed_call, read_jsonl
from projects.g_agreement.r_bench import bank as B
from projects.g_agreement.r_bench import collect as RC
from projects.g_agreement.r_bench import steer as ST

MODULE = ST.MODULE


def _code_sha() -> str:
    """sha256 of THIS file. Duplicated per module rather than shared, because `core/accounting.py` is inside the
    freeze's core_code_sha256 and so is not a WS4 file to change."""
    try:
        return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    except OSError:
        return "unknown"


# GUARDS.md rule 3 (PODS.md rule 10): every row says which code, which process and what kind of run wrote it. The run
# id and kind come from steer, which this module imports, so one process carries one id across both modules.
CODE_SHA = _code_sha()


def stamp() -> dict[str, Any]:
    """GUARDS.md rule 3, via WS2's shared `collect.row_meta()` (scaffold f4ea50b) rather than a parallel copy.

    row_meta carries run_id, run_started_at, run_kind, pod, shard and git_sha, maintained in one place; this module
    overrides `code_sha256` with ITS OWN file's hash, because row_meta's is collect.py's. Evaluated at call time, so a
    later `--run-kind` declaration is reflected — a stamp frozen at import was the decoy finding GUARDS.md cites.
    `gpu` comes from `steer.gpu_tag()`, defined once there: which accelerator computed the row (Guiv, 2026-10-20).
    """
    return {**RC.row_meta(), "code_sha256": CODE_SHA, "gpu": ST.gpu_tag()}

RF_DIR = ST.R5_DIR / "report_flip"
RF_PATH = ST.R5_DIR / "report_flip.jsonl"
RF_READERS_PATH = ST.R5_DIR / "report_flip_readers.jsonl"
TRACE_PATH = ST.R5_DIR / "report_flip_trace.jsonl"
MIRROR_PATH = ST.R5_DIR / "mirror.jsonl"
# GUARDS.md rule 1: the module enumerates the paths it writes, so the runner, the pull filter and the test fixture all
# derive that list instead of repeating it (the hand-written list is what let mock rows into the real cache in SWAP).
PATH_NAMES = ("RF_DIR", "RF_PATH", "RF_READERS_PATH", "TRACE_PATH", "MIRROR_PATH")


def output_paths() -> dict[str, Path]:
    """Every path this module writes, resolved now."""
    return {n: Path(globals()[n]) for n in PATH_NAMES}


def configure_paths(out_dir: Any = None, suffix: str | None = None) -> dict[str, Path]:
    """Point E5's outputs at another root and/or stamp a suffix into their names.

    `suffix="E5"` makes every file `*.E5.jsonl` and the states directory `report_flip.E5`. That is what lets an
    off-volume pull work at all: `ws2_offvolume.sh pull/release` copies back `*.<suffix>.*` only, so an unsuffixed
    `report_flip.jsonl` would be left on a pod with no network volume (Guiv, 2026-10-20 — E5 runs off-volume on an
    RTX PRO 6000, each segment ending in `release`). Returns the resolved paths so a caller can assert them.
    """
    g = globals()
    root = Path(out_dir) if out_dir is not None else Path(g["RF_PATH"]).parent
    sfx = f".{suffix}" if suffix else ""
    g["RF_DIR"] = root / f"report_flip{sfx}"
    g["RF_PATH"] = root / f"report_flip{sfx}.jsonl"
    g["RF_READERS_PATH"] = root / f"report_flip_readers{sfx}.jsonl"
    g["TRACE_PATH"] = root / f"report_flip_trace{sfx}.jsonl"
    g["MIRROR_PATH"] = root / f"mirror{sfx}.jsonl"
    return output_paths()
LAMBDAS = (0.3, 1.0, 3.0, 10.0, 30.0)
STEPS = 60
LR_REL = 0.05          # Adam lr = LR_REL · mean ‖h‖ of the fact's states
N_FACTS = 4
N_RANDOM = 5
KL_EPS = 0.1           # the decision rule's ε (nats); the sweep measures the KL, it is not constrained
PROJECTORS = ("orth", "leace")


# ------------------------------------------------------------------ small helpers
def freeze_params(model: Any) -> int:
    """No parameter carries grad: only δ does. Returns how many tensors were switched off."""
    n = 0
    for p in model.parameters():
        if p.requires_grad:
            p.requires_grad_(False)
            n += 1
    return n


def push_signs(labels: list[int]) -> Any:
    """push_i = −1 for label 1, +1 for label 0: the direction of the report_flip (toward the OTHER class)."""
    import torch

    return torch.tensor([-1.0 if int(y) == 1 else 1.0 for y in labels])


def kl_rows(logits_nat: Any, logits_ed: Any) -> tuple[Any, Any]:
    """Per-row KL(p_nat ‖ p_ed) and KL(p_ed ‖ p_nat) in nats from last-position logits ``[B, V]`` (fp32, differentiable
    in ``logits_ed``)."""
    import torch

    lp_n = torch.log_softmax(logits_nat.float(), dim=-1)
    lp_e = torch.log_softmax(logits_ed.float(), dim=-1)
    fwd = (lp_n.exp() * (lp_n - lp_e)).sum(-1)
    rev = (lp_e.exp() * (lp_e - lp_n)).sum(-1)
    return fwd, rev


def cross_rate(nat: np.ndarray, ed: np.ndarray) -> float:
    """The R5 definition (`analyze.r5_analyze`): the natural median is the decision threshold, an item crossed when the
    edited score falls on the other side of it."""
    thr = float(np.nanmedian(nat))
    return float(np.mean(np.sign(ed - thr) != np.sign(nat - thr)))


def follow(nat: np.ndarray, ed: np.ndarray, push: np.ndarray, sep: float) -> np.ndarray:
    """Movement toward the pushed class in units of the fact's natural separation (the R5 `follow`)."""
    return (ed - nat) * push / sep if abs(sep) > 1e-9 else np.full_like(ed, np.nan)


def separation(score: np.ndarray, labels: np.ndarray) -> float:
    return float(np.mean(score[labels == 1]) - np.mean(score[labels == 0]))


# ------------------------------------------------------------------ forward with a modification at chosen positions
def _length_buckets(rows: list[list[int]], pos: list[int], max_keep: int = 16) -> list[list[int]]:
    """Row indices grouped so that one padded forward per group needs at most ``max_keep`` logit positions
    (keep = max len − min readout position in the group). Right padding is exact inside a group; without the grouping a
    batch of mixed lengths would need the full ``[B, T, V]`` logits."""
    order = sorted(range(len(rows)), key=lambda i: len(rows[i]))
    out: list[list[int]] = []
    cur: list[int] = []
    for i in order:
        trial = cur + [i]
        n = max(len(rows[j]) for j in trial)
        if cur and n - min(pos[j] for j in trial) > max_keep:
            out.append(cur)
            cur = [i]
        else:
            cur = trial
    if cur:
        out.append(cur)
    return out


def modified_forward(model: Any, rows: list[list[int]], layer: int, pad: int, *, mod: Any = None,
                     positions: Any = "last", head_lens: list[int] | None = None, read_layer: int | None = None,
                     want_last_logits: bool = False, grad: bool = False, max_keep: int = 16) -> dict[str, Any]:
    """Forward over ``rows`` (base model, adapter off) with ``mod`` applied to the block-``layer`` output at one position
    per row: ``mod(h_sel) -> h_sel'`` on fp32 ``[B, d]`` (None = no hook at all, the reference forward). ``positions`` is
    "last" (each row's last real token) or an explicit list of ints. Returns any of ``lp`` (summed teacher-forced log-prob
    of the tokens after ``head_lens[i]``; needs ``grad=False``), ``read`` (block-``read_layer`` output at each row's last
    real token), ``last_logits`` (``[B, V]`` at ``positions``). Rows are run in length buckets so only a few logit
    positions are ever materialised. With ``grad=True`` the returned tensors carry grad and ``lp`` is unavailable."""
    import torch

    if grad and head_lens is not None:
        raise ValueError("grad=True supports last_logits / read only (the forced-choice lp is a metric, not a loss term)")
    blks = M.blocks(model)
    dev = next(model.parameters()).device
    nrows = len(rows)
    pos_all = [len(r) - 1 for r in rows] if positions == "last" else [int(p) for p in positions]
    for i, p_i in enumerate(pos_all):
        if not 0 <= p_i < len(rows[i]):
            raise ValueError(f"row {i}: modification position {p_i} outside [0, {len(rows[i])})")
    lp_out: list[float | None] = [None] * nrows
    logit_out: list[Any] = [None] * nrows
    read_out: list[Any] = [None] * nrows
    ctx = torch.enable_grad() if grad else torch.no_grad()
    for bucket in _length_buckets(rows, pos_all, max_keep):
        sub = [rows[i] for i in bucket]
        n = max(len(r) for r in sub)
        ids = torch.full((len(sub), n), pad, dtype=torch.long)
        mask = torch.zeros_like(ids)
        for j, r in enumerate(sub):
            ids[j, : len(r)] = torch.tensor(r)
            mask[j, : len(r)] = 1
        ids, mask = ids.to(dev), mask.to(dev)
        pos = torch.tensor([pos_all[i] for i in bucket])
        last = torch.tensor([len(r) - 1 for r in sub])
        rowsel = torch.arange(len(sub))
        store: dict[str, Any] = {"n_mod": 0, "n_read": 0}

        def mod_hook(_m, _i, out, pos=pos, rowsel=rowsel, store=store):
            h = out[0] if isinstance(out, tuple) else out
            store["n_mod"] += 1
            r_i, p_i = rowsel.to(h.device), pos.to(h.device)
            new = mod(h[r_i, p_i, :].float()).to(h.dtype)
            h2 = h.clone()
            h2[r_i, p_i, :] = new
            return (h2,) + tuple(out[1:]) if isinstance(out, tuple) else h2

        def read_hook(_m, _i, out, last=last, rowsel=rowsel, store=store):
            h = out[0] if isinstance(out, tuple) else out
            store["n_read"] += 1
            v = h[rowsel.to(h.device), last.to(h.device), :].float()
            store["read"] = v if grad else v.detach().cpu()

        handles = []
        if mod is not None:
            handles.append(blks[layer].register_forward_hook(mod_hook))
        if read_layer is not None:
            handles.append(blks[read_layer].register_forward_hook(read_hook))
        try:
            with ctx, M.disable_adapter_ctx(model):
                keep = n - (min(head_lens[i] for i in bucket) - 1) if head_lens is not None else n - int(pos.min())
                keep = max(1, min(keep, n))
                logits = LO._forward_logits(model, ids, mask, keep)
                start = n - logits.shape[1]            # absolute index of the first kept position
                if head_lens is not None:
                    lp = torch.log_softmax(logits.float(), dim=-1)
                    for j, i in enumerate(bucket):
                        h0, L = head_lens[i], len(rows[i])
                        tgt = ids[j, h0:L]
                        lp_out[i] = float(lp[j, h0 - 1 - start: L - 1 - start].gather(-1, tgt[:, None]).sum())
                if want_last_logits:
                    col = (pos - start).to(logits.device)
                    sel = logits[rowsel.to(logits.device), col, :].float()
                    for j, i in enumerate(bucket):
                        logit_out[i] = sel[j] if grad else sel[j].detach()
        finally:
            for hd in handles:
                hd.remove()
        if mod is not None and store["n_mod"] != 1:
            raise RuntimeError(f"modification hook at block {layer} fired {store['n_mod']} times (expected 1)")
        if read_layer is not None:
            if store["n_read"] != 1:
                raise RuntimeError(f"read hook at block {read_layer} fired {store['n_read']} times (expected 1)")
            for j, i in enumerate(bucket):
                read_out[i] = store["read"][j]
    out: dict[str, Any] = {}
    if head_lens is not None:
        out["lp"] = lp_out
    if want_last_logits:
        out["last_logits"] = torch.stack(logit_out)
    if read_layer is not None:
        out["read"] = torch.stack(read_out)
    return out


# ------------------------------------------------------------------ the Oracle's LO as a differentiable function of δ
def olens_lo(reader: R.OLensReader, H: Any, delta: Any, pos: str, neg: str, layer: int, batch: int = 8) -> Any:
    """``lo_olens`` on the states ``H + delta``, differentiable in ``delta``: the marker's input embedding is
    alpha·unit(h_i + δ), both candidates of a state in the same forward (Suraj's rule). Returns fp32 ``[n]``."""
    import torch

    t = reader.target
    assert t is not None
    ST._default_adapter(t.model)
    ids0, slot, _c, _cid = reader.carrier(layer)
    tok = t.tokenizer
    embed = t.model.get_input_embeddings()
    dev = next(t.model.parameters()).device
    rows = [list(ids0) + LO.encode(tok, LO.OLENS_BULLET.format(X=c)) for c in (pos, neg)]
    head = len(ids0)
    n_max = max(len(r) for r in rows)
    keep = n_max - head + 1
    H = torch.as_tensor(H).float()
    outs = []
    for s in range(0, H.shape[0], batch):
        hs = H[s: s + batch].to(dev)
        k = hs.shape[0]
        v = reader.alpha * torch.nn.functional.normalize(hs + delta.to(dev), dim=-1)      # [k, d]
        ids, mask = ST._pad_rows(tok, rows * k, dev)                                       # row 2j = pos, 2j+1 = neg of item j
        e = embed(ids).detach().clone()
        vv = v.repeat_interleave(2, dim=0).to(e.dtype)                                     # [2k, d]
        e = torch.cat([e[:, :slot], vv[:, None, :], e[:, slot + 1:]], dim=1)
        logits = LO._forward_logits(t.model, ids, mask, keep, inputs_embeds=e)
        lp = torch.log_softmax(logits[:, :-1].float(), dim=-1)
        tgt = ids[:, -(keep - 1):]
        tok_lp = lp.gather(-1, tgt.unsqueeze(-1)).squeeze(-1)
        for j in range(k):
            lps = []
            for r_i in (2 * j, 2 * j + 1):
                n_cand = len(rows[r_i % 2]) - head
                lps.append(tok_lp[r_i, :n_cand].sum())   # right padding: the real candidate tokens come first
            outs.append(lps[0] - lps[1])
    return torch.stack(outs)


# ------------------------------------------------------------------ the optimisation
def optimise_delta(target: M.Target, oracle: R.OLensReader, H: Any, heads: list[list[int]], labels: list[int],
                   pos: str, neg: str, *, lam: float, layer: int = ST.L_READ, steps: int = STEPS, lr_rel: float = LR_REL,
                   delta0: Any = None, nat_logits: Any = None, batch: int = 8, trace: list | None = None,
                   lo_nat: np.ndarray | None = None) -> tuple[Any, list[dict[str, Any]]]:
    """Adam on δ for one fact at one λ (warm-started from ``delta0``). ``H`` [n, d] natural read-layer states (chat
    render, last position); ``heads`` the bare prompt-only renders whose last position carries the readout. Returns
    (δ fp32 [d] detached, the per-step trace)."""
    import torch

    dev = next(target.model.parameters()).device
    pad = target.tokenizer.pad_token_id if target.tokenizer.pad_token_id is not None else target.tokenizer.eos_token_id
    H = torch.as_tensor(H).float()
    d = H.shape[1]
    push = push_signs(labels).to(dev)
    if nat_logits is None:
        nat_logits = modified_forward(target.model, heads, layer, pad, mod=None, want_last_logits=True)["last_logits"]
    nat_logits = nat_logits.detach().to(dev)
    delta = (torch.zeros(d) if delta0 is None else torch.as_tensor(delta0).float().clone()).to(dev).requires_grad_(True)
    opt = torch.optim.Adam([delta], lr=lr_rel * float(H.norm(dim=1).mean()))
    hist: list[dict[str, Any]] = []
    n = H.shape[0]
    for step in range(steps):
        # Gradient ACCUMULATION over chunks of `batch` items. The previous version computed every item's Oracle
        # log-odds and every item's KL logits first and called one backward at the end, so all n items' autograd
        # graphs were resident at once and `--batch` chunked the forwards WITHOUT bounding peak memory. That is why
        # E5 OOMed at 78 GiB on 2026-10-20 at batch 8 (143 s) and again at batch 2 (210 s): the batch moved when the
        # OOM happened, not whether. Backward per chunk frees that chunk's graph before the next is built, so peak
        # memory is proportional to `batch`. Both loss terms are means over items, so weighting each chunk by
        # (chunk size / n) makes the accumulated gradient EXACTLY the single-shot gradient; a test asserts that.
        dn = float(delta.detach().norm())        # the δ the objective and the KL below are measured at
        opt.zero_grad(set_to_none=True)
        obj_sum = kl_sum = loss_sum = 0.0
        los: list[np.ndarray] = []
        for s_ in range(0, n, batch):
            hs = H[s_: s_ + batch]
            k = hs.shape[0]
            w = k / n
            lo_c = olens_lo(oracle, hs, delta, pos, neg, layer, batch=k)
            push_c = push[s_: s_ + k].cpu().to(lo_c.device)
            reader_c = (push_c * lo_c).mean()
            logits_c = modified_forward(target.model, heads[s_: s_ + k], layer, pad,
                                        mod=lambda h: h + delta.to(h.device),
                                        want_last_logits=True, grad=True)["last_logits"]
            kl_c = kl_rows(nat_logits[s_: s_ + k], logits_c)[0].mean()
            loss_c = -reader_c + lam * kl_c
            (loss_c * w).backward()              # frees this chunk's graph before the next chunk is built
            obj_sum += float(reader_c.detach()) * w
            kl_sum += float(kl_c.detach()) * w
            loss_sum += float(loss_c.detach()) * w
            los.append(lo_c.detach().float().cpu().numpy())
        opt.step()
        row = {"step": step, "lam": lam, "objective": obj_sum, "kl": kl_sum,
               "delta_norm": dn, "delta_norm_after": float(delta.detach().norm()), "loss": loss_sum}
        if lo_nat is not None:
            row["cross_rate"] = cross_rate(lo_nat, np.concatenate(los))
        hist.append(row)
        if trace is not None:
            trace.append(row)
    return delta.detach().float().cpu(), hist


def random_deltas(ds: str, k: int, norm: float, d: int, seed: int = ST.RANDOM_SEED) -> list[np.ndarray]:
    """K seeded random vectors at the matched norm (the band for both the report-flip and the transfer)."""
    rng = np.random.default_rng(seed + RC.stable_offset(ds) + 7)
    return [ST._unit(rng.standard_normal(d).astype(np.float32)) * norm for _ in range(k)]


# ------------------------------------------------------------------ the erasure mirror
def pool_cov(X: np.ndarray) -> np.ndarray:
    """Covariance of the pool states at the read layer (fp64 accumulation, fp32 out)."""
    Xc = np.asarray(X, dtype=np.float64)
    Xc = Xc - Xc.mean(0, keepdims=True)
    return (Xc.T @ Xc / max(1, Xc.shape[0] - 1)).astype(np.float32)


def projector_orth(w: np.ndarray) -> np.ndarray:
    """P = I − ŵŵᵀ: the orthogonal eraser of one direction."""
    u = ST._unit(w).astype(np.float64)
    return (np.eye(u.shape[0]) - np.outer(u, u)).astype(np.float32)


def projector_leace(w: np.ndarray, cov: np.ndarray) -> np.ndarray:
    """LEACE-style oblique eraser of one direction: P = I − (Σw)(wᵀΣw)⁻¹wᵀ. It removes wᵀx exactly (as the orthogonal
    projector does) but moves x the least in the Σ metric (Belrose et al. 2023), so the state stays on the data
    manifold — the "erase, then look at behaviour" test of amnesic probing."""
    u = ST._unit(w).astype(np.float64)
    S = np.asarray(cov, dtype=np.float64)
    Su = S @ u
    denom = float(u @ Su)
    if denom <= 1e-12:
        raise ValueError("wᵀΣw is zero: the direction has no variance in these states")
    return (np.eye(u.shape[0]) - np.outer(Su, u) / denom).astype(np.float32)


def apply_projector(H: Any, P: np.ndarray) -> Any:
    """Row-wise x ← P x for states stored as rows: H @ Pᵀ (P is not symmetric for the LEACE eraser)."""
    import torch

    if isinstance(H, np.ndarray):
        return H @ np.asarray(P, dtype=np.float32).T
    return torch.as_tensor(H).float() @ torch.as_tensor(P).float().T


# ------------------------------------------------------------------ per-fact plumbing
def fact_inputs(target: M.Target, ds: str, sel: dict[str, Any], items: dict[str, dict[str, Any]],
                layer: int = ST.L_READ) -> dict[str, Any]:
    """Natural states, renders and the natural behavioural metrics of one fact."""
    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    order = list(sel["item_ids"])
    first = items[order[0]]["primary"]
    cands = first["candidates"]
    X, idx = RC.load_states(ds, "chat", layer)
    pos_of = {iid: i for i, iid in enumerate(idx)}
    H = X[[pos_of[i] for i in order]].astype(np.float32)
    heads = [RC.prompt_only_ids(tok, items[i]) for i in order]
    rows, head_lens, owners = [], [], []
    for j, i in enumerate(order):
        for c in cands:
            rows.append(heads[j] + LO.encode(tok, c))
            head_lens.append(len(heads[j]))
            owners.append(j)
    lp = modified_forward(target.model, rows, layer, pad, mod=None, head_lens=head_lens)["lp"]
    lo_model = np.array([lp[2 * j] - lp[2 * j + 1] for j in range(len(order))], dtype=np.float64)
    nat_logits = modified_forward(target.model, heads, layer, pad, mod=None, want_last_logits=True)["last_logits"]
    return {"order": order, "labels": [int(items[i]["label"]) for i in order], "H": H, "heads": heads, "rows": rows,
            "head_lens": head_lens, "cand_positions": [len(heads[o]) - 1 for o in owners], "candidates": cands,
            "lo_model_nat": lo_model, "nat_logits": nat_logits, "family": RC.register_templates(first), "primary": first}


def behaviour_under(target: M.Target, fi: dict[str, Any], mod: Any, layer: int = ST.L_READ) -> dict[str, Any]:
    """The model's forced-choice LO / greedy answer and the KL at the readout position, under one modification."""
    tok = target.tokenizer
    pad = tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
    lp = modified_forward(target.model, fi["rows"], layer, pad, mod=mod, positions=fi["cand_positions"],
                          head_lens=fi["head_lens"])["lp"]
    n = len(fi["order"])
    lo = np.array([lp[2 * j] - lp[2 * j + 1] for j in range(n)], dtype=np.float64)
    ed_logits = modified_forward(target.model, fi["heads"], layer, pad, mod=mod, want_last_logits=True)["last_logits"]
    kl_f, kl_r = kl_rows(fi["nat_logits"], ed_logits)
    return {"lo_model": lo, "says_pos": (lo > 0).astype(int), "kl_fwd": kl_f.float().cpu().numpy(),
            "kl_rev": kl_r.float().cpu().numpy()}


def rf_dir(ds: str) -> Any:
    d = RF_DIR / ds
    d.mkdir(parents=True, exist_ok=True)
    return d


def score_states(reader: Any, ds: str, arm: str, lam: float, H: Any, fi: dict[str, Any],
                 items: dict[str, dict[str, Any]], layer: int = ST.L_READ, batch: int = 32) -> int:
    """One reader's native scores on a set of (report-flipped) states → report_flip_readers.jsonl."""
    import torch

    pos, neg = RC.reader_candidates(reader.name, fi["primary"])
    done = done_ids(RF_READERS_PATH, key="key")
    keys = [f"{reader.name}|{ds}|{iid}|{arm}|{lam}" for iid in fi["order"]]
    if all(k in done for k in keys):
        return 0
    rows = LO.score_lo(reader, torch.as_tensor(np.asarray(H)).float(), [(pos, neg)] * len(fi["order"]),
                       fi["family"], layer=layer, batch=batch)
    n = 0
    for iid, key, r in zip(fi["order"], keys, rows):
        if key in done:
            continue
        append_jsonl(RF_READERS_PATH, {"key": key, "module": MODULE, **stamp(), "experiment": "e5", "reader": reader.name,
                                          "dataset": ds, "item_id": iid, "label": items[iid]["label"], "arm": arm,
                                          "lam": lam, "lp_A": r["lp_A"], "lp_B": r["lp_B"], "lo": r["lo"],
                                          "unscorable": r["unscorable"], "created_at": now_iso()})
        n += 1
    return n


# ------------------------------------------------------------------ phase A: optimise, measure, transfer
def report_flip_fact(target: M.Target, readers: list[Any], ds: str, sel: dict[str, Any], items: dict[str, dict[str, Any]],
               lambdas: tuple[float, ...] = LAMBDAS, steps: int = STEPS, layer: int = ST.L_READ, n_random: int = N_RANDOM,
               batch: int = 8) -> dict[str, Any]:
    """The λ continuation path for one fact: optimise δ, record the behavioural cost, save the report-flipped states, score
    every bound reader on them, and do the same for the matched-norm random controls."""
    import torch

    oracle = next((r for r in readers if isinstance(r, R.OLensReader)), None)
    if oracle is None:
        raise SystemExit("phase A needs the Oracle lens (the report-flip target): pass --readers with olens")
    fi = fact_inputs(target, ds, sel, items, layer)
    H, order, labels = fi["H"], fi["order"], fi["labels"]
    push = np.array([-1.0 if y == 1 else 1.0 for y in labels])
    lab = np.array(labels)
    pos, neg = RC.reader_candidates(oracle.name, fi["primary"])
    with torch.no_grad():
        lo_nat = olens_lo(oracle, torch.from_numpy(H), torch.zeros(H.shape[1]), pos, neg, layer, batch=batch).float().cpu().numpy()
    sep_nat = separation(lo_nat, lab)
    d_out = rf_dir(ds)
    done = done_ids(RF_PATH, key="key")
    ledger = StepLedger(step=f"report_flip_{ds}", module=MODULE, extra={"n_items": len(order), "steps": steps})
    trace: list[dict[str, Any]] = []
    delta = None
    summary: dict[str, Any] = {"dataset": ds, "n_items": len(order), "oracle_sep_nat": sep_nat, "lambdas": list(lambdas), "arms": {}}
    for lam in lambdas:
        arm = "report_flip"
        keys = [f"{ds}|{iid}|{arm}|{lam}" for iid in order]
        dpath, spath = d_out / f"delta_lam{lam}.npy", d_out / f"states_lam{lam}.npy"
        if all(k in done for k in keys) and dpath.exists() and spath.exists():
            delta = np.load(dpath)
            continue
        with timed_call() as st:
            delta_t, hist = optimise_delta(target, oracle, torch.from_numpy(H), fi["heads"], labels, pos, neg, lam=lam,
                                           layer=layer, steps=steps, delta0=delta, nat_logits=fi["nat_logits"],
                                           batch=batch, trace=trace, lo_nat=lo_nat)
        delta = delta_t.numpy()
        np.save(dpath, delta)
        Hs = (H + delta[None, :]).astype(np.float32)
        np.save(spath, Hs.astype(np.float16))
        with torch.no_grad():
            lo_ed = olens_lo(oracle, torch.from_numpy(Hs), torch.zeros(H.shape[1]), pos, neg, layer, batch=batch).float().cpu().numpy()
            beh = behaviour_under(target, fi, lambda h, dv=torch.from_numpy(delta): h + dv.to(h.device, h.dtype), layer)
        summary["arms"][f"{arm}|{lam}"] = {
            "delta_norm": float(np.linalg.norm(delta)), "delta_norm_rel": float(np.linalg.norm(delta) / np.linalg.norm(H, axis=1).mean()),
            "oracle_cross_rate": cross_rate(lo_nat, lo_ed), "oracle_follow_mean": float(np.nanmean(follow(lo_nat, lo_ed, push, sep_nat))),
            "kl_fwd_mean": float(beh["kl_fwd"].mean()), "kl_rev_mean": float(beh["kl_rev"].mean()),
            "answer_change_rate": float(np.mean(beh["says_pos"] != (fi["lo_model_nat"] > 0).astype(int))),
            "model_lo_abs_shift_median": float(np.median(np.abs(beh["lo_model"] - fi["lo_model_nat"]))),
            "n_steps": steps, "wall_s": st.wall_s}
        for j, (iid, key) in enumerate(zip(order, keys)):
            if key in done:
                continue
            append_jsonl(RF_PATH, {"key": key, "module": MODULE, **stamp(), "experiment": "e5", "dataset": ds, "item_id": iid,
                                      "label": labels[j], "arm": arm, "lam": lam, "push": push[j],
                                      "read_layer": layer, "delta_norm": float(np.linalg.norm(delta)),
                                      "oracle_lo_nat": float(lo_nat[j]), "oracle_lo_ed": float(lo_ed[j]),
                                      "oracle_sep_nat": sep_nat, "model_lo_nat": float(fi["lo_model_nat"][j]),
                                      "model_lo_ed": float(beh["lo_model"][j]), "model_says_pos_nat": int(fi["lo_model_nat"][j] > 0),
                                      "model_says_pos_ed": int(beh["says_pos"][j]), "kl_fwd": float(beh["kl_fwd"][j]),
                                      "kl_rev": float(beh["kl_rev"][j]), "candidates": fi["candidates"], "created_at": now_iso()})
        ledger.add(sum(len(r) for r in fi["rows"]), 0, st.wall_s, st.peak_mem_gb)
        for rd in readers:          # transfer: the same report-flipped states, every reader family bound here
            score_states(rd, ds, arm, lam, Hs, fi, items, layer)
        # matched-norm random controls (the band for both the report-flip and the transfer)
        for k, rv in enumerate(random_deltas(ds, n_random, float(np.linalg.norm(delta)), H.shape[1])):
            arm_k = f"rand{k}"
            keys_k = [f"{ds}|{iid}|{arm_k}|{lam}" for iid in order]
            Hr = (H + rv[None, :]).astype(np.float32)
            np.save(d_out / f"{arm_k}_lam{lam}.npy", rv)
            np.save(d_out / f"{arm_k}_lam{lam}_states.npy", Hr.astype(np.float16))
            if not all(k2 in done for k2 in keys_k):
                with torch.no_grad():
                    lo_r = olens_lo(oracle, torch.from_numpy(Hr), torch.zeros(H.shape[1]), pos, neg, layer, batch=batch).float().cpu().numpy()
                    beh_r = behaviour_under(target, fi, lambda h, dv=torch.from_numpy(rv): h + dv.to(h.device, h.dtype), layer)
                for j, (iid, key) in enumerate(zip(order, keys_k)):
                    append_jsonl(RF_PATH, {"key": key, "module": MODULE, **stamp(), "experiment": "e5", "dataset": ds, "item_id": iid,
                                              "label": labels[j], "arm": arm_k, "lam": lam, "push": push[j], "read_layer": layer,
                                              "delta_norm": float(np.linalg.norm(rv)), "oracle_lo_nat": float(lo_nat[j]),
                                              "oracle_lo_ed": float(lo_r[j]), "oracle_sep_nat": sep_nat,
                                              "model_lo_nat": float(fi["lo_model_nat"][j]), "model_lo_ed": float(beh_r["lo_model"][j]),
                                              "model_says_pos_nat": int(fi["lo_model_nat"][j] > 0), "model_says_pos_ed": int(beh_r["says_pos"][j]),
                                              "kl_fwd": float(beh_r["kl_fwd"][j]), "kl_rev": float(beh_r["kl_rev"][j]),
                                              "candidates": fi["candidates"], "created_at": now_iso()})
            for rd in readers:
                score_states(rd, ds, arm_k, lam, Hr, fi, items, layer)
    for row in trace:
        append_jsonl(TRACE_PATH, {"key": f"{ds}|{row['lam']}|{row['step']}", "module": MODULE, **stamp(), "experiment": "e5",
                                  "dataset": ds, **row, "created_at": now_iso()})
    (d_out / "index.json").write_text(json.dumps({"item_ids": order, "labels": labels, "lambdas": list(lambdas),
                                                  "read_layer": layer, "steps": steps, "summary": summary}, indent=1))
    r = ledger.flush()
    log_line(ST.LOG, f"e5 report_flip {ds}: " + "; ".join(
        f"λ={k.split('|')[1]} cross {v['oracle_cross_rate']:.2f} KL {v['kl_fwd_mean']:.3f} answer Δ {v['answer_change_rate']:.2f}"
        for k, v in summary["arms"].items() if k.startswith("report_flip|")) + f" {r}")
    return summary


# ------------------------------------------------------------------ phase mirror: erase the reader's direction
def mirror_fact(target: M.Target, readers: list[Any], ds: str, sel: dict[str, Any], items: dict[str, dict[str, Any]],
                dirs: dict[str, np.ndarray], layer: int = ST.L_READ, n_random: int = N_RANDOM, batch: int = 32) -> dict[str, Any]:
    """Project the reader's own direction out of the block-42 state (orthogonal and LEACE-style), then ask whether the
    reader's separation collapses and whether the model's answer is unchanged."""
    import torch

    fi = fact_inputs(target, ds, sel, items, layer)
    H, order, labels = fi["H"], fi["order"], fi["labels"]
    lab = np.array(labels)
    Xall, idx = RC.load_states(ds, "chat", layer)
    pool = [i for i, iid in enumerate(idx) if items.get(iid, {}).get("split") == "pool"]
    cov = pool_cov(Xall[pool] if pool else Xall)
    done = done_ids(MIRROR_PATH, key="key")
    ledger = StepLedger(step=f"mirror_{ds}", module=MODULE)
    out: dict[str, Any] = {"dataset": ds, "cells": {}}
    targets: list[tuple[str, np.ndarray]] = []
    for rd in readers:
        w = dirs.get(f"d_{rd.name}_L{layer}")
        if w is not None:
            targets.append((rd.name, w))
    rng = np.random.default_rng(ST.RANDOM_SEED + RC.stable_offset(ds) + 11)
    targets += [(f"rand{k}", ST._unit(rng.standard_normal(H.shape[1]).astype(np.float32))) for k in range(n_random)]
    for wname, w in targets:
        for proj in PROJECTORS:
            P = projector_orth(w) if proj == "orth" else projector_leace(w, cov)
            Hp = np.asarray(apply_projector(H, P), dtype=np.float32)
            with timed_call() as st:
                with torch.no_grad():
                    beh = behaviour_under(target, fi, lambda h, Pt=torch.from_numpy(P): h.float() @ Pt.to(h.device).T, layer)
            ledger.add(sum(len(r) for r in fi["rows"]), 0, st.wall_s, st.peak_mem_gb)
            answer_change = float(np.mean(beh["says_pos"] != (fi["lo_model_nat"] > 0).astype(int)))
            for rd in readers:
                pos, neg = RC.reader_candidates(rd.name, fi["primary"])
                rows_nat = LO.score_lo(rd, torch.from_numpy(H), [(pos, neg)] * len(order), fi["family"], layer=layer, batch=batch)
                rows_p = LO.score_lo(rd, torch.from_numpy(Hp), [(pos, neg)] * len(order), fi["family"], layer=layer, batch=batch)
                s_nat = np.array([np.nan if r["lo"] is None else r["lo"] for r in rows_nat], dtype=np.float64)
                s_p = np.array([np.nan if r["lo"] is None else r["lo"] for r in rows_p], dtype=np.float64)
                sep_nat, sep_p = separation(s_nat, lab), separation(s_p, lab)
                cell = {"sep_nat": sep_nat, "sep_proj": sep_p, "sep_ratio": (sep_p / sep_nat if abs(sep_nat) > 1e-9 else np.nan),
                        "answer_change_rate": answer_change, "model_lo_abs_shift_median": float(np.median(np.abs(beh["lo_model"] - fi["lo_model_nat"]))),
                        "kl_fwd_mean": float(beh["kl_fwd"].mean())}
                out["cells"][f"{wname}|{proj}|{rd.name}"] = cell
                for j, iid in enumerate(order):
                    key = f"{ds}|{iid}|{rd.name}|{wname}|{proj}"
                    if key in done:
                        continue
                    append_jsonl(MIRROR_PATH, {"key": key, "module": MODULE, **stamp(), "experiment": "e5_mirror", "dataset": ds,
                                               "item_id": iid, "label": labels[j], "reader": rd.name, "erased": wname,
                                               "projector": proj, "read_layer": layer, "score_nat": None if np.isnan(s_nat[j]) else float(s_nat[j]),
                                               "score_proj": None if np.isnan(s_p[j]) else float(s_p[j]), "sep_nat": sep_nat, "sep_proj": sep_p,
                                               "model_lo_nat": float(fi["lo_model_nat"][j]), "model_lo_proj": float(beh["lo_model"][j]),
                                               "model_says_pos_nat": int(fi["lo_model_nat"][j] > 0), "model_says_pos_proj": int(beh["says_pos"][j]),
                                               "kl_fwd": float(beh["kl_fwd"][j]), "created_at": now_iso()})
    ledger.flush()
    log_line(ST.LOG, f"e5 mirror {ds}: " + "; ".join(
        f"{k} sep {v['sep_ratio']:.2f} answer Δ {v['answer_change_rate']:.2f}" for k, v in out["cells"].items()
        if not k.startswith("rand"))[:600])
    return out


# ------------------------------------------------------------------ main
def select_facts(sel_all: dict[str, Any], datasets: list[str] | None, n_facts: int) -> dict[str, Any]:
    """The first n facts of the R5 selection, ordered as `analyze.r5_select` wrote them (probe + prompt-only AUROC)."""
    sel = {ds: s for ds, s in sel_all["datasets"].items() if not datasets or ds in datasets}
    if not datasets:
        sel = dict(list(sel.items())[:n_facts])
    return sel


def audit_e5(sel: dict[str, Any], lambdas: tuple[float, ...], k_random: int,
             readers: tuple[str, ...] = ("jlens", "olens", "skip_a"),
             require_gpu: str | None = None) -> tuple[list[str], dict[str, Any]]:
    """PODS.md rule 5 for E5: every (fact × arm × λ) cell of the optimisation, every reader's transfer row for the
    optimised arm, and both projectors of the mirror must hold one row per item. Files only — no model, no GPU.

    E5's failure mode is the same shape as the one that cost a pod launch in SWAP: if the optimisation diverges or a
    reader cannot be bound, its cell writes nothing while the random arms fill in normally, and a total row count
    hides it. `--phase audit` makes that exit non-zero instead.

    It also checks the accelerator the rows came from (Guiv, 2026-10-20): E5 runs on an RTX PRO 6000 while the earlier
    phases ran on H100s, and bf16 reduction order is device-dependent, so rows from two cards are not a comparable
    panel. Rows on MORE THAN ONE device fail, as mixed run kinds do; `require_gpu` additionally fails any row whose
    `gpu` does not name the pre-registered card (unstamped rows included — E5 starts with no rows, so every row of it
    must say where it ran).
    """
    opt = read_jsonl(RF_PATH)
    rdr = read_jsonl(RF_READERS_PATH)
    mir = read_jsonl(MIRROR_PATH)
    c_opt = collections.Counter((r.get("dataset"), r.get("arm"), float(r.get("lam", 0.0))) for r in opt)
    c_rdr = collections.Counter((r.get("dataset"), r.get("reader"), r.get("arm"), float(r.get("lam", 0.0))) for r in rdr)
    c_mir = collections.Counter((r.get("dataset"), r.get("reader"), r.get("erased"), r.get("projector")) for r in mir)
    arms = ["report_flip"] + [f"rand{k}" for k in range(k_random)]
    fails: list[str] = []
    summary: dict[str, Any] = {"opt_rows": len(opt), "reader_rows": len(rdr), "mirror_rows": len(mir),
                               "facts": len(sel), "cells": 0, "empty": 0, "short": 0}

    def cell(n_expected: int, got: int, label: str) -> None:
        summary["cells"] += 1
        if got == 0:
            summary["empty"] += 1
            fails.append(f"SMOKE FAILED: {label} has NO rows (expected {n_expected})")
        elif got != n_expected:
            summary["short"] += 1
            fails.append(f"SMOKE FAILED: {label} has {got} rows, expected {n_expected}")

    gpus = collections.Counter(str(r.get("gpu")) for r in (*opt, *rdr, *mir))
    summary["gpus"] = dict(gpus)
    named = {g for g in gpus if g not in ("None", "", "cpu")}
    if len(named) > 1:
        fails.append("SMOKE FAILED: rows were computed on more than one accelerator ("
                     + ", ".join(f"{g} x{gpus[g]}" for g in sorted(named))
                     + "); E5's arms are comparable only within one device")
    if require_gpu and gpus:
        wrong = {g: n for g, n in gpus.items() if require_gpu.lower() not in g.lower()}
        if wrong:
            fails.append(f"SMOKE FAILED: {sum(wrong.values())} row(s) not computed on {require_gpu!r} ("
                         + ", ".join(f"{g} x{n}" for g, n in sorted(wrong.items())) + ")")

    for ds, spec in sorted(sel.items()):
        n = len(spec["item_ids"])
        for lam in lambdas:
            for arm in arms:
                cell(n, c_opt.get((ds, arm, float(lam)), 0), f"{ds}/{arm}@lam{lam}")
            for rd in readers:                      # the transfer panel, on the optimised arm
                cell(n, c_rdr.get((ds, rd, "report_flip", float(lam)), 0), f"{ds}/transfer:{rd}@lam{lam}")
        if mir:                                      # the mirror is its own phase; audit it only once it has run
            erased = sorted({r.get("erased") for r in mir if r.get("dataset") == ds})
            if not erased:
                fails.append(f"SMOKE FAILED: {ds} has mirror rows for other facts but none of its own")
            for w in erased:
                for proj in PROJECTORS:
                    for rd in readers:
                        cell(n, c_mir.get((ds, rd, w, proj), 0), f"{ds}/mirror:{rd}|{w}|{proj}")
        else:
            summary.setdefault("notes", []).append(f"NOTE: no mirror rows yet ({MIRROR_PATH.name}); "
                                                   f"--phase mirror has not run, so its cells are not audited")
    return fails, summary


def main(argv: list[str] | None = None) -> int:
    from projects.g_agreement.g1_agreement.collect import load_target_timed

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--phase", choices=["A", "B", "mirror", "audit"], required=True,
                    help="audit = rule 5: one row per item in every fact x arm x lambda cell, the "
                         "transfer panel and both mirror projectors (files only, no model)")
    ap.add_argument("--datasets", nargs="*", default=None)
    ap.add_argument("--readers", nargs="*", default=["jlens", "olens", "skip_a"])
    ap.add_argument("--lambdas", nargs="*", type=float, default=list(LAMBDAS))
    ap.add_argument("--steps", type=int, default=STEPS)
    ap.add_argument("--n-facts", type=int, default=N_FACTS)
    ap.add_argument("--k-random", type=int, default=N_RANDOM)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--allow-unfrozen", action="store_true")
    ap.add_argument("--require-gpu", default=None,
                    help="audit: fail unless every row's `gpu` names this card (substring, case-insensitive). E5's "
                         "pre-registered card is \"RTX PRO 6000\" (Guiv, 2026-10-20); rows from two devices always fail")
    ap.add_argument("--run-kind", choices=list(RC.RUN_KINDS), default=None,
                    help="GUARDS.md rule 3: a real run says --run-kind real. The default is \"unknown\", never "
                         "\"real\" by omission; --limit forces \"smoke\". --datasets never implies smoke")
    a = ap.parse_args(argv)
    if a.run_kind:
        RC.set_run_kind(a.run_kind)
    RC.require_frozen_r(a.allow_unfrozen)
    sel = select_facts(ST.load_selection(), a.datasets, a.n_facts)
    if a.phase == "audit":                      # files only: no model, no GPU
        fails, summary = audit_e5(sel, tuple(a.lambdas), a.k_random, tuple(a.readers), a.require_gpu)
        for n in summary.get("notes", []):
            print(f"[e5 audit] {n}", flush=True)
        for line in fails:
            print(line, flush=True)
        print(f"[e5 audit] {summary['facts']} facts, {summary['cells']} cells; rows opt {summary['opt_rows']}, "
              f"reader {summary['reader_rows']}, mirror {summary['mirror_rows']}; empty {summary['empty']}, "
              f"short {summary['short']}; gpu {summary['gpus'] or 'no rows'}", flush=True)
        log_line(ST.LOG, f"e5 audit: {len(fails)} failures over {summary['cells']} cells")
        return 1 if fails else 0
    items = {it["item_id"]: it for it in B.load_items(B.ITEMS_R, "all", list(sel))}
    RF_DIR.mkdir(parents=True, exist_ok=True)
    log_line(ST.LOG, f"e5 phase {a.phase}: {len(sel)} facts {sorted(sel)} λ {a.lambdas} steps {a.steps}")
    if a.phase == "B":
        nla = R.NLAReader().bind()
        for ds in sel:
            fi_items = {i: items[i] for i in sel[ds]["item_ids"]}
            idx = json.loads((RF_DIR / ds / "index.json").read_text())
            first = items[idx["item_ids"][0]]["primary"]
            fi = {"order": idx["item_ids"], "primary": first, "family": RC.register_templates(first)}
            for f in sorted((RF_DIR / ds).glob("*states*.npy")):
                stem = f.stem.replace("_states", "")
                arm, lam = (stem.split("_lam") + [""])[:2] if "_lam" in stem else ("report_flip", "0")
                arm = "report_flip" if arm == "states" else arm
                score_states(nla, ds, arm, float(lam), np.load(f).astype(np.float32), fi, fi_items)
        nla.unload()
        return 0
    target = load_target_timed(MODULE)
    n_frozen = freeze_params(target.model)
    readers = ST.bind_readers(target, a.readers)
    freeze_params(target.model)   # the Oracle / skip-lens adapters mount trainable LoRA tensors
    print(f"[e5] parameters switched to requires_grad=False: {n_frozen} (+ adapter tensors)", flush=True)
    out = []
    for ds, s in sel.items():
        if a.phase == "A":
            out.append(report_flip_fact(target, readers, ds, s, items, tuple(a.lambdas), a.steps, n_random=a.k_random, batch=a.batch))
        else:
            out.append(mirror_fact(target, readers, ds, s, items, ST.directions_for(ds), n_random=a.k_random))
        print(f"[e5 {a.phase}] {ds} done", flush=True)
    M.unload(target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
