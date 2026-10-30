"""Sealed complete-grid E33 analysis; joins frozen truth only after collection validation."""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path
import numpy as np

from prepare import HERE, read, records, dump, sha, verify

PREFIX = 'results/g_agreement/understand/e33/'
OPERATIONS = 'OPERATIONS_2026-10-25.json'


def auc(scores, labels):
    """Tie-aware Mann-Whitney AUROC, matching mats.metrics.auroc_labels."""
    x = np.asarray(scores, float)
    y = np.asarray(labels, bool)
    if not y.any() or y.all():
        raise ValueError('both classes required')
    delta = x[y, None] - x[~y][None, :]
    return float(np.mean((delta > 0) + 0.5 * (delta == 0)))


def validate_grid(scores, items, plan):
    expected = {(r['id'], p, float(d)) for r in items for p in plan['prompts'] for d in plan['doses']}
    lookup = {r['id']: r['feature'] for r in items}
    actual = [(r['id'], r['prompt'], float(r['dose'])) for r in scores]
    if len(actual) != len(expected) or len(set(actual)) != len(actual) or set(actual) != expected:
        raise ValueError('complete unique registered 21000-score grid required')
    for r in scores:
        values = np.asarray(r['scores'], float)
        if r['feature'] != lookup[r['id']] or values.shape != (2,) or not np.isfinite(values).all():
            raise ValueError('invalid frozen feature/two-pair score')
        if not np.isfinite(r['score']) or abs(r['score'] - float(values.mean())) > 1e-8:
            raise ValueError('average paired log-odds before AUROC required')


def decide(medians, difference, ci):
    s0, s1 = medians['structure']['P1'][0], medians['structure']['P1'][-1]
    c0, c1 = medians['semantic']['P1'][0], medians['semantic']['P1'][-1]
    return {
        'adapter_policy': bool(difference >= .20 and ci[0] > 0 and s0 >= .90 and s1 <= .65 and min(c0, c1) >= .95),
        'prompt_account': bool(s1 >= .85),
        'content_all_doses_at_least_095_diagnostic': bool(min(medians['semantic']['P1']) >= .95),
    }


def compute(scores, labels, templates, plan, n_boot=2000):
    """Fixed rows; paired cluster resamples across the entire dose/prompt grid."""
    paths = [(p, float(d)) for p in plan['prompts'] for d in plan['doses']]
    ix_score = {(r['id'], r['prompt'], float(r['dose'])): r['score'] for r in scores}
    features = sorted(templates)
    rng = np.random.default_rng(plan['bootstrap']['seed'])
    points = np.empty((len(features), len(paths)))
    boots = np.empty((n_boot, len(features), len(paths)))
    rows = []
    for f_index, f in enumerate(features):
        keys = sorted(k for k, label in labels.items() if label['feature'] == f)
        y = np.array([labels[k]['value'] == templates[f]['values'][0] for k in keys], bool)
        group_names = sorted({labels[k]['cluster'] for k in keys})
        groups = [np.array([i for i, k in enumerate(keys) if labels[k]['cluster'] == group]) for group in group_names]
        if len(keys) != 84 or len(groups) != 6 or any(len(set(y[g])) != 2 for g in groups):
            raise ValueError('frozen W1 84 items / six two-class template clusters required')
        matrix = np.array([[ix_score[k, p, d] for p, d in paths] for k in keys])
        points[f_index] = [auc(matrix[:, j], y) for j in range(len(paths))]
        for b in range(n_boot):
            take = np.concatenate([groups[g] for g in rng.integers(0, len(groups), len(groups))])
            boots[b, f_index] = [auc(matrix[take, j], y[take]) for j in range(len(paths))]
        for j, (prompt, dose) in enumerate(paths):
            rows.append({'feature': f, 'class': templates[f]['class'], 'prompt': prompt, 'dose': dose,
                         'auroc': float(points[f_index, j]), 'ci95': np.quantile(boots[:, f_index, j], [.025, .975]).tolist(),
                         'n_items': len(keys), 'n_clusters': len(groups)})
    medians = {}; boot_medians = {}
    for cls in ['semantic', 'structure']:
        selected = [i for i, f in enumerate(features) if (templates[f]['class'] == 'semantic') == (cls == 'semantic')]
        medians[cls] = {p: np.median(points[selected], axis=0)[i * 5:(i + 1) * 5].tolist() for i, p in enumerate(plan['prompts'])}
        boot_medians[cls] = np.median(boots[:, selected], axis=1)
    s, c = medians['structure']['P1'], medians['semantic']['P1']
    difference = float((s[0] - s[-1]) - (c[0] - c[-1]))
    paired = (boot_medians['structure'][:, 0] - boot_medians['structure'][:, 4]) - (boot_medians['semantic'][:, 0] - boot_medians['semantic'][:, 4])
    ci = np.quantile(paired, [.025, .975]).tolist()
    return {'status': 'EXPLORATORY_E33', 'rows': rows, 'class_medians': medians,
            'primary': {'difference': difference, 'ci95': ci, 'structure_drop': s[0] - s[-1], 'content_drop': c[0] - c[-1]},
            'rules': decide(medians, difference, ci), 'bootstrap': {**plan['bootstrap'], 'n_boot': n_boot},
            'content_stays_interpretation': plan['content_stays_interpretation']}


