import unittest
from collections import Counter
from bank108 import native_items,CATEGORIES,DELAYED,IMMEDIATE,SURFACES
class Tests(unittest.TestCase):
 def test_grid(self):
  xs=native_items();self.assertEqual(len(xs),1008);self.assertEqual(len({x['id'] for x in xs}),1008);self.assertEqual(len({x['text'] for x in xs}),1008)
  self.assertEqual(set(Counter((x['category'],x['arm']) for x in xs).values()),{42})
  for cat in CATEGORIES:
   groups=[{x['prompt_id'] for x in xs if x['category']==cat and x['arm']==arm} for arm in ('immediate','delayed')];self.assertEqual(groups[0],groups[1])
 def test_raw_read_and_delay(self):
  for x in native_items():
   self.assertTrue(x['text'].endswith(':'));self.assertNotIn('<|im_start|>',x['text'])
   if x['arm']=='delayed':self.assertIn('At the park,',x['text']);self.assertIn('one sentence',x['text'] if 'one sentence' in x['text'] else x['text'].replace('a sentence','one sentence'))
 def test_frozen_shape(self):
  self.assertEqual((len(IMMEDIATE),len(DELAYED),len(SURFACES)),(6,6,7));self.assertEqual(len(CATEGORIES),12)
  self.assertEqual(native_items(),native_items())
if __name__=='__main__':unittest.main()
