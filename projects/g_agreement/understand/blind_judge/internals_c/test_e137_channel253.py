import unittest
from decimal import Decimal
from unittest.mock import patch
from . import transport,resume_e340 as bounds
from .e137_channel253 import render,worker
from .e133_judge import naming_call
from .e138_judge253 import assert_value_allowlist
class Tests(unittest.TestCase):
 def test_exact_original_rubric_payload_roundtrip(self):
  import json
  u=json.loads(json.dumps(dict(id='0'*32,property='holder of the ring',values={'A':['Alice'],'B':['Bob']},readout='')))
  call,_=render('E137',u);self.assertEqual(call,naming_call(u)[0]);assert_value_allowlist(call,u,'E137')
 def test_extrafield_rejected(self):
  with self.assertRaises(Exception):render('E137',dict(id='0'*32,property='p',values={'A':['a']},readout='',source_text='forbidden'))
 def test_registered_cap_namespaces(self):
  with patch('projects.g_agreement.understand.blind_judge.internals_c.e137_channel253.source_gate'):
   with worker('E137'):
    self.assertEqual(transport.CAPS['E137'],Decimal(2));self.assertEqual(bounds.CAPS['E137'],Decimal(2));self.assertEqual(transport.EXPIRY,1793372400)

 def test_serialized_field_order_stable(self):
  import json
  u=dict(id='0'*32,property='p',values={'B':['b'],'A':['a']},readout='')
  self.assertEqual(render('E137',u)[0],render('E137',json.loads(json.dumps(u,sort_keys=True)))[0])
