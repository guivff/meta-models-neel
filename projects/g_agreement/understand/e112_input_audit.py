"""Read-only check of the existing canonical E112 vectors; never builds a bank."""
import ast
from pathlib import Path
import numpy as np
from projects.g_agreement.readerbench.io import read, sha, verify
from projects.g_agreement.readerbench.scoring import require

ROOT = Path(__file__).resolve().parents[3]
ORIGINAL = Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-blindspot-internals/projects/g_agreement/understand/e80c/build.py')
ORIGINAL_SHA = '4ebb9cdd8b6c6d53089edacfe2d34cd1ef6e89b116af769d2265ff3626ca940a'
CANONICAL = ROOT.parent / 'outputs/e112-vectors-v1/vectors'
VECTOR_SHA = 'a356cc5a0a96dac3a12c6fbcfa9a8feafc690420ccf6ef5c7f17e684b37e559d'


def transform():
    require(sha(ORIGINAL) == ORIGINAL_SHA, 'frozen original E80c builder')
    nodes = [x for x in ast.parse(ORIGINAL.read_text()).body if isinstance(x, ast.FunctionDef) and x.name == 'transform']
    require(len(nodes) == 1, 'one original pure transform')
    env = {'np': np}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<original E80c transform>', 'exec'), env)
    return env['transform']


def reference(h, q):
    require(h.ndim == 2 and q.shape == (h.shape[1], 1) and np.isfinite(h).all() and np.isfinite(q).all(), 'finite single-column transform')
    mu = h.astype(np.float64).mean(axis=0)
    ablated, projected = transform()(h, mu, q.astype(np.float64))
    return ablated.astype(np.float32), projected, mu


def audit():
    selected_path = ROOT / 'results/g_agreement/understand/e112/K_SELECTION.json'
    selected = read(selected_path)
    require(selected['k'] == 1, 'committed k1 freeze')
    for key in ('PCA384','J384','capture_seal','acts44'):
        require(sha(selected['inputs'][key]['path']) == selected['inputs'][key]['sha256'], 'original ' + key)
    cap_path = Path(selected['inputs']['capture_seal']['path'])
    verify(cap_path, selected['inputs']['capture_seal']['sha256'])
    seal = verify(CANONICAL / 'VECTOR_SEAL.json', VECTOR_SHA)
    require(seal['k_selection_sha256'] == sha(selected_path) and seal['n_items'] == 518 and seal['n_vectors'] == 1036, 'canonical complete frozen grid')
    q = np.load(selected['inputs']['PCA384']['path'], allow_pickle=False)[:, :1].astype(np.float64)
    require(np.array_equal(q, np.load(CANONICAL / 'PCA1.npy', allow_pickle=False)), 'exact first saved column; no refit/rescaling')
    diagnostics = {}
    for block in (44,42):
        h = np.load(cap_path.parent / f'acts{block}.npy', allow_pickle=False)
        require(h.shape == (518,5120) and h.dtype == np.float32, 'original site capture')
        expected, projected, mu = reference(h, q)
        require(np.array_equal(mu, np.load(CANONICAL / f'mu{block}.npy', allow_pickle=False)), 'own-site original mean')
        require(np.array_equal(expected, np.load(CANONICAL / f'PCA1_ablated{block}.npy', allow_pickle=False)), 'all 518 exact fp32 vectors')
        centred = h.astype(np.float64) - mu
        ratio = np.linalg.norm(expected.astype(np.float64), axis=1) / np.linalg.norm(h.astype(np.float64), axis=1)
        diagnostics[str(block)] = dict(vectors_verified=518, variance_removed=float(np.sum(projected ** 2)/np.sum(centred ** 2)),
                                      saved_fp32_norm_ratio_mean=float(ratio.mean()), saved_vector_sha256=sha(CANONICAL / f'PCA1_ablated{block}.npy'))
    return dict(status='CANONICAL_INPUTS_VERIFIED_REUSE_EXISTING', experiment='E112', k=1,
                canonical_vector_seal_path=str(CANONICAL / 'VECTOR_SEAL.json'), canonical_vector_seal_sha256=VECTOR_SHA,
                k_selection_sha256=sha(selected_path), original_transform_sha256=ORIGINAL_SHA, per_block=diagnostics,
                new_production_inputs=0, new_PCA_fits=0, reader_calls=0, GPU_calls=0, labels_exported=False)
