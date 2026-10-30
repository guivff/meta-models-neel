import unittest,copy
from .prepare import entries_for,NATIVE
class Tests(unittest.TestCase):
 def fixture(self):
  key={};joins=[]
  for i in range(400):
   id_=str(i);meta=dict(cue='misuse_intent'if i%2 else'sycophancy_pressure',split='test'if i<320 else'dev',pair_id=str(i//2))
   if i<320:key[id_]=meta
   joins.append(dict(item_id=id_,native_id=id_+':oracle:44',layer=44,**meta,source_ref=dict(sha256=NATIVE,seal='/NATIVE/OUTPUT_SEAL.json',member=f'jobs/{i//8:06d}.json',keys=[i%8,'text'])))
  return joins,key
 def test_exact320_native_pointers_no_text_copy(self):
  e=entries_for(*self.fixture());self.assertEqual(len(e),320);self.assertTrue(all(r['block']==44 and r['identity']['reader']=='oracle'and'text'not in r for r in e))
 def test_duplicate_native_and_missing_test_rejected(self):
  a,k=self.fixture();a[0]=copy.deepcopy(a[1])
  with self.assertRaises(ValueError):entries_for(a,k)
 def test_judgment_substitution_rejected(self):
  a,k=self.fixture();a[0]['source_ref']['seal']='/JUDGE/JUDGMENT_SEAL.json'
  with self.assertRaises(ValueError):entries_for(a,k)
 def test_literal_role_and_label_identity_rejected(self):
  for field,value in [('layer',52),('native_id','wrong'),('split','dev')]:
   a,k=self.fixture();a[0][field]=value
   with self.assertRaises(ValueError):entries_for(a,k)
if __name__=='__main__':unittest.main()
