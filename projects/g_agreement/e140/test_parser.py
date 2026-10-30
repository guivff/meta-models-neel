import unittest
from .parser import parse_answer,select_pairs
class Tests(unittest.TestCase):
 def test_first_nonempty_line_lowercase_punctuation(self):self.assertEqual(parse_answer("\n \n  'PARIS!'\nRome"),'paris')
 def test_no_fallback_after_punctuation_only_line(self):self.assertEqual(parse_answer('\n ... \nParis'),'')
 def test_no_answer_prefix_or_alias_or_word_trimming(self):
  self.assertEqual(parse_answer('Answer: New-York.\nRome'),'answer newyork')
  self.assertNotEqual(parse_answer('USA'),parse_answer('America'))
 def test_unicode_lower_not_casefold(self):
  self.assertEqual(parse_answer('Björk!'),'björk');self.assertNotEqual(parse_answer('Straße'),parse_answer('STRASSE'))
 def test_empty_and_wrong_type(self):
  self.assertEqual(parse_answer(' \n\t'),'')
  with self.assertRaises(TypeError):parse_answer(None)
 def fixture(self,n):
  pairs=[dict(pair_id=str(i),members=[f'{i}a',f'{i}b'],generation_order=i)for i in range(600)]
  cs={m:('X'if m.endswith('a')or i>=n else'Y')for i,p in enumerate(pairs)for m in p['members']};return pairs,cs
 def test_first84_input_order_not_map_order(self):
  p,c=self.fixture(100);r=select_pairs(p,dict(reversed(list(c.items()))));self.assertEqual([x['generation_order']for x in r['selected']],list(range(84)))
 def test_floor40_and_no_extra_correctness_gate(self):
  p,c=self.fixture(39);self.assertEqual(select_pairs(p,c)['status'],'SCREEN_ONLY')
  p,c=self.fixture(40);self.assertEqual(len(select_pairs(p,c)['selected']),40)
 def test_missing_record_not_imputed_empty(self):
  p,c=self.fixture(40);c.pop(next(iter(c)))
  with self.assertRaises(ValueError):select_pairs(p,c)
if __name__=='__main__':unittest.main()
