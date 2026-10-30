import json
from contextlib import nullcontext
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand import e24_environment as E,e24_clone_capture as C
from projects.g_agreement.understand.e24_diagnostic import original_module
from projects.g_agreement.understand.e24_worker import seal

def test_clone_copy_changes_only_hook():
    s=(P.ROOT/'external/mats-nla-workspace/src/mats/capture.py').read_text()
    assert (P.ROOT/'projects/g_agreement/understand/e24_clone_capture.py').read_text()==s.replace('cur[L] = _hidden(o).detach()','cur[L] = _hidden(o).detach().clone()')
class Block(torch.nn.Module):
    def forward(self,x):return x.add_(1)
class Model(torch.nn.Module):
    def __init__(self):
        super().__init__();self.p=torch.nn.Parameter(torch.zeros(1));self.layers=torch.nn.ModuleList([Block() for _ in range(61)])
    def forward(self,input_ids,attention_mask,logits_to_keep):
        h=input_ids.float().unsqueeze(-1).repeat(1,1,2)
        for layer in self.layers:h=layer(h)
        return h
@pytest.mark.parametrize('arm',E.ARMS)
def test_real_w1_route_clone_position_no_truncation(arm):
    original=original_module({'w1_capture_module':'results/g_agreement/understand/e24d/frozen_w1_run.py'})
    ol=SimpleNamespace(base=nullcontext,model=Model(),tok=SimpleNamespace(pad_token_id=0))
    batch=[{'ids':list(range(503)),'id':'long'},{'ids':[10,20],'id':'short'}]
    if arm in ('C','D','E'):batch=batch[:1]
    h=E.capture_batch(arm,ol,batch,original,C.capture)
    assert torch.equal(h[44][:,0],torch.tensor([x['ids'][-1]+45. for x in batch]))
    assert set(h)==(set(range(20,61,4)) if arm=='G' else {42,44})
    assert not any(b._forward_hooks for b in ol.model.layers)

def test_layout_preserves_neighbours_and_zero_padding():
    items={k:{'ids':[0]*n} for k,n in [('a',2),('b',4),('c',2),('bg',7)]}
    original=[{'unit':'u','start':0,'ids':['a','bg']},{'unit':'u','start':32,'ids':['b','c']}]
    q=E.layouts(items,['a','b','c'],original)
    assert q['A']==q['B']==q['G']==original
    assert all(len(x['ids'])==1 for x in q['C']+q['D'])
    assert all(len({len(items[uid]['ids']) for uid in x['ids']})==1 for x in q['E'])

def decision_data():return {k:[1.,1.] for k in E.ARMS},{k:float(i+1) for i,k in enumerate(E.ARMS)}
def test_G_preference_and_fastest_other():
    w,t=decision_data();assert E.decide(w,[1,1],t)['certified_arm']=='G'
    w['G']=[.99,1];assert E.decide(w,[1,1],t)['certified_arm']=='A'
    w['A']=[.99,1];assert E.decide(w,[1,1],t)['certified_arm']=='B'
def test_reference_suspect_overrides_passing_G():
    w,t=decision_data();w['C']=[.99,1];w['D']=[.99,1]
    r=E.decide(w,[1,1],t);assert r['certified_arm'] is None and 'SUSPECT' in r['status']
def test_no_passing_mode():
    w,t=decision_data();w={k:[.9,1] for k in w}
    assert E.decide(w,[.8,1],t)['status']=='NO_MODE_CERTIFIED'
def test_boundary_and_nonfinite():
    w,t=decision_data();w={k:[.999,1] for k in w};assert E.decide(w,[1,1],t)['certified_arm']=='G'
    w['B']=[float('nan'),1]
    with pytest.raises(ValueError):E.decide(w,[1,1],t)
def test_assignment_caps_run_once_and_envs():
    q={'issuer':'integrator','experiment':'E24-E','pod_id':'p','plan_sha256':'h','source_published':True,'external_hardstop_verified':True,'previous_e24e_gpu_seconds':0,'provider_created_epoch':100,'deadline_epoch':2800,'environments':{k:{'python':path,'expected_packages':dict.fromkeys(['torch','transformers','peft'],'x'),'reference_evidence':'sealed'} for k,path in [('w1','/weights/venv/bin/python'),('kernels','/weights/venv-kernels/bin/python')]}}
    E.validate_assignment(q,'h','p')
    for key,value in [('deadline_epoch',2801),('previous_e24e_gpu_seconds',1),('external_hardstop_verified',False),('pod_id','other')]:
        bad={**q,key:value}
        with pytest.raises(ValueError):E.validate_assignment(bad,'h','p')

def test_full_cpu_analysis_once_and_seals(tmp_path):
    bank=tmp_path/'bank';bank.mkdir();out=tmp_path/'out';out.mkdir();plan=tmp_path/'plan.json'
    sel=[{'id':'x','reference_index':0},{'id':'y','reference_index':1}];P.dump(bank/'selected.json',sel)
    np.save(bank/'reference44.npy',np.eye(2));P.seal(bank,['selected.json','reference44.npy'],'inputs')
    P.dump(plan,{'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json')})
    for arm in E.ARMS:
        d=out/arm;d.mkdir();np.save(d/'acts44.npy',np.eye(2));P.jsonl(d/'records.jsonl',[{'id':x['id'],'row':'r','token_count':10+i,'padding_length':i,'arm':arm} for i,x in enumerate(sel)])
        P.dump(d/'TIMING.json',{'capture_seconds':1.});P.dump(d/'BINDING.json',{'plan_sha256':P.sha(plan),'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json')})
        seal(d,[p.name for p in d.iterdir()],'CAPTURE_SEAL.json','mock')
    E.analyse(out,bank,plan);P.verify(out,'ANALYSIS_SEAL.json')
    assert json.loads((out/'DECISION.json').read_text())['certified_arm']=='G'
    assert len(P.rows(out/'metrics.jsonl'))==12
    with pytest.raises(FileExistsError):E.analyse(out,bank,plan)

def test_frozen_sample_and_layout():
    bank=P.ROOT/'cache/g_agreement/understand/e24e-stage-v1'
    if not bank.exists():pytest.skip('local bank absent')
    P.verify(bank,'INPUT_SEAL.json');sel=json.loads((bank/'selected.json').read_text());ids={x['id'] for x in sel}
    old=json.loads((P.ROOT/'cache/g_agreement/understand/e24d-stage-v1/selected.json').read_text())
    assert len(sel)==len(ids)==500 and {x['id'] for x in old}<=ids
    items={x['id']:x for x in P.rows(bank/'items.input.jsonl')}
    for arm,bb in json.loads((bank/'layout.json').read_text()).items():
        seen=[uid for b in bb for uid in b['ids'] if uid in ids];assert len(seen)==500 and set(seen)==ids
        if arm in ('C','D','E'):assert all(len({len(items[u]['ids']) for u in b['ids']})==1 for b in bb)
