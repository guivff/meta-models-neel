import copy
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from sklearn.metrics import roc_auc_score
from projects.g_agreement.r_bench import remainder_x1 as D
from projects.g_agreement.r_bench import remainder_x1_analyze as A
from projects.g_agreement.r_bench import remainder_x1_collect as C
from projects.g_agreement.r_bench import remainder_x1_launch as G


@pytest.fixture(autouse=True)
def isolate_all_test_writes(tmp_path,monkeypatch):
    import tempfile
    monkeypatch.setattr(tempfile,'tempdir',str(tmp_path))
    # Catch-all: a newly introduced writer cannot silently escape the redirected test root.
    with D.write_guard(roots=[tmp_path]):
        yield


def rows(n=16):return [{'bridge':f'b{i//2}','donor_bridge':f'd{i%4}','natural_lo':float(i+1)} for i in range(n)]


def test_mahalanobis_matches_full_regularized_inverse():
    rng=np.random.default_rng(12);fit=rng.normal(size=(9,27));test=rng.normal(size=(13,27))
    model=D.Mahalanobis(fit);z=test-fit.mean(0);cov=np.cov(fit,rowvar=False)+np.eye(27)*model.ridge
    expected=np.einsum('ij,jk,ik->i',z,np.linalg.inv(cov),z)
    np.testing.assert_allclose(model.score(test),expected,rtol=1e-10,atol=1e-9)


def test_mahalanobis_includes_orthogonal_energy():
    fit=np.array([[0.,0,0],[1,0,0],[2,0,0]])
    model=D.Mahalanobis(fit)
    assert model.score([[1,0,9]])[0]>model.score([[1,0,0]])[0]+1000


@pytest.mark.parametrize('fit',[np.zeros((5,4)),np.array([[0.,np.nan]]*4),np.zeros((2,4))])
def test_detector_rejects_invalid_fit(fit):
    with pytest.raises(ValueError):D.Mahalanobis(fit)


def state_fixture():
    # All distances exactly one; unrelated donors need not share a direction.
    return {'r':{24:{'bridge':np.zeros(3),'answer':np.zeros(3)}},
            'd':{24:{'bridge':np.array([1.,0,0]),'answer':np.array([0.,1,0])}},
            'u':{24:{'bridge':np.array([0.,0,1]),'answer':np.array([0.,0,-1])}}}


def test_matching_keeps_exact_natural_vectors():
    states=state_fixture();before=copy.deepcopy(states);m=D.norm_matching('r','d',['u'],states,24)
    assert m['norm']==m['answer_norm']==m['random_bridge']['norm']==1
    for k in states:
        for p in states[k][24]:np.testing.assert_array_equal(states[k][24][p],before[k][24][p])


@pytest.mark.parametrize('site,scale',[('answer',1.051),('answer',.949),('bridge',0)])
def test_norm_caliper_refuses_mismatch(site,scale):
    states=state_fixture();states['d'][24][site]*=scale
    assert D.norm_matching('r','d',['u'],states,24) is None


def test_random_control_must_also_match():
    s=state_fixture();s['u'][24]['answer']*=2
    assert D.norm_matching('r','d',['u'],s,24) is None


def test_pair_candidates_relation_answer_split_and_seed():
    r={'id':'r','split':'pool','template':'k1','hop2':'capital','bridge':'France','answer':'Paris'}
    bank=[r,dict(r,id='same'),dict(r,id='good',bridge='Italy',answer='Rome'),dict(r,id='badtemplate',template='k2',bridge='Italy',answer='Rome'),dict(r,id='badanswer',bridge='Italy'),dict(r,id='test',split='test',bridge='Italy',answer='Rome')]
    assert D.pair_candidates(r,bank)==['good']
    assert D.pair_candidates(r,list(reversed(bank)))==['good']


def pilot(f24=10,f28=10):
    return [{'recipient':f'p{i}','split':'pilot','layer':L,'natural_lo':1.,'patched_lo':-1. if i<f else 1.} for L,f in [(24,f24),(28,f28)] for i in range(20)]


def test_layer_keeps24_when_quota_projected():
    assert D.select_layer(pilot(10,12),{24:200,28:200})['primary_layer']==24


def test_layer_selects28_only_by_pool_projection():
    assert D.select_layer(pilot(19,10),{24:200,28:200})['primary_layer']==28


