import unittest,json
from .phases253 import render,check_r2
class Tests(unittest.TestCase):
 def test_r_roundtrip_and_no_source(self):
  u=dict(id='0'*32,readout='literal text',cue='sycophancy_pressure');self.assertEqual(render('E136R',u)[0],render('E136R',json.loads(json.dumps(u,sort_keys=True)))[0]);self.assertEqual(set(json.loads(render('E136R',u)[0]['rendered']['user'])),{'id','readout'})
 def test_value_roundtrip(self):
  u=dict(id='0'*32,property='fact_recall',values={'B':['two'],'A':['one']},readout='one');self.assertEqual(render('E138',u)[0],render('E138',json.loads(json.dumps(u,sort_keys=True)))[0])
 def test_no_r2_no_dispatch(self):
  with self.assertRaises(Exception):check_r2({},None)
