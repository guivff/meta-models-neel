import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from projects.g_agreement.understand import cpu,runtime,worker
from projects.g_agreement.understand.analyse import fidelity_ratio,variance_subspace


def test_pca_matches_independent_svd_projection():
    rng=np.random.default_rng(8);x=rng.normal(size=(35,12))+np.arange(12)
    result=cpu.pca(x,4);_,_,v=np.linalg.svd(x-x.mean(0),full_matrices=False)
    assert np.allclose(result['basis'].T@result['basis'],v[:4].T@v[:4],atol=1e-9)
    assert np.allclose(result['mean'],x.mean(0))
    with pytest.raises(ValueError):cpu.image_fraction(np.ones((1,12)),result['basis'])


def test_variance_subspace_95_99_are_smallest_ranks():
    x=np.concatenate([np.diag(np.sqrt([100.,2.,.01])),-np.diag(np.sqrt([100.,2.,.01]))])
    basis,ranks,captured=variance_subspace(x)
    assert ranks=={'0.95':1,'0.99':2}
    assert captured['0.95']>=.95 and captured['0.99']>=.99
    assert cpu.image_fraction(np.array([[1.,0,0]]),basis[:1])[0]==pytest.approx(1)


def test_fidelity_signed_unclipped_fixed_gap():
    r=fidelity_ratio([2.,2.,-2.,-2.],[1,1,0,0],2,n_boot=20)
    assert r['fidelity']==2 and r['ci95']==[2,2]
    r=fidelity_ratio([-2.,-2.,2.,2.],[1,1,0,0],2,n_boot=20)
    assert r['fidelity']==-2
    assert fidelity_ratio([1,-1],[1,0],0,n_boot=20)['status']=='UNDEFINED_REAL_GAP'
    with pytest.raises(ValueError):fidelity_ratio([1,2,3,4],[1,1,0,0],1,[0,0,1,1],n_boot=20)


def test_e7_six_arms_preserve_donor_and_native_self_identity():
    ol=np.array([[1.,0],[2.,0],[3.,0]]);nla=ol+np.array([[0.,1],[0.,2],[0.,3]])
    arms=worker.e7_arms(ol,nla,[{'recipient':0,'donor':1,'random':2}])
    assert set(arms)=={'swap','self','ol_only','nla_only','delta_only','random'}
    assert np.array_equal(arms['self'],arms['nla_only'])
    assert np.array_equal(arms['swap'],[[1.,2.]])
    assert np.array_equal(arms['random'],[[1.,3.]])
    assert np.array_equal(arms['delta_only'],[[0.,1.]])


@pytest.mark.parametrize('reader',['ar','nla'])
def test_resident_decoder_loaded_once_warmup_before_two_science_clocks(tmp_path,monkeypatch,reader):
    events=[];jobs=[]
    assets=tmp_path/'assets.json';assets.write_text('{}')
    for experiment in ['E1','E2']:
        inp=tmp_path/experiment;inp.mkdir();records=[{'id':f'{experiment}:{i}','text':'test '+str(i)} for i in range(24)]
        worker.jsonl(inp/'records.jsonl',records)
        cpu.dump(inp/'INPUT_SEAL.json',{'files':{'records.jsonl':cpu.sha(inp/'records.jsonl')}})
        assignment=tmp_path/(experiment+'.json')
        cpu.dump(assignment,{'preceding_science_gpu_seconds':0 if experiment=='E1' else 400,'input_seal_sha256':cpu.sha(inp/'INPUT_SEAL.json')})
        jobs.append({'experiment':experiment,'reader':reader,'inputs':str(inp),'assets':str(assets),'assignment':str(assignment),'records':'records.jsonl','batch':8,'out':str(tmp_path/(experiment+'out'))})
    class FakeGate:
        def __init__(self,path,experiment):self.assignment=cpu.read(path);self.allocation=400;self.started=None;self.setup_complete=False;self.name=experiment
        def setup_guard(self):pass
        def start(self):
            assert self.setup_complete and events.count('load')==1 and events.count('warmup')==1
            events.append('science:'+self.name);self.started=__import__('time').monotonic()
        def guard(self):pass
    class Tensor:
        def __init__(self,x):self.x=x
        def numpy(self):return self.x
    class Decoder:
        def reconstruct(self,texts,batch):
            if not any(e.startswith('science:') for e in events):events.append('warmup')
            return Tensor(np.zeros((len(texts),5120),np.float32))
    def load(_):events.append('load');return Decoder()
    monkeypatch.setattr(worker,'Gate',FakeGate);monkeypatch.setattr(worker,'decoder_only',load)
    if reader=='ar':
        from projects.g_agreement.blindspot import ar_tests
        from projects.g_agreement.w_claims import ar as adapter
        monkeypatch.setattr(ar_tests,'_assets',lambda *args:{'model':'fixture','ar':'fixture'})
        def arload(*args):events.append('load');return Decoder(),None,None
        monkeypatch.setattr(adapter,'load_reconstructor',arload)
        monkeypatch.setattr(adapter,'reconstruct',lambda model,tok,texts:model.reconstruct(texts,len(texts)))
        for job in jobs:job.update(official=str(tmp_path/'official'),whitener=str(tmp_path/'whitener'))
    plan=tmp_path/'plan.json';cpu.dump(plan,jobs)
    worker.reconstruction_session(SimpleNamespace(plan=plan,out=tmp_path/'session'))
    assert events==['load','warmup','science:E1','science:E2']
    for experiment in ['E1','E2']:
        out=tmp_path/(experiment+'out');cpu.verify(out)
        prov=cpu.read(out/'provenance.json');assert prov['reconstructor_load_count']==1 and prov['science_clock_started_after_setup']
        assert len(cpu.read(out/'WARMED_FORECAST.json')['timed_unit_seconds'])==3
    assert cpu.read(tmp_path/'session/session.json')['reconstructor_load_count']==1
    if reader=='nla':assert cpu.read(tmp_path/'session/decoder-probe/report.json')['AV_loaded'] is False


