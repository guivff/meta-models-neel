"""Mechanically seal §136 predictions from already sealed E29 W12 D/P.

CPU only. No reader outcomes are accepted, and D/P are never recomputed here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import math
from pathlib import Path

import analyze as A

HERE = Path(__file__).resolve().parent
STRUCTURE_CLASSES = {'structure', 'state-like', 'count-like'}
CONTENT_CLASSES = {'semantic', 'content'}


def prediction_rows(rows, row_classes):
    names = [row.get('feature') for row in rows]
    if len(names) != len(set(names)) or set(names) != set(row_classes):
        raise ValueError('Exact frozen row/class coverage required')
    result = []
    for row in rows:
        feature = row['feature']
        kind = row_classes[feature]
        if kind not in STRUCTURE_CLASSES | CONTENT_CLASSES:
            raise ValueError('Unrecognized frozen row class')
        d, p = row.get('D'), row.get('P')
        if (type(d) not in (int, float) or not math.isfinite(d) or not 0 <= d <= 1
                or type(p) not in (int, float) or not math.isfinite(p) or p > 0):
            raise ValueError('Invalid sealed D/P')
        predictions = {}
        if kind in STRUCTURE_CLASSES:
            predictions['oracle_asked_AUROC_max'] = 0.65
        if d >= 0.70:
            predictions['D_minus_oracle_asked_AUROC_min'] = 0.15
        result.append({'feature': feature, 'class': kind, 'D': d, 'P': p,
                       'predictions': predictions})
    return result


def generate(plan_path, values_seal_path, code_seal_path, out):
    plan_path, values_seal_path, code_seal_path, out = map(Path, (plan_path, values_seal_path, code_seal_path, out))
    plan, code_seal = A.read(plan_path), A.read(code_seal_path)
    cohort = A.select_cohort(plan, 'w12')
    if (code_seal.get('status') != 'FROZEN_BEFORE_W12_SCORES'
            or code_seal.get('authority_commit') != 'e29dc767'
            or plan.get('prediction_code_seal_sha256') != A.sha(code_seal_path)):
        raise ValueError('Prediction code seal must be bound in the scoring plan')
    A.verify_files(A.ROOT, code_seal.get('files'))
    A.verify_files(A.ROOT, plan.get('source_files'))
    own = str(Path(__file__).resolve().relative_to(A.ROOT))
    if code_seal['files'].get(own) != A.sha(__file__) or plan['source_files'].get(own) != A.sha(__file__):
        raise ValueError('Prediction generator not frozen in both source manifests')
    seal = A.read(values_seal_path)
    expected = {'cohort': 'w12', 'blind': True, 'plan_sha256': A.sha(plan_path),
                'input_seal_sha256': cohort['input_seal_sha256'], 'labels_sha256': cohort['labels_sha256'],
                'freeze': cohort['freeze'], 'source_files': plan['source_files']}
    if seal.get('complete') is not True or any(seal.get(k) != v for k, v in expected.items()):
        raise ValueError('Complete W12 values must match the exact freeze and scoring plan')
    if {'METRICS.json', 'RESULTS.md', 'cache/ITEM_SCORES.jsonl'} != set(seal.get('files', {})):
        raise ValueError('Incomplete sealed W12 value bundle')
    A.verify_files(values_seal_path.parent, seal['files'])
    metrics = A.read(values_seal_path.parent / 'METRICS.json')
    if any(metrics.get(k) != v for k, v in expected.items()):
        raise ValueError('Metrics identity differs from its value seal')
    if ([r.get('feature') for r in metrics.get('rows', [])] != cohort['rows']
            or metrics.get('n_items') != len(cohort['items'])):
        raise ValueError('Metrics do not cover every frozen W12 row/item')
    created = datetime.now(timezone.utc)
    if not A._timestamp(code_seal.get('created_at')) <= A._timestamp(seal.get('created_at')) <= created:
        raise ValueError('Code must precede sealed D/P; timestamps must not be future dated')
    row_classes = cohort.get('row_classes')
    if not isinstance(row_classes, dict):
        raise ValueError('READY plan must bind row classes from the W12 freeze')
    payload = {'experiment': 'E29', 'cohort': 'w12', 'status': 'SEALED_PROSPECTIVE_PREDICTIONS',
               'authority_section': 136, 'authority_commit': 'e29dc767',
               'created_at': created.isoformat(), 'freeze': cohort['freeze'],
               'plan_sha256': A.sha(plan_path), 'input_seal_sha256': cohort['input_seal_sha256'],
               'values_seal_sha256': A.sha(values_seal_path), 'metrics_sha256': A.sha(values_seal_path.parent / 'METRICS.json'),
               'prediction_code_seal_sha256': A.sha(code_seal_path), 'source_files': code_seal['files'],
               'rows': prediction_rows(metrics['rows'], row_classes),
               'reader_outcomes_read': False, 'DP_recomputed': False, 'model_calls': 0,
               'interpretation': 'Fixed per-row predictions only; registered R1/R2/R3 decision rules and later comparisons are unchanged.',
               'fresh_coordinator_ruling_required': False,
               'release_policy': 'Integrator/W-core must verify the exact freeze, sealed D/P, this prediction seal and required D/P publication; this program does not release readers.'}
    if any((out / name).exists() for name in ('PREDICTIONS.json', 'PREDICTIONS_SEAL.json')):
        raise ValueError('Predictions already exist; never overwrite or regenerate')
    out.mkdir(parents=True, exist_ok=True)
    A.dump(out / 'PREDICTIONS.json', payload)
    A.dump(out / 'PREDICTIONS_SEAL.json', {'experiment': 'E29', 'complete': True, 'created_at': payload['created_at'],
        'freeze': cohort['freeze'], 'plan_sha256': payload['plan_sha256'],
        'input_seal_sha256': payload['input_seal_sha256'], 'values_seal_sha256': payload['values_seal_sha256'],
        'prediction_code_seal_sha256': payload['prediction_code_seal_sha256'],
        'files': {'PREDICTIONS.json': A.sha(out / 'PREDICTIONS.json')}})
    return {'status': payload['status'], 'rows': len(payload['rows']),
            'predictions_seal_sha256': A.sha(out / 'PREDICTIONS_SEAL.json')}


if __name__ == '__main__':
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--values-seal', type=Path, required=True)
    parser.add_argument('--code-seal', type=Path, default=HERE / 'PREDICTION_CODE_SEAL.json')
    parser.add_argument('--out', type=Path, default=HERE)
    args = parser.parse_args()
    print(json.dumps(generate(args.plan, args.values_seal, args.code_seal, args.out), sort_keys=True))
