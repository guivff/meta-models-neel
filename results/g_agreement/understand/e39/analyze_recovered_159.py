"""§159 collection validation; original E39 scientific analysis below is byte-identical."""
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
            raise ValueError('missing or altered E39 environment/parity receipt')
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
            or reference.get('original_e28_input_seal_sha256') != C.read(C.HERE / 'PARITY_PREPARATION_2026-10-25.json')['original_e28_input_seal_sha256']):
        raise ValueError('authorized pre-training parity evidence required')
    for row, cell in parity['rows'].items():
        values = [cell.get(k) for k in ('observed', 'reference', 'absolute_delta')]
        if (any(type(v) not in (int, float) or not math.isfinite(v) for v in values)
                or cell.get('n') != 84 or cell.get('threshold') != .03 or cell['reference'] != expected[row]
                or not 0 <= cell['observed'] <= 1
                or abs(cell['absolute_delta'] - abs(cell['observed'] - cell['reference'])) > 1e-12
                or not 0 <= cell['absolute_delta'] <= .03):
            raise ValueError('E39 W1 AUROC environment parity failed')
    ready = C.read(root / 'ENVIRONMENT_RUNTIME_RESULT.json')
    epoch, gate_epoch = ready.get('completed_epoch'), parity.get('completed_epoch')
    if (ready.get('schema') != 'E39_TRAINING_ENV_RUNTIME_v1' or ready.get('status') != 'TRAINING_ENVIRONMENT_READY'
            or ready.get('device') != 'cuda' or ready.get('real_cuda_backward') is not True
            or ready.get('finite_loss') is not True or ready.get('finite_gradients') is not True
            or ready.get('fresh_lora_only') is not True or ready.get('optimizer_steps_in_readiness') != 1
            or ready.get('environment_manifest_sha256') != receipt['environment_manifest_sha256']
            or ready.get('parity_result_sha256') != receipt['parity_result_sha256']
            or ready.get('readiness_deadline_epoch') != 1793228340
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in (epoch, gate_epoch))
            or not 0 < gate_epoch <= epoch <= 1793228340):
        raise ValueError('real CUDA backward readiness by programme cutoff required')


def analysis(input_dir, outputs, out):
    import numpy as np
    import common
    from common.stats import wilson
    from mats.metrics import auroc_labels
    from projects.g_agreement.understand.e24_statements import statement, PATTERNS
    C.verify(C.ROOT, str((C.HERE / 'SOURCE_MANIFEST.json').relative_to(C.ROOT)))
    C.verify(input_dir)
    test = C.rows(input_dir / 'test.jsonl')
    from recovery_159 import collect
    directories = collect(input_dir, outputs)
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
        free_rows = C.rows(d / 'free.800.jsonl')
        if len(free_rows) != 84 or {r['id'] for r in free_rows} != ids or any(not isinstance(r['raw'], str) for r in free_rows):
            raise ValueError('incomplete free grid before unblinding')
    labels_path = input_dir / 'test.labels.DO_NOT_STAGE.jsonl'
    preparation = C.read(C.HERE / 'PREPARATION.json')
    if C.sha(labels_path) != preparation['private_test_labels_sha256']:
        raise ValueError('frozen local analysis label key mismatch')
    out = C.cache_output(out)
    C.dump(out/'ANALYSIS_STARTED.json', {'experiment':'E39','analysis_invocations':1,
        'plan_sha256':C.sha(C.HERE/'PLAN.json'),'input_seal_sha256':C.sha(input_dir/'INPUT_SEAL.json')})
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
            free = C.rows(d / 'free.800.jsonl')
            if len(free) != 84 or {r['id'] for r in free} != set(ids):
                raise ValueError('complete 84 native free readouts required')
            statuses = [statement(row, r['raw']) for r in free]
            naming = None if row not in PATTERNS else sum(x in ('A', 'B', 'both') for x in statuses)
            correct = None if naming is None else sum(statement(row, r['raw']) == ('A' if lookup[r['id']]['y'] else 'B') for r in free)
            cell = {'row': row, 'arm': arm, 'asked': [{'step': step, 'auroc': auc[i], 'ci95': ci[:, i].tolist()}
                   for i, step in enumerate(C.CHECKPOINTS)], 'fast': fast, 'first_step_ge_080': crossed(auc),
                   'right_censored_at800': crossed(auc) is None,
                   'free_statement_statuses': {s: statuses.count(s) for s in sorted(set(statuses))},
                   'free_naming_rate_ci95': list(wilson(naming, 84)) if naming is not None else None,
                   'free_correct_statement_rate_ci95': list(wilson(correct, 84)) if correct is not None else None,
                   'free_detector_note': 'E24 frozen regex has no detector for this semantic row; retained raw and reported not evaluable' if naming is None else None}
            cells.append(cell)
            histories[row, arm] = (cell, boot)
    rules = evaluate_rules(cells)
    report = {'experiment': 'E39', 'status': 'COMPLETE_ANALYSIS', 'cells': cells, **rules,
        'analysis_plan_sha256': C.sha(C.HERE/'PLAN.json'), 'bootstrap_seed': C.SEED,
        'bootstrap_replicates': 2000, 'row_classes': C.plan()['row_classes'],
        'semantic_rows_descriptive': list(C.SEMANTIC),
        'positions_vs_states': {kind: [c for c in cells if c['row'] in C.STRUCTURE and
            C.plan()['row_classes'][c['row']] == kind] for kind in ('count-like','state-like')}}
    C.dump(out/'METRICS.json', report)
    verdict = lambda x: 'MET' if x is True else 'NOT MET' if x is False else 'NOT EVALUABLE'
    text = ['# E39 registered results', '',
        'R1′: '+verdict(rules['R1prime']['met']), 'R3′: '+verdict(rules['R3prime']['met']), '',
        '| Row | Arm | Interpretable | Fast | First ≥0.80 | Naming rate at800 |',
        '|---|---|---|---|---|---|']
    for c in cells:
        naming=c['free_naming_rate_ci95']
        text.append('| {} | {} | {} | {} | {} | {} |'.format(c['row'],c['arm'],
            rules['row_eligibility'][c['row']]['interpretable'],c['fast'],
            c['first_step_ge_080'] if c['first_step_ge_080'] is not None else '>800',
            naming[0] if naming is not None else 'not evaluable'))
    text+=['','R1′ is confirmatory; R3′ and naming/positions-versus-states are exploratory/descriptive. '
        'Excluded rows and reasons are listed in METRICS.json. Both censored crossings are assigned800; '
        'strictly more than half doubly censored makes R3′ not evaluable. E24 regex is unchanged.','']
    (out/'RESULTS.md').write_text('\n'.join(text))
    C.seal(out,'ANALYSIS_SEAL.json')
    return report


