import unittest,json
from .named import messages,validate,QUESTIONS
class Tests(unittest.TestCase):
 def test_exact_questions_readout_only_uid_wire(self):
  for c,q in QUESTIONS.items():
   x=messages('opaque01','original readout',c);self.assertEqual(json.loads(x[1]['content']),dict(id='opaque01',readout='original readout'));self.assertTrue(x[0]['content'].endswith('Question: '+q))
 def test_source_prompt_argument_is_not_accepted(self):
  with self.assertRaises(TypeError):messages('opaque01','original readout','misuse_intent',source_text='PRIVATE SOURCE')
 def test_yes_verbatim_evidence(self):self.assertEqual(validate(dict(code='YES',evidence='presses an answer'),'It presses an answer.' )['code'],'YES')
 def test_no_and_unparseable_are_distinct(self):
  for code in ('NO','UNPARSEABLE'):self.assertEqual(validate(dict(code=code,evidence=''),'')['code'],code)
 def test_bad_codes_schema_and_source_only_evidence_fail(self):
  for r in [dict(code='YES',evidence=''),dict(code='YES',evidence='absent'),dict(code='NO',evidence='x'),dict(code='UNPARSEABLE',evidence='x'),dict(code='maybe',evidence=''),dict(code=True,evidence=''),dict(code='NO',evidence='',label=0)]:
   with self.assertRaises(ValueError):validate(r,'x')
 def test_dropped_cue_not_reintroduced(self):
  with self.assertRaises(ValueError):messages('id','readout','unreliable_tool')
if __name__=='__main__':unittest.main()

class FrozenContractTest(unittest.TestCase):
 def test_contract_questions_and_wire_match_renderer(self):
  from pathlib import Path
  from . import named
  c=json.loads(Path(named.__file__).with_name('CONTRACT.json').read_text())
  self.assertEqual(c['questions'],QUESTIONS);self.assertEqual(c['user_data_fields'],['id','readout']);self.assertFalse(c['source_prompt_on_wire'])
