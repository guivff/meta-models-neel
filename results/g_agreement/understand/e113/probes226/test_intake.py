import copy,unittest
from intake import ordered_labels
from probes import ROWS
class IntakeTests(unittest.TestCase):
 def fixture(self):
  order={};labels=[]
  for row in ROWS:
   for split in ['dev','test']:
    g=[]
    for i in range(84):
     x={'id':f'{row}:{split}:{i}','base_id':f'{row}:{split}:{i}','row':row,'split':split,'block':44,'first_token_id':12};g.append(x)
     labels.append({**x,'label':i%2,'bank':'E57' if row in ROWS[:3] else 'E56' if row=='fact_recall' else 'E59'})
    order[row+':'+split]=g
  return order,labels
 def test_exact_order_preserves_labels(self):
  o,l=self.fixture();o[ROWS[0]+':dev'].reverse();a=ordered_labels(o,l);self.assertEqual(a[ROWS[0]+':dev'].tolist(),[1,0]*42)
 def test_duplicate_missing_and_bad_split_fail(self):
  for kind in ['duplicate','missing','split']:
   o,l=self.fixture()
   if kind=='duplicate':o[ROWS[0]+':dev'][0]=o[ROWS[0]+':dev'][1]
   elif kind=='missing':l.pop()
   else:o[ROWS[0]+':test'][0]['split']='dev'
   with self.assertRaises(AssertionError):ordered_labels(o,l)
 def test_source_identity_overlap_fails(self):
  o,l=self.fixture();o[ROWS[0]+':test'][0]['base_id']=o[ROWS[0]+':dev'][0]['base_id'];l[84]['base_id']=o[ROWS[0]+':dev'][0]['base_id']
  with self.assertRaises(AssertionError):ordered_labels(o,l)
if __name__=='__main__':unittest.main()
