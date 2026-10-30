from pathlib import Path
import pytest
from . import adapter as a, rules
from .test_rules import item


def fixture(tmp,monkeypatch):
    monkeypatch.setattr(a,'GUARD',tmp/'ANALYSIS_ONCE.json')
    monkeypatch.setattr(a,'exploratory_inputs',lambda spec,data:{x['item_id']for x in data['fact_recall'][:35]})
    ep=tmp/'E121Analysis';ep.mkdir();a.core.write(ep/'BINDING.json',dict(synthetic=True))
    a.core.seal(ep,'ANALYSIS_SEAL.json',experiment='E121',status='COMPLETE_ONCE')
    monkeypatch.setattr(a,'E121_ANALYSIS_SHA',a.core.sha(ep/'ANALYSIS_SEAL.json'))
    inv={};private=[];measurements={};source_records={'E109':[],'E123':[]}
    for row,n in rules.ROWS.items():
        inv[row]=[];measurements[row]=[]
        for i in range(n):
            unit=f'{row}-{i}';base=item(unit);inv[row].append(dict(item_id=unit,old_value='A'))
            private.append(dict(item_id=unit,row=row,arm='U',condition='steered',target='B',flipped=True))
            conditions={}
            for cond in rules.CONDITIONS:
                experiment='E123' if cond=='unhooked' else 'E109';ix=1 if experiment=='E123' else 0;layers={}
                for layer in (44,52):
                    identity=dict(item_id=unit,row=row,condition=cond,layer=layer,reader='oracle',judgment_id=f'{unit}-{cond}-{layer}')
                    code=dict(base['conditions'][cond][str(layer)],id=identity['judgment_id'])
                    record=dict(identity=identity,code=code,text='x')
                    index=len(source_records[experiment]);source_records[experiment].append(record)
                    ref=lambda k:dict(seal_index=ix,member='original.json',keys=[index,k])
                    layers[str(layer)]=dict(identity,identity=ref('identity'),code=ref('code'),text=ref('text'))
                conditions[cond]=layers
            measurements[row].append(dict(item_id=unit,conditions=conditions))
    pp=tmp/'PRIVATE.json';a.core.write(pp,private);monkeypatch.setattr(a,'PRIVATE_SHA',a.core.sha(pp))
    ip=tmp/'inventory';ip.mkdir();a.core.write(ip/'INVENTORY.json',inv)
    a.core.seal(ip,'SEAL.json',experiment='E123',status='SOURCE_ONLY_COHORT_BOUND',labels_cpu_only=True,source_e104_private_sha256=a.PRIVATE_SHA)
    sources=[]
    for experiment,records in source_records.items():
        folder=tmp/experiment;folder.mkdir();a.core.write(folder/'original.json',records);a.core.seal(folder,'SEAL.json',experiment=experiment,status='COMPLETE')
        sources.append(dict(seal=str(folder/'SEAL.json'),sha256=a.core.sha(folder/'SEAL.json')))
    output=tmp/'output';output.mkdir();a.core.write(output/'MEASUREMENTS.json',measurements)
    a.core.seal(output,'SEAL.json',experiment='E123',status='COMPLETE',inventory_sha256=a.core.sha(ip/'SEAL.json'),reader='oracle',layers=[44,52],labels_cpu_only=True,route_verified=True,redaction_audit_complete=True,source_seals=sources,source_roles={'E109_steered_random':[0],'E123_unhooked':[1]})
    return dict(e121_analysis_seal=str(ep/'ANALYSIS_SEAL.json'),e121_analysis_sha256=a.E121_ANALYSIS_SHA,inventory_seal=str(ip/'SEAL.json'),inventory_sha256=a.core.sha(ip/'SEAL.json'),e104_private=str(pp),output_seal=str(output/'SEAL.json'),output_sha256=a.core.sha(output/'SEAL.json'),analysis=str(tmp/'analysis'))


def test_complete_synthetic_source_binding_and_no_replay(tmp_path,monkeypatch):
    spec=fixture(tmp_path,monkeypatch)
    seal=a.run(spec,'synthetic-committed');result=a.core.read(seal.parent/'RESULTS.json')
    assert result['rows']['fact_recall']['R_DIS1']=='MET'
    assert result['rows']['language_plan']['AUROC']['n_stale']==50
    post=a.core.read(seal.parent/'POST_HOC_EXPLORATORY_NOTE1.json')
    assert post['false_consensus35']['planned_n']==35
    assert post['label'].startswith('POST HOC')
    with pytest.raises(ValueError,match='once guard'):a.run(spec,'synthetic-committed')


def test_old_target_mismatch_rejected_before_guard(tmp_path,monkeypatch):
    spec=fixture(tmp_path,monkeypatch);p=Path(spec['inventory_seal']);data=a.core.read(p.parent/'INVENTORY.json');data['fact_recall'][0]['old_value']='B';a.core.write(p.parent/'INVENTORY.json',data)
    meta=a.core.read(p);meta.pop('files');a.core.seal(p.parent,p.name,**meta);spec['inventory_sha256']=a.core.sha(p)
    with pytest.raises(ValueError,match='original old value'):a.run(spec,'synthetic-committed')
    assert not a.GUARD.exists()


