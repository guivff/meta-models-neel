import sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from worker import *
from smoke_profile import TinyBackend,TinyOracle,TinyModel,Tok
from contextlib import nullcontext
from unittest.mock import patch

def smoke(out):
 out.mkdir();TinyOracle.base=lambda self:nullcontext();TinyModel.get_input_embeddings=lambda self:self.emb;b=TinyBackend();b.load_oracle()
 def forbidden():raise AssertionError('NLA dropped')
 b.load_nla=forbidden;np.save(out/'h.npy',np.ones((1,5120),np.float32));x=dict(id='x',feature='S1_L4',state='S1',rung='L4',base_item_id='b',split='test',read_index=0,first_content_index=0,alpha_token_id=1,beta_token_id=2,ids=[1],text='stub');jobs=[]
 for kind in ('native','behaviour'):
  n=len(jobs);jobs.append(dict(exp='E62',stage='E62',reader='oracle',kind=kind,phase='E62_oracle_'+kind,key=str(n),number=n,h_file='h.npy' if kind=='native' else None,measured_seconds=1,units=[x]))
 original=Tok.encode
 def encode(self,text,**kw):return [2] if text==' beta' else original(self,text,**kw)
 with patch.object(Tok,'encode',encode):run_stages({'experiment':'E62','jobs':jobs,'retained_pilots':[]},out,b,Clock(out,time.time()+10000),out,{'plan_sha256':'stub'})
 assert read(out/'E62/STAGE_SEAL.json')['NLA'].startswith('NOT RUN') and len(read(out/'E62/COMPLETED.json'))==2

def test_native_and_L4_behaviour(tmp_path):smoke(tmp_path/'smoke')
