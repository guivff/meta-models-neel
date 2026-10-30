import unittest
from .e107b_judging245 import units_from
from ..rubric202 import amended
class ForecastJudgingTest(unittest.TestCase):
 def fixture(self):
  return [dict(forecast_id='f',judgment_id=t,property='location',values={'A':['X'],'B':['Y']},target=t)for t in ('belief','truth')],[dict(id='f',phase='generation',status='GENERATED',finish_reason='stop',text='Y',refusal=None)]
 def test_exact_forecast_and_original_values(self):
  p,g=self.fixture();u=units_from(p,g,2);self.assertEqual([x['id']for x in u],['belief','truth']);self.assertTrue(all(x['data']['values']==p[0]['values']and x['data']['readout']=='Y'and x['rubric']==amended().decode()for x in u))
 def test_truncation_is_retained(self):
  p,g=self.fixture();g[0]['finish_reason']='length';self.assertEqual(len(units_from(p,g,2)),2)
 def test_missing_not_empty_forecast(self):
  p,g=self.fixture();g[0]['status']='UNPARSEABLE'
  with self.assertRaises(Exception):units_from(p,g,2)
 def test_duplicate_target_rejected(self):
  p,g=self.fixture();p[1]['judgment_id']=p[0]['judgment_id']
  with self.assertRaises(Exception):units_from(p,g,2)
 def test_absent_original_source_rejected(self):
  p,g=self.fixture()
  with self.assertRaises(Exception):units_from(p,[],2)
if __name__=='__main__':unittest.main()
