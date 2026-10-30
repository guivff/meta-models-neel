import copy
import json
import time
from pathlib import Path
import pytest
import worker87 as W
import timing95 as T
import package95 as P
from test_scope95 import fixture
from test_worker87 import Tiny87


def test_profile_exact_placebo_counts_and_short_widths(tmp_path,monkeypatch):
    monkeypatch.setattr(W,'DIM',8)
    items,plan=fixture((1,));items[0]['ids']=[1]*3;items[0]['read_index']=2
    inp=tmp_path/'inputs';inp.mkdir();W.write(inp/'PLAN.json',plan);W.write(inp/'items.json',items)
    out=tmp_path/'out';out.mkdir()
    r=T.measure(inp,items,plan,Tiny87(),out,{},time.time()+3600,200)
    assert r['production_admitted'] is False and r['regenerate_all_readouts']
    assert r['native_phases']['nla:placebo:42:8']['measured_batches']==15
    assert r['native_phases']['oracle:real:56:3']['measured_batches']==1
    assert r['native_phases']['oracle:real:56:8']['measured_batches']==3
    assert r['native_phases']['oracle:real:56:8']['full_batches']==16
    assert r['forecast_seconds']>=325 # staging + retrieval, padded


def test_reused_row_only_profiles_fifteen_nla(tmp_path,monkeypatch):
    monkeypatch.setattr(W,'DIM',8)
    items,plan=fixture((1,));plan['mode']='nla_placebo_only';plan['row_roster'][1]['reuse_e87']=True
    inp=tmp_path/'inputs';inp.mkdir();W.write(inp/'PLAN.json',plan);W.write(inp/'items.json',items)
    out=tmp_path/'out';out.mkdir()
    r=T.measure(inp,items,plan,Tiny87(),out,{},time.time()+3600,0)
    assert set(r['native_phases'])=={'nla:placebo:42:8'}
    assert r['native_phases']['nla:placebo:42:8']['measured_batches']==15
    assert W.read(out/'COUNTS.json')['real_readouts']==0


def test_profile_deadline_still_stops(tmp_path,monkeypatch):
    monkeypatch.setattr(W,'DIM',8);items,plan=fixture((1,))
    with pytest.raises(W.NoFit):T.measure(tmp_path,items,plan,Tiny87(),tmp_path,{},time.time()+1,0)


def base_inputs(tmp_path):
    xs,plan=fixture();rows=[];dirs=[]
    for r in [0,1]:
        items,p=fixture((r,));inp=tmp_path/f'in{r}';inp.mkdir()
        W.write(inp/'PLAN.json',p);W.write(inp/'items.json',items);W.write(inp/'STAGE_REQUEST.json',{'status':'HOLD'})
        W.seal(inp,'INPUT_SEAL.json');dirs.append(inp)
        rows.append(dict(row_index=r,test_count=len(items),reuse_e87=False,item_ids=p['item_ids'],nla_position_counts=[8]*len(items),
            oracle_layers=[20,36,44,56],probe_auroc=.95,nla_placebo_count=15,oracle_placebo_count=15))
    inv=dict(experiment='E95',reduction_step=0,rows=rows)
    index=P.index_for(inv,dict(experiment='E95',reduction_step=0,seed=20261028))
    W.write(tmp_path/'inventory.json',inv);W.write(tmp_path/'index.json',index)
    return dirs


def completed_profiles(scope,tmp_path,monkeypatch):
    monkeypatch.setattr(W,'DIM',8);request=W.read(scope/'REQUEST.json');paths=[]
    for entry in request['shards']:
        row=entry['row'];inp=scope/f'row{row}'/'inputs';items=W.read(inp/'items.json');plan=W.read(inp/'PLAN.json')
        out=tmp_path/f'profile{row}';out.mkdir()
        ass=dict(pod_created_epoch=100,custody_start_epoch=100,gpu_type='H200',image_digest='sha256:'+'a'*64,stack_sha256='b'*64,assets_sha256='c'*64)
        W.write(out/'ASSIGNMENT.json',ass)
        stage=dict(assignment_sha256=W.sha(out/'ASSIGNMENT.json'),pod_created_epoch=100,worker_ready_epoch=300)
        W.write(out/'STAGING_RECEIPT.json',stage)
        bind={k:request[k] for k in ['source_seal_sha256','scope_seal_sha256','inventory_sha256','index_sha256','reduction_step']}
        bind.update(input_seal_sha256=entry['input_seal_sha256'],row_indices=[row],gpu_type='H200',assets_sha256='c'*64,
            hardware=dict(gpu_type='H200',actual_gpu_name='H200',image_digest=ass['image_digest'],stack_sha256='b'*64),
            staging_receipt_sha256=W.sha(out/'STAGING_RECEIPT.json'),synthetic=False)
        T.measure(inp,items,plan,Tiny87(),out,bind,time.time()+3600,200)
        W.seal(out,'OUTPUT_SEAL.json',**bind,status='PROFILE_ONLY');paths.append(out/'MEASURED_PROFILE.json')
    return paths


