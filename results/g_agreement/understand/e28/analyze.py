"""CPU analysis of sealed E28 outputs. No scoring, threshold fitting, or sign flipping."""
from __future__ import annotations
import argparse
import math
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract as C
sys.path.insert(0, str(C.ROOT))


def crossed(values):
    return next((step for step, value in zip(C.CHECKPOINTS, values) if value >= .80), None)


def validate_operational_gates(root, receipt, assignment):
    """2026-10-25: verify authorized environment/parity evidence before unblinding."""
    bindings = {'TRAINING_ENVIRONMENT.json': 'environment_manifest_sha256',
                'ENVIRONMENT_RUNTIME_RESULT.json': 'environment_runtime_result_sha256',
                'PARITY_RESULT.json': 'parity_result_sha256', 'PARITY_SCORES.jsonl': 'parity_scores_sha256'}
    for name, key in bindings.items():
        if receipt.get(key) != C.sha(root / name):
            raise ValueError('missing or altered E28 environment/parity receipt')
    if (assignment.get('training_environment_sha256') != receipt['environment_manifest_sha256']
            or assignment.get('parity_input_seal_sha256') != receipt.get('parity_input_seal_sha256')
            or receipt['parity_input_seal_sha256'] != C.read(C.HERE / 'PARITY_PREPARATION_2026-10-25.json')['parity_input_seal_sha256']):
        raise ValueError('environment/parity assignment mismatch')
    parity = C.read(root / 'PARITY_RESULT.json')
    reference = C.read(root / 'PARITY_REFERENCE.json')
    expected = {'prose_sentiment': 0.9109977324263039, 'prose_paren': 0.4846938775510204,
                'python_string': 0.6439909297052154}
    if (parity.get('schema') != 'E28_PRETRAIN_PARITY_RESULT_v1' or parity.get('status') != 'PASS'
            or parity.get('optimizer_steps_before_gate') != 0 or set(parity.get('rows', {})) != set(expected)
            or parity.get('environment_manifest_sha256') != receipt['environment_manifest_sha256']
            or parity.get('parity_input_seal_sha256') != receipt['parity_input_seal_sha256']
            or parity.get('raw_scores_sha256') != receipt['parity_scores_sha256']
            or parity.get('reference_sha256') != C.sha(root / 'PARITY_REFERENCE.json')
            or reference.get('reference_auc') != expected or reference.get('max_abs_auroc_delta') != .03
            or reference.get('original_e28_input_seal_sha256') != assignment['input_seal_sha256']):
        raise ValueError('authorized pre-training parity evidence required')
    for row, cell in parity['rows'].items():
        values = [cell.get(k) for k in ('observed', 'reference', 'absolute_delta')]
        if (any(type(v) not in (int, float) or not math.isfinite(v) for v in values)
                or cell.get('n') != 84 or cell.get('threshold') != .03 or cell['reference'] != expected[row]
                or not 0 <= cell['observed'] <= 1
                or abs(cell['absolute_delta'] - abs(cell['observed'] - cell['reference'])) > 1e-12
                or not 0 <= cell['absolute_delta'] <= .03):
            raise ValueError('E28 W1 AUROC environment parity failed')
    ready = C.read(root / 'ENVIRONMENT_RUNTIME_RESULT.json')
    epoch, gate_epoch = ready.get('completed_epoch'), parity.get('completed_epoch')
    if (ready.get('schema') != 'E28_TRAINING_ENV_RUNTIME_v1' or ready.get('status') != 'TRAINING_ENVIRONMENT_READY'
            or ready.get('device') != 'cuda' or ready.get('real_cuda_backward') is not True
            or ready.get('finite_loss') is not True or ready.get('finite_gradients') is not True
            or ready.get('fresh_lora_only') is not True or ready.get('optimizer_steps_in_readiness') != 1
            or ready.get('environment_manifest_sha256') != receipt['environment_manifest_sha256']
            or ready.get('parity_result_sha256') != receipt['parity_result_sha256']
            or ready.get('readiness_deadline_epoch') != 1793012400
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in (epoch, gate_epoch))
            or not 0 < gate_epoch <= epoch <= 1793012400):
        raise ValueError('real CUDA backward readiness by Monday noon required')


