"""BRIEF_BLINDSPOT §§71–73/80: AR fidelity, actual residuals, and causal swaps.

All arithmetic is in raw block-44 activation space. Real collection requires the
shared compute receipt; W4 additionally requires P3's review of these exact bytes.
No model/official code is imported until a collection command passes admission.
Legacy decompose/kl_to remain for scaffold compatibility, not W2–W4 inference.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict
import json
from pathlib import Path
import time

from . import protocol as P

BRIEF = 'projects/g_agreement/BRIEF_BLINDSPOT.md'
P3_SOURCE_COMMIT = 'c176e2595564324eb919b242c59e13895086f944'
CAP_HOURS = {'fidelity': .3, 'residual': 2., 'swap': .5, 'sae': 1.5}
ARMS = ('swap', 'self', 'random', 'ar_only')
SITE = {'construction_block': 44, 'nla_native_block': 42, 'site': 'OFF-NATIVE'}
CONTEXTS = (
    'A reviewer is describing the current excerpt.',
    'This note records the state at the read position.',
    'An editor is inspecting the unfinished passage.',
    'The following observation concerns the current text.',
    'A reader is checking the current position.',
    'This annotation describes the excerpt as it stands.',
    'An analyst is examining the current passage.',
    'This report concerns the current read position.',
    'A writer is reviewing the unfinished excerpt.',
    'The observation below describes the current excerpt.',
)


def _tensor(value, name, ndim=2):
    import torch
    value = torch.as_tensor(value).detach().float().cpu()
    if value.ndim != ndim or not torch.isfinite(value).all() or not value.numel():
        raise ValueError(f'invalid {name}: expected finite nonempty {ndim}-D array')
    return value


def _binary(value, n):
    import numpy as np
    value = np.asarray(value)
    if value.shape != (n,) or not np.isin(value, [0, 1]).all() or len(np.unique(value)) != 2:
        raise ValueError('both binary classes required')
    return value.astype(int)


def freeze_text_records(definitions):
    """Exactly 2 phrasings × 10 neutral contexts × 2 values per feature.

    Value 1 always means the first (A) member of the upstream frozen value order.
    The value join is a separate DO_NOT_STAGE file; text IDs encode no value.
    """
    import numpy as np
    records, labels = [], []
    rng = np.random.default_rng(P.SEED)
    for feature, spec in sorted(definitions.items()):
        if spec['row_class'] not in ('count-like', 'state-like', 'semantic'):
            raise ValueError('unknown row class')
        values, descriptions = spec['values'], spec['descriptions']
        if len(values) != 2 or len(set(values)) != 2 or len(descriptions) != 2:
            raise ValueError('two frozen values/descriptions required')
        phrasings = spec.get('statement_pairs', [
            [f'The current excerpt has {d}.' for d in descriptions],
            [f'At the read position, the excerpt has {d}.' for d in descriptions],
        ])
        if len(phrasings) != 2 or any(len(pair) != 2 for pair in phrasings):
            raise ValueError('exactly two statement phrasing pairs required')
        if any(len({phrasings[p][side] for p in range(2)}) != 2 for side in range(2)):
            raise ValueError('statement phrasings must differ')
        grid = [(side, phrasing, context) for side in range(2) for phrasing in range(2) for context in range(10)]
        for serial, index in enumerate(rng.permutation(len(grid))):
            side, phrasing, context = grid[index]
            key = f'{feature}:ar:{serial:03d}'
            records.append({'id': key, 'feature': feature, 'text': CONTEXTS[context] + ' ' + phrasings[phrasing][side]})
            labels.append({'id': key, 'feature': feature, 'value': 1-side,
                           'value_name': values[side], 'phrasing': phrasing, 'context': context})
    return records, labels


def fidelity(ar_outputs, text_labels, h, y, direction, n_boot=2000, seed=P.SEED):
    """Signed projection ratio, never clipped or absolute-valued.

    Bootstrap the frozen texts within value/phrasing strata, holding the real
    class-mean denominator and the upstream raw-space direction fixed (§71).
    """
    import numpy as np
    rec, h, direction = _tensor(ar_outputs, 'AR outputs'), _tensor(h, 'activations'), _tensor(direction, 'direction', 1)
    if rec.shape[1] != h.shape[1] or direction.shape != (h.shape[1],) or float(direction.norm()) <= 1e-12:
        raise ValueError('direction/activation shape mismatch or degenerate direction')
    if len(text_labels) and isinstance(text_labels[0], dict):
        ty = _binary([r['value'] for r in text_labels], len(rec))
        phrases = np.asarray([r['phrasing'] for r in text_labels])
    else:
        ty = _binary(text_labels, len(rec))
        phrases = np.zeros(len(rec), dtype=int)
    y = _binary(y, len(h))
    # Normalisation is ratio-invariant and makes the degeneracy tolerance meaningful.
    direction = direction / direction.norm()
    hp, rp = (h @ direction).double().numpy(), (rec @ direction).double().numpy()
    denominator = float(hp[y == 1].mean() - hp[y == 0].mean())
    if abs(denominator) <= 1e-10 * max(1., float(np.abs(hp).max())):
        raise ValueError('degenerate real class-mean gap; fidelity is undefined')
    numerator = float(rp[ty == 1].mean() - rp[ty == 0].mean())
    strata = [np.flatnonzero((ty == side) & (phrases == phrasing))
              for side in (0, 1) for phrasing in np.unique(phrases)]
    if any(len(s) == 0 for s in strata) or n_boot < 1:
        raise ValueError('incomplete text/value/phrasing grid')
    rng = np.random.default_rng(seed)
    boot = []
    for _ in range(n_boot):
        idx = np.concatenate([rng.choice(s, size=len(s), replace=True) for s in strata])
        boot.append(float((rp[idx][ty[idx] == 1].mean() - rp[idx][ty[idx] == 0].mean()) / denominator))
    return {'fidelity': numerator / denominator, 'numerator': numerator, 'denominator': denominator,
            'ci95': np.quantile(boot, [.025, .975]).tolist(), 'n_texts': len(rec), 'n_real': len(h),
            'bootstrap': 'texts within value/phrasing; fixed direction and real gap', 'status': 'COMPLETE'}


def residual_activations(h, reconstructed):
    h, reconstructed = _tensor(h, 'activations'), _tensor(reconstructed, 'reconstructions')
    if h.shape != reconstructed.shape:
        raise ValueError('activation/reconstruction shape mismatch')
    return h - reconstructed


def swap_arms(h, reconstructed, pairs):
    """§73: same raw-space residual and recipient norm rule for all four arms."""
    import torch
    h, reconstructed = _tensor(h, 'activations'), _tensor(reconstructed, 'reconstructions')
    residual = residual_activations(h, reconstructed)
    if not pairs:
        raise ValueError('empty swap pairs')
    for row in pairs:
        if any(type(row[k]) is not int or not 0 <= row[k] < len(h) for k in ('recipient', 'donor', 'random')):
            raise ValueError('invalid pair index')
    i = [p['recipient'] for p in pairs]
    j = [p['donor'] for p in pairs]
    random = [p['random'] for p in pairs]
    norms = h[i].norm(dim=-1, keepdim=True)
    arms = {'swap': reconstructed[i] + residual[j],
            'self': reconstructed[i] + residual[i],
            'random': reconstructed[i] + residual[random],
            'ar_only': reconstructed[i]}
    if (norms <= 1e-12).any():
        raise ValueError('degenerate recipient norm')
    for name, v in arms.items():
        n = v.norm(dim=-1, keepdim=True)
        if (n <= 1e-12).any() or not torch.isfinite(n).all():
            raise ValueError(f'degenerate {name} swap norm')
        arms[name] = v * (norms / n)
    return arms


def score_swaps(nla, h, reconstructed, pairs, templates, batch=8):
    """Use the exact W-core scorer, prefix, candidate order, and frozen phrasings."""
    import torch
    from mats.readers.nla import paired_logodds_templates
    arms = swap_arms(h, reconstructed, pairs)
    if len({p['id'] for p in pairs}) != len(pairs):
        raise ValueError('duplicate pair IDs')
    result = []
    for feature in sorted({p['feature'] for p in pairs}):
        frozen = templates[feature]['nla']
        if len(frozen) < 2 or len({tuple(p) for p in frozen}) != len(frozen) or any(len(p) != 2 for p in frozen):
            raise ValueError('at least two distinct frozen NLA phrasing pairs required')
        indices = [k for k, p in enumerate(pairs) if p['feature'] == feature]
        for arm in ARMS:
            scores = paired_logodds_templates(nla, arms[arm][indices], frozen, batch=batch)
            if scores.shape != (len(frozen), len(indices)) or not torch.isfinite(scores).all():
                raise ValueError('invalid NLA score shape/value')
            for k, index in enumerate(indices):
                result.append({'id': pairs[index]['id'], 'feature': feature, 'arm': arm,
                               'scores': scores[:, k].tolist(), **SITE})
    return result


def _correlation(rows, x, y, n_boot=2000, seed=P.SEED):
    import numpy as np
    from scipy.stats import spearmanr
    a, b = np.asarray([r[x] for r in rows]), np.asarray([r[y] for r in rows])
    if len(a) < 3 or not np.isfinite(a).all() or not np.isfinite(b).all() or len(set(a)) < 2 or len(set(b)) < 2:
        return {'rho': None, 'ci95': [None, None], 'n': len(rows), 'status': 'NOT EVALUABLE'}
    rng = np.random.default_rng(seed)
    boot = []
    for _ in range(n_boot):
        idx = rng.integers(len(a), size=len(a))
        if len(set(a[idx])) > 1 and len(set(b[idx])) > 1:
            boot.append(float(spearmanr(a[idx], b[idx]).statistic))
    if not boot:
        return {'rho': None, 'ci95': [None, None], 'n': len(rows), 'status': 'NOT EVALUABLE'}
    return {'rho': float(spearmanr(a, b).statistic), 'ci95': np.quantile(boot, [.025, .975]).tolist(),
            'n': len(rows), 'n_boot_valid': len(boot), 'status': 'COMPLETE'}


def w2_decision(rows):
    import numpy as np
    rows = [r for r in rows if r['evaluable'] and r.get('fidelity') is not None]
    correlation = _correlation(rows, 'fidelity', 'oracle_auroc')
    status = 'NOT EVALUABLE'
    if correlation['rho'] is not None:
        status = 'CONFIRMED' if correlation['rho'] >= .5 and correlation['ci95'][0] > 0 else 'NOT MET'
    medians = {c: float(np.median([r['fidelity'] for r in rows if r['row_class'] == c]))
               for c in ('count-like', 'state-like', 'semantic') if any(r['row_class'] == c for r in rows)}
    return {'status': status, 'correlation': correlation, 'median_fidelity_by_class': medians}


def s2_decision(rows):
    rows = [dict(r, oracle_gap=r['probe_auroc']-r['oracle_auroc'])
            for r in rows if r['evaluable'] and r.get('fidelity') is not None]
    asked = _correlation(rows, 'fidelity', 'oracle_auroc')
    gap = _correlation(rows, 'fidelity', 'oracle_gap')
    status = 'NOT EVALUABLE'
    if asked['rho'] is not None and gap['rho'] is not None:
        status = 'CONFIRMED' if (asked['rho'] >= .4 and asked['ci95'][0] > 0
                                 and gap['rho'] <= -.4 and gap['ci95'][1] < 0) else 'NOT MET'
    return {'status': status, 'asked_correlation': asked, 'gap_correlation': gap}


def w3_decision(rows):
    def summarize(selected, criterion):
        from common.stats import wilson
        n = len(selected)
        k = sum(criterion(r) for r in selected)
        return {'n': n, 'n_met': k, 'fraction': k/n if n else None,
                'wilson_ci95': list(wilson(k, n)[1:]) if n else [None, None]}
    eligible = [r for r in rows if r['evaluable']]
    blind = summarize([r for r in eligible if r['blindspot'] and r['row_class'] in ('count-like', 'state-like')],
                      lambda r: r['residual_auroc'] >= .9*r['original_auroc'])
    semantic = summarize([r for r in eligible if r['row_class'] == 'semantic'],
                         lambda r: r['original_auroc']-r['residual_auroc'] >= .15-1e-12)
    status = 'NOT EVALUABLE' if not blind['n'] or not semantic['n'] else (
        'CONFIRMED' if blind['fraction'] >= .7 and semantic['fraction'] >= .7 else 'NOT MET')
    return {'status': status, 'blindspot_retention': blind, 'semantic_drop': semantic}


def residual_probe(h, reconstructed, labels, groups, donors, k=5):
    """Same W-core grouped CV routine, item order and folds on h and true residual."""
    from mats import metrics
    h = _tensor(h, 'activations')
    r = residual_activations(h, reconstructed)
    from .analysis import grouped_probe
    original, _, folds = grouped_probe(h, labels, groups, donors, k=k)
    residual, _, residual_folds = grouped_probe(r, labels, groups, donors, k=k)
    if folds != residual_folds:
        raise ValueError('W3 probe folds differ')
    return {'original': asdict(metrics.auroc_ci(original, labels, groups, n_boot=2000, seed=P.SEED)),
            'residual': asdict(metrics.auroc_ci(residual, labels, groups, n_boot=2000, seed=P.SEED)),
            'original_scores': original.tolist(), 'residual_scores': residual.tolist(), 'folds': folds}


def prepare_swap_pairs(items, labels, features, n_pairs=40, seed=P.SEED):
    """Freeze directed pairs; item reuse is allowed, inference clusters by template.

    Opposite-value pairing uses labels ONLY here, before score collection. Random
    donors use only domain/identity (never their value), including the dev pool.
    """
    import numpy as np
    if len({it['id'] for it in items}) != len(items) or set(labels) != {it['id'] for it in items}:
        raise ValueError('item/label coverage mismatch')
    rng = np.random.default_rng(seed)
    pairs = []
    for feature in sorted(features):
        # W1 summary identifies blind-spot/semantic rows without W4 outcomes.
        selected = [i for i, it in enumerate(items) if it['feature'] == feature and labels[it['id']]['split'] == 'test']
        candidates = []
        for i in selected:
            a = labels[items[i]['id']]
            for j in selected:
                b = labels[items[j]['id']]
                if (i != j and a['value'] != b['value'] and a['domain'] == b['domain']
                    and a['template_family'] == b['template_family'] and a['length_bin'] == b['length_bin']):
                    candidates.append((i, j))
        if len(candidates) < n_pairs:
            raise ValueError(f'{feature}: fewer than {n_pairs} eligible directed test pairs')
        chosen = rng.choice(len(candidates), size=n_pairs, replace=False)
        for serial, index in enumerate(chosen):
            i, j = candidates[index]
            # Independent of any random donor value; exclude i/j to avoid identity controls.
            pool = [k for k, it in enumerate(items) if k not in (i, j) and labels[it['id']]['domain'] == labels[items[i]['id']]['domain']]
            if not pool:
                raise ValueError('no independent same-domain random donor')
            pairs.append({'id': f'{feature}:swap:{serial:03d}', 'feature': feature,
                          'recipient': i, 'donor': j, 'random': int(rng.choice(pool)),
                          'cluster': labels[items[i]['id']]['template_family']})
    return pairs


def analyse_swap_scores(scores, pairs, labels, items, definitions):
    """Label join follows score sealing in the CLI. No invented pooled W4 threshold."""
    import numpy as np
    from mats import metrics
    keys = [(s['id'], s['arm']) for s in scores]
    expected = {(p['id'], arm) for p in pairs for arm in ARMS}
    if len(set(keys)) != len(keys) or set(keys) != expected or any(any(s[k] != v for k, v in SITE.items()) for s in scores):
        raise ValueError('incomplete/duplicate W4 score grid or wrong site')
    lookup = dict(zip(keys, scores))
    pair_features = {p['id']: p['feature'] for p in pairs}
    if any(s['feature'] != pair_features[s['id']] for s in scores):
        raise ValueError('score feature differs from frozen pair feature')
    rows = []
    for feature in sorted({p['feature'] for p in pairs}):
        pp = [p for p in pairs if p['feature'] == feature]
        positive = definitions[feature]['values'][0]
        yi = _binary([labels[items[p['recipient']]['id']]['value'] == positive for p in pp], len(pp))
        yj = _binary([labels[items[p['donor']]['id']]['value'] == positive for p in pp], len(pp))
        if not np.array_equal(yi, 1-yj):
            raise ValueError('swap pair values are not opposite')
        groups = np.array([p['cluster'] for p in pp])
        arms, means = {}, {}
        for arm in ARMS:
            means[arm] = np.array([np.mean(lookup[p['id'], arm]['scores']) for p in pp])
            if not np.isfinite(means[arm]).all():
                raise ValueError('nonfinite W4 scores')
            arms[arm] = {'recipient': asdict(metrics.auroc_ci(means[arm], yi, groups, n_boot=2000, seed=P.SEED)),
                         'donor': asdict(metrics.auroc_ci(means[arm], yj, groups, n_boot=2000, seed=P.SEED))}
        contrasts = {}
        for control in ARMS[1:]:
            for name, y in (('recipient', yi), ('donor', yj)):
                stat = lambda idx: metrics.auroc_labels(means['swap'][idx], y[idx])-metrics.auroc_labels(means[control][idx], y[idx])
                contrasts[f'swap-minus-{control}:{name}'] = {
                    'difference': float(stat(np.arange(len(pp)))),
                    'ci95': list(metrics.cluster_bootstrap(stat, groups, n_boot=2000, seed=P.SEED))}
        # Field names in mats.metrics are stable; direct values keep decision logic explicit.
        donor_auc = metrics.auroc_labels(means['swap'], yj)
        recip_auc = metrics.auroc_labels(means['swap'], yi)
        donor_ci = metrics.cluster_bootstrap(lambda idx: metrics.auroc_labels(means['swap'][idx], yj[idx]), groups, n_boot=2000, seed=P.SEED)
        semantic = definitions[feature]['row_class'] == 'semantic'
        met = bool(recip_auc >= .7 if semantic else donor_auc >= .7 and donor_ci[0] > .5)
        rows.append({'feature': feature, 'row_class': definitions[feature]['row_class'], 'n_pairs': len(pp),
                     'arms': arms, 'contrasts': contrasts, 'rule_met': met, **SITE})
    # §73 gives per-row rules, but no fraction/pooling rule. Report conjunction explicitly.
    blind = [r for r in rows if r['row_class'] != 'semantic']
    semantic = [r for r in rows if r['row_class'] == 'semantic']
    return {'rows': rows, 'status': 'PER_ROW_RULES_REPORTED',
            'all_tested_rows_meet_rule': bool(blind and semantic and all(r['rule_met'] for r in rows)),
            'aggregation_note': 'No pooled or row-fraction decision threshold is specified in §73.', **SITE}


# Compatibility helpers retained for existing scaffold tests, not the current protocol.
def decompose(delta, reconstructed_direction, whitener):
    import torch
    dw, rw = delta.float() @ whitener.w.T, reconstructed_direction.float() @ whitener.w.T
    norm = rw.norm()
    if not torch.isfinite(norm) or norm <= 1e-10:
        raise ValueError('degenerate reconstructed direction')
    u = rw/norm
    component = ((dw@u)/norm)[..., None]*reconstructed_direction
    return component, delta-component, u


def kl_to(donor_logits, other_logits):
    import torch
    a, b = torch.log_softmax(donor_logits.float(), -1), torch.log_softmax(other_logits.float(), -1)
    return (a.exp()*(a-b)).sum(-1)


def _verify(directory, seal_name, required):
    directory = Path(directory)
    seal = P.verify(directory, seal_name)
    if not set(required) <= set(seal['files']):
        raise ValueError('seal does not cover required files: ' + ', '.join(sorted(set(required)-set(seal['files']))))
    return seal


def _read(path):
    return json.loads(Path(path).read_text())


def _no_labels(directory):
    if list(Path(directory).rglob('*.DO_NOT_STAGE.*')):
        raise ValueError('label-bearing files must not be staged to a GPU worker')


def _target(bank, target):
    import numpy as np
    _verify(bank, 'INPUT_SEAL.json', ['items.input.jsonl', 'templates.json', 'provenance.json'])
    _verify(target, 'SCORE_SEAL.json', ['acts44.npy', 'items.order.json', 'provenance.target.json'])
    if _read(target/'provenance.target.json')['input_seal_sha256'] != P.sha(bank/'INPUT_SEAL.json'):
        raise ValueError('target/bank seal mismatch')
    items = P.rows(bank/'items.input.jsonl')
    if len({i['id'] for i in items}) != len(items):
        raise ValueError('duplicate item IDs')
    if _read(target/'items.order.json') != [it['id'] for it in items]:
        raise ValueError('target item order mismatch')
    h = _tensor(np.load(target/'acts44.npy', allow_pickle=False), 'target activations')
    if len(h) != len(items):
        raise ValueError('target item coverage mismatch')
    return items, h


def _labels(bank, label_file, items):
    if P.sha(label_file) != _read(bank/'provenance.json')['labels_sha256']:
        raise ValueError('label hash differs from frozen bank')
    rows = P.rows(label_file)
    labels = {r['id']: r for r in rows}
    if len(labels) != len(rows) or set(labels) != {it['id'] for it in items}:
        raise ValueError('label coverage mismatch')
    return labels


def _validate_definitions(bank, definitions):
    templates = _read(bank/'templates.json')
    for feature, definition in definitions.items():
        spec = templates.get(feature)
        if (spec is None or definition['values'] != spec.get('values')
            or definition['row_class'] != spec.get('class')
            or spec.get('kind', 'binary') != 'binary'):
            raise ValueError('definition values/class differ from sealed bank: '+feature)


def _reference(path, bank, target):
    import numpy as np
    _verify(path, 'INPUT_SEAL.json', ['definitions.json', 'rows.json', 'directions.npz', 'provenance.json'])
    p = _read(path/'provenance.json')
    if (p['input_seal_sha256'] != P.sha(bank/'INPUT_SEAL.json')
        or p['target_score_seal_sha256'] != P.sha(target/'SCORE_SEAL.json')
        or p['direction_space'] != 'raw_block44'):
        raise ValueError('reference source/space mismatch')
    definitions, rows = _read(path/'definitions.json'), _read(path/'rows.json')
    _validate_definitions(bank, definitions)
    with np.load(path/'directions.npz', allow_pickle=False) as archive:
        directions = {k: _tensor(archive[k], 'direction', 1) for k in archive.files}
    if not set(directions) <= set(definitions) or {r['feature'] for r in rows} != set(definitions) or len(rows) != len(definitions):
        raise ValueError('reference row/direction coverage mismatch')
    return definitions, rows, directions


def _provenance(**sources):
    return {'brief_sha256': P.sha(P.ROOT/BRIEF), 'source_files': mechanism_source_hashes(),
            'p3_reference_commit': P3_SOURCE_COMMIT, 'raw_activation_space': 'block44',
            **{key: P.sha(path) for key, path in sources.items()}}


def _assets(path, needed):
    """Reuse scaffold's pinned local-assets format without loading unrelated readers."""
    assets = _read(path)
    covered = {str(Path(r['path']).resolve()): r['sha256'] for r in assets.get('files', [])}
    if not covered:
        raise ValueError('pinned asset file manifest required')
    for name in needed:
        root = Path(assets[name])
        paths = list(root.rglob('*')) if root.is_dir() else [root]
        required = [p for p in paths if p.is_file()]
        if not required:
            raise ValueError('missing local asset: ' + name)
        for p in required:
            if covered.get(str(p.resolve())) != P.sha(p):
                raise ValueError('asset hash/coverage mismatch: ' + name)
    return assets


