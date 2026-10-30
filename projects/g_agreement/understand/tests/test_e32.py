from types import SimpleNamespace
import numpy as np
import pytest
import torch
from projects.g_agreement.understand import e32 as E


def test_donors_reproducible_same_row_value_independent_random():
    items=[dict(id=f'{f}{i}',feature=f,value=i%2) for f in ('a','b') for i in range(8)]
    m=E.donors(items);by={x['id']:x for x in items}
    assert m==E.donors(list(reversed(items)))
    for i,d in m.items():
        assert all(j!=i and by[j]['feature']==by[i]['feature'] for j in d.values())
        assert by[d['same']]['value']==by[i]['value']
        assert by[d['opposite']]['value']!=by[i]['value']
    # Inverting labels leaves the seeded random selection untouched.
    flipped=[{**x,'value':1-x['value']} for x in items]
    assert {i:d['random'] for i,d in m.items()}=={i:d['random'] for i,d in E.donors(flipped).items()}


class Block(torch.nn.Module):
    def forward(self,h):return h+1
class Toy(torch.nn.Module):
    def __init__(self):
        super().__init__();self.layers=torch.nn.ModuleList([Block() for _ in range(64)])


def test_patch_targets_only_placeholder_and_cleans_up():
    m=Toy();h=torch.zeros(2,4,3)
    with E.patch(m,[44,45],{44:torch.full((2,3),9.),45:torch.full((2,3),8.)},[0,2]):
        out=m.layers[44](h)
        assert torch.all(out[0,0]==9) and torch.all(out[1,2]==9)
        assert torch.all(out[0,1:]==1) and torch.all(out[1,:2]==1)
        assert torch.all(m.layers[45](h)[0,0]==8)
        assert torch.all(m.layers[43](h)==1)
    assert not any(b._forward_hooks for b in m.layers)
    with pytest.raises(RuntimeError):
        with E.patch(m,[44],{44:torch.zeros(2,3)},[0,2]):raise RuntimeError('test')
    assert not any(b._forward_hooks for b in m.layers)


@pytest.mark.parametrize('content,baseline,score,verdict',[(7,True,.6,'NOT_LENS_SPECIFIC'),(7,True,.7,'LENS_POLICY'),(7,True,.65,'MIXED'),(6,True,.8,'NOT EVALUABLE'),(9,False,.8,'NOT EVALUABLE')])
def test_registered_gates(content,baseline,score,verdict):
    refs={**{f'c{i}':{'class':'semantic','D':.8} for i in range(9)},**{f's{i}':{'class':'structure','D':.8} for i in range(16)}}
    rows={f:{c:{'A':.8 if baseline else .84,'B':(.75 if int(f[1:])<content else .74) if f.startswith('c') else score} for c in ('w1','e30')} for f in refs}
    r=E.rules(rows,refs,[f's{i}' for i in range(8)])
    assert r['candidate_sets']['w1']['verdict']==verdict


def test_late_and_all_layer_patch_routing(monkeypatch):
    from contextlib import contextmanager
    events=[]
    @contextmanager
    def fake_patch(model,layers,vectors,positions):
        events.append((layers,vectors,positions));yield
    monkeypatch.setattr(E,'patch',fake_patch)
    monkeypatch.setattr(E.E,'encode_frame',lambda t,x,c:{'ids':[62,198,1],'candidate_start':2,'token_count':1})
    monkeypatch.setattr(E.E,'score_batch',lambda *a:[0.])
    eng=object.__new__(E.Engine);eng.model=None;eng.pad=0;eng.tok=SimpleNamespace(encode=lambda *a,**k:[62])
    acts={l:torch.tensor([[float(l)],[100.+l]]) for l in range(64)}
    args=([{'id':'a','text':'text'}],[['a','b']])
    eng.score(*args,'B',acts,{'a':0,'b':1},{})
    assert events[0][0]==list(range(44,64)) and all(v.item()==44 for v in events[0][1].values())
    events.clear();eng.score(*args,'Bprime',acts,{'a':0,'b':1},{})
    assert events[0][0]==list(range(64)) and all(v.item()==l for l,v in events[0][1].items())
    events.clear();eng.score(*args,'opposite',acts,{'a':0,'b':1},{'a':{'opposite':'b'}})
    assert all(v.item()==144 for v in events[0][1].values())


