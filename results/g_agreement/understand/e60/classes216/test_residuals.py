import unittest
import numpy as np
from residuals import coded_rows, summarize

class Model:
    def __init__(self, p): self.p = p
    def predict_probability(self, x): return np.full(x.shape, self.p)

class Tests(unittest.TestCase):
    def rows(self):
        return [dict(bank='B',row=str(i),j_fraction=i/10,S=(-.5 if i<5 else .5),reported=i>=5) for i in range(10)]
    def coding(self):
        return dict(rows=[dict(bank='B',row=str(i),silent_state_class='a' if i<5 else 'b') for i in range(10)])
    def test_unknown_and_duplicate_cannot_disappear(self):
        rows=self.rows(); rows[0]['row']='new'
        with self.assertRaises(ValueError): coded_rows(rows,self.coding())
        with self.assertRaises(ValueError): coded_rows(self.rows()+self.rows()[:1],self.coding())
    def test_signed_residual_is_distinct_from_binary_calibration(self):
        out=summarize(coded_rows(self.rows(),self.coding()),Model(.5),lambda x,y:Model(y.mean()),draws=100,minimum_success=90)
        self.assertEqual(out['classes']['a']['signed_S_minus_report_probability'],-1)
        self.assertEqual(out['classes']['a']['binary_calibration_residual'],-.5)
        self.assertEqual(out['classes']['b']['signed_S_minus_report_probability'],0)
    def test_whole_rows_and_pooled_uncertainty_are_retained(self):
        calls=[]
        def fit(x,y):
            calls.append((x.copy(),y.copy()))
            np.testing.assert_array_equal(y,x>=.5)
            return Model(y.mean())
        out=summarize(coded_rows(self.rows(),self.coding()),Model(.5),fit,draws=100,minimum_success=90)
        self.assertEqual(len(calls),100)
        self.assertTrue(all(len(x)==10 for x,y in calls))
        lo,hi=out['classes']['a']['signed_residual_CI95']
        self.assertLess(lo,hi) # fixed pooled predictions would wrongly collapse this interval
    def test_failed_draws_are_not_replaced(self):
        out=summarize(coded_rows(self.rows(),self.coding()),Model(.5),lambda x,y:(_ for _ in ()).throw(ValueError('singular')),draws=20,minimum_success=19)
        self.assertEqual(out['bootstrap']['failed_or_absent']['pooled_fit'],20)
        self.assertEqual(out['classes']['a']['interval_status'],'NOT EVALUABLE')
        self.assertIsNone(out['classes']['a']['signed_residual_CI95'])

if __name__=='__main__': unittest.main()