def test_layer_underpowered_retains_status():
    x=D.select_layer(pilot(2,3),{24:100,28:100});assert x['underpowered_projection'] and x['primary_layer']==28


def test_layer_rejects_test_outcomes_and_incomplete_pilot():
    p=pilot();p[0]['split']='test'
    with pytest.raises(ValueError):D.select_layer(p,{24:200,28:200})
    with pytest.raises(ValueError):D.select_layer(pilot()[:-1],{24:200,28:200})


def test_downstream_exact_sites_and_coverage():
    assert not D.downstream('jlens',28,28)
    assert D.downstream('jlens',28,24)
    assert not D.downstream('olens',24,24)
    rr=[dict(layer=L,arm=a,reader=r,read_layer=s,status='OK',lo=1.) for L,a,r,s in D.expected_cells()]
    assert D.assert_coverage(rr)['required_cells']==len(D.expected_cells())
    with pytest.raises(ValueError,match='SMOKE FAILED'):D.assert_coverage(rr[:-1])
    rr[0]['lo']=None
    with pytest.raises((ValueError,TypeError)):D.assert_coverage(rr)


def test_dissociation_uses_strict_bounds():
    e=lambda lo,hi:{'wider_ci':[lo,hi]}
    assert A.dissociated(e(.21,.4),e(.21,.4),e(-.1,.09),e(.21,.4))=='DISSOCIATED'
    assert A.dissociated(e(.2,.4),e(.21,.4),e(-.1,.09),e(.21,.4))=='NOT_DISSOCIATED'
    assert A.dissociated(e(.21,.4),e(.21,.4),e(-.1,.1),e(.21,.4))=='NOT_DISSOCIATED'
    assert A.dissociated({'wider_ci':None},e(.21,.4),e(-.1,.09),e(.21,.4))=='UNDEFINED'


def test_paired_control_zero_and_cluster_ci():
    effect=A.paired_effect(rows(),np.zeros(16),n=80)
    assert effect['wider_ci']==[0.,0.] and effect['estimate']==0
    effect=A.paired_effect(rows(),np.repeat([-1.,1.],8),n=80)
    assert effect['wider_ci'][0]<=effect['item_ci'][0] and effect['wider_ci'][1]>=effect['item_ci'][1]


def test_ratio_undefined_denominator_counts_against_claim():
    rr=rows();r=A.ratio(rr,[-1.]*8+[2.]*8,[True]*8+[False]*8,n=80)
    assert r['status']=='UNDEFINED' and r['rho'] is None
    assert r['p']['written']==1. and A.ratio_verdict(r,0,0)=='MIXED'


def test_ratio_positive_exact_known_value_and_bh():
    rr=rows();r=A.ratio(rr,[2.]*8+[1.5]*8,[True]*8+[False]*8,n=200)
    assert r['rho']==.75 and r['wider_ci']['rho']==[.75,.75]
    assert A.ratio_verdict(r,0,1)=='READS WRITTEN'
    assert A.bh([.01,.04,.08])==pytest.approx([.03,.06,.08])


def test_margin_matched_empty_groups_explicit():
    r=A.ratio(rows(),np.ones(16),[True]*8+[False]*8,n=80,margin_matched=True)
    assert r['retained_n']<16 and set(r['retained_terciles'])=={1}


def test_gate_natural_specificity_and_detectable_shift():
    rr=rows();s=np.arange(16.)
    assert A.gate(rr,s,s,n=50)['wider_ci']==[.5,.5]
    assert A.gate(rr,s,s+100,n=50)['auroc']==1. and not A.gate(rr,s,s+100,n=50)['point_gate']


def booking():return {'experiment':'X1','pod':'p1','confirmed_by':'integrator','handoff_line':'X1 assigned','mode':'warm_network_volume','network_volume_id':'v1','assigned_epoch':100.,'deadline_epoch':5500.,'previous_billed_seconds':0.,'segment_id':'s1'}


def test_booking_limits_and_no_offvolume():
    assert G.validate_booking(booking(),'p1',101.)['pod']=='p1'
    for updates in ({'deadline_epoch':5501.},{'previous_billed_seconds':2000.},{'mode':'offvolume'},{'confirmed_by':'self'},{'assigned_epoch':102.}):
        with pytest.raises(ValueError):G.validate_booking(booking()|updates,'p1',101.)
    with pytest.raises(ValueError):G.validate_booking(booking(),'p2',101.)
    with pytest.raises(ValueError):G.validate_booking(booking(),'p1',5300.)


