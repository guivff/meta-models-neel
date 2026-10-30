"""Post-hoc E26 reward geometry and tokenization audit; CPU, no model calls."""
import argparse
import ast
import __future__
import hashlib
import time
from collections import Counter
from pathlib import Path

import numpy as np

from .cpu import ROOT, dump, read, rows, seal, sha, verify
from .e26_bank import FEATURES
from .e26_metrics import item_measures, summarize

AUDIT = ROOT / 'results/g_agreement/understand/e26/reward_audit'
EVIDENCE = AUDIT / 'evidence/olens_draft'
REGISTERED_SEAL = '9efc74fdd08870fb188b35f718b88155362cc422a53d6d545871c7dab32d4240'


def pinned_function(path, name, namespace):
    """Execute only one dependency-light function from the verified pinned source."""
    tree = ast.parse(path.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec',
                 flags=__future__.annotations.compiler_flag), namespace)
    return namespace[name]


def source_checks():
    manifest = read(AUDIT / 'PINNED_TREE.json')
    index = {r['path']: r for r in manifest['files']}
    checked = {}
    for p in sorted(EVIDENCE.rglob('*')):
        if not p.is_file() or '__pycache__' in p.parts:
            continue
        rel = p.relative_to(EVIDENCE).as_posix()
        data = p.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if blob != index[rel]['git_blob_sha']:
            raise ValueError(f'pinned source mismatch: {rel}')
        checked[rel] = {'git_blob_sha': blob, 'sha256': sha(p)}
    return checked


def one_atom_fve(recon_w, targets_w):
    """Exact one-atom NNLS geometry; negative alignment is clipped to zero."""
    x = np.asarray(recon_w, dtype=np.float64)
    h = np.asarray(targets_w, dtype=np.float64)
    if not np.isfinite(x).all() or not np.isfinite(h).all():
        raise ValueError('nonfinite whitened vectors')
    xn = np.linalg.norm(x, axis=1)
    hn = np.linalg.norm(h, axis=1)
    if (xn <= 0).any() or (hn <= 0).any():
        raise ValueError('degenerate vectors outside analytic shortcut domain')
    return np.maximum((h / hn[:, None]) @ (x / xn[:, None]).T, 0.) ** 2


def token_audit(records, tokenizer):
    ns = {}
    exec(compile((EVIDENCE / 'src/oracle_lens/readout_text.py').read_text(), 'readout_text.py', 'exec'), ns)
    clean = ns['strip_scaffolding']
    split = pinned_function(EVIDENCE / 'src/oracle_lens/pipeline/rl_reward.py', 'split_bullets',
                            {'prepare_reward_text': clean})
    special = set(tokenizer.all_special_ids)
    def tokens(text):
        return tuple(tokenizer(text, add_special_tokens=False)['input_ids'])
    original = {r['id']: tokens(r['text']) for r in records}
    lookup = {}
    for r in records:
        lookup.setdefault(original[r['id']], []).append(r['id'])
    details = []
    for r in records:
        bullets = split(r['text'], 4)
        ids = [tuple(t for t in tokens(clean(b)) if t not in special)[:64] for b in bullets]
        ids = [v for v in ids if v]
        matches = [lookup.get(v, []) for v in ids]
        details.append({'id': r['id'], 'category': r['category'], 'feature': r['feature'],
                        'n_bullets': len(ids), 'all_bullets_available': bool(ids) and all(matches),
                        'same_single_input': len(ids) == 1 and ids[0] == original[r['id']],
                        'missing_bullets': sum(not m for m in matches),
                        'matching_sealed_ids': matches,
                        'original_tokens': len(original[r['id']]),
                        'reward_bullet_tokens': [len(v) for v in ids]})
    return {'parser_lineage': 'pinned legacy LC parser; s3d wrapper not present',
            'k_max': 4, 'span_width': 64, 'n_candidates': len(details),
            'same_single_input': sum(r['same_single_input'] for r in details),
            'all_bullets_available': sum(r['all_bullets_available'] for r in details),
            'missing_candidate_counts_by_category': dict(Counter(r['category'] for r in details if not r['all_bullets_available'])),
            'multi_bullet_candidates': sum(r['n_bullets'] > 1 for r in details),
            'details': details}


def numeric_check():
    import torch
    p = EVIDENCE / 'src/oracle_lens/core/nnomp.py'
    ns = {'torch': torch}
    pinned_function(p, '_nnls_batched', ns)
    nnls_refit = pinned_function(p, 'nnls_refit', ns)
    rng = np.random.default_rng(9)
    x = rng.normal(size=(32, 7)); h = rng.normal(size=(32, 7))
    x[0] = -h[0]; x[1] = h[1]
    x /= np.linalg.norm(x, axis=1, keepdims=True)
    _, fve = nnls_refit(torch.tensor(x[:, None]), torch.tensor(h), torch.ones(32, 1, dtype=torch.bool))
    err = float(np.abs(fve.numpy() - np.diag(one_atom_fve(x, h))).max())
    assert err < 1e-12
    # Orthogonal directions jointly explain all of [1,1], not the mean (0.5) of scores.
    _, joint = nnls_refit(torch.eye(2, dtype=torch.float64)[None], torch.ones(1, 2, dtype=torch.float64), torch.ones(1, 2, dtype=torch.bool))
    assert abs(float(joint[0]) - 1.) < 1e-12
    assert fve[0] == 0 and abs(float(fve[1]) - 1.) < 1e-12
    return {'one_atom_max_abs_error_vs_pinned_nnls': err, 'joint_orthogonal_FVE': float(joint[0]),
            'negative_alignment_FVE': float(fve[0]), 'n_random_fixtures': 32}


