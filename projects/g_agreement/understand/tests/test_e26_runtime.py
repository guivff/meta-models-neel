from collections import Counter
from types import SimpleNamespace
import numpy as np
import pytest
from projects.g_agreement.understand import e26_runtime as R, e26_worker as W
from projects.g_agreement.understand.e26 import PATHS, unit_plan, validate_inputs
from projects.g_agreement.understand.e26_bank import FEATURES, expected_counts
from projects.g_agreement.understand.cpu import dump, read, rows, sha, verify
from projects.g_agreement.understand.followup_packed import jsonl


def inputs_fixture(root):
    root.mkdir(); records=[]; receipts=[]
    for feature in FEATURES:
        folder=root/'banks'/feature;folder.mkdir(parents=True)
        candidates=[]
        for category,count in expected_counts(feature).items():
            for i in range(count):
                candidates.append({'id':f'{feature}-{category}-{i}','category':category,'text':f'{category} {i}'})
        jsonl(folder/'candidates.input.jsonl',candidates)
        receipts.append({'feature':feature,'status':'FROZEN_COMPLETE_ROW_BANK',
                         'candidate_sha256':sha(folder/'candidates.input.jsonl')})
        records.extend({**r,'feature':feature} for r in candidates)
    pilot=[]; pu={}
    for j,path in enumerate(PATHS):
        source=next(r for r in records if r['category']==path)
        pilot.extend({'id':f'pilot-{path}-{i}','category':path,'text':source['text'],
                      'source_candidate_id':source['id']} for i in range(24))
        pu[path]=[list(range(j*24+k,j*24+k+8)) for k in (0,8,16)]
    jsonl(root/'texts.input.jsonl',records);jsonl(root/'pilot.input.jsonl',pilot)
    dump(root/'units.json',unit_plan(records));dump(root/'pilot_units.json',pu)
    dump(root/'BANKS.json',{'authority_commit':'4384b1ad','launch_allowed':True,'rows':receipts})
    dump(root/'INPUT_SEAL.json',{'files':{str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}})
    return records


@pytest.fixture
def fixture(tmp_path,monkeypatch):
    clock=SimpleNamespace(epoch=1800000000.,mono=1.)
    timer=SimpleNamespace(time=lambda:clock.epoch,monotonic=lambda:clock.mono)
    monkeypatch.setattr(R,'ROOT',tmp_path);monkeypatch.setattr(R,'STOP',clock.epoch+10000)
    monkeypatch.setattr(R,'time',timer);monkeypatch.setattr(W,'time',timer)
    for name in [R.BRIEF,*R.REQUIRED_SOURCE]:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('synthetic CPU fixture')
    dump(tmp_path/R.PLAN,{'authority_commit':'4384b1ad','primary_measure':'raw_cosine_candidate_ranking'})
    records=inputs_fixture(tmp_path/'inputs')
    assignment={'issuer':'integrator','experiment':'E26','gpu_count':1,'pod_id':'synthetic',
        'brief_registered':True,'brief_pushed':True,'external_hardstop_verified':True,'hold_renewer_verified':True,
        'brief_sha256':sha(tmp_path/R.BRIEF),'plan_sha256':sha(tmp_path/R.PLAN),
        'source_files':{f:sha(tmp_path/f) for f in R.REQUIRED_SOURCE},
        'allocated_gpu_seconds':7200,'previous_gpu_seconds':0,'provider_created_epoch':clock.epoch-10,
        'setup_deadline_epoch':clock.epoch+1490,'deadline_epoch':clock.epoch+8690,
        'setup_allowance_seconds':1500,'forecast_method':R.FORECAST_METHOD,'source_commit':'synthetic',
        'input_seal_sha256':sha(tmp_path/'inputs/INPUT_SEAL.json')}
    ap=tmp_path/'assignment.json';dump(ap,assignment)
    g=R.Gate(ap,{p:len(v) for p,v in unit_plan(records).items()})
    out=tmp_path/'out';out.mkdir();g.out=out
    return SimpleNamespace(clock=clock,g=g,path=ap,assignment=assignment,root=tmp_path,records=records)