def verify_p3_review(path):
    review = _read(path)
    if (review.get('reviewer') != 'P3' or review.get('status') != 'APPROVED'
        or review.get('ar_tests_sha256') != P.sha(__file__)
        or review.get('brief_sha256') != P.sha(P.ROOT/BRIEF)
        or not review.get('review_evidence')):
        raise ValueError('P3 review of the exact swap code is required before launch')
    return review


def mechanism_source_hashes():
    paths = P.code_hashes()
    for name in ('projects/g_agreement/blindspot/ar_tests.py',
                 'projects/g_agreement/w_claims/ar.py'):
        paths[name] = P.sha(P.ROOT/name)
    return paths


def admit_mechanism(path, stage, *, now=None, pod_id=None):
    """W-core owns its W1 admission; retain identical receipt checks for W2–W4."""
    import math
    import os
    a = _read(path)
    now = time.time() if now is None else now
    pod_id = os.environ.get('RUNPOD_POD_ID') if pod_id is None else pod_id
    if not pod_id or a.get('pod_id') != pod_id or a.get('issuer') != 'integrator':
        raise ValueError('requires integrator assignment for this RunPod pod')
    if a.get('brief_registered') is not True or a.get('brief_pushed') is not True:
        raise ValueError('BRIEF_BLINDSPOT must be registered and pushed first')
    for key in ('source_commit', 'brief_commit'):
        value = a.get(key, '')
        if len(value) != 40 or any(c not in '0123456789abcdef' for c in value):
            raise ValueError('missing pinned '+key)
    if a.get('brief_sha256') != P.sha(P.ROOT/BRIEF) or a.get('source_files') != mechanism_source_hashes():
        raise ValueError('assigned brief/source differs from worker bytes')
    if a.get('mechanism_budget') != stage or a.get('gpu_count') != 1:
        raise ValueError('assignment must name mechanism budget and one GPU')
    created, deadline, budget, previous = (float(a[k]) for k in
        ('provider_created_epoch', 'deadline_epoch', 'allocated_gpu_seconds', 'previous_gpu_seconds'))
    setup = float(a.get('setup_allowance_seconds', 0))
    phase = float(a.get('phase_started_epoch', created))
    if not all(math.isfinite(x) for x in (created, deadline, budget, previous, setup, phase)):
        raise ValueError('invalid allocation times')
    if not 0 <= setup <= 1500:
        raise ValueError('setup allowance exceeds 1500 seconds')
    if not created <= phase <= now or phase != created and setup:
        raise ValueError('invalid phase start or repeated setup allowance')
    cap = CAP_HOURS[stage]*3600
    if stage == 'residual':
        forecast = float(a.get('smoke_forecast_seconds', float('nan')))
        if not math.isfinite(forecast) or not 0 < forecast <= cap:
            raise ValueError('invalid/over-cap smoke forecast; report before launch')
        cap = min(cap, 1.5*forecast)
    if previous < 0 or budget <= 0 or previous+budget > cap:
        raise ValueError('cumulative allocation exceeds registered mechanism cap')
    if not 0 < deadline-phase <= setup+budget or not created <= now < deadline-180:
        raise ValueError('allocation expired or retrieval reserve reached')
    if a.get('external_hardstop_verified') is not True:
        raise ValueError('integrator hardstop evidence required')
    return a


