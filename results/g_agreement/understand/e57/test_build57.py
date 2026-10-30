"""CPU-only semantic and custody checks before the input freeze."""
import unittest
from bank57 import *
from prepare57 import verify
TOKENIZER=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json')
class BankTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from transformers import PreTrainedTokenizerFast
  assert sha(TOKENIZER)==TOKENIZER_SHA
  cls.tok=PreTrainedTokenizerFast(tokenizer_file=str(TOKENIZER))
  cls.enc=staticmethod(lambda s:cls.tok.encode(s,add_special_tokens=False))
  cls.r,cls.d,cls.a,cls.c=construct(cls.enc)
 def test_complete_build_checks(self):self.assertEqual(len(verify(self.r,self.a,self.enc)),20)
 def test_entity_first_token_and_later_distinction(self):
  self.assertEqual(len(group_a.PAIRS),6)
  for a,b in group_a.PAIRS:
   aa,bb=self.enc(' '+a),self.enc(' '+b)
   self.assertEqual(aa[0],bb[0]);self.assertNotEqual(aa[1:],bb[1:])
 def test_reused_count_arms_unchanged(self):
  source=json.loads((HERE.parent/'e56/cache/bank_2026-10-27_v1/items.PRIVATE.json').read_text())
  for row in ['linewrap_implicit','linewrap_asked']:
   expected={x['id']:x for x in source if x['feature']==row}
   actual={x['id']:x for x in self.r if x['feature']==row}
   self.assertEqual(actual,expected)
 def test_first_letter_derived_and_shared_answer_disclosed(self):
  by={x['id']:x for x in self.r}
  for x in self.r:
   if x['feature']=='count_gradient_first_letter':
    a=self.a[x['id']]
    self.assertEqual(x['text'],by[a['report_id']]['text']+'\n'+FIRST_LETTER_QUESTION)
    self.assertEqual(a['expected_letter'],number_word(a['original_count'])[0])
  self.assertEqual({a['expected_letter'] for a in self.a.values() if 'expected_letter' in a},{'s'})
 def test_no_invented_probe_targets(self):
  for row in UNLABELLED:
   self.assertFalse(self.d[row]['probe_applicable'])
   self.assertTrue(all(x['label'] is None for x in self.r if x['feature']==row))
 def test_capacity_single_token_diverse_nouns(self):
  for x in self.r:
   if x['feature']=='capacity_list':
    nouns=self.a[x['id']]['list_nouns']
    self.assertEqual(len(set(nouns)),12)
    self.assertTrue(all(len(self.enc(' '+w))==1 for w in nouns))
 def test_page_end_digit_and_family_balance(self):
  counts=Counter()
  for x in self.r:
   if x['feature']=='page_range_digit':
    a=self.a[x['id']];self.assertEqual(str(a['authored_range_end'])[0],a['expected_answer'])
    counts[x['split'],a['pair_family'],x['variant']]+=1
  for split in ['dev','test']:
   for f in range(4):self.assertEqual(counts[split,f,0],counts[split,f,1]);self.assertGreater(counts[split,f,0],0)
 def test_sentiment_checker_and_swap(self):
  for x in self.r:
   if x['feature']=='sentiment_judgement':
    self.assertEqual(amendment_rows.check_label(x['feature'],x['text']),x['value'])
    self.assertEqual(self.a[x['id']]['continuation_pair'],[' positive',' negative'])
 def test_label_checker_rejects_unknown_review(self):
  with self.assertRaises(ValueError):amendment_rows.check_label('sentiment_judgement','My experience was ambiguous. Overall, the review is')
if __name__=='__main__':unittest.main()
