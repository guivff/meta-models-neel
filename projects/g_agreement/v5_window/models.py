"""V5 readers and training (torch; MPS when available, else CPU).

Every reader maps a window ``x`` [n, T, d] with a validity mask [n, T] (True = real position; the last True position is the
last token) to class logits [n, K]:
  (a) last_linear   linear head on the last token
  (b) mean_linear   linear head on the masked mean over the window
  (c) attn_linear   one learned query q (McKenzie-style): a = softmax_t(x_t . q / sqrt(d)); linear head on sum_t a_t x_t
  (d) attn_mlp      the same attention pooling, then Linear(d, 256) -> GELU -> Linear(256, K)
Features are standardised per dimension with training-set statistics (last-token statistics for (a), all valid positions for
(b)-(d)); the standardiser is part of the module so saved weights are self-contained. Loss = mean cross-entropy +
lambda * sum of squared weights (biases excluded); lambda from the pre-registered grid {1e-3, 1e-2, 1e-1, 1} by inner CV
(held-out accuracy, ties -> the largest lambda), early stopping on the inner validation loss; the final model is refit on
the whole training set for the median best epoch of the inner fits.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import torch
from torch import nn

MODELS = ("last_linear", "mean_linear", "attn_linear", "attn_mlp")
WINDOW_MODELS = ("attn_linear", "attn_mlp")
MODEL_LABEL = {"last_linear": "(a) last-token linear", "mean_linear": "(b) mean-pooled linear", "attn_linear": "(c) attention-pooled linear",
               "attn_mlp": "(d) attention-pooled MLP"}
LAMBDAS = (1e-3, 1e-2, 1e-1, 1.0)
HIDDEN = 256


def pick_device(prefer: str = "auto") -> torch.device:
    if prefer == "cpu":
        return torch.device("cpu")
    if prefer in ("auto", "mps") and torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def last_index(mask: torch.Tensor) -> torch.Tensor:
    """index of the last True position per row ([n] long); rows with no True position map to 0."""
    T = mask.shape[1]
    ar = torch.arange(T, device=mask.device)
    return torch.where(mask, ar, torch.full_like(ar, -1)).max(dim=1).values.clamp(min=0)


def masked_mean(x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    m = mask.to(x.dtype).unsqueeze(-1)
    return (x * m).sum(1) / m.sum(1).clamp(min=1.0)


class Reader(nn.Module):
    def __init__(self, kind: str, d: int, n_classes: int, hidden: int = HIDDEN):
        super().__init__()
        if kind not in MODELS:
            raise ValueError(f"unknown reader kind {kind!r}; expected one of {MODELS}")
        self.kind, self.d, self.n_classes = kind, d, n_classes
        self.register_buffer("mu", torch.zeros(d))
        self.register_buffer("sd", torch.ones(d))
        if kind in WINDOW_MODELS:
            self.q = nn.Parameter(torch.zeros(d))  # zero init: starts as the masked mean (uniform attention)
        if kind == "attn_mlp":
            self.head = nn.Sequential(nn.Linear(d, hidden), nn.GELU(), nn.Linear(hidden, n_classes))
        else:
            self.head = nn.Linear(d, n_classes)

    # -- standardiser -------------------------------------------------------------------------------------------------
    @torch.no_grad()
    def set_standardiser(self, x: torch.Tensor, mask: torch.Tensor) -> None:
        """mu/sd over the training rows: the last token for (a), every valid position otherwise."""
        if self.kind == "last_linear":
            v = x[torch.arange(x.shape[0], device=x.device), last_index(mask)]
        else:
            v = x[mask]
        mu = v.mean(0)
        sd = v.std(0, unbiased=False)
        sd = torch.where(sd > 0, sd, torch.ones_like(sd))
        self.mu.copy_(mu)
        self.sd.copy_(sd)

    # -- forward -------------------------------------------------------------------------------------------------------
    def attention(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """[n, T] attention weights (zero on masked positions)."""
        z = (x - self.mu) / self.sd
        s = (z @ self.q) / math.sqrt(self.d)
        s = s.masked_fill(~mask, float("-inf"))
        return torch.softmax(s, dim=1)

    def pooled(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        z = (x - self.mu) / self.sd
        if self.kind == "last_linear":
            return z[torch.arange(z.shape[0], device=z.device), last_index(mask)]
        if self.kind == "mean_linear":
            return masked_mean(z, mask)
        a = self.attention(x, mask)
        return (a.unsqueeze(-1) * z).sum(1)

    def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        return self.head(self.pooled(x, mask))

    def weight_sq(self) -> torch.Tensor:
        tot = torch.zeros((), device=self.mu.device)
        for name, p in self.named_parameters():
            if not name.endswith("bias"):
                tot = tot + (p * p).sum()
        return tot


# ------------------------------------------------------------------------------------------------------- training
@dataclass
class FitResult:
    model: Reader
    lam: float
    epochs: int
    inner: List[dict] = field(default_factory=list)
    wall_s: float = 0.0


def _ce(logits: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    return nn.functional.cross_entropy(logits, y)


def train_once(kind: str, x: torch.Tensor, mask: torch.Tensor, y: torch.Tensor, n_classes: int, lam: float, *, max_epochs: int = 300,
               lr: float = 3e-3, patience: int = 30, val: Optional[Tuple[torch.Tensor, torch.Tensor, torch.Tensor]] = None,
               fixed_epochs: Optional[int] = None, seed: int = 0, hidden: int = HIDDEN) -> Tuple[Reader, int, Dict[str, float]]:
    """Full-batch Adam. With ``val`` = (x, mask, y): early stopping on the validation loss (best-epoch weights restored).
    With ``fixed_epochs``: exactly that many epochs, no validation. Returns (model, epochs used, {val_loss, val_acc})."""
    torch.manual_seed(seed)
    model = Reader(kind, x.shape[-1], n_classes, hidden=hidden).to(x.device)
    model.set_standardiser(x, mask)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    best_loss, best_acc, best_epoch, best_state, bad = float("inf"), float("nan"), 0, None, 0
    n_epochs = fixed_epochs if fixed_epochs is not None else max_epochs
    for ep in range(1, n_epochs + 1):
        model.train()
        opt.zero_grad(set_to_none=True)
        loss = _ce(model(x, mask), y) + lam * model.weight_sq()
        loss.backward()
        opt.step()
        if val is None:
            continue
        model.eval()
        with torch.no_grad():
            lv = model(val[0], val[1])
            vloss = float(_ce(lv, val[2]))
            vacc = float((lv.argmax(1) == val[2]).float().mean())
        if vloss < best_loss - 1e-6:
            best_loss, best_acc, best_epoch, bad = vloss, vacc, ep, 0
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= patience:
                break
    if val is None:
        return model, n_epochs, {}
    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    return model, best_epoch, {"val_loss": best_loss, "val_acc": best_acc}


def fit_inner_cv(kind: str, x: torch.Tensor, mask: torch.Tensor, y: torch.Tensor, n_classes: int, inner_splits: Sequence[Tuple[np.ndarray, np.ndarray]],
                 lambdas: Sequence[float] = LAMBDAS, *, max_epochs: int = 300, lr: float = 3e-3, patience: int = 30, seed: int = 0,
                 hidden: int = HIDDEN) -> FitResult:
    """Choose lambda by inner CV (mean held-out accuracy over ``inner_splits`` = (train_idx, val_idx) into the rows of x; ties ->
    the largest lambda), then refit on all rows for the median best epoch (at least 5)."""
    t0 = time.time()
    inner: List[dict] = []
    best_lam, best_score, best_epochs = lambdas[-1], -1.0, [max_epochs]
    for lam in lambdas:
        accs, losses, eps = [], [], []
        for k, (tr, va) in enumerate(inner_splits):
            tr_t, va_t = torch.as_tensor(tr, device=x.device), torch.as_tensor(va, device=x.device)
            if len(set(y[tr_t].tolist())) < 2:
                continue
            _, ep, st = train_once(kind, x[tr_t], mask[tr_t], y[tr_t], n_classes, lam, max_epochs=max_epochs, lr=lr, patience=patience,
                                   val=(x[va_t], mask[va_t], y[va_t]), seed=seed + k, hidden=hidden)
            accs.append(st["val_acc"])
            losses.append(st["val_loss"])
            eps.append(max(ep, 1))
        score = float(np.mean(accs)) if accs else -1.0
        inner.append({"lambda": lam, "val_acc": score, "val_loss": float(np.mean(losses)) if losses else float("nan"), "epochs": eps})
        if score >= best_score - 1e-12:  # >=: later (larger) lambdas win ties
            best_lam, best_score, best_epochs = lam, score, eps or [max_epochs]
    n_ep = int(max(5, round(float(np.median(best_epochs)))))
    model, _, _ = train_once(kind, x, mask, y, n_classes, best_lam, fixed_epochs=n_ep, lr=lr, seed=seed, hidden=hidden)
    model.eval()
    return FitResult(model=model, lam=best_lam, epochs=n_ep, inner=inner, wall_s=time.time() - t0)


@torch.no_grad()
def predict_logits(model: Reader, x: torch.Tensor, mask: torch.Tensor, batch: int = 512) -> np.ndarray:
    model.eval()
    out = [model(x[i:i + batch], mask[i:i + batch]).float().cpu().numpy() for i in range(0, x.shape[0], batch)]
    return np.concatenate(out, 0) if out else np.zeros((0, model.n_classes))


@torch.no_grad()
def attention_weights(model: Reader, x: torch.Tensor, mask: torch.Tensor) -> np.ndarray:
    if model.kind not in WINDOW_MODELS:
        raise ValueError("attention weights exist only for the attention-pooled readers")
    return model.attention(x, mask).float().cpu().numpy()


def export_state(fit: FitResult, **meta) -> dict:
    """fp16 state dict + metadata for cache/g_agreement/v/window_reader/."""
    sd = {k: (v.detach().cpu().half() if v.is_floating_point() else v.detach().cpu()) for k, v in fit.model.state_dict().items()}
    return {"state_dict": sd, "kind": fit.model.kind, "d": fit.model.d, "n_classes": fit.model.n_classes, "lambda": fit.lam,
            "epochs": fit.epochs, "inner_cv": fit.inner, **meta}
