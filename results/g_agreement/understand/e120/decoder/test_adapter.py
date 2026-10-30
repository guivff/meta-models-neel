import unittest,tempfile
from pathlib import Path
import numpy as np
from probes import fit_dev,reading,validate_metadata,POSITIONS
from run_once import claim

def metadata():
 labels=[];order={'dev':[],'test':[]}
 for split,n,offset in [('dev',50,0),('test',100,50)]:
  for i in range(offset,offset+n):
   for genre in [0,1]:
    for addressed in [0,1]:
     ident=f'{i}:{genre}:{addressed}';labels.append(dict(public_id=ident,matched_set=i,genre=genre,addressed=addressed,split=split));order[split].append(dict(id=ident,split=split,first_token_id=12+genre,source_layer=44,injected_position=24,first_generated_position=56))
 return order,[r for rows in order.values() for r in rows],labels
class Adapter(unittest.TestCase):
 def test_exact_cells_and_token_counts(self):
  o,i,l=metadata();ys,t=validate_metadata(o,i,l);self.assertEqual(np.bincount(ys['dev']).tolist(),[100,100]);self.assertEqual(t['test']['genre=1,addressed=0']['token_id_counts'],{13:100});self.assertEqual(t['combined']['genre=0,addressed=1']['n'],150)
 def test_split_quartet_contamination_rejected(self):
  o,i,l=metadata();l[-1]['matched_set']=0
  with self.assertRaises(AssertionError):validate_metadata(o,i,l)
 def test_wrong_token_position_rejected(self):
  o,i,l=metadata();o['test'][0]['first_generated_position']=24
  with self.assertRaises(AssertionError):validate_metadata(o,i,l)
 def test_registered_first_token_late_layers_only(self):
  g={str(l):dict(zip(POSITIONS,[1.,.65])) for l in range(64)};self.assertEqual(reading(g)['R_EV2'],'STATE_NOT_SURVIVING');g['47'][POSITIONS[1]]=1;self.assertEqual(reading(g)['R_EV2'],'STATE_NOT_SURVIVING');g['63'][POSITIONS[1]]=.90;self.assertEqual(reading(g)['R_EV2'],'DECODER_STATE_CARRIED')
 def test_missing_grid_rejected(self):
  with self.assertRaises(AssertionError):reading({})
 def test_dev_only_cv_recipe_and_tie(self):
  y=np.tile([0,1],20);x=np.column_stack([y*2-1,np.zeros(40)]);m,s=fit_dev(x,y);self.assertEqual(s['selected_C'],.01);self.assertEqual(len(s['dev_CV']),5);self.assertTrue(all(len(v['fold_AUROC'])==5 for v in s['dev_CV']));self.assertFalse(s['test_used_for_selection']);self.assertEqual(m.classes_.tolist(),[0,1])
 def test_exclusive_guard(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'ONCE.json';claim(p,{'a':1})
   with self.assertRaises(FileExistsError):claim(p,{'a':2})
class NativeLayout(unittest.TestCase):
 def test_native_ab_metadata_normalization(self):
  from prepare_capture import normalized
  o,ix,labels=metadata();native=[dict(id=r['id'],split=r['split'],block=44,member='states/0000.npy',vector_index_in_file=0,first_token_id=r['first_token_id']) for r in ix]
  fmt=dict(layers=list(range(64)),positions=list(POSITIONS),source_layer=44,first_generated_position=56,carrier_ids=list(range(56)),injected_position=24,alpha=16000,transform='unit',first_generated_capture='full forward on native injected carrier plus its actual greedy first token; not the last carrier token')
  ni,no=normalized(native,fmt,[r['id'] for r in o['dev']],[r['id'] for r in o['test']]);ys,t=validate_metadata(no,ni,labels);self.assertEqual(len(ys['test']),400)
  fmt['first_generated_position']=55
  with self.assertRaises(AssertionError):normalized(native,fmt,[r['id'] for r in o['dev']],[r['id'] for r in o['test']])
if __name__=='__main__':unittest.main()