def evaluate_rules(cells):
    """§141 and clarification1; pure rule evaluation, no model calls."""
    import numpy as np
    by={(c['row'],c['arm']):c for c in cells}
    if set(by)!=set(C.RUNS) or len(cells)!=len(C.RUNS):
        raise ValueError('all54cells required')
    eligibility={}
    for row in C.ROWS:
        l=by[row,'L'];shuffled=by[row,'S']
        for arm in ('L','B','S'):
            values=by[row,arm]['asked']
            if ([x['step'] for x in values]!=list(C.CHECKPOINTS) or
                    any(not math.isfinite(x['auroc']) or not 0<=x['auroc']<=1 for x in values)):
                raise ValueError('complete finite checkpoint AUROCs required')
        reasons=[]
        if any(x['auroc']>.60 for x in shuffled['asked']):reasons.append('S_above_0.60')
        if l['asked'][0]['auroc']>.65:reasons.append('L_already_answered_at_step0')
        eligibility[row]={'interpretable':not reasons,'exclusion_reasons':reasons,
            'S_max_auroc':max(x['auroc'] for x in shuffled['asked']),'L_step0_auroc':l['asked'][0]['auroc']}
    eligible=[r for r in C.STRUCTURE if eligibility[r]['interpretable']]
    fast=[r for r in eligible if by[r,'L']['fast']]
    r1={'met':len(fast)/len(eligible)>=.60 if len(eligible)>=8 else None,
        'interpretable_structure_rows':eligible,'n_interpretable':len(eligible),
        'fast_structure_rows':fast,'n_fast':len(fast),
        'fraction_fast':len(fast)/len(eligible) if eligible else None,'minimum_interpretable':8,'threshold':.60}
    pairs=[]
    for row in eligible:
        l=crossed([x['auroc'] for x in by[row,'L']['asked']]);b=crossed([x['auroc'] for x in by[row,'B']['asked']])
        pairs.append({'row':row,'L_steps':800 if l is None else l,'B_steps':800 if b is None else b,
            'L_censored':l is None,'B_censored':b is None,'both_censored':l is None and b is None,
            'L_minus_B_steps':(800 if l is None else l)-(800 if b is None else b)})
    doubly=sum(x['both_censored'] for x in pairs)
    reason='no_interpretable_structure_rows' if not pairs else 'more_than_half_both_censored' if doubly>len(pairs)/2 else None
    mean=float(np.mean([x['L_minus_B_steps'] for x in pairs])) if pairs else None
    ci=None
    if reason is None:
        # Resample the paired row differences, keeping the declared interpretable cohort fixed.
        delta=np.array([x['L_minus_B_steps'] for x in pairs],float)
        rng=np.random.default_rng(C.SEED)
        boot=delta[rng.integers(0,len(delta),size=(2000,len(delta)))].mean(axis=1)
        ci=np.quantile(boot,[.025,.975]).tolist()
    r3={'met':bool(mean<0 and ci[1]<0) if ci is not None else None,
        'mean_L_minus_B_steps':mean,'ci95':ci,'paired_rows':pairs,
        'both_censored_rows':doubly,'not_evaluable_reason':reason,
        'bootstrap_unit':'row (paired L minus B)','bootstrap_replicates':2000}
    return {'row_eligibility':eligibility,'R1prime':r1,'R3prime':r3,
        'excluded_structure_rows':[r for r in C.STRUCTURE if not eligibility[r]['interpretable']]}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--outputs', type=Path, nargs='+', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = analysis(a.input, a.outputs, a.out)
    print('E39 CPU analysis complete; R1=', result['R1prime']['met'], 'R3prime=', result['R3prime']['met'])


if __name__ == '__main__':
    main()
