import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import comparison_once as C

class DeferredComparison(unittest.TestCase):
    def records(self):
        return [{'row':str(i),'class':'tracked_state','probe_auroc':.90,'base_text_auroc':.85,'bow_auroc':.65,'unprompted_mention_rate':1.,'correct_value_rate':.10 if i<8 else .0999,'wrong_only_rate':.05} for i in range(16)]

    def test_wrong_value_and_ties_do_not_count_as_reported(self):
        rr=self.records();rr[0]['wrong_only_rate']=.10;rr[1]['wrong_only_rate']=.11
        pred={str(i):'REPORTED' for i in range(16)}
        result=C.evaluate_r3(rr,pred,pred,'scale_9_over_16')
        self.assertEqual(result['rows'][0]['truth'],'MISSED');self.assertEqual(result['rows'][1]['truth'],'MISSED')
        self.assertEqual(result['rows'][2]['truth'],'REPORTED');self.assertEqual(result['rows'][8]['truth'],'MISSED')

    def test_native_truth_and_mechanical_gates(self):
        rr=self.records();pred={str(i):'REPORTED' if i<8 else 'MISSED' for i in range(16)}
        result=C.evaluate_r3(rr,pred,pred,'scale_9_over_16');self.assertTrue(result['met']);self.assertEqual(result['correct'],16)
        rr[0]['probe_auroc']=.8999;rr[1]['base_text_auroc']=.8499;rr[2]['bow_auroc']=.65001
        result=C.evaluate_r3(rr,pred,pred,'scale_9_over_16');self.assertEqual(result['n_gated'],13);self.assertEqual(result['excluded_rows'],['0','1','2'])
        rr[2]['class']='content';self.assertEqual(C.evaluate_r3(rr,pred,pred,'scale_9_over_16')['n_gated'],14)

    def test_thresholds_and_empty_gate(self):
        rr=self.records();pred={str(i):'REPORTED' if i<8 else 'MISSED' for i in range(16)}
        for i in range(4):pred[str(i)]='MISSED'
        self.assertTrue(C.evaluate_r3(rr,pred,pred,'scale_9_over_16')['met'])
        pred['4']='MISSED';self.assertFalse(C.evaluate_r3(rr,pred,pred,'scale_9_over_16')['met'])
        for i in (5,6):pred[str(i)]='MISSED'
        self.assertTrue(C.evaluate_r3(rr,pred,pred,'scale_9_over_16')['falsifier_low_accuracy'])
        pred['6']='REPORTED'
        self.assertFalse(C.evaluate_r3(rr,pred,pred,'scale_9_over_16')['falsifier_low_accuracy'])
        rr[15]['probe_auroc']=0
        with self.assertRaises(ValueError):C.evaluate_r3(rr,pred,pred,'require_all_16')
        for r in rr:r['probe_auroc']=0
        self.assertIsNone(C.evaluate_r3(rr,pred,pred,'scale_9_over_16')['met'])

    def test_partial_denominator_and_minimum_eight_gated_rows(self):
        rr=self.records()
        for r in rr[8:]:r['probe_auroc']=0
        pred={str(i):'REPORTED' if i<4 else 'MISSED' for i in range(16)}
        result=C.evaluate_r3(rr,pred,pred,'scale_9_over_16')
        self.assertEqual((result['status'],result['n_gated'],result['accuracy']),('EVALUABLE',8,.5))
        self.assertTrue(result['falsifier_low_accuracy'])
        pred['4']='REPORTED'
        self.assertFalse(C.evaluate_r3(rr,pred,pred,'scale_9_over_16')['falsifier_low_accuracy'])
        for i in range(8):pred[str(i)]='REPORTED'
        self.assertTrue(C.evaluate_r3(rr,pred,pred,'scale_9_over_16')['met'])
        rr[7]['probe_auroc']=0
        result=C.evaluate_r3(rr,pred,pred,'scale_9_over_16')
        self.assertEqual(result['status'],'NOT EVALUABLE');self.assertEqual(result['accuracy'],1.)
        self.assertIsNone(result['met']);self.assertIsNone(result['falsifier_low_accuracy'])

    def test_json_pointers_are_exact(self):
        self.assertEqual(C.at({'a/b':[{'c~d':.5}]},'/a~1b/0/c~0d'),.5)
        with self.assertRaises(ValueError):C.at({},'not-a-pointer')

    def test_no_early_claim_or_outcome_access(self):
        with tempfile.TemporaryDirectory() as d,patch.object(C,'CLAIM',Path(d)/'claim'),patch.object(C,'read',return_value={'falsifier_denominator':'scale_9_over_16','verified_inputs':str(Path(d)/'absent')}),patch.object(C,'comparison') as invoke:
            self.assertEqual(C.main(),2);self.assertFalse(C.CLAIM.exists());invoke.assert_not_called()

if __name__=='__main__':unittest.main()
