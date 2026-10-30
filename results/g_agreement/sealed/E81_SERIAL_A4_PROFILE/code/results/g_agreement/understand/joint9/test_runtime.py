import time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from runtime import *
from smoke_profile import TinyBackend,TinyOracle,TinyModel
from contextlib import nullcontext

def smoke(out):
 out.mkdir();TinyOracle.base=lambda self:nullcontext();TinyModel.get_input_embeddings=lambda self:self.emb;b=TinyBackend();b.load_oracle();(out/'jobs').mkdir();np.save(out/'h.npy',np.ones((1,5120),np.float32));clock=Clock(out,time.time()+10000)
 x={'id':'i','feature':'row','split':'test','ids':[1],'text':'stub'};jobs=[]
 for r in ('oracle','nla'):
  for kind in ('native','continuation'):
   n=len(jobs);jobs.append(dict(exp='E56',reader=r,kind=kind,units=[x],h_file='h.npy',phase=r+'_'+kind,key=str(n),resume_number=n,measured_seconds=.001,pairs=[[' a',' b']],arm='own'))
 done=execute_remaining(jobs,out,b,clock,out);require(len(done)==4 and len(list((out/'jobs').glob('*.json')))==4,'each unfinished job executed once')
 from smoke_joint import smoke_joint
 smoke_joint(out/'all_registered_paths')

def test_all_runtime_paths(tmp_path):smoke(tmp_path/'smoke')

def test_cap_totals_and_partition(tmp_path):
 assert {e:sum(v) for e,v in CAPS.items()}=={'E56':17845,'E57':21619,'E61':18876}
 p={'identity':'i','jobs':[dict(exp='E56',shard=0,retained_pilot=False),dict(exp='E56',shard=0,retained_pilot=True)]};assert len(selected_jobs(p,'E56',0))==1
