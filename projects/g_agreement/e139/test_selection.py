import unittest
from .selection import select,graft
class Tests(unittest.TestCase):
 def test_balance_and_order_independence(self):
  rows=[dict(id=str(i),split='test',label=i%2,genre=(i//2)%2)for i in range(80)]
  x=select(rows,'evaluation_cue','test',cell='genre')
  self.assertEqual(x,select(rows[::-1],'evaluation_cue','test',cell='genre'))
  self.assertEqual(len(x),20)
  for a in (0,1):
   for b in (0,1):self.assertEqual(sum(r['label']==a and r['genre']==b for r in x),5)
 def test_insufficient_fails_no_refill(self):
  with self.assertRaises(ValueError):select([dict(id='a',label=0,split='test')],'language','test')
 def test_exact_readout_preserved_and_neutral_matches(self):
  enc=lambda s:s.split()
  text='  original\n- item \n';xs,m=graft(text,'inside_string',0,enc)
  self.assertEqual(xs['original'],text)
  self.assertTrue(xs['true'].startswith(text+'\n'))
  self.assertEqual(m['tokens']['true'],m['tokens']['neutral'])
if __name__=='__main__':unittest.main()