def analysis(input_dir, outputs, out):
    import numpy as np
    import common
    from common.stats import wilson
    from mats.metrics import auroc_labels
    from projects.g_agreement.understand.e24_statements import statement
    C.verify(C.ROOT, str((C.HERE / 'SOURCE_MANIFEST.json').relative_to(C.ROOT)))
    C.verify(input_dir)
    test = C.rows(input_dir / 'test.jsonl')
    directories = {}
    for root in outputs:
        receipt = C.read(root / 'RUN_RECEIPT.json')
        if receipt['status'] != 'COMPLETE_FULL_ASSIGNED_GRID' or receipt['plan_sha256'] != C.sha(C.HERE / 'PLAN.json'):
            raise ValueError('all assigned runs must be complete before unblinding')
        assignment = C.read(root / 'assignment.json')
        C.assignment(assignment, now=assignment['provider_created_epoch'])
        elapsed = receipt.get('gpu_seconds_provider')
        if (receipt.get('previous_gpu_seconds') != assignment['previous_gpu_seconds']
                or type(elapsed) not in (int, float) or not math.isfinite(elapsed)
                or not 0 <= elapsed <= assignment['allocated_gpu_seconds']):
            raise ValueError('E28 prior custody or live provider budget differs')
        if assignment['input_seal_sha256'] != C.sha(input_dir / 'INPUT_SEAL.json'):
            raise ValueError('scores originate from another input')
        validate_operational_gates(root, receipt, assignment)
        for row, arm in receipt['runs']:
            if (row, arm) in directories:
                raise ValueError('duplicate row/arm output')
            d = root / (row + '__' + arm)
            C.verify(d, 'SCORE_SEAL.json')
            directories[row, arm] = d
    if set(directories) != set(C.RUNS):
        raise ValueError('all fourteen registered runs required')
    # Validate every scientific score and free-output cell before opening the label key.
    for (row, arm), d in directories.items():
        ids = {r['id'] for r in test if r['feature'] == row}
        for step in C.CHECKPOINTS:
            raw = C.rows(d / ('asked.' + str(step) + '.jsonl'))
            if len(raw) != 84 or {r['id'] for r in raw} != ids:
                raise ValueError('incomplete checkpoint before unblinding')
            values = np.array([r['scores'] for r in raw], float)
            if values.shape != (84, 2) or not np.isfinite(values).all():
                raise ValueError('invalid score cell before unblinding')
        free_rows = C.rows(d / 'free.400.jsonl')
        if len(free_rows) != 84 or {r['id'] for r in free_rows} != ids or any(not isinstance(r['raw'], str) for r in free_rows):
            raise ValueError('incomplete free grid before unblinding')
    labels_path = input_dir / 'test.labels.DO_NOT_STAGE.jsonl'
    preparation = C.read(C.HERE / 'PREPARATION.json')
    if C.sha(labels_path) != preparation['private_test_labels_sha256']:
        raise ValueError('frozen local analysis label key mismatch')
    labels = C.rows(labels_path)
    lookup = {r['id']: r for r in labels}
    if set(lookup) != {r['id'] for r in test} or len(labels) != len(lookup):
        raise ValueError('exact test-label coverage required')
    cells, histories = [], {}
    for row in C.ROWS:
        ids = sorted(r['id'] for r in test if r['feature'] == row)
        y = np.array([lookup[k]['y'] for k in ids], int)
        groups = np.array([lookup[k]['cluster'] for k in ids])
        clusters = sorted(set(groups))
        rng = np.random.default_rng(C.SEED)
        draws = [np.concatenate([np.flatnonzero(groups == g) for g in rng.choice(clusters, len(clusters), replace=True)])
                 for _ in range(2000)]
        for arm in ('L', 'B', 'S'):
            if (row, arm) not in directories:
                continue
            d = directories[row, arm]
            scores = []
            for step in C.CHECKPOINTS:
                raw = C.rows(d / ('asked.' + str(step) + '.jsonl'))
                index = {r['id']: r for r in raw}
                if len(raw) != 84 or set(index) != set(ids):
                    raise ValueError('incomplete checkpoint')
                a = np.array([index[k]['scores'] for k in ids], float)
                if a.shape != (84, 2) or not np.isfinite(a).all():
                    raise ValueError('invalid native paired scores')
                scores.append(a.mean(axis=1))
            scores = np.stack(scores)
            auc = [float(auroc_labels(x, y)) for x in scores]
            boot = np.array([[auroc_labels(x[take], y[take]) for x in scores] for take in draws], float)
            ci = np.quantile(boot, [.025, .975], axis=0)
            fast = any(step <= 100 and value >= .80 and ci[0, i] >= .65 for i, (step, value) in enumerate(zip(C.CHECKPOINTS, auc)))
            free = C.rows(d / 'free.400.jsonl')
            if len(free) != 84 or {r['id'] for r in free} != set(ids):
                raise ValueError('complete 84 native free readouts required')
            statuses = [statement(row, r['raw']) for r in free]
            naming = None if row == 'prose_sentiment' else sum(x in ('A', 'B', 'both') for x in statuses)
            correct = None if naming is None else sum(statement(row, r['raw']) == ('A' if lookup[r['id']]['y'] else 'B') for r in free)
            cell = {'row': row, 'arm': arm, 'asked': [{'step': step, 'auroc': auc[i], 'ci95': ci[:, i].tolist()}
                   for i, step in enumerate(C.CHECKPOINTS)], 'fast': fast, 'first_step_ge_080': crossed(auc),
                   'right_censored_at400': crossed(auc) is None,
                   'free_statement_statuses': {s: statuses.count(s) for s in sorted(set(statuses))},
                   'free_naming_rate_ci95': list(wilson(naming, 84)) if naming is not None else None,
                   'free_correct_statement_rate_ci95': list(wilson(correct, 84)) if correct is not None else None,
                   'free_sentiment_note': 'E24 frozen regex has no sentiment detector; retained raw and reported not evaluable' if naming is None else None}
            cells.append(cell)
            histories[row, arm] = (cell, boot)
    r2 = {row: all(x['auroc'] <= .60 for x in histories[row, 'S'][0]['asked'])
          for row in ('prose_paren', 'prose_sentiment')}
    contrasts = []
    for row in C.ROWS:
        l, lb = histories[row, 'L']
        b, bb = histories[row, 'B']
        left, right = l['first_step_ge_080'], b['first_step_ge_080']
        diffs = []
        censored = 0
        for la, ba in zip(lb, bb):
            lc, bc = crossed(la), crossed(ba)
            if lc is None or bc is None:
                censored += 1
            else:
                diffs.append(lc-bc)
        # No arbitrary post-hoc 401/800-step replacement for an unobserved crossing.
        ci = np.quantile(diffs, [.025, .975]).tolist() if censored == 0 else None
        contrasts.append({'row': row, 'L_minus_B_steps': left-right if left is not None and right is not None else None,
            'ci95': ci, 'bootstrap_replicates_with_censoring': censored,
            'slower_L': bool(left is not None and right is not None and left > right and ci and ci[0] > 0)
                         if censored == 0 else None})
    r1_rows = {f: histories[f, 'L'][0]['fast'] for f in C.STATES}
    byrow = {x['row']: x for x in contrasts}
    required = [byrow[f]['slower_L'] for f in (*C.STATES, 'prose_sentiment')]
    r3 = None if any(x is None for x in required) else all(required[:3]) and not required[3]
    report = {'experiment': 'E28', 'status': 'COMPLETE_ANALYSIS', 'cells': cells,
        'R1': {'state_rows_fast': r1_rows, 'met': all(r1_rows.values()) if r2['prose_paren'] else None},
        'R2': r2, 'R3': {'met': r3 if all(r2.values()) else None, 'contrasts': contrasts,
                         'confound': 'L contains a merged Oracle adapter; interpret alongside E33, per §130'},
        'analysis_plan_sha256': C.sha(C.HERE / 'PLAN.json'), 'bootstrap_seed': C.SEED,
        'bootstrap_replicates': 2000, 'uninterpretable_rows': [f for f, passed in r2.items() if not passed]}
    out = C.cache_output(out)
    C.dump(out / 'METRICS.json', report)
    verdict = lambda x: 'met' if x is True else 'not met' if x is False else 'not evaluable'
    text = ['# E28 results', '', 'Registered predictions: R1 holds; R2 holds; R3 does not. '
            'Positions are fast and spontaneous naming stays below10%.', '',
            '- R1: ' + verdict(report['R1']['met']),
            '- R2 (prose_paren): ' + verdict(r2['prose_paren']),
            '- R2 (prose_sentiment): ' + verdict(r2['prose_sentiment']),
            '- R3: ' + verdict(report['R3']['met']), '',
            '| Row | Arm | Fast | First ≥.80 step | Naming rate |',
            '|---|---|---:|---:|---:|']
    for cell in cells:
        name = cell['free_naming_rate_ci95']
        text.append('| {} | {} | {} | {} | {} |'.format(cell['row'], cell['arm'],
            cell['fast'], cell['first_step_ge_080'] if cell['first_step_ge_080'] is not None else '>400',
            format(name[0], '.3f') if name is not None else 'not evaluable'))
    text += ['', 'R3 retains the merged-adapter/E33 confound required by §130. '
             'Censored crossings are not imputed. Failed S controls make the corresponding row uninterpretable. '
             'E24 has no sentiment statement regex; its native free text is retained. '
             'All checkpoint AUROCs, cluster CIs, statement-rate CIs and censoring counts are in METRICS.json.', '']
    (out / 'RESULTS.md').write_text('\n'.join(text))
    C.seal(out, 'ANALYSIS_SEAL.json')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--outputs', type=Path, nargs='+', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = analysis(a.input, a.outputs, a.out)
    print('E28 CPU analysis complete; R1=', result['R1']['met'], 'R3=', result['R3']['met'])


if __name__ == '__main__':
    main()
