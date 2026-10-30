import copy
import pytest
from . import e102,e103
from .common import *

def e102fixture():
    rows=[]
    for group,names in e102.SETS.items():
        for row in names:
            for i in range(84):
                rows.append(dict(id=group+row+str(i),item_id=str(i),reader='oracle',set=group,row=row,original_score=0 if group!='content' else 1,retrained_score=1))
    rows += [dict(id='p'+str(i),item_id=str(i),reader='oracle',set='placebo',row='placebo',original_statement=0,retrained_statement=0) for i in range(500)]
    rows += [dict(id='w'+str(i),item_id=str(i),reader='oracle',set='workspace',row='workspace',family='one' if i%2 else 'two',original_pass=True,retrained_pass=True) for i in range(518)]
    return rows,{'readers':['oracle']}

def test_e102_all_rules_and_paired_intervals():
    rows,inv=e102fixture();r=e102.analyze(rows,inv)['readers']['oracle']
    assert all(r['rules'][k]['status']=='MET' for k in ('R-V1','R-V2','R-V3'))
    assert r['rows']['content']['format_plan']['difference']['CI95']==[0,0]
    assert set(r['workspace_families'])=={'one','two'}
    assert r['sets']['trained']['retrained']['total']==252

def test_e102_placebo_and_workspace_conditions_cannot_be_omitted():
    rows,inv=e102fixture()
    for x in rows:
        if x['set']=='placebo':x['retrained_statement']=1
    assert e102.analyze(rows,inv)['readers']['oracle']['rules']['R-V1']['status']=='NOT MET'
    for x in rows:
        if x['set']=='workspace':x['retrained_pass']=False
    assert e102.analyze(rows,inv)['readers']['oracle']['rules']['R-V3']['status']=='NOT MET'

def test_e102_falsifier_and_missing_not_zero():
    rows,inv=e102fixture()
    for x in rows:
        if x['set']=='trained':x['retrained_score']=0
    assert e102.analyze(rows,inv)['readers']['oracle']['rules']['falsifier']['status']=='MET'
    for x in rows:
        if x['set']=='trained':x['retrained_score']=None
    assert e102.analyze(rows,inv)['readers']['oracle']['rules']['falsifier']['status']=='NOT EVALUABLE'

def e103fixture():
    return [dict(id=f'{wave}{reader}{i}{claim}{kind}',wave=wave,bank='bank',reader=reader,source_item_id=str(i),kind=kind,own=1,mismatched=0)
            for wave in ('one','two') for reader in ('oracle','nla') for i in range(10) for claim in range(2) for kind in ('CONTRADICTED','SUPPORTED')]

def test_e103_wave_identity_and_item_clusters():
    rows=e103fixture();r=e103.analyze(rows)
    assert r['rules']['R-H2']['status']=='MET'
    assert r['pooled']['CONTRADICTED']['items']==20
    assert r['pooled']['CONTRADICTED']['claims']==80
    assert r['pooled']['CONTRADICTED']['difference']['CI95']==[1,1]
    assert len(r['breakdowns']['reader_bank_wave'])==4

def test_e103_pairing_falsifier_and_claim_weighting():
    rows=e103fixture()
    for x in rows:x['mismatched']=x['own']
    assert e103.analyze(rows)['rules']['falsifier']['status']=='MET'
    assert e103.rates(rows)['difference']['CI95']==[0,0]
    # Two items, three claims. Claim rate is 2/3, not mean item rate 1/2.
    xs=[dict(wave='w',bank='b',source_item_id='a',own=1,mismatched=0)]*2+[dict(wave='w',bank='b',source_item_id='b',own=0,mismatched=0)]
    assert e103.rates(xs)['own']['estimate']==pytest.approx(2/3)

def test_e103_missing_codes_and_paired_reproducibility():
    rows=e103fixture()
    for x in rows:x['own']=None
    r=e103.analyze(rows)
    assert r['rules']['R-H2']['status']=='NOT EVALUABLE'
    assert r['pooled']['CONTRADICTED']['own']['missing']==80
    assert e103.rates(e103fixture())==e103.rates(e103fixture())

def test_extensions_source_gate_before_io(monkeypatch):
    for mod in (e102,e103):
        monkeypatch.setattr(mod,'committed',lambda: (_ for _ in ()).throw(ValueError('uncommitted')))
        monkeypatch.setattr(mod,'read',lambda _:pytest.fail('opened before commit'))
        monkeypatch.setattr('sys.argv',['adapter','--spec','never'])
        with pytest.raises(ValueError,match='uncommitted'):mod.main()