def main(a):
    started = time.monotonic()
    sources = source_checks()
    registered = ROOT / 'results/g_agreement/understand/e26/analysis'
    verify(registered)
    assert sha(registered / 'SCORE_SEAL.json') == REGISTERED_SEAL
    verify(a.inputs, 'INPUT_SEAL.json'); verify(a.collection)
    run = read(a.collection / 'run.json')
    assert run['status'] == 'COMPLETE'
    assert run['input_seal_sha256'] == sha(a.inputs / 'INPUT_SEAL.json')
    assert run['candidate_banks_sha256'] == sha(a.banks / 'PREPARATION.json')
    for path, digest in run['source_files'].items():
        assert sha(ROOT / path) == digest, path
    records = rows(a.inputs / 'texts.input.jsonl')
    assert read(a.collection / 'ids.json') == [r['id'] for r in records]
    recon = np.load(a.collection / 'recon.npy', allow_pickle=False)
    assert recon.shape == (836, 5120) and np.isfinite(recon).all()
    verify(a.whitener.parent)
    wm = read(a.whitener.parent / 'WHITENER.json')
    assert sha(a.whitener) == wm['export_sha256'] == '8ca79f211072d12a998793dba5cf9483e6af9bead4267fb1e481be8a821160b6'
    assert wm['moments_sha256'] == '178ceb36251e5e7ed2eb51aa54ccc4eac45dc928116b7498b46d22657a31c62a'
    assert wm['ridge_c'] == .1
    w = np.load(a.whitener, allow_pickle=False)
    def whiten(x):
        return (np.asarray(x, dtype=np.float32) - w['mu'].astype(np.float32)) @ w['w'].astype(np.float32).T
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained(a.tokenizer, local_files_only=True)
    token_report = token_audit(records, tokenizer)
    checks = numeric_check()
    a.out.mkdir(parents=True, exist_ok=False)
    dump(a.out / 'TOKENIZATION_AUDIT.json', token_report)
    dump(a.out / 'NUMERIC_CHECK.json', checks)
    xw = whiten(recon)
    index = {r['id']: i for i, r in enumerate(records)}
    result = {}
    for feature in FEATURES:
        folder = a.banks / feature
        verify(folder, 'BANK_SEAL.json')
        c = rows(folder / 'candidates.DO_NOT_STAGE.jsonl')
        public = rows(folder / 'candidates.input.jsonl')
        for private, p in zip(c, public, strict=True):
            assert all(private[k] == v for k, v in p.items())
            assert all(records[index[p['id']]][k] == v for k, v in p.items())
            assert records[index[p['id']]]['feature'] == feature
        items = rows(folder / 'items.DO_NOT_STAGE.jsonl')
        assert read(folder / 'ids.json') == [r['id'] for r in items]
        values = read(a.templates)[feature]['values']
        truth = [values.index(r['value']) for r in items]
        assert truth.count(0) == truth.count(1) == 40
        h = np.load(folder / 'acts44.npy', allow_pickle=False)
        scores = one_atom_fve(xw[[index[r['id']] for r in c]], whiten(h))
        im = item_measures(scores, [r['category'] for r in c], [r.get('value', -1) for r in c], truth)
        result[feature] = summarize(im, n_boot=2000, seed=20261025)
    out = {'status': 'POSTHOC_FIXED_VECTOR_ONE_ATOM_REWARD_GEOMETRY_ONLY',
           'exact_actual_reward_reranking': False,
           'reason': 'Published s3d/ptag RL wrapper absent from pin; parsed-bullet vectors not all present in sealed E26 collection.',
           'rows': result, 'registered_verdict_unchanged': True,
           'descriptive_states_joint_R1_R2': sum(result[f]['R1'] and result[f]['R2'] for f in FEATURES[:-1]),
           'descriptive_sentiment_joint_R1_R2': result['prose_sentiment']['R1'] and result['prose_sentiment']['R2']}
    dump(a.out / 'metrics.json', out)
    verify(registered)
    assert sha(registered / 'SCORE_SEAL.json') == REGISTERED_SEAL
    dump(a.out / 'RUN.json', {'status': 'COMPLETE_POSTHOC_SENSITIVITY_FULL_REWARD_NOT_IDENTIFIABLE',
         'wall_seconds': time.monotonic() - started, 'GPU_hours': 0, 'model_calls': 0,
         'registered_analysis_seal_sha256': REGISTERED_SEAL,
         'plan_sha256': sha(AUDIT / 'POSTHOC_PLAN.md'), 'script_sha256': sha(Path(__file__)),
         'input_seal_sha256': sha(a.inputs / 'INPUT_SEAL.json'),
         'collection_seal_sha256': sha(a.collection / 'SCORE_SEAL.json'),
         'whitener_export_sha256': sha(a.whitener), 'whitener_metadata': wm,
         'tokenizer_files': {p.name: sha(p) for p in a.tokenizer.iterdir() if p.name in ('tokenizer.json', 'tokenizer_config.json', 'config.json')},
         'sources': sources})
    seal(a.out, [p.name for p in a.out.iterdir() if p.is_file()], 'E26_POSTHOC_REWARD_GEOMETRY')
    print({k: v for k, v in token_report.items() if k != 'details'})
    print(out)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('inputs', 'banks', 'collection', 'whitener', 'tokenizer', 'templates', 'out'):
        p.add_argument('--' + name, type=Path, required=True)
    main(p.parse_args())
