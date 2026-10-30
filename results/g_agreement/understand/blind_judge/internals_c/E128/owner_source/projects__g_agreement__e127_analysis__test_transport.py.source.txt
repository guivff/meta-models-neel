from pathlib import Path
import pytest
from . import transport as t
from . import rules as r127
from projects.g_agreement.e128_analysis import rules as r128


def fixture(tmp,monkeypatch,experiment):
    monkeypatch.setattr(t,'CUSTODY',tmp/'canonical')
    inv=[];prior=[];measurements=[];source_records=[[],[]]
    def ptr(obj,key,index):return dict(seal_index=index,member='original.json',keys=[obj,key])
    for i in range(84):
        unit=str(i);item=dict(item_id=unit,old_value='A',new_value='B');inv.append(item)
        for c in ('steered','random'):prior.append(dict(item_id=unit,row='fact_recall',arm='U',condition=c,target='B',flipped=c=='steered'))
        def oracle(condition,layer,dose=None):
            ix=1 if dose==8 else 0;code_id=f'{unit}:{condition}:{layer}:{dose}';value='A'if layer==44 else 'B'
            identity=dict(item_id=unit,row='fact_recall',condition=condition,layer=layer,reader='oracle',dose=dose,judgment_id=code_id)
            code=dict(id=code_id,category='states_value',values=[value],evidence=value)
            k=len(source_records[ix]);source_records[ix].append(dict(identity=identity,code=code,text='A B'))
            return dict(identity=ptr(k,'identity',ix),code=ptr(k,'code',ix),text=ptr(k,'text',ix))
        def behaviour(condition,dose=None):
            identity=dict(item_id=unit,condition=condition,dose=dose,classifier_sha256=t.MATCHER_SHA256,raw_id=f'{unit}:{condition}:{dose}')
            new=(condition=='context_update'and i<60)or(condition=='steered'and i<(50 if dose==2 else 60))
            raw=dict(id=identity['raw_id'],text='London'if new else 'Paris',token_ids=[1],greedy_max_new_tokens=3,pair_logits=[[5,1]])
            k=len(source_records[0]);source_records[0].append(dict(identity=identity,record=raw))
            return dict(identity=ptr(k,'identity',0),record=ptr(k,'record',0))
        m=dict(item_id=unit)
        if experiment=='E127':m['conditions']={c:dict(behaviour=behaviour(c),oracle={str(l):oracle(c,l)for l in (44,52,60)})for c in r127.CONDITIONS}
        else:m['doses']={str(d):{c:dict(behaviour=None if d==8 else behaviour(c,d),oracle={str(l):oracle(c,l,d)for l in (44,52)})for c in ('steered','random')}for d in (2,4,8)}
        measurements.append(m)
    def bundle(name,files,**meta):
        d=tmp/name;d.mkdir()
        for k,v in files.items():t.core.write(d/k,v)
        t.core.seal(d,'SEAL.json',**meta);return d/'SEAL.json'
    pp=tmp/'PRIVATE.json';t.core.write(pp,prior);monkeypatch.setattr(t,'PRIVATE_SHA',t.core.sha(pp))
    cp=bundle('candidates',{'LABELS.PRIVATE.json':[dict(original_base_id=str(i),old_value='Paris',new_value='London')for i in range(84)]},labels_cpu_only=True)
    monkeypatch.setattr(t,'CANDIDATE_SHA',t.core.sha(cp))
    ip=bundle('inventory',{'INVENTORY.json':inv},experiment=experiment,status='SOURCE_ONLY_COHORT_BOUND',labels_cpu_only=True,candidate_sha256=t.core.sha(cp),source_e104_private_sha256=t.PRIVATE_SHA,behaviour_classifier_sha256=t.MATCHER_SHA256)
    sources=[]
    for index,records in enumerate(source_records):
        if not records:continue
        sp=bundle(f'source{index}',{'original.json':records},experiment=experiment if index==0 else 'E109',status='COMPLETE')
        sources.append(dict(seal=str(sp),sha256=t.core.sha(sp)))
    meta=dict(judging_bank=experiment,judging_cap_usd=3,experiment=experiment,status='COMPLETE',inventory_sha256=t.core.sha(ip),rubric_sha256=t.RUBRIC_SHA,route_verified=True,labels_cpu_only=True,redaction_audit_complete=True,behaviour_classifier_sha256=t.MATCHER_SHA256,source_seals=sources)
    meta.update(dict(no_hooks=True,layers=[44,52,60],greedy_answer_max_new_tokens=3)if experiment=='E127'else dict(layers=[44,52],new_doses=[2,4],alpha8_reused_unchanged=True,steer=dict(block=40,positions='eight_before_read',direction='class_mean')))
    op=bundle('output',{'MEASUREMENTS.json':measurements},**meta)
    return dict(candidate_seal=str(cp),candidate_sha256=t.core.sha(cp),inventory_seal=str(ip),inventory_sha256=t.core.sha(ip),e104_private=str(pp),output_seal=str(op),output_sha256=t.core.sha(op),analysis=str(tmp/'analysis'))


@pytest.mark.parametrize('experiment,analyze',[('E127',r127.analyze),('E128',r128.analyze)])
def test_full_source_binding_serialization_and_no_replay(tmp_path,monkeypatch,experiment,analyze):
    spec=fixture(tmp_path,monkeypatch,experiment);seal=t.run(spec,experiment,'synthetic-commit',analyze);result=t.core.read(seal.parent/'RESULTS.json')
    if experiment=='E127':assert result['R_NAT1']=='MET'and result['flipped_n']==60
    else:
        assert result['alpha_min']==2 and result['R_DOSE1']=='MET'
        assert result['doses']['8']['behaviour_missing_n']==84
        assert result['pair_preference_descriptive']['8']['steered']['flipped_n']==84
        assert result['doses']['8']['flipped_n']is None
    assert not (t.CUSTODY/('e128'if experiment=='E127'else'e127')/'ANALYSIS_ONCE.json').exists()
    with pytest.raises(ValueError,match='once guard'):t.run(spec,experiment,'synthetic-commit',analyze)


