import unittest,tempfile,subprocess,struct
from pathlib import Path
from audit import normalize,signed,bounds,kappa,compare_judges,HERE
class Tests(unittest.TestCase):
 def test_normalize(self):self.assertEqual(normalize('Ａ  B\nC'),'a b c')
 def test_signed(self):
  self.assertEqual(signed({'category':'states_value','values':['A']},1),1)
  self.assertEqual(signed({'category':'states_value','values':['A']},0),-1)
  self.assertEqual(signed({'category':'states_value','values':['A','B']},0),0)
  self.assertIsNone(signed({'category':'UNPARSEABLE'},0))
 def test_bounds(self):
  xs=[dict(bank='X',reader='oracle',row='r',item_id=str(i),score=v)for i,v in enumerate([1]*20+[None]*80)]
  r=bounds(xs)[0];self.assertAlmostEqual(r['lower']['S'],-.6);self.assertEqual(r['upper']['S'],1);self.assertTrue(r['verdict_can_flip'])
 def test_duplicate(self):
  x=dict(bank='X',reader='oracle',row='r',item_id='a',score=1)
  with self.assertRaises(ValueError):bounds([x,x])
 def test_kappa(self):self.assertEqual(kappa(['a','b'],['a','b'])['kappa'],1)
 def test_constant_kappa(self):self.assertIsNone(kappa(['a'],['a'])['kappa'])
 def test_missing_pairs(self):
  r=compare_judges([dict(bank='x',reader='nla',row='r',primary_score=None,new_score=1)])
  self.assertEqual(r['unparseable_pairs'],1)
 def test_distance(self):
  with tempfile.TemporaryDirectory()as d:
   d=Path(d);subprocess.run(['clang++','-O2','-std=c++17',str(HERE/'near_duplicate.cpp'),'-o',str(d/'run')],check=True)
   a=['abcdefghij','abcdefghijk','same','abc'];b=['abcdefghiX','abcdefghijX','same','abcd']
   with(d/'in').open('wb')as f:
    f.write(struct.pack('<II',len(a),len(b)))
    for s in a+b:f.write(struct.pack('<I',len(s))+struct.pack('<'+'I'*len(s),*[ord(c)for c in s]))
   subprocess.run([str(d/'run'),str(d/'in'),str(d/'out')],check=True)
   pairs={tuple(map(int,l.split()[:2]))for l in(d/'out').read_text().splitlines()}
   self.assertNotIn((0,0),pairs);self.assertIn((1,1),pairs);self.assertIn((2,2),pairs);self.assertNotIn((3,3),pairs)
if __name__=='__main__':unittest.main()
