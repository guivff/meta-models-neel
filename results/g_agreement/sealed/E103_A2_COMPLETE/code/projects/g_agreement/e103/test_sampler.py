from pathlib import Path
from types import SimpleNamespace
import contextlib
import sys
import json
import torch
import pytest
from projects.g_agreement.e103 import sampler as W
ROOT=Path(__file__).resolve().parents[3]
RUNTIME=ROOT/'results/g_agreement/understand/late198/runtime.py'

def test_actual_e81_text_sampling_patch_is_serial_and_keeps_decode_path():
    sys.path.insert(0,str(RUNTIME.parent));calls=[]
    class Model:
        generation_config=SimpleNamespace(eos_token_id=9)
        def generate(self,**kwargs):
            calls.append(kwargs)
            return torch.cat([kwargs['input_ids'],torch.tensor([[1,2,9,9]])],dim=1)
    class Backend:
        def token_batch(self,sequences):
            return Model(),SimpleNamespace(pad_token_id=0,eos_token_id=9,decode=lambda x,**k:':'.join(map(str,x))),contextlib.nullcontext(),torch.tensor(sequences)
    b=Backend();W.bind_sampling(b,RUNTIME);result=b.text([[7,8]],max_new_tokens=64)
    assert result==[dict(raw='1:2:9',token_ids=[1,2,9])]
    assert len(calls)==1 and calls[0]['do_sample'] is True
    assert {k:calls[0][k]for k in ['temperature','top_p','top_k','max_new_tokens']}==dict(temperature=1.,top_p=.95,top_k=0,max_new_tokens=64)
    with pytest.raises(ValueError):b.text([[1],[2]],max_new_tokens=64)
    with pytest.raises(ValueError):b.text([[1]],max_new_tokens=128)

def test_real_pilot_is_retained_before_running_mean_no_fit(tmp_path,monkeypatch):
    monkeypatch.setattr(W,'bind_sampling',lambda *a:None)
    class Backend:
        def load_base(self):pass
        def check_tokens(self,items):pass
        def synthetic(self):return [[0]]
        def seed(self,seed):assert seed==20261028
        def text(self,sequences,max_new_tokens):
            assert len(sequences)==1 and max_new_tokens==64
            return [dict(raw='fixture',token_ids=[1])]
    class Clock:
        def call(self,phase,fn,real=False):return fn()
        def admit(self):raise RuntimeError('NO_FIT')
    with pytest.raises(RuntimeError,match='NO_FIT'):W.acquire([dict(id='opaque',prompt='prefix',input_ids=[1],read_position=0)],Backend(),Clock(),tmp_path,RUNTIME)
    rows=list((tmp_path/'jobs').glob('*.json'));assert len(rows)==1
    assert json.loads(rows[0].read_text())['repeat']==0

def test_eight_samples_per_source_one_seed_stream(tmp_path,monkeypatch):
    monkeypatch.setattr(W,'bind_sampling',lambda *a:None);seeds=[];calls=[]
    class Backend:
        def load_base(self):pass
        def check_tokens(self,items):pass
        def synthetic(self):return [[0]]
        def seed(self,seed):seeds.append(seed)
        def text(self,sequences,max_new_tokens):calls.append(sequences);return [dict(raw='fixture',token_ids=[1])]
    class Clock:
        def call(self,phase,fn,real=False):return fn()
        def admit(self):pass
    W.acquire([dict(id=f'opaque{i}',prompt='p',input_ids=[i],read_position=0)for i in [1,2]],Backend(),Clock(),tmp_path,RUNTIME)
    assert seeds==[20261028]and len(calls)==17
    assert len(list((tmp_path/'jobs').glob('*.json')))==16


def test_d4_literal_match_is_exact_and_requires_eight_samples():
    assert W.literal_match('Final token',['xFinal tokeny']+['']*7)
    assert not W.literal_match('Final token',['final token']*8)
    assert not W.literal_match('a b',['a  b']*8)
    with pytest.raises(ValueError):W.literal_match('',['']*8)
    with pytest.raises(ValueError):W.literal_match('x',['x']*7)
