"""E40 registered TopK configuration; unspecified E35 training choices reused."""
from dataclasses import dataclass, asdict
import math
from e40_common import E35
from fallback_sae import TrainConfig, SAETrainer, TopKSAE
from sae import QwenScopeSAE

@dataclass(frozen=True)
class E40Config(TrainConfig):
    d_sae: int = 65536
    k: int = 128
    target_tokens: int = 100_000_000
    seed: int = 20261026
    learning_rate: float = 2e-4

FIXED_CONFIG = E40Config()


class Trainer(SAETrainer):
    def __init__(self, *, scale, device='cuda', config=FIXED_CONFIG,
                 synthetic=False, timing_force_auxiliary=False):
        if not math.isfinite(scale) or scale <= 0:
            raise ValueError('fixed positive training-only scale required')
        if not synthetic and (config != FIXED_CONFIG or timing_force_auxiliary):
            raise ValueError('registered E40 configuration and ordinary AuxK only')
        # The inherited implementation permits alternative dimensions only in
        # its generic path; E40's production guard above replaces E35's guard.
        super().__init__(device=device, config=config, synthetic=True,
                         timing_force_auxiliary=timing_force_auxiliary)
        self.synthetic = synthetic is True
        self.scale = float(scale)

    def step(self, raw, *, first_position, split):
        return super().step(raw * self.scale, first_position=first_position, split=split)

    def completed_manifest(self):
        result = super().completed_manifest()
        result.update(experiment='E40', normalization={'input': 'raw_residual * fixed_scale',
                       'scale': self.scale, 'reconstruction': 'scaled_decoder_output / fixed_scale'})
        return result


class ScaledSAE:
    def __init__(self, params, scale, *, k=128, device='cpu'):
        if not math.isfinite(scale) or scale <= 0:
            raise ValueError('sealed positive scale required')
        self.core = QwenScopeSAE(params, k=k).to(device)
        self.scale = float(scale)
        self.d_model, self.d_sae, self.k = self.core.d_model, self.core.d_sae, self.core.k
    def encode(self, raw):
        return self.core.encode(raw * self.scale)
    def decode(self, z):
        return self.core.decode(z) / self.scale
    def raw_decoder_norms(self):
        from decomposition import decoder_column_norms
        return decoder_column_norms(self.core) / self.scale