def test_registration_refuses_missing_section(tmp_path,monkeypatch):
    monkeypatch.setattr(D,'ROOT',tmp_path);brief=tmp_path/'projects/g_agreement/BRIEF_R.md';brief.parent.mkdir(parents=True);brief.write_text('No X1 section yet')
    plan={'x':1};D.save(tmp_path/'registration.json',{'experiment':'X1','section':30,'confirmed_by':'integrator','handoff_line':'confirm X1','plan_sha256':D.digest(plan),'brief_sha256':D.sha(brief),'prereg_commit':'a'*40,'pushed_before_compute':True})
    with pytest.raises(ValueError,match='section missing'):G.check_registration(tmp_path,plan)


def test_layer_release_binds_actual_decision(tmp_path):
    p=tmp_path/'decision.json';D.save(p,{'selection_uses_test_outcomes':False});D.save(tmp_path/'layer_release.json',{'decision_sha256':D.sha(p),'pushed_before_test':True,'commit':'a'*40})
    G.check_layer_release(tmp_path,p)
    D.save(p,{'selection_uses_test_outcomes':True})
    with pytest.raises(ValueError):G.check_layer_release(tmp_path,p)


def test_forward_exact_replacement_position_and_hook_cleanup(monkeypatch):
    import torch
    from projects.g_agreement.core import model as M
    class Tiny(torch.nn.Module):
        def __init__(self):
            super().__init__();self.emb=torch.nn.Embedding(20,3);self.layers=torch.nn.ModuleList([torch.nn.Identity() for _ in range(3)])
        def forward(self,input_ids,**kw):
            h=self.emb(input_ids)
            for block in self.layers:h=block(h)
            return SimpleNamespace(logits=h@self.emb.weight.T)
    model=Tiny();target=SimpleNamespace(model=model,tokenizer=SimpleNamespace(pad_token_id=0,eos_token_id=0))
    monkeypatch.setattr(M,'blocks',lambda m:m.layers)
    v=np.array([[7.,8,9],[2.,3,4]],np.float32)
    _,captured=C.forward(target,[[1,2,3],[4,5]], [1,0],[0,2],patch_layer=0,patch_positions=[1,0],values=v)
    np.testing.assert_array_equal(captured[2],v)
    assert all(not b._forward_hooks for b in model.layers)
    with pytest.raises(ValueError):C.forward(target,[[1,2]], [1],[2],patch_layer=0,patch_positions=[1],values=np.ones((1,4)))
    assert all(not b._forward_hooks for b in model.layers)


def test_prepare_real_bank_cpu_only():
    plan=D.prepare();assert len(plan['pilot_ids'])==20 and len(plan['specificity_ids'])==20
    assert not set(plan['pilot_ids'])&set(plan['detector_fit_ids'])
    assert not set(plan['specificity_ids'])&set(plan['detector_fit_ids'])
    assert len(plan['detector_fit_ids'])==160
    assert sum(p['split']=='test' for p in plan['pairs'])==200
    assert sum(bool(p['donor_candidates']) for p in plan['pairs'])==220
    assert plan['primary_layer'] is None and not plan['outcomes_computed']


def test_bootstrap_is_syntax_valid_own_id_first_and_no_secret(monkeypatch):
    import subprocess
    monkeypatch.setattr(G.time,'time',lambda:101.)
    script=G.bootstrap(booking(),'/workspace/remainder/x1/test')
    subprocess.run(['bash','-n'],input=script,text=True,check=True)
    assert script.index('POD ID MISMATCH')<script.index('mkdir')<script.index('nohup')<script.index('X1_VOLUME_CHECK')
    assert 'Cannot renew a segment' in script and 'Segment already armed' in script
    assert 'source /workspace/.env' in script and 'trap ' not in script
    assert "'User-Agent':'Remainder-X1/1.0'" in script


def test_measurement_checksums_and_consolidation(tmp_path):
    with pytest.raises(ValueError):C.verify_measurement(tmp_path)
    p=tmp_path/'bundle';p.mkdir();D.save(p/'rows.json',[{'x':1}]);np.savez(p/'states.npz',x=np.ones(3))
    D.save(p/'complete.json',{'files':{name:D.sha(p/name) for name in ('rows.json','states.npz')}})
    D.save(tmp_path/'model_rows.json',[{'x':1,'state_file':'bundle/states.npz'}]);C.verify_measurement(tmp_path)
    D.save(tmp_path/'model_rows.json',[{'x':2,'state_file':'bundle/states.npz'}])
    with pytest.raises(ValueError,match='Consolidated'):C.verify_measurement(tmp_path)


