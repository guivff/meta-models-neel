"""R2-B §36 CPU design primitives. No live collector or model/API calls.

The live runner must consume this contract; this module alone is NOT launch-ready.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import uuid
from datetime import datetime, timezone
import numpy as np

SEED = 20261020
STAGES = ('source', 'internal', 'constrained', 'free')
READERS = {'olens': 44, 'nla': 42}
ARMS = ('natural', 'shuffled', 'text_only', 'prompt_only', 'positive_system',
        'wrong_candidates', 'mean_ablation', 'random_ablation', 'sham')
OUTPUTS = ('selection.json', 'rows.jsonl', 'probe_fits.json', 'volume_states.json',
           'judge_inputs.jsonl', 'judge_outputs.jsonl', 'analysis.json', 'stage_accuracy.png')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def rank(key):
    return hashlib.sha256(f'{SEED}|{key}'.encode()).hexdigest()


def output_paths(root):
    return {name: Path(root) / name for name in OUTPUTS}


def audit_paths(root, paths):
    expected = {p.resolve() for p in output_paths(root).values()}
    extra = {Path(p).resolve() for p in paths} - expected
    if extra:
        raise ValueError(f'Undeclared output: {sorted(map(str, extra))}')


def tap_blocks(depth):
    if not isinstance(depth, int) or depth < 4:
        raise ValueError(f'Invalid decoder depth: {depth}')
    return tuple(depth * n // 4 for n in (1, 2, 3))


def stamp(pod, git_sha, code_sha256, run_kind='real'):
    if run_kind not in ('real', 'smoke', 'test'):
        raise ValueError(f'Invalid run_kind: {run_kind}')
    if not pod or not git_sha or len(code_sha256) != 64:
        raise ValueError('Missing pod/git/code provenance')
    return dict(pod=pod, git_sha=git_sha, code_sha256=code_sha256,
                run_kind=run_kind, run_id=f'{datetime.now(timezone.utc).isoformat()}-{uuid.uuid4()}')


def audit_rows(rows, expected, process):
    """Expected cells supplied by selection's own cell enumeration, never typed counts."""
    seen = set()
    for row in rows:
        cell = tuple(row['cell'])
        if cell not in expected:
            raise ValueError(f'Unexpected cell: {cell}')
        if cell in seen:
            raise ValueError(f'Duplicate cell: {cell}')
        for key, value in process.items():
            if row.get(key) != value:
                raise ValueError(f'Provenance mismatch {key}: {cell}')
        seen.add(cell)
    if expected - seen:
        raise ValueError(f'Missing cells: {sorted(expected-seen)}')


def select_main(facts):
    """Input is a frozen TH-3 per-fact difficulty inventory, not outcome predictions."""
    eligible = [x for x in facts if not x['label_defect'] and x['binary'] and x['provenance_ok']]
    if len({x['dataset'] for x in eligible}) != len(eligible):
        raise ValueError('Duplicate dataset in difficulty inventory')
    if any(not np.isfinite(x['median_abs_model_margin']) for x in eligible):
        raise ValueError('Nonfinite TH-3 margin')
    eligible.sort(key=lambda x: (x['median_abs_model_margin'], x['dataset']))
    selected = []
    for bin_id, indices in enumerate(np.array_split(np.arange(len(eligible)), 5)):
        group = [eligible[i] for i in indices]
        if len(group) < 4:
            raise ValueError(f'Insufficient difficulty bin {bin_id}: {len(group)}')
        selected += [dict(x, difficulty_bin=bin_id) for x in sorted(group, key=lambda x: rank(x['dataset']))[:4]]
    return selected


