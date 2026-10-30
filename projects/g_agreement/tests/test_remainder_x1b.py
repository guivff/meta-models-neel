import copy
from projects.g_agreement.r_bench.remainder_x1b_compare import metrics
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from projects.g_agreement.r_bench import remainder_x1b as D, remainder_x1b_collect as C, remainder_x1b_analyze as A, remainder_x1b_launch as G

@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    import tempfile
    monkeypatch.setattr(tempfile,'tempdir',str(tmp_path))
    with D.write_guard(roots=[tmp_path]):yield


def states():
    return {i:{L:{s:np.array([v,1.]) for s in ('bridge','answer')} for L in D.LAYERS} for i,v in [('r',1.),('d',3.),('good',3.1),('DECOY_DONOR',9.)]}


def test_decile_ties_and_edges():
    cuts=np.arange(1.,10.)
    assert D.decile(1,cuts)==0 and D.decile(1.01,cuts)==1 and D.decile(10,cuts)==9
    assert D.decile(1,[1.]*9)==0


def test_decile_decoy():
    with pytest.raises(ValueError,match='Invalid decile boundaries'):D.decile(1,[1.,2.])


def test_exact_natural_control_and_no_caliper():
    st=states();before=copy.deepcopy(st);cuts=np.arange(1.,10.)
    x=D.match_control('r','d',['good','DECOY_DONOR'],st,24,'bridge',cuts)
    assert x['control']['donor']=='good' and x['real']['ratio']>2
    for i in st:
        for L in st[i]:
            for site in st[i][L]:np.testing.assert_array_equal(st[i][L][site],before[i][L][site])


def test_unmatched_is_not_relaxed():
    x=D.match_control('r','d',['DECOY_DONOR'],states(),24,'bridge',np.arange(1.,10.))
    assert x['control'] is None and x['status']=='UNMATCHED_DECILE'
    assert x['candidates'][0]['donor']=='DECOY_DONOR'


def test_no_class_mean_and_downstream_cells():
    assert 'class_mean' not in D.ARMS
    assert all(site>L for L,arm,reader,site in D.expected_cells())
    assert (28,'bridge_patch','jlens',28) not in D.expected_cells()


def test_extra_arm_and_missing_cell_named():
    rows=[dict(layer=L,arm=a,reader=r,read_layer=s,status='OK',lo=1.) for L,a,r,s in D.expected_cells()]
    D.assert_coverage(rows)
    with pytest.raises(ValueError,match='DECOY_ARM'):D.assert_coverage(rows+[dict(rows[0],arm='DECOY_ARM')])
    missing=rows.pop()
    with pytest.raises(ValueError,match=missing['arm']):D.assert_coverage(rows)


def test_write_decoy_named(tmp_path):
    with D.write_guard([tmp_path/'allowed.json']):
        with pytest.raises(ValueError,match='DECOY_FILE'):(tmp_path/'DECOY_FILE').write_text('x')


def test_adjustment_recovers_known_contrast():
    rng=np.random.default_rng(42);r=rng.uniform(.8,1.2,100);c=rng.uniform(.8,1.2,100);center=np.mean((r+c)/2)
    y=.25+3*(r-c)+2*(r-center)
    assert A.adjusted_values(y,np.zeros(100),r,c).mean()==pytest.approx(.25)


def test_rank_and_overlap_decoys():
    with pytest.raises(ValueError,match='rank deficient'):A.adjusted_values(np.ones(10),np.zeros(10),np.ones(10),np.ones(10))
    with pytest.raises(ValueError,match='lacks ratio overlap'):A.adjusted_values(np.ones(10),np.zeros(10),np.arange(10.),np.arange(20.,30.))


def test_booking_rejects_extra_time_and_wrong_pod():
    b=dict(experiment='X1b-lite',pod='actual',confirmed_by='integrator',handoff_line='dated',mode='warm_network_volume',network_volume_id='v',assigned_epoch=100,deadline_epoch=5500,previous_billed_seconds=0,segment_id='one')
    G.validate_booking(b,'actual',101)
    with pytest.raises(ValueError):G.validate_booking(dict(b,deadline_epoch=5501),'actual',101)
    with pytest.raises(ValueError):G.validate_booking(b,'DECOY_POD',101)


def test_capture_runtime_decoy(monkeypatch):
    from projects.g_agreement.core import config
    r=dict(model_id='DECOY_MODEL',model_revision=config.TARGET_MODEL_SHA,dtype=config.TARGET_DTYPE)
    with pytest.raises(ValueError,match='DECOY_MODEL'):C.verify_reuse_runtime(r)


def test_plan_is_same_frozen_pilot():
    from projects.g_agreement.r_bench import remainder_x1 as old
    p=D.prepare();o=old.prepare()
    assert p['pilot_ids']==o['pilot_ids'] and p['records']==o['records']
    assert all('class_mean_supported_donors' not in x for x in p['pairs'])
    assert p['caliper'] is None


