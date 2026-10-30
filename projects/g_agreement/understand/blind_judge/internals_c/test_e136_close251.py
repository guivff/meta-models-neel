import unittest
from .e136_close251 import pointers
class Tests(unittest.TestCase):
 def row(self,code,status='KEPT'):return dict(id='u',kind='cue136',status=status,code=dict(code=code,evidence='')if code else None,judgment=code or'UNPARSEABLE',request_id='r',response_sha256='h')
 def test_codes(self):
  for code in ['YES','NO','UNPARSEABLE',None]:
   status='KEPT'if code in('YES','NO')else'UNPARSEABLE';r=self.row(code,status);x=pointers([dict(id='u',native_id='n')],[r],'test',1)['n'];self.assertEqual(x['code_source']['keys'],[0,'code']);self.assertEqual(x['judgment_source']['keys'],[0,'judgment'])
 def test_missing_not_no(self):
  with self.assertRaises(Exception):pointers([dict(id='u',native_id='n')],[self.row('NO','UNPARSEABLE')],'test',1)
 def test_incomplete(self):
  with self.assertRaises(Exception):pointers([],[],'test',1)