@contextmanager
def _compute(stage, assignment_path, review=None):
    """Shared admission + cumulative phase cap, including failed collection attempts."""
    if P.BRIEF != BRIEF:
        raise ValueError('shared scaffold still targets a superseded brief')
    if stage == 'swap':
        if review is None:
            raise ValueError('P3 review required before W4 launch')
        verify_p3_review(review)
    a = admit_mechanism(assignment_path, stage)
    if a.get('gpu_count', 1) != 1:
        raise ValueError('mechanism caps assume one GPU')
    ledger = P.ROOT/'results/g_agreement/compute.jsonl'
    used = sum(float(row['gpu_hours']) for row in P.rows(ledger)
               if row.get('extra', {}).get('mechanism_budget') == stage) if ledger.exists() else 0.
    remaining = CAP_HOURS[stage] - used
    requested = float(a['allocated_gpu_seconds'])/3600
    if remaining <= 0 or requested > remaining + 1e-9:
        raise ValueError(f'{stage} allocation exceeds remaining cap: {max(0., remaining):.6f} GPU-h')
    if stage == 'sae':
        raise ValueError('optional §81 not scheduled: requires verified remaining GPU after §79/§80')
    import os
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', WANDB_MODE='disabled')
    with P.logged('mechanism_'+stage, gpu=True, extra={'mechanism_budget': stage, 'pod_id': a['pod_id']}), P.compute_window(a):
        yield a


