import unittest
from worker42 import warmed_forecast,record_batch_timing,CAP
import io,json
class ForecastTests(unittest.TestCase):
 def test_cold_batch_never_extrapolated(self):
  self.assertIsNone(warmed_forecast([300.],107))
  self.assertEqual(warmed_forecast([300.,2.],106),212.)
 def test_mean_of_all_warmed(self):
  self.assertEqual(warmed_forecast([300.,4.,2.,3.],104),312.)
  self.assertEqual(warmed_forecast([300.,4.,2.,3.,1.],103),257.5)
 def test_complete_has_no_remaining_forecast(self):
  self.assertEqual(warmed_forecast([300.,2.],0),0.)
 def test_timing_records_cold_and_warm_before_gate(self):
  stream=io.StringIO()
  self.assertIsNone(record_batch_timing(stream,0,32,[300.],107))
  self.assertEqual(record_batch_timing(stream,1,32,[300.,2.],106),212.)
  log=[json.loads(x) for x in stream.getvalue().splitlines()]
  self.assertEqual([r['seconds'] for r in log],[300.,2.])
  self.assertEqual(log[1]['warmed_mean_seconds'],2.)
  self.assertEqual(log[1]['gate_remaining_seconds'],318.)
  self.assertIsNone(log[0]['gate_remaining_seconds'])
 def test_cap_matches_plan_and_request(self):
  from pathlib import Path
  here=Path(__file__).resolve().parent
  self.assertEqual(CAP,1800)
  self.assertEqual(json.loads((here/'RUN_PLAN.json').read_text())['total_gpu_seconds'],CAP)
  request=json.loads((here/'LAUNCH_REQUEST.json').read_text())
  self.assertEqual(request['aggregate_cap_seconds'],CAP)
  self.assertIn('deadline_epoch <= provider_created_epoch + 1800',request['required_assignment'])
if __name__=='__main__':unittest.main()
