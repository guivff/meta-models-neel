import time
from types import SimpleNamespace
import numpy as np
import pytest
import specialized as S
from contract import read,write,sha,seal
from worker import Clock

class Tiny:
    def sync(self):pass
    def load_base(self):pass
    def load_oracle(self):pass
    def load_nla(self):pass
    def check_tokens(self,items):pass
    def synthetic(self):return [[1]*4]
    def complete_answer(self,xs,limit):return [dict(token_ids=[x[0]],finish_reason='length' if limit==1 else 'eos') for x in xs]
    def capture_positions(self,x,ps):return {l:np.full((len(ps),5120),l,np.float32) for l in (42,44)}
    def rank_distributions(self,x,h):return {'next_token_logits':np.arange(32,dtype=np.float32),'block44_logit_lens':np.arange(32,dtype=np.float32)}
    def native(self,r,h,sampled=False):return [[dict(raw=str(float(v[0])),text=str(float(v[0])),malformed=False)] for v in h]

def clock(out,b):return Clock(out,time.time()+3600,{},b)

def test_e86_full_filter_and_owner_seal(tmp_path):
    xs=[dict(id=str(i),input_ids=[1]*4,max_new_tokens=limit,prompt='') for i,limit in enumerate([1]*64+[16]*64)]
    b=Tiny();S.filter86(xs,b,clock(tmp_path,b),tmp_path,dict(input_archive_sha256='a'*64))
    assert len(read(tmp_path/'FILTER_OUTPUTS.json'))==128
    assert read(tmp_path/'FILTER_SEAL.json')['input_archive_sha256']=='a'*64
    assert read(tmp_path/'PARITY_16.json')['n']==8
    assert read(tmp_path/'FILTER_SEAL.json')['first_output_utc']!='unknown'


def test_e82_all_positions_and_e86_no_dev_readers(tmp_path):
    xs=[dict(id=str(i),input_ids=[1]*4,prompt='',read_positions=[0,1,2,3],read_position=3) for i in range(16)]
    b=Tiny();capout=tmp_path/'cap82';capout.mkdir();binding=dict(experiment='E82',input_archive_sha256='a'*64)
    root=S.capture_bound(xs,'E82',b,clock(capout,b),capout,binding)
    out=tmp_path/'read82';out.mkdir();S.read_bound(xs,'E82',b,clock(out,b),out,binding,root)
    assert read(out/'COUNTS.json')['positions']==64
    rows=[r for f in (out/'jobs').glob('oracle*') for r in read(f)]
    assert {r['position'] for r in rows}=={0,1,2,3}
    selection=[dict(id=x['id'],split='test' if i<8 else 'dev',reader_allowed=i<8,full_rank_vectors_required=i==0) for i,x in enumerate(xs)]
    capout=tmp_path/'cap86';capout.mkdir();binding=dict(experiment='E86',input_archive_sha256='b'*64,selection_sha256='c'*64)
    root=S.capture_bound(xs,'E86',b,clock(capout,b),capout,binding,selection)
    assert read(root/'INDEX.json')[0]['rank_distributions']
    release=dict(capture_seal_sha256=sha(root/'CAPTURE_SEAL.json'),selection_sha256='c'*64,released_ids=[str(i) for i in range(8)],cpu_gate_receipt_sha256='d'*64,authorized=True)
    out=tmp_path/'read86';out.mkdir();S.read_bound(xs,'E86',b,clock(out,b),out,binding,root,selection,release)
    assert read(out/'COUNTS.json')['positions']==8
    out=tmp_path/'bad';out.mkdir();release['released_ids'].append('8')
    with pytest.raises(ValueError,match='permitted test'):S.read_bound(xs,'E86',b,clock(out,b),out,binding,root,selection,release)


def test_e86_complete_eos_byte_parity():
    import torch
    class Model:
        generation_config=SimpleNamespace(eos_token_id=[9,10])
        def generate(self,input_ids,**kwargs):
            assert kwargs['do_sample'] is False and kwargs['max_new_tokens']==16
            n=len(input_ids);suffix=torch.tensor([[3,9,0,0]]*n)
            return torch.cat([input_ids,suffix],1)
    from contextlib import nullcontext
    b=S.BoundRuntime(None)
    b.token_batch=lambda xs:(Model(),SimpleNamespace(pad_token_id=0,eos_token_id=9),nullcontext(),torch.tensor(xs))
    batch=b.complete_answer([[1,2]]*32,16)
    assert batch[:8]==[b.complete_answer([[1,2]],16)[0] for _ in range(8)]
    assert batch[0]==dict(token_ids=[3],finish_reason='eos')


def test_selection_strict_private_field_rejected():
    with pytest.raises(ValueError,match='allowlist'):
        S.selected86([dict(id='x')],[dict(id='x',split='test',reader_allowed=True,full_rank_vectors_required=False,label=1)])
