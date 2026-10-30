"""Fixed E35 fallback TopK training implementation, chosen 2026-10-25.

Only the authorized collector supplies unique training positions. This module
does not load corpus/model/gate data, select checkpoints, or run a training job.
See FALLBACK_TRAINING_CHOICES.20261025.md before using its production defaults.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import math
import os

import torch
from torch import Tensor, nn


@dataclass(frozen=True)
class TrainConfig:
    d_model: int = 5120
    d_sae: int = 16384
    k: int = 64
    batch_size: int = 4096
    target_tokens: int = 20_000_000
    seed: int = 20261025
    learning_rate: float = 3e-4
    beta1: float = .9
    beta2: float = .999
    adam_epsilon: float = 1e-8
    grad_clip: float = 1.
    dead_after_tokens: int = 1_000_000
    auxiliary_k: int = 512
    auxiliary_weight: float = 1 / 32


FIXED_CONFIG = TrainConfig()
NORMALIZATION_MANIFEST = {
    'experiment': 'E35',
    'schema': 'e35-fallback-identity-v1',
    'input_transform': 'identity_raw_residual_float32',
    'encoder': 'TopK(ReLU(x @ W_enc.T + b_enc),64)',
    'decoder': 'z @ W_dec.T + b_dec',
    'external_centering': False,
    'external_whitening': False,
    'input_scale_fit': False,
    'decoder_bias_in_latent_norm_share': False,
}
PARAMETER_KEYS = ('W_enc', 'W_dec', 'b_enc', 'b_dec')


def _validate_config(config):
    for name in ('d_model', 'd_sae', 'k', 'batch_size', 'target_tokens', 'seed',
                 'dead_after_tokens', 'auxiliary_k'):
        if type(getattr(config, name)) is not int or getattr(config, name) < 1:
            raise ValueError('positive integer training dimensions and counts required')
    if config.k > config.d_sae or config.auxiliary_k > config.d_sae:
        raise ValueError('TopK counts cannot exceed dictionary width')
    for name in ('learning_rate', 'adam_epsilon', 'grad_clip', 'auxiliary_weight'):
        value = getattr(config, name)
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError('positive finite optimization settings required')
    if not 0 <= config.beta1 < 1 or not 0 <= config.beta2 < 1:
        raise ValueError('Adam betas must lie in [0,1)')


def _finite(tensor, name):
    if not bool(torch.isfinite(tensor).all()):
        raise ValueError(name + ' must be finite')


class TopKSAE(nn.Module):
    """Trainable affine raw-input adapter with decoder columns of unit norm."""
    def __init__(self, config=FIXED_CONFIG):
        super().__init__()
        _validate_config(config)
        self.d_model, self.d_sae, self.k = config.d_model, config.d_sae, config.k
        generator = torch.Generator(device='cpu').manual_seed(config.seed)
        decoder = torch.randn((self.d_model, self.d_sae), generator=generator, dtype=torch.float32)
        decoder /= torch.linalg.vector_norm(decoder, dim=0, keepdim=True)
        self.W_dec = nn.Parameter(decoder)
        self.W_enc = nn.Parameter(decoder.T.contiguous().clone())
        self.b_enc = nn.Parameter(torch.zeros(self.d_sae))
        self.b_dec = nn.Parameter(torch.zeros(self.d_model))

    def checked_input(self, x):
        if (not isinstance(x, Tensor) or not x.is_floating_point()
                or x.ndim != 2 or x.shape[1] != self.d_model or len(x) == 0
                or x.device != self.W_enc.device):
            raise ValueError('nonempty aligned floating training activations required')
        if any(getattr(self, name).dtype != torch.float32 for name in PARAMETER_KEYS):
            raise ValueError('SAE parameters must remain float32')
        x = x.detach().float()
        _finite(x, 'raw input')
        return x

    @staticmethod
    def sparse_topk(pre, k):
        values, indices = torch.topk(torch.relu(pre), k, dim=-1)
        return torch.zeros_like(pre).scatter(-1, indices, values)

    def encode(self, x):
        x = self.checked_input(x)
        with torch.autocast(device_type=x.device.type, enabled=False):
            pre = x @ self.W_enc.T + self.b_enc
            _finite(pre, 'encoder preactivations')
            return self.sparse_topk(pre, self.k)

    def decode(self, z):
        if (z.ndim != 2 or z.shape[1] != self.d_sae or z.device != self.W_dec.device
                or not z.is_floating_point() or (z < 0).any()):
            raise ValueError('aligned nonnegative SAE code required')
        _finite(z, 'SAE code')
        with torch.autocast(device_type=z.device.type, enabled=False):
            reconstruction = z.float() @ self.W_dec.T + self.b_dec
            _finite(reconstruction, 'SAE reconstruction')
            return reconstruction

    @torch.no_grad()
    def project_decoder_(self):
        norms = torch.linalg.vector_norm(self.W_dec, dim=0, keepdim=True)
        _finite(norms, 'decoder column norms')
        if (norms <= 0).any():
            raise ValueError('zero decoder column cannot be normalized')
        self.W_dec.div_(norms)

    @torch.no_grad()
    def project_decoder_gradient_(self):
        if self.W_dec.grad is None:
            raise ValueError('decoder gradient required')
        radial = (self.W_dec.grad * self.W_dec).sum(dim=0, keepdim=True)
        self.W_dec.grad.sub_(self.W_dec * radial)


def auxiliary_loss(pre, decoder, residual, dead_mask, *, k, loss_scale):
    """Dead-only AuxK, no decoder bias; residual is detached before this loss.

    The fixed initial TRAINING energy scales both objectives. No current-batch
    residual variance or held-out statistics are fitted. See the dated choices
    file for explicit differences from the OpenAI reference implementation.
    """
    if (dead_mask.dtype != torch.bool or dead_mask.shape != (pre.shape[1],)
            or decoder.shape[1] != pre.shape[1] or residual.shape != (len(pre), decoder.shape[0])):
        raise ValueError('AuxK shapes disagree')
    if type(k) is not int or k < 1 or not math.isfinite(loss_scale) or loss_scale <= 0:
        raise ValueError('positive AuxK size and loss scale required')
    count = int(dead_mask.sum())
    if not count:
        return pre.sum() * 0
    masked = pre.masked_fill(~dead_mask[None, :], -torch.inf)
    z = TopKSAE.sparse_topk(masked, min(k, count))
    estimate = z @ decoder.T
    return (estimate - residual.detach()).square().mean() * loss_scale


class SAETrainer:
    """One contiguous single pass, with no gate input or checkpoint selection.

    `first_position` is a monotonic stream offset, not proof of corpus identity;
    the collector must enforce original document/token uniqueness and the held-
    out group exclusion. The first minibatch initializes statistics AND receives
    one ordinary optimization update. Production requires FIXED_CONFIG exactly.
    """
    def __init__(self, *, device='cpu', config=FIXED_CONFIG, synthetic=False,
                 timing_force_auxiliary=False):
        _validate_config(config)
        if synthetic is not True and config != FIXED_CONFIG:
            raise ValueError('production uses the fixed registered training configuration')
        if timing_force_auxiliary is not False and (timing_force_auxiliary is not True or synthetic is not True):
            raise ValueError('forced auxiliary timing is scratch-only')
        self.config, self.synthetic = config, synthetic is True
        self.timing_force_auxiliary = timing_force_auxiliary
        device = torch.device(device)
        if device.type == 'cuda' and os.environ.get('CUBLAS_WORKSPACE_CONFIG') not in (':4096:8', ':16:8'):
            raise ValueError('set deterministic CUBLAS_WORKSPACE_CONFIG before CUDA initialization')
        torch.use_deterministic_algorithms(True)
        if device.type == 'cuda':
            torch.backends.cuda.matmul.allow_tf32 = False
            torch.backends.cudnn.allow_tf32 = False
        self.model = TopKSAE(config).to(device)
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=config.learning_rate,
                                         betas=(config.beta1, config.beta2), eps=config.adam_epsilon,
                                         weight_decay=0, foreach=False)
        self.tokens_seen, self.steps = 0, 0
        self.last_fired = torch.zeros(config.d_sae, dtype=torch.int64, device=device)
        self.initial_statistics = None
        self.loss_scale = None
        self.failed = False

    @torch.no_grad()
    def _initialize(self, x):
        # Statistics use the first training minibatch only, in fp64 accumulation.
        mean = x.double().mean(dim=0)
        energy = float((x.double() - mean).square().mean())
        if not math.isfinite(energy) or energy <= 0:
            raise ValueError('positive finite initial training centered energy required')
        self.loss_scale = 1 / energy
        mean32 = mean.float()
        self.model.b_dec.copy_(mean32)
        self.model.b_enc.copy_(-(self.model.W_enc @ mean32))
        self.initial_statistics = {
            'source': 'first_training_minibatch_only', 'tokens': len(x),
            'centered_mean_square': energy, 'loss_scale': self.loss_scale,
            'mean_float32_sha256': hashlib.sha256(mean32.cpu().numpy().tobytes()).hexdigest(),
        }

    def step(self, x, *, first_position, split):
        """Train each accepted unique stream position once; final batch is short."""
        if self.failed:
            raise RuntimeError('failed training instance cannot be resumed or retried')
        if split != 'train' or type(first_position) is not int or first_position != self.tokens_seen:
            raise ValueError('training-only contiguous unreplayed stream positions required')
        x = self.model.checked_input(x)
        expected = min(self.config.batch_size, self.config.target_tokens - self.tokens_seen)
        if expected <= 0 or len(x) != expected:
            raise ValueError('exact full minibatch or final unpadded partial batch required')
        # Once numerical training starts, an operational failure poisons this
        # trainer; the Integrator's explicitly authorized stage rebuild is external.
        try:
            if self.initial_statistics is None:
                self._initialize(x)
            self.optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=x.device.type, enabled=False):
                pre = x @ self.model.W_enc.T + self.model.b_enc
                _finite(pre, 'encoder preactivations')
                z = self.model.sparse_topk(pre, self.config.k)
                reconstruction = self.model.decode(z)
                end = self.tokens_seen + len(x)
                fired = z.detach().gt(0).any(dim=0)
                next_last_fired = torch.where(fired, end, self.last_fired)
                dead = end - next_last_fired >= self.config.dead_after_tokens
                if self.timing_force_auxiliary:
                    dead = torch.ones_like(dead)
                main = (reconstruction - x).square().mean() * self.loss_scale
                aux = auxiliary_loss(pre, self.model.W_dec, x - reconstruction,
                                     dead, k=self.config.auxiliary_k, loss_scale=self.loss_scale)
                loss = main + self.config.auxiliary_weight * aux
                _finite(loss, 'training loss')
            loss.backward()
            self.model.project_decoder_gradient_()
            norm = torch.nn.utils.clip_grad_norm_(self.model.parameters(), self.config.grad_clip,
                                                 error_if_nonfinite=True, foreach=False)
            self.optimizer.step()
            self.model.project_decoder_()
            for name in PARAMETER_KEYS:
                _finite(getattr(self.model, name), name)
            self.last_fired = next_last_fired
            self.tokens_seen, self.steps = end, self.steps + 1
            return {'tokens_seen': end, 'step': self.steps, 'batch_tokens': len(x),
                    'loss': float(loss.detach()), 'main_loss': float(main.detach()),
                    'auxiliary_loss': float(aux.detach()), 'dead_for_aux': int(dead.sum()),
                    'gradient_norm_before_clip': float(norm)}
        except Exception:
            self.failed = True
            raise

    def _require_complete(self):
        if self.failed or self.timing_force_auxiliary or self.tokens_seen != self.config.target_tokens:
            raise ValueError('only a successful complete single pass can emit a checkpoint')

    def checkpoint_tensors(self):
        """Exactly four CPU fp32 tensors, compatible with QwenScopeSAE(params,k)."""
        self._require_complete()
        return {name: getattr(self.model, name).detach().cpu().contiguous().clone()
                for name in PARAMETER_KEYS}

    def completed_manifest(self):
        self._require_complete()
        return {'experiment': 'E35', 'status': 'COMPLETE', 'synthetic': self.synthetic,
                'config': asdict(self.config), 'training_tokens': self.tokens_seen,
                'optimizer_updates': self.steps, 'checkpoint_selection': 'final_only',
                'data_passes': 1, 'replayed_positions': 0,
                'initial_statistics': dict(self.initial_statistics),
                'normalization': dict(NORMALIZATION_MANIFEST)}
