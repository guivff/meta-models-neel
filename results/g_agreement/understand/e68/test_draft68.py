import json,unittest
from pathlib import Path
from draft_positions68 import boundary
HERE=Path(__file__).resolve().parent
class DraftTests(unittest.TestCase):
 def test_positions_and_exclusion(self):
  d=json.loads((HERE/'POSITIONS_DRAFT.json').read_text());self.assertIn('DRAFT',d['status']);self.assertEqual(len(d['items']),336)
  for x in d['items']:
   p=x['positions'];a,b,c=[p[k]['index'] for k in ('P_far','P_mid','P_pre')]
   self.assertEqual(b,(a+c)//2);self.assertEqual(x['gap'],c-a);self.assertEqual(x['dropped'],c-a<6)
   if x['row']=='holder_after_handovers':self.assertEqual(x['append_suffix'],'\nQ: Who has it now?\nA:')
   else:self.assertEqual(x['append_suffix'],'');self.assertEqual(c,x['source_tokens']-1)
 def test_examples_and_clause(self):
  for row,xs in json.loads((HERE/'WORKED_EXAMPLES_DRAFT.json').read_text()).items():
   self.assertEqual(len(xs),3)
   for x in xs:
    self.assertEqual(boundary(row,x['original_text']),x['far_clause_end_char_exclusive'])
    if row=='arith_compare':self.assertTrue(x['far_context'].endswith('?'))
 def test_reject_missing_clause(self):
  for row in ('container_after_move','holder_after_handovers','arith_compare','topic_twin'):
   with self.assertRaises(AssertionError):boundary(row,'Unrecognised source text.')
if __name__=='__main__':unittest.main()