def test_provenance_and_owned_paths(tmp_path):
    p=D.prepare();paths=D.output_paths(tmp_path,p,8);meta=D.provenance()
    assert meta['run_kind']=='test' and len(meta['code_sha256'])==64 and meta['run_id']
    assert all(x.is_relative_to(tmp_path) for x in paths)
    assert not any('class_mean' in str(x) for x in paths)


def test_selected_layer_coverage():
    rows=[dict(layer=24,arm=a,status='OK') for a in D.ARMS]
    C.assert_model_coverage(rows,(24,))
    with pytest.raises(ValueError,match='DECOY_ARM'):C.assert_model_coverage(rows+[dict(layer=24,arm='DECOY_ARM',status='OK')],(24,))


def test_ratio_undefined_and_refit():
    rows=[dict(bridge=str(i//2),donor_bridge=str(i%4),natural_lo=i+1.) for i in range(20)]
    assert A.ratio(rows,np.ones(20),np.ones(20,bool),n=20)['status']=='UNDEFINED'
    x=A.ratio(rows,np.ones(20),[True,False]*10,n=20)
    assert x['rho']==pytest.approx(1.)
    bad=A.ratio(rows,np.ones(20),[True,False]*10,n=20,adjustment=(np.ones(20),np.zeros(20),np.ones(20),np.ones(20)))
    assert bad['status']=='UNDEFINED'

def test_synthetic_tables_no_dissociation(tmp_path):
    plan=D.prepare();natural=tmp_path/'natural';natural.mkdir();rng=np.random.default_rng(42)
    for rec in plan['records']:
        arrays={f'L{L}_{site}':rng.normal(size=5).astype(np.float32) for L in (24,28,42,44) for site in ('bridge','answer') if site=='answer' or L in D.LAYERS}
        np.savez(natural/(rec['id']+'.npz'),**arrays)
    D.save(natural/'checksums.json',{p.name:D.sha(p) for p in natural.glob('*.npz')})
    pairs=[p for p in plan['pairs'] if p['split']=='test'][:12];test=tmp_path/'test';test.mkdir();allrows=[];readerrows=[];bank={r['id']:r for r in plan['records']}
    for arm in D.ARMS:
        folder=test/f'L24_{arm}';folder.mkdir();rr=[];arrays={}
        for i,pair in enumerate(pairs):
            iid=pair['recipient'];did=pair['nominal_donor'];rec=bank[iid];donor=bank[did]
            row={'recipient':iid,'donor':did,'layer':24,'arm':arm,'status':'OK','lo':-1. if arm in ('bridge_patch','answer_patch') and i<6 else 1.,'bridge':rec['bridge'],'donor_bridge':donor['bridge'],'norm_ratio':float(rng.uniform(.9,1.1)),'displacement_ratio':.04,**D.provenance()}
            rr.append(row)
            for site in (28,42,44):arrays[f'{iid}_L{site}']=rng.normal(size=5).astype(np.float32)
            for reader,sites in D.READERS.items():
                for site in sites:
                    if site>24:readerrows.append({**row,'reader':reader,'read_layer':site,'lo':-.5 if arm=='bridge_patch' else 1.})
        np.savez(folder/'states.npz',**arrays);D.save(folder/'rows.json',rr);D.save(folder/'complete.json',{'files':{name:D.sha(folder/name) for name in ('states.npz','rows.json')}})
    for folder in sorted(test.iterdir()):allrows.extend({**r,'state_file':f'{folder.name}/states.npz'} for r in D.read(folder/'rows.json'))
    D.save(test/'model_rows.json',allrows);C.write_rows(test/'reader_rows.jsonl',readerrows)
    result=A.analyze(plan,tmp_path,24,tmp_path/'results',n=12)
    assert result['F']==6 and result['N']==6
    assert len(D.read(tmp_path/'results/rho_table.json')['data'])==len(D.READERS)*4
    for p in (tmp_path/'results').glob('*.json'):
        assert 'DISSOCIATED' not in p.read_text() and 'class_mean' not in p.read_text()
    assert all(r['status']=='DESCRIPTIVE' for r in D.read(tmp_path/'results/flip_table.json')['data'] if r['arm'] in ('answer_patch','random_answer'))


def test_reuse_manifest_decoy_names_file(tmp_path,monkeypatch):
    # The checksum manifest itself passes, but a malicious/changed captured array must be named.
    run=tmp_path/'run';source=run/'reuse_source';natural=source/'natural';natural.mkdir(parents=True)
    f=natural/'DECOY_CAPTURE.npz';f.write_bytes(b'changed')
    m={'files':{'cache/g_agreement/r/remainder/x1/natural/DECOY_CAPTURE.npz':{'bytes':1,'sha256':'0'*64}}}
    D.save(source/'pull_manifest.json',m);out=tmp_path/'out';out.mkdir()
    D.save(out/'capture_reuse.json',{'pulled_manifest_sha256':D.sha(source/'pull_manifest.json')})
    monkeypatch.setattr(D,'OUT',out);monkeypatch.setattr(C,'verify_reuse_runtime',lambda r:None)
    with pytest.raises(ValueError,match='DECOY_CAPTURE'):C.reuse_capture(run,{},tmp_path/'data',{})


def test_pool_deciles_ignore_test_state_decoy():
    plan=D.prepare();rng=np.random.default_rng(0)
    st={r['id']:{L:{site:rng.normal(size=3) for site in ('bridge','answer')} for L in D.LAYERS} for r in plan['records']}
    before=D.fit_deciles(plan,st,24)
    for r in plan['records']:
        if r['split']=='test':st[r['id']][24]['bridge']*=1e8
    assert D.fit_deciles(plan,st,24)==before


def test_bootstrap_syntax_and_owned_id(monkeypatch):
    import subprocess,re
    monkeypatch.setattr(G.time,'time',lambda:101.)
    b=dict(experiment='X1b-lite',pod='pod1',confirmed_by='integrator',handoff_line='dated',mode='warm_network_volume',network_volume_id='v',assigned_epoch=100,deadline_epoch=5500,previous_billed_seconds=0,segment_id='one')
    script=G.bootstrap(b,'/workspace/remainder/x1b/test')
    subprocess.run(['bash','-n'],input=script,text=True,check=True)
    for payload in re.findall(r"<<'([^']+)'\n",script):
        code=script.split("<<'"+payload+"'\n",1)[1].split('\n'+payload,1)[0]
        compile(code,payload,'exec')
    assert script.index('POD ID MISMATCH')<script.index('mkdir')<script.index('nohup')

def test_measure_exact_vectors_and_independent_missing_answer(tmp_path,monkeypatch):
    from projects.g_agreement.core import scoring_lo as LO
    monkeypatch.setattr(LO,'encode',lambda *args:[7])
    st=states();plan={'records':[dict(id='r',bridge='France',answer='Paris',template='capital'),dict(id='d',bridge='Italy',answer='Rome',template='capital')]}
    pair=dict(recipient='r',donor='d',layer=24,norm=2.,answer_norm=2.,random_bridge={'donor':'good','norm':2.1},random_answer=None,matches={'bridge':{'status':'MATCHED'},'answer':{'status':'UNMATCHED_DECILE'}})
    seen=[]
    def forward(target,rows,positions,layers,**kw):
        seen.append(kw.get('values'));return [1.,0.]* (len(rows)//2),{L:np.ones((len(rows),2)) for L in layers}
    monkeypatch.setattr(C,'forward',forward)
    enc={'r':{'ids':[1,2,3],'bridge':0,'answer':2}};meta=D.provenance()
    result=C.measure(SimpleNamespace(tokenizer=object()),plan,st,enc,[pair],tmp_path/'measure','test',lambda:None,meta)
    assert next(r for r in result if r['arm']=='random_answer')['status']=='UNMATCHED_DECILE'
    assert next(r for r in result if r['arm']=='random_bridge')['status']=='OK'
    np.testing.assert_array_equal(seen[0][0],st['d'][24]['bridge'])
    C.verify_measurement(tmp_path/'measure')
    folder=tmp_path/'measure/L24_bridge_patch_00000';p=folder/'states.npz'
    with np.load(p) as x:arrays=dict(x)
    arrays['DECOY_ARRAY']=np.ones(2);np.savez(p,**arrays)
    cert=D.read(folder/'complete.json');cert['files']['states.npz']=D.sha(p);D.save(folder/'complete.json',cert)
    with pytest.raises(ValueError,match='DECOY_ARRAY'):C.verify_measurement(tmp_path/'measure')

@pytest.fixture
def handback(tmp_path,monkeypatch):
    run=tmp_path/'run';run.mkdir();pod='own-pod';now=G.time.time()
    D.save(run/'booking.json',{'pod':pod,'segment_id':'s','deadline_epoch':now+600})
    data=run/D.DATA_REL/'row.json';D.save(data,{'x':1})
    files={str(data.relative_to(run)):{'bytes':data.stat().st_size,'sha256':D.sha(data)}}
    D.save(run/'pull_manifest.json',{'pod':pod,'files':files})
    D.save(run/'mac_receipt.json',{'pod':pod,'files':files,'verified_on':'Mac','manifest_sha256':D.sha(run/'pull_manifest.json')})
    for i,name in enumerate(('watchdog','hardstop')):
        (run/f'{name}.s.pid').write_text(str(100+i))
        (run/f'{name}.s.log').write_text(pod+' armed: credential /workspace/.env RUNPOD_API_KEY (check http 200)')
    original=Path.read_bytes
    monkeypatch.setattr(Path,'read_bytes',lambda p: b'RUNPOD_POD_ID=own-pod\0' if str(p)=='/proc/1/environ' else original(p))
    signals=[];monkeypatch.setattr(G.os,'kill',lambda pid,sig:signals.append((pid,sig)))
    return run,pod,signals


def test_warm_handback_keeps_guards_and_fixed_deadline(handback):
    run,pod,signals=handback
    result=G.warm_handback(pod,run)
    assert result['status']=='HANDOVER_READY' and not result['custody_transferred']
    assert signals==[(100,0),(101,0)]
    assert result['reservation_until_epoch']<=result['deadline_epoch']
    assert 'until=' in (run/'reservation').read_text()


def test_handback_decoy_pod(handback):
    run,pod,_=handback
    with pytest.raises(ValueError,match='DECOY_POD'):G.warm_handback('DECOY_POD',run)
    assert not (run/'reservation').exists()


def test_handback_decoy_unpulled_file(handback):
    run,pod,_=handback;D.save(run/D.DATA_REL/'DECOY_UNPULLED.json',{})
    with pytest.raises(ValueError,match='DECOY_UNPULLED'):G.warm_handback(pod,run)
    assert not (run/'reservation').exists()


def test_handback_decoy_guard(handback):
    run,pod,_=handback;(run/'watchdog.s.log').write_text('DECOY_UNARMED')
    with pytest.raises(ValueError,match='watchdog.s.log'):G.warm_handback(pod,run)
    assert not (run/'reservation').exists()


def test_real_stamp_and_smoke_stamp_are_distinct(monkeypatch):
    monkeypatch.setattr(D,'RUN_KIND','real');real=D.provenance('own-pod')
    monkeypatch.setattr(D,'RUN_KIND','smoke');smoke=D.provenance('own-pod')
    assert real['run_kind']=='real' and smoke['run_kind']=='smoke'
    assert real['run_id'] and len(real['code_sha256'])==64


def test_capture_comparison_metrics_and_decoy():
    x=metrics([1.,0.],[2.,0.],'same_direction')
    assert x=={'cosine':1.,'relative_l2':1.}
    with pytest.raises(ValueError,match='DECOY_VECTOR'):metrics([0.,0.],[1.,0.],'DECOY_VECTOR')
    with pytest.raises(ValueError,match='DECOY_SHAPE'):metrics([1.],[1.,2.],'DECOY_SHAPE')


def test_h100_rejects_reuse_before_any_pod_action(tmp_path):
    with pytest.raises(ValueError,match='rejected phase: reuse'):G.run_phase('DECOY_POD',tmp_path,'reuse',tmp_path/'missing')


def test_capture_comparison_checksums_and_decoy(tmp_path,monkeypatch):
    import json
    from projects.g_agreement.r_bench import remainder_x1b_compare as Q
    old=tmp_path/'old';new=tmp_path/'new';out=tmp_path/'out'
    old.mkdir();new.mkdir();out.mkdir();monkeypatch.setattr(D,'OUT',out)
    ids=[f'item-{i}' for i in range(D.PILOT_N)];files={};checks={};encoded={}
    for iid in ids:
        np.savez(old/(iid+'.npz'),L24_bridge=np.array([1.,0.]),provenance_json=np.array('{}'))
        np.savez(new/(iid+'.npz'),L24_bridge=np.array([2.,0.]),provenance_json=np.array('{}'))
        files['cache/natural/'+iid+'.npz']={'bytes':(old/(iid+'.npz')).stat().st_size,'sha256':D.sha(old/(iid+'.npz'))}
        checks[iid+'.npz']=D.sha(new/(iid+'.npz'));encoded[iid]={'ids':[1,2],'bridge':0,'answer':1}
    manifest=tmp_path/'manifest.json';D.save(manifest,{'files':files})
    D.save(out/'capture_reuse.json',{'pulled_manifest_sha256':D.sha(manifest)})
    D.save(new/'checksums.json',checks)
    for root in (old,new):D.save(root/'encoded.json',encoded)
    plan={'pairs':[{'recipient':iid,'split':'pilot'} for iid in ids]}
    result=Q.compare(old,new,manifest,plan)
    assert len(result['rows'])==D.PILOT_N and result['summary']['L24_bridge']['relative_l2']['median']==1
    assert result['used_for_layer_choice'] is False
    (new/'item-0.npz').write_bytes(b'DECOY_CHANGED_STATE')
    with pytest.raises(ValueError,match='H100 checksum differs: item-0.npz'):Q.compare(old,new,manifest,plan)
