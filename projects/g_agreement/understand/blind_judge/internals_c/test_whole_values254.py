import unittest
from .whole_values254 import encode,assert_encoded,e140_unit
from .e138r_units254 import build,assert_all
from .e140_judge254 import value_call140
class Tests(unittest.TestCase):
 def test_atomic_multi_character_and_unicode(self):self.assertEqual(encode({'A':'Paris','B':'São Paulo'}),{'A':['Paris'],'B':['São Paulo']})
 def test_character_split_rejected(self):
  with self.assertRaises(Exception):assert_encoded({'A':list('Paris'),'B':['Rome']},{'A':'Paris','B':'Rome'})
 def test_nested_or_missing_source_not_guessed(self):
  for x in [None,['Paris'],'']:
   with self.assertRaises(Exception):encode({'A':x,'B':'Rome'})
 def test_every_actual_168_unit_matches_whole_source(self):
  units,joins,_=build();assert_all(units,joins);self.assertEqual(len(units),168)
  for u in units:self.assertTrue(all(len(v)==1 and type(v[0])is str for v in u['values'].values()))
 def test_e140_builder_and_wire_whole_strings(self):
  import json
  u=e140_unit('0'*32,'p','','New York','Los Angeles');c,_=value_call140(u)
  self.assertEqual(json.loads(c['rendered']['user'])[0]['values'],{'X':['New York'],'Y':['Los Angeles']})
