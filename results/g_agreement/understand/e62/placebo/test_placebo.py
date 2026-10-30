import unittest,copy
from build_placebo import *
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from transformers import PreTrainedTokenizerFast
  t=PreTrainedTokenizerFast(tokenizer_file='/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json');cls.enc=staticmethod(lambda s:t.encode(s,add_special_tokens=False));cls.items,cls.private,cls.old=construct(cls.enc)
 def test_full_contract(self):self.assertEqual(validate(self.items,self.private,self.old,self.enc)['cells'],15)
 def test_unrelated_counts(self):
  self.assertEqual(truth('S1','[[[x]]]'),(0,False));self.assertEqual(truth('S2','a,b'),(1,True));self.assertEqual(truth('S4','one\n\ntwo'),(2,True));self.assertEqual(truth('S5','The clerks near the'),(6,True))
 def test_private_decisions_not_in_items(self):
  for x in self.items:self.assertNotIn('expected_decision',x);self.assertNotIn('unrelated_condition_true',x)
 def test_labels_unchanged(self):
  lookup={x['id']:x for x in self.old}
  for x in self.items:self.assertEqual(x['label'],lookup[self.private[x['id']]['real_rung_id']]['label'])
 def test_read_token_mutation_rejected(self):
  items=copy.deepcopy(self.items);items[0]['ids'][-1]=-99
  with self.assertRaises(AssertionError):validate(items,self.private,self.old,self.enc)
if __name__=='__main__':unittest.main()
