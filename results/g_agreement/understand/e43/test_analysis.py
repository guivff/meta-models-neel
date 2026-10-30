import unittest
from analyze_once import silent_sets, auc, rule

class AnalysisTests(unittest.TestCase):
    def test_all_vs_any(self):
        rs=[{'id':'a'},{'id':'a'},{'id':'b'},{'id':'b'},{'id':'c'}]
        self.assertEqual(silent_sets(rs,['neither','A','neither','neither',None]),({'b'},{'a','b'}))
    def test_unknown_is_not_silence(self):
        self.assertEqual(silent_sets([{'id':'a'},{'id':'a'}],['neither',None]),(set(),{'a'}))
    def test_orientation_and_single_class(self):
        self.assertEqual(auc(['A','B'],[1,0]),1.)
        self.assertEqual(auc(['A','B'],[0,1]),0.)
        self.assertIsNone(auc(['A','A'],[1,0]))
    def row(self, name='r', **kwargs):
        return dict(primary=True,reader='oracle',classification='state-like',evaluable=True,probe_auroc=.9,mention_rate=.05,silent_all={'auroc':.85},bank='w1',row=name,**kwargs)
    def test_boundary_passes(self):
        self.assertEqual(rule([self.row()])['verdict'],'R1 HOLDS')
    def test_strict_majority(self):
        r=self.row('b');r['mention_rate']=.051
        self.assertEqual(rule([self.row(),r])['verdict'],'R1 DOES NOT HOLD')
    def test_no_eligible(self):
        r=self.row();r['evaluable']=False
        self.assertEqual(rule([r])['verdict'],'NOT EVALUABLE')
    def test_other_layer_nla_trained_content_excluded(self):
        rs=[]
        for field,value in [('primary',False),('reader','nla'),('classification','semantic'),('probe_auroc',.8999)]:
            r=self.row();r[field]=value;rs.append(r)
        self.assertEqual(rule(rs)['eligible_rows'],0)
if __name__=='__main__':unittest.main()
