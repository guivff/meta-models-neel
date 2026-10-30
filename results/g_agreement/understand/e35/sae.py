"""E35 pinned Qwen-Scope adapter, implementation note dated 2026-10-25.

Encoder convention follows the pinned official app.py (lines 190--242): raw
resid_post activations, fp32, affine encoder, ReLU, then TopK. No whitening,
centering, unit normalization, or subtraction of the decoder bias is applied.

The decoder formula is the conventional affine reconstruction inferred from
the checkpoint's documented W_dec[d_model, d_sae] and b_dec[d_model] shapes;
the published app only encodes/steers. Shape disagreement fails closed.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from pathlib import Path

import torch
from torch import Tensor, nn


PINNED_REPOSITORY = "Qwen/SAE-Res-Qwen3.5-27B-W80K-L0_50"
PINNED_REVISION = "13d4221569f7ca5d3c1e605e3e3dc95117e4807c"
PINNED_FILENAME = "layer44.sae.pt"
PINNED_SHA256 = "7316b684ada2e8461d814c6fc78200cc2a1f5b6756bedf172f58ce5f92b3977f"
PINNED_BYTES = 3355793787
D_MODEL = 5120
D_SAE = 81920
TOP_K = 50
_KEYS = frozenset({"W_enc", "W_dec", "b_enc", "b_dec"})


def sha256_file(path: str | Path) -> str:
    """Hash the complete checkpoint without reading it all into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_finite(tensor: Tensor, name: str) -> None:
    # Chunk the large parameter matrices instead of allocating a full-size mask.
    flat = tensor.reshape(-1)
    for start in range(0, flat.numel(), 1024 * 1024):
        if not bool(torch.isfinite(flat[start : start + 1024 * 1024]).all()):
            raise ValueError(f"{name} contains non-finite values")


def _validate_parameters(params: Mapping[str, Tensor]) -> tuple[int, int]:
    if not isinstance(params, Mapping) or set(params) != _KEYS:
        raise ValueError("SAE checkpoint must contain exactly W_enc, W_dec, b_enc, b_dec")
    if any(not isinstance(params[key], Tensor) for key in _KEYS):
        raise TypeError("Every SAE parameter must be a torch tensor")
    if any(not params[key].is_floating_point() for key in _KEYS):
        raise TypeError("Every SAE parameter must have a floating dtype")
    if params["W_enc"].ndim != 2:
        raise ValueError("W_enc must have shape [d_sae, d_model]")
    d_sae, d_model = params["W_enc"].shape
    expected = {"W_dec": (d_model, d_sae), "b_enc": (d_sae,), "b_dec": (d_model,)}
    if d_sae < 1 or d_model < 1 or any(tuple(params[key].shape) != shape for key, shape in expected.items()):
        raise ValueError("SAE parameter shapes disagree with W_enc[d_sae, d_model]")
    if len({params[key].device for key in _KEYS}) != 1:
        raise ValueError("All SAE parameters must share one device")
    return d_model, d_sae


class QwenScopeSAE(nn.Module):
    """Inference-only adapter; small parameter dictionaries support offline tests."""

    def __init__(self, params: Mapping[str, Tensor], *, k: int):
        super().__init__()
        self.d_model, self.d_sae = _validate_parameters(params)
        if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= self.d_sae:
            raise ValueError("k must be an integer between 1 and d_sae")
        self.k = k
        for name in sorted(_KEYS):
            value = params[name].detach().to(dtype=torch.float32).contiguous()
            _require_finite(value, name)
            self.register_buffer(name, value)
        self.eval()

    @classmethod
    def from_checkpoint(cls, path: str | Path, *, device: str | torch.device = "cpu") -> "QwenScopeSAE":
        """Load only the exact preregistered transfer checkpoint; never use pickle fallback."""
        path = Path(path)
        if sha256_file(path) != PINNED_SHA256:
            raise ValueError("Checkpoint SHA-256 does not match the pinned layer-44 SAE")
        if path.stat().st_size != PINNED_BYTES:
            raise ValueError("Checkpoint byte count does not match the pinned layer-44 SAE")
        params = torch.load(path, map_location="cpu", weights_only=True)
        d_model, d_sae = _validate_parameters(params)
        if (d_model, d_sae) != (D_MODEL, D_SAE):
            raise ValueError("Pinned SAE must have d_model=5120 and d_sae=81920")
        return cls(params, k=TOP_K).to(device=device)

    def _check_tensor(self, value: Tensor, width: int, name: str) -> Tensor:
        if not isinstance(value, Tensor) or not value.is_floating_point():
            raise TypeError(f"{name} must be a floating torch tensor")
        if value.ndim < 1 or value.shape[-1] != width or value.numel() == 0:
            raise ValueError(f"{name} must be nonempty with last dimension {width}")
        if value.device != self.W_enc.device:
            raise ValueError(f"{name} must be on the SAE device")
        if any(getattr(self, key).dtype != torch.float32 for key in _KEYS):
            raise ValueError("SAE parameters must remain float32")
        value = value.float()
        _require_finite(value, name)
        return value

    @torch.no_grad()
    def encode(self, x: Tensor) -> Tensor:
        """Encode unnormalized residuals in fp32; retain positive TopK activations."""
        x = self._check_tensor(x, self.d_model, "input")
        # Disable an enclosing autocast context: the registered SAE math is fp32.
        with torch.autocast(device_type=x.device.type, enabled=False):
            pre = x @ self.W_enc.T + self.b_enc
            _require_finite(pre, "encoder preactivations")
            values, indices = torch.topk(torch.relu(pre), self.k, dim=-1)
            code = torch.zeros_like(pre).scatter_(-1, indices, values)
        _require_finite(code, "SAE code")
        return code

    @torch.no_grad()
    def decode(self, code: Tensor) -> Tensor:
        """Conventional affine decoder in raw residual units, including b_dec."""
        code = self._check_tensor(code, self.d_sae, "SAE code")
        if bool((code < 0).any()):
            raise ValueError("TopK ReLU codes cannot be negative")
        with torch.autocast(device_type=code.device.type, enabled=False):
            reconstructed = code @ self.W_dec.T + self.b_dec
        _require_finite(reconstructed, "SAE reconstruction")
        return reconstructed

    @torch.no_grad()
    def reconstruct_and_fired(self, x: Tensor) -> tuple[Tensor, Tensor]:
        """Return reconstruction and a [d_sae] mask of latents positive anywhere.

        A zero value selected by TopK does not count as a fired latent. Finiteness
        is enforced before the boolean reduction used by the dead-latent gate.
        """
        code = self.encode(x)
        _require_finite(code, "SAE code before fired reduction")
        reconstructed = self.decode(code)
        fired = (code.reshape(-1, self.d_sae) > 0).any(dim=0)
        return reconstructed, fired
