import unittest,copy
from build_d4a import *
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from transformers import PreTrainedTokenizerFast
  t=PreTrainedTokenizerFast(tokenizer_file='/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json');cls.enc=staticmethod(lambda s:t.encode(s,add_special_tokens=False));cls.items,cls.meta,cls.old=construct(cls.enc)
 def test_full_contract(self):self.assertEqual(validate(self.items,self.meta,self.old,self.enc)['test'],840)
 def test_probe_dev_only_think_balanced(self):
  for pair in ('birds_vs_citrus','instruments_vs_planets'):
   dev=[x for x in self.items if x['split']=='dev' and self.meta[x['id']]['probe_pair']==pair]
   self.assertEqual(Counter(self.meta[x['id']]['target_label'] for x in dev),{0:42,1:42});self.assertTrue(all(x['arm']=='think' for x in dev))
 def test_cross_concept_is_other(self):
  for x in self.items:
   if x['arm']=='cross':self.assertNotEqual(self.meta[x['id']]['target_concept'],self.meta[x['id']]['instructed_concept'])
 def test_new_answers_single_token(self):
  for x in self.items:self.assertEqual(self.enc(x['answer']),[x['answer_token_id']])
 def test_old_record_mutation_rejected(self):
  items=copy.deepcopy(self.items);items[0]['read_prefix']+='changed'
  with self.assertRaises(AssertionError):validate(items,self.meta,self.old,self.enc)
if __name__=='__main__':unittest.main()