def warm(g):
    for p in PATHS:g.warm(p,.1)
    g.start()


def test_full_forecast_counts_overhead_and_pilot_no_reset(fixture):
    f=fixture;g=f.g;warm(g);start=g.started
    for p in PATHS[:-1]:
        for _ in range(3):g.record(p,1.,retained=False);f.clock.mono+=1
    assert g.forecast()['F_seconds'] is None
    with pytest.raises(ValueError,match='all four'):g.admit()
    with pytest.raises(ValueError,match='forbidden'):g.record(PATHS[0],1.,retained=True)
    for _ in range(3):g.record(PATHS[-1],1.,retained=False);f.clock.mono+=1
    f.clock.mono+=2  # calibration overhead is science too
    g.admit();g.start()
    assert g.started==start and g.forecast()['F_seconds']==119
    assert g.cap==538.5
    f.clock.mono+=5
    assert g.forecast()['F_seconds']==119
    verify(g.out,'FORECAST_SEAL.json')


def test_no_fit_sealed_before_production(fixture):
    g=fixture.g;g.counts={p:10000 for p in PATHS};warm(g)
    for p in PATHS:
        for _ in range(3):g.record(p,1.,retained=False)
    with pytest.raises(R.NoFit):g.admit()
    assert g.status=='NO_FIT' and not g.admitted and g.cap==7200
    verify(g.out,'FORECAST_SEAL.json')


@pytest.mark.parametrize('change',[{'setup_allowance_seconds':1501},{'allocated_gpu_seconds':7201},
    {'previous_gpu_seconds':1},{'hold_renewer_verified':False},{'gpu_count':2},
    {'deadline_epoch':1800010000.}])
def test_assignment_cannot_relax_limits(fixture,change):
    f=fixture;f.assignment.update(change);dump(f.path,f.assignment)
    with pytest.raises(ValueError):R.Gate(f.path,f.g.counts)


@pytest.mark.parametrize('fail',[False,True])
def test_one_load_same_model_complete_grid_and_partial_seal(fixture,monkeypatch,fail):
    f=fixture;a=SimpleNamespace(inputs=f.root/'inputs',out=f.g.out)
    model,tok=object(),object();calls=[];loads=[]
    def load(a,g):
        assert g.started is None
        validate_inputs(a.inputs,g.assignment['input_seal_sha256'])
        loads.append(1);return model,tok
    def reconstruct(ar,tokenizer,texts):
        assert ar is model and tokenizer is tok
        if f.g.admitted:
            verify(f.g.out,'FORECAST_SEAL.json')
            if fail and any(x[0] for x in calls):raise TimeoutError('synthetic cap')
        calls.append((f.g.admitted,len(texts)))
        f.clock.mono+=.1;f.clock.epoch+=.1
        return np.ones((len(texts),5120),dtype=np.float32)
    monkeypatch.setattr(W,'load',load)
    status=W.execute(a,f.g,reconstruct=reconstruct)
    assert len(loads)==1 and status==('INCOMPLETE' if fail else 'COMPLETE')
    s=verify(a.out);assert s['status']=='E26_'+status
    run=read(a.out/'run.json');assert run['checkpoint_load_counts']=={'AR':1} and run['generation_calls']==0
    assert sum(n for admitted,n in calls if not admitted)==4*4*8
    if not fail:
        assert sum(n for admitted,n in calls if admitted)==836
        assert read(a.out/'ids.json')==[r['id'] for r in f.records]
        assert np.load(a.out/'recon.npy').shape==(836,5120)
    else:assert 'recon.npy' not in s['files'] and 'E15/unit-00000.npy' in s['files']


