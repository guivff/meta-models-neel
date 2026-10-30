"""Synthetic-only tests; no W12 items, D/P or reader outcomes are loaded."""
import math
import unittest
import json
from pathlib import Path
import tempfile

import predict as P
from test_analysis import fixture


def sealed_fixture(root):
    plan, _, _ = fixture()
    own = str(Path(P.__file__).relative_to(P.A.ROOT))
    plan['source_files'][own] = P.A.sha(P.__file__)
    code = {'status': 'FROZEN_BEFORE_W12_SCORES', 'authority_commit': 'e29dc767',
            'created_at': '2020-01-01T00:00:00+00:00', 'files': dict(plan['source_files'])}
    code_path = root / 'code.json'
    code_path.write_text(json.dumps(code))
    plan['prediction_code_seal_sha256'] = P.A.sha(code_path)
    cohort = plan['cohorts'][0]
    cohort['row_classes'] = {r: 'structure' for r in cohort['rows']}
    plan_path = root / 'plan.json'
    plan_path.write_text(json.dumps(plan))
    values = root / 'values'
    (values / 'cache').mkdir(parents=True)
    identity = {'cohort': 'w12', 'blind': True, 'plan_sha256': P.A.sha(plan_path),
                'input_seal_sha256': cohort['input_seal_sha256'], 'labels_sha256': cohort['labels_sha256'],
                'freeze': cohort['freeze'], 'source_files': plan['source_files']}
    metrics = {**identity, 'n_items': len(cohort['items']),
               'rows': [{'feature': r, 'D': .70, 'P': -2.0} for r in cohort['rows']]}
    (values / 'METRICS.json').write_text(json.dumps(metrics))
    (values / 'RESULTS.md').write_text('Synthetic only.\n')
    (values / 'cache/ITEM_SCORES.jsonl').write_text('{}\n')
    seal = {**identity, 'complete': True, 'created_at': '2021-01-01T00:00:00+00:00',
            'files': {n: P.A.sha(values / n) for n in ('METRICS.json', 'RESULTS.md', 'cache/ITEM_SCORES.jsonl')}}
    seal_path = values / 'VALUES_SEAL.json'
    seal_path.write_text(json.dumps(seal))
    return plan_path, seal_path, code_path, root / 'out'


class PredictionTests(unittest.TestCase):
    def test_exact_threshold_and_every_structure_class(self):
        rows = [{'feature': k, 'D': d, 'P': -2.0} for k, d in [('a', .699999999), ('b', .7), ('c', .91)]]
        result = P.prediction_rows(rows, {'a': 'state-like', 'b': 'count-like', 'c': 'structure'})
        self.assertEqual([r['predictions']['oracle_asked_AUROC_max'] for r in result], [.65]*3)
        self.assertNotIn('D_minus_oracle_asked_AUROC_min', result[0]['predictions'])
        self.assertEqual(result[1]['predictions']['D_minus_oracle_asked_AUROC_min'], .15)
        self.assertEqual(result[2]['predictions']['D_minus_oracle_asked_AUROC_min'], .15)

    def test_no_extra_prediction_for_content(self):
        rows = [{'feature': 'a', 'D': .4, 'P': -1}, {'feature': 'b', 'D': .8, 'P': -1}]
        result = P.prediction_rows(rows, {'a': 'semantic', 'b': 'content'})
        self.assertEqual(result[0]['predictions'], {})
        self.assertEqual(result[1]['predictions'], {'D_minus_oracle_asked_AUROC_min': .15})

    def test_no_class_inference_or_missing_rows(self):
        rows = [{'feature': 'a', 'D': .8, 'P': -1}]
        for classes in ({}, {'a': 'unknown'}, {'a': 'structure', 'b': 'structure'}):
            with self.subTest(classes=classes), self.assertRaises(ValueError):
                P.prediction_rows(rows, classes)

    def test_invalid_values_rejected(self):
        for d, p in ((math.nan, -1), (.8, math.inf), (1.1, -1), (True, -1), (.8, .1)):
            with self.subTest(d=d,p=p), self.assertRaises(ValueError):
                P.prediction_rows([{'feature': 'a', 'D': d, 'P': p}], {'a': 'structure'})

    def test_sealed_generation_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = sealed_fixture(Path(tmp))
            result = P.generate(*args)
            self.assertEqual(result['rows'], 2)
            output = P.A.read(args[3] / 'PREDICTIONS.json')
            self.assertFalse(output['reader_outcomes_read'])
            self.assertFalse(output['DP_recomputed'])
            self.assertEqual(output['values_seal_sha256'], P.A.sha(args[1]))
            digest = P.A.sha(args[3] / 'PREDICTIONS.json')
            with self.assertRaisesRegex(ValueError, 'never overwrite'):
                P.generate(*args)
            self.assertEqual(digest, P.A.sha(args[3] / 'PREDICTIONS.json'))

    def test_tampered_metrics_or_foreign_freeze_fail_closed(self):
        for fault in ('metrics', 'freeze', 'extra_file'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as tmp:
                args = sealed_fixture(Path(tmp))
                if fault == 'metrics':
                    with (args[1].parent / 'METRICS.json').open('a') as stream:
                        stream.write(' ')
                else:
                    seal = P.A.read(args[1])
                    if fault == 'freeze':
                        seal['freeze'] = {'id': 'another-freeze'}
                    else:
                        seal['files']['reader.json'] = '1'*64
                    args[1].write_text(json.dumps(seal))
                with self.assertRaises(ValueError):
                    P.generate(*args)
                self.assertFalse(args[3].exists())

    def test_code_must_be_frozen_in_scoring_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = sealed_fixture(Path(tmp))
            plan = P.A.read(args[0])
            plan.pop('prediction_code_seal_sha256')
            args[0].write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError, 'bound in the scoring plan'):
                P.generate(*args)


if __name__ == '__main__':
    unittest.main()
