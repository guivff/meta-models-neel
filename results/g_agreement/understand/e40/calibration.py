"""E40 §142 clarification1; calibration-only constants and unchanged gate rules."""
import math
import numpy as np
from e40_common import dump_new, sha
from gate_math import GateAccumulator

CALIBRATION_TOKENS = 1_000_000
D_MODEL = 5120


def norms64(x):
    x = np.asarray(x)
    if x.ndim != 2 or not len(x) or x.dtype.kind != 'f' or not np.isfinite(x).all():
        raise ValueError('finite nonempty floating residual matrix required')
    return np.sqrt(np.einsum('ij,ij->i', x, x, dtype=np.float64))


def calibrate(norms, *, d_model=D_MODEL, expected=CALIBRATION_TOKENS):
    a = np.asarray(norms, dtype=np.float64)
    if (a.shape != (expected,) or expected < 1 or d_model < 1
            or not np.isfinite(a).all() or (a < 0).any()):
        raise ValueError('complete fixed calibration population required')
    median = float(np.median(a))
    threshold = 10 * median
    retained = a <= threshold
    mean = float(a[retained].mean()) if retained.any() else 0.
    if not math.isfinite(mean) or mean <= 0:
        raise ValueError('positive calibration mean required')
    return {'experiment': 'E40', 'schema': 'E40_CALIBRATION_V1',
            'population_tokens': expected, 'position_zero_included': False,
            'median_raw_norm': median, 'outlier_threshold_raw_norm': threshold,
            'mean_raw_norm_after_outlier_exclusion': mean,
            'scale': math.sqrt(d_model) / mean, 'd_model': d_model,
            'outlier_rule': 'raw_norm > 10 * median; equality retained',
            'calibration_outliers': int((~retained).sum()),
            'calibration_retained': int(retained.sum()),
            'norm_arithmetic': 'float64 Euclidean norm; median midpoint; arithmetic mean',
            'heldout_statistics_used': False}


def seal_calibration(out, record):
    path = out / 'CALIBRATION.json'
    dump_new(path, record)
    dump_new(out / 'CALIBRATION_SEAL.json', {'status': 'COMPLETE',
              'before_training_step': 1, 'files': {'CALIBRATION.json': sha(path)}})
    return sha(path)


def eligible(norms, positions, calibration):
    norms = np.asarray(norms, dtype=np.float64)
    positions = np.asarray(positions)
    if (norms.ndim != 1 or positions.shape != norms.shape or positions.dtype.kind not in 'iu'
            or (positions < 0).any() or not np.isfinite(norms).all() or (norms < 0).any()):
        raise ValueError('aligned finite raw norms and original document positions required')
    return (positions != 0) & (norms <= calibration['outlier_threshold_raw_norm'])


class FilteredGate(GateAccumulator):
    """Same pooled moments/strict thresholds as E35, on the registered retained set."""
    def result(self):
        if self.n_tokens <= 0 or self.n_tokens > 50000 or self._m2 <= 0:
            raise ValueError('nonempty positive-variance retained gate required')
        dead = int(self.d_sae - np.count_nonzero(self._active))
        fvu = self._squared_error / self._m2
        if not math.isfinite(fvu):
            raise ValueError('finite retained FVU required')
        return {'n_tokens': self.n_tokens, 'd_model': self.d_model, 'd_sae': self.d_sae,
                'squared_error': self._squared_error, 'total_variance': self._m2,
                'fvu': fvu, 'dead_latents': dead, 'dead_fraction': dead / self.d_sae,
                'fvu_pass': fvu <= .25, 'dead_pass': 10 * dead < self.d_sae,
                'passed': fvu <= .25 and 10 * dead < self.d_sae}