def freeze_texts(a):
    definitions = _read(a.definitions)
    records, labels = freeze_text_records(definitions)
    a.out.mkdir(parents=True, exist_ok=False)
    with P.logged('mechanism_freeze_texts'):
        P.jsonl(a.out/'texts.input.jsonl', records)
        P.jsonl(a.out/'text_labels.DO_NOT_STAGE.jsonl', labels)
        P.dump(a.out/'definitions.json', definitions)
        P.dump(a.out/'provenance.json', _provenance(definitions_sha256=a.definitions,
                    labels_sha256=a.out/'text_labels.DO_NOT_STAGE.jsonl'))
        P.seal(a.out, ['texts.input.jsonl', 'definitions.json', 'provenance.json'], 'INPUTS_FROZEN_AR_STATEMENTS')


def freeze_reference(a):
    """Normalize W-core/lens handoff once, before mechanism collection.

    rows JSON: list of {feature, row_class, evaluable, blindspot, probe_auroc,
    oracle_auroc}; definitions JSON uses the upstream A/B value order. Directions
    NPZ maps feature -> *raw-coordinate* coefficient (standardized coef/scale).
    No stats/directions are re-fit or selected here.
    """
    import numpy as np
    items, h = _target(a.bank, a.target)
    definitions, rows = _read(a.definitions), _read(a.rows)
    _validate_definitions(a.bank, definitions)
    freeze_text_records(definitions)  # validates the frozen definition schema
    if (len(rows) != len(definitions) or {r['feature'] for r in rows} != set(definitions)
        or not set(definitions) <= {i['feature'] for i in items}):
        raise ValueError('reference feature coverage mismatch')
    for row in rows:
        if (row['row_class'] != definitions[row['feature']]['row_class']
            or type(row['evaluable']) is not bool or type(row['blindspot']) is not bool
            or any(v is not None and not 0 <= v <= 1 for v in (row['probe_auroc'], row['oracle_auroc']))):
            raise ValueError('invalid W1/S1 row metadata')
        if row['evaluable'] and (row['probe_auroc'] is None or row['probe_auroc'] < .85 or row['oracle_auroc'] is None):
            raise ValueError('reference marks undecodable row evaluable')
        if row['blindspot'] != bool(row['evaluable'] and row['row_class'] in ('count-like', 'state-like') and row['oracle_auroc'] <= row['probe_auroc']-.15):
            raise ValueError('blindspot must follow W1(i), not a post-hoc criterion')
    with np.load(a.directions, allow_pickle=False) as z:
        directions = {k: _tensor(z[k], 'direction', 1).numpy() for k in z.files}
    if not set(directions) <= set(definitions) or any(v.shape != (h.shape[1],) for v in directions.values()):
        raise ValueError('raw direction shape/coverage mismatch')
    a.out.mkdir(parents=True, exist_ok=False)
    with P.logged('mechanism_freeze_reference'):
        P.dump(a.out/'definitions.json', definitions)
        P.dump(a.out/'rows.json', rows)
        np.savez(a.out/'directions.npz', **directions)
        P.dump(a.out/'provenance.json', {**_provenance(input_seal_sha256=a.bank/'INPUT_SEAL.json',
                    target_score_seal_sha256=a.target/'SCORE_SEAL.json', upstream_rows_sha256=a.rows,
                    upstream_directions_sha256=a.directions), 'direction_space': 'raw_block44',
                    'upstream_evidence': a.evidence})
        P.seal(a.out, ['definitions.json', 'rows.json', 'directions.npz', 'provenance.json'], 'INPUTS_FROZEN_MECHANISM_REFERENCE')


