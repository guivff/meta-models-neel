"""E37 sealed-grid CPU analysis: paired SFT−RL contrasts, fixed registered rules."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PREFIX = 'results/g_agreement/understand/e37/'
ARMS = ('RL', 'SFT')
CHANNELS = ('C1', 'C1prime', 'C2')
C2_ROWS = ('prose_paren', 'prose_quote', 'python_string', 'python_indent',
           'python_depth', 'list_depth', 'table_role')
CHECKPOINT_ARRIVAL_DEADLINE = 1793127600  # 2026-10-27 20:00 Europe/Zurich.


def read(path):
    return json.loads(Path(path).read_text())


def records(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def verify(directory, name):
    directory = Path(directory)
    seal = read(directory / name)
    for relative, digest in seal.get('files', {}).items():
        path = (directory / relative).resolve()
        if not path.is_relative_to(directory.resolve()) or sha(path) != digest:
            raise ValueError('sealed-file mismatch: ' + relative)
    return seal


def auc(scores, labels):
    x, y = np.asarray(scores, float), np.asarray(labels, bool)
    if not y.any() or y.all():
        raise ValueError('both classes required')
    difference = x[y, None] - x[~y][None, :]
    return float(np.mean((difference > 0) + .5 * (difference == 0)))


def wilson(k, n):
    if not 0 <= k <= n or n <= 0:
        raise ValueError('valid nonempty Wilson count required')
    p, z = k / n, 1.96
    denominator = 1 + z*z/n
    centre = (p + z*z/(2*n)) / denominator
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / denominator
    return {'correct': int(k), 'n': int(n), 'rate': p, 'ci95': [centre-half, centre+half]}


def validate_grid(scores, free, items, templates, plan):
    rows = plan['rows']
    if (len(rows) != 25 or len(set(rows)) != 25 or len(items) != 2100
            or len({r['id'] for r in items}) != 2100
            or Counter(r['feature'] for r in items) != Counter({f: 84 for f in rows})):
        raise ValueError('exact frozen W1 25×84 population required')
    if (set(plan['classes']) != set(rows) or set(plan['values']) != set(rows)
            or sum(plan['classes'][f] == 'semantic' for f in rows) != 9
            or any(len(plan['values'][f]) != 2 or len(set(plan['values'][f])) != 2 for f in rows)):
        raise ValueError('frozen 16 structure / 9 semantic row definitions required')
    if set(plan['c2_rows']) != set(C2_ROWS) or len(plan['c2_rows']) != 7:
        raise ValueError('exact seven frozen E15 valid rows required')
    if set(templates) != set(CHANNELS):
        raise ValueError('all three frozen paired-score channels required')
    for channel in CHANNELS:
        expected_rows = set(C2_ROWS) if channel == 'C2' else set(rows)
        if set(templates[channel]) != expected_rows:
            raise ValueError('frozen candidate row coverage mismatch')
        for pairs in templates[channel].values():
            if (not isinstance(pairs, list) or len(pairs) != 2
                    or any(not isinstance(pair, list) or len(pair) != 2
                           or any(not isinstance(x, str) or not x for x in pair) for pair in pairs)):
                raise ValueError('exact two frozen valid phrasing pairs required')
    lookup = {r['id']: r for r in items}
    for item in items:
        donor = lookup.get(item.get('donor_id'))
        if donor is None or donor['id'] == item['id'] or donor['feature'] != item['feature'] or donor.get('donor_id') != item['id']:
            raise ValueError('exact reciprocal same-row W1 donor map required')
    expected = {(item['id'], arm, channel, control)
                for item in items for arm in ARMS for channel in CHANNELS
                if item['feature'] in templates[channel]
                for control in (('matched', 'opposite') if channel == 'C2' else ('matched',))}
    actual = [(r['id'], r['arm'], r['channel'], r['control']) for r in scores]
    if len(actual) != 10752 or len(set(actual)) != len(actual) or set(actual) != expected:
        raise ValueError('complete unique 10752 paired-score records required')
    for r in scores:
        item = lookup[r['id']]
        values = np.asarray(r['scores'], float)
        if r['feature'] != item['feature'] or values.shape != (2,) or not np.isfinite(values).all():
            raise ValueError('finite complete frozen pair scores required')
        if not np.isfinite(r['score']) or abs(r['score'] - float(values.mean())) > 1e-8:
            raise ValueError('average exact paired log-odds before AUROC')
        if r['control'] == 'opposite' and r.get('donor_id') != item['donor_id']:
            raise ValueError('C2 opposite donor differs from frozen W1 mapping')
    free_keys = [(r['id'], r['arm']) for r in free]
    expected_free = {(r['id'], arm) for r in items for arm in ARMS}
    if len(free_keys) != 4200 or len(set(free_keys)) != len(free_keys) or set(free_keys) != expected_free:
        raise ValueError('complete unique 4200 native greedy readouts required')
    if any(r['feature'] != lookup[r['id']]['feature'] or not isinstance(r['raw'], str) for r in free):
        raise ValueError('native free-text schema mismatch')


def source_check(pins):
    root = HERE.parents[3].resolve()
    needed = {PREFIX + n for n in ('PLAN.json', 'runtime.py', 'analyse.py', 'PARITY_GATE.json', 'checkpoint_cpu.py', 'CHECKPOINT_MANIFEST_2026-10-26.json')}
    needed.add('projects/g_agreement/understand/e24_statements.py')
    if not isinstance(pins, dict) or not needed <= set(pins):
        raise ValueError('frozen source/statement-regex coverage required')
    for relative, digest in pins.items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file() or sha(path) != digest:
            raise ValueError('frozen analysis/runtime source drift')


def validate_gate_receipts(inputs, collection, provenance, seal):
    bindings = {'checkpoint_receipt.json': 'checkpoint_receipt_sha256',
                'parity_gate.json': 'parity_gate_sha256', 'PARITY_RESULT.json': 'parity_result_sha256',
                'predecessors.json': 'predecessors_sha256', 'CPU_TENSOR_CHECK.json': 'cpu_tensor_check_sha256'}
    if not set(bindings) | {'RUN.json'} <= set(seal['files']):
        raise ValueError('sealed checkpoint/parity/predecessor/run evidence required')
    for name, key in bindings.items():
        if provenance.get(key) != sha(collection / name):
            raise ValueError('copied gate receipt/provenance hash mismatch')
    checkpoint = read(collection / 'checkpoint_receipt.json')
    if (checkpoint.get('schema') != 'E37_SFT_RECEIPT_v1' or checkpoint.get('status') != 'RECEIVED_FROZEN'
            or checkpoint.get('issuer') != 'integrator' or checkpoint.get('provided_by') != 'Agam'
            or checkpoint.get('checkpoint_identity') != 's3d.omp4bp.s2/step251'
            or checkpoint.get('identity_verified') is not True or checkpoint.get('frozen_before_model_calls') is not True
            or checkpoint.get('model_calls_before_freeze') != 0):
        raise ValueError('verified Agam step251 checkpoint required')
    arrival = checkpoint.get('received_epoch')
    if type(arrival) not in (int, float) or not math.isfinite(arrival) or not 0 <= arrival <= CHECKPOINT_ARRIVAL_DEADLINE:
        raise ValueError('checkpoint arrived outside registered deadline')
    if not {'adapter_config.json', 'adapter_model.safetensors'} <= set(checkpoint.get('files', {})):
        raise ValueError('checkpoint bytes must be pinned')
    import importlib.util
    spec = importlib.util.spec_from_file_location('e37_cpu_analysis', HERE / 'checkpoint_cpu.py')
    cpu_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(cpu_module)
    cpu = cpu_module.validate_selection(read(collection / 'CPU_TENSOR_CHECK.json'), check_files=False)
    if (checkpoint.get('cpu_tensor_check_sha256') != sha(collection / 'CPU_TENSOR_CHECK.json')
            or checkpoint['files'] != cpu['selected_files']
            or checkpoint.get('selected_branch') != cpu['selected_branch']
            or provenance.get('selected_branch') != cpu['selected_branch']
            or checkpoint.get('received_epoch') != cpu['received_epoch']
            or provenance.get('readme_identity_claim_verified') != cpu['readme_identity_claim_verified']):
        raise ValueError('CPU checkpoint selection lineage mismatch')
    policy = read(collection / 'parity_gate.json')
    if policy.get('status') != 'REGISTERED_FROZEN' or sha(collection / 'parity_gate.json') != sha(HERE / 'PARITY_GATE.json'):
        raise ValueError('registered parity policy required')
    parity = read(collection / 'PARITY_RESULT.json')
    if (parity.get('status') != 'PASS' or
            parity.get('gate_order') != 'RL_three_row_reproduction_then_RL_smoke_then_SFT_smoke'):
        raise ValueError('passed smoke and RL reproduction gate required')
    if set(parity.get('smoke', {})) != set(ARMS):
        raise ValueError('both arms require native smoke repeat checks')
    for smoke in parity['smoke'].values():
        delta = smoke.get('max_abs_self_repeat_delta')
        if (smoke.get('items') != 20 or smoke.get('finite') is not True or smoke.get('threshold') != 1e-4
                or type(delta) not in (int, float) or not math.isfinite(delta) or not 0 <= delta <= 1e-4):
            raise ValueError('smoke self-repeat tolerance failed')
    reference = read(inputs / 'parity_inputs.json')['rl_reference_auc']
    if set(parity.get('RL_row_auroc', {})) != {'prose_sentiment', 'prose_paren', 'python_string'}:
        raise ValueError('all three frozen W1 reproduction rows required')
    for feature, cell in parity['RL_row_auroc'].items():
        values = [cell.get(k) for k in ('observed', 'W1_reference', 'absolute_delta')]
        if (any(type(v) not in (int, float) or not math.isfinite(v) for v in values)
                or cell.get('n') != 84 or cell.get('threshold') != .03
                or cell['W1_reference'] != reference[feature] or not 0 <= cell['observed'] <= 1
                or abs(cell['absolute_delta'] - abs(cell['observed']-cell['W1_reference'])) > 1e-12
                or not 0 <= cell['absolute_delta'] <= .03):
            raise ValueError('RL reproduction exceeds frozen W1 AUROC tolerance')
    predecessors = read(collection / 'predecessors.json')
    if (predecessors.get('schema') != 'E37_PREREQUISITE_COMPLETION_v1'
            or predecessors.get('issuer') != 'integrator'
            or predecessors.get('status') not in ('COMPLETE', 'READY_AFTER_PREDECESSORS')
            or set(predecessors.get('experiments', {})) != {'E33', 'E28'}
            or any(e.get('status') not in ('COMPLETE', 'NOT_RUN', 'NO_FIT', 'NO_GO')
                   or not e.get('receipts') for e in predecessors['experiments'].values())):
        raise ValueError('completed or explicitly closed E33 and E28 prerequisite receipts required')
    run = read(collection / 'RUN.json')
    if (run.get('status') != 'COMPLETE' or run.get('experiment') != 'E37'
            or any(run.get(key) != provenance.get(key) for key in ('input_seal_sha256', 'plan_sha256', 'source_files'))):
        raise ValueError('completed run receipt differs from score provenance')
    elapsed, allocated = run.get('provider_elapsed_seconds_at_worker_exit'), run.get('allocated_gpu_seconds')
    # 2026-10-26 §149: 1979 s prior custody + 11000 s allocation = 12979 s total.
    if (any(type(v) not in (int, float) or not math.isfinite(v) for v in (elapsed, allocated))
            or not 0 <= elapsed <= allocated <= 11000 or allocated <= 0
            or elapsed + 1979 > 12979
            or run.get('budget_includes_setup') is not True or run.get('budget_clock_resets') != 0 or run.get('GPU_count') != 1):
        raise ValueError('sealed run violated the 11000-second allocation or 12979-second cumulative cap')


def validate_collection(inputs, collection, plan):
    input_seal = verify(inputs, 'INPUT_SEAL.json')
    required_input = {'items.input.jsonl', 'templates.json', 'provenance.json', 'parity_inputs.json'}
    if not required_input <= set(input_seal.get('files', {})):
        raise ValueError('input seal lacks required file coverage')
    if read(inputs / 'provenance.json').get('plan_sha256') != sha(HERE / 'PLAN.json'):
        raise ValueError('input/frozen plan mismatch')
    seal = verify(collection, 'SCORE_SEAL.json')
    required = {'scores.jsonl', 'free.jsonl', 'provenance.json'}
    if seal.get('status') != 'E37_COMPLETE' or not required <= set(seal.get('files', {})):
        raise ValueError('complete E37 score and free-output seals required')
    provenance = read(collection / 'provenance.json')
    if (provenance.get('status') != 'COMPLETE'
            or provenance.get('input_seal_sha256') != sha(inputs / 'INPUT_SEAL.json')
            or provenance.get('plan_sha256') != sha(HERE / 'PLAN.json')):
        raise ValueError('complete matching E37 input/plan provenance required')
    source_check(provenance.get('source_files'))
    validate_gate_receipts(inputs, collection, provenance, seal)
    items, templates = records(inputs / 'items.input.jsonl'), read(inputs / 'templates.json')
    scores, free = records(collection / 'scores.jsonl'), records(collection / 'free.jsonl')
    validate_grid(scores, free, items, templates, plan)
    return items, templates, scores, free, provenance


def compute(scores, free, labels, templates, plan, n_boot=None):
    """Fixed rows, shared template-cluster draws across both arms and every channel."""
    sys.path.insert(0, str(ROOT))
    from projects.g_agreement.understand.e24_statements import statement
    n_boot = plan['bootstrap']['n_boot'] if n_boot is None else n_boot
    rng = np.random.default_rng(plan['bootstrap']['seed'])
    score_lookup = {(r['id'], r['arm'], r['channel'], r['control']): r['score'] for r in scores}
    free_lookup = {(r['id'], r['arm']): r['raw'] for r in free}
    paired_rows, naming_rows = [], []
    c1_points, c1_boots, naming_boots = {}, {}, {}
    for feature in plan['rows']:
        keys = sorted(k for k, r in labels.items() if r['feature'] == feature)
        y = np.array([labels[k]['value'] == plan['values'][feature][0] for k in keys], bool)
        group_names = sorted({labels[k]['cluster'] for k in keys})
        groups = [np.array([i for i, k in enumerate(keys) if labels[k]['cluster'] == group]) for group in group_names]
        if len(keys) != 84 or len(groups) != 6 or any(len(set(y[g])) != 2 for g in groups):
            raise ValueError('frozen 84-item six-cluster two-class W1 row required')
        draws = [np.concatenate([groups[g] for g in rng.integers(0, len(groups), len(groups))]) for _ in range(n_boot)]
        for channel in CHANNELS:
            if feature not in templates[channel]:
                continue
            for control in (('matched', 'opposite') if channel == 'C2' else ('matched',)):
                matrix = np.array([[score_lookup[k, arm, channel, control] for arm in ARMS] for k in keys])
                point = np.array([auc(matrix[:, a], y) for a in range(2)])
                boot = np.array([[auc(matrix[take, a], y[take]) for a in range(2)] for take in draws])
                delta = boot[:, 1] - boot[:, 0]
                cell = {'feature': feature, 'class': plan['classes'][feature], 'channel': channel, 'control': control,
                    'n_items': 84, 'n_clusters': 6,
                    'arms': {arm: {'auroc': float(point[a]), 'ci95': np.quantile(boot[:, a], [.025, .975]).tolist()}
                             for a, arm in enumerate(ARMS)},
                    'SFT_minus_RL': float(point[1]-point[0]), 'difference_ci95': np.quantile(delta, [.025, .975]).tolist()}
                paired_rows.append(cell)
                if channel == 'C1':
                    c1_points[feature], c1_boots[feature] = point, boot
        statuses = {arm: [statement(feature, free_lookup[k, arm]) for k in keys] for arm in ARMS}
        naming = {'feature': feature, 'class': plan['classes'][feature], 'channel': 'C4',
                  'statement_statuses': {arm: dict(Counter(statuses[arm])) for arm in ARMS}}
        if any(s == 'not_structure' for arm in ARMS for s in statuses[arm]):
            naming.update(status='NOT_EVALUABLE_NO_FROZEN_REGEX', arms={arm: None for arm in ARMS},
                          SFT_minus_RL=None, difference_ci95=None)
        else:
            correct = np.array([[statuses[arm][i] == ('A' if y[i] else 'B') for arm in ARMS] for i in range(84)], float)
            boot = np.array([correct[take].mean(axis=0) for take in draws])
            naming.update(status='EVALUABLE', arms={arm: wilson(int(correct[:, a].sum()), 84) for a, arm in enumerate(ARMS)},
                SFT_minus_RL=float(correct[:, 1].mean()-correct[:, 0].mean()),
                difference_ci95=np.quantile(boot[:, 1]-boot[:, 0], [.025, .975]).tolist())
            naming_boots[feature] = boot
        naming_rows.append(naming)
    medians = {}
    for cls in ('structure', 'content'):
        selected = [f for f in plan['rows'] if (plan['classes'][f] == 'semantic') == (cls == 'content')]
        point = np.median(np.stack([c1_points[f] for f in selected]), axis=0)
        boot = np.median(np.stack([c1_boots[f] for f in selected], axis=1), axis=1)
        medians[cls] = {'arms': dict(zip(ARMS, map(float, point))), 'SFT_minus_RL': float(point[1]-point[0]),
                        'difference_ci95': np.quantile(boot[:, 1]-boot[:, 0], [.025, .975]).tolist()}
    return finish_rules(paired_rows, naming_rows, naming_boots, medians, plan, n_boot)


def finish_rules(paired_rows, naming_rows, naming_boots, medians, plan, n_boot):
    c2 = [r for r in paired_rows if r['channel'] == 'C2' and r['control'] == 'matched']
    inherited = [r['feature'] for r in c2 if abs(r['SFT_minus_RL']) <= .05
                 and min(r['arms'][a]['auroc'] for a in ARMS) >= .65]
    c1_structure = [r for r in paired_rows if r['channel'] == 'C1' and r['class'] != 'semantic']
    changed = [r['feature'] for r in c1_structure if abs(r['SFT_minus_RL']) >= .15
               and (r['difference_ci95'][0] > 0 or r['difference_ci95'][1] < 0)]
    descriptive = [{'feature': r['feature'], 'RL_minus_SFT': -r['SFT_minus_RL'],
                    'difference_ci95': [-r['difference_ci95'][1], -r['difference_ci95'][0]]}
                   for r in paired_rows if r['channel'] == 'C1' and r['class'] == 'semantic']
    structure_naming = [r for r in naming_rows if r['class'] != 'semantic']
    evaluable = bool(structure_naming) and all(r['status'] == 'EVALUABLE' for r in structure_naming)
    pooled = {arm: None for arm in ARMS}
    pooled_delta, pooled_ci = None, None
    pooled_met = per_row_met = None
    if evaluable:
        pooled = {arm: wilson(sum(r['arms'][arm]['correct'] for r in structure_naming),
                             sum(r['arms'][arm]['n'] for r in structure_naming)) for arm in ARMS}
        boot = np.mean(np.stack([naming_boots[r['feature']] for r in structure_naming], axis=1), axis=1)
        pooled_delta = pooled['SFT']['rate'] - pooled['RL']['rate']
        pooled_ci = np.quantile(boot[:, 1]-boot[:, 0], [.025, .975]).tolist()
        pooled_met = all(pooled[a]['ci95'][1] < .05 for a in ARMS)
        per_row_met = all(r['arms'][a]['ci95'][1] < .05 for r in structure_naming for a in ARMS)
    r4_scope = plan.get('r4_scope')
    if r4_scope not in (None, 'pooled', 'all_rows'):
        raise ValueError('unknown frozen R4 scope')
    r4 = {'scope': r4_scope, 'status': 'PENDING_COORDINATOR_RULING' if r4_scope is None else
          'EVALUABLE' if evaluable else 'NOT_EVALUABLE_NO_FROZEN_REGEX',
          'met': None if r4_scope is None else pooled_met if r4_scope == 'pooled' else per_row_met,
          'pooled': {'met': pooled_met, 'arms': pooled, 'SFT_minus_RL': pooled_delta, 'difference_ci95': pooled_ci},
          'all_rows': {'met': per_row_met, 'row_count': len(structure_naming)},
          'strict_threshold': 'Wilson upper < .05 for both arms'}
    return {'experiment': 'E37', 'status': 'EXPLORATORY_E37', 'paired_rows': paired_rows,
        'naming_rows': naming_rows, 'C1_class_medians': medians,
        'rules': {'R1': {'met': len(inherited) >= 5, 'qualifying_rows': inherited, 'n_valid_rows': len(c2)},
                  'R2': {'met': abs(medians['structure']['SFT_minus_RL']) <= .05 and not changed,
                         'structure_median_SFT_minus_RL': medians['structure']['SFT_minus_RL'],
                         'large_significant_structure_rows': changed},
                  'R3': {'status': 'DESCRIPTIVE', 'content_RL_minus_SFT': descriptive}, 'R4': r4},
        'bootstrap': {**plan['bootstrap'], 'n_boot': n_boot,
                      'pairing': 'same within-row template-cluster draws across both arms and all channels; no rows resampled'},
        'statement_policy': 'unchanged E24 detector; exact A/B correct; both/neither incorrect; absent regex not evaluable'}


def analyse(inputs, collection, labels_path, out):
    inputs, collection, labels_path, out = map(Path, (inputs, collection, labels_path, out))
    if out.exists():
        raise FileExistsError('analysis is immutable; use a new destination')
    plan = read(HERE / 'PLAN.json')
    items, templates, scores, free, provenance = validate_collection(inputs, collection, plan)
    # No full private truth file is opened until every raw grid/seal above is valid.
    if sha(labels_path) != plan['private_labels_sha256']:
        raise ValueError('frozen W1 private truth hash mismatch')
    raw_labels = records(labels_path)
    full = {r['id']: r for r in raw_labels}
    if len(full) != len(raw_labels):
        raise ValueError('duplicate private label IDs')
    labels = {}
    for item in items:
        label = full[item['id']]
        if label['feature'] != item['feature'] or label['split'] != 'test' or label['value'] not in plan['values'][item['feature']]:
            raise ValueError('frozen test label identity mismatch')
        donor = full[item['donor_id']]
        if donor['value'] == label['value'] or donor['cluster'] != label['cluster'] or donor['feature'] != label['feature']:
            raise ValueError('frozen opposite donor label/cluster mismatch')
        labels[item['id']] = label
    result = compute(scores, free, labels, templates, plan)
    result['lineage'] = {'plan_sha256': sha(HERE / 'PLAN.json'), 'input_seal_sha256': sha(inputs / 'INPUT_SEAL.json'),
        'score_seal_sha256': sha(collection / 'SCORE_SEAL.json'), 'source_files': provenance['source_files']}
    result['lineage'].update({k: provenance[k] for k in ('checkpoint_receipt_sha256', 'parity_gate_sha256',
                             'parity_result_sha256', 'predecessors_sha256', 'cpu_tensor_check_sha256', 'selected_branch', 'readme_identity_claim_verified')})
    out.mkdir(parents=True)
    dump(out / 'metrics.json', result)
    verdict = lambda value: 'met' if value is True else 'not met' if value is False else 'not evaluable'
    lines = ['# E37 results', '', 'Registered prediction (§134): R1, R2 and R4 hold; R3 is descriptive.', '']
    lines += ['Checkpoint branch: ' + provenance['selected_branch'] + '.',
              'README identity claim: ' + ('verified by exact CPU tensor comparison.' if provenance['readme_identity_claim_verified'] else 'UNVERIFIED; see sealed CPU tensor receipt for differences or download failure.'), '']
    for rule in ('R1', 'R2', 'R4'):
        lines.append('- ' + rule + ': ' + verdict(result['rules'][rule]['met']) + '.')
    lines += ['', 'All paired differences are SFT minus RL; R3 explicitly reverses the sign to report RL minus SFT.',
              'C1′ and C2 opposite-donor results are descriptive. Semantic C4 rows lacking E24 detectors remain not evaluable.', '',
              '| Row | Channel | Control | RL AUROC | SFT AUROC | SFT−RL | Paired 95% CI |',
              '|---|---|---|---:|---:|---:|---|']
    for r in result['paired_rows']:
        lo, hi = r['difference_ci95']
        lines.append(f"| {r['feature']} | {r['channel']} | {r['control']} | {r['arms']['RL']['auroc']:.4f} | {r['arms']['SFT']['auroc']:.4f} | {r['SFT_minus_RL']:.4f} | [{lo:.4f}, {hi:.4f}] |")
    lines += ['', 'C4 pooled and per-row Wilson summaries, paired cluster differences, and the frozen R4 interpretation are retained in metrics.json.', '']
    (out / 'RESULTS.md').write_text('\n'.join(lines))
    dump(out / 'ANALYSIS_SEAL.json', {'status': 'E37_ANALYSIS_SEALED',
         'files': {n: sha(out / n) for n in ('metrics.json', 'RESULTS.md')}})
    return result['rules']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('inputs', 'collection', 'labels', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(analyse(args.inputs, args.collection, args.labels, args.out), sort_keys=True))
