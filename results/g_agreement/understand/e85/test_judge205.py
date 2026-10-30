import unittest
from judge205 import messages, validate, primary
class Tests(unittest.TestCase):
 def test_independent_codes(self):
  r=dict(a_model_self_evaluated=False,b_evaluation_genre_vocabulary=True,c_absent_genre_named=True,a_evidence='',b_evidence='benchmark',c_genres=['README'],c_evidence='README')
  self.assertFalse(primary(r))
  r['a_model_self_evaluated']=True;self.assertTrue(primary(r))
  r['c_genres']=[]
  with self.assertRaises(AssertionError):validate(r)
 def test_blind_source_payload(self):
  import json
  m=messages('print(1)','A README benchmark.')
  self.assertEqual(set(json.loads(m[1]['content'])),{'source_text','readout'})
  for word in ['R-E1 uses only (a)','negation','bare option','source text']:self.assertIn(word,m[0]['content'])
if __name__=='__main__':unittest.main()
