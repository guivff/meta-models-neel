import contextlib
import json
import time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from contract import *
from worker import Clock, NoFit, acquire, initial_work

class TinyRuntime:
    def __init__(self):self.calls=[]
    def sync(self):pass
    def load_base(self):self.calls.append('load_base')
    def load_oracle(self):self.calls.append('load_oracle')
    def load_nla(self):self.calls.append('load_nla')
    def check_tokens(self,items):pass
    def synthetic(self):return [[1]*32]*8
    def text(self,xs):self.calls.append('text');return [dict(raw='synthetic text',token_ids=[2]) for _ in xs]
    def next_token(self,xs):self.calls.append('next_token');return [dict(token_id=3,decoded='x',probability=.6) for _ in xs]
    def warm_capture(self):self.calls.append('warm_capture')
    def capture(self,xs):
        self.calls.append('capture')
        return {l:np.ones((len(xs),5120),np.float32) for l in (42,44)}
    def native(self,reader,h,sampled=False):
        self.calls.append(reader+'_native')
        return [[dict(raw='<explanation>synthetic</explanation>',text='synthetic',malformed=False)
                 for _ in range(8 if sampled else 1)] for _ in h]
    def seed(self,value):self.calls.append('reset_seed')

def fixture(exp):
    arms={'E81':['describe','oracle_wording'],'E86':['honest','lie','role']}.get(exp,['main'])
    items=[dict(id=f'{arm}-{i}',feature='synthetic',arm=arm,split='dev' if i<2 and exp not in ('E81','E83') else 'test',
                text='x',ids=[1,2],read_index=1) for arm in arms for i in range(4)]
    score=[dict(id=f'score-{i}',text='x',ids=[1,2],read_index=1) for i in range(3)] if exp in ('E82','E86') else []
    down=[dict(id='down',text='x',ids=[1,2],read_index=1)] if exp=='E85' else []
    plan=dict(experiment=exp,seed=20261028,bank_seal_sha256='a'*64,owner_contract_sha256='b'*64,
              item_ids=[x['id'] for x in items],score_ids=[x['id'] for x in score],downstream_ids=[x['id'] for x in down],forecast_required=False)
    return plan,items,score,down

def seeds():
    return dict(base_setup=0,oracle_setup=0,nla_setup=0,base_text=0,next_token=0,capture=0,downstream=0,oracle_native=0,nla_native=0)

@pytest.mark.parametrize('exp',['E81','E86','E82','E83','E85','E91','E92'])
def test_all_stages_and_cpu_barriers(tmp_path,exp):
    plan,items,score,down=fixture(exp);validate_plan(plan,items,score,down)
    inp=tmp_path/'in';inp.mkdir();out=tmp_path/'out';out.mkdir()
    if exp=='E83':np.save(inp/'acts44.npy',np.ones((len(items),5120),np.float32))
    b=TinyRuntime();c=Clock(out,time.time()+300,seeds(),b)
    def release(name,ready,allowed,forecast,probe):
        assert not any(x.endswith('_native') for x in b.calls)
        assert ready['stage_seal_sha256']==sha(out/('behaviour' if name=='SELECTION_GO' else 'capture')/'STAGE_SEAL.json')
        b.calls.append(name)
        return allowed
    acquire(inp,plan,items,score,down,b,c,out,dict(experiment=exp),release)
    if exp=='E81':assert b.calls.count('load_base')==1 and 'load_oracle' not in b.calls
    elif exp=='E83':
        assert 'capture' not in b.calls and 'nla_native' not in b.calls
        rows=[x for f in (out/'oracle').glob('[0-9]*.json') for x in read(f)]
        assert len(rows)==8*len(items) and {x['repeat'] for x in rows}==set(range(8))
        assert b.calls.index('reset_seed')>b.calls.index('oracle_native')
    else:
        assert b.calls.index('READERS_GO')<b.calls.index('oracle_native')
        if score:assert b.calls.index('SELECTION_GO')<b.calls.index('capture')
        assert (out/'NLA_TRUNCATION.json').exists()
    assert all('warmup' not in k for k in c.observed)
    for stage in ('behaviour','capture','text','oracle','nla','downstream'):
        if (out/stage).exists():assert (out/stage/'STAGE_SEAL.json').exists()

def test_release_rejects_labels_stale_wrong_stage_and_forecast():
    ready=dict(experiment='E86',pod_id='p',source_seal_sha256='a'*64,input_seal_sha256='b'*64,stage_seal_sha256='c'*64,ready_epoch=1)
    go={k:v for k,v in ready.items() if k!='ready_epoch'}
    go.update(released_ids=['one'],issued_epoch=2,authorized=True,cpu_receipt_sha256='d'*64,probe_seal_sha256='e'*64)
    assert check_release(go,ready,['one'],3,probe=True)==['one']
    for change in ({'label':1},{'stage_seal_sha256':'f'*64},{'issued_epoch':0},{'released_ids':['unknown']}):
        with pytest.raises(ValueError):check_release(go|change,ready,['one'],3,probe=True)
    with pytest.raises(ValueError):check_release(go,ready,['one'],3,forecast_required=True,probe=True)

