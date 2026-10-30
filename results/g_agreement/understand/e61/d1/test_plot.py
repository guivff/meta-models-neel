from pathlib import Path
import tempfile
import unittest
from plot_once import prepare_rows,render,BANKS,COLOURS

class D1Contracts(unittest.TestCase):
    def table(self):
        return {'status':'SEALED_E60_ROW_TABLE','banks':list(BANKS),'rows':[{'bank':'W1','row':'a','reader':'oracle','gated':True,'J_fraction':.02,'native_counts':{'N':100,'correct_only':10,'wrong_only':60}}, {'bank':'E57','row':'focus_think','reader':'nla','gated':True,'J_fraction':.4,'native_counts':{'N':320,'correct_only':240,'wrong_only':0}}, {'bank':'E36','row':'excluded','reader':'oracle','gated':False,'gate_reason':'registered probe gate'}]}

    def test_signed_S_all_gated_rows_and_frozen_aliases(self):
        points,excluded=prepare_rows(self.table(),{('W1','a'):'bookkeeping',('E57','focus_ignore_mention'):'content'},{('E57','focus_think'):'focus_ignore_mention'})
        self.assertEqual(len(points),2);self.assertEqual(points[0]['S'],-.5);self.assertEqual(points[1]['S'],.75)
        self.assertEqual(points[1]['row'],'focus_think');self.assertEqual(len(excluded),1)
        with self.assertRaises(ValueError):prepare_rows(self.table(),{}, {})

    def test_bad_counts_and_duplicate_points_are_not_silently_dropped(self):
        t=self.table();t['rows'][0]['native_counts']['N']=0
        with self.assertRaises(ValueError):prepare_rows(t,{('W1','a'):'content'}, {})
        t=self.table();t['rows'].append(t['rows'][0])
        with self.assertRaises(ValueError):prepare_rows(t,{('W1','a'):'content',('E57','focus_think'):'content'}, {})

    def test_every_point_is_rendered_even_with_no_estimable_curve(self):
        points,_=prepare_rows(self.table(),{('W1','a'):'bookkeeping',('E57','focus_think'):'content'}, {})
        curves={'oracle':{'status':'ESTIMATED','J_fraction':[0,.5],'P_report':[.2,.8]},'nla':{'status':'NOT EVALUABLE','reason':'synthetic constant target'}}
        with tempfile.TemporaryDirectory() as t:
            result=render(points,curves,Path(t))
            self.assertEqual(result['points_rendered'],2);self.assertFalse(result['E60_refitted'])
            self.assertTrue((Path(t)/'D1.png').is_file());self.assertTrue((Path(t)/'D1.svg').is_file())

if __name__=='__main__':unittest.main()