def test_pull_inventory_is_an_immutable_snapshot(tmp_path,monkeypatch):
    D.save(tmp_path/'booking.json',booking());(tmp_path/D.DATA_REL).mkdir(parents=True);(tmp_path/D.DATA_REL/'output.json').write_text('data')
    (tmp_path/'job.log').write_text('first');m=G.inventory(tmp_path)
    (tmp_path/'job.log').write_text('first second')
    assert D.sha(tmp_path/m['bundle']/'job.log')==m['files']['job.log']['sha256']
    assert m['bundle']=='pull_bundle/s1'
    with pytest.raises(ValueError,match='already exists'):G.inventory(tmp_path)


def test_complete_synthetic_analysis_produces_all_deliverables(tmp_path,monkeypatch):
    # No model calls and no real activation values: complete identity/coverage fixture.
    plan=D.prepare();natural=tmp_path/'natural';natural.mkdir();rng=np.random.default_rng(42)
    for rec in plan['records']:
        arrays={f'L{L}_{site}':rng.normal(size=5).astype(np.float32) for L in (24,28,42,44) for site in ('bridge','answer') if site=='answer' or L in D.LAYERS}
        np.savez(natural/(rec['id']+'.npz'),**arrays)
    D.save(natural/'checksums.json',{p.name:D.sha(p) for p in natural.glob('*.npz')})
    ids=[p['recipient'] for p in plan['pairs'] if p['split']=='test' and p['class_mean_supported_donors']][:8]
    test=tmp_path/'test';test.mkdir();allrows=[];readerrows=[]
    for L in D.LAYERS:
      for arm in D.ARMS:
        folder=test/f'L{L}_{arm}';folder.mkdir();rr=[];arrays={}
        for i,iid in enumerate(ids):
            rec=next(r for r in plan['records'] if r['id']==iid)
            donor_id=next(p['class_mean_supported_donors'][0] for p in plan['pairs'] if p['recipient']==iid)
            donor=next(r for r in plan['records'] if r['id']==donor_id)
            unrelated=D.unrelated(rec,donor,plan['records'])[0]
            row={'recipient':iid,'donor':donor_id,'layer':L,'arm':arm,'status':'OK','lo':-1. if arm in ('bridge_patch','answer_patch') and i<4 else 1.,'bridge':rec['bridge'],'donor_bridge':donor['bridge'],'norm_a':1.,'random_bridge_donor':unrelated,'random_answer_donor':unrelated,'pod':'mock','git_sha':'mock','code_sha':'mock'}
            rr.append(row)
            for site in (28,42,44):
                if site>L:arrays[f'{iid}_L{site}']=rng.normal(size=5).astype(np.float32)
            for reader,sites in D.READERS.items():
                for site in sites:
                    if site>L:readerrows.append({**row,'reader':reader,'read_layer':site,'lo':-.5 if arm=='bridge_patch' else 1.})
        np.savez(folder/'states.npz',**arrays);D.save(folder/'rows.json',rr);D.save(folder/'complete.json',{'files':{name:D.sha(folder/name) for name in ('states.npz','rows.json')}})
    for folder in sorted(test.iterdir()):allrows.extend({**r,'state_file':f'{folder.name}/states.npz'} for r in D.read(folder/'rows.json'))
    D.save(test/'model_rows.json',allrows);C.write_rows(test/'reader_rows.jsonl',readerrows)
    summary=A.analyze(plan,tmp_path,24,tmp_path/'results',n=8)
    assert summary['F']==4 and summary['N']==4 and summary['quota_status']=='UNDERPOWERED'
    assert summary['examples_n']==4
    assert len(D.read(tmp_path/'results/mahalanobis_gate.json')['data'])==47
    assert len(D.read(tmp_path/'results/rho_table.json')['data'])==8
    assert all((tmp_path/'results'/f'{name}.json').is_file() for name in ('flip_table','readback_table','rho_table','mahalanobis_gate','examples','summary'))


