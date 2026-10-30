import unittest,copy
from .bank import generate,validate,CUES,cue_sentence,TASKS
class Tests(unittest.TestCase):
 def test_census_and_split(self):self.assertTrue(validate(generate()))
 def test_deterministic(self):self.assertEqual(generate(),generate())
 def test_shared_task_all_cues(self):
  rows=generate()
  for t in range(25):
   for k in range(4):
    xs=[x for x in rows if x['base_task']==t and x['template']==k]
    self.assertEqual(len(xs),8);self.assertEqual(len({x['messages'][1]['content'] for x in xs}),1)
 def test_cue_system_only(self):
  for x in generate():
   sentence=cue_sentence(x['cue'],bool(x['label']),TASKS[x['base_task']])
   if sentence:self.assertIn(sentence,x['messages'][0]['content']);self.assertNotIn(sentence,x['messages'][1]['content'])
 def test_invalid_pair(self):
  rows=generate();rows.pop()
  with self.assertRaises(AssertionError):validate(rows)
 def test_wrong_task_rejected(self):
  rows=generate();a=rows[0];other=next(x for x in rows if x['pair_key']==a['pair_key'] and x['label']!=a['label']);other['correct']='bad'
  with self.assertRaises(AssertionError):validate(rows)
if __name__=='__main__':unittest.main()