def test_wrong_cohort_orientation_prevents_claim(tmp_path,monkeypatch):
    spec=fixture(tmp_path,monkeypatch,'E127');p=Path(spec['inventory_seal']);items=t.core.read(p.parent/'INVENTORY.json');items[0]['new_value']='A';items[0]['old_value']='B';t.core.write(p.parent/'INVENTORY.json',items)
    meta=t.core.read(p);meta.pop('files');t.core.seal(p.parent,p.name,**meta);spec['inventory_sha256']=t.core.sha(p)
    with pytest.raises(ValueError,match='orientation'):t.run(spec,'E127','synthetic',r127.analyze)
    assert not (t.CUSTODY/'e127/ANALYSIS_ONCE.json').exists()


def test_wrong_rubric_rejected_without_calls(tmp_path,monkeypatch):
    spec=fixture(tmp_path,monkeypatch,'E128');p=Path(spec['output_seal']);meta=t.core.read(p);meta['rubric_sha256']='changed';meta.pop('files');t.core.seal(p.parent,p.name,**meta);spec['output_sha256']=t.core.sha(p)
    with pytest.raises(ValueError,match='rubric'):t.run(spec,'E128','synthetic',r128.analyze)


@pytest.mark.parametrize('name',['e127_analysis','e128_analysis'])
def test_commit_gate_before_spec_IO(monkeypatch,name):
    import importlib,sys
    adapter=importlib.import_module('projects.g_agreement.'+name+'.adapter')
    monkeypatch.setattr(sys,'argv',['adapter','--spec','not-opened'])
    def fail(here):raise ValueError('uncommitted')
    monkeypatch.setattr(adapter.transport,'committed',fail);monkeypatch.setattr(adapter.transport.core,'read',lambda p:pytest.fail('read before gate'))
    with pytest.raises(ValueError,match='uncommitted'):adapter.main()


def test_bank_ceiling_not_silently_increased(tmp_path,monkeypatch):
    spec=fixture(tmp_path,monkeypatch,'E127');p=Path(spec['output_seal']);meta=t.core.read(p);meta['judging_cap_usd']=4;meta.pop('files');t.core.seal(p.parent,p.name,**meta);spec['output_sha256']=t.core.sha(p)
    with pytest.raises(ValueError,match='bank cap'):t.run(spec,'E127','synthetic',r127.analyze)
    assert not (t.CUSTODY/'e127/ANALYSIS_ONCE.json').exists()


def test_wrong_candidate_packet_prevents_output_opening(tmp_path,monkeypatch):
    spec=fixture(tmp_path,monkeypatch,'E127');spec['candidate_sha256']='changed'
    with pytest.raises(ValueError,match='candidate packet'):t.run(spec,'E127','synthetic',r127.analyze)
    assert not (t.CUSTODY/'e127/ANALYSIS_ONCE.json').exists()


@pytest.mark.parametrize('disposition',['UNPARSEABLE','KEPT',None])
def test_e127_null_terminal_code_is_missing_only_with_recorded_disposition(tmp_path,monkeypatch,disposition):
    spec=fixture(tmp_path,monkeypatch,'E127');output=Path(spec['output_seal'])
    meta=t.core.read(output);measurements=t.core.read(output.parent/'MEASUREMENTS.json')
    pointer=measurements[0]['conditions']['context_update']['oracle']['44']['code']
    source=Path(meta['source_seals'][pointer['seal_index']]['seal']);records=t.core.read(source.parent/pointer['member'])
    terminal=records[pointer['keys'][0]];terminal['id']=terminal['identity']['judgment_id'];terminal['code']=None
    if disposition is not None:terminal['status']=disposition
    t.core.write(source.parent/pointer['member'],records)
    source_meta=t.core.read(source);source_meta.pop('files');t.core.seal(source.parent,source.name,**source_meta)
    meta['source_seals'][pointer['seal_index']]['sha256']=t.core.sha(source)
    meta.pop('files');t.core.seal(output.parent,output.name,**meta);spec['output_sha256']=t.core.sha(output)
    if disposition!='UNPARSEABLE':
        with pytest.raises((ValueError,KeyError),match='UNPARSEABLE|status'):t.run(spec,'E127','synthetic-committed',r127.analyze)
        assert not (t.CUSTODY/'e127/ANALYSIS_ONCE.json').exists()
        return
    seal=t.run(spec,'E127','synthetic-committed',r127.analyze);result=t.core.read(seal.parent/'RESULTS.json')
    assert result['flipped_n']==60 # behaviour selection unchanged
    for value in ('old','new'):
        full=result['all84_descriptive']['context_update']['44'][value]
        assert full['planned_n']==84 and full['n']==83 and full['missing_n']==1
        selected=result['flipped_set_rates']['context_update']['44'][value]
        assert selected['planned_n']==60 and selected['n']==59 and selected['missing_n']==1
    assert result['all84_descriptive']['context_update']['44']['old']['k']==83
    assert result['all84_descriptive']['context_update']['44']['new']['k']==0
    assert result['all84_descriptive']['neutral_prefix']['44']['old']['missing_n']==0
    assert result['all84_descriptive']['context_update']['52']['old']['missing_n']==0
    assert t.core.read(source.parent/pointer['member'])[pointer['keys'][0]]['code']is None
