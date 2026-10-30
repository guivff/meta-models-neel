"""CPU-only E22 full-grid, donor-index, parity and fail-closed launch checks."""
from collections import Counter
from contextlib import nullcontext
from datetime import datetime, timezone
import hashlib
import json
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand.e19.tests.test_run import data_and_directions
from projects.g_agreement.understand.e22 import run as R, request as Q


def data():
    d,_=data_and_directions()
    opposite=d['donors']
    same=[{**r,'donor_index':r['recipient_index']//84*84+(r['recipient_index']+2)%84} for r in opposite]
    d['donors']={'opposite':opposite,'same':same}
    d['provenance']['registration_sha256']=P.sha(P.ROOT/'results/g_agreement/understand/e22/REGISTRATION.md')
    return d


def test_complete_schedule_and_all_donor_arms():
    d=data();plan=list(R.schedule(d))
    assert R.LAYERS==tuple(range(0,64,4))+(63,)
    assert len(R.PROMPTS)==9 and len(plan)==3672
    count=Counter((row,prompt,layer,position,arm,i) for row,prompt,layer,position,arm,ids in plan for i in ids)
    assert len(count)==51408 and set(count.values())=={1}
    assert {len(s[-1]) for s in plan}=={4,16}
    assert ('prose_sentiment','continuation') not in R.PROMPTS
    assert set(s[4] for s in plan)=={'same','opposite'}


def test_unit_preserves_recipient_donor_scores_and_frozen_valid_pairs():
    d=data();row=R.ROWS[1];indices,pairs,prefix,valid=R.contract(d,row,'continuation')
    base=torch.stack([torch.arange(84.),torch.arange(84.)+100],1)
    cap={'recipient':{'per_pair_scores':base},'same':{'per_pair_scores':base+2}}
    calls=[]
    class Mock:
        def score_patch(self,acts,pairs,cap,layer,position,**kw):
            calls.append((acts,pairs,layer,position,kw))
            return {'per_pair_scores':torch.tensor([[1.,12.],[3.,14.]])}
    records=R.unit(Mock(),d,cap,(row,'continuation',63,'preanswer','same',indices[:2]))
    assert calls[0][-1]['prefix']=='- ' and calls[0][-1]['donor_indices']==[0,1]
    assert records[0]['recipient_score']==100 and records[0]['donor_score']==102
    assert records[0]['patched_score']==12 and records[0]['patched_pair_scores']==[1,12]
    assert records[0]['donor_id']==d['items'][indices[2]]['id']
    assert records[0]['item_id']==d['items'][indices[0]]['id']


@pytest.fixture
def clock_factory(tmp_path,monkeypatch):
    now={'monotonic':1000.,'wall':1900000000.};alarms=[];made=[]
    monkeypatch.setattr(R.time,'monotonic',lambda:now['monotonic'])
    monkeypatch.setattr(R.time,'time',lambda:now['wall'])
    monkeypatch.setattr(R.signal,'getsignal',lambda *_:None)
    monkeypatch.setattr(R.signal,'signal',lambda *_:None)
    monkeypatch.setattr(R.signal,'setitimer',lambda _,seconds:alarms.append(seconds))
    monkeypatch.setattr(R,'source_hashes',lambda:{'source':'hash'})
    monkeypatch.setenv('RUNPOD_POD_ID','expected')
    def create(**overrides):
        out=tmp_path/f'clock{len(list(tmp_path.iterdir()))}';out.mkdir()
        a={'experiment':'E22','gpu_count':1,'max_science_seconds':10800.,'setup_allowance_seconds':1500.,
           'source_files':R.source_hashes(),'input_seal_sha256':'input','pod_id':'expected',
           'external_hard_stop_verified':True,
           'hard_deadline_utc':datetime.fromtimestamp(now['wall']+10000,timezone.utc).isoformat()}
        a.update(overrides);path=out/'assignment.json';path.write_text(json.dumps(a))
        clock=R.Clock(path,out,{'input_seal_sha256':'input'});made.append(clock);return clock
    yield create,now,alarms
    for c in made:
        if not c.lock.closed:c.close('TEST')


def test_clock_uses_nine_forecasts_and_continuous_budget(clock_factory):
    create,now,alarms=clock_factory;c=create();c.start();first=c.first
    now['monotonic']+=100;g=c.gate([100.]*9)
    assert g['science_cap_seconds']==1710 and alarms[-1]==1610 and c.first==first
    with pytest.raises(ValueError,match='already'):c.gate([100.]*9)
    with pytest.raises(ValueError,match='restart'):c.start()
    now['monotonic']=first+1710
    with pytest.raises(TimeoutError):c.check()


def test_clock_no_go_and_exact_assignment(clock_factory):
    create,now,_=clock_factory;c=create();c.start();now['monotonic']+=100
    with pytest.raises(RuntimeError,match='NO_GO'):c.gate([1200.]*9)
    assert c.state['gate']['admitted'] is False and c.state['science_cap_seconds']==10800
    with pytest.raises(ValueError,match='max_science'):create(max_science_seconds=9000)
    with pytest.raises(ValueError,match='RUNPOD_POD_ID'):create(pod_id='other')
    d=create();d.state['setup_seconds']=1501
    with pytest.raises(ValueError,match='setup'):d.start()


@pytest.mark.parametrize('forecasts',[[1.]*8,[float('nan')]*9,[float('inf')]*9,[0.]*9,[-1.]*9])
def test_clock_rejects_invalid_forecast(clock_factory,forecasts):
    create,_,_=clock_factory;c=create();c.start()
    with pytest.raises(ValueError,match='nine positive'):c.gate(forecasts)
    assert 'gate' not in c.state


def test_request_requires_committed_sources(tmp_path,monkeypatch):
    monkeypatch.setattr(Q,'source_hashes',lambda:{'runtime':hashlib.sha256(b'new').hexdigest()})
    monkeypatch.setattr(Q.subprocess,'check_output',lambda args,**kw:'c'*40 if args[1]=='rev-parse' else b'old')
    monkeypatch.setattr(Q,'load',lambda *_:pytest.fail('must stop before inputs'))
    with pytest.raises(ValueError,match='uncommitted'):Q.create(tmp_path,tmp_path,tmp_path/'out')


def test_request_pins_kernel_environment_scope_and_cap(tmp_path,monkeypatch):
    monkeypatch.setattr(Q,'source_hashes',lambda:{})
    monkeypatch.setattr(Q.subprocess,'check_output',lambda *_a,**_k:'c'*40)
    monkeypatch.setattr(Q,'load',lambda *_:data())
    (tmp_path/'INPUT_SEAL.json').write_text('{}')
    receipt=tmp_path/'cpu.json';receipt.write_text(json.dumps({'status':'PASS','gpu_hours':0,'layer0_full_swap_check':'PASS'}))
    out=tmp_path/'request.json';Q.create(tmp_path,receipt,out);r=json.loads(out.read_text())
    assert r['model_environment']=='/weights/venv-kernels' and r['launch_argv'][0]=='/weights/venv-kernels/bin/python'
    assert r['assignment_required']['max_science_seconds']==10800 and r['assignment_required']['setup_allowance_seconds']==1500
    assert r['scope']['patch_units']==3672 and r['scope']['patch_records']==51408
    assert r['scope']['items']==420 and r['registration_commit']=='e71d1eeb'


@pytest.mark.parametrize('parity_pass',[True,False])
def test_failed_parity_or_no_go_seals_without_production(tmp_path,monkeypatch,parity_pass):
    from projects.g_agreement.understand import reader_runtime
    from projects.g_agreement.understand.e22 import runtime as module
    import mats.capture
    d=data();(tmp_path/'INPUT_SEAL.json').write_text('{}');calls=[]
    class Clock:
        def __init__(self,*_):self.first=None;self.state={'science_cap_seconds':10800.}
        def setup(self):return nullcontext()
        def start(self):self.first=R.time.monotonic()
        def check(self):pass
        def gate(self,forecasts):
            assert len(forecasts)==9
            raise RuntimeError('NO_GO_WARMED_FORECAST')
        def disarm(self):pass
        def close(self,*_):pass
    class Runtime:
        oracle=SimpleNamespace(model=None,reader=SimpleNamespace(tok=SimpleNamespace(encode=lambda *_a,**_k:[1])))
        def __init__(self,*_a,**_kw):pass
        def capture(self,*_a,**_kw):
            calls.append('capture');return {'scores':[],'per_pair_scores':[],'layer_ids':R.LAYERS,'metadata':{}}
    monkeypatch.setattr(R,'Clock',Clock);monkeypatch.setattr(R,'load',lambda _:d)
    monkeypatch.setattr(R,'source_hashes',lambda:{})
    monkeypatch.setattr(reader_runtime,'load_runtime',lambda *_a,**_kw:None)
    monkeypatch.setattr(module,'E22Runtime',Runtime)
    monkeypatch.setattr(mats.capture,'decoder_blocks',lambda _:list(range(64)))
    monkeypatch.setattr(R,'swap_check',lambda *_:{'passed':parity_pass})
    monkeypatch.setattr(R,'unit',lambda *_a:(calls.append('patch') or []))
    out=tmp_path/'out';result=R.run(tmp_path,'assets','assignment',out)
    assert result['status']=='INCOMPLETE'
    assert ('NO_GO' if parity_pass else 'full activation swap') in result['error']
    assert calls.count('capture')==(108 if parity_pass else 3)
    assert calls.count('patch')==(36 if parity_pass else 1)
    assert not list((out/'units').glob('*.json')) and not (out/'scores.jsonl').read_text()
    assert P.verify(out,'SCORE_SEAL.json')['status']=='SCORES_SEALED_EXPLORATORY_E22'


def test_matching_layout_fullswap_baseline_including_tail_and_both_prompts():
    from projects.g_agreement.understand.tests.test_reader_runtime import oracle
    from projects.g_agreement.understand.reader_runtime import ReaderRuntime
    from projects.g_agreement.understand.e22.runtime import E22Runtime
    d=data();d['activations']=np.random.default_rng(123).normal(size=(420,6)).astype('float32')
    rt=E22Runtime(ReaderRuntime('olens',oracle()))
    row=R.ROWS[0]
    for prompt in ('asked','continuation'):
        indices,_,_,_=R.contract(d,row,prompt)
        cap=R.capture_bundle(rt,d,row,prompt)
        for arm in R.ARMS:
            for ix in (indices[:16],indices[-4:]):
                records=R.unit(rt,d,cap,(row,prompt,0,'injection',arm,ix))
                assert all(r['patched_pair_scores']==r['donor_pair_scores'] for r in records)
                assert all(r['patched_score']==r['donor_score'] for r in records)
        assert R.swap_check(rt,d,cap,row,prompt)['passed']
