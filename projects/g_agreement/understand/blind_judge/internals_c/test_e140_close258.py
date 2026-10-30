import unittest
from .e140_close258 import pointers
class Tests(unittest.TestCase):
 def test_literal_dual_and_missing_distinct(self):
  js=[dict(id='1',native_key='a@44'),dict(id='2',native_key='a@52')];code=dict(id='1',category='states_value',values=['X','Y'],evidence='x y');rows=[dict(id='1',kind='E140',status='KEPT',code=code,request_id='r1',response_sha256='h1'),dict(id='2',kind='E140',status='UNPARSEABLE',code=None,request_id='r2',response_sha256='h2')];p=pointers(js,rows,'seal',2);self.assertEqual(p['a@44']['code_source']['keys'],[0,'code']);self.assertEqual(p['a@52']['status'],'UNPARSEABLE');self.assertEqual(code['values'],['X','Y'])
 def test_native_collisions_reject(self):
  with self.assertRaises(Exception):pointers([dict(id='1',native_key='same')]*2,[],'seal',2)
