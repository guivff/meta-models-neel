import unittest,copy,hashlib,ast,json
from pathlib import Path
from score79 import score,CONDITIONS,PAIRS
class Tests(unittest.TestCase):
 def fixture(self):
  private={};records=[]
  for row in PAIRS:
   for i in range(84):
    uid=f'{row}:{i}';y=i%2;private[uid]={'feature':row,'label':y}
    for c in CONDITIONS:
     sign=(2*y-1)*(-1 if c=='d_perp' else 1)
     if c=='random':sign=0
     records.append({'id':uid,'feature':row,'condition':c,'pair_logits':[[1000+sign,1000] for _ in PAIRS[row]]})
  return records,private
 def test_correct_reverse_and_ties(self):
  r,p=self.fixture();v=score(r,p)
  for row in PAIRS:
   self.assertEqual(v['auroc']['none'][row],1);self.assertEqual(v['auroc']['d_perp'][row],0);self.assertEqual(v['auroc']['random'][row],.5);self.assertTrue(v['behaviour_condition'][row])
 def test_mean_pairs_before_auc(self):
  r,p=self.fixture()
  for x in r:
   if x['feature']=='language_plan':
    y=p[x['id']]['label'];x['pair_logits']=[[2*y-1,0],[-3*(2*y-1),0]]
  self.assertEqual(score(r,p)['auroc']['none']['language_plan'],0)
 def test_reject_bad_grid_and_nan(self):
  r,p=self.fixture()
  with self.assertRaises(ValueError):score(r[:-1],p)
  with self.assertRaises(ValueError):score(r+[r[0]],p)
  r[0]['pair_logits'][0][0]=float('nan')
  with self.assertRaises(ValueError):score(r,p)
 def test_frozen_functions_verbatim(self):
  here=Path(__file__).resolve().parent;s=(here/'frozen59.py').read_text()
  for ref in json.loads((here/'FROZEN_FUNCTIONS.json').read_text()):
   n=next(n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name==ref['function'])
   self.assertEqual(hashlib.sha256(ast.get_source_segment(s,n).encode()).hexdigest(),ref['verbatim_function_sha256'])
if __name__=='__main__':unittest.main()
