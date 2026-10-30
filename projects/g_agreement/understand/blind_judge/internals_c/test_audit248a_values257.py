import unittest
from .audit248a_values257 import union_atoms,expected_values,check_values,check_header,suffix
class Tests(unittest.TestCase):
 def test_scalar_candidate_rejected_not_split(self):
  with self.assertRaises(Exception):union_atoms('Paris',[])
 def test_scalar_alias_rejected(self):
  with self.assertRaises(Exception):union_atoms(['Paris'],'')
 def test_whole_original_atoms_aliases_and_flipped_letters(self):
  x=dict(belief=['New York'],belief_aliases=['NYC','New York'],truth=['São Paulo'],truth_aliases=[])
  self.assertEqual(expected_values(x,dict(belief='B',truth='A')),{'B':['New York','NYC'],'A':['São Paulo']})
 def test_character_split_array_and_header_rejected(self):
  good={'A':['Paris'],'B':['Lima']}
  with self.assertRaises(Exception):check_values({'A':list('Paris'),'B':['Lima']},good)
  with self.assertRaises(Exception):check_header(suffix('p',{'A':list('Paris'),'B':['Lima']}),'p',good)
 def test_legitimate_single_character_source_not_false_positive(self):
  good={'A':['7'],'B':['X']};self.assertEqual(check_values(good,good),2);check_header(suffix('p',good),'p',good)

 def test_explicit_absent_truth_is_empty_not_stringified(self):
  self.assertEqual(expected_values(dict(belief=['Paris'],belief_aliases=[],truth=None,truth_aliases=[]),{'belief':'A'}),{'A':['Paris'],'B':[]})
