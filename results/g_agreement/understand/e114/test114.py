import unittest
from build114 import number,variants,annotation_for
T={'nesting_depth':'The current nesting depth is {n}.','indent_level':'The current line is indented by {n} spaces.','page_range_digit':'The hundreds digit of the current page range is {n}.'}
def item(row,text,value,variant=0):return dict(feature=row,split='test',text=text,value=value,variant=variant,label=1-variant,template_index=6,filler_index=0)
class Tests(unittest.TestCase):
 def test_nesting_comment_not_state(self):
  self.assertEqual(number(item('nesting_depth','# [ [\n[ 1,','one')),1)
  self.assertEqual(number(item('nesting_depth','# 101\n[ ( [ 1,','three',1)),3)
 def test_indent_final_line_not_earlier(self):
  self.assertEqual(number(item('indent_level','if True:\n            pass\n    pass','four')),4)
 def test_current_page_not_distractor(self):
  self.assertEqual(number(item('page_range_digit','Citation fragment 7: pp. 816–\nCurrent citation: pp. 416–','A')),4)
 def test_pair_changes_only_one_prepended_sentence_not_gold(self):
  a=item('page_range_digit','Citation fragment 7: pp. 816–\nCurrent citation: pp. 416–','A');b=item('page_range_digit','Citation fragment 7: pp. 416–\nCurrent citation: pp. 816–','B',1)
  v=list(variants(a,b,T));self.assertEqual([x[3] for x in v],[4,8]);self.assertEqual(a['label'],1)
  for _,sentence,text,_ in v:self.assertEqual(text,sentence+'\n'+a['text'])
 def test_dev_and_label_mismatch_rejected(self):
  a=item('indent_level','    pass','four');a['split']='dev'
  with self.assertRaises(ValueError):number(a)
  with self.assertRaises(ValueError):number(item('nesting_depth','[ [ [ 1,','one'))
 def test_pair_identity_mismatch_rejected(self):
  a=item('indent_level','    pass','four');b=item('indent_level','            pass','twelve',1);b['filler_index']=1
  with self.assertRaises(ValueError):list(variants(a,b,T))
 def test_optional_annotations_are_not_missing_labels(self):
  a=item('indent_level','    pass','four');a['id']='source'
  self.assertEqual(annotation_for(a,{}),{});self.assertEqual(number(a),4)
  a['feature']='page_range_digit'
  with self.assertRaises(ValueError):annotation_for(a,{})
if __name__=='__main__':unittest.main()
