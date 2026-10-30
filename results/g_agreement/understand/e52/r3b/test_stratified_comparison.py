import unittest
from stratified_comparison import within_category,score_forecasts_by_reader
class StratifiedTests(unittest.TestCase):
    def rows(self,category,n=4,perfect=True):
        return [{'bank':'E56' if i%2 else 'E57','row':category+str(i),'category':category,
                 'truth':'REPORTED' if i<n//2 else 'MISSED',
                 'j_prediction':('REPORTED' if i<n//2 else 'MISSED') if perfect else ('MISSED' if i<n//2 else 'REPORTED')} for i in range(n)]
    def test_row_weighted_not_equal_category_mean(self):
        r=within_category(self.rows('content',4)+self.rows('format',8,False))
        self.assertAlmostEqual(r['stratified_balanced_accuracy'],1/3)
        self.assertEqual(r['status'],'DESCRIPTIVE')
    def test_three_strata_is_confirmatory_even_below_original_pooled_minimum(self):
        rows=sum([self.rows(c) for c in ['content','format','syntactic']],[])
        r=within_category(rows)
        self.assertEqual(r['status'],'CONFIRMATORY');self.assertEqual(r['n'],12)
        self.assertTrue(r['criterion_met']);self.assertEqual(r['permutation']['count'],1000)
    def test_only_within_stratum_shuffling(self):
        rows=self.rows('content',8)+self.rows('format',8)
        for r in rows:r['j_prediction']='REPORTED' if r['category']=='content' else 'MISSED'
        r=within_category(rows)
        self.assertEqual(set(r['permutation']['null_balanced_accuracy']),{.5})
        self.assertFalse(r['criterion_met'])
    def test_qualification_and_no_qualified_stratum(self):
        rows=self.rows('content',2)+self.rows('format',4)
        for x in rows:
            if x['category']=='format':x['truth']='REPORTED'
        r=within_category(rows)
        self.assertEqual(r['status'],'NOT EVALUABLE');self.assertEqual(len(r['excluded_strata']),2)
    def test_input_order_does_not_change_seeded_null(self):
        rows=self.rows('content',8)+self.rows('format',6)
        self.assertEqual(within_category(rows),within_category(list(reversed(rows))))
    def test_scoring_entry_always_includes_both_tests_for_both_readers(self):
        rows=sum([self.rows(c,8) for c in ['content','format','syntactic']],[])
        r=score_forecasts_by_reader({'oracle':rows,'nla':rows})
        for reader in r:self.assertEqual(set(r[reader]),{'pooled_and_category','within_category'})
if __name__=='__main__':unittest.main()
