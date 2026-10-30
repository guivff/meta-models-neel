import sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from worker import *
from smoke_profile import TinyBackend,TinyOracle,TinyModel
from contextlib import nullcontext

def smoke(out,e):
 out.mkdir();TinyOracle.base=lambda self:nullcontext();TinyModel.get_input_embeddings=lambda self:self.emb;b=TinyBackend();b.load_oracle()
 def unit(i,split='test'):return dict(id=i,feature='row',split=split,ids=[1],text='stub')
 if e=='E59':state=dict(items=[unit('a'),unit('b'),unit('dev','dev')],plan={'continuation_pairs':{'row':[[' a',' b']]},'donors':{'a':'b','b':'a'}})
 elif e=='E63':state=dict(items=[unit('real'+str(i)) for i in range(200)],random=np.random.default_rng(20261027).standard_normal((200,5120)).astype(np.float32))
 else:state=dict(items=[dict(unit('dev','dev'),read_index=0),dict(unit('new'),read_index=0,completion_ids=[1],completion_text='stub',answer_text='stub',answer_token_id=1,concept='planets',arm='mention',pair_id='p'),dict(unit('old'),read_index=0,completion_ids=[1],completion_text='stub',answer_text='stub',answer_token_id=1,concept='planets',arm='think',pair_id='p',reuse_first_wave=True)])
 cap=capture(state,b,Clock(out,time.time()+10000),out,e,'i');assert read(cap/'items.order.json')==[x['id'] for x in state['items']];jobs=jobs_for({e:state});(out/'jobs').mkdir();budget=Budget(out,{e:10000},time.time()+10000,{'oracle_setup':1,'oracle_native_8_items':.01});done=admit_and_run(jobs,b,budget,lambda j:execute(j,b,out));assert len(done)==len(jobs)
 if e=='D4A':assert all(x['id']=='new' for j in jobs for x in j['units']) and len(state['acts'][44])==3
 if e=='E63':assert sum(len(j['units']) for j in jobs)==800
 if e=='E59':assert {'own','swap'}=={j['arm'] for j in jobs if j['kind']=='continuation'}

def test_all_followon_paths(tmp_path):
 for e in CAPS:smoke(tmp_path/e,e)

def test_staging_and_go_bounds():
 import pytest
 now=time.time();r=dict(pod_id='p',cohort_id=COHORT,capture_seals={},input_seals={},ready_epoch=now-1);g=dict(r,issued_epoch=now,reader_launch_authorized=True,forecast_commit='a'*40,forecast_seal_sha256='b'*64);a={'staging_start_epoch':now-10,'compute_cap_seconds':1080};assert go_end(g,r,a)==now+1080
 with pytest.raises(ValueError):go_end(g,r,dict(a,staging_start_epoch=now-901))


def test_e59_post_capture_window(monkeypatch,tmp_path):
 import worker,pytest
 now=10000.;monkeypatch.setattr(worker.time,'time',lambda:now)
 ready=dict(pod_id='p',cohort_id=COHORT,capture_seals={},input_seals={},ready_epoch=8000.)
 go=dict(ready,issued_epoch=now,reader_launch_authorized=True,forecast_commit='a'*40,forecast_seal_sha256='b'*64)
 ass=dict(experiment='E59',staging_start_epoch=7200.,compute_cap_seconds=7200,go_wait_cap_seconds=2700)
 assert go_deadline(ready,ass)==10700.
 assert go_end(go,ready,ass)==17200.
 with pytest.raises(ValueError):go_end(dict(go,issued_epoch=10701.),ready,ass)
 with pytest.raises(ValueError):go_end(go,ready,dict(ass,experiment='E63'))
 path=tmp_path/'GO.json';dump(path,go);assert wait_go(path,ready,ass)==go
 monkeypatch.setattr(worker.time,'time',lambda:10701.)
 with pytest.raises(GoTimeout):wait_go(path,ready,ass)
 path.unlink()
 with pytest.raises(GoTimeout):wait_go(path,ready,ass)
