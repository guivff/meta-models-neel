import contextlib,time
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from projects.g_agreement.e101 import runner109 as R
from projects.g_agreement.e101.contract109 import CAPTURE,READ,identity
from projects.g_agreement.e101.contract import read
from projects.g_agreement.e101.test_e104 import Tiny104,Layer
from projects.g_agreement.e101.runner import dependencies


@pytest.fixture(autouse=True)
def vendored_runtime_path():
    dependencies()


class Tiny109(Tiny104):
    def __init__(self,fail_call=None):
        super().__init__(fail_call);self.layers.extend(Layer(i) for i in range(46,61));self.config.num_hidden_layers=61


def packet():
    xs=[];dd=[]
    for split in ('dev','test'):
        for base in ('a','b'):
            for condition in ('unhooked','steered','random'):
                ix=None
                if condition!='unhooked':
                    ix=len(dd);dd.append([1.,.2,-.3,.5] if condition=='steered' else [-.2,1.,.5,.3])
                xs.append(dict(id=identity(split,'fact_recall',base,condition),base_id=base,row='fact_recall',split=split,
                  condition=condition,alpha=8.,ids=list(range(1,11)),read_index=9,delta_index=ix))
    return xs,dict(deltas=np.asarray(dd,np.float32),manifest={})


def test_three_conditions_five_layer_capture_reuses_E104_hook_without_read_patch():
    xs,data=packet();xs=[x for x in xs if x['split']=='test'];xs=[x for c in ('unhooked','steered','random') for x in xs if x['condition']==c]
    m=Tiny109();before=data['deltas'].tobytes();rr,arrays=R.capture_batch(m,xs,data['deltas'])
    assert m.calls==3 and set(arrays)==set(CAPTURE) and all(v.shape==(6,4) for v in arrays.values())
    assert data['deltas'].tobytes()==before and [x['id'] for x in rr]==[x['id'] for x in xs]
    for snapshot in m.snapshots[1:]:
        assert torch.equal(snapshot[40][:,9],m.snapshots[0][40][:,9])
        assert torch.equal(snapshot[40][:,0],m.snapshots[0][40][:,0])
        assert not torch.equal(snapshot[40][:,1:9],m.snapshots[0][40][:,1:9])
    for layer in CAPTURE:
        expected=np.concatenate([s[layer][:,9].numpy() for s in m.snapshots])
        assert np.array_equal(arrays[layer],expected)
    assert all(not l._forward_hooks for l in m.layers)
    assert rr[0]['injection_sites']==[] and not rr[0]['hook_installed']
    assert [x['position'] for x in rr[2]['injection_sites']]==list(range(1,9))


@pytest.mark.parametrize('call',[1,2,3])
def test_hook_cleanup_after_natural_or_intervened_failure(call):
    xs,data=packet();xs=[x for c in ('unhooked','steered','random') for x in xs if x['split']=='test' and x['condition']==c]
    m=Tiny109(fail_call=call)
    with pytest.raises(RuntimeError):R.capture_batch(m,xs,data['deltas'])
    assert all(not l._forward_hooks for l in m.layers)


class Runtime:
    def __init__(self):self.base=Tiny109();self.hardware_assignment={'gpu_type':'CPU_SYNTHETIC'};self.loaded=[]
    def load_base(self):self.loaded.append('base')
    def load_oracle(self):self.loaded.append('oracle')
    def subject(self):return self.base,None,contextlib.nullcontext()


class Backend:
    @staticmethod
    def confirm_layers(runtime):return [20,28,36,44,48,52,56,60]
    @staticmethod
    def sweep(runtime,reader,vectors,layer):
        assert reader=='oracle' and layer in READ
        return [dict(text='synthetic',raw='synthetic',native_max_new_tokens=128) for _ in vectors]


