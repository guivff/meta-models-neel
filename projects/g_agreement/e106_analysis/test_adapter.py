import copy, pytest
from . import adapter as a
from . import rules as r

def test_statement_union_not_signed_score():
    assert a.statement(dict(states_any_trained_value=True,evidence='7'),'value 7')==1
    assert a.statement(dict(states_any_trained_value=False,evidence=''),'nothing')==0
    assert a.statement(dict(states_any_trained_value=None,evidence=''),'bad') is None
    with pytest.raises(ValueError):a.statement(dict(states_any_trained_value=True,evidence='absent'),'value 7')

def place(n):return [dict(item_id=str(i),original=int(i<10),intervention=int(i<n)) for i in range(200)]
def test_fixed200_and_original_rate_and_thresholds():
    p=a.placebo(place(40));assert p['original']['statement_rate']==.05 and p['intervention']['statement_rate']==.20
    assert a.placebo(place(60))['intervention']['statement_rate']==.30
    xs=place(40);xs[199]['intervention']=None;p=a.placebo(xs)['intervention'];assert p['statement_rate'] is None and p['rate_bounds']==[.2,.205]
    with pytest.raises(ValueError):a.placebo(xs[:-1])
    with pytest.raises(ValueError):a.placebo(xs[:-1]+[xs[0]])

def fixture():
    rows=[];dis={};di={}
    for reader in ('oracle','nla'):
        dis[reader]={'P':{'status':'COMPLETE'},'T':{'status':'COMPLETE'}}
        for arm in ('P','T'):
            for row in r.TRAIN+r.HELD+(r.CONTENT if arm=='T' else ()):
                for i in range(84):rows.append(dict(reader=reader,arm=arm,row=row,item_id=str(i),original=0,intervention=1))
            if arm=='T':rows.extend(dict(x,reader=reader,arm=arm,row='placebo') for x in place(40))
        di[reader]=dict(gate=dict(status='PASS',steps=10,parity_byte_equal=3,frozen_before_sha256='x',frozen_after_sha256='x',adapter_tensors_changed=1,parity_before_optimizer=True,fresh_production_adapter=True,parity=[dict(expected_sha256='a',actual_sha256='a')]*3,gate_losses=[1.]*10),recipe=dict(rank=16,lr=1e-4,steps=300,batch_size=16,seed=20261029),dev_only=True,equal_replay=True,test_optimizer_items=0,losses=[1.]*299+[.5],oracle_e102_resolution_sha256='resolved')
    return rows,dis,di

def test_full_two_reader_rules_and_falsifier():
    rows,ds,di=fixture();out=a.analyze(rows,ds,di)
    for x in out['readers'].values():assert x['T']['rules']['R_FX1']=='MET' and x['T']['rules']['R_FX2']=='MET' and x['T']['rules']['falsifier']=='NOT MET'
    for x in rows:
        if x['row']=='placebo':x['intervention']=1
    assert a.analyze(rows,ds,di)['readers']['nla']['T']['rules']['falsifier']=='MET'

def test_failed_training_arm_keeps_prompt_arm():
    rows,ds,di=fixture()
    for reader in ds:ds[reader]['T']=dict(status='NOT RUN (feasibility)',reason='gate failed')
    rows=[x for x in rows if x['arm']=='P'];out=a.analyze(rows,ds,{})
    assert out['readers']['nla']['P']['R-FX0']['status']=='DESCRIPTIVE'
    assert out['readers']['nla']['T']['status']=='NOT RUN (feasibility)'

@pytest.mark.parametrize('change',[lambda d:d['gate'].update(parity_before_optimizer=False),lambda d:d['gate'].update(frozen_after_sha256='changed'),lambda d:d['recipe'].update(steps=299),lambda d:d.update(test_optimizer_items=1),lambda d:d.update(losses=[1.]*299)])
def test_gate_recipe_leakage_fail_closed(change):
    rows,ds,di=fixture();change(di['nla'])
    with pytest.raises(ValueError):a.analyze(rows,ds,di)

def test_source_tampering_and_once_guard(tmp_path):
    a.core.write(tmp_path/'raw.json',{'x':1});a.core.seal(tmp_path,'SEAL.json');h=a.core.sha(tmp_path/'SEAL.json');a.core.verify(tmp_path/'SEAL.json',h)
    a.core.write(tmp_path/'raw.json',{'x':2})
    with pytest.raises(ValueError):a.core.verify(tmp_path/'SEAL.json',h)
    s=dict(analysis=str(tmp_path/'out'),guard=str(tmp_path/'guard'),output_sha256='synthetic')
    a.core.claim(s,'synthetic')
    with pytest.raises((ValueError,FileExistsError)):a.core.claim(s,'synthetic')
