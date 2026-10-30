import unittest
from .e137_close253 import pointers
class Tests(unittest.TestCase):
 def test_code_and_map_literal(self):
  j=[dict(id='u',native_id='n',value_map={'A':'a','OTHER':'other'})];r=[dict(id='u',kind='E137',status='KEPT',code=dict(id='u',category='states_value',values=['A','OTHER']),request_id='r',response_sha256='h')]
  o=pointers('E137',j,r,'test',1)['n'];self.assertEqual(o['code_source']['keys'],[0,'code']);self.assertEqual(o['value_map'],j[0]['value_map']);self.assertEqual(r[0]['code']['values'],['A','OTHER'])
 def test_null_not_silent_or_zero(self):
  j=[dict(id='u',native_id='n')];r=[dict(id='u',kind='E137',status='UNPARSEABLE',code=None,request_id='r',response_sha256='h')];self.assertIn('n',pointers('E137',j,r,'test',1));self.assertIsNone(r[0]['code'])
