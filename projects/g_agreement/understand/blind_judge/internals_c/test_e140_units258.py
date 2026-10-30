import copy,json,unittest
from .e140_units258 import build,assert_all
from .e140_judge254 import value_call140
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.units,cls.joins,cls.sources=build()
 def test_all348_original_whole_strings_and_both_members(self):assert_all(self.units,self.joins)
 def test_all1044_roundtripped_readout_only_wires(self):
  for u in self.units:
   for attempt in range(3):
    c,_=value_call140(u);r=json.loads(c['rendered']['user'])[0];self.assertEqual(r,u);self.assertEqual(set(r),{'id','property','values','readout'});self.assertEqual(c,value_call140(json.loads(json.dumps(u,sort_keys=True)))[0])
 def test_char_split_rejected(self):
  us=copy.deepcopy(self.units);us[0]['values']['X']=list(self.joins[0]['X'])
  with self.assertRaises(Exception):assert_all(us,self.joins)
 def test_foreign_prompt_or_role_rejected(self):
  for k in('source_prompt','pair_id','condition','truth','probe','label'):
   u=dict(self.units[0],**{k:'forbidden'})
   with self.assertRaises(Exception):value_call140(u)
