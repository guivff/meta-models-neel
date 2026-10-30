"""Exact-archive CPU audit and model-free full acquisition-core smoke."""
import json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path
from common76 import *

SMOKE=r'''
import sys,json
from pathlib import Path
import numpy as np
sys.path.insert(0,sys.argv[1])
import worker76 as W
from common76 import DIM,N,READERS,ARMS
from regex76 import validate_grid
bank={'experiment':'E76','schema':'E76_BLIND_V1','source_bank_count':5,'items':[{'id':f'{i:032x}','ids':[i+1,2],'bank':i%5} for i in range(N)],'selected_indices':list(range(N))}
class Backend:
 def __init__(self):self.calls={r:0 for r in READERS};self.warmups=[]
 def load_oracle(self):pass
 def load_nla(self):pass
 def capture(self,items,batch):
  a=np.array([1+x['ids'][0]%7 for x in items],np.float32)
  return {l:np.repeat((a+l/10)[:,None],DIM,axis=1) for l in (42,44)}
 def native(self,reader,h,batch):
  self.calls[reader]+=len(h)
  dummy=np.random.default_rng(20261028).standard_normal((32,DIM)).astype(np.float32)
  if np.array_equal(h,dummy):
   assert self.calls[reader]==32  # The dummy is the first batch for this reader.
   self.warmups.append(reader)
   return [{'raw':'DISCARDED_SYNTHETIC_ONLY','text':'DISCARDED_SYNTHETIC_ONLY'} for _ in h]
  return [{'raw':'<explanation></explanation>','text':'','malformed':False,'truncated':False,'native_max_new_tokens':512,'native_stop':'</explanation>'} if reader=='nla' else {'raw':'','text':'','malformed':False,'native_max_new_tokens':128} for x in h]
class Clock:
 def __init__(self):self.events=[];self.observed={}
 def warmup(self,phase,fn):fn()
 def call(self,phase,fn,left=0):self.events.append({'phase':phase,'left':left});return fn()
b=Backend();out=Path(sys.argv[2]);out.mkdir();z=np.random.default_rng(20261027).standard_normal((N,DIM)).astype(np.float32)
W.run(b,bank,bank['items'],bank['selected_indices'],z,out,Clock())
records=[json.loads(line) for r in READERS for line in (out/(r+'.jsonl')).read_text().splitlines()]
validate_grid(records)
assert b.calls=={'oracle':1032,'nla':1032}
assert b.warmups==['oracle','nla']
assert not any('DISCARDED_SYNTHETIC_ONLY' in x['text'] for x in records)
assert len(records)==2000
assert json.loads((out/'CALIBRATION.json').read_text())['sealed_before_any_native_readout'] is True
from parity76 import load_parity,generate
parity_out=out.parent/'parity-smoke';parity_out.mkdir()
class ParityBackend:
 def load_oracle(self):pass
 def parity_scores(self,h,pairs):return [[float(i),-float(i)] for i in range(len(h))]
inputs=load_parity(W.CACHE/'parity_inputs',W.sha(W.CACHE/'parity_inputs/INPUT_SEAL.json'))
info=generate(ParityBackend(),Clock(),inputs,parity_out)
assert info['records']==252 and info['labels_loaded'] is False and info['verdict_computed'] is False
assert len((parity_out/'PARITY_SCORES.jsonl').read_text().splitlines())==252
print('E76_MODEL_FREE_CORE_PASS')
'''


def exact(archive):
    source=read(HERE/'POD_SOURCE_SEAL.json');expected=set(source['files'])|{str((HERE/'POD_SOURCE_SEAL.json').relative_to(ROOT))}
    expected|={str((CACHE/'pod_inputs'/n).relative_to(ROOT)) for n in ('BANK.json','gaussian.npy','INPUT_SEAL.json')}
    expected|={str((CACHE/'parity_inputs'/n).relative_to(ROOT)) for n in ('items.jsonl','acts44.npy','templates.json','INPUT_SEAL.json')}
    with tempfile.TemporaryDirectory(prefix='e76-archive-') as tmp:
        root=Path(tmp)
        with tarfile.open(archive) as t:
            members=t.getmembers();names=[m.name for m in members]
            require(len(names)==len(set(names)) and set(names)==expected and all(m.isfile() for m in members),'Positive exact archive whitelist failed')
            for m in members:
                require(not Path(m.name).is_absolute() and '..' not in Path(m.name).parts,'Unsafe archive path')
                p=root/m.name;p.parent.mkdir(parents=True,exist_ok=True)
                with p.open('xb') as f:f.write(t.extractfile(m).read())
                require(sha(p)==sha(ROOT/m.name),'Archive checksum differs from bound file')
        worker=root/HERE.relative_to(ROOT)/'worker76.py'
        env=dict(os.environ,CUDA_VISIBLE_DEVICES='',PYTHONDONTWRITEBYTECODE='1')
        result=subprocess.run([sys.executable,str(worker),'--preflight'],cwd=root,env=env,capture_output=True,text=True,check=True)
        info=json.loads(result.stdout)
        # regex76 is CPU-only and never part of the pod archive; make its validator
        # available to this test process from the original CPU-side source directory.
        script=SMOKE.replace('from regex76 import validate_grid',f"sys.path.append({str(HERE)!r})\nfrom regex76 import validate_grid")
        result=subprocess.run([sys.executable,'-c',script,str(worker.parent),str(root/'cpu-smoke')],cwd=root,env=env,capture_output=True,text=True,check=True)
        require(result.stdout.strip()=='E76_MODEL_FREE_CORE_PASS','Extracted acquisition-core smoke failed')
    return {'experiment':'E76','status':'EXACT_ARCHIVE_CPU_PREFLIGHT_PASS','archive_sha256':sha(archive),'members':sorted(expected),
        'member_checksums_verified':True,'extracted_worker_preflight':info,'extracted_model_free_core_smoke':'PASS:calibration-before-readouts, two native layers, four500-vector pools,2000 one-greedy records and source covariate',
        'split_parity_model_free_smoke':'PASS:252 original-order records, two raw candidate contrasts per item; no labels or verdict',
        'synthetic_warmup_model_free_smoke':'PASS:one32-vector dummy native batch per reader; outputs absent from2000 real records; separate dummy parity batch',
        'GPU_model_calls':0,'actual_native_readouts':0,'private_or_label_files_in_archive':False}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    dump(a.out,exact(a.archive));print('Exact E76 archive CPU preflight PASS')
