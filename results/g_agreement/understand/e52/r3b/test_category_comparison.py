import unittest
from category_comparison import compare,category_prediction
class CategoryTests(unittest.TestCase):
    def rows(self):
        return [{'bank':'E56' if i<10 else 'E57','row':str(i),'truth':'REPORTED' if i<10 else 'MISSED','j_prediction':'REPORTED' if i<10 else 'MISSED','category':'content' if i<10 else 'bookkeeping'} for i in range(20)]
    def test_content_and_plan_only(self):
        self.assertEqual(category_prediction('plan'),'REPORTED')
        self.assertEqual(category_prediction('format'),'MISSED')
        with self.assertRaises(ValueError):category_prediction(None)
    def test_identical_predictions_have_zero_paired_difference(self):
        r=compare(self.rows(),draws=300)
        self.assertEqual(r['J_minus_category_balanced_accuracy'],0)
        self.assertEqual(r['bootstrap']['percentile95']['J_minus_category_balanced_accuracy'],[0,0])
        self.assertFalse(r['workspace_incremental_support'])
    def test_opposite_category_predictions_positive_difference(self):
        rows=self.rows()
        for x in rows:x['category']='bookkeeping' if x['truth']=='REPORTED' else 'plan'
        r=compare(rows,draws=300)
        self.assertEqual(r['J_minus_category_balanced_accuracy'],1)
        self.assertEqual(r['bootstrap']['percentile95']['J_minus_category_balanced_accuracy'],[1,1])
        self.assertTrue(r['workspace_incremental_support'])
    def test_registered_minimum_support(self):
        r=compare(self.rows()[:-1],draws=100)
        self.assertEqual(r['status'],'NOT EVALUABLE');self.assertIsNone(r['workspace_incremental_support'])
    def test_missing_category_never_silently_drops_row(self):
        rows=self.rows();rows[0]['category']='unknown'
        with self.assertRaises(ValueError):compare(rows)
    def test_duplicate_identity_rejected(self):
        rows=self.rows();rows[-1]=rows[0]
        with self.assertRaises(ValueError):compare(rows)
if __name__=='__main__':unittest.main()
