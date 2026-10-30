import unittest
from prepare61 import *
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from transformers import PreTrainedTokenizerFast
  p=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json');assert sha(p)==TOKENIZER_SHA
  tok=PreTrainedTokenizerFast(tokenizer_file=str(p));cls.enc=staticmethod(lambda s:tok.encode(s,add_special_tokens=False));cls.a=d3(cls.enc);cls.b=d4(cls.enc)
 def test_all_build_invariants(self):self.assertEqual(validate(self.a,self.b,self.enc)['D4_prompts'],252)
 def test_D3_exact_timeline_bounds(self):
  for x in self.a:
   self.assertEqual(x['read_token_indices'][0],len(self.enc(x['instruction']))-1)
   self.assertEqual(x['read_token_indices'][-1],len(x['ids'])-1)
 def test_future_completion_absent_at_capture(self):
  for x in self.b:self.assertNotIn('Complete:',x['read_prefix']);self.assertEqual(self.enc(x['read_prefix']),x['read_ids'])
 def test_answers_are_single_tokens(self):
  for x in self.b:self.assertEqual(self.enc(x['answer']),[x['answer_token_id']])
 def test_mutated_arm_pair_rejected(self):
  import copy
  b=copy.deepcopy(self.b);b[0]['copied_sentence']='Wrong sentence.'
  with self.assertRaises(AssertionError):validate(self.a,b,self.enc)
 def test_no_none_target(self):
  self.assertEqual(sum(x['arm']=='none' and x['label'] is None and x['instruction']=='' for x in self.b),84)
if __name__=='__main__':unittest.main()
