import importlib.util
from pathlib import Path
import unittest
s=importlib.util.spec_from_file_location('quotes',Path(__file__).with_name('quotes.py'));q=importlib.util.module_from_spec(s);s.loader.exec_module(q)
class QuotesTest(unittest.TestCase):
 def test_delimiters_and_apostrophes(self):
  self.assertEqual(q.extract('It isn\'t "ABC" or “def”; `xy` and ‘ghi’.'),['ABC','def','ghi'])
 def test_literal_casefold_without_paraphrase(self):
  self.assertEqual(q.literal_counts('"STRASSE" "a  b" "absent"','Straße a b'),dict(quoted_spans=3,literal_spans=1))
 def test_occurrences_and_no_denominator(self):
  self.assertEqual(q.literal_counts('"abc" "abc"','abc')['literal_spans'],2)
  result=q.report([dict(reader='nla',text='silent',prefix='abc',random_vector=False)])
  self.assertIsNone(result[0]['literal_fraction'])
 def test_no_nested_double_count(self):
  self.assertEqual(q.extract('"abc `def`"'),['abc `def`'])
if __name__=='__main__':unittest.main()
