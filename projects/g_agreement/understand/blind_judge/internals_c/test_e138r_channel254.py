import json,unittest
from unittest.mock import patch
from decimal import Decimal
from . import transport,resume_e340 as bounds
from .e138r_channel254 import render,check_r5,worker
class Tests(unittest.TestCase):
 def test_wire_roundtrip_whole_strings(self):
  u=dict(id='0'*32,property='fact_recall',values={'B':['whole donor'],'A':['whole recipient']},readout='')
  a,_=render('E138R',u);self.assertEqual(a,render('E138R',json.loads(json.dumps(u,sort_keys=True)))[0]);self.assertEqual(json.loads(a['rendered']['user'])[0]['values'],{'A':['whole recipient'],'B':['whole donor']})
 def test_sample_gate_required(self):
  with self.assertRaises(Exception):check_r5({},None)
 def test_actual_cap_namespaces(self):
  with patch('projects.g_agreement.understand.blind_judge.internals_c.e138r_channel254.source_gate'):
   with worker('E138R'):
    self.assertEqual(transport.CAPS['E138R'],Decimal(1));self.assertEqual(bounds.CAPS['E138R'],Decimal(1));self.assertEqual(transport.EXPIRY,1793372400)
