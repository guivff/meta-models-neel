import sys
from pathlib import Path
import numpy as np
import torch
from contextlib import nullcontext
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from runtime62 import capture_batch,acquire_capture,behaviour,read,verify

def item(k,lo,hi):return dict(id=k,base_item_id=k,state='S1',rung='L0',feature='S1_L0',split='test',ids=list(range(hi+2)),first_content_index=lo,read_index=hi,text='frozen')

def test_all_positions_offsets_fp16_and_readpoints(tmp_path,monkeypatch):
 import mats.capture
 def fake(model,seqs,layers,positions,**kw):
  assert layers==[42,44] and seqs==[list(range(5)),list(range(3))]
  assert positions==[[1,2,3,4],[0,1,2,2]]
  return {l:torch.tensor(positions,dtype=torch.float32)[:,:,None].repeat(1,1,5120)+l for l in layers}
 monkeypatch.setattr(mats.capture,'capture',fake)
 oracle=type('Oracle',(),{'base':lambda s:nullcontext(),'model':None,'tok':type('Tok',(),{'pad_token_id':0})()})()
 backend=type('B',(),{'oracle':oracle,'validate_tokenization':lambda s,x:None})()
 budget=type('Budget',(),{'call':lambda s,p,fn,n=0:fn()})()
 cap=acquire_capture([item('a',1,4),item('b',0,2)],backend,budget,tmp_path,{'source_seal_sha256':'synthetic'})
 verify(cap,'CAPTURE_SEAL.json');h=np.load(cap/'all_positions44.npy');assert h.dtype==np.float16 and h.shape==(7,5120)
 assert h[:,0].tolist()==[45,46,47,48,44,45,46]
 assert np.load(cap/'offsets.npy').tolist()==[0,4,7]
 assert read(cap/'items.order.json')==['a','b']
 assert np.load(cap/'acts44.npy')[:,0].tolist()==[48,46]
 assert np.load(cap/'acts42.npy')[:,0].tolist()==[46,44]

def test_l4_uses_base_probability_difference():
 class Model:
  def get_input_embeddings(self):return type('E',(),{'weight':torch.zeros(1)})()
  def __call__(self,**kw):return type('O',(),{'logits':torch.tensor([[[0.,1.,2.]]])})()
 class Tok:
  def encode(self,s,**kw):return [1 if s==' alpha' else 2]
 backend=type('B',(),{'oracle':type('Oracle',(),{'model':Model(),'tok':Tok(),'base':lambda s:nullcontext()})()})()
 x=dict(item('a',0,0),alpha_token_id=1,beta_token_id=2,rung='L4')
 result=behaviour(backend,x);p=torch.tensor([0.,1.,2.]).softmax(-1)
 assert abs(result['score']-float(p[1]-p[2]))<1e-7

def test_eval_measure_pairs_items_and_keeps_silent_zero():
 from measures62 import eval_measure
 items=[];records=[];jj={}
 for c in range(5):
  for i in range(84):
   k=f'{c}:{i}';items.append(dict(id=k,state='S6',split='test',rung=f'C{c}',base_item_id=str(i)))
   for reader in ('oracle','nla'):
    rid=k+reader;hit=c==4
    records.append(dict(id=rid,unit_id=k,reader=reader,repeat=0,text='evaluation' if hit else 'silent'))
    jj[rid]=dict(eval_mention=hit,evidence='evaluation' if hit else '')
 out=eval_measure(items,records,jj)
 assert out['oracle']['R_L4']=='MET' and out['nla']['CI95']==[1.,1.] and out['oracle']['M']['C0']==0