@pytest.mark.parametrize('timing',[False,True])
def test_end_to_end_capture_and_only_hooked_test_greedy_reads(tmp_path,monkeypatch,timing):
    xs,data=packet();rt=Runtime();old,*_=dependencies();monkeypatch.setattr(R,'backend87',lambda:Backend)
    result=R.acquire(xs,data,rt,old.Clock(tmp_path,time.time()+3600),tmp_path,timing)
    assert result==('TIMING_ONLY' if timing else 'COMPLETE') and rt.loaded==['base','oracle']
    oracle=[]
    for p in (tmp_path/'jobs').glob('*.json'):
        oracle.extend(x for x in read(p) if x['channel'].startswith('oracle_'))
    assert len(oracle)==2*2*3 and {x['layer'] for x in oracle}==set(READ)
    assert all(x['split']=='test' and x['condition']!='unhooked' for x in oracle)
    assert len({x['id'] for x in oracle})==len(oracle)
    if timing:assert read(tmp_path/'MEASURED_PROFILE.json')['profile_outputs_discarded']
    else:
        assert len(read(tmp_path/'CAPTURE_INDEX.json'))==12
        arrays=read(tmp_path/'CAPTURE_ARRAYS.json');order=read(tmp_path/'ARRAY_ORDER.json')
        assert order['fact_recall']['dev']==['a','b']
        for layer in CAPTURE:
            ref=arrays['fact_recall']['test']['steered'][str(layer)]
            assert np.load(tmp_path/ref['member']).shape==(2,4)
        assert len(read(tmp_path/'READOUT_INDEX.json'))==3


def test_original_E87_sweep_parameters_and_layer_are_preserved(monkeypatch):
    old,*_=dependencies();b=R.backend87();calls=[]
    class Oracle:
        def verbalize(self,vectors,layer,**kwargs):
            calls.append((vectors.clone(),layer,kwargs));return [['text'] for _ in vectors]
    rt=SimpleNamespace(readers=SimpleNamespace(oracle=Oracle()))
    vectors=np.ones((2,4),np.float32);before=vectors.tobytes()
    result=b.sweep(rt,'oracle',vectors,52)
    assert len(result)==2 and vectors.tobytes()==before and calls[0][1]==52
    kw=calls[0][2];assert kw['k']==1 and kw['batch']==8 and kw['sampling'].temperature==0
    assert kw['sampling'].max_new_tokens==128 and kw['sampling'].top_p==1 and kw['sampling'].top_k==0


def full_contract_packet():
    from projects.g_agreement.e101.contract109 import DIRECTION_SHA
    xs=[];dd=[]
    for split in ('dev','test'):
        for i in range(84):
            for condition in ('unhooked','steered','random'):
                ix=None
                if condition!='unhooked':ix=len(dd);dd.append(np.ones(5120,np.float32))
                xs.append(dict(id=identity(split,'fact_recall',str(i),condition),base_id=str(i),row='fact_recall',split=split,condition=condition,alpha=8.,ids=list(range(10)),read_index=9,delta_index=ix))
    return xs,np.asarray(dd),dict(experiment='E109',seed=20261029,rows=['fact_recall'],capture_blocks=list(CAPTURE),oracle_blocks=list(READ),direction_sha256=DIRECTION_SHA,write_block=40,read_token_patched=False)


def test_contract_accepts_all_84_dev_test_and_matched_controls():
    from projects.g_agreement.e101.contract109 import validate
    xs,dd,m=full_contract_packet();validate(xs,dd,m)


@pytest.mark.parametrize('defect',['private_label','patched_baseline','changed_dose','unmatched_random'])
def test_contract_rejects_scientific_or_privacy_substitution(defect):
    from projects.g_agreement.e101.contract109 import validate
    xs,dd,m=full_contract_packet()
    if defect=='private_label':xs[0]['label']=1
    if defect=='patched_baseline':xs[0]['delta_index']=0
    if defect=='changed_dose':xs[1]['alpha']=4.
    if defect=='unmatched_random':dd[1]*=2
    with pytest.raises(ValueError):validate(xs,dd,m)
