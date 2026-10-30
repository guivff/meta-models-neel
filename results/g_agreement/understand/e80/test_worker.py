import time
from pathlib import Path
from types import SimpleNamespace
import pytest
from worker import *

def items():return [dict(id=f'{family}:{i}',feature=family,text='synthetic',ids=[1,2,3,4],read_index=2) for family,n in FAMILIES.items() for i in range(n)]
class TinyBackend:
 def __init__(self):self.calls=[]
 def load_oracle(self):self.calls.append('oracle_setup')
 def load_nla(self):self.calls.append('nla_setup')
 def capture_positions(self,xs):self.calls.append('capture');return {l:np.ones((len(xs),5120),np.float32)*l for l in (42,44)}
 def native_one(self,r,h):self.calls.append(r+'_native');return [[dict(raw='</explanation>',text='synthetic')] for _ in h]

def clock(out):return Clock(out,time.time()+10000,dict(oracle_native=.1,nla_native=.1,nla_setup=.1))
def test_capture_and_go_before_any_reader(tmp_path):
 b=TinyBackend();c=clock(tmp_path);xs=items();validate(xs);binding=dict(experiment='E80',pod_id='stub',source_seal_sha256='a'*64,input_seal_sha256='b'*64);acts,ready=capture_stage(xs,b,c,tmp_path,binding)
 assert not any('native' in k or 'nla_setup'==k for k in b.calls)
 verify(tmp_path/'capture','CAPTURE_SEAL.json',ready['capture_seal_sha256']);assert read(tmp_path/'capture/items.order.json')==[x['id'] for x in xs]
 go=dict(ready,reader_launch_authorized=True,issued_epoch=time.time(),forecast_commit='c'*40,forecast_seal_sha256='d'*64);check_go(go,ready,time.time());assert read_stages(xs,acts,b,c,tmp_path)
 assert len(read(tmp_path/'RECORDS.json'))==1036
 assert c.observed.keys()=={'oracle_native','nla_native'} and len(c.observed['oracle_native'])==65
 assert len([x for x in c.events if 'warmup' in x['phase']])==2
 assert len(list((tmp_path/'jobs').glob('*.json')))==132

def test_invalid_go_rejected(tmp_path):
 ready=dict(experiment='E80',pod_id='stub',source_seal_sha256='a'*64,input_seal_sha256='b'*64,capture_seal_sha256='c'*64,ready_epoch=100)
 go=dict(ready,reader_launch_authorized=True,issued_epoch=110,forecast_commit='a'*40,forecast_seal_sha256='b'*64)
 for changes in [dict(capture_seal_sha256='f'*64),dict(issued_epoch=99),dict(reader_launch_authorized=False),dict(forecast_commit='')]:
  with pytest.raises(ValueError):check_go(dict(go,**changes),ready,120)

def test_labels_and_wrong_counts_rejected():
 xs=items()
 with pytest.raises(ValueError):validate(xs[:-1])
 xs[0]['item_targets']=['private']
 with pytest.raises(ValueError):validate(xs)

def test_clock_and_mean_exclude_warmups(tmp_path,monkeypatch):
 import worker
 now=[100.];monkeypatch.setattr(worker.time,'time',lambda:now[0]);c=Clock(tmp_path,190,dict(oracle_native=1,nla_native=1,nla_setup=1));c.observed={'oracle_native':[1,1,10]};assert c.forecast({'oracle':4,'nla':0},True)
 assert read(tmp_path/'FORECAST.json')['mean_real_or_seed_seconds']['oracle_native']==4
 now[0]=131
 with pytest.raises(ValueError):c.check()

def test_actual_capture_path_truncates_only_at_owner_site(monkeypatch):
 import torch
 from contextlib import nullcontext
 import mats.capture
 calls=[]
 def capture(model,sequences,layers,positions,**kw):
  calls.append((sequences,layers,positions,kw));return {l:torch.ones((len(sequences),1,5120)) for l in layers}
 monkeypatch.setattr(mats.capture,'capture',capture)
 b=object.__new__(E80Backend);b.oracle=SimpleNamespace(base=lambda:nullcontext(),model=None,tok=SimpleNamespace(pad_token_id=0));b.validate_tokenization=lambda x:None
 result=b.capture_positions(items()[:2]);assert calls[0][0]==[[1,2,3],[1,2,3]] and calls[0][1]==(42,44) and calls[0][2]==[[2],[2]]
 assert all(v.shape==(2,5120) for v in result.values())

def test_readers_only_never_recaptures(tmp_path):
 xs=items();inp=tmp_path/'inputs';cap=inp/'capture';cap.mkdir(parents=True);dump(cap/'items.order.json',[x['id'] for x in xs]);
 for l in (42,44):np.save(cap/f'acts{l}.npy',np.ones((518,5120),np.float32)*l)
 seal(cap,'CAPTURE_SEAL.json',dict(experiment='E80',layers=[42,44],synthetic=False,reader_outputs=0));digest=sha(cap/'CAPTURE_SEAL.json');out=tmp_path/'out';out.mkdir();b=TinyBackend();acts,ready=reuse_capture(inp,[{'id':x['id'],'feature':x['feature']} for x in xs],{'capture_seal_sha256':digest},out,dict(experiment='E80',pod_id='readerpod',source_seal_sha256='a'*64,input_seal_sha256='b'*64))
 assert b.calls==[] and ready['capture_seal_sha256']==digest and ready['capture_reused']
 assert not (out/'capture').exists()
 c=clock(out);c.call('oracle_setup',b.load_oracle);assert read_stages(xs,acts,b,c,out);assert 'capture' not in b.calls
 assert len(read(out/'RECORDS.json'))==1036
 with pytest.raises(ValueError):reuse_capture(inp,list(reversed(xs)),{'capture_seal_sha256':digest},tmp_path/'wrong',{})
