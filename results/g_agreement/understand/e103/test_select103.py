import unittest
from select103 import allocate,select,pair_controls,cohort
from judge103 import render,parse,QUESTION
from all_claims103 import calls_for
class Tests(unittest.TestCase):
 def test_eligibility(self):
  self.assertEqual(cohort({'claims':[{'verdict':'SUPPORTED'},{'verdict':'CONTRADICTED'}]}),'hallucinated')
  self.assertEqual(cohort({'claims':[{'verdict':'SUPPORTED'}]}),'faithful')
  self.assertIsNone(cohort(None));self.assertIsNone(cohort({'claims':[]}))
 def test_allocation(self):
  self.assertEqual(allocate({'a':3,'b':2},3),{'a':2,'b':1})
  self.assertEqual(allocate({'a':0}),{'a':0})
 def test_matching_and_namespace(self):
  units=[]
  for w in (1,2):
   for c in ('hallucinated','faithful'):
    for i in range(8 if c=='faithful' else 3):
     units.append(dict(uid=f'{w}:{c}:{i}',wave=w,bank='B',reader='oracle',cohort=c,source_key=f'{w}:{c}:{i}'))
  s,counts=select(units,4)
  self.assertEqual(len(s),8);self.assertEqual(s,select(list(reversed(units)),4)[0])
  pairs=pair_controls(s,units)
  for u in s:self.assertNotEqual(pairs[u['uid']],u['source_key']);self.assertTrue(pairs[u['uid']].startswith(str(u['wave'])+':'))
  for x in counts:self.assertEqual(x['selected_per_cohort'],2)
 def test_no_self_control_fails(self):
  u=dict(uid='x',wave=1,bank='B',source_key='same',cohort='faithful')
  with self.assertRaises(ValueError):pair_controls([u],[u])
 def test_all_claims_kept(self):
  u=dict(uid="w1:a",wave=1,bank="B",reader="oracle",item_id="i",cohort="hallucinated",own_source_id="s1",control_source_id="s2",claims=[dict(claim="literal",verdict=v) for v in ("CONTRADICTED","SUPPORTED","UNVERIFIABLE")])
  calls=calls_for([u]);self.assertEqual(len(calls),6);self.assertEqual(len({c["id"] for c in calls}),6)
  self.assertEqual({c["verdict"] for c in calls},{"CONTRADICTED","SUPPORTED","UNVERIFIABLE"})
 def test_judge(self):
  s=render('An exact claim.', ['a']*8);self.assertTrue(s.startswith(QUESTION));self.assertNotIn('SUPPORTED',s)
  self.assertTrue(parse('YES\n'));self.assertFalse(parse('no'))
  with self.assertRaises(ValueError):parse('yes because')
  with self.assertRaises(ValueError):render('a', ['a']*7)
if __name__=='__main__':unittest.main()