def assignment_fixture(tmp_path,monkeypatch):
    monkeypatch.setattr(runtime,'ROOT',tmp_path);monkeypatch.setattr(runtime.time,'time',lambda:100.)
    package=tmp_path/'projects/g_agreement/understand';package.mkdir(parents=True);(package/'worker.py').write_text('fixture')
    brief=tmp_path/runtime.BRIEF;brief.parent.mkdir(parents=True);brief.write_text('brief')
    d={'issuer':'integrator','experiment':'E1','gpu_count':1,'pod_id':'fixture','external_hardstop_verified':True,'hold_renewer_verified':True,'brief_sha256':cpu.sha(brief),'brief_registered':True,'brief_pushed':True,'source_files':{'projects/g_agreement/understand/worker.py':cpu.sha(package/'worker.py')},'allocated_gpu_seconds':600,'previous_gpu_seconds':0,'smoke_forecast_seconds':160,'deadline_epoch':1000,'setup_deadline_epoch':500,'forecast_method':'warmed_median_next_3_real_units','setup_allowance_seconds':1000,'provider_created_epoch':1}
    # allocation limit = 1.5*160+360 =600
    return d


@pytest.mark.parametrize('change',[{'previous_gpu_seconds':1},{'allocated_gpu_seconds':601},{'smoke_forecast_seconds':float('nan')},{'forecast_method':'cold'},{'hold_renewer_verified':False}])
def test_admission_rejects_overrun_or_invalid_warmed_evidence(tmp_path,monkeypatch,change):
    d=assignment_fixture(tmp_path,monkeypatch);d.update(change);p=tmp_path/'assignment.json';p.write_text(json.dumps(d))
    with pytest.raises(ValueError):runtime.Gate(p,'E1')


def test_admission_accepts_exact_boundary_and_rejects_changed_source(tmp_path,monkeypatch):
    d=assignment_fixture(tmp_path,monkeypatch);p=tmp_path/'assignment.json';cpu.dump(p,d)
    assert runtime.Gate(p,'E1').allocation==600
    (tmp_path/'projects/g_agreement/understand/worker.py').write_text('changed')
    with pytest.raises(ValueError,match='source pin'):runtime.Gate(p,'E1')


def test_science_clock_is_not_reset_between_experiment_phases(tmp_path,monkeypatch):
    d=assignment_fixture(tmp_path,monkeypatch);p=tmp_path/'assignment.json';cpu.dump(p,d)
    g=runtime.Gate(p,'E1');g.start();first=g.started
    monkeypatch.setattr(runtime.time,'monotonic',lambda:first+10)
    g.start();assert g.started==first


