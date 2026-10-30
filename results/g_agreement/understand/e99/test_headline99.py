import json,unittest
from pathlib import Path
import hallucination99 as h
import corroboration99 as c
from source99 import SOURCE,prompt_data
class Tests(unittest.TestCase):
 def test_frozen_prompt_identity(self):
  raw=json.loads((SOURCE/'evals/hallucination/judge_prompt_v5c_chat.json').read_text())
  self.assertEqual(h.C['JUDGE_SYSTEM'],raw['system']);self.assertEqual(h.C['JUDGE_USER'],raw['user']);self.assertEqual(h.C['JUDGE_SCHEMA'],raw['schema'])
  self.assertEqual(h.C,prompt_data('hallucination')['constants'])
 def test_single_sample_format(self):
  item={'prompt':'Question {not_a_placeholder}','response':'abc def'};site={'char':3}
  r=h.render(item,site,'A "claim".')
  expected=h.C['JUDGE_USER'].format(prompt=item['prompt'],mark=h.C['READ_MARK'],marked_response='abc'+h.C['READ_MARK']+' def',facts_block='',k=1,samples_block='<readout idx="0">\nA "claim".\n</readout>')
  self.assertEqual(r['user'],expected)
  v=h.render(item,site,'A "claim".',wrong_spans=['A "claim".'])
  self.assertIn('Established FALSE spans of readout 0:\n  - "A \\"claim\\"."'.replace('\\\\','\\'),v['user'])
 def test_corroboration_blinding_and_evidence(self):
  claims=[dict(claim_id='false:0',quote='The door is open.')]
  # IDs used by the caller must be opaque to truth; the renderer accepts no truth field.
  claims[0]['claim_id']='claim-000'
  c.render('The door is open.','An open door.',claims)
  r={'claims':[dict(claim_id='claim-000',corroborated=True,nla_evidence='open door',reason='same')]} 
  self.assertEqual(c.validate(r,claims,'An open door.'),r)
  with self.assertRaises(AssertionError): c.validate(r,claims,'A closed window.')
  with self.assertRaises(AssertionError): c.render('a','b',[dict(claim_id='x',quote='a',truth=True)])
if __name__=='__main__':unittest.main()
