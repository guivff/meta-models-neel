import time
import pytest
from pathlib import Path
from worker81 import *

class Tiny81:
    def __init__(self):self.limits=[];self.loads=0
    def sync(self):pass
    def load_base(self):self.loads+=1
    def check_tokens(self,items):pass
    def synthetic(self):return [[1]*32]*8
    def text(self,sequences,max_new_tokens=128):
        self.limits.append(max_new_tokens)
        return [dict(raw='synthetic',token_ids=[2]) for x in sequences]

def fixture():
    return [dict(id=str(i),input_ids=[1,2],prompt='synthetic',read_position=1,max_new_tokens=128 if i<7376 else 32) for i in range(11064)]

def test_all_three_arms_once_with_exact_generation_limits(tmp_path):
    items=fixture();validate(items);b=Tiny81()
    limits=dict(batch_size=64);c=Clock(tmp_path,time.time()+3600,dict(base_setup=0,base_text128=0,base_text32=0),b)
    acquire(items,b,c,tmp_path,limits)
    records=[x for f in (tmp_path/'jobs').glob('*.json') for x in read(f)]
    assert len(records)==11064 and len({x['id'] for x in records})==11064
    assert Counter(x['max_new_tokens'] for x in records)=={128:7376,32:3688}
    assert b.loads==1 and set(b.limits)=={32,128}
    assert len([x for x in c.events if 'warmup' in x['phase']])==2

def test_private_and_length_changes_fail_closed():
    xs=fixture();xs[0]['arm']='hidden'
    with pytest.raises(ValueError):validate(xs)


def test_full_batches_precede_sparse_longest_bucket():
    xs=fixture()
    xs[0]['input_ids']=[1]*500;xs[1]['input_ids']=[1]*500
    work=jobs(xs,64)
    assert len(work[0][1])==64
    assert all(len(chunk)==64 for _,chunk in work[:3])
    assert sorted(x['id'] for _,chunk in work for x in chunk)==sorted(x['id'] for x in xs)
    assert any(len(chunk)==2 and len(chunk[0]['input_ids'])==500 for _,chunk in work)


def test_profile_three_batches_and_eight_item_parity_per_phase(tmp_path):
    b=Tiny81();c=Clock(tmp_path,time.time()+3600,dict(base_setup=0,base_text128=0,base_text32=0),b)
    acquire(fixture(),b,c,tmp_path,dict(batch_size=64),profile_only=True)
    assert len(list((tmp_path/'jobs').glob('*.json')))==6
    assert not (tmp_path/'COUNTS.json').exists()
    for limit in (128,32):
        proof=read(tmp_path/f'PARITY_{limit}.json')
        assert proof['status']=='PASS' and proof['n']==8 and proof['production_batch_size']==64
        assert len(c.observed['base_text'+str(limit)])==3
    assert read(tmp_path/'MEASURED_PROFILE.json')['full_job_regenerates_every_item']


def test_batch_serial_mismatch_stops_before_output(tmp_path):
    class Bad(Tiny81):
        def text(self,sequences,max_new_tokens=128):
            return [dict(raw='serial' if len(sequences)==1 else 'batch',token_ids=[2]) for _ in sequences]
    b=Bad();c=Clock(tmp_path,time.time()+3600,dict(base_setup=0,base_text128=0,base_text32=0),b)
    with pytest.raises(ValueError,match='differs from serial'):
        acquire(fixture(),b,c,tmp_path,dict(batch_size=64))
    assert read(tmp_path/'PARITY_128.json')['status']=='FAIL'
    assert not list((tmp_path/'jobs').glob('*.json'))


def test_eight_item_runtime_parity_including_early_eos():
    import torch
    from types import SimpleNamespace
    from runtime import Runtime
    class Tok:
        pad_token_id=0;eos_token_id=9
        def decode(self,ids,skip_special_tokens=True):
            return ' '.join(str(x) for x in ids if x not in (0,9))
    class Greedy:
        generation_config=SimpleNamespace(eos_token_id=9)
        def get_input_embeddings(self):return SimpleNamespace(weight=torch.zeros(1))
        def generate(self,**kw):
            assert kw['do_sample'] is False and kw['max_new_tokens'] in (32,128)
            rows=[[int(x[0])]*int(x[0])+[9] for x in kw['input_ids']]
            n=max(map(len,rows))
            return torch.cat([kw['input_ids'],torch.tensor([r+[0]*(n-len(r)) for r in rows])],dim=1)
    b=Runtime(None);b.model=Greedy();b.tok=Tok()
    items=[[i,2] for i in range(1,9)]
    for limit in (32,128):
        assert b.text(items,limit)==[b.text([x],limit)[0] for x in items]
    xs=fixture();xs[-1]['max_new_tokens']=128
    with pytest.raises(ValueError):validate(xs)
