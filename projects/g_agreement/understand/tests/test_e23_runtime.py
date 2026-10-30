from contextlib import nullcontext
from types import SimpleNamespace
import numpy as np
import pytest
from projects.g_agreement.understand import e23 as E,e23_runtime as R,e23_worker as W
from projects.g_agreement.understand.cpu import dump,read,sha,verify,seal
from projects.g_agreement.understand.followup_packed import jsonl


@pytest.fixture
def fixture(tmp_path,monkeypatch):
    clock=SimpleNamespace(epoch=1800000000.,mono=1.)
    timer=SimpleNamespace(time=lambda:clock.epoch,monotonic=lambda:clock.mono)
    monkeypatch.setattr(R,'ROOT',tmp_path);monkeypatch.setattr(R,'STOP',clock.epoch+20000)
    monkeypatch.setattr(R,'time',timer);monkeypatch.setattr(W,'time',timer)
    for name in [R.BRIEF,*R.REQUIRED_SOURCE]:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('synthetic fixture')
    dump(tmp_path/R.PLAN,{'authority_commit':'e347b86a','primary_measure':'raw_M1_frozen_true_activation_direction'})
    assignment={'issuer':'integrator','experiment':'E23','gpu_count':1,'pod_id':'synthetic','source_commit':'synthetic',
        'brief_registered':True,'brief_pushed':True,'external_hardstop_verified':True,'hold_renewer_verified':True,
        'brief_sha256':sha(tmp_path/R.BRIEF),'plan_sha256':sha(tmp_path/R.PLAN),
        'source_files':{f:sha(tmp_path/f) for f in R.REQUIRED_SOURCE},'allocated_gpu_seconds':5400,'previous_gpu_seconds':0,
        'provider_created_epoch':clock.epoch-10,'setup_deadline_epoch':clock.epoch+1490,'deadline_epoch':clock.epoch+6890,
        'setup_allowance_seconds':1500,'forecast_method':R.FORECAST_METHOD}
    ap=tmp_path/'assignment.json';dump(ap,assignment)
    g=R.Gate(ap,{k:3 for k in R.PATHS});out=tmp_path/'out';out.mkdir();g.out=out
    def tick(seconds=.1):clock.mono+=seconds;clock.epoch+=seconds
    return SimpleNamespace(g=g,root=tmp_path,path=ap,assignment=assignment,clock=clock,tick=tick)


def target_pilot(f):
    for k in E.TARGET_PATHS:f.g.warm(k,.1)
    f.g.start()
    for k in E.TARGET_PATHS:
        for j in range(3):f.tick();f.g.record(k,.1,retained=False)


def test_unknown_AR_cannot_be_zero_or_admitted(fixture):
    f=fixture;target_pilot(f)
    assert f.g.forecast()['F_seconds'] is None
    with pytest.raises(ValueError,match='three'):f.g.admit()
    f.g.admit_prefix();f.g.record('capture',.1,retained=True)
    with pytest.raises(ValueError,match='forbidden'):f.g.record('asked_44_W1',.1,retained=True)


def test_full_forecast_charges_prefix_and_late_warm_no_clock_reset(fixture):
    f=fixture;target_pilot(f);start=f.g.started;f.g.admit_prefix()
    for k in ('capture','generation'):
        for j in range(3):f.tick(1);f.g.record(k,1.,retained=True)
    for k in E.AR_PATHS:
        f.tick(.5);f.g.warm(k,.5)
        for j in range(3):f.tick(.1);f.g.record(k,.1,retained=False)
    elapsed=f.g.elapsed(); expected=elapsed+len(E.TARGET_PATHS[2:]+E.AR_PATHS)*3*.1
    assert f.g.forecast()['F_seconds']==pytest.approx(expected)
    f.g.admit();f.g.start();assert f.g.started==start
    assert f.g.cap==pytest.approx(1.5*expected+360)
    verify(f.g.out,'FORECAST_SEAL.json')


def test_full_forecast_no_fit_is_sealed_and_production_not_admitted(fixture):
    f=fixture;target_pilot(f);f.g.admit_prefix()
    for k in E.AR_PATHS:
        f.g.warm(k,.5)
        for j in range(3):f.tick(2);f.g.record(k,2.,retained=False)
        f.g.counts[k]=1000
    with pytest.raises(R.NoFit):f.g.admit()
    assert not f.g.admitted and f.g.status=='NO_FIT'
    verify(f.g.out,'FORECAST_SEAL.json')
    assert read(f.g.out/'FULL_WARMED_FORECAST.json')['fit'] is False


