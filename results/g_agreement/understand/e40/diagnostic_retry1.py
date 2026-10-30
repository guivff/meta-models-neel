"""E40(a): once-only descriptive CPU diagnostic of both sealed E35 SAEs."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import time
import numpy as np
from e40_common import HERE, ROOT, E35, read, sha, dump_new, verify_files

TRANSFER = 'cache/g_agreement/understand/e35/gate-rerun1-20261025/833ksjl7c6sxie'
FALLBACK = 'cache/g_agreement/understand/e35/training-20261025/xts9pkxii8jlqn'


def metadata(sample):
    positions, domains, ids = [], [], []
    for document in sample['documents']:
        for position in document['positions']:
            positions.append(position); domains.append(document['domain'])
            ids.append([document['id'], position])
    if len(ids) != 50000 or len({tuple(i) for i in ids}) != 50000:
        raise ValueError('unchanged unique 50000-token gate population required')
    return np.array(positions), np.array(domains), ids


def strata(h, positions, domains):
    """Independent marginal bins; exact equal-frequency deciles, stable tie order."""
    if h.ndim != 2 or len(h) != len(positions) or len(h) != len(domains) or not len(h):
        raise ValueError('aligned nonempty gate metadata required')
    norms = np.sqrt(np.einsum('ij,ij->i', h, h, dtype=np.float64))
    if not np.isfinite(norms).all():
        raise ValueError('finite raw norms required')
    order = np.argsort(norms, kind='stable')
    deciles = np.empty(len(h), dtype=np.int64)
    deciles[order] = np.minimum(np.arange(len(h)) * 10 // len(h), 9)
    groups = {'all': np.ones(len(h), dtype=bool),
              'position:0': positions == 0,
              'position:1-7': (positions >= 1) & (positions <= 7),
              'position:8+': positions >= 8}
    groups.update({f'norm_decile:{i+1}': deciles == i for i in range(10)})
    groups.update({'domain:' + domain: domains == domain for domain in sorted(set(domains))})
    return norms, groups


class Summaries:
    def __init__(self, h, groups, d_sae):
        self.groups = groups
        self.active = {name: np.zeros(d_sae, dtype=bool) for name in groups}
        self.errors = {name: 0. for name in groups}
        self.stats = {}
        global_mean = np.asarray(h, dtype=np.float64).mean(axis=0)
        for name, mask in groups.items():
            x = np.asarray(h[mask], dtype=np.float64)
            if len(x):
                mean = x.mean(axis=0)
                centered = float(np.square(x - mean).sum())
                global_centered = float(np.square(x - global_mean).sum())
            else:
                centered = global_centered = 0.
            self.stats[name] = dict(n_tokens=int(mask.sum()), total_variance=centered,
                                   variance_about_global_mean=global_centered)

    def update(self, start, h, r, indices, values):
        if (h.shape != r.shape or indices.shape != values.shape or len(indices) != len(h)
                or not np.isfinite(r).all() or not np.isfinite(values).all() or (values < 0).any()):
            raise ValueError('finite aligned reconstruction and sparse codes required')
        error = np.square(h.astype(np.float64) - r.astype(np.float64)).sum(axis=1)
        end = start + len(h)
        for name, mask in self.groups.items():
            selected = mask[start:end]
            self.errors[name] += float(error[selected].sum())
            self.active[name][indices[selected][values[selected] > 0]] = True

    def result(self):
        result = {}
        for name, stat in self.stats.items():
            n = stat['n_tokens']; total = stat['total_variance']; error = self.errors[name]
            dead = int((~self.active[name]).sum()); width = len(self.active[name])
            result[name] = dict(stat, squared_error=error,
                fvu=error / total if n and total > 0 else None,
                dead_latents=dead if n else None,
                dead_fraction=dead / width if n else None,
                d_sae=width)
        return result


def run(checkpoint, out, *, batch_size=128, threads=8):
    import torch
    from sae import QwenScopeSAE, PINNED_SHA256
    if not 1 <= batch_size <= 512 or not 1 <= threads <= 16:
        raise ValueError('bounded CPU batch/thread settings required')
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)
    freeze = read(HERE / 'DIAGNOSTIC_RERUN1_FREEZE.20261026.json')
    if any(sha(HERE / name) != digest for name, digest in freeze['files'].items()):
        raise ValueError('frozen diagnostic source changed')
    transfer, fallback = ROOT / TRANSFER, ROOT / FALLBACK
    ts = verify_files(transfer / 'final', arrays=transfer / 'arrays')
    fs = verify_files(fallback / 'final', arrays=fallback / 'arrays')
    if ts['status'] != 'FAIL' or fs['status'] != 'FAIL':
        raise ValueError('two sealed scientific E35 failures required')
    if sha(checkpoint) != PINNED_SHA256:
        raise ValueError('exact pinned transfer checkpoint required')
    sample = read(E35 / 'GATE_SAMPLE.json')
    if sha(E35 / 'GATE_SAMPLE.json') != 'dff73a3a83b76a6de4a5a2cbf2fe909a14a6888eaa9b91eeca6df849323fc593':
        raise ValueError('sample changed')
    positions, domains, ids = metadata(sample)
    h = np.load(transfer / 'arrays/h.npy', mmap_mode='r', allow_pickle=False)
    saved_r = np.load(transfer / 'arrays/reconstruction.npy', mmap_mode='r', allow_pickle=False)
    if h.shape != (50000, 5120) or saved_r.shape != h.shape:
        raise ValueError('sealed gate residual dimensions required')
    out = Path(out).resolve()
    if not out.is_relative_to((ROOT / 'cache/g_agreement/understand/e40').resolve()):
        raise ValueError('E40 cache output required')
    if out.exists():
        raise FileExistsError('diagnostic output already exists')
    guard = ROOT / 'cache/g_agreement/understand/e40/diagnostic-rerun1.RUN_ONCE.json'
    guard.parent.mkdir(parents=True, exist_ok=True)
    dump_new(guard, {'experiment': 'E40', 'date': '2026-10-26',
                     'plan_sha256': sha(HERE / 'DIAGNOSTIC_PLAN.20261026.json')})
    out.mkdir(parents=True)
    norms, groups = strata(h, positions, domains)
    results = {}
    for label, weights, k in [('transfer', Path(checkpoint), 50),
                             ('fallback', fallback / 'arrays/layer44.fallback.sae.pt', 64)]:
        print('CPU_DIAGNOSTIC_BEGIN', label, flush=True)
        params = torch.load(weights, map_location='cpu', weights_only=True)
        sae = QwenScopeSAE(params, k=k)
        del params
        summary = Summaries(h, groups, sae.d_sae)
        started = time.monotonic()
        with torch.inference_mode():
            for start in range(0, len(h), batch_size):
                x = torch.from_numpy(np.array(h[start:start+batch_size], copy=True))
                pre = x @ sae.W_enc.T + sae.b_enc
                if not torch.isfinite(pre).all():
                    raise ValueError('nonfinite encoder output')
                values, indices = torch.topk(torch.relu(pre), k, dim=-1)
                if label == 'transfer':
                    r = saved_r[start:start+len(x)]
                else:
                    z = torch.zeros_like(pre).scatter_(-1, indices, values)
                    r = sae.decode(z).numpy()
                summary.update(start, x.numpy(), r, indices.numpy(), values.numpy())
                if start % (batch_size * 25) == 0:
                    print('CPU_DIAGNOSTIC_PROGRESS', label, start+len(x), flush=True)
        tables = summary.result()
        gate = read((transfer if label == 'transfer' else fallback) / 'final/GATE_RESULT.json')
        expected = gate['metrics']
        parity = dict(fvu_abs_difference=abs(tables['all']['fvu']-expected['fvu']),
                      dead_count_difference=tables['all']['dead_latents']-expected['dead_latents'])
        # Scientific reporting retains the original sealed global values beside
        # CPU-derived firing sets; no diagnostic is used to alter E40 design.
        if parity['fvu_abs_difference'] > 1e-5:
            raise ValueError('CPU reconstruction does not reproduce sealed global FVU')
        results[label] = dict(groups=tables, sealed_global=expected,
                              cpu_reproduction=parity, cpu_seconds=time.monotonic()-started)
        del sae, pre, x, values, indices, summary
        print('CPU_DIAGNOSTIC_COMPLETE', label, flush=True)
    norm_bins = {name: dict(min=float(norms[mask].min()), max=float(norms[mask].max()))
                 for name, mask in groups.items() if mask.any()}
    result = {'experiment': 'E40', 'part': 'a', 'date': '2026-10-26',
              'descriptive_only': True, 'design_changes_from_diagnostic': False,
              'plan_sha256': sha(HERE / 'DIAGNOSTIC_PLAN.20261026.json'),
              'source_freeze_sha256': sha(HERE / 'DIAGNOSTIC_RERUN1_FREEZE.20261026.json'),
              'transfer_seal_sha256': sha(transfer / 'final/OUTPUT_SEAL.json'),
              'fallback_seal_sha256': sha(fallback / 'final/OUTPUT_SEAL.json'),
              'transfer_checkpoint_sha256': sha(checkpoint),
              'token_order_sha256': __import__('hashlib').sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest(),
              'norm_ranges': norm_bins, 'saes': results,
              'cpu_threads': threads, 'batch_size': batch_size, 'new_gpu_hours': 0}
    dump_new(out / 'RESULTS.json', result)
    dump_new(out / 'OUTPUT_SEAL.json', {'status': 'COMPLETE', 'files': {'RESULTS.json': sha(out / 'RESULTS.json')}})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--transfer-checkpoint', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    run(args.transfer_checkpoint, args.out)
if __name__ == '__main__':
    main()
