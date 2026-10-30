import unittest
from .freeze import pack_rows,native_sample_zero
from .selection import STATES
class Tests(unittest.TestCase):
 def fixture(self):
  stage=[];dev=[]
  for s in STATES:
   for i in range(20):
    text=' original\ntext ';st=dict(true='- true',false='- false',neutral='- neutral',tokens=dict(true=2,false=2,neutral=2))
    stage.append(dict(state=s,label=i%2,original_id=f'PRIVATE-{s}-{i}',strings=dict(original=text,**{k:text+'\n'+st[k]for k in ('true','false','neutral')}),statements=st))
    if s!='evaluation_cue':dev.append(dict(state=s,label=i%2,text='true source span'))
  return stage,dev,[dict(label=i%2)for i in range(200)]
 def test_exact_public_census_privacy_and_stability(self):
  x=self.fixture();public,rows,ds=pack_rows(*x)
  self.assertEqual(len(public),580);self.assertEqual(len(rows),120);self.assertEqual(len(ds),300)
  self.assertTrue(all(set(r)=={'id','text'}and'PRIVATE'not in r['id']for r in public))
  self.assertEqual(pack_rows(*x)[0],public)
 def test_original_not_stripped_and_appends_not_rewritten(self):
  x=self.fixture();p,r,d=pack_rows(*x);p={r['id']:r['text']for r in p}
  self.assertEqual(p[r[0]['variants']['original']],' original\ntext ')
  self.assertEqual(p[r[0]['variants']['true']],' original\ntext \n- true')
 def test_partial_or_unbalanced_inputs_rejected(self):
  x=self.fixture()
  with self.assertRaises(ValueError):pack_rows(x[0][:-1],x[1],x[2])
  x[0][0]['label']=1
  with self.assertRaises(ValueError):pack_rows(*x)
if __name__=='__main__':unittest.main()

class NativeTests(unittest.TestCase):
 def test_first_frozen_sample_not_text_selection(self):
  rows=[dict(id='x',reader='olens',layer=44,status='COMPLETE',sample=i,raw=t)for i,t in [(1,'second'),(0,'  first  ')]]
  self.assertEqual(native_sample_zero(rows),{'x':'  first  '})
 def test_duplicate_sample_rejected(self):
  r=dict(id='x',reader='olens',layer=44,status='COMPLETE',sample=0,raw='')
  with self.assertRaises(ValueError):native_sample_zero([r,r])
