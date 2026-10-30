import unittest,json
from .e138_judge253 import value_call138,assert_value_allowlist,BASE_SHA,rubric
from .e133_judge import naming_call
class Tests(unittest.TestCase):
 def unit(self):return dict(id='0'*32,property='fact_recall',values={'A':['value one'],'B':['value two']},readout='value one and value two')
 def test_e138_exact_original_e104_adaptation(self):
  u=self.unit();c,v=value_call138(u);self.assertTrue(assert_value_allowlist(c,u,'E138'));v(dict(records=[dict(id=u['id'],category='states_value',values=['A','B'],evidence=u['readout'])]));self.assertIn('names_property_without_value',rubric())
 def test_e137_original_e133_allowlist(self):
  u=self.unit();c,_=naming_call(u);self.assertTrue(assert_value_allowlist(c,u,'E137'))
 def test_both_reject_source_and_private_fields(self):
  for fn in [value_call138,naming_call]:
   for key in ['source_text','source_prompt','prompt','context','label','cue','condition','reader','probe','recipient_old','donor_old']:
    u=self.unit();u[key]='forbidden'
    with self.assertRaises(Exception):fn(u)
 def test_e138_roundtrip(self):
  u=self.unit();self.assertEqual(value_call138(u)[0],value_call138(json.loads(json.dumps(u,sort_keys=True)))[0])
 def test_missing_not_none(self):
  _,v=value_call138(self.unit())
  with self.assertRaises(Exception):v(dict(records=[dict(id='0'*32,category='states_value',values=[],evidence='')]))
 def test_other_explicit_value(self):
  u=self.unit();u['readout']='a different value';_,v=value_call138(u);v(dict(records=[dict(id=u['id'],category='states_value',values=['OTHER'],evidence=u['readout'])]))
