import unittest,copy
from .e117_publication_rows250 import validate_rows
class Tests(unittest.TestCase):
 def setUp(self):
  self.p=[dict(unit=dict(id='u',kind='original57'),calls=['a'])]
  self.t=[dict(unit_id='u',id='a',attempt=0,status='KEPT',request_id='r',response_sha256='h',result=dict(records=[dict(id='u',values=['A'])]))]
  self.r=[dict(id='u',kind='original57',attempts=0,status='KEPT',request_id='r',response_sha256='h',code=dict(id='u',values=['A']))]
 def test_exact(self):self.assertEqual(validate_rows(self.r,self.t,self.p,1),self.r)
 def test_null(self):
  self.t[0]['status']='UNPARSEABLE';self.r[0].update(status='UNPARSEABLE',code=None);validate_rows(self.r,self.t,self.p,1)
 def test_changed_code(self):
  self.r[0]['code']['values']=['B']
  with self.assertRaises(Exception):validate_rows(self.r,self.t,self.p,1)
 def test_wrong_request(self):
  self.r[0]['request_id']='other'
  with self.assertRaises(Exception):validate_rows(self.r,self.t,self.p,1)
 def test_incomplete(self):
  with self.assertRaises(Exception):validate_rows([],self.t,self.p,1)
 def test_wrong_attempt(self):
  self.t[0]['id']='other'
  with self.assertRaises(Exception):validate_rows(self.r,self.t,self.p,1)
