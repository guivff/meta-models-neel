import unittest
from compute65 import duration
from onsets65 import onset
from bins65 import count_p,run_length
class Tests(unittest.TestCase):
 def test_inclusive_token(self):
  offsets=[(0,3),(3,5),(5,9)]
  self.assertEqual(duration(offsets,9),1);self.assertEqual(duration(offsets,5),2);self.assertEqual(duration(offsets,1),3)
 def test_plan_end(self):
  s='Use French.\nQuestion: Explain rain.\nAnswer:'
  p,_=onset('E59',{'feature':'language_plan','text':s})
  self.assertEqual(s[:p],'Use French.')
 def test_nested_parenthesis_does_not_reset_membership(self):
  s='Start (outer (inner) more words'
  p,_=onset('E36',{'feature':'prose_paren','text':s})
  self.assertEqual(p,s.index('(')+1)
 def test_parenthesis_close_resets(self):
  s='Start (inside) outside'
  p,_=onset('E36',{'feature':'prose_paren','text':s})
  self.assertEqual(p,s.index(')')+1)
 def test_unknown_onset_explicit(self):
  p,r=onset('X',{'feature':'unknown','text':'Example'})
  self.assertIsNone(p);self.assertIn('No certified',r)
 def test_count_rule_held(self):
  p,r=count_p('W1',{'feature':'prose_column','text':'Example','value':'short'},[(0,7)])
  self.assertIsNone(p);self.assertIn('do not specify',r)
 def test_no_none_probe_label(self):
  self.assertIsNone(onset('E57',{'feature':'focus_none','text':'Copy this.'})[0])
 def test_latex_comment_boundary(self):
  s='\\begin% environment follows\n{equation}\nx'
  p,_=onset('E36',{'feature':'latex_environment','text':s})
  self.assertEqual(s[:p],'\\begin% environment follows\n{equation}')
 def test_within_bin_changes_do_not_reset(self):
  text='x'*69;offsets=[(i,i+1) for i in range(69)]
  p,_=count_p('E56',{'feature':'linewrap_implicit','text':text,'value':'long'},offsets)
  self.assertEqual(p,15) # first >=55 character through character 69, inclusive
 def test_asked_count_remains_original(self):
  text='abc\nHow many characters are on the current line so far?'
  p,_=count_p('E56',{'feature':'linewrap_asked','text':text,'value':'short'},[(i,i+1) for i in range(len(text))])
  self.assertEqual(p,len(text))
 def test_bin_exit_then_return_resets(self):
  self.assertEqual(run_length(['A','A','B','A','A'],'A'),2)
 def test_data_role_persists_across_rows(self):
  text='| A | B |\n| --- | --- |\n| one | two |\n| three'
  p,_=onset('E36',{'feature':'table_role','text':text})
  self.assertEqual(p,text.index('| one')+1)
if __name__=='__main__':unittest.main()