def _source_files(pins):
    required = {PREFIX + n for n in ('PLAN.json', OPERATIONS, 'runtime.py', 'prepare.py', 'reused.py', 'analyse.py')}
    if not isinstance(pins, dict) or not required <= set(pins):
        raise ValueError('run plan lacks frozen source coverage')
    root = HERE.parents[3].resolve()
    for name, digest in pins.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or not path.is_file() or sha(path) != digest:
            raise ValueError('run-plan frozen source hash mismatch')


def _run_plan(value, inputs, plan):
    """Validate the full operational ledger without changing the scientific PLAN."""
    if value.get('schema') != 'E33_RUN_PLAN_v2' or value.get('experiment') != 'E33' or not value.get('run_id'):
        raise ValueError('E33_RUN_PLAN_v2 ledger required')
    if value.get('original_plan_sha256') != sha(HERE / 'PLAN.json'):
        raise ValueError('operational ledger changed original scientific plan')
    if value.get('input_seal_sha256') != sha(inputs / 'INPUT_SEAL.json'):
        raise ValueError('operational ledger/input lineage mismatch')
    if value.get('operations_sha256') != sha(HERE / OPERATIONS):
        raise ValueError('operational authority hash mismatch')
    operations = read(HERE / OPERATIONS)
    for name in ('previous_gpu_seconds', 'global_cap_gpu_seconds', 'original_plan_sha256', 'input_seal_sha256'):
        if value.get(name) != operations.get(name):
            raise ValueError('operational ledger differs from frozen authority/budget')
    _source_files(value.get('source_files'))
    for name in ('previous_gpu_seconds', 'global_cap_gpu_seconds'):
        if type(value.get(name)) not in (int, float) or not math.isfinite(value[name]):
            raise ValueError('finite cumulative budget ledger required')
    if value['previous_gpu_seconds'] < 0 or value['global_cap_gpu_seconds'] != 16200:
        raise ValueError('registered cumulative 4.5 GPU-hour ceiling required')
    allocations = value.get('allocations', [])
    if (len(allocations) not in (1, 2) or any(type(a.get('slot')) is not int for a in allocations)
            or [a.get('slot') for a in allocations] != list(range(len(allocations)))):
        raise ValueError('one or two unique complete assigned pod slots required')
    expected = [list(plan['doses'])] if len(allocations) == 1 else [list(plan['doses'][:3]), list(plan['doses'][3:])]
    if [a.get('doses') for a in allocations] != expected:
        raise ValueError('fixed dose allocation must cover all five doses exactly once')
    if any(not a.get('pod_id') for a in allocations) or len({a['pod_id'] for a in allocations}) != len(allocations):
        raise ValueError('unique assigned provider pod IDs required')
    for a in allocations:
        n = a.get('allocated_gpu_seconds')
        if type(n) not in (int, float) or not math.isfinite(n) or n <= 0:
            raise ValueError('finite positive per-pod allocation required')
        loss = a.get('infrastructure_loss_gpu_seconds', 0)
        envelope = a.get('budget_envelope_gpu_seconds', n)
        if (type(loss) not in (int, float) or not math.isfinite(loss) or not 0 <= loss <= 600
                or type(envelope) not in (int, float) or not math.isfinite(envelope)
                or n + loss != envelope or (loss > 0 and not a.get('infrastructure_losses'))):
            raise ValueError('setup loss must reduce its fixed live-pod envelope')
    if value['previous_gpu_seconds'] + sum(a['allocated_gpu_seconds'] + a.get('infrastructure_loss_gpu_seconds', 0)
                                         for a in allocations) > value['global_cap_gpu_seconds']:
        raise ValueError('cumulative prior plus allocated GPU budget exceeds cap')
    return allocations


