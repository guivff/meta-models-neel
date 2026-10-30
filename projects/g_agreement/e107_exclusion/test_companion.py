import unittest
from .companion import strict_failures,mask,table
class TestCompanion(unittest.TestCase):
    def data(self,text,evidence):return {'oracle':{'S':{'code':{'category':'states_value','evidence':evidence},'text':text}}}
    def test_exact(self):self.assertEqual(strict_failures({'id':'x','bank':'E81'},self.data('Hello world','Hello')),[])
    def test_case_is_strict(self):self.assertEqual(len(strict_failures({'id':'x','bank':'E81'},self.data('Hello','hello'))),1)
    def test_space_is_strict(self):self.assertEqual(len(strict_failures({'id':'x','bank':'E81'},self.data('a  b','a b'))),1)
    def test_group_no_concat(self):self.assertEqual(len(strict_failures({'id':'x','bank':'E82'},self.data([{'readout':'a'},{'readout':'b'}],'a b'))),1)
    def test_group_one_position(self):self.assertEqual(strict_failures({'id':'x','bank':'E82'},self.data([{'readout':'a b'},{'readout':'c'}],'a b')),[])
    def test_cell_only_mask(self):
        x={'bank':'E81','systems':{'oracle':{'S':1,'named':True},'outside':{'S':-1,'named':True}}}
        y=mask(x,[{'system':'oracle','target':'S'}]);self.assertIsNone(y['systems']['oracle']['S']);self.assertEqual(x['systems']['oracle']['S'],1);self.assertEqual(y['systems']['outside'],x['systems']['outside'])
    def test_table_overlap_missing(self):
        xs=[{'bank':'E82','row':'r','cohort':'belief_wrong','systems':{'oracle':{'belief':1,'truth':1,'named':True},'outside':{'belief':None,'truth':None,'named':None}}}]
        t=table(xs);o=next(x for x in t if x['reader']=='oracle');self.assertEqual(o['both_belief_and_truth'],1);self.assertEqual(o['states_belief'],1);self.assertEqual(o['states_truth'],1);self.assertEqual(next(x for x in t if x['reader']=='outside')['missing'],1)
    def test_other_no_value(self):
        xs=[{'bank':'E82','row':'r','cohort':'belief_wrong','systems':{'oracle':{'belief':0,'truth':0,'named':b}}} for b in (True,False)]
        o=table(xs)[0];self.assertEqual(o['states_other'],1);self.assertEqual(o['no_value'],1);self.assertEqual(o['unconditional_belief_rate_observed'],0)
if __name__=='__main__':unittest.main()
