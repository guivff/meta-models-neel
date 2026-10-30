import unittest
from .e135_close245 import pointers
class PointerTest(unittest.TestCase):
 def fixture(self):return [dict(id=x,readout_id='native'+x)for x in('a','b')],[dict(id=x,kind='original104',status='UNPARSEABLE',code=None)for x in('b','a')]
 def test_explicit_id_join_ignores_row_order(self):
  j,r=self.fixture();v=pointers(j,r,'p',2);self.assertEqual(v['nativea']['code_source']['keys'],[1,'code'])
 def test_null_never_zero(self):
  j,r=self.fixture();self.assertEqual(pointers(j,r,'p',2)['nativea']['status'],'UNPARSEABLE')
 def test_wrong_code_id_rejected(self):
  j,r=self.fixture();r[0].update(status='KEPT',code=dict(id='wrong'))
  with self.assertRaises(Exception):pointers(j,r,'p',2)
if __name__=='__main__':unittest.main()
