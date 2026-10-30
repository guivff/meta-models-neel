import json,unittest
from .e140_judge254 import value_call140,CATEGORIES
class Tests(unittest.TestCase):
 def unit(self):return dict(id='0'*32,property='answer to the factual question',values={'X':['alpha'],'Y':['beta']},readout='alpha and beta and gamma')
 def test_registered_four_fields_and_roundtrip(self):
  u=self.unit();a,_=value_call140(u);b,_=value_call140(json.loads(json.dumps(u,sort_keys=True)));self.assertEqual(a,b);self.assertEqual(set(json.loads(a['rendered']['user'])[0]),{'id','property','values','readout'})
 def test_all_stated_values_other_and_dual(self):
  u=self.unit();_,v=value_call140(u);v(dict(records=[dict(id=u['id'],category='states_value',values=['X','Y','OTHER'],evidence=u['readout'])]))
 def test_none_distinct_from_missing(self):
  u=self.unit();u['readout']='';_,v=value_call140(u);v(dict(records=[dict(id=u['id'],category='silent',values=[],evidence='')]))
  with self.assertRaises(Exception):v(dict(records=[dict(id=u['id'],category='states_value',values=[],evidence='')]))
 def test_no_source_roles_or_probe_fields(self):
  for k in ['source_prompt','context','current','pair_id','label','probe','reader']:
   u=self.unit();u[k]='forbidden'
   with self.assertRaises(Exception):value_call140(u)