def test_measured_pull_reserve_increases_when_link_is_slow(tmp_path,monkeypatch):
    monkeypatch.setattr(G.time,'time',lambda:102.)
    proof={'pod':'p1','bytes':8*1024*1024,'bytes_per_second':1_000_000,'sha256':'a'*64,'measured_epoch':101.}
    D.save(tmp_path/'bandwidth.json',proof)
    assert G.pull_reserve(tmp_path,booking())==585
    D.save(tmp_path/'bandwidth.json',proof|{'bytes_per_second':10_000_000})
    assert G.pull_reserve(tmp_path,booking())==300
    D.save(tmp_path/'bandwidth.json',proof|{'pod':'other'})
    with pytest.raises(ValueError):G.pull_reserve(tmp_path,booking())


def test_bandwidth_remote_script_compiles_and_checks_own_id(tmp_path,monkeypatch):
    import hashlib
    monkeypatch.setattr(G.time,'time',lambda:102.)
    sample=b'x'*(8*1024*1024);calls=[]
    def fake_run(args,**kw):
        calls.append(args)
        if args[0]=='ssh':
            compile(kw['input'],'<remote measure>','exec')
            assert "split(b'\\0')" in kw['input']
            assert kw['input'].index('POD ID MISMATCH')<kw['input'].index('os.urandom')
            return SimpleNamespace(stdout=json.dumps({'bytes':len(sample),'sha256':hashlib.sha256(sample).hexdigest()}))
        if len(calls)==2:Path(args[-1]).write_bytes(sample)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(G.subprocess,'run',fake_run)
    m=G.measure_bandwidth(booking(),'/workspace/remainder/x1/run1','test.example',22,Path('/fake/key'),tmp_path/'bandwidth.json')
    assert m['bytes']==len(sample) and len(calls)==3


def test_reader_completion_requires_every_item_not_just_one_per_arm():
    model=[{'recipient':i,'layer':L,'arm':a,'status':'OK'} for i in ('one','two') for L in D.LAYERS for a in D.ARMS]
    rr=[{**r,'reader':reader,'read_layer':s,'lo':1.} for r in model for reader,sites in D.READERS.items() for s in sites if s>r['layer']]
    assert C.assert_reader_completion(model,rr)['complete_item_cells']==2*len(D.expected_cells())
    assert D.assert_coverage(rr[1:])['required_cells']==len(D.expected_cells())
    with pytest.raises(ValueError,match='item cells'):C.assert_reader_completion(model,rr[1:])


def offvolume_booking():
    return booking()|{'pod':'bufsab55s7gmrq','mode':'warm_off_volume','network_volume_id':None,'pull_all_before_stop':True,'delete_after_queue':True}


def test_offvolume_assignment_is_exact_and_fail_closed():
    b=offvolume_booking()
    assert G.validate_booking(b,b['pod'],101.)==b
    for changes in ({'pod':'unassigned'},{'pull_all_before_stop':False},{'delete_after_queue':False},{'network_volume_id':'v1'}):
        bad=b|changes
        with pytest.raises(ValueError):G.validate_booking(bad,bad['pod'],101.)
    receipt={'pod':b['pod'],'mode':b['mode'],'network_volume_id':None,'http_status':200}
    assert G.validate_storage(b,receipt)==receipt
    for changes in ({'pod':'wrong'},{'network_volume_id':'v1'},{'http_status':403},{'mode':'warm_network_volume'}):
        with pytest.raises(ValueError):G.validate_storage(b,receipt|changes)


def test_offvolume_bootstrap_python_and_shell_syntax(monkeypatch):
    import subprocess,re
    monkeypatch.setattr(G.time,'time',lambda:101.)
    script=G.bootstrap(offvolume_booking(),'/workspace/remainder/x1/test')
    subprocess.run(['bash','-n'],input=script,text=True,check=True)
    for label in ('X1_BOOTSTRAP_DATA','X1_VOLUME_CHECK','X1_RESERVATION'):
        payload=script.split("<<'"+label+"'\n",1)[1].split('\n'+label,1)[0]
        compile(payload,label,'exec')
    assert "body.get('networkVolumeId')==volume" in script
    assert script.index('POD ID MISMATCH')<script.index('mkdir')<script.index('nohup')