def test_frozen_stage_exact_grid():
    from projects.g_agreement.blindspot import protocol as P
    import json
    b=P.ROOT/'cache/g_agreement/understand/e32-stage-v1'
    P.verify(b,'INPUT_SEAL.json');items=P.rows(b/'items.jsonl');maps=json.loads((b/'DONORS.json').read_text())
    assert len(items)==2100 and len(maps)==2100 and len({x['feature'] for x in items})==25
    for f in {x['feature'] for x in items}:
        row=[x for x in items if x['feature']==f];assert len(row)==84 and sum(x['label'] for x in row)==42


@pytest.mark.parametrize('content_ok',[True,False])
def test_complete_worker_and_content_stop_cpu(tmp_path,monkeypatch,content_ok):
    import json
    from projects.g_agreement.blindspot import protocol as P
    b=tmp_path/'bank';b.mkdir();items=[];refs={};pairs={'w1':{},'e30':{}}
    for i in range(25):
        f=f'r{i}';refs[f]={'D':1.,'class':'semantic' if i<9 else 'structure'}
        for cs in pairs:pairs[cs][f]=[['a','b'],['c','d']]
        for j in range(84):items.append(dict(id=f'{f}:{j}',feature=f,text='t',ids=[1],label=j%2,cluster=str(j//14)))
    P.jsonl(b/'items.jsonl',items);P.dump(b/'pairs.json',pairs);P.dump(b/'references.json',refs);P.dump(b/'DONORS.json',{})
    np.save(b/'reference44.npy',np.ones((2100,2),dtype=np.float32));P.seal(b,[p.name for p in b.iterdir()],'TEST')
    plan=tmp_path/'plan.json';P.dump(plan,{'source_files':{},'input_seal_sha256':P.sha(b/'INPUT_SEAL.json'),'high_D_rows':[f'r{i}' for i in range(9,17)]})
    assets=tmp_path/'assets.json';P.dump(assets,{})
    assignment=tmp_path/'assignment.json';now=E.time.time()
    P.dump(assignment,dict(issuer='integrator',experiment='E32',pod_id='test',plan_sha256=P.sha(plan),assets_manifest_sha256=P.sha(assets),previous_gpu_seconds=0,external_hardstop_verified=True,source_published=True,provider_created_epoch=now-1,deadline_epoch=now+1700))
    class Fake:
        def __init__(self,*a):self.tok=SimpleNamespace(encode=lambda *a,**k:[62])
        def capture(self,items):return {l:torch.ones(2100,2) for l in range(64)}
        def score(self,group,pairs,arm,*a):return [float(x['label']) if arm=='A' or content_ok else 0. for x in group]
    monkeypatch.setattr(E,'Engine',Fake);monkeypatch.setenv('RUNPOD_POD_ID','test');monkeypatch.setattr(torch.cuda,'is_available',lambda:True);monkeypatch.setattr(torch.cuda,'synchronize',lambda:None)
    monkeypatch.setattr(E.signal,'signal',lambda *a:None);monkeypatch.setattr(E.signal,'setitimer',lambda *a:None)
    out=tmp_path/'out';E.run(SimpleNamespace(plan=plan,bank=b,assignment=assignment,assets=assets,out=out))
    if content_ok:
        P.verify(out,'SCORE_SEAL.json');assert len(P.rows(out/'scores.jsonl'))==25200
    else:
        P.verify(out,'GATE_SEAL.json');assert not (out/'SCORE_SEAL.json').exists()
        assert all(x['arm']=='A' or refs[x['feature']]['class']=='semantic' for x in P.rows(out/'gate_scores.jsonl'))