def test_mean_outlier_and_warmups(tmp_path):
    c=Clock(tmp_path,time.time()+220,seeds(),TinyRuntime())
    c.remaining={'oracle_native':10};c.observed={'oracle_native':[50]+[1]*9}
    c.admit()  # mean5.9*10*1.25 fits; slowest50*10*1.25 would fail.
    c.call('oracle_warmup_discarded',lambda:None)
    assert set(c.observed)=={'oracle_native'}
    c.remaining={'oracle_native':1000}
    with pytest.raises(NoFit):c.admit()

def test_request_caps_not_constants():
    a=dict(experiment='E81',gpu_count=1,cap_seconds=120,prior_seconds=10,pod_created_epoch=1,
           custody_start_epoch=2,absolute_deadline_epoch=122,daily_budget_verified=True,projected_daily_USD=260)
    limits=dict(experiment='E81',cap_seconds=120,cumulative_cap_seconds=130,account_gate_USD=260)
    assert deadline(a,limits,3)==122
    with pytest.raises(ValueError):deadline(a,limits|{'cap_seconds':119},3)
    with pytest.raises(ValueError):deadline(a|{'prior_seconds':11},limits,3)

def test_no_private_public_items():
    plan,items,scores,down=fixture('E81');items[0]['target']='private'
    with pytest.raises(ValueError):validate_plan(plan,items,scores,down)

def test_cpu_truth_and_wrong_belief_classification():
    from cpu_gates import behaviour_decisions
    pred={str(i):dict(token_id=1) for i in range(6)};pred['4']['token_id']=2
    group=dict(id='g',paraphrase_score_ids=['0','1','2'],truth_token_id=1,arm_score_ids=dict(honest='3',lie='4',role='5'))
    d=behaviour_decisions('E86',pred,[group])[0]
    assert d['arms']==dict(honest=True,lie=True,role=False)
    group['truth_token_id']=2
    d=behaviour_decisions('E82',pred,[group])[0]
    assert d['belief_wrong'] and d['stable'] and not d['belief_right']
    pred['2']['token_id']=3
    assert not behaviour_decisions('E82',pred,[group])[0]['stable']

def test_three_way_dev_fit_and_private_grouping():
    from cpu_gates import fit_three_way
    from cpu_banks import build_groups
    x=np.repeat(np.eye(3,dtype=np.float32),6,axis=0);y=np.repeat(np.arange(3),6)
    fit=fit_three_way(x,y,np.eye(3,dtype=np.float32))
    assert fit['test_scores'].argmax(1).tolist()==[0,1,2]
    assert np.allclose(fit['mu'],x.mean(0))
    rows=[dict(id=str(i),content_id=i//3,label=i%3,split='dev' if i<6 else 'test') for i in range(12)]
    groups,test=build_groups('E92',rows,[x['id'] for x in rows])
    assert len(groups)==2 and len(test)==6
    assert set(groups[0]['dev_cluster_ids']).isdisjoint(groups[0]['test_cluster_ids'])

def test_runtime_real_methods_with_tiny_model(monkeypatch):
    import torch
    import sys
    from runtime import Runtime
    sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
    class Tok:
        pad_token_id=0;eos_token_id=5
        def encode(self,text,**kwargs):return [1,2] if text=='x' else [1]
        def decode(self,ids,**kwargs):return 'decoded'
    class Model:
        def __init__(self):self.emb=torch.nn.Embedding(6,4);self.kw=[]
        def get_input_embeddings(self):return self.emb
        def __call__(self,**kw):
            self.kw.append(kw);z=torch.zeros((len(kw['input_ids']),1,6));z[:,:,3]=5
            return SimpleNamespace(logits=z)
        def generate(self,**kw):
            self.kw.append(kw)
            return torch.cat([kw['input_ids'],torch.full((len(kw['input_ids']),2),4)],dim=1)
    b=Runtime(None);b.model=Model();b.tok=Tok()
    assert b.next_token([[1,2]])[0]['token_id']==3
    assert b.model.kw[-1]['logits_to_keep']==1 and not b.model.kw[-1]['use_cache']
    assert b.text([[1,2]])[0]['token_ids']==[4,4]
    assert b.model.kw[-1]['max_new_tokens']==128 and b.model.kw[-1]['do_sample'] is False
    import mats.capture
    def capture(model,seqs,layers,positions,**kwargs):
        assert layers==(42,44) and positions==[[1]]
        return {l:torch.ones((1,1,5120)) for l in layers}
    monkeypatch.setattr(mats.capture,'capture',capture)
    assert b.capture([dict(text='x',ids=[1,2],read_index=1)])[44].shape==(1,5120)
    class Reader:
        def verbalize(self,h,layer,k,sampling,batch):
            assert layer==44 and k==8 and sampling.temperature==1 and sampling.top_p==.95 and sampling.top_k==0 and sampling.max_new_tokens==128
            return [['sample']*8 for _ in h]
    b.readers=SimpleNamespace(oracle=Reader(),native_one=lambda reader,h:[[dict(raw='greedy')] for _ in h])
    assert len(b.native('oracle',np.ones((1,5120)),True)[0])==8
    assert b.native('nla',np.ones((1,5120)))[0][0]['raw']=='greedy'
