import json,time
from pathlib import Path
import numpy as np
import pytest
from . import worker as W


def fixture():
    xs=[dict(id=f'x{i:04d}',text='prefix:',ids=[2]*(5+i%2),read_index=4+i%2) for i in range(1008)]
    specs=[dict(id=f'p{i:03d}',reference_id=xs[i]['id'],generator='E76',seed=20261029) for i in range(84)]
    return xs,specs


class Fake:
    def __init__(self):self.model=None;self.readers=None;self.calls=[]
    def sync(self):pass
    def seed(self,s):assert s==20261029
    def load_base(self):self.model=True;self.readers=None;self.calls.append('base')
    def load_oracle(self):self.model=None;self.readers=True;self.calls.append('oracle')
    def load_nla(self):self.calls.append('nla')
    def check_tokens(self,xs):assert len(xs)==1008
    def synthetic(self):return [[2]*5 for _ in range(8)]
    def text64(self,xs):return [dict(raw='one choice',token_ids=[4,5]) for x in xs]
    def warm_capture(self):pass
    def capture(self,xs):
        return {l:np.ones((len(xs),5120),np.float32)*(l+np.arange(len(xs))[:,None]) for l in (42,44)}
    def native(self,r,h):return [[dict(raw='native',text='native',malformed=False)] for x in h]


def test_full_grid_same_pod_pilots_capture_seals_and_no_duplicate_outputs(tmp_path):
    xs,sp=fixture();b=Fake();created=time.time()-10;c=W.RunClock(tmp_path,created+5400,b,created)
    # Test real cap tightening separately; avoid tiny CPU I/O becoming the timing signal.
    c.frozen=True
    assert W.acquire(xs,sp,b,c,tmp_path,dict(experiment='E108'))=='COMPLETE'
    assert b.calls==['base','oracle','nla','base','oracle']
    counts=W.read(tmp_path/'COUNTS.json');assert counts['base_continuations']==1008 and counts['oracle_placebo']==84
    got={'base64':[],'oracle':[],'nla':[]}
    for p in (tmp_path/'jobs').glob('*.json'):
        if p.name=='JOBS_SEAL.json':continue
        for x in W.read(p):got[x.get('reader','base64')].append(x['id'])
    assert len(set(got['base64']))==len(got['base64'])==1008
    for r in ('oracle','nla'):assert len(got[r])==len(set(got[r]))==1092
    assert (tmp_path/'placebo/PLACEBO_SEAL.json').exists() and (tmp_path/'capture/CAPTURE_SEAL.json').exists()
    assert all(x['includes_staging'] for x in c.setup)


def test_e76_norms_native_layers_deterministic_and_different_item_refs():
    xs,sp=fixture();a={l:np.ones((1008,5120),np.float32)*l for l in (42,44)}
    h,receipt=W.make_placebos(xs,sp,a);again,_=W.make_placebos(xs,sp,a)
    for l in a:
        assert np.array_equal(h[l],again[l])
        assert np.allclose(np.linalg.norm(h[l].astype(float),axis=1),np.linalg.norm(a[l][:84].astype(float),axis=1),rtol=1e-6)
    assert not np.array_equal(h[42],h[44]) and receipt['seed']==20261029


def test_measured_cap_freezes_original_clock_and_unknown_or_over_cap_stops(tmp_path,monkeypatch):
    monkeypatch.setattr(W.time,'time',lambda:1000.)
    c=W.RunClock(tmp_path,6300.,Fake(),900.);c.setup=[dict(seconds=100.)]
    left=dict(base64=10,oracle_native=10,nla_native=10)
    with pytest.raises(ValueError,match='real timing pilots'):c.forecast_all(left,2)
    c.observed=dict(base64=[1.],oracle_native=[2.],nla_native=[3.]);c.forecast_all(left,2)
    assert c.end==1335. and W.read(tmp_path/'CAP_ADMISSION.json')['production_cap_seconds']==435.
    left['nla_native']=1000
    with pytest.raises(W.NoFit):c.forecast_all(left,2)