def test_deadline_reserves_retrieval_without_reset(fixture):
    f=fixture;target_pilot(f);start=f.g.started
    f.tick(5400)
    with pytest.raises(TimeoutError):f.g.guard()
    assert f.g.started==start


@pytest.mark.parametrize('change',[{'setup_allowance_seconds':1501},{'allocated_gpu_seconds':5401},{'previous_gpu_seconds':1},{'hold_renewer_verified':False}])
def test_fixed_limits(fixture,change):
    f=fixture;f.assignment.update(change);dump(f.path,f.assignment)
    with pytest.raises(ValueError):R.Gate(f.path,{p:3 for p in R.PATHS})


@pytest.mark.parametrize('bad_parity',[False,True])
def test_single_load_full_collection_seal_order_and_partial_failure(fixture,monkeypatch,bad_parity):
    f=fixture;inp=f.root/'inputs';inp.mkdir()
    items=[{'id':f'{s}-{i}','source_id':str(i),'set':s,'feature':'table_column','split':'dev' if i<8 else 'test','cluster':f'{s}-{i}','ids':[1,2,3],'P32':'prefix','Pfull':'prefix'} for s in ('O','S') for i in range(32)]
    jsonl(inp/'items.input.jsonl',items);units=E.schedule(items);dump(inp/'units.json',units)
    f.g.counts={k:len(v) for k,v in units.items()}
    jsonl(inp/'O.continuations.jsonl',[{'id':r['id'],'feature':r['feature'],'ids':[4]*16,'text':'future'} for r in items if r['set']=='O'])
    dump(inp/'donors.json',{k:{r['id']:r['id'] for r in items} for k in ('Mis','Swap')})
    dump(inp/'pairs.json',{'W1':[['a','b'],['c','d']],'Suraj':[['e','f']]})
    dump(inp/'pilot.json',{'target':[dict(items[32],id='pilot')]*8,'AR_neutral_text':{k:'neutral' for k in E.UNIQUE_ARMS}})
    dump(inp/'provenance.json',{'source_audit_sha256':'fixture'})
    for l in (42,44):np.save(inp/f'O.acts{l}.npy',np.ones((32,5120),np.float32))
    for l in (40,42,44):np.save(inp/f'S.parity{l}.npy',np.ones((32,5120),np.float32))
    seal(inp,[p.name for p in inp.iterdir()],'FIXTURE');(inp/'SCORE_SEAL.json').rename(inp/'INPUT_SEAL.json')
    a=SimpleNamespace(inputs=inp,out=f.g.out);reader=SimpleNamespace(model=object(),tok=object(),base=lambda:nullcontext());ar,tok=object(),SimpleNamespace(encode=lambda *args,**kwargs:[1]);loads=[];events=[]
    def load(a,g):assert g.started is None;loads.append(1);return reader,ar,tok
    def capture(model,rr):
        f.tick();events.append('capture');x=np.ones((len(rr),5120),np.float32)
        if bad_parity and rr[0]['id']!='pilot':x[0]*=-1
        return {l:x for l in (40,42,44)}
    def generate(model,t,rr):f.tick();events.append('generation');return [{'id':r['id'],'feature':r['feature'],'ids':[4]*16,'text':'future'} for r in rr]
    def ar_call(model,t,texts,layer):
        assert model is ar and t is tok
        verify(a.out/'continuations');assert len(rows_local(a.out/'continuations/continuations.jsonl'))==64
        events.append('AR');f.tick();return np.ones((len(texts),5120),np.float32)
    def ask(reader,h,layer,pairs):f.tick();return np.ones((len(h),len(pairs)))
    monkeypatch.setattr(W,'load',load);monkeypatch.setattr(W,'capture',capture);monkeypatch.setattr(W,'greedy16',generate)
    monkeypatch.setattr(W,'reconstruct',ar_call);monkeypatch.setattr(W,'asked',ask)
    status=W.execute(a,f.g)
    assert loads==[1]
    verify(a.out)
    if bad_parity:
        assert status=='INCOMPLETE' and 'AR' not in events
    else:
        assert status=='COMPLETE',read(a.out/'run.json')
        assert max(i for i,e in enumerate(events) if e=='generation')<min(i for i,e in enumerate(events) if e=='AR')
        assert all(f.g.completed[k]==f.g.counts[k] for k in R.PATHS)
        assert read(a.out/'run.json')['checkpoint_load_counts']=={'AR':1,'Oracle_base_backbone':1,'Oracle_adapter':1}


def rows_local(p):
    import json
    return [json.loads(x) for x in p.read_text().splitlines()]
