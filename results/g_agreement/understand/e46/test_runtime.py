import unittest,importlib.util
from pathlib import Path
from worker46 import warmed_forecast
from states import state
p=Path(__file__).resolve().parent.parent/'e42/persistence_core.py'
s=importlib.util.spec_from_file_location('core46_test',p);core=importlib.util.module_from_spec(s);s.loader.exec_module(core)
class RuntimeTests(unittest.TestCase):
    def test_cold_batch_excluded_mean_used(self):
        self.assertIsNone(warmed_forecast([900],10))
        self.assertEqual(warmed_forecast([900,2,4],10),30)
    def test_anchored_completion_with_frozen_core(self):
        i={'feature':'word_first_piece','text':'micro','label':'A','value':'first_piece'}
        pieces=['micro','architecture',' ']+['x']*30
        self.assertEqual(core.persistence([0],list(range(1,33)),i['value'],lambda ids:''.join(pieces[x] for x in ids),lambda text:state(i,text)),1)
    def test_no_completion_is_right_censored_32(self):
        i={'feature':'word_first_piece','text':'micro','label':'A','value':'first_piece'}
        self.assertEqual(core.persistence([0],[1]*32,i['value'],lambda ids:'micro'+'a'*(len(ids)-1),lambda text:state(i,text)),32)
    def test_horizon_cannot_shorten(self):
        with self.assertRaises(ValueError):core.persistence([],[],None,str,lambda x:None)
if __name__=='__main__':unittest.main()