def join_collections(inputs, collections, plan):
    """Validate and join complete dose shards before any private-label access."""
    if isinstance(collections, (str, Path)):
        collections = [Path(collections)]
    collections = [Path(p) for p in collections]
    if len(collections) not in (1, 2) or len({p.resolve() for p in collections}) != len(collections):
        raise ValueError('one or two distinct complete collections required')
    input_seal = verify(inputs)
    if not {'items.input.jsonl', 'templates.json', 'provenance.json'} <= set(input_seal['files']):
        raise ValueError('input seal lacks required analysis coverage')
    if read(inputs / 'provenance.json')['plan_sha256'] != sha(HERE / 'PLAN.json'):
        raise ValueError('plan changed after input freeze')
    items = records(inputs / 'items.input.jsonl')
    if (len(items) != 2100 or len({r['id'] for r in items}) != 2100
            or Counter(r['feature'] for r in items) != Counter({f: 84 for f in plan['rows']})):
        raise ValueError('full frozen 25-row 2100-item population required')
    scores, provenance_records, seal_hashes = [], [], []
    common_run_plan = None
    common_run_hash = None
    seen_slots, seen_doses = set(), set()
    provider_seconds = 0.0
    legacy = False
    for collection in collections:
        seal = verify(collection, 'SCORE_SEAL.json')
        required = {'scores.jsonl', 'provenance.json'}
        if not required <= set(seal['files']):
            raise ValueError('score seal lacks complete scientific-file coverage')
        provenance = read(collection / 'provenance.json')
        if provenance.get('input_seal_sha256') != sha(inputs / 'INPUT_SEAL.json'):
            raise ValueError('collection/input lineage mismatch')
        if provenance.get('status') != 'COMPLETE' or provenance.get('activation_injection') is not False:
            raise ValueError('completed activation-free collection required')
        if provenance.get('source_files', {}).get(PREFIX + 'PLAN.json') != sha(HERE / 'PLAN.json'):
            raise ValueError('collection/frozen plan lineage mismatch')
        if seal.get('status') == 'E33_COMPLETE':
            if len(collections) != 1:
                raise ValueError('legacy E33_COMPLETE is valid only as one full-grid collection')
            legacy = True
            doses = list(plan['doses'])
        elif seal.get('status') == 'E33_SHARD_COMPLETE':
            if not {'run_plan.json', 'RUN.json'} <= set(seal['files']):
                raise ValueError('shard seal lacks operational run plan')
            run_hash = sha(collection / 'run_plan.json')
            if provenance.get('run_plan_sha256') != run_hash:
                raise ValueError('shard/run-plan hash mismatch')
            run_plan = read(collection / 'run_plan.json')
            allocations = _run_plan(run_plan, inputs, plan)
            from runtime import infrastructure_losses
            for allocation in allocations:
                entries = []
                for index, entry in enumerate(allocation.get('infrastructure_losses', [])):
                    name = f"infrastructure_loss_slot{allocation['slot']}_{index}.json"
                    if name not in seal['files']:
                        raise ValueError('stopped deployment receipt missing from score seal')
                    entries.append({**entry, 'receipt_path': str(collection / name)})
                # Retain the original immutable run-plan bytes/hash; only relocate
                # receipt paths for verification of downloaded sealed copies.
                infrastructure_losses({**allocation, 'infrastructure_losses': entries})
            if common_run_hash is None:
                common_run_plan, common_run_hash = run_plan, run_hash
            elif run_hash != common_run_hash:
                raise ValueError('cannot join different run/source/budget ledgers')
            slot = provenance.get('slot')
            if type(slot) is not int or slot not in range(len(allocations)) or slot in seen_slots:
                raise ValueError('missing, duplicate, or invalid shard slot')
            assigned = allocations[slot]
            for name in ('run_id', 'operations_sha256', 'source_files', 'global_cap_gpu_seconds', 'previous_gpu_seconds'):
                if provenance.get(name) != run_plan[name]:
                    raise ValueError('shard operational/source/budget identity mismatch')
            if (type(provenance.get('pod_count')) is not int or provenance.get('pod_count') != len(allocations)
                    or provenance.get('assigned_doses') != assigned['doses']
                    or provenance.get('allocated_gpu_seconds') != assigned['allocated_gpu_seconds']
                    or provenance.get('original_plan_sha256') != sha(HERE / 'PLAN.json')
                    or provenance.get('expected_score_records') != 2100 * 2 * len(assigned['doses'])):
                raise ValueError('shard differs from assigned complete dose allocation')
            if provenance.get('pod_id') != assigned['pod_id']:
                raise ValueError('shard provider pod differs from ledger')
            run = read(collection / 'RUN.json')
            identity = ('run_id', 'run_plan_sha256', 'operations_sha256', 'original_plan_sha256',
                        'slot', 'pod_id', 'pod_count', 'assigned_doses', 'previous_gpu_seconds',
                        'global_cap_gpu_seconds', 'allocated_gpu_seconds', 'expected_score_records',
                        'source_files', 'input_seal_sha256', 'status', 'activation_injection')
            if any(run.get(k) != provenance.get(k) for k in identity):
                raise ValueError('sealed run receipt/shard provenance mismatch')
            elapsed = run.get('provider_elapsed_seconds')
            if (type(elapsed) not in (int, float) or not math.isfinite(elapsed)
                    or not 0 <= elapsed <= assigned['allocated_gpu_seconds']
                    or run.get('budget_includes_setup') is not True or run.get('budget_clock_resets') != 0
                    or run.get('GPU_count') != 1):
                raise ValueError('shard run exceeded or reset its provider budget')
            provider_seconds += elapsed
            doses = assigned['doses']
            if seen_doses.intersection(map(float, doses)):
                raise ValueError('overlapping dose shards')
            seen_slots.add(slot)
            seen_doses.update(map(float, doses))
        else:
            raise ValueError('incomplete/NO_FIT run cannot be analysed')
        shard_scores = records(collection / 'scores.jsonl')
        validate_grid(shard_scores, items, dict(plan, doses=doses))
        scores.extend(shard_scores)
        provenance_records.append(provenance)
        seal_hashes.append(sha(collection / 'SCORE_SEAL.json'))
    if not legacy and (seen_slots != set(range(len(common_run_plan['allocations'])))
                       or seen_doses != set(map(float, plan['doses']))):
        raise ValueError('all assigned shards and all five doses required before analysis')
    validate_grid(scores, items, plan)
    lineage = {'input_seal_sha256': sha(inputs / 'INPUT_SEAL.json'),
               'score_seal_sha256': seal_hashes[0] if len(seal_hashes) == 1 else None,
               'score_seal_sha256s': seal_hashes, 'plan_sha256': sha(HERE / 'PLAN.json'),
               'run_plan_sha256': common_run_hash, 'collection_count': len(collections),
               'source_files': provenance_records[0]['source_files'], 'legacy_single_full_grid': legacy}
    if common_run_plan:
        lineage.update({k: common_run_plan[k] for k in ('run_id', 'operations_sha256', 'previous_gpu_seconds', 'global_cap_gpu_seconds')})
        lineage['worker_observed_new_provider_seconds'] = provider_seconds
        loss = sum(a.get('infrastructure_loss_gpu_seconds', 0) for a in common_run_plan['allocations'])
        lineage['new_infrastructure_loss_gpu_seconds'] = loss
        lineage['prior_reserved_plus_worker_elapsed_seconds'] = common_run_plan['previous_gpu_seconds'] + loss + provider_seconds
        lineage['reserved_total_gpu_seconds'] = common_run_plan['previous_gpu_seconds'] + sum(
            a['allocated_gpu_seconds'] + a.get('infrastructure_loss_gpu_seconds', 0) for a in common_run_plan['allocations'])
        lineage['final_provider_custody_status'] = 'Integrator must add retrieval and provider termination; worker elapsed is not final custody'
    return scores, items, lineage


