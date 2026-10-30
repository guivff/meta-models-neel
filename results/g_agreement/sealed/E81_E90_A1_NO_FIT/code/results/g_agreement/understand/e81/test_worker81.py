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
    xs=fixture();xs[-1]['max_new_tokens']=128
    with pytest.raises(ValueError):validate(xs)
