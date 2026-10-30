import copy
from pathlib import Path
import pytest
import worker87 as W
import package95 as P
import representative95 as R
from test_timing95 import base_inputs,completed_profiles,inflated_profiles


def scope(tmp_path,short=False,unknown=False):
    dirs=base_inputs(tmp_path)
    if short:
        xs=W.read(dirs[1]/'items.json');xs[1]['ids']=[1]*5;xs[1]['read_index']=4
        W.write(dirs[1]/'items.json',xs,replace=True);(dirs[1]/'INPUT_SEAL.json').unlink();W.seal(dirs[1],'INPUT_SEAL.json')
        inv=W.read(tmp_path/'inventory.json');inv['rows'][1]['nla_position_counts'][1]=5
        W.write(tmp_path/'inventory.json',inv,replace=True)
    if unknown:
        inv=W.read(tmp_path/'inventory.json');inv['rows'][0]['probe_auroc']=None
        W.write(tmp_path/'inventory.json',inv,replace=True)
    out=tmp_path/'scope';P.prepare(tmp_path/'inventory.json',tmp_path/'index.json',dirs,out)
    return out


def test_one_profile_multirow_hold_and_runtime_binding(tmp_path,monkeypatch):
    s=scope(tmp_path);profiles=completed_profiles(s,tmp_path,monkeypatch)[:1]
    with pytest.raises(ValueError,match='all retained rows'):P.evaluate(s,profiles)
    out=tmp_path/'bound';d=R.bind(s,profiles,out,120,shards=1)
    assert d['status']=='WITHIN_40H_REQUIRES_I3_GO' and not d['production_admitted']
    request=W.read(out/'REQUEST.json');assert not request['full_launch_allowed'] and len(request['shards'])==1
    shard=request['shards'][0];inp=Path(shard['input_archive']).parent/'inputs'
    plan=W.read(inp/'PLAN.json');limits=W.read(inp/'STAGE_REQUEST.json');m=limits['timing95']
    assert plan['row_indices']==[0,1] and len(W.read(inp/'items.json'))==47
    assert limits['status']=='HOLD_I3_GLOBAL_ADMISSION'
    a={k:m[k] for k in ['gpu_type','image_digest','stack_sha256','assets_sha256','scope_seal_sha256','inventory_sha256','index_sha256']}
    a.update(measured_profile_set_sha256=m['profile_set_sha256'],measured_decision_sha256=m['measured_decision_sha256'],e95_integrator_admission_sha256='f'*64)
    a.update(pod_created_epoch=100,custody_start_epoch=100)
    R.validate_production(a,limits,plan,inp,m['source_seal_sha256'])
    a['stack_sha256']='e'*64
    with pytest.raises(ValueError,match='assigned'):R.validate_production(a,limits,plan,inp,m['source_seal_sha256'])


def test_unmeasured_width5_never_gets_width8_rate(tmp_path,monkeypatch):
    s=scope(tmp_path,short=True);profiles=completed_profiles(s,tmp_path,monkeypatch)[:1]
    out=tmp_path/'blocked';d=R.bind(s,profiles,out,0,shards=1)
    assert d['status']=='BLOCKED_UNMEASURED_PHASE_WIDTH'
    assert not d['reductions'][-1]['projection_is_complete']
    missing=d['reductions'][-1]['missing_native_phases'];assert 'nla:real:42:5' in missing
    assert not (out/'REQUEST.json').exists()


def test_reductions_use_surviving_phase_rates_and_block_unknown_auroc(tmp_path,monkeypatch):
    s=scope(tmp_path,short=True,unknown=True)
    profiles=inflated_profiles(s,tmp_path/'profile',monkeypatch)[:1]
    d,_=R.plan(s,profiles,100,shards=1)
    assert [x['reduction_step'] for x in d['reductions']]==[0,1,2,3]
    assert all(x['status']=='REDUCTION_REQUIRED' for x in d['reductions'][:3])
    assert d['status']=='BLOCKED_DEV_AUROC_EVIDENCE' and d['reductions'][-1]['unknown_rows']==[0]
    inv=W.read(s/'ROW_INVENTORY.json');reduced,_=R.reduce_inventory(inv,2)
    assert reduced['rows'][0]['item_ids']==inv['rows'][0]['item_ids'][:20]
    assert reduced['rows'][1]['item_ids']==inv['rows'][1]['item_ids'] # only17 available
    assert all(x['oracle_layers']==[36,44,56] for x in reduced['rows'])


