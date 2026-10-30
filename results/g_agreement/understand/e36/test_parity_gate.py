"""Synthetic CPU checks for the mandatory §137 gate and stop ordering."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import parity_gate as G
import channel_contract as C


def synthetic_inputs():
    items = [{'id': f'{row}:{i}', 'feature': row, 'split': 'test'} for row in G.ROWS for i in range(84)]
    labels = {x['id']: int(x['id'].split(':')[-1]) % 2 for x in items}
    templates = {row: {'olens': [['a', 'b'], ['c', 'd']]} for row in G.ROWS}
    return items, labels, templates, [44] * 252, {'reference_auc': {row: .5 for row in G.ROWS}}


class ParityTests(unittest.TestCase):
    def records(self):
        items, labels, _, _, ref = synthetic_inputs()
        return [dict(x, scores=[0., 0.]) for x in items], labels, ref

    def test_tied_scores_are_half_auc(self):
        records, labels, ref = self.records()
        self.assertEqual(G.adjudicate(records, labels, ref)['status'], 'PASS')

    def test_uses_two_pair_mean_and_A_positive(self):
        records, labels, ref = self.records()
        for x in records:
            y = labels[x['id']]
            x['scores'] = [-y, 3 * y]
        ref['reference_auc'] = dict.fromkeys(G.ROWS, 1.)
        self.assertEqual(G.adjudicate(records, labels, ref)['status'], 'PASS')
        ref['reference_auc'] = dict.fromkeys(G.ROWS, 0.)
        self.assertEqual(G.adjudicate(records, labels, ref)['status'], 'FAIL')

    def test_stricter_137_threshold(self):
        records, labels, ref = self.records()
        ref['reference_auc'][G.ROWS[0]] = .519
        self.assertEqual(G.adjudicate(records, labels, ref)['status'], 'PASS')
        ref['reference_auc'][G.ROWS[0]] = .521
        self.assertEqual(G.adjudicate(records, labels, ref)['status'], 'FAIL')

    def test_missing_duplicate_nan_or_missing_pair_rejected(self):
        records, labels, ref = self.records()
        bad = [records[:-1], records[:-1] + [records[0]]]
        for scores in ([float('nan'), 0.], [0.]):
            x = copy.deepcopy(records)
            x[0]['scores'] = scores
            bad.append(x)
        for x in bad:
            with self.assertRaises(ValueError):
                G.adjudicate(x, labels, ref)

    def test_missing_or_changed_input_binding_rejected(self):
        for x in (None, {}, {'path': 'INPUT_SEAL.json', 'sha256': 'a'*64}):
            with self.assertRaises(ValueError):
                G.validate_binding(x)

    def test_failed_gate_precedes_production_capture(self):
        import worker as W
        from test_worker import FakeBackend, FakeBudget, items, candidates
        class Backend(FakeBackend):
            def capture(self, values):
                raise AssertionError('production reached despite failed gate')
        data = synthetic_inputs()
        data[-1]['reference_auc'][G.ROWS[0]] = 1.
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'score parity failed'):
                W.run_pipeline(items(), candidates(), Backend(), FakeBudget(), tmp, parity_inputs=data)
            self.assertEqual(json.loads((Path(tmp)/'PARITY_RESULT.json').read_text())['status'], 'FAIL')
            self.assertFalse((Path(tmp)/'scores.jsonl').exists())

    def test_bound_plan_cannot_drop_gate(self):
        from test_channel_contract import plan
        p = plan()
        del p['parity_inputs']
        p['plan_sha256'] = C.canonical_hash({k: v for k, v in p.items() if k != 'plan_sha256'})
        with self.assertRaisesRegex(ValueError, 'exact sealed'):
            C.validate_plan(p)


if __name__ == '__main__':
    unittest.main()
