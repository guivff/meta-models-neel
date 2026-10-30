import copy,unittest
from .e137_intake253 import confirm_map,OTHER
class Tests(unittest.TestCase):
 def fixture(self):
  rows=[dict(item_id=str(i),pair_id='p',member=i,current='x'+str(i),previous='z',value_map={'A':'x0','B':'x1','OTHER':OTHER})for i in(0,1)]
  pairs=[dict(pair_id='p',pair_count=1,value_map=rows[0]['value_map'],members=[dict(item_id=r['item_id'],member=r['member'],current=r['current'],previous=r['previous'])for r in rows])];return rows,pairs
 def test_exact(self):
  r,p=self.fixture();self.assertEqual(set(confirm_map(r,p,['0','1'])),{'0','1'})
 def test_swapped_alphabet(self):
  r,p=self.fixture();p=copy.deepcopy(p);p[0]['value_map']['A']='x1'
  with self.assertRaises(Exception):confirm_map(r,p,['0','1'])
 def test_wrong_role(self):
  r,p=self.fixture();p=copy.deepcopy(p);p[0]['members'][0]['current']='z'
  with self.assertRaises(Exception):confirm_map(r,p,['0','1'])
 def test_partial_or_duplicate(self):
  r,p=self.fixture()
  with self.assertRaises(Exception):confirm_map(r,p,['0'])
