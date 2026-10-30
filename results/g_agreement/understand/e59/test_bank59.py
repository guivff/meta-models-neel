"""CPU input invariants; no model or reader calls."""
import unittest
from collections import Counter
from build59 import *
TOKENIZER=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json')
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from transformers import PreTrainedTokenizerFast
  assert sha(TOKENIZER)==TOKENIZER_SHA
  cls.tok=PreTrainedTokenizerFast(tokenizer_file=str(TOKENIZER))
  cls.enc=staticmethod(lambda s:cls.tok.encode(s,add_special_tokens=False))
  cls.r,cls.i,cls.v=build(cls.enc)
 def test_coverage_balance(self):
  self.assertEqual(len(self.r),1008)
  for row in ROWS:
   for split in ['dev','test']:
    self.assertEqual(Counter(x['label'] for x in self.r if x['feature']==row and x['split']==split),{0:42,1:42})
 def test_shared_question_last_token_and_length(self):
  for row in ROWS:
   for t in range(12):
    for f in range(7):
     a,b=[render(row,t,f,v) for v in (0,1)]
     self.assertEqual(a.split('\nQuestion: ')[1],b.split('\nQuestion: ')[1])
     aa,bb=self.enc(a),self.enc(b)
     self.assertEqual(aa[-1],bb[-1]);self.assertLessEqual(max(len(aa),len(bb))/min(len(aa),len(bb)),1.10)
 def test_instruction_only_scope(self):
  for x in self.i:
   self.assertNotIn('Question:',x['text']);self.assertNotIn('Answer:',x['text'])
   self.assertEqual(x['text'],instruction(x['feature'],x['template_index'],x['variant']))
 def test_checker_and_invalid_instruction(self):
  for x in self.r:self.assertEqual(check_label(x['feature'],x['text']),x['value'])
  with self.assertRaises(ValueError):check_label('format_plan','Instruction\nInstruction: Undefined.\nQuestion: Question?\nAnswer:')
 def test_value_word_disjointness(self):
  for a,b in VALUE_TERMS.values():self.assertFalse(set(w.lower() for w in a)&set(w.lower() for w in b))
 def test_benign_role_offtopic_matched(self):
  for x in self.r:
   if x['feature']=='decline_plan':
    self.assertIn('Your role is a baking adviser.',x['text'])
    self.assertIn(question('decline_plan',x['filler_index']),x['text'])
 def test_instruction_vocabulary_held_out(self):
  for row in ROWS:
   self.assertTrue(set(ROWS[row][1][0]).isdisjoint(ROWS[row][1][1]))
if __name__=='__main__':unittest.main()