def test_capture_caliper_shortfall_stops_before_smoke(tmp_path,monkeypatch):
    monkeypatch.setattr(D,'freeze_pairs',lambda plan,states,layer,split:([{'id':i} for i in range(19 if layer==24 else 20)],[]))
    with pytest.raises(ValueError,match='without relaxing'):
        C.pilot_caliper_audit({'pilot_ids':list(range(D.PILOT_N))}, {}, tmp_path, {'pod':'p'})
    report=D.read(tmp_path/'pilot_shortfall.json')
    assert report['counts']=={'24':19,'28':20} and report['caliper']==.05
    assert report['uses_answer_outcomes'] is False


def test_capture_caliper_complete_can_proceed(tmp_path,monkeypatch):
    monkeypatch.setattr(D,'freeze_pairs',lambda *args:([{'id':i} for i in range(20)],[]))
    assert C.pilot_caliper_audit({'pilot_ids':list(range(D.PILOT_N))}, {}, tmp_path, {})['counts']=={'24':20,'28':20}
    assert not (tmp_path/'pilot_shortfall.json').exists()


def test_staging_20_minute_estimate_and_stale_guard():
    from projects.g_agreement.r_bench import remainder_x1_stage as S
    p=S.estimate(61_300_000_000,100_000_000,600)
    assert p['estimated_seconds']==1100 and p['within_20_minutes']
    rec=p|{'pod':'p','measurement_source':'owner measured download','measured_epoch':100}
    assert S.validate_estimate(rec,'p',101)==p
    with pytest.raises(ValueError):S.validate_estimate(rec,'wrong',101)
    with pytest.raises(ValueError):S.validate_estimate(rec,'p',4000)
    slow=S.estimate(61_300_000_000,50_000_000,600)|{'pod':'p','measurement_source':'owner measured download','measured_epoch':100}
    with pytest.raises(ValueError,match='report before starting'):S.validate_estimate(slow,'p',101)
    for args in ((1,0,60),(1,1,29),(-1,1,60),(1,float('nan'),60)):
        with pytest.raises(ValueError):S.estimate(*args)


def test_staging_assets_are_fixed_four_reader_set():
    from projects.g_agreement.r_bench import remainder_x1_stage as S
    assets=S.requirements()
    assert len(assets)==5 and all(len(a['revision'])==40 for a in assets)
    assert all('main'!=a['revision'] for a in assets)


def test_guard_decoy_unexpected_arm_and_reader_row():
    rr=[dict(layer=L,arm=a,reader=r,read_layer=site,status='OK',lo=1.) for L,a,r,site in D.expected_cells()]
    with pytest.raises(ValueError,match='DECOY_ARM'):D.assert_coverage(rr+[rr[0]|{'arm':'DECOY_ARM'}])
    with pytest.raises(ValueError,match='DECOY_ARM'):C.assert_model_coverage([{'layer':D.LAYERS[0],'arm':'DECOY_ARM','status':'OK'}])
    with pytest.raises(ValueError,match='DECOY_ROW'):C.assert_reader_completion([], [{'recipient':'DECOY_ROW','layer':D.LAYERS[0],'arm':D.ARMS[0],'reader':next(iter(D.READERS)),'read_layer':44}])


def test_writer_paths_derived_and_catchall_names_decoy(tmp_path,monkeypatch):
    plan={'records':[{'id':'bank_item'}],'pairs':[{'split':'pilot'}]}
    monkeypatch.setattr(D,'ARMS',(*D.ARMS,'DECOY_ARM'))
    paths=D.output_paths(tmp_path/'science',plan,8)
    assert any('DECOY_ARM' in str(p) for p in paths)
    with D.write_guard(paths):
        D.save(tmp_path/'science/natural/identity.json',{'ok':True})
        with pytest.raises(ValueError,match='DECOY_PATH'):
            (tmp_path/'DECOY_PATH.json').write_text('forbidden')
        with pytest.raises(ValueError,match='DECOY_ARRAY'):
            np.savez(tmp_path/'DECOY_ARRAY.npz',x=np.zeros(1))
    assert not (tmp_path/'DECOY_PATH.json').exists()


def test_provenance_run_id_once_per_process_and_smoke_kind(monkeypatch):
    first=D.provenance();second=D.provenance()
    assert first['run_id']==second['run_id'] and first['code_sha256']==first['code_sha']
    assert first['run_kind']=='test'
    monkeypatch.setattr(D,'RUN_KIND','smoke');assert D.provenance()['run_kind']=='smoke'