def balanced_items(items, split, n):
    if n % 2:
        raise ValueError(f'Unbalanced quota: {n}')
    selected = []
    for label in (0, 1):
        group = [x for x in items if x['split'] == split and x['label'] == label]
        group.sort(key=lambda x: rank(x.get('base_item_id', x['item_id'])))
        if len(group) < n//2:
            raise ValueError(f'Insufficient {split} label {label}: {len(group)}')
        selected.extend(group[:n//2])
    if len({x['item_id'] for x in selected}) != n:
        raise ValueError('Duplicate selected item_id')
    return sorted(selected, key=lambda x: x['item_id'])


def audit_split(train, test):
    """Caller supplies entity/document/fact grouping keys from the bank, not row IDs."""
    overlap = set(train) & set(test)
    if overlap:
        raise ValueError(f'Split leakage: {sorted(overlap)}')


def raw_normal(coef, scale):
    coef, scale = np.asarray(coef, dtype=float), np.asarray(scale, dtype=float)
    if coef.shape != scale.shape or np.any(scale <= 0) or not np.isfinite(scale).all():
        raise ValueError('Invalid probe scale')
    w = coef / scale
    if not np.isfinite(w).all() or np.linalg.norm(w) == 0:
        raise ValueError('Degenerate probe normal')
    return w / np.linalg.norm(w)


def mean_ablate(states, mean, normal):
    h, mu, u = (np.asarray(x, dtype=float) for x in (states, mean, normal))
    if h.shape[-1:] != mu.shape or mu.shape != u.shape:
        raise ValueError('Ablation shape mismatch')
    if not all(np.isfinite(x).all() for x in (h, mu, u)) or not np.isclose(np.linalg.norm(u), 1):
        raise ValueError('Invalid ablation values/unit normal')
    return h - ((h-mu) @ u)[..., None] * u


def random_orthogonal(normal, key):
    u = np.asarray(normal, dtype=float)
    if u.ndim != 1 or len(u) < 2 or not np.isclose(np.linalg.norm(u), 1):
        raise ValueError('Invalid random-control normal')
    rng = np.random.default_rng(int(rank(key)[:16], 16))
    v = rng.normal(size=u.shape); v -= (v @ u)*u
    if np.linalg.norm(v) < 1e-10:
        raise ValueError('Degenerate random direction')
    return v/np.linalg.norm(v)


def bh(pvalues):
    """Include missing preregistered hypotheses as p=1 before this call."""
    p = np.asarray(pvalues, dtype=float)
    if p.ndim != 1 or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError('Invalid BH p-values')
    if not len(p): return p
    order = np.argsort(p, kind='stable')
    adjusted = np.minimum.accumulate((p[order]*len(p)/np.arange(1, len(p)+1))[::-1])[::-1]
    out = np.empty_like(p); out[order] = np.minimum(adjusted, 1)
    return out


def verdict(points, cis, q, ablation_ci90, manipulation_ok):
    """q values are externally computed conjunction tests, not inferred from CIs."""
    if set(points) != set(STAGES) or set(cis) != set(STAGES):
        raise ValueError('Missing/extra stage')
    if any(not np.isfinite(points[s]) for s in STAGES): return 'UNDERPOWERED/MIXED'
    high = {s: points[s] >= .85 for s in STAGES}
    low = {s: points[s] <= .65 for s in STAGES}
    if high['source'] and low['internal'] and cis['source'][0] > cis['internal'][1] and q.get('representation', 1) <= .10:
        return 'REPRESENTATION BOTTLENECK'
    if all(high[s] for s in STAGES[:3]) and low['free'] and q.get('naming', 1) <= .10:
        return 'NAMING BOTTLENECK'
    if (high['source'] and high['internal'] and low['constrained'] and low['free'] and manipulation_ok
        and -.05 < ablation_ci90[0] <= ablation_ci90[1] < .05 and q.get('access', 1) <= .10):
        return 'ACCESS BOTTLENECK'
    return 'UNDERPOWERED/MIXED'


def text_buffer_verdict(ci90, ci95):
    for interval in (ci90, ci95):
        if len(interval) != 2 or not np.isfinite(interval).all() or interval[0] > interval[1]:
            raise ValueError('Invalid text-buffer interval')
    if -.05 < ci90[0] <= ci90[1] < .05:
        return 'TEXT-LIKE'
    if ci95[0] > .05:
        return 'STATE-SPECIFIC'
    return 'UNDERPOWERED/MIXED'


def rebuilt_subset(facts, elapsed, mandatory_remaining, rebuilt_seconds_per_fact, pull_reserve):
    """Timing-only decision. Costs supplied conservatively from all-arm smoke.

mandatory_remaining includes probes/hash/analysis; rebuilt_seconds_per_fact
already includes the registered 1.5 multiplier. No outcome argument exists.
"""
    values=(elapsed,mandatory_remaining,rebuilt_seconds_per_fact,pull_reserve)
    if not np.isfinite(values).all() or any(x < 0 for x in values):
        raise ValueError('Invalid timing projection')
    groups={b:sorted([f for f in facts if f['difficulty_bin']==b],
                    key=lambda f:rank('rebuilt-subset|'+f['dataset'])) for b in range(5)}
    if len(facts)!=20 or any(len(g)!=4 for g in groups.values()) or len({f['dataset'] for f in facts})!=20:
        raise ValueError('Invalid frozen twenty-fact inventory')
    ordered=[groups[b][i]['dataset'] for i in range(4) for b in range(5)]
    projections={n:elapsed+mandatory_remaining+n*rebuilt_seconds_per_fact+max(300,pull_reserve)
                 for n in (20,15,10,5)}
    for n,total in projections.items():
        if total<=7200:
            selected=ordered[:n]
            return dict(facts=selected,n=n,subset_sha256=digest(selected),projected_seconds=total)
    raise ValueError(f'No authorized rebuilt subset fits: {projections}')


def code_sha256():
    """Hash the archived project's Python sources, so new imports cannot be omitted."""
    root=Path(__file__).resolve().parents[1]
    return digest({str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(root.rglob('*.py')) if '__pycache__' not in p.parts})