def test_bound_scope_measured_forecast_and_identity_rejection(tmp_path,monkeypatch):
    dirs=base_inputs(tmp_path);scope=tmp_path/'scope'
    P.prepare(tmp_path/'inventory.json',tmp_path/'index.json',dirs,scope)
    paths=completed_profiles(scope,tmp_path,monkeypatch)
    decision=P.evaluate(scope,paths,120)
    assert decision['status']=='WITHIN_40H_REQUIRES_I3_GO' and not decision['production_admitted']
    assert decision['projected_custody_seconds']==decision['forecast_cap_seconds']+120
    with pytest.raises(ValueError):P.evaluate(scope,paths[:1],0)
    bound=tmp_path/'production';P.bind(scope,paths,bound,120)
    limits=W.read(bound/'row0/inputs/STAGE_REQUEST.json');m=limits['timing95']
    assert limits['status']=='HOLD_I3_GLOBAL_ADMISSION'
    ass={k:m[k] for k in ['gpu_type','image_digest','stack_sha256','assets_sha256','scope_seal_sha256','inventory_sha256','index_sha256']}
    ass.update(measured_profile_sha256=m['profile_sha256'],measured_decision_sha256=m['measured_decision_sha256'],e95_integrator_admission_sha256='e'*64)
    plan=W.read(bound/'row0/inputs/PLAN.json')
    T.validate_production(ass,limits,plan,bound/'row0/inputs',m['source_seal_sha256'])
    ass['gpu_type']='B200'
    with pytest.raises(ValueError,match='measured gpu_type'):T.validate_production(ass,limits,plan,bound/'row0/inputs',m['source_seal_sha256'])
    # Even re-sealing a wrong stack claim cannot override the assigned stack.
    path=paths[0];r=W.read(path);r['hardware']['stack_sha256']='d'*64;W.write(path,r,replace=True)
    s=W.read(path.parent/'OUTPUT_SEAL.json');s['files'][path.name]=W.sha(path);W.write(path.parent/'OUTPUT_SEAL.json',s,replace=True)
    with pytest.raises(ValueError,match='assigned hardware'):P.evaluate(scope,paths,0)


def test_no_unmeasured_reduction(tmp_path):
    dirs=base_inputs(tmp_path)
    inv=W.read(tmp_path/'inventory.json');inv['reduction_step']=1
    idx=P.index_for(inv,W.read(tmp_path/'index.json'));W.write(tmp_path/'inventory.json',inv,replace=True);W.write(tmp_path/'index.json',idx,replace=True)
    with pytest.raises(ValueError,match='start from full'):P.prepare(tmp_path/'inventory.json',tmp_path/'index.json',dirs,tmp_path/'bad')


def inflated_profiles(scope,base,monkeypatch):
    base.mkdir();paths=completed_profiles(scope,base,monkeypatch)
    for path in paths:
        r=W.read(path);events=W.read(path.parent/'PHASE_TIMINGS.json')
        for e in events:
            if e['phase'] in r['native_phases']:e['seconds']=1000.
        for v in r['native_phases'].values():v['mean_seconds']=1000.
        W.write(path.parent/'PHASE_TIMINGS.json',events,replace=True);r['phase_timings_sha256']=W.sha(path.parent/'PHASE_TIMINGS.json')
        r['forecast_seconds']=__import__('math').ceil(1.25*(r['staging_seconds']+r['non_native_seconds']+r['measured_other_seconds']+
            sum(v['full_batches']*v['mean_seconds'] for v in r['native_phases'].values())+60))
        W.write(path,r,replace=True);s=W.read(path.parent/'OUTPUT_SEAL.json')
        for n in s['files']:s['files'][n]=W.sha(path.parent/n)
        W.write(path.parent/'OUTPUT_SEAL.json',s,replace=True)
    return paths


def test_registered_reduction_chain_refreezes_index_and_requires_new_timing(tmp_path,monkeypatch):
    dirs=base_inputs(tmp_path);scope=tmp_path/'scope0'
    P.prepare(tmp_path/'inventory.json',tmp_path/'index.json',dirs,scope)
    for step in [1,2,3]:
        profiles=inflated_profiles(scope,tmp_path/f'measure{step}',monkeypatch)
        decision=P.evaluate(scope,profiles,0);assert decision['status']=='REDUCTION_REQUIRED'
        W.write(scope/'DECISION.json',decision)
        next_scope=tmp_path/f'scope{step}'
        inputs=[scope/f"row{r['row']}"/'inputs' for r in W.read(scope/'REQUEST.json')['shards']]
        P.prepare(scope/'ROW_INVENTORY.json',scope/'JUDGE_INDEX.json',inputs,next_scope,previous=scope/'DECISION.json')
        inv=W.read(next_scope/'ROW_INVENTORY.json');index=W.read(next_scope/'JUDGE_INDEX.json')
        assert inv['reduction_step']==index['reduction_step']==step
        assert all(r['oracle_layers']==[36,44,56] and r['nla_placebo_count']==15 for r in inv['rows'])
        if step>=2:assert all(len(r['item_ids'])<=20 for r in inv['rows'])
        with pytest.raises(ValueError,match='exact source/final scope'):P.evaluate(next_scope,profiles,0)
        scope=next_scope
