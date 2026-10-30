import unittest
from .e133_close259 import validate_contract
class Tests(unittest.TestCase):
 def fixture(self):return [dict(experiment='E133',status='COMPLETE',route_verified=True,phase='synthetic_naming_judging'),dict(experiment='E133',arm='synthetic',status='COMPLETE_SOURCE_CODE_BINDING'),[dict(id=str(i),status='KEPT'if i<467 else'UNPARSEABLE')for i in range(540)],dict(experiment='E133b',status='NOT_EVALUABLE_MEASUREMENT',screen_only=True,qualifying_pairs=0,final_attempt_closed=True,further_runs_authorized=False,main_capture_readers_probes_patching=False,negative_result_claim=False,model_task_failure_claim=False),'0.24170250','0','0.24170250']
 def test_once_unused_combined_allocation(self):self.assertEqual(validate_contract(*self.fixture())['unused_allocation_released_usd'],'4.75829750')
 def test_unknown_reservation_blocks_release(self):
  a=self.fixture();a[5]='.01'
  with self.assertRaises(Exception):validate_contract(*a)
 def test_nonterminal_or_future_babi_cannot_close(self):
  for k,v in [('status','PENDING'),('further_runs_authorized',True),('qualifying_pairs',20),('final_attempt_closed',False)]:
   a=self.fixture();a[3][k]=v
   with self.assertRaises(Exception):validate_contract(*a)
 def test_missing_synthetic_terminal_cannot_close(self):
  a=self.fixture();a[2].pop()
  with self.assertRaises(Exception):validate_contract(*a)
 def test_scientific_negative_never_substituted(self):
  a=self.fixture();a[3]['negative_result_claim']=True
  with self.assertRaises(Exception):validate_contract(*a)
 def test_extra_cost_not_silently_dropped(self):
  a=self.fixture();a[4]='.3'
  with self.assertRaises(Exception):validate_contract(*a)
