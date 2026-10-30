import unittest
from .e138r_close254 import pointers
class Tests(unittest.TestCase):
 def test_original_wholevalue_code_source_and_identity(self):
  j=[dict(id='u',native_id='n',recipient_letter='B',donor_letter='A',defective_E138_unit_id='old')];r=[dict(id='u',kind='E138R',status='KEPT',code=dict(id='u',values=['A','B']),request_id='r',response_sha256='h')]
  o=pointers('E138R',j,r,'test',1)['n'];self.assertEqual(o['code_source']['keys'],[0,'code']);self.assertEqual(o['defective_E138_unit_id'],'old');self.assertEqual(o['recipient_letter'],'B');self.assertEqual(r[0]['code']['values'],['A','B'])
 def test_missing_not_none_code(self):
  j=[dict(id='u',native_id='n')];r=[dict(id='u',kind='E138R',status='UNPARSEABLE',code=None,request_id='r',response_sha256='h')];self.assertIn('n',pointers('E138R',j,r,'test',1));self.assertIsNone(r[0]['code'])
