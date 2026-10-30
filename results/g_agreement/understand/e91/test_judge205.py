import unittest
from judge205 import messages, validate, negated, explicit_only
class Tests(unittest.TestCase):
 def test_subcodes(self):
  for code in ('explicit','indirect'):
   r=dict(concept_mentioned=True,presentation='negated',negation_subcode=code,evidence='synthetic evidence')
   self.assertTrue(negated(r));self.assertEqual(explicit_only(r),code=='explicit')
  with self.assertRaises(AssertionError): validate(dict(concept_mentioned=True,presentation='affirmed',negation_subcode='indirect',evidence='x'))
 def test_blind_payload(self):
  import json
  m=messages('The vase is on the shelf.','That claim is mistaken.')
  self.assertEqual(set(json.loads(m[1]['content'])),{'concept','readout'})
  for word in ['false','mistaken','error','criticised','quoted instruction','bare option']:
   self.assertIn(word,m[0]['content'])
if __name__=='__main__':unittest.main()