def definitions_from_bank(bank):
    _verify(bank, 'INPUT_SEAL.json', ['templates.json'])
    templates = _read(bank/'templates.json')
    definitions = {}
    for f, spec in templates.items():
        if spec.get('kind', 'binary') != 'binary':
            continue
        if spec.get('score_orientation') != 'value_A_positive' or len(spec['olens']) < 2:
            raise ValueError('W1 definition lacks frozen A-positive phrasings')
        definitions[f] = {'row_class': spec['class'], 'values': spec['values'],
                          'descriptions': [text.removeprefix('- ') for text in spec['olens'][0]],
                          'statement_pairs': spec['olens'][:2]}
    return definitions


def freeze_w1_texts(a):
    """Freeze AR texts directly from the W1 bank; no rephrasing after readouts."""
    definitions = definitions_from_bank(a.bank)
    records, labels = freeze_text_records(definitions)
    a.out.mkdir(parents=True, exist_ok=False)
    with P.logged('mechanism_freeze_w1_texts'):
        P.jsonl(a.out/'texts.input.jsonl', records)
        P.jsonl(a.out/'text_labels.DO_NOT_STAGE.jsonl', labels)
        P.dump(a.out/'definitions.json', definitions)
        P.dump(a.out/'provenance.json', _provenance(input_seal_sha256=a.bank/'INPUT_SEAL.json',
                    labels_sha256=a.out/'text_labels.DO_NOT_STAGE.jsonl'))
        P.seal(a.out, ['texts.input.jsonl', 'definitions.json', 'provenance.json'], 'INPUTS_FROZEN_AR_STATEMENTS')


def reference_from_w1(a):
    """Consume the actual W-core ANALYSIS_SEAL and dev-fitted raw directions."""
    import numpy as np
    _target(a.bank, a.target)
    _verify(a.w1, 'ANALYSIS_SEAL.json', ['metrics.json', 'probe_directions.json', 'probe_directions.npz'])
    metrics = _read(a.w1/'metrics.json')
    if (metrics['input_seal_sha256'] != P.sha(a.bank/'INPUT_SEAL.json')
        or P.sha(a.target/'SCORE_SEAL.json') not in metrics['reader_seals']):
        raise ValueError('W-core analysis is from another bank/target')
    definitions = definitions_from_bank(a.bank)
    cells = {(c['feature'], c['reader'], c['layer']): c for c in metrics['rows']}
    meta = _read(a.w1/'probe_directions.json')
    if meta['fit_split'] != 'dev':
        raise ValueError('directions must be fitted only on dev')
    directions, rows = {}, []
    with np.load(a.w1/'probe_directions.npz', allow_pickle=False) as arrays:
        for f, definition in definitions.items():
            o, n = cells[f, 'olens', 44], cells[f, 'nla', 42]
            eligible = o['status'] == 'EVALUABLE'
            probe, oracle = o['probe_auroc'], o['true']['auroc'] if o['true'] is not None else None
            if eligible and (probe < .85 or o['mismatched']['auroc'] > .6):
                raise ValueError('upstream Oracle evaluability gate mismatch')
            nla_eligible = n['status'] == 'EVALUABLE'
            if nla_eligible and (n['probe_auroc'] < .85 or n['mismatched']['auroc'] > .6):
                raise ValueError('upstream NLA evaluability gate mismatch')
            direction_rows = [r for r in meta['rows'] if r['feature'] == f and r['layer'] == 44]
            if len(direction_rows) != 1:
                raise ValueError('missing/duplicate direction metadata')
            dm = direction_rows[0]
            if 'array_prefix' in dm:
                if (dm['fit_split'] != 'dev' or dm['positive_value'] != definition['values'][0]
                    or dm['orientation_flipped'] is not False):
                    raise ValueError('direction orientation or fitting provenance differs')
                directions[f] = arrays[dm['array_prefix']+'__unit']
            rows.append({'feature': f, 'row_class': definition['row_class'], 'evaluable': eligible,
                         'blindspot': bool(eligible and definition['row_class'] in ('count-like', 'state-like')
                                           and oracle <= probe-.15),
                         'probe_auroc': probe, 'oracle_auroc': oracle, 'nla_evaluable': nla_eligible,
                         'oracle_mismatched_auroc': o['mismatched']['auroc'] if o['mismatched'] else None})
    a.out.mkdir(parents=True, exist_ok=False)
    with P.logged('mechanism_reference_from_w1'):
        P.dump(a.out/'definitions.json', definitions)
        P.dump(a.out/'rows.json', rows)
        np.savez(a.out/'directions.npz', **directions)
        P.dump(a.out/'provenance.json', {**_provenance(input_seal_sha256=a.bank/'INPUT_SEAL.json',
                    target_score_seal_sha256=a.target/'SCORE_SEAL.json', w1_analysis_seal_sha256=a.w1/'ANALYSIS_SEAL.json'),
                    'direction_space': 'raw_block44', 'w1_status': metrics['w1']['status']})
        P.seal(a.out, ['definitions.json', 'rows.json', 'directions.npz', 'provenance.json'], 'INPUTS_FROZEN_MECHANISM_REFERENCE')


def collect_fidelity(a):
    import numpy as np
    import torch
    _no_labels(a.texts)
    _verify(a.texts, 'INPUT_SEAL.json', ['texts.input.jsonl', 'definitions.json', 'provenance.json'])
    records = P.rows(a.texts/'texts.input.jsonl')
    expected, _ = freeze_text_records(_read(a.texts/'definitions.json'))
    if records != expected:
        raise ValueError('statement grid differs from frozen definition template')
    assets = _assets(a.assets, ('model', 'ar'))
    with _compute('fidelity', a.assignment):
        from projects.g_agreement.w_claims.ar import load_reconstructor, reconstruct
        a.out.mkdir(parents=True, exist_ok=False)
        ar, tok, _ = load_reconstructor(a.official, a.whitener, assets['ar'], assets['model'])
        vectors = []
        for begin in range(0, len(records), a.batch):
            vectors.append(reconstruct(ar, tok, [r['text'] for r in records[begin:begin+a.batch]]))
        np.save(a.out/'recon.npy', torch.cat(vectors).numpy(), allow_pickle=False)
        P.dump(a.out/'ids.json', [r['id'] for r in records])
        P.dump(a.out/'provenance.json', {**_provenance(text_seal_sha256=a.texts/'INPUT_SEAL.json',
                   assets_sha256=a.assets, assignment_sha256=a.assignment, whitener_sha256=a.whitener), 'stage': a.study})
        P.seal(a.out, ['recon.npy', 'ids.json', 'provenance.json'], 'SCORES_SEALED_FIDELITY_BEFORE_LABEL_JOIN')


