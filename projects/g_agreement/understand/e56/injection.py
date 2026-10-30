"""E56 row 10: CPU input construction only; no reader imports or forwards."""
import hashlib
import importlib.util
import json
import time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
HERE = ROOT / 'results/g_agreement/understand/e56/nonJ_injection'

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def read(p):
    return json.loads(Path(p).read_text())

def dump(p, value):
    with Path(p).open('x') as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write('\n')

def verify(base, files):
    base = Path(base).resolve()
    for name, digest in files.items():
        path = (base / name).resolve()
        if not path.is_relative_to(base) or sha(path) != digest:
            raise ValueError('sealed member mismatch: ' + name)

def combine(directions, reconstruction, carriers):
    """Equal injection norms, retaining the original carrier in all three arms."""
    d = np.asarray(directions, dtype=np.float64)
    j = np.asarray(reconstruction, dtype=np.float64)
    c = np.asarray(carriers, dtype=np.float64)
    if d.shape != j.shape or c.shape != d.shape or d.ndim != 2:
        raise ValueError('direction/carrier shape')
    parts = np.stack([d, j, d - j], axis=1)
    norms = np.linalg.norm(parts, axis=2)
    if not np.isfinite(parts).all() or not np.isfinite(c).all() or np.any(norms <= 1e-8):
        raise ValueError('nonfinite or degenerate component; no fallback')
    target = np.linalg.norm(d, axis=1)
    delta = parts / norms[:, :, None] * target[:, None, None]
    injected = (c[:, None, :] + delta).astype(np.float32)
    if not np.allclose(np.linalg.norm(injected.astype(float) - c[:, None, :], axis=2), target[:, None], rtol=2e-5, atol=1e-5):
        raise ValueError('stored injection norm mismatch')
    return injected, delta.astype(np.float32), norms

