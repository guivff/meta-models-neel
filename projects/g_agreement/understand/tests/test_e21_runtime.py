from types import SimpleNamespace
import numpy as np
import pytest
from projects.g_agreement.understand import e21_runtime as R, e21_worker as W
from projects.g_agreement.understand.cpu import dump,read,sha,verify
from projects.g_agreement.understand.followup_packed import jsonl


@pytest.fixture
def fixture(tmp_path,monkeypatch):
    clock=SimpleNamespace(epoch=1800000000.,mono=1.)
    timer=SimpleNamespace(time=lambda:clock.epoch,monotonic=lambda:clock.mono)
    monkeypatch.setattr(R,'ROOT',tmp_path); monkeypatch.setattr(R,'STOP',clock.epoch+10000)
    monkeypatch.setattr(R,'time',timer); monkeypatch.setattr(W,'time',timer)
    for name in [R.BRIEF,*R.REQUIRED_SOURCE]:
        p=tmp_path/name; p.parent.mkdir(parents=True,exist_ok=True); p.write_text('synthetic CPU fixture')
    dump(tmp_path/R.PLAN,{'authority_commit':'6a2b114e','primary_measure':'raw_cosine_true_minus_opposite'})
    assignment={'issuer':'integrator','experiment':'E21','gpu_count':1,'pod_id':'synthetic',
                'brief_registered':True,'brief_pushed':True,'external_hardstop_verified':True,'hold_renewer_verified':True,
                'brief_sha256':sha(tmp_path/R.BRIEF),'plan_sha256':sha(tmp_path/R.PLAN),
                'source_files':{f:sha(tmp_path/f) for f in R.REQUIRED_SOURCE},
                'allocated_gpu_seconds':2400,'previous_gpu_seconds':0,'provider_created_epoch':clock.epoch-10,
                'setup_deadline_epoch':clock.epoch+1490,'deadline_epoch':clock.epoch+3890,
                'setup_allowance_seconds':1500,'forecast_method':R.FORECAST_METHOD,'source_commit':'synthetic'}
    ap=tmp_path/'assignment.json'; dump(ap,assignment)
    g=R.Gate(ap,{p:3 for p in R.PATHS}); out=tmp_path/'out';out.mkdir();g.out=out
    return SimpleNamespace(clock=clock,g=g,path=ap,assignment=assignment,root=tmp_path)


def warm(g):
    for p in R.PATHS:g.warm(p,.1)
    g.start()


def test_all_paths_measured_before_admission_and_no_reset(fixture):
    f=fixture;g=f.g;warm(g);start=g.started
    for p in R.PATHS[:-1]:
        for _ in range(3):g.record(p,1.,retained=False)
    assert g.forecast()['F_seconds'] is None
    with pytest.raises(ValueError,match='all four'):g.admit()
    with pytest.raises(ValueError,match='forbidden'):g.record(R.PATHS[0],1.,retained=True)
    for _ in range(3):g.record(R.PATHS[-1],1.,retained=False)
    g.admit();g.start()
    assert g.started==start and g.forecast()['F_seconds']==24
    assert g.cap==396
    verify(g.out,'FORECAST_SEAL.json')


def test_no_fit_seals_and_never_admits(fixture):
    g=fixture.g;g.counts={p:1000 for p in R.PATHS};warm(g)
    for p in R.PATHS:
        for _ in range(3):g.record(p,1.,retained=False)
    with pytest.raises(R.NoFit):g.admit()
    assert g.status=='NO_FIT' and not g.admitted
    verify(g.out,'FORECAST_SEAL.json')


@pytest.mark.parametrize('change',[{'setup_allowance_seconds':1501},{'allocated_gpu_seconds':2401},
                                  {'previous_gpu_seconds':1},{'hold_renewer_verified':False}])
def test_assignment_cannot_relax_limits(fixture,change):
    f=fixture;f.assignment.update(change);dump(f.path,f.assignment)
    with pytest.raises(ValueError):R.Gate(f.path,{p:3 for p in R.PATHS})


@pytest.mark.parametrize('fail',[False,True])
def test_one_load_same_warm_object_no_generation_and_partial_seal(fixture,monkeypatch,fail):
    f=fixture;inp=f.root/'inputs';inp.mkdir()
    records=[{'id':f'prod-{p}-{i}','text':f'production {p} {i}','path':p} for p in R.PATHS for i in range(24)]
    pilot=[{'id':f'pilot-{p}-{i}','text':f'dev {p} {i}','path':p,'split':'dev'} for p in R.PATHS for i in range(24)]
    units={p:[list(range(j*24+k,j*24+k+8)) for k in (0,8,16)] for j,p in enumerate(R.PATHS)}
    for name,obj in [('units',units),('pilot_units',units)]:dump(inp/(name+'.json'),obj)
    jsonl(inp/'texts.input.jsonl',records);jsonl(inp/'pilot.input.jsonl',pilot)
    dump(inp/'INPUT_SEAL.json',{'files':{p.name:sha(p) for p in inp.iterdir()}})
    args=SimpleNamespace(inputs=inp,out=f.g.out); model,tokenizer=object(),object();calls=[];loads=[]
    def load(a,g):
        assert g.started is None
        loads.append(1);return model,tokenizer
    def reconstruct(ar,tok,texts):
        assert ar is model and tok is tokenizer
        if texts[0].startswith('production'):
            assert f.g.admitted
            verify(f.g.out,'FORECAST_SEAL.json')
            if fail and any(t.startswith('production') for t in calls):raise TimeoutError('synthetic cap')
        calls.extend(texts);f.clock.mono+=.1;f.clock.epoch+=.1
        return np.ones((len(texts),5120),dtype=np.float32)
    monkeypatch.setattr(W,'load',load)
    status=W.execute(args,f.g,reconstruct=reconstruct)
    assert len(loads)==1
    assert status==('INCOMPLETE' if fail else 'COMPLETE')
    seal=verify(args.out)
    assert seal['status']=='E21_'+status
    assert read(args.out/'run.json')['checkpoint_load_counts']=={'AR':1}
    assert read(args.out/'run.json')['generation_calls']==0
    assert sum(t.startswith('dev') for t in calls)==4*4*8
    if not fail:
        assert read(args.out/'ids.json')==[r['id'] for r in records]
        assert np.load(args.out/'recon.npy').shape==(96,5120)
    else:assert 'recon.npy' not in seal['files']


def test_unusable_whitener_is_secondary_unavailable_only(tmp_path):
    W.export_whitener(object(),tmp_path)
    assert read(tmp_path/'WHITENER.json')['status']=='UNAVAILABLE'
    assert not (tmp_path/'whitener.npz').exists()
