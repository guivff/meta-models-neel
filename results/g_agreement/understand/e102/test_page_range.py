import json,unittest
from page_range102 import render_dev,HERE
class PageRangeTests(unittest.TestCase):
 def test_all_digits(self):
  for d in [1,2,3,4,6,7,8,9]:
   item=dict(split='dev',feature='page_range_digit',value='A' if d<5 else 'B',text=f'Citation fragment 1: pp. 555–\nCurrent citation: pp. {d}25–')
   texts=render_dev(item);self.assertEqual(len(set(texts)),5)
   for text in texts:self.assertTrue(text.startswith('- '));self.assertIn(str(d),text);self.assertNotIn('{',text);self.assertNotIn('\n',text)
 def test_reject_wrong_binding_and_test_split(self):
  item=dict(split='dev',feature='page_range_digit',value='A',text='Current citation: pp. 725–')
  with self.assertRaises(ValueError):render_dev(item)
  item['value']='B';item['split']='test'
  with self.assertRaises(ValueError):render_dev(item)
 def test_only_digit_placeholder(self):
  data=json.loads((HERE/'PAGE_RANGE_TEMPLATES.json').read_text())
  for templates in data['templates_by_family'].values():
   for text in templates:self.assertEqual(text.count('{d}'),1);self.assertNotIn('{',text.replace('{d}',''))
if __name__=='__main__':unittest.main()