def test_bank_tamper_stops_before_next_reconstructor_call(fixture,monkeypatch):
    f=fixture;a=SimpleNamespace(inputs=f.root/'inputs',out=f.g.out);calls=[]
    monkeypatch.setattr(W,'load',lambda a,g:(object(),object()))
    def reconstruct(ar,tok,texts):
        calls.append(1);f.clock.mono+=.1;f.clock.epoch+=.1
        (a.inputs/'banks/prose_sentiment/candidates.input.jsonl').write_text('tampered')
        return np.ones((len(texts),5120),dtype=np.float32)
    assert W.execute(a,f.g,reconstruct=reconstruct)=='INCOMPLETE'
    assert len(calls)==1


def test_sentiment_omission_is_only_exception(fixture):
    r=validate_inputs(fixture.root/'inputs')
    assert Counter(x['category'] for x in r if x['feature']=='prose_sentiment')==expected_counts('prose_sentiment')
    assert expected_counts('prose_paren')['E15']==4
    assert sum(len(v) for v in unit_plan(r).values())==105


def test_cap_expiry_reserves_retrieval(fixture):
    f=fixture;warm(f.g);f.clock.mono+=7021
    with pytest.raises(TimeoutError):f.g.guard()


def test_full_synthetic_analysis_and_freeze_preserves_all_payloads(fixture):
    from projects.g_agreement.understand.e26 import freeze_existing
    from projects.g_agreement.understand.e26_analyse import evaluate,render
    import shutil
    f=fixture;draft=f.root/'draft';draft.mkdir();receipts=[]
    recon=np.zeros((836,5120),dtype=np.float32);ix={r['id']:i for i,r in enumerate(f.records)}
    templates={}
    for feature in FEATURES:
        folder=draft/feature;folder.mkdir()
        shutil.copyfile(f.root/'inputs/banks'/feature/'candidates.input.jsonl',folder/'candidates.input.jsonl')
        c=rows(folder/'candidates.input.jsonl')
        for i,r in enumerate(c):
            r['value']=i%2
            if r['category']=='continuation':recon[ix[r['id']],r['value']]=1.
            elif r['category']=='description':
                recon[ix[r['id']],r['value']]=.7;recon[ix[r['id']],2]=.7
            else:recon[ix[r['id']],3]=1.
        jsonl(folder/'candidates.DO_NOT_STAGE.jsonl',c)
        items=[{'id':f'{feature}-{i}','value':'A' if i<40 else 'B'} for i in range(80)]
        jsonl(folder/'items.DO_NOT_STAGE.jsonl',items);dump(folder/'ids.json',[r['id'] for r in items])
        h=np.zeros((80,5120),dtype=np.float32);h[:40,0]=1.;h[40:,1]=1.;np.save(folder/'acts44.npy',h)
        dump(folder/'BANK_SEAL.json',{'status':'DRAFT' if feature=='prose_sentiment' else 'FROZEN_COMPLETE_ROW_BANK',
            'files':{p.name:sha(p) for p in folder.iterdir()}})
        receipts.append({'feature':feature,'bank_seal_sha256':sha(folder/'BANK_SEAL.json')})
        templates[feature]={'values':['A','B']}
    dump(draft/'PREPARATION.json',{'authority_commit':'97cfc5dd','reconstructor_calls':0,'rows':receipts,'source_pins':{}})
    final=f.root/'frozen';prep=freeze_existing(draft,final)
    assert prep['launch_allowed'] and not prep['missing']
    for feature in FEATURES:
        assert sha(draft/feature/'candidates.input.jsonl')==sha(final/feature/'candidates.input.jsonl')
        if feature!='prose_sentiment':assert sha(draft/feature/'BANK_SEAL.json')==sha(final/feature/'BANK_SEAL.json')
    result=evaluate(recon,f.records,final,templates)
    assert result['prediction_met'] and result['states_joint_R1_R2']==5
    assert result['rows']['prose_sentiment']['M1']['estimate']==1.
    assert 'Prediction **MET**' in render(result)
