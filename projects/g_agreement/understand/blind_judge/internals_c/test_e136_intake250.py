import unittest,copy
from .e136_intake250 import units_for
class Tests(unittest.TestCase):
 def setUp(self):
  self.items=[dict(id=x)for x in('a','b')];self.ptr=[dict(id=x,cue=c,split='test',source_pair_id=x,source_index=i)for i,(x,c)in enumerate(zip(('a','b'),('sycophancy_pressure','misuse_intent')))];self.lab=[dict(id=p['id'],cue=p['cue'],split='test',pair_id=p['id'],messages=[dict(role='system',content='exact system'),dict(role='user',content='exact task')])for p in self.ptr];self.rs=[({},dict(id=x+':oracle:44',item_id=x,reader='oracle',source_layer=44,text=''))for x in('a','b')]
 def test_empty_full_exact(self):
  u,j=units_for(self.rs,self.items,self.ptr,self.lab,2);self.assertEqual(len(u),2);self.assertTrue(all(x['readout']==''and set(x)=={'id','readout','source_text'}for x in u))
 def test_missing(self):
  with self.assertRaises(Exception):units_for(self.rs[:1],self.items,self.ptr,self.lab,2)
 def test_duplicate(self):
  with self.assertRaises(Exception):units_for([self.rs[0]]*2,self.items,self.ptr,self.lab,2)
 def test_wrong_layer(self):
  self.rs[0][1]['source_layer']=52
  with self.assertRaises(Exception):units_for(self.rs,self.items,self.ptr,self.lab,2)
 def test_role_join(self):
  self.lab[0]['cue']='misuse_intent'
  with self.assertRaises(Exception):units_for(self.rs,self.items,self.ptr,self.lab,2)
