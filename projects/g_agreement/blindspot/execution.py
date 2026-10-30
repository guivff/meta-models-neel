"""Additive W1 execution units over an unchanged, sealed item bank.

The worker plan partitions whole rows; it contains no per-item ground truth or
split membership. A separate local analysis seal binds the priority dev labels.
Nothing in this module loads model weights, runs a reader, or edits the bank.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from . import protocol as P

PRIORITY_FEATURES = ('table_column', 'prose_paren', 'prose_sentiment', 'python_effect', 'latex_subject')
UNITS = ('priority', 'remainder_a', 'remainder_b')
SCHEMA = 'blindspot-execution-v1'
TRAINING_SCHEMA = 'blindspot-training-labels-v1'
TRAINING_FILE = 'priority.dev.DO_NOT_STAGE.jsonl'
TRAINING_SEAL = 'TRAINING_LABEL_SEAL.json'
BASELINE_SOURCE_COMMIT = 'fe7c7513d592ed384ab3930ec07ec1efb830862f'
SOURCE_POLICY = 'user-authorized execution-only update; frozen bank unchanged'
MODES = {
    'one_pod': {'pod_a': ['priority', 'remainder_a', 'remainder_b']},
    'two_pods': {'pod_a': ['priority', 'remainder_a'], 'pod_b': ['remainder_b']},
}
_PLAN_KEYS = {
    'schema', 'status', 'experiment', 'input_seal_sha256', 'manifest_sha256',
    'items_input_sha256', 'templates_sha256', 'feature_order', 'units', 'modes',
    'training_labels', 'runtime_source_files', 'baseline_source_commit',
    'baseline_source_files', 'source_policy', 'free_batch_policy',
}


def _digest(value, size=64):
    return isinstance(value, str) and len(value) == size and all(c in '0123456789abcdef' for c in value)


def _exclusive_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def _read_bank(bank):
    bank = Path(bank)
    seal = P.verify(bank, 'INPUT_SEAL.json')
    needed = {'manifest.json', 'items.input.jsonl', 'templates.json', 'provenance.json'}
    if seal.get('status') != 'INPUTS_FROZEN' or not needed <= set(seal.get('files', {})):
        raise ValueError('execution requires the full frozen bank seal')
    manifest = json.loads((bank/'manifest.json').read_text())
    if manifest.get('experiment') != 'W1':
        raise ValueError('priority execution plan applies only to W1')
    items = P.rows(bank/'items.input.jsonl')
    templates = json.loads((bank/'templates.json').read_text())
    ids = [row.get('id') for row in items]
    if not items or any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('empty bank or repeated item ID')
    if any(set(row) != {'id', 'feature', 'ids', 'donor_id'} for row in items):
        raise ValueError('execution worker inputs must remain label-free')
    if {row['feature'] for row in items} != set(templates) or set(templates) != set(manifest['rows']):
        raise ValueError('bank feature coverage mismatch')
    index = {row['id']: row for row in items}
    for row in items:
        if not row['ids'] or any(type(t) is not int or t < 0 for t in row['ids']):
            raise ValueError('invalid bank token IDs')
        donor = row['donor_id']
        ordinal = templates[row['feature']].get('kind') == 'ordinal'
        if donor is None:
            if not ordinal:
                raise ValueError('binary item lacks donor')
        elif (ordinal or donor == row['id'] or donor not in index
              or index[donor]['donor_id'] != row['id']
              or index[donor]['feature'] != row['feature']
              or len(index[donor]['ids']) != len(row['ids'])):
            raise ValueError('invalid donor relation')
    counts = Counter(row['feature'] for row in items)
    if any(counts[f] != manifest['rows'][f]['n'] for f in counts):
        raise ValueError('item count differs from frozen manifest')
    return items, templates, manifest


def _layout(items):
    canonical = list(dict.fromkeys(row['feature'] for row in items))
    if not set(PRIORITY_FEATURES) <= set(canonical):
        raise ValueError('priority rows missing from frozen bank')
    rest = [f for f in canonical if f not in PRIORITY_FEATURES]
    if len(rest) < 2:
        raise ValueError('need two nonempty remainder units')
    counts = Counter(row['feature'] for row in items)
    groups = {'priority': list(PRIORITY_FEATURES), 'remainder_a': [], 'remainder_b': []}
    loads = {'remainder_a': sum(counts[f] for f in PRIORITY_FEATURES), 'remainder_b': 0}
    # Fixed canonical row order; balance the two complete pod allocations. Pod A
    # already owns priority, so include that load before assigning remainders.
    # Ties go to A. No scores, labels or semantic classes influence the partition.
    for feature in rest:
        unit = min(('remainder_a', 'remainder_b'), key=lambda name: (loads[name], name))
        groups[unit].append(feature)
        loads[unit] += counts[feature]
    units = {}
    for name in UNITS:
        chosen = set(groups[name])
        unit_ids = ([row['id'] for feature in PRIORITY_FEATURES
                     for row in items if row['feature'] == feature] if name == 'priority'
                    else [row['id'] for row in items if row['feature'] in chosen])
        units[name] = {'features': groups[name], 'item_ids': unit_ids, 'count': len(unit_ids)}
    return list(PRIORITY_FEATURES) + rest, units


def _training_count(manifest):
    return sum(manifest['rows'][f]['split_counts']['dev'] for f in PRIORITY_FEATURES)


def _check_source_mapping(mapping):
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError('source file hash mapping required')
    if any(not isinstance(path, str) or Path(path).is_absolute() or '..' in Path(path).parts
           or not _digest(digest) for path, digest in mapping.items()):
        raise ValueError('invalid source file hash mapping')


def _validate(plan, bank, items, manifest):
    bank = Path(bank)
    if not isinstance(plan, dict) or set(plan) != _PLAN_KEYS:
        raise ValueError('unexpected worker execution-plan fields; labels and split IDs are forbidden')
    if plan['schema'] != SCHEMA or plan['status'] != 'FROZEN' or plan['experiment'] != 'W1':
        raise ValueError('unrecognized execution plan')
    for field, filename in (
        ('input_seal_sha256', 'INPUT_SEAL.json'), ('manifest_sha256', 'manifest.json'),
        ('items_input_sha256', 'items.input.jsonl'), ('templates_sha256', 'templates.json'),
    ):
        if plan[field] != P.sha(bank/filename):
            raise ValueError('execution plan does not bind this bank: ' + field)
    features, expected_units = _layout(items)
    if plan['feature_order'] != features or plan['units'] != expected_units:
        raise ValueError('execution units differ from the immutable canonical whole-row partition')
    # Explicit coverage and donor-closure checks survive future layout extensions.
    full_ids = {row['id'] for row in items}
    combined = [key for name in UNITS for key in plan['units'][name]['item_ids']]
    if set(combined) != full_ids or len(combined) != len(full_ids):
        raise ValueError('execution units must cover every item exactly once')
    for name in UNITS:
        selected = set(plan['units'][name]['item_ids'])
        if any(row['donor_id'] is not None and row['donor_id'] not in selected
               for row in items if row['id'] in selected):
            raise ValueError('execution unit is not donor-closed')
    if plan['modes'] != MODES or plan['free_batch_policy'] != 'canonical_batch_intersections':
        raise ValueError('execution scheduling/seed policy differs from frozen protocol')
    training = plan['training_labels']
    if (not isinstance(training, dict) or set(training) != {'sha256', 'relative_path', 'count'}
            or not _digest(training['sha256']) or training['relative_path'] != TRAINING_FILE
            or type(training['count']) is not int or training['count'] != _training_count(manifest)):
        raise ValueError('invalid label-free training-file commitment')
    if plan['baseline_source_files'] != manifest['source_files']:
        raise ValueError('baseline source mapping differs from frozen manifest')
    if not _digest(plan['baseline_source_commit'], 40) or plan['source_policy'] != SOURCE_POLICY:
        raise ValueError('missing baseline source commit or execution-only policy')
    _check_source_mapping(plan['runtime_source_files'])
    _check_source_mapping(plan['baseline_source_files'])
    return plan


def validate_plan(bank, path):
    """Validate only label-free inputs and plan bytes; never open the labels."""
    items, _, manifest = _read_bank(bank)
    return _validate(json.loads(Path(path).read_text()), bank, items, manifest)


def select_unit(plan_path, unit, bank, items):
    """Select frozen unit order, retaining each item's original full-bank index.

    Priority runs in its explicit feature order; siblings within a feature and
    both remainder units retain canonical order. Indices need not be monotonic.
    """
    canonical, _, manifest = _read_bank(bank)
    if items != canonical:
        raise ValueError('selection requires unchanged canonical full-bank worker inputs')
    plan = _validate(json.loads(Path(plan_path).read_text()), bank, canonical, manifest)
    if unit not in UNITS:
        raise ValueError('unknown execution unit')
    index = {row['id']: i for i, row in enumerate(canonical)}
    indices = [index[key] for key in plan['units'][unit]['item_ids']]
    return {'items': [canonical[i] for i in indices], 'indices': indices,
            'binding': {'execution_plan_sha256': P.sha(plan_path), 'execution_unit': unit}}


def select_inputs(bank, plan_path, unit):
    """Convenience reader inputs without importing run.py or opening labels."""
    items, templates, _ = _read_bank(bank)
    selection = select_unit(plan_path, unit, bank, items)
    selected = selection['items']
    index = {row['id']: i for i, row in enumerate(selected)}
    donors = [None if row['donor_id'] is None else index[row['donor_id']] for row in selected]
    relevant = {f: templates[f] for f in dict.fromkeys(row['feature'] for row in selected)}
    return selected, donors, relevant


def validate_assignment(assignment, plan_path, unit, bank):
    """Unit admission only; protocol.admit owns fleet and aggregate-budget checks."""
    plan = validate_plan(bank, plan_path)
    if not isinstance(assignment, dict):
        assignment = json.loads(Path(assignment).read_text())
    allowed = assignment.get('execution_units')
    if (unit not in UNITS or assignment.get('execution_plan_sha256') != P.sha(plan_path)
            or not isinstance(allowed, list) or len(allowed) != len(set(allowed))
            or any(name not in UNITS for name in allowed) or unit not in allowed):
        raise ValueError('assignment does not authorize this execution plan and unit')
    return plan


def _training_rows(bank, items, manifest):
    # This helper is builder-only, on the local analysis side. Workers never call it.
    bank = Path(bank)
    source = bank/'labels.DO_NOT_STAGE.jsonl'
    source_hash = P.sha(source)
    provenance = json.loads((bank/'provenance.json').read_text())
    if (source_hash != manifest['files']['labels.DO_NOT_STAGE.jsonl']
            or source_hash != provenance['labels_sha256']):
        raise ValueError('frozen source labels hash mismatch')
    source_rows = P.rows(source)
    all_ids = [row['id'] for row in items]
    if [row['id'] for row in source_rows] != all_ids:
        raise ValueError('frozen labels do not follow full-bank order')
    selected = [row for row in source_rows if row['feature'] in PRIORITY_FEATURES and row['split'] == 'dev']
    if len(selected) != _training_count(manifest) or len({r['id'] for r in selected}) != len(selected):
        raise ValueError('training label coverage mismatch')
    for feature in PRIORITY_FEATURES:
        rows = [row for row in selected if row['feature'] == feature]
        expected = manifest['rows'][feature]['split_counts']['dev']
        if len(rows) != expected or len({r['value'] for r in rows}) != 2:
            raise ValueError('priority training row missing a class or item')
        if len(set(Counter(r['value'] for r in rows).values())) != 1:
            raise ValueError('priority training labels are not balanced')
        dev_clusters = {r['cluster'] for r in rows}
        test_clusters = {r['cluster'] for r in source_rows if r['feature'] == feature and r['split'] == 'test'}
        if dev_clusters & test_clusters:
            raise ValueError('priority dev/test template leakage')
    return selected, source_hash


def build_plan(bank, plan_path, training_dir, *, runtime_source_files=None,
               baseline_source_commit=BASELINE_SOURCE_COMMIT):
    """Create immutable plan plus local dev-only labels; never modify bank bytes."""
    bank, plan_path, training_dir = Path(bank), Path(plan_path), Path(training_dir)
    for destination in (plan_path, training_dir):
        if destination.resolve() == bank.resolve() or bank.resolve() in destination.resolve().parents:
            raise ValueError('execution additions must be outside the frozen bank')
    if plan_path.exists() or (training_dir/TRAINING_FILE).exists() or (training_dir/TRAINING_SEAL).exists():
        raise FileExistsError('preserve existing execution plan and training-label seal')
    items, _, manifest = _read_bank(bank)
    training, source_hash = _training_rows(bank, items, manifest)
    feature_order, units = _layout(items)
    runtime = P.code_hashes() if runtime_source_files is None else runtime_source_files
    plan = {'schema': SCHEMA, 'status': 'FROZEN', 'experiment': 'W1',
            'input_seal_sha256': P.sha(bank/'INPUT_SEAL.json'), 'manifest_sha256': P.sha(bank/'manifest.json'),
            'items_input_sha256': P.sha(bank/'items.input.jsonl'), 'templates_sha256': P.sha(bank/'templates.json'),
            'feature_order': feature_order, 'units': units, 'modes': MODES,
            'training_labels': {'sha256': '0'*64, 'relative_path': TRAINING_FILE, 'count': len(training)},
            'runtime_source_files': runtime, 'baseline_source_commit': baseline_source_commit,
            'baseline_source_files': manifest['source_files'], 'source_policy': SOURCE_POLICY,
            'free_batch_policy': 'canonical_batch_intersections'}
    _validate(plan, bank, items, manifest)
    training_dir.mkdir(parents=True, exist_ok=True)
    P.jsonl(training_dir/TRAINING_FILE, training)
    training_hash = P.sha(training_dir/TRAINING_FILE)
    seal = {'schema': TRAINING_SCHEMA, 'status': 'DEV_ONLY_FROM_FROZEN_LABELS',
            'input_seal_sha256': plan['input_seal_sha256'], 'manifest_sha256': plan['manifest_sha256'],
            'source_labels_sha256': source_hash, 'training_labels_sha256': training_hash,
            'training_labels_file': TRAINING_FILE, 'count': len(training),
            'ordered_train_ids': [row['id'] for row in training], 'features': list(PRIORITY_FEATURES)}
    _exclusive_json(training_dir/TRAINING_SEAL, seal)
    plan['training_labels']['sha256'] = training_hash
    _exclusive_json(plan_path, plan)
    return validate_plan(bank, plan_path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bank', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--training-dir', type=Path, required=True)
    parser.add_argument('--baseline-source-commit', default=BASELINE_SOURCE_COMMIT)
    args = parser.parse_args(argv)
    plan = build_plan(args.bank, args.out, args.training_dir, baseline_source_commit=args.baseline_source_commit)
    print(json.dumps({'execution_plan_sha256': P.sha(args.out),
                      'units': {name: row['count'] for name, row in plan['units'].items()},
                      'training_labels': plan['training_labels']['count']}, sort_keys=True))


if __name__ == '__main__':
    main()
