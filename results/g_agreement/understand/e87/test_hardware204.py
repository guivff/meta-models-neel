import sys
from pathlib import Path
import numpy as np
import pytest
import worker87
import hardware204 as H
sys.path.insert(0,str(worker87.ROOT))


def fixture(mode='readers'):
    a=dict(gpu_type='B200',actual_gpu_name='B200',pod_id='synthetic',image_digest='sha256:'+'a'*64,
        stack_sha256='b'*64,source_seal_sha256='c'*64,hardware_authority=H.AUTHORITY,analysis_unit_gpu_types={'0':'B200'})
    readers=['text'] if mode=='text' else ['oracle','nla']
    items=[dict(id=str(i),ids=[1,2],max_new_tokens=32,h200={r:{'raw':'old'} for r in readers}) for i in range(3)]
    ref=dict(status='VERIFIED_H200_REFERENCE',gpu_type='H200',source_output_seals=['d'*64],mode=mode,
        h200_readout_sha256={str(i):'e'*64 for i in range(3)})
    return a,items,ref


class Backend:
    def load_base(self):pass
    def load_oracle(self):self.state='oracle'
    def load_nla(self):self.state='nla'
    def capture_all(self,item,layers):
        assert self.state=='oracle'
        return {l:np.ones((len(item['ids']),5120)) for l in layers}
    def sweep(self,reader,h,l):
        assert self.state==reader
        return [{'raw':'new','finite':1.0}]
    def text(self,items,max_new_tokens):return [{'raw':'new'}]
    def next_token(self,items):return [{'probability':0.5}]


@pytest.mark.parametrize('mode',['text','readers'])
def test_smoke_divergence_provenance_and_policy(tmp_path,monkeypatch,mode):
    a,items,ref=fixture(mode);assets=tmp_path/'assets.json';H.write(assets,{})
    r=H.smoke(items,ref,a,Backend(),tmp_path,H.sha(assets))
    assert r['status']=='PASS' and all(c['first_divergence_position']==0 for c in r['comparisons'])
    assert r['first_output_evidence']['sha256']==H.sha(tmp_path/'FIRST_READOUT.json')
    assert r['first_output_evidence']['mtime_ns'] <= (tmp_path/'SMOKE_RECEIPT.json').stat().st_mtime_ns
    a['b200_smoke_receipt_sha256']=H.sha(tmp_path/'SMOKE_RECEIPT.json')
    monkeypatch.setattr(H,'actual_gpu',lambda a:'B200')
    hw=H.production_gate(a,tmp_path/'SMOKE_RECEIPT.json',assets,r['capabilities'])
    if mode=='readers':
        p=dict(row_indices=[0],row_roster=[dict(row_index=0,reuse_e87=False)])
        assert H.validate_e95(a,p,None,tmp_path/'SMOKE_RECEIPT.json',hw)['gpu_type']=='B200'
    a['image_digest']='sha256:'+'f'*64
    with pytest.raises(ValueError):H.production_gate(a,tmp_path/'SMOKE_RECEIPT.json',assets,r['capabilities'])


def test_reused_hardware_mismatch():
    a,_,_=fixture()
    with pytest.raises(ValueError):H.bind_units(a,[0],{'0':dict(gpu_type='H200',output_seal_sha256='a'*64)})


def test_failed_load_stop_and_unknown_provenance(tmp_path):
    a,items,ref=fixture()
    class Broken(Backend):
        def load_oracle(self):raise RuntimeError('load')
    with pytest.raises(RuntimeError):H.smoke(items,ref,a,Broken(),tmp_path,'a'*64)
    assert H.read(tmp_path/'STOP_REQUIRED.json')['production_allowed'] is False
    assert H.smoke_provenance(tmp_path)['first_output_utc']=='unknown'
    calls=[]
    def stop():calls.append(True);return {'status':'EXITED'}
    with pytest.raises(RuntimeError):H.operator_gate(tmp_path/'SMOKE_RECEIPT.json',stop)
    assert calls==[True]


def test_nonfinite_stops(tmp_path):
    a,items,ref=fixture('text')
    class Broken(Backend):
        def next_token(self,items):return [{'probability':float('nan')}]
    with pytest.raises(ValueError):H.smoke(items,ref,a,Broken(),tmp_path,'a'*64)
    assert not (tmp_path/'SMOKE_RECEIPT.json').exists()
