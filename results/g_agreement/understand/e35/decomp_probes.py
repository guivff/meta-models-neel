"""E35 dev-trained SAE-code probes; frozen 2026-10-25, no work at import.

The runtime caller must verify the passing SAE gate, committed rubric, and label
receipts before setting ``authorized=True``. All 25 rows use the fixed W1 library
logistic recipe, dev-only standardisation/fitting, and descriptive test AUROC.
No probe CI, decision threshold, hyperparameter search, or test-fold fitting is
introduced. Private truth metadata is supplied only by the authorized runtime.
"""
from __future__ import annotations

import hashlib
import sys
import types
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
SOURCE_DIR = Path('external/mats-nla-workspace/src/mats')
SOURCE_SHA256 = {
    'probes.py': '955a7b516d97bee88b149bee1b8a3d9cdffaa7ef1b407cdef5cc4159f4677ae7',
    'metrics.py': '17ff3b1467186a8c4e24e76ed52d2263b0201e651e2010d4b99bd47c25cda473',
}
ROWS = (
    'json_status', 'json_type', 'latex_environment', 'latex_role',
    'latex_section', 'latex_subject', 'list_depth', 'list_index',
    'list_priority', 'list_topic', 'prose_paren', 'prose_quote',
    'prose_sentence', 'prose_sentiment', 'prose_topic', 'python_argument',
    'python_comment', 'python_depth', 'python_error', 'python_indent',
    'python_string', 'table_column', 'table_role', 'table_row', 'table_status',
)
TERMS = ('h', 'window_loss', 'policy_loss')


def _binary(values):
    return all(isinstance(v, (int, np.integer)) and not isinstance(v, (bool, np.bool_))
               and v in (0, 1) for v in values)


def validate_production_metadata(metadata):
    """Require the complete frozen 25 x (84 dev + 84 test) W1 population.

Each row has id,row,split,label,cluster. The caller binds IDs and first-value-A
positive polarity to the frozen input seals; this function checks the grid.
"""
    if len(metadata) != 25 * 168 or any(not isinstance(r, dict) for r in metadata):
        raise ValueError('complete 4200-item metadata required')
    for record in metadata:
        if not {'id', 'row', 'split', 'label', 'cluster'} <= record.keys():
            raise ValueError('metadata fields missing')
        if any(not isinstance(record[k], str) or not record[k] for k in ('id', 'row', 'cluster')):
            raise ValueError('nonempty string IDs, rows, and clusters required')
        if record['split'] not in ('dev', 'test') or not _binary([record['label']]):
            raise ValueError('dev/test split and integer binary labels required')
    if len({r['id'] for r in metadata}) != len(metadata):
        raise ValueError('unique full item IDs required')
    if {r['row'] for r in metadata} != set(ROWS):
        raise ValueError('exact frozen 25 rows required')
    for row in ROWS:
        clusters = {}
        for split in ('dev', 'test'):
            selected = [r for r in metadata if r['row'] == row and r['split'] == split]
            if len(selected) != 84 or sum(r['label'] for r in selected) != 42:
                raise ValueError('each row requires balanced 42/42 labels in each 84-item split')
            clusters[split] = {r['cluster'] for r in selected}
        if clusters['dev'] & clusters['test']:
            raise ValueError('dev/test template clusters overlap within row')


def load_pinned_library(root=ROOT):
    """Execute only the two SHA-verified library sources, in an isolated package.

No existing ``mats`` installation or bytecode cache can substitute for the pinned
source. Recheck bytes on every call, even if this private package is already loaded.
"""
    root = Path(root).resolve()
    source = {}
    for filename, expected in SOURCE_SHA256.items():
        path = root / SOURCE_DIR / filename
        source[filename] = path.read_bytes()
        if hashlib.sha256(source[filename]).hexdigest() != expected:
            raise ValueError('pinned W1 source hash mismatch: ' + filename)
    package_name = '_e35_pinned_mats_' + hashlib.sha256(str(root).encode()).hexdigest()[:16]
    if package_name not in sys.modules:
        package = types.ModuleType(package_name)
        package.__path__ = [str(root / SOURCE_DIR)]
        sys.modules[package_name] = package
        try:
            for filename in ('metrics.py', 'probes.py'):
                name = package_name + '.' + filename[:-3]
                module = types.ModuleType(name)
                module.__file__ = str(root / SOURCE_DIR / filename)
                module.__package__ = package_name
                sys.modules[name] = module
                exec(compile(source[filename], module.__file__, 'exec'), module.__dict__)
        except BaseException:
            for name in (package_name + '.probes', package_name + '.metrics', package_name):
                sys.modules.pop(name, None)
            raise
    return sys.modules[package_name + '.probes'], sys.modules[package_name + '.metrics']