def test_failed_attempt_keeps_once_guard(tmp_path,monkeypatch):
    spec=fixture(tmp_path,monkeypatch);p=Path(spec['output_seal']);meta=a.core.read(p);meta['layers']=[44,60];meta.pop('files');a.core.seal(p.parent,p.name,**meta);spec['output_sha256']=a.core.sha(p)
    with pytest.raises(ValueError,match='reader/site'):a.run(spec,'synthetic-committed')
    assert a.GUARD.exists() and not (Path(spec['analysis'])/'ANALYSIS_SEAL.json').exists()
    with pytest.raises(ValueError,match='once guard'):a.run(spec,'synthetic-committed')


def test_main_commit_gate_before_spec_or_outcome_io(monkeypatch):
    import sys
    monkeypatch.setattr(sys,'argv',['adapter','--spec','must-not-open'])
    def fail():raise ValueError('uncommitted source')
    monkeypatch.setattr(a,'committed',fail)
    monkeypatch.setattr(a.core,'read',lambda p:pytest.fail('IO before committed gate'))
    with pytest.raises(ValueError,match='uncommitted source'):a.main()


def test_wrong_e121_note1_binding_rejected_before_once_guard(tmp_path,monkeypatch):
    spec=fixture(tmp_path,monkeypatch);spec['e121_analysis_sha256']='changed'
    with pytest.raises(ValueError,match='frozen E121'):a.run(spec,'synthetic-committed')
    assert not a.GUARD.exists()


def test_note1_reuses_e121_source_normalizer_never_its_analysis(tmp_path,monkeypatch):
    actual=a.exploratory_inputs
    spec=fixture(tmp_path,monkeypatch)
    monkeypatch.setattr(a,'exploratory_inputs',actual)
    from projects.g_agreement.e121_analysis import adapter as old
    rows=[dict(item_id=f'fact_recall-{i}',condition=c,reader=r,**{'class':'wrong'if i<35 else'correct'})for i in range(84)for c in ('steered','random')for r in ('oracle','nla')]
    calls=[]
    def normalize(binding):calls.append(binding);return rows
    monkeypatch.setattr(old,'inputs',normalize)
    monkeypatch.setattr(old,'analyze',lambda *args:pytest.fail('E121 analysis replay'))
    seal=a.run(spec,'synthetic-committed')
    assert len(calls)==1
    post=a.core.read(seal.parent/'POST_HOC_EXPLORATORY_NOTE1.json')
    assert post['false_consensus35']['planned_n']==35


@pytest.mark.parametrize('disposition',['UNPARSEABLE','KEPT',None])
def test_null_code_requires_recorded_missing_and_keeps_all_audits(tmp_path,monkeypatch,disposition):
    spec=fixture(tmp_path,monkeypatch);output=Path(spec['output_seal']);meta=a.core.read(output)
    measurements=a.core.read(output.parent/'MEASUREMENTS.json')
    pointer=measurements['fact_recall'][0]['conditions']['unhooked']['44']['code']
    source=Path(meta['source_seals'][pointer['seal_index']]['seal']);records=a.core.read(source.parent/pointer['member'])
    terminal=records[pointer['keys'][0]];terminal['id']=terminal['identity']['judgment_id'];terminal['code']=None
    if disposition is not None:terminal['status']=disposition
    a.core.write(source.parent/pointer['member'],records)
    sm=a.core.read(source);sm.pop('files');a.core.seal(source.parent,source.name,**sm)
    meta['source_seals'][pointer['seal_index']]['sha256']=a.core.sha(source)
    meta.pop('files');a.core.seal(output.parent,output.name,**meta);spec['output_sha256']=a.core.sha(output)
    if disposition!='UNPARSEABLE':
        with pytest.raises((ValueError,KeyError),match='UNPARSEABLE|status'):a.run(spec,'synthetic-committed')
        assert a.GUARD.exists() # failed synthetic claim remains consumed, never reset
        return
    seal=a.run(spec,'synthetic-committed');r=a.core.read(seal.parent/'RESULTS.json')
    assert r['rows']['fact_recall']['AUROC']['n_unhooked']==83
    assert r['rows']['fact_recall']['missing']['unhooked']['missing_44']==1
    assert r['rows']['fact_recall']['missing']['unhooked']['missing_52']==0
    assert r['rows']['fact_recall']['false_positive_rate']['n']==83
    post=a.core.read(seal.parent/'POST_HOC_EXPLORATORY_NOTE1.json')
    assert post['operating_point']['rows']['fact_recall']['unhooked_missing_n']==1
    assert post['operating_point']['rows']['fact_recall']['coverage']['unhooked']['missing_pairs']==1
    assert post['false_consensus35']['missing_n']==0
    assert a.core.read(source.parent/pointer['member'])[pointer['keys'][0]]['code']is None