def test_prior_custody_counts_toward40h(tmp_path,monkeypatch):
    s=scope(tmp_path);profiles=completed_profiles(s,tmp_path,monkeypatch)[:1]
    d,_=R.plan(s,profiles,R.CEILING-1,shards=1)
    assert d['status']=='REDUCTION_REQUIRED' and d['reduction_step']==3
    assert d['reductions'][-1]['projected_custody_seconds']>R.CEILING


def test_unmeasured_row_prompt_cannot_change_after_scope_seal(tmp_path,monkeypatch):
    s=scope(tmp_path);profiles=completed_profiles(s,tmp_path,monkeypatch)[:1]
    p=s/'row1/inputs/items.json';xs=W.read(p);xs[0]['ids'][0]=999
    W.write(p,xs,replace=True)
    with pytest.raises(ValueError):R.plan(s,profiles,0,shards=1)


def test_ast_allows_admission_only_not_measurement_changes():
    one='def measure():\n return 1\ndef validate_production():\n return 2\n'
    assert R.measurement_ast(one)==R.measurement_ast(one.replace('return 2','return 3'))
    assert R.measurement_ast(one)!=R.measurement_ast(one.replace('return 1','return 3'))


def test_metadata_dependency_is_packaged_and_only_permitted_addition(tmp_path):
    import tarfile
    archive=tmp_path/'source.tar.gz';P.source_archive(archive)
    with tarfile.open(archive) as tar:
        data=tar.extractfile(R.ELIGIBILITY_PATH).read()
    import hashlib
    current=W.read(W.HERE/'DEPENDENCIES.json')
    assert hashlib.sha256(data).hexdigest()==current[R.ELIGIBILITY_PATH]
    assert R.dependency_extension({'reader.py':'a'},{'reader.py':'a',R.ELIGIBILITY_PATH:'b'})=={R.ELIGIBILITY_PATH:'b'}
    with pytest.raises(ValueError):R.dependency_extension({'reader.py':'a'},{'reader.py':'changed',R.ELIGIBILITY_PATH:'b'})
    with pytest.raises(ValueError):R.dependency_extension({'reader.py':'a'},{'reader.py':'a','another.py':'b'})


def test_dev_evidence_uses_sealed_quantitative_pointer(tmp_path):
    inv=dict(rows=[dict(row_index=0,bank='e49',row='r',probe_auroc=None)])
    raw=tmp_path/'raw';raw.mkdir();W.write(raw/'metric.json',dict(dev_auroc=.94));raw_sha=W.seal(raw,'SEAL.json')
    evidence=tmp_path/'evidence';evidence.mkdir()
    W.write(evidence/'DEV_PROBES.json',[dict(row_index=0,bank='e49',row='r',split='dev',source_ref=dict(seal_index=0,member='metric.json',keys=['dev_auroc']))])
    evidence_sha=W.seal(evidence,'SEAL.json',metric='dev_probe_auroc',source_seals=[dict(seal=str(raw/'SEAL.json'),sha256=raw_sha)])
    entry=dict(seal=str(evidence/'SEAL.json'),sha256=evidence_sha)
    R.evidence_values(inv,entry);assert inv['rows'][0]['probe_auroc']==.94
    W.write(raw/'metric.json',dict(dev_auroc=.99),replace=True)
    with pytest.raises(ValueError):R.evidence_values(inv,entry)


def test_section217_maximum_whole_setup_and_work_only_margin(tmp_path,monkeypatch):
    import math
    s=scope(tmp_path);profiles=completed_profiles(s,tmp_path,monkeypatch)
    book=R.rates(s,profiles)
    expected=[]
    for path in profiles:
        profile=W.read(path);events=W.read(path.parent/'PHASE_TIMINGS.json')
        expected.append(profile['staging_seconds']+profile['measured_other_seconds']+
            sum(e['seconds'] for e in events if e['phase'] not in profile['native_phases'] and e['phase'] not in ('capture','placebo_build')))
    assert book['maximum_measured_setup_seconds']==max(expected)
    inv=W.read(s/'ROW_INVENTORY.json');xs,p=R.row_inputs(s,inv['rows'][0],0)
    e=R.estimate(xs,p,book);cost=e['measured_phase_cost_seconds']
    work=sum(cost[k] for k in ('capture','placebo_build','native'))
    assert e['cap_seconds']==math.ceil(max(expected)+60+1.25*work)
    altered=copy.deepcopy(book);altered['maximum_measured_setup_seconds']+=1
    with pytest.raises(ValueError,match='maximum own measured setup'):R.estimate(xs,p,altered)
    missing=copy.deepcopy(book);missing.pop('setup_profiles')
    with pytest.raises(KeyError):R.estimate(xs,p,missing)