def densify_row(indices, values, item_indices, n_latents):
    """Densify only selected items from equal-shaped [items,k] sparse codes."""
    indices, values, selected = np.asarray(indices), np.asarray(values), np.asarray(item_indices)
    if (indices.ndim != 2 or indices.shape != values.shape
            or not np.issubdtype(indices.dtype, np.integer)):
        raise ValueError('matching [items,k] sparse arrays and integer indices required')
    if (not isinstance(n_latents, (int, np.integer)) or isinstance(n_latents, (bool, np.bool_))
            or n_latents < 1):
        raise ValueError('positive integer latent count required')
    if (selected.ndim != 1 or not np.issubdtype(selected.dtype, np.integer)
            or len(selected) == 0 or len(np.unique(selected)) != len(selected)
            or np.any(selected < 0) or np.any(selected >= len(indices))):
        raise ValueError('nonempty unique valid item indices required')
    selected_indices, selected_values = indices[selected], values[selected]
    if (np.any(selected_indices < 0) or np.any(selected_indices >= n_latents)
            or not np.isfinite(selected_values).all() or np.any(selected_values < 0)):
        raise ValueError('finite nonnegative codes with in-range indices required')
    if selected_indices.shape[1] > 1 and np.any(np.diff(np.sort(selected_indices, axis=1), axis=1) == 0):
        raise ValueError('duplicate latent indices within an item')
    dense = np.zeros((len(selected), n_latents), dtype=np.float32)
    dense[np.arange(len(selected))[:, None], selected_indices] = selected_values
    if not np.isfinite(dense).all():
        raise ValueError('codes overflow float32')
    return dense


def fit_row_probe(dev_x, dev_y, test_x, test_y, *, authorized=False, root=ROOT):
    """Fit one fixed dev-only model and return descriptive held-out AUROC.

Small synthetic inputs are supported for CPU tests; the full runtime must first
call validate_production_metadata (run_per_row_probes does so automatically).
"""
    if authorized is not True:
        raise PermissionError('gate PASS and frozen rubric/label receipts must be verified first')
    dx, tx = np.asarray(dev_x), np.asarray(test_x)
    dy, ty = np.asarray(dev_y), np.asarray(test_y)
    if (dx.ndim != 2 or tx.ndim != 2 or dx.shape[1] != tx.shape[1] or dx.shape[1] == 0
            or len(dx) < 2 or len(tx) < 2 or dy.shape != (len(dx),) or ty.shape != (len(tx),)
            or not _binary(dy) or not _binary(ty) or set(dy.tolist()) != {0, 1}
            or set(ty.tolist()) != {0, 1} or not np.isfinite(dx).all() or not np.isfinite(tx).all()
            or np.any(dx < 0) or np.any(tx < 0)):
        raise ValueError('finite nonnegative matching codes and both binary classes required')
    probes, metrics = load_pinned_library(root)
    import torch
    dx_tensor, tx_tensor = torch.as_tensor(dx, dtype=torch.float32), torch.as_tensor(tx, dtype=torch.float32)
    if not torch.isfinite(dx_tensor).all() or not torch.isfinite(tx_tensor).all():
        raise ValueError('codes overflow float32')
    model = probes.fit_logreg(dx_tensor, torch.as_tensor(dy), lam=1e-3, iters=200)
    scores = model.decision(tx_tensor).detach().cpu().numpy()
    if not np.isfinite(scores).all():
        raise ValueError('nonfinite fitted probe scores')
    return {'auroc': metrics.auroc(scores[ty == 1], scores[ty == 0]),
            'n_dev': len(dx), 'n_test': len(tx), 'n_latents': dx.shape[1],
            'lam': 1e-3, 'iters': 200, 'fit_split': 'dev', 'evaluation_split': 'test',
            'descriptive_only': True}


def run_per_row_probes(metadata, codes_by_term, n_latents, *, authorized=False, root=ROOT):
    """Fit 75 frozen models; densify at most one row/term's dev and test codes."""
    if authorized is not True:
        raise PermissionError('gate PASS and frozen rubric/label receipts must be verified first')
    validate_production_metadata(metadata)
    if set(codes_by_term) != set(TERMS):
        raise ValueError('exact h/window_loss/policy_loss sparse code terms required')
    for pair in codes_by_term.values():
        if len(pair) != 2 or len(pair[0]) != len(metadata) or len(pair[1]) != len(metadata):
            raise ValueError('sparse code arrays must align with complete metadata')
    reports = []
    for row in ROWS:
        dev = np.asarray([i for i, r in enumerate(metadata) if r['row'] == row and r['split'] == 'dev'])
        test = np.asarray([i for i, r in enumerate(metadata) if r['row'] == row and r['split'] == 'test'])
        dev_y, test_y = [metadata[i]['label'] for i in dev], [metadata[i]['label'] for i in test]
        for term in TERMS:
            indices, values = codes_by_term[term]
            dev_x = densify_row(indices, values, dev, n_latents)
            test_x = densify_row(indices, values, test, n_latents)
            result = fit_row_probe(dev_x, dev_y, test_x, test_y, authorized=True, root=root)
            reports.append({'row': row, 'term': term, **result})
            del dev_x, test_x
    return reports