def run():
    import subprocess
    import torch
    from safetensors import safe_open
    plan_path = HERE / 'PLAN.json'
    plan = read(plan_path)
    if subprocess.check_output(['git', 'show', 'HEAD:' + str(plan_path.relative_to(ROOT))], cwd=ROOT) != plan_path.read_bytes():
        raise ValueError('plan must be committed first')
    for p, h in plan['pins'].items():
        if sha(p) != h:
            raise ValueError('frozen input/source changed: ' + p)
    lens = Path(plan['wlens_root'])
    bank = lens / 'cache/g_agreement/understand/e52/E36-input'
    verify(bank, read(bank / 'INPUT_SEAL.json')['files'])
    basis = read(lens / 'results/g_agreement/understand/e52/BASIS_SEAL_2026-10-27.json')
    verify(lens / 'cache/g_agreement/understand/e52', basis['files'])
    assets = read(lens / 'results/g_agreement/understand/e52/BASIS_INPUTS_2026-10-27.json')
    for f in assets['files'].values():
        if sha(f['path']) != f['sha256']:
            raise ValueError('basis asset changed')
    lock = ROOT / 'cache/g_agreement/understand/e56/INJECTION_ONCE.json'
    lock.parent.mkdir(parents=True, exist_ok=True)
    dump(lock, {'plan_sha256': sha(plan_path), 'retry': False})
    start = time.monotonic()
    try:
        torch.set_num_threads(8)
        src = ROOT / plan['suraj_source']
        spec = importlib.util.spec_from_file_location('e56_nonj_lib', src)
        lib = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(lib)
        h = np.load(bank / 'acts44.npy', allow_pickle=False)
        items = read(bank / 'items.json')
        if h.shape != (len(items), 5120) or not np.isfinite(h).all():
            raise ValueError('capture shape/finite')
        directions, carriers, records, means = [], [], [], []
        for row in plan['rows']:
            group = [np.array([i for i, x in enumerate(items) if x['feature'] == row and x['y'] == y]) for y in (1, 0)]
            if any(len(g) != 42 for g in group):
                raise ValueError('42 test items per class required')
            mu = np.stack([h[g].astype(np.float64).mean(0) for g in group])
            means.append(mu)
            carrier = mu.mean(0)
            for v, value in enumerate(plan['rows'][row]):
                directions.append(mu[v] - carrier)
                carriers.append(carrier)
                records.append({'row': row, 'variant': 'AB'[v], 'value': value,
                                'source_item_ids': [items[i]['id'] for i in group[v]]})
        d = np.array(directions, dtype=np.float32)
        carriers = np.array(carriers, dtype=np.float32)
        j = lib.load_jlens_layers(assets['files']['jlens']['path'], [44])[44]
        with safe_open(assets['files']['unembedding_shard']['path'], framework='pt', device='cpu') as f:
            wu = f.get_tensor('lm_head.weight')
        with safe_open(assets['files']['norm_shard']['path'], framework='pt', device='cpu') as f:
            gain = 1 + f.get_tensor('model.language_model.norm.weight').float()
        with torch.inference_mode():
            atoms, atom_norms = lib.jlens_atoms(j, wu, gain, chunk=4096)
            # Positive scaling preserves pursuit; both class signs are pursued independently.
            unit = torch.from_numpy(d / np.linalg.norm(d, axis=1, keepdims=True))
            idx, coef, reconstruction = lib.nn_pursuit(unit, atoms, k=16, refine_steps=6)
            rec = reconstruction.numpy() * np.linalg.norm(d, axis=1, keepdims=True)
        injected, delta, norms = combine(d, rec, carriers)
        np.savez_compressed(HERE / 'INPUT_VECTORS.npz',
            activations=injected.reshape(-1, 5120), injection_deltas=delta,
            carriers=carriers, class_means=np.array(means, dtype=np.float32),
            directions=d, j_components=rec, nonj_residuals=d-rec,
            pursuit_indices=idx.numpy(), pursuit_coefficients_unit=coef.numpy())
        entries = []
        for i, record in enumerate(records):
            for k, arm in enumerate(plan['arms']):
                entries.append(dict(record, index=i*3+k, arm=arm,
                    id='e56.nonJ_injection.'+record['row']+'.'+record['variant']+'.'+arm))
        dump(HERE / 'ITEMS.json', {'layer': 44, 'activation_file': 'INPUT_VECTORS.npz',
            'activation_key': 'activations', 'readers': ['Oracle_lens', 'NLA'], 'items': entries,
            'normalization': 'none beyond each readers frozen native adapter',
            'carrier_controls': {'array': 'carriers', 'unique_indices': list(range(0, 12, 2))},
            'independent_units': '6 rows; 2 class directions each; not 40 independent text items'})
        dump(HERE / 'BUILD_RECEIPT.json', {'status': 'SEALED_INPUTS_NO_READER_RUN',
            'plan_sha256': sha(plan_path), 'wall_seconds': time.monotonic()-start,
            'gpu_hours': 0, 'reader_forwards': 0, 'directions': 12, 'injection_inputs': 36,
            'raw_component_norms': norms.tolist(), 'target_norms': np.linalg.norm(d, axis=1).tolist(),
            'pursuit_dictionary': 'all 248320 normalized rows of W_U diag(1+w) J44, bf16 per Suraj',
            'pursuit_k': 16, 'refine_steps': 6,
            'residual_caveat': 'd - nonnegative pursuit reconstruction; not orthogonal SVD projection'})
        files = ['PLAN.json', 'INPUT_VECTORS.npz', 'ITEMS.json', 'BUILD_RECEIPT.json']
        dump(HERE / 'INPUT_SEAL.json', {'files': {n: sha(HERE/n) for n in files},
            'experiment': 'E56', 'row': 'nonJ_injection', 'layer': 44})
        print('SEALED', sha(HERE / 'INPUT_SEAL.json'), flush=True)
    except Exception as exc:
        dump(HERE / 'FAILED.json', {'error': str(exc), 'retry': False})
        raise

if __name__ == '__main__':
    run()
