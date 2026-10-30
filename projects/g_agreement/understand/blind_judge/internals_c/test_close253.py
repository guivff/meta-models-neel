import unittest
from .close253 import pointers
class Tests(unittest.TestCase):
 def test_original_e138_code(self):
  j=[dict(id='u',native_id='n',recipient_letter='B',donor_letter='A')];r=[dict(id='u',kind='E138',status='KEPT',code=dict(id='u',values=['A','OTHER']),request_id='r',response_sha256='h')];o=pointers('E138',j,r,'test',1)['n'];self.assertEqual(o['code_source']['keys'],[0,'code']);self.assertEqual(r[0]['code']['values'],['A','OTHER'])
 def test_r_null_preserved(self):
  j=[dict(id='u',native_id='n')];r=[dict(id='u',kind='E136R',status='UNPARSEABLE',code=None,judgment='UNPARSEABLE',request_id='r',response_sha256='h')];self.assertEqual(pointers('E136R',j,r,'test',1)['n']['judgment_source']['keys'],[0,'judgment'])
 def test_incomplete(self):
  with self.assertRaises(Exception):pointers('E138',[],[],'test',1)
