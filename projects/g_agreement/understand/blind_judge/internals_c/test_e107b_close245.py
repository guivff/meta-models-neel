import unittest
from .e107b_close245 import bindings
class BindingTest(unittest.TestCase):
 def fixture(self):return [dict(inventory_id='i',forecast_id='f',judgment_id=t,target=t)for t in('belief','truth')],[dict(id='f',status='GENERATED',text='x')],[dict(id=t,kind='value',status='UNPARSEABLE',code=None)for t in('truth','belief')]
 def test_source_id_join_not_position(self):
  p,g,j=self.fixture();r=bindings(p,g,j,1);self.assertEqual(r[0]['original_code_keys'],[1,'code']);self.assertEqual(r[1]['original_code_keys'],[0,'code'])
 def test_null_stays_null(self):
  p,g,j=self.fixture();self.assertEqual([r['status']for r in bindings(p,g,j,1)],['UNPARSEABLE']*2)
 def test_wrong_code_identity_fails(self):
  p,g,j=self.fixture();j[0]['id']='other'
  with self.assertRaises(Exception):bindings(p,g,j,1)
if __name__=='__main__':unittest.main()