def collect_readouts(a):
    _no_labels(a.bank)
    items, h = _target(a.bank, a.target)
    assets = _assets(a.assets, ('model', 'olens'))
    with _compute('residual', a.assignment):
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from mats.readers.olens import load_olens, Sampling
        a.out.mkdir(parents=True, exist_ok=False)
        model = AutoModelForCausalLM.from_pretrained(assets['model'], dtype=torch.bfloat16,
                                                    device_map='cuda', local_files_only=True).eval()
        tok = AutoTokenizer.from_pretrained(assets['model'], local_files_only=True)
        ol = load_olens(model, tok, lora_dir=assets['olens'])
        records = []
        for begin in range(0, len(items), a.batch):
            texts = ol.verbalize(h[begin:begin+a.batch], layer=44, k=1,
                                sampling=Sampling(temperature=0, max_new_tokens=256), batch=a.batch)
            if len(texts) != len(items[begin:begin+a.batch]) or any(len(t) != 1 or not t[0].strip() for t in texts):
                raise ValueError('empty/incomplete greedy OL readout')
            records.extend({'id': it['id'], 'text': t[0]} for it, t in zip(items[begin:begin+a.batch], texts))
        P.jsonl(a.out/'readouts.jsonl', records)
        P.dump(a.out/'provenance.json', {**_provenance(input_seal_sha256=a.bank/'INPUT_SEAL.json',
                    target_score_seal_sha256=a.target/'SCORE_SEAL.json', assets_sha256=a.assets,
                    assignment_sha256=a.assignment), 'decoding': {'layer': 44, 'temperature': 0, 'k': 1, 'max_new_tokens': 256}})
        P.seal(a.out, ['readouts.jsonl', 'provenance.json'], 'SCORES_SEALED_GREEDY_READOUTS_BEFORE_LABEL_JOIN')


def _check_readouts(readouts, bank, target, items):
    _verify(readouts, 'SCORE_SEAL.json', ['readouts.jsonl', 'provenance.json'])
    p = _read(readouts/'provenance.json')
    if (p['input_seal_sha256'] != P.sha(bank/'INPUT_SEAL.json')
        or p['target_score_seal_sha256'] != P.sha(target/'SCORE_SEAL.json')
        or p['decoding'] != {'layer': 44, 'temperature': 0, 'k': 1, 'max_new_tokens': 256}):
        raise ValueError('readout source/greedy-decoding mismatch')
    rows = P.rows(readouts/'readouts.jsonl')
    if any(not isinstance(r.get('text'), str) or not r['text'].strip() for r in rows):
        raise ValueError('empty/invalid greedy readout')
    if [r['id'] for r in rows] != [i['id'] for i in items]:
        raise ValueError('readout ID/order mismatch')
    return rows


def collect_residuals(a):
    import numpy as np
    import torch
    _no_labels(a.bank)
    items, h = _target(a.bank, a.target)
    readouts = _check_readouts(a.readouts, a.bank, a.target, items)
    assets = _assets(a.assets, ('model', 'ar'))
    with _compute('residual', a.assignment):
        from projects.g_agreement.w_claims.ar import load_reconstructor, reconstruct
        a.out.mkdir(parents=True, exist_ok=False)
        ar, tok, _ = load_reconstructor(a.official, a.whitener, assets['ar'], assets['model'])
        rec = torch.cat([reconstruct(ar, tok, [r['text'] for r in readouts[b:b+a.batch]])
                         for b in range(0, len(readouts), a.batch)])
        r = residual_activations(h, rec)
        np.save(a.out/'recon.npy', rec.numpy(), allow_pickle=False)
        np.save(a.out/'residual.npy', r.numpy(), allow_pickle=False)
        P.dump(a.out/'ids.json', [it['id'] for it in items])
        P.dump(a.out/'provenance.json', {**_provenance(input_seal_sha256=a.bank/'INPUT_SEAL.json',
                    target_score_seal_sha256=a.target/'SCORE_SEAL.json', readout_score_seal_sha256=a.readouts/'SCORE_SEAL.json',
                    assets_sha256=a.assets, assignment_sha256=a.assignment, whitener_sha256=a.whitener),
                    'readout_provenance': _read(a.readouts/'provenance.json')})
        P.seal(a.out, ['recon.npy', 'residual.npy', 'ids.json', 'provenance.json'], 'SCORES_SEALED_RESIDUALS_BEFORE_LABEL_JOIN')


def _residuals(directory, bank, target, items, h):
    import numpy as np
    import torch
    _verify(directory, 'SCORE_SEAL.json', ['recon.npy', 'residual.npy', 'ids.json', 'provenance.json'])
    p = _read(directory/'provenance.json')
    if (p['input_seal_sha256'] != P.sha(bank/'INPUT_SEAL.json')
        or p['target_score_seal_sha256'] != P.sha(target/'SCORE_SEAL.json')
        or _read(directory/'ids.json') != [it['id'] for it in items]):
        raise ValueError('residual source/ID mismatch')
    rec = _tensor(np.load(directory/'recon.npy', allow_pickle=False), 'reconstructions')
    residual = _tensor(np.load(directory/'residual.npy', allow_pickle=False), 'residuals')
    if residual.shape != h.shape or not torch.allclose(residual, residual_activations(h, rec)):
        raise ValueError('residual is not h minus AR(OL(h))')
    return rec


def _test_indices(items, labels, feature):
    idx = [i for i, it in enumerate(items) if it['feature'] == feature and labels[it['id']]['split'] == 'test']
    if not idx:
        raise ValueError('no test items for ' + feature + '; mine/select banks are superseded')
    return idx


def analyse_fidelity(a):
    import numpy as np
    items, h = _target(a.bank, a.target)
    definitions, summary, directions = _reference(a.reference, a.bank, a.target)
    _verify(a.texts, 'INPUT_SEAL.json', ['texts.input.jsonl', 'definitions.json', 'provenance.json'])
    _verify(a.reconstruction, 'SCORE_SEAL.json', ['recon.npy', 'ids.json', 'provenance.json'])
    if (_read(a.reconstruction/'provenance.json')['text_seal_sha256'] != P.sha(a.texts/'INPUT_SEAL.json')
        or _read(a.texts/'definitions.json') != definitions):
        raise ValueError('fidelity definition/source mismatch')
    records = P.rows(a.texts/'texts.input.jsonl')
    if records != freeze_text_records(definitions)[0]:
        raise ValueError('incomplete frozen statement grid')
    rec = _tensor(np.load(a.reconstruction/'recon.npy', allow_pickle=False), 'AR predictions')
    if _read(a.reconstruction/'ids.json') != [r['id'] for r in records] or len(rec) != len(records):
        raise ValueError('incomplete fidelity reconstruction grid')
    if P.sha(a.text_labels) != _read(a.texts/'provenance.json')['labels_sha256']:
        raise ValueError('statement label hash mismatch')
    # All upstream score seals and numeric coverage are validated BEFORE label access.
    labels = _labels(a.bank, a.labels, items)
    text_labels = P.rows(a.text_labels)
    if [r['id'] for r in text_labels] != [r['id'] for r in records]:
        raise ValueError('statement label ID/order mismatch')
    with P.logged('mechanism_analyse_fidelity'):
        rows = []
        for row in summary:
            f = row['feature']
            idx = _test_indices(items, labels, f)
            ti = [i for i, r in enumerate(records) if r['feature'] == f]
            y = [labels[items[i]['id']]['value'] == definitions[f]['values'][0] for i in idx]
            if f not in directions:
                rows.append({**row, 'fidelity': None, 'status': 'NOT EVALUABLE', 'reason': 'upstream direction not exported'})
                continue
            try:
                measured = fidelity(rec[ti], [text_labels[i] for i in ti], h[idx], y, directions[f])
            except ValueError as error:
                if 'degenerate real class-mean gap' not in str(error):
                    raise
                measured = {'status': 'NOT EVALUABLE', 'fidelity': None, 'reason': str(error)}
            rows.append({**row, **measured})
        scope = 'EXPLORATORY' if _read(a.reference/'provenance.json').get('w1_status') == 'NOT MET' else 'REGISTERED_RULES'
        result = {'rows': rows, 'inference_scope': scope, 'W2': w2_decision(rows), 'S2': s2_decision(rows),
                  'reconstruction_score_seal_sha256': P.sha(a.reconstruction/'SCORE_SEAL.json'),
                  'reference_seal_sha256': P.sha(a.reference/'INPUT_SEAL.json')}
        _save_analysis(a.out, result, 'fidelity')