def test_registered47_ceiling_requires_exact_gate_and_step3_roster(tmp_path,monkeypatch):
    import timing95 as T
    s=scope(tmp_path);profiles=completed_profiles(s,tmp_path,monkeypatch)
    inv,_=R.reduce_inventory(W.read(s/'ROW_INVENTORY.json'),3)
    proof=copy.deepcopy(R.REOPEN_BINDING);proof['step3_roster_sha256']=R.roster_digest(inv)
    monkeypatch.setattr(R,'REOPEN_BINDING',proof)
    out=tmp_path/'reopened';d=R.bind(s,profiles,out,120,shards=1,reopening=proof)
    assert d['status']=='WITHIN_47H_REQUIRES_I3_GO' and d['ceiling_seconds']==169200
    assert [r['reduction_step'] for r in d['reductions']]==[3]
    request=W.read(out/'REQUEST.json');assert not request['full_launch_allowed']
    shard=request['shards'][0];inp=Path(shard['input_archive']).parent/'inputs'
    plan=W.read(inp/'PLAN.json');limits=W.read(inp/'STAGE_REQUEST.json');m=limits['timing95']
    a={k:m[k] for k in ['gpu_type','image_digest','stack_sha256','assets_sha256','scope_seal_sha256','inventory_sha256','index_sha256']}
    a.update(measured_profile_set_sha256=m['profile_set_sha256'],measured_decision_sha256=m['measured_decision_sha256'],e95_integrator_admission_sha256='f'*64,pod_created_epoch=100,custody_start_epoch=100)
    T.validate_production(a,limits,plan,inp,m['source_seal_sha256']) # actual runtime dispatcher, not only direct helper
    bad=copy.deepcopy(limits);bad['timing95']['ceiling_binding']['ceiling_seconds']=172800
    with pytest.raises(ValueError,match='registered sealed'):T.validate_production(a,bad,plan,inp,m['source_seal_sha256'])
    bad=copy.deepcopy(limits);bad['timing95']['programme_projected_custody_seconds']=169201
    with pytest.raises(ValueError,match='whole programme'):T.validate_production(a,bad,plan,inp,m['source_seal_sha256'])
    monkeypatch.setitem(R.REOPEN_BINDING,'step3_roster_sha256','f'*64)
    with pytest.raises(ValueError,match='unchanged registered step3'):R.plan(s,profiles,120,1,reopening=R.REOPEN_BINDING)


def test_reopen_gate_identity_and_tamper_fail_closed(tmp_path,monkeypatch):
    gate=tmp_path/'gate';gate.mkdir();W.write(gate/'GATE_DECISION.json',dict(status='REOPEN_E95_DEVIATION_2',conditional_ceiling_gpu_hours=47))
    decision_sha=W.sha(gate/'GATE_DECISION.json');seal_sha=W.seal(gate,'GATE_SEAL.json',experiment='E95')
    monkeypatch.setattr(R,'REOPEN_GATE_SEAL_SHA',seal_sha);monkeypatch.setattr(R,'REOPEN_GATE_DECISION_SHA',decision_sha)
    assert R.reopen_binding(gate/'GATE_SEAL.json',seal_sha)==R.REOPEN_BINDING
    with pytest.raises(ValueError,match='registered §220 gate seal'):R.reopen_binding(gate/'GATE_SEAL.json','f'*64)
    W.write(gate/'GATE_DECISION.json',dict(status='KEEP_NOT_RUN',conditional_ceiling_gpu_hours=47),replace=True)
    with pytest.raises(ValueError):R.reopen_binding(gate/'GATE_SEAL.json',seal_sha)
    assert R.registered_ceiling()==144000
