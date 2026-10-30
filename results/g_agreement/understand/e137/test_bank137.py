import unittest
from bank137 import generate,check,NAMES,PLACES,SEED
class Tests(unittest.TestCase):
 def test_census_deterministic(self):
  a,b=generate();self.assertEqual((a,b),generate());self.assertEqual(len(a),720);self.assertEqual(len(b),360)
  self.assertEqual({d:sum(x['subdesign']==d for x in b) for d in ['D1','D2','one_hop']},{'D1':150,'D2':150,'one_hop':60})
 def test_all_anti_recency_and_labels(self):
  p,ps=generate();items={x['id']:x['prompt'] for x in p}
  for pair in ps:
   for m in pair['members']:
    s=check(items[m['id']]);self.assertEqual(s['current'],m['current_holder']);self.assertEqual(s['previous'],m['previous_holder'])
    if pair['subdesign']!='one_hop':self.assertNotIn(s['latest_mention'],pair['recipients']);self.assertIn(s['trailing_sentences'],(1,2))
    if pair['subdesign']=='D2':self.assertIn(s['current'],s['chain'][:2]);self.assertTrue(s['returned'])
 def test_only_final_span_diff(self):
  p,ps=generate();items={x['id']:x['prompt'] for x in p}
  for pair in ps:
   normalized=[]
   for m in pair['members']:
    a,b=m['final_recipient_char_span'];text=items[m['id']];self.assertEqual(text[a:b],m['current_holder']);normalized.append(text[:a]+'X'+text[b:])
   self.assertEqual(*normalized)
 def test_transfer_after_distractor_rejected(self):
  p,ps=generate();text=p[0]['prompt'];goal=text.rsplit('. ',1)[1]
  with self.assertRaises(ValueError):check(text.rsplit('. ',1)[0]+'. Alice passes the brass key to Bob. '+goal)
 def test_unknown_sentence_rejected(self):
  p,_=generate()
  with self.assertRaises(ValueError):check(p[0]['prompt'].replace('. Later,','. Someone moves the object. Later,',1))
 def test_latest_current_rejected(self):
  p,ps=generate();pair=ps[0];m=pair['members'][0];text=next(x['prompt'] for x in p if x['id']==m['id']);prefix,goal=text.rsplit('. ',1)
  with self.assertRaises(ValueError):check(prefix+f". {m['previous_holder']} waves to {m['current_holder']}. "+goal)
if __name__=='__main__':unittest.main()
