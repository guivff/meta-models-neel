import unittest
from analyze import row_summary,score,mention,summarize
class Tests(unittest.TestCase):
 def bootstrap(self,x):return sum(x)/len(x),.01,.99
 def test_conditional_named_denominator(self):
  r=row_summary([dict(belief=True,truth=False)]*6+[dict(belief=False,truth=True)]*4+[dict(belief=False,truth=False)]*90,self.bootstrap);self.assertEqual(r['delta'],.2);self.assertTrue(r['criterion_met']);self.assertEqual(r['naming_either_value'],10)
 def test_named_anywhere_not_dropped_for_cross_judgment_disagreement(self):
  r=row_summary([dict(belief=False,truth=False,any_named=True)],self.bootstrap);self.assertEqual(r['naming_either_value'],1);self.assertEqual(r['delta'],0);self.assertEqual(r['named_in_other_judgment_but_neither_dedicated_target'],1)
 def test_lower_CI_must_be_strictly_positive(self):self.assertFalse(row_summary([dict(belief=True,truth=False)],lambda x:(1,0,1))['criterion_met'])
 def test_both_is_named_zero(self):
  r=row_summary([dict(belief=True,truth=True)],self.bootstrap);self.assertEqual(r['both'],1);self.assertEqual(r['delta'],0)
 def test_missing_not_silent_or_wrong(self):
  r=row_summary([dict(belief=True,truth=None)],self.bootstrap);self.assertEqual(r['paired_missing'],1);self.assertIsNone(r['delta']);self.assertEqual(r['missingness_diagnostic_bounds'],[-1,1])
 def test_no_names_not_evaluable(self):self.assertFalse(row_summary([dict(belief=False,truth=False)],self.bootstrap)['evaluable'])
 def test_both_target_S_zero(self):self.assertEqual(score(dict(category='states_value',values=['A','B']),'A'),0)
 def test_target_order_join(self):self.assertTrue(mention(dict(category='states_value',values=['B']),'B'));self.assertEqual(score(dict(category='states_value',values=['A']),'B'),-1)
 def fixture(self):
  m=[dict(id='b',group_id='g',target='belief',target_letter='A',reader='oracle',family='row',source_public_id='item'),dict(id='t',group_id='g',target='truth',target_letter='B',reader='oracle',family='row',source_public_id='item'),dict(id='no_truth',group_id='g2',target='belief',target_letter='A',reader='oracle',family='row',source_public_id='missing_truth_item')]
  c={x['id']:dict(category='states_value',values=['A'])for x in m};return m,c
 def test_no_truth_items_rate_only_not_S_or_contrast(self):
  m,c=self.fixture();r=summarize(c,m,self.bootstrap);self.assertEqual(r['rows']['oracle/row']['planned_items'],1);self.assertEqual(len(r['belief_only_no_truth']),1);self.assertEqual(r['S_target']['oracle/row/belief']['N'],1)
 def test_matched_single_target_not_invented_pair(self):
  m,c=self.fixture();r=summarize({'t':c['t']},[m[1]],self.bootstrap,truth_known_groups={'g'},partial_target_subset=True);self.assertEqual(r['rows'],{});self.assertEqual(r['belief_only_no_truth'],[]);self.assertEqual(r['unpaired_target_groups_from_matched_sampling'],{'oracle/row':1})
if __name__=='__main__':unittest.main()