def analyse_residual(a):
    items, h = _target(a.bank, a.target)
    definitions, summary, _ = _reference(a.reference, a.bank, a.target)
    rec = _residuals(a.residuals, a.bank, a.target, items, h)
    labels = _labels(a.bank, a.labels, items)
    with P.logged('mechanism_analyse_residual'):
        rows = []
        for row in summary:
            f = row['feature']
            idx = _test_indices(items, labels, f)
            y = [labels[items[i]['id']]['value'] == definitions[f]['values'][0] for i in idx]
            groups = [labels[items[i]['id']]['cluster'] for i in idx]
            # W-core routine only requires same-held-out-group donors; identity is
            # intentional because its mismatched result is unused for W3.
            import numpy as np
            result = residual_probe(h[idx], rec[idx], y, groups, np.arange(len(idx)))
            if row['probe_auroc'] is not None and not np.isclose(result['original']['auroc'], row['probe_auroc'], atol=1e-6):
                raise ValueError('W3 original probe does not reproduce frozen W1 probe')
            rows.append({**row, **result, 'original_auroc': result['original']['auroc'],
                         'residual_auroc': result['residual']['auroc']})
        scope = 'EXPLORATORY' if _read(a.reference/'provenance.json').get('w1_status') == 'NOT MET' else 'REGISTERED_RULES'
        _save_analysis(a.out, {'rows': rows, 'inference_scope': scope, 'W3': w3_decision(rows),
                       'residual_score_seal_sha256': P.sha(a.residuals/'SCORE_SEAL.json'),
                       'reference_seal_sha256': P.sha(a.reference/'INPUT_SEAL.json'),
                       'secondary_NLA_decoder': 'NOT RUN; descriptive and requires its frozen block42 decoder'}, 'residual')


def _save_analysis(out, result, stage):
    out.mkdir(parents=True, exist_ok=False)
    P.dump(out/f'metrics.{stage}.json', result)
    P.seal(out, [f'metrics.{stage}.json'], 'SCORES_SEALED_ANALYSIS_'+stage.upper())


def prepare_swaps(a):
    items, h = _target(a.bank, a.target)
    definitions, rows, _ = _reference(a.reference, a.bank, a.target)
    _residuals(a.residuals, a.bank, a.target, items, h)
    labels = _labels(a.bank, a.labels, items)
    # W-core's source cluster IS the template family. Length bins are frozen here
    # from token counts, without outcomes; width=8 tokens, recorded in provenance.
    for it in items:
        r = labels[it['id']]
        r['template_family'] = r['cluster']
        r['length_bin'] = len(it['ids'])//8
    selected = [r['feature'] for r in rows if r['evaluable'] and r.get('nla_evaluable') is True and (r['blindspot'] or r['row_class'] == 'semantic')]
    fallback = _read(a.reference/'provenance.json').get('w1_status') == 'NOT MET'
    if fallback:
        selected = [r['feature'] for r in rows if r['feature'] in ('table_column', 'prose_paren') and r['evaluable'] and r.get('nla_evaluable') is True]
    if not selected:
        raise ValueError('no evaluable blind-spot/semantic rows')
    pairs = prepare_swap_pairs(items, labels, selected)
    templates = _read(a.bank/'templates.json')
    if any(len(templates[f]['nla']) < 2 for f in selected):
        raise ValueError('W4 requires W1 frozen NLA phrasings (at least two pairs)')
    with P.logged('mechanism_prepare_swaps'):
        a.out.mkdir(parents=True, exist_ok=False)
        P.jsonl(a.out/'pairs.input.jsonl', pairs)
        P.dump(a.out/'templates.json', {f: templates[f] for f in selected})
        P.dump(a.out/'definitions.json', {f: definitions[f] for f in selected})
        P.dump(a.out/'provenance.json', {**_provenance(input_seal_sha256=a.bank/'INPUT_SEAL.json',
                   target_score_seal_sha256=a.target/'SCORE_SEAL.json', residual_score_seal_sha256=a.residuals/'SCORE_SEAL.json',
                   reference_seal_sha256=a.reference/'INPUT_SEAL.json'),
                   'pairing': '40 directed pairs without replacement; item reuse allowed; template-cluster bootstrap',
                   'random_control': 'uniform same-domain item excluding i/j; value ignored',
                   'length_bin_width': 8, 'seed': P.SEED, 'inference_scope': 'EXPLORATORY' if fallback else 'REGISTERED_RULES', **SITE})
        P.seal(a.out, ['pairs.input.jsonl', 'templates.json', 'definitions.json', 'provenance.json'], 'INPUTS_FROZEN_CAUSAL_SWAP')


def _swap_inputs(a, items, h):
    _verify(a.pairs, 'INPUT_SEAL.json', ['pairs.input.jsonl', 'templates.json', 'definitions.json', 'provenance.json'])
    p = _read(a.pairs/'provenance.json')
    if (p['input_seal_sha256'] != P.sha(a.bank/'INPUT_SEAL.json')
        or p['target_score_seal_sha256'] != P.sha(a.target/'SCORE_SEAL.json')
        or p['residual_score_seal_sha256'] != P.sha(a.residuals/'SCORE_SEAL.json')
        or any(p[k] != v for k, v in SITE.items())):
        raise ValueError('swap input source/site mismatch')
    pairs, templates = P.rows(a.pairs/'pairs.input.jsonl'), _read(a.pairs/'templates.json')
    definitions = _read(a.pairs/'definitions.json')
    _validate_definitions(a.bank, definitions)
    pair_features = {p['feature'] for p in pairs}
    if (set(templates) != set(definitions) or pair_features != set(templates)
        or len({p['id'] for p in pairs}) != len(pairs)):
        raise ValueError('swap pair/template/definition coverage mismatch')
    for pair in pairs:
        if any(type(pair[k]) is not int or not 0 <= pair[k] < len(items) for k in ('recipient', 'donor', 'random')):
            raise ValueError('swap pair index out of bounds')
        if (pair['recipient'] == pair['donor'] or pair['random'] in (pair['recipient'], pair['donor'])
            or any(items[pair[k]]['feature'] != pair['feature'] for k in ('recipient', 'donor'))):
            raise ValueError('swap pair identity/feature mismatch')
    original_templates = _read(a.bank/'templates.json')
    for f in templates:
        if templates[f] != original_templates[f] or sum(row['feature'] == f for row in pairs) != 40:
            raise ValueError('W1/W4 scoring template or 40-pair count mismatch')
    rec = _residuals(a.residuals, a.bank, a.target, items, h)
    return pairs, templates, rec


def collect_swaps(a):
    # Review gate is checked before any asset hashing, CUDA import or model load.
    verify_p3_review(a.review)
    _no_labels(a.bank)
    _no_labels(a.pairs)
    items, h = _target(a.bank, a.target)
    pairs, templates, rec = _swap_inputs(a, items, h)
    assets = _assets(a.assets, ('nla',))
    with _compute('swap', a.assignment, review=a.review):
        from mats.readers.nla import load_nla
        a.out.mkdir(parents=True, exist_ok=False)
        nla = load_nla(root=assets['nla'], load_ar=False, enable_thinking=False)
        scores = score_swaps(nla, h, rec, pairs, templates, batch=a.batch)
        P.jsonl(a.out/'scores.swap.jsonl', scores)
        P.dump(a.out/'provenance.json', {**_provenance(pair_seal_sha256=a.pairs/'INPUT_SEAL.json',
                    assets_sha256=a.assets, assignment_sha256=a.assignment, p3_review_sha256=a.review), **SITE})
        P.seal(a.out, ['scores.swap.jsonl', 'provenance.json'], 'SCORES_SEALED_SWAP_BEFORE_LABEL_JOIN')