def test_normalizer_exact_sealed_fields_and_inventory(tmp_path,monkeypatch):
    from . import common
    from .common import normalized
    monkeypatch.setattr(common,'ROOT',tmp_path)
    def bundle(folder,files,**meta):
        path=tmp_path/folder;path.mkdir()
        for n,v in files.items():write(path/n,v)
        core.seal(path,'SEAL.json',**meta)
        return dict(seal=str(path/'SEAL.json'),sha256=sha(path/'SEAL.json'))
    meta=dict(id='x',row='synthetic')
    inv=bundle('inventory',{'INVENTORY.json':[meta]},experiment='E103',frozen_before_outputs=True)
    source=bundle('source',{'response.json':{'reply':'yes'}})
    data=bundle('data',{'RECORDS.json':[dict(id='x',metadata=meta,measurements={arm+'_response':dict(seal_index=0,member='response.json',keys=['reply']) for arm in ('own','mismatched')})]},experiment='E103',status='COMPLETE',inventory_sha256=inv['sha256'],route_verified=True,redaction_audit_complete=True,source_seals=[source])
    monkeypatch.setattr(common.subprocess,'check_output',lambda *a,**kw:(tmp_path/'inventory/SEAL.json').read_bytes())
    rows,_,_=normalized(dict(inventory=inv,inventory_commit='a'*40,data=data),'E103');assert rows[0]['own_response']=='yes'
    (tmp_path/'source'/'response.json').write_text('{}')
    with pytest.raises(ValueError,match='member mismatch'):normalized(dict(inventory=inv,inventory_commit='a'*40,data=data),'E103')

def test_once_guard_rejects_second_claim(tmp_path):
    s=dict(guard=str(tmp_path/'once'),analysis=str(tmp_path/'result'),output_sha256='synthetic')
    core.claim(s,'synthetic');s['analysis']=str(tmp_path/'again')
    with pytest.raises(FileExistsError):core.claim(s,'synthetic')

def test_e102_full_registered_preparation_and_wrong_adapter():
    rows,inv=e102fixture()
    inv.update(counts={'oracle':{g:{r:84 for r in rs} for g,rs in e102.SETS.items()}},feasibility={'oracle':dict(status='PASS',base_frozen=True,steps=10,greedy_reproductions=3,adapter='olens_s3d_rl600')})
    for x in rows:
        x['split']='test';x['target']='A';x['rung']='L0'
        if x['set']=='workspace':x['frozen_scorer_sha256']='synthetic-frozen-family'
        elif x['set']=='placebo':
            x['property']='any_registered_bookkeeping_value'
            for a in ('original','retrained'):x[a+'_placebo_code']={'statement':False,'evidence':''};x[a+'_text']='nothing'
        else:
            for a in ('original','retrained'):x[a+'_code']=dict(id=x['id'],category='states_value',values=['A'],evidence='a');x[a+'_text']='a'
    assert len(e102.prepare(rows,inv))==2278
    inv['feasibility']['oracle']['adapter']='ar_ptag_pooled'
    with pytest.raises(ValueError,match='reader adapter'):e102.prepare(rows,inv)

def test_e103_preparation_rejects_same_item_and_wrong_cohort():
    x=dict(id='a',wave='one',bank='b',reader='oracle',readout_id='r',claim_id='c',source_item_id='i',mismatch_item_id='j',mismatch_bank='b',mismatch_wave='one',kind='SUPPORTED',original_verdict='SUPPORTED',claim='frozen claim',cohort='faithful',readout_has_contradicted=False,own_response='yes',mismatched_response='no')
    inv=dict(selection_seed=20261028,mismatch_same_bank=True,selection_plan_sha256='frozen')
    y=dict(x,id='b',readout_id='h',kind='CONTRADICTED',original_verdict='CONTRADICTED',cohort='hallucinated',readout_has_contradicted=True)
    assert e103.prepare([x,y],inv)[0]['own']==1
    x['mismatch_item_id']='i'
    with pytest.raises(ValueError,match='different item'):e103.prepare([x],inv)
    x['mismatch_item_id']='j';x['readout_has_contradicted']=True
    with pytest.raises(ValueError,match='faithful'):e103.prepare([x],inv)