def test_one_process_packed_sequence_and_one_load_each(tmp_path,monkeypatch):
    import time
    from projects.g_agreement.understand import packed
    events=[];assets=tmp_path/'assets.json';assets.write_text('{}');inputs=tmp_path/'inputs';inputs.mkdir();out=tmp_path/'out';out.mkdir()
    for tag in ['e1','e2','e7']:
        p=inputs/tag;p.mkdir();cpu.dump(p/'INPUT_SEAL.json',{'files':{}})
    class G:
        def __init__(self,e):self.experiment=e;self.started=None;self.allocation=1000;self.assignment={};self.starts=0
        def start(self):
            if self.started is None:self.started=time.monotonic();self.first_science_epoch=time.time();self.starts+=1
        def guard(self):pass
    class Tensor:
        def numpy(self):return np.zeros((2,5120))
    class Decoder:
        def reconstruct(self,*args,**kwargs):return Tensor()
    class R:
        def __init__(self):self.gates={e:G(e) for e in ['E1','E2','E7']};self.objects={};self.loads={};self.events=[];self.derived_inputs={};self.completed_science=0.;self.current=None
        def get(self,name):
            if name not in self.objects:self.loads[name]=self.loads.get(name,0)+1;self.objects[name]=Decoder() if name=='decoder' else object()
            return self.objects[name]
        def release(self,name):self.objects.pop(name,None)
    resident=R()
    def phase(a,name,model):
        events.append((resident.current,name));resident.get(model);resident.gates[resident.current].start();a.out.mkdir()
        cpu.dump(a.out/'mock.json',{'phase':name});cpu.seal(a.out,['mock.json'],'SYNTHETIC_PHASE')
    monkeypatch.setattr(worker,'reconstruct',lambda a:phase(a,'reconstruct:'+a.reader,'ar' if a.reader=='ar' else 'decoder'))
    monkeypatch.setattr(worker,'capture',lambda a:phase(a,'capture','target'))
    monkeypatch.setattr(worker,'nla_readouts',lambda a:phase(a,'readouts','nla'))
    monkeypatch.setattr(worker,'score_e7',lambda a:phase(a,'score','nla'))
    def prepare(a):
        a.out.mkdir();cpu.dump(a.out/'provenance.json',{'input_seal_sha256':cpu.sha(a.inputs/'INPUT_SEAL.json')});cpu.dump(a.out/'INPUT_SEAL.json',{'files':{'provenance.json':cpu.sha(a.out/'provenance.json')}})
    monkeypatch.setattr(worker,'prepare_e7_decode',prepare)
    packed.execute(SimpleNamespace(out=out,inputs=inputs,assets=assets,assignments=tmp_path,official=tmp_path,whitener=tmp_path),resident)
    assert events==[('E1','reconstruct:ar'),('E1','reconstruct:nla'),('E2','capture'),('E2','reconstruct:ar'),('E2','reconstruct:nla'),('E7','readouts'),('E7','reconstruct:nla'),('E7','score')]
    assert resident.loads=={'ar':1,'decoder':1,'target':1,'nla':1}
    assert all(g.starts==1 for g in resident.gates.values())
    for tag in ['e1','e2','e7']:cpu.verify(out/tag)
    assert cpu.read(out/'packed.json')['same_process']


def test_e7_solo_rejects_target_and_AR_loads():
    from projects.g_agreement.understand.e7_solo import SoloResidents
    r=SoloResidents.__new__(SoloResidents)
    for name in ['ar','target','unknown']:
        with pytest.raises(ValueError,match='only native42'):r.get(name)


def test_e7_solo_never_executes_E1_E2_and_reuses_two_models(tmp_path,monkeypatch):
    import time
    from projects.g_agreement.understand import e7_solo
    assets=tmp_path/'assets.json';assets.write_text('{}');inputs=tmp_path/'inputs';(inputs/'e7').mkdir(parents=True)
    cpu.dump(inputs/'e7/INPUT_SEAL.json',{'files':{}});out=tmp_path/'out';out.mkdir();events=[]
    class G:
        experiment='E7';allocation=2880;assignment={};started=None
        def start(self):
            if self.started is None:self.started=time.monotonic();self.first_science_epoch=time.time()
        def guard(self):pass
    class Tensor:
        def numpy(self):return np.zeros((2,5120))
    class Decoder:
        def reconstruct(self,*a,**kw):return Tensor()
    class R:
        def __init__(self):self.gates={'E7':G()};self.objects={};self.loads={};self.events=[];self.derived_inputs={};self.completed_science=0.;self.current=None
        def get(self,name):
            assert name in ['decoder','nla']
            if name not in self.objects:self.loads[name]=self.loads.get(name,0)+1;self.objects[name]=Decoder() if name=='decoder' else object()
            return self.objects[name]
        def release(self,name):self.objects.pop(name,None)
    resident=R()
    def phase(a,name,model):
        assert a.inputs==inputs/'e7' or a.inputs==out/'e7/decode-inputs'
        events.append(name);resident.get(model);resident.gates['E7'].start();a.out.mkdir()
        cpu.dump(a.out/'fixture.json',{'phase':name});cpu.seal(a.out,['fixture.json'],'SYNTHETIC')
    monkeypatch.setattr(worker,'nla_readouts',lambda a:phase(a,'readouts','nla'))
    monkeypatch.setattr(worker,'reconstruct',lambda a:phase(a,'decode','decoder'))
    monkeypatch.setattr(worker,'score_e7',lambda a:phase(a,'score','nla'))
    monkeypatch.setattr(worker,'capture',lambda a:pytest.fail('E2 must not run'))
    def prepare(a):
        a.out.mkdir();cpu.dump(a.out/'provenance.json',{'input_seal_sha256':cpu.sha(a.inputs/'INPUT_SEAL.json')});cpu.dump(a.out/'INPUT_SEAL.json',{'files':{'provenance.json':cpu.sha(a.out/'provenance.json')}})
    monkeypatch.setattr(worker,'prepare_e7_decode',prepare)
    e7_solo.execute(SimpleNamespace(out=out,inputs=inputs,assets=assets,assignments=tmp_path,official=None,whitener=None),resident)
    assert events==['readouts','decode','score'] and resident.loads=={'decoder':1,'nla':1}
    assert not (out/'e1').exists() and not (out/'e2').exists()
    cpu.verify(out);cpu.verify(out/'e7')
    assert cpu.read(out/'solo.json')['E1_E2_executed'] is False