def analyse_swaps(a):
    items, h = _target(a.bank, a.target)
    pairs, _, _ = _swap_inputs(a, items, h)
    _verify(a.scores, 'SCORE_SEAL.json', ['scores.swap.jsonl', 'provenance.json'])
    if _read(a.scores/'provenance.json')['pair_seal_sha256'] != P.sha(a.pairs/'INPUT_SEAL.json'):
        raise ValueError('W4 score/pair seal mismatch')
    scores = P.rows(a.scores/'scores.swap.jsonl')
    expected = {(p['id'], arm) for p in pairs for arm in ARMS}
    keys = [(r['id'], r['arm']) for r in scores]
    if len(keys) != len(expected) or set(keys) != expected:
        raise ValueError('incomplete W4 scores before label join')
    labels = _labels(a.bank, a.labels, items)
    with P.logged('mechanism_analyse_swaps'):
        result = analyse_swap_scores(scores, pairs, labels, items, _read(a.pairs/'definitions.json'))
        result['score_seal_sha256'] = P.sha(a.scores/'SCORE_SEAL.json')
        result['inference_scope'] = _read(a.pairs/'provenance.json')['inference_scope']
        _save_analysis(a.out, result, 'swap')


def dry_run(a):
    """Offline software check on two pilot row definitions, never empirical fidelity."""
    import numpy as np
    import torch
    definitions = {
        'table_column': {'row_class': 'count-like', 'values': ['first', 'later'],
                         'descriptions': ['the first table column', 'a later table column']},
        'prose_paren': {'row_class': 'state-like', 'values': ['inside', 'outside'],
                        'descriptions': ['an open parenthesis', 'no open parenthesis']},
    }
    pilot_files = {'table_column': 'gen_ol_tb_tablecol.json', 'prose_paren': 'gen_ol_tb_paren.json'}
    a.out.mkdir(parents=True, exist_ok=False)
    with P.logged('mechanism_pilot_dry_run', extra={'mode': 'CPU_CONTRACT_ONLY', 'model_forwards': 0}):
        records, labels = freeze_text_records(definitions)
        P.jsonl(a.out/'texts.input.jsonl', records)
        P.jsonl(a.out/'text_labels.DO_NOT_STAGE.jsonl', labels)
        P.dump(a.out/'definitions.json', definitions)
        P.dump(a.out/'provenance.json', _provenance(labels_sha256=a.out/'text_labels.DO_NOT_STAGE.jsonl'))
        P.seal(a.out, ['texts.input.jsonl', 'definitions.json', 'provenance.json'], 'INPUTS_FROZEN_PILOT_SOFTWARE_CHECK')
        report = []
        for f, filename in pilot_files.items():
            path = P.ROOT/'external/mats-nla-workspace/experiments/13_new_rows/results'/filename
            pilot = _read(path)
            inventory = {'source': str(path.relative_to(P.ROOT)), 'sha256': P.sha(path),
                         'n_pilot_items': len(pilot['items']),
                         'readout_layers_available': sorted(pilot['ol_gens'])}
            ti = [i for i, r in enumerate(records) if r['feature'] == f]
            ty = np.array([labels[i]['value'] for i in ti])
            # Explicitly manufactured vectors with a known analytic ratio; no use
            # of pilot outcomes or cached scores in a mock scientific result.
            y = np.tile([1, 0], 10)
            h = torch.tensor(np.column_stack([2*(2*y-1), np.ones(len(y))]), dtype=torch.float32)
            reconstruction = torch.tensor(np.column_stack([.4*(2*ty-1), np.ones(len(ty))]), dtype=torch.float32)
            result = fidelity(reconstruction, [labels[i] for i in ti], h, y, [1., 0.])
            if not np.isclose(result['fidelity'], .2):
                raise AssertionError('known projection ratio failed')
            own = h * .5
            pairs = [{'id': 'self-check', 'feature': f, 'recipient': 0, 'donor': 1, 'random': 2}]
            arms = swap_arms(h, own, pairs)
            if not torch.allclose(arms['self'][0], h[0]):
                raise AssertionError('self swap does not recover recipient')
            report.append({'feature': f, 'pilot_inventory': inventory, 'frozen_statement_texts': len(ti),
                           'numeric_fixture_check': 'PASS', 'measured_fidelity': None,
                           'model_forwards': 0, 'gpu_hours': 0.})
        P.dump(a.out/'dry_run.json', {
            'status': 'CPU_CONTRACT_ONLY_NOT_EMPIRICAL', 'rows': report,
            'missing_for_measured_fidelity': ['pilot block44 activations', 'pilot raw-space probe directions',
                                              'complete pinned AR/model weights', 'integrator GPU allocation'],
            'W4_launch': 'BLOCKED_PENDING_P3_REVIEW', **SITE,
            'input_seal_sha256': P.sha(a.out/'INPUT_SEAL.json'), 'source_files': mechanism_source_hashes()})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('plan')
    commands = {
        'dry-run': (dry_run, ('out',)),
        'freeze-texts': (freeze_texts, ('definitions', 'out')),
        'freeze-w1-texts': (freeze_w1_texts, ('bank', 'out')),
        'reference-from-w1': (reference_from_w1, ('bank', 'target', 'w1', 'out')),
        'freeze-reference': (freeze_reference, ('bank', 'target', 'definitions', 'rows', 'directions', 'out')),
        'collect-fidelity': (collect_fidelity, ('texts', 'assets', 'assignment', 'official', 'whitener', 'out')),
        'collect-readouts': (collect_readouts, ('bank', 'target', 'assets', 'assignment', 'out')),
        'collect-residuals': (collect_residuals, ('bank', 'target', 'readouts', 'assets', 'assignment', 'official', 'whitener', 'out')),
        'analyse-fidelity': (analyse_fidelity, ('bank', 'target', 'reference', 'labels', 'texts', 'text-labels', 'reconstruction', 'out')),
        'analyse-residual': (analyse_residual, ('bank', 'target', 'reference', 'labels', 'residuals', 'out')),
        'prepare-swaps': (prepare_swaps, ('bank', 'target', 'reference', 'labels', 'residuals', 'out')),
        'collect-swaps': (collect_swaps, ('bank', 'target', 'pairs', 'residuals', 'assets', 'assignment', 'review', 'out')),
        'analyse-swaps': (analyse_swaps, ('bank', 'target', 'pairs', 'residuals', 'scores', 'labels', 'out')),
    }
    for name, (function, paths) in commands.items():
        p = sub.add_parser(name)
        p.set_defaults(function=function)
        for path in paths:
            p.add_argument('--'+path, type=Path, required=True)
        if name.startswith('collect-'):
            p.add_argument('--batch', type=int, default=8)
        if name == 'collect-fidelity':
            p.add_argument('--study', choices=('W2', 'S2', 'W2+S2', 'PILOT'), default='W2+S2')
        if name == 'freeze-reference':
            p.add_argument('--evidence', required=True, help='W-core/lens frozen export commit/path or manifest digest')
    args = parser.parse_args(argv)
    if args.command == 'plan':
        print(json.dumps({'brief': BRIEF, 'caps_gpu_h': CAP_HOURS,
                          'fidelity_cap_note': 'W2/S2 share collection and the conservative 0.3 GPU-h user cap',
                          'W4_launch': 'P3_REVIEW_REQUIRED', 'S3': 'OPTIONAL_NOT_SCHEDULED',
                          'p3_reference_commit': P3_SOURCE_COMMIT, 'source_files': mechanism_source_hashes(), **SITE}, indent=2))
    else:
        if getattr(args, 'batch', 1) < 1:
            parser.error('--batch must be positive')
        args.function(args)


if __name__ == '__main__':
    main()