def test_public_contract_rejects_label_leaks_and_bad_final_positions(tmp_path):
    xs,sp=fixture();raw=[dict(id=x['id'],prompt=x['text'],input_ids=x['ids'],read_position=x['read_index']) for x in xs]
    W.write(tmp_path/'PUBLIC_INPUTS.json',raw);W.write(tmp_path/'PLACEBO_SPECS.json',sp);W.write(tmp_path/'STAGE_REQUEST.json',{})
    sh=W.seal(tmp_path,'INPUT_SEAL.json');assert len(W.load(tmp_path,sh)[0])==1008
    W.write(tmp_path/'LABELS.json',{});
    with pytest.raises(ValueError,match='public-only'):W.load(tmp_path,sh)
    (tmp_path/'LABELS.json').unlink();raw[0]['read_position']=0
    W.write(tmp_path/'PUBLIC_INPUTS.json',raw,replace=True);(tmp_path/'INPUT_SEAL.json').unlink();sh=W.seal(tmp_path,'INPUT_SEAL.json')
    with pytest.raises(ValueError,match='raw final'):W.load(tmp_path,sh)


def test_greedy64_uses_raw_tokens_full_greedy_and_eos_trimming():
    import torch,contextlib
    from .runtime import Runtime108
    class Tok:
        pad_token_id=0;eos_token_id=7
        def decode(self,x,skip_special_tokens=True):return ''.join(str(i) for i in x if i!=7)
    class Model:
        generation_config=type('Config',(),{'eos_token_id':7})()
        def generate(self,**kw):
            assert kw['do_sample'] is False and kw['max_new_tokens']==64 and torch.all(kw['attention_mask']==1)
            return torch.cat([kw['input_ids'],torch.tensor([[4,7,0]]*len(kw['input_ids']))],1)
    b=Runtime108(None);b.token_batch=lambda sequences:(Model(),Tok(),contextlib.nullcontext(),torch.tensor(sequences))
    serial=b.text64([[2,3]])[0];batched=b.text64([[2,3]]*32)
    assert batched==[serial]*32 and serial==dict(raw='4',token_ids=[4,7])


def test_native_load_or_nonfinite_crash_remains_fatal(tmp_path):
    class Bad(Fake):
        def capture(self,xs):return {l:np.full((len(xs),5120),np.nan,np.float32) for l in (42,44)}
    xs,sp=fixture();b=Bad();c=W.RunClock(tmp_path,time.time()+5400,b,time.time())
    with pytest.raises(ValueError,match='finite native'):W.acquire(xs,sp,b,c,tmp_path,dict(experiment='E108'))
    assert not list((tmp_path/'jobs').glob('*.json'))


def test_package_source_creates_missing_receipt_parent(tmp_path,monkeypatch):
    from . import package as P
    root=tmp_path/'root';legacy=root/'results/g_agreement/understand/late198';legacy.mkdir(parents=True)
    (legacy/'runtime.py').write_text('class Runtime: pass\n')
    P.write(legacy/'DEPENDENCIES.json',{'results/g_agreement/understand/late198/runtime.py':P.sha(legacy/'runtime.py')})
    P.write(legacy/'SOURCE_SEAL.json',dict(files={p.name:P.sha(p) for p in legacy.iterdir()}))
    owned=root/'projects/g_agreement/e108';owned.mkdir(parents=True);(owned/'__init__.py').write_text('')
    e76=root/'results/g_agreement/understand/e76';e76.mkdir();(e76/'common76.py').write_text('# fixture\n')
    out=tmp_path/'out';out.mkdir();monkeypatch.setattr(P,'ROOT',root)
    result=P.source(out)
    assert (root/result['source_seal_relative']).is_file() and (out/'source.tar.gz').is_file()