def analyse(inputs, collection, labels_path, out):
    if out.exists():
        raise FileExistsError('analysis immutable; do not overwrite or rerun for another decision')
    plan = read(HERE / 'PLAN.json')
    scores, items, lineage = join_collections(inputs, collection, plan)
    # No private labels are opened until every score/seal/grid check above passes.
    if sha(labels_path) != plan['private_labels_sha256']:
        raise ValueError('private truth hash drift')
    all_labels = {r['id']: r for r in records(labels_path)}
    labels = {r['id']: all_labels[r['id']] for r in items}
    if any(r['split'] != 'test' for r in labels.values()):
        raise ValueError('test-only analysis required')
    result = compute(scores, labels, read(inputs / 'templates.json'), plan)
    result['lineage'] = lineage
    out.mkdir(parents=True)
    dump(out / 'metrics.json', result)
    p = result['primary']; rules = result['rules']
    lines = ['Prediction/rules (§128): a structure-specific adapter-dose drop supports the policy account; high structure AUROC at full dose supports the prompt account.', '',
             f"Adapter-policy rule: {'met' if rules['adapter_policy'] else 'not met'}. Prompt-account rule: {'met' if rules['prompt_account'] else 'not met'}.", '',
             f"Paired difference of class-median drops: {p['difference']:.4f}, 95% template-cluster CI [{p['ci95'][0]:.4f}, {p['ci95'][1]:.4f}].", '',
             'EXPLORATORY. Frozen W1 phrasings, both prompts, all five doses; no injected activation and no post-score selection.', '',
             '| Row | Prompt | Dose | AUROC | 95% CI |', '|---|---|---:|---:|---|']
    lines += [f"| {r['feature']} | {r['prompt']} | {r['dose']} | {r['auroc']:.4f} | [{r['ci95'][0]:.4f}, {r['ci95'][1]:.4f}] |" for r in result['rows']]
    (out / 'RESULTS.md').write_text('\n'.join(lines) + '\n')
    dump(out / 'ANALYSIS_SEAL.json', {'status': 'E33_ANALYSIS_SEALED', 'files': {n: sha(out / n) for n in ['metrics.json', 'RESULTS.md']}})
    return result['rules']


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ['inputs', 'labels', 'out']:
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--collections', '--collection', dest='collection', type=Path, nargs='+', required=True)
    a = p.parse_args()
    print(json.dumps(analyse(a.inputs, a.collection, a.labels, a.out)))
