import ast,json
from pathlib import Path
from types import SimpleNamespace
from contextlib import nullcontext
import numpy as np
import pytest
import torch
from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand import certified_capture as C,e24_relaunch as E,e24_relaunch_analysis as A,e32_relaunch as R
from projects.g_agreement.understand.tests.test_e24_environment import Model

def context(tmp_path):
    items=[{'id':'short','feature':'f','ids':[10,20]},{'id':'long','feature':'f','ids':list(range(503))}]
    b=tmp_path/'context';b.mkdir();P.jsonl(b/'items.input.jsonl',items);P.dump(b/'layout.json',[{'unit':'u','start':0,'ids':['short','long']}]);P.seal(b,['items.input.jsonl','layout.json'],'context');return b,items
@pytest.mark.parametrize('mode',['G','E','C','D'])
def test_capture_routes_clones_lengths_and_metadata(tmp_path,mode):
    b,items=context(tmp_path);ol=SimpleNamespace(model=Model(),tok=SimpleNamespace(pad_token_id=0),base=nullcontext)
    hs,meta=C.capture(ol,items,[20,44,60],mode,b)
    assert set(hs)=={20,44,60}
    for l,h in hs.items():assert h[:,0].tolist()==[20+l+1,502+l+1]
    assert {x['id'] for x in meta}=={'short','long'}
    assert all(x['read_position']==x['token_count']-1 for x in meta)
    assert [x['padding_length'] for x in meta]==([501,0] if mode=='G' else [0,0])
    assert not any(x._forward_hooks for x in ol.model.layers)

def cert(tmp_path,mode='G',failed=0):
    import importlib.metadata as md
    d=tmp_path/'cert';d.mkdir()
    packages={x.metadata['Name'].lower():x.version for x in md.distributions() if x.metadata.get('Name')}
    for env in ('w1','kernels'):P.dump(d/f'ENV_{env}.json',{'packages':packages})
    E.seal(d,['ENV_w1.json','ENV_kernels.json'],'DIAGNOSTIC_SEAL.json','mock')
    P.dump(d/'DECISION.json',{'status':'CAPTURE_MODE_CERTIFIED','certified_arm':mode,'below_0999':{'C':failed}});P.dump(d/'STRATA.json',{'C':{'minimum_W1':.8 if failed else 1.}});E.seal(d,['DECISION.json','STRATA.json'],'ANALYSIS_SEAL.json','mock');return d
@pytest.mark.parametrize('mode,requested',[('G','G'),('E','E'),('C','CD'),('D','CD')])
def test_only_certified_mode_and_matching_environment(tmp_path,monkeypatch,mode,requested):
    b,_=context(tmp_path);d=cert(tmp_path,mode);p={'capture_mode':requested,'capture_context_seal_sha256':P.sha(b/'INPUT_SEAL.json')};q={'diagnostic_analysis_seal_sha256':P.sha(d/'ANALYSIS_SEAL.json')}
    monkeypatch.setattr(C.sys,'prefix',C.PREFIX[mode]);assert C.release(p,q,d,b)==mode
    monkeypatch.setattr(C.sys,'prefix','/wrong')
    with pytest.raises(ValueError,match='environment'):C.release(p,q,d,b)
    p['capture_mode']='E' if requested!='E' else 'G'
    with pytest.raises(ValueError,match='uncertified'):C.release(p,q,d,b,False)

def test_C_failure_overrides_G_certification(tmp_path):
    b,_=context(tmp_path);d=cert(tmp_path,failed=18)
    with pytest.raises(ValueError,match='all capture-dependent'):
        C.release({'capture_mode':'G','capture_context_seal_sha256':P.sha(b/'INPUT_SEAL.json')},{'diagnostic_analysis_seal_sha256':P.sha(d/'ANALYSIS_SEAL.json')},d,b,False)

def test_parity_failure_preserves_ids(tmp_path):
    with pytest.raises(ValueError):C.parity_gate(np.array([[1.,0],[0,1]]),np.array([[1.,0],[1,0]]),tmp_path,[{'id':'good'},{'id':'bad'}])
    rr=P.rows(tmp_path/'PARITY_FAILURE_ITEMS.jsonl');assert rr[1]=={'id':'bad','cosine':0.}
    assert not (tmp_path/'PARITY.json').exists()

def forecasts(n=8):
    return [dict(slot=i,layers=ls,plan_sha256='p',capture_seal_sha256=f'own{i}',provider_created_epoch=0.,first_science_epoch=500.,forecast_epoch=1000.,provider_deadline_epoch=E.TOTAL/n,tier1={str(l):{c:1. for c in ('C1','C2','C4','C5')} for l in ls},C6={str(l):1. for l in ls if l in E.C6_LAYERS},C7={str(l):1. for l in ls if l in E.C7_LAYERS},c6_capture_and_transfer_s=10.) for i,ls in enumerate(E.shards(n))]
@pytest.mark.parametrize('n',range(1,9))
def test_shard_layout_budget_and_own_seals(n):
    ls=E.shards(n);assert all(x[0]==44 for x in ls)
    assert sorted(l for x in ls for l in x if l!=44)==sorted(set(E.PRIORITY)-{44})
    result=E.schedule(forecasts(n),1100);assert result['status']=='FIT'
    assert result['reserved_gpu_s']<=32738
    assert result['capture_seals']=={str(i):f'own{i}' for i in range(n)}

def test_scientific_helpers_byte_identical():
    root=P.ROOT/'projects/g_agreement/understand'
    for old,new,excluded in [('e24_analysis.py','e24_relaunch_analysis.py',{'analyse'}),('e32.py','e32_relaunch.py',{'run'})]:
        def funcs(n):return {x.name:ast.dump(x,include_attributes=False) for x in ast.parse((root/n).read_text()).body if isinstance(x,ast.FunctionDef) and x.name not in excluded}
        assert funcs(old)==funcs(new)

def test_no_scoring_before_local_parity():
    s=(P.ROOT/'projects/g_agreement/understand/e24_relaunch.py').read_text()
    assert s.index('p=parity_gate(')<s.index('def measure(')<s.index("for l in own['layers']")
    assert 'if a.slot==0' not in s and "capture=a.out/'capture'" in s
    with pytest.raises(ValueError):E.shards(9)


def test_cpu_analysis_end_to_end_synthetic(tmp_path,monkeypatch):
    """Complete fake 28-row population, real dev probe fits, shortened test bootstrap."""
    bank=tmp_path/'bank';bank.mkdir();out=tmp_path/'pod';out.mkdir();capture=out/'capture';capture.mkdir();dest=out/'L44';dest.mkdir()
    scope=json.loads((P.ROOT/'results/g_agreement/understand/e24/SCOPE.json').read_text())
    source=json.loads((P.ROOT/'cache/g_agreement/understand/e24-stage-v1/templates.json').read_text())
    items=[];labels=[];h=[];readouts=[];c5ids=[];c5=[];c2rows=['prose_paren','prose_quote','python_string','python_indent','python_depth','list_depth','table_role']
    for f in scope['rows_c1_c3_c4']:
        for split in ('dev','test'):
            for j in range(84):
                uid=f'{f}:{split}:{j}';y=j%2;items.append({'id':uid,'feature':f,'split':split,'ids':[1]});h.append([float(y),1.])
                labels.append({'id':uid,'feature':f,'split':split,'value':source[f]['values'][0 if y else 1],'cluster':f'{split}:{j//14}','class':source[f]['class']})
                if split=='test':
                    readouts.append({'id':uid,'feature':f,'C1':[0.,0.],'C2':[0.,0.] if f in c2rows else None,'C2_swap':[0.,0.] if f in c2rows else None,'C4':''})
                    if f in scope['rows_c5']:c5ids.append(uid);c5.append([0.,1.])
    P.dump(bank/'SCOPE.json',scope);P.dump(bank/'templates.json',source);P.dump(bank/'c2.json',{f:[['a','b']]*2 for f in c2rows});P.jsonl(bank/'items.input.jsonl',items)
    np.save(bank/'reference44.npy',np.array(h,dtype=np.float32));P.seal(bank,[p.name for p in bank.iterdir()],'TEST')
    lab=tmp_path/'labels.json';P.dump(lab,{'w1':labels,'w1_metrics':{'rows':[{'feature':f,'reader':'olens','layer':44,'true':{'auroc':.6 if f=='prose_paren' else .5}} for f in source]},
        'e15_metrics':[{'feature':f,'valid_pairs':[0,1],'readers':{'olens':{'arms':{'true':{'auroc':.5}}}}} for f in c2rows]})
    ref=tmp_path/'e1b.json';P.dump(ref,{'rows':{f:.5 for f in scope['rows_c5']}})
    plan=tmp_path/'plan.json';P.dump(plan,{'source_files':{},'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),'labels_sha256':P.sha(lab),'e1b_reference':str(ref)})
    np.save(capture/'acts44.npy',np.array(h,dtype=np.float32));P.dump(capture/'ORDER.json',[x['id'] for x in items]);P.dump(capture/'BINDING.json',{'plan_sha256':P.sha(plan)})
    E.seal(capture,['acts44.npy','ORDER.json','BINDING.json'],'L44_SEAL.json','TEST');E.seal(capture,['L44_SEAL.json'],'CAPTURE_SEAL.json','TEST')
    P.dump(out/'FORECAST.json',{'slot':0});P.dump(out/'ADMISSION.json',{'pods':[{'layers':[44]}],'layers_priority':[44],'C6':False,'C7':False})
    P.jsonl(dest/'readouts.jsonl',readouts);np.save(dest/'C5.npy',np.array(c5));P.dump(dest/'C5_ORDER.json',c5ids)
    P.dump(dest/'BINDING.json',{'layer':44,'plan_sha256':P.sha(plan),'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),
        'capture_layer_seal_sha256':P.sha(capture/'L44_SEAL.json'),'admission_sha256':P.sha(out/'ADMISSION.json')})
    E.seal(dest,[p.name for p in dest.iterdir()],'SCORE_SEAL.json','TEST');E.seal(out,['L44/SCORE_SEAL.json','ADMISSION.json','FORECAST.json'],'SCORE_SEAL.json','TEST')
    monkeypatch.setattr(A,'draws',lambda clusters:[np.arange(len(clusters))]*10)
    a=SimpleNamespace(bank=bank,plan=plan,capture=capture,labels=lab,out=tmp_path/'analysis',outputs=[out],c6_capture=None)
    A.analyse(a);P.verify(a.out,'ANALYSIS_SEAL.json');m=json.loads((a.out/'metrics.json').read_text())
    assert m['invalid_R0_rows_uninterpretable_everywhere']==['prose_paren']
    assert 'R6_all_layers' not in m and 'R6' not in m['rules']['44']
    assert sum('C5' in cell for cell in m['layers']['44'].values())==25
    assert all(c['C5_pass'] for f in scope['rows_c5'] for c in m['R0'][f]['anchors'])
    assert len(m['holm'])==190 and len(m['layers']['44'])==28
    assert len(m['rules']['44']['R3_prime']['denominator'])==7
    assert m['rules']['44']['R4']['held'] is None
    assert len(P.rows(a.out/'JUDGE_PACKET.jsonl'))==20
    assert m['layers']['44']['prose_paren']['C3']['auroc']==1
    with pytest.raises(FileExistsError):A.analyse(a)

@pytest.mark.parametrize('mode',['G','E','C','D'])
@pytest.mark.parametrize('bad_parity',[False,True])
def test_e24_worker_complete_shard_or_stop_before_scores(tmp_path,monkeypatch,mode,bad_parity):
    import time
    from projects.g_agreement.blindspot import ar_tests
    bank=tmp_path/'bank';bank.mkdir();items=[];cont=[];specs={}
    for f in range(28):
        row=f'r{f}';specs[row]={'olens':[['A','B'],['C','D']]}
        for split in ('dev','test'):
            for j in range(84):
                uid=f'{row}:{split}:{j}';items.append({'id':uid,'feature':row,'split':split,'ids':[j+1],'donor_id':f'{row}:{split}:{j^1}'})
                if f<25 and split=='test':cont.append({'id':uid,'text':'fixed'})
    P.jsonl(bank/'items.input.jsonl',items);P.jsonl(bank/'continuations.jsonl',cont);P.dump(bank/'templates.json',specs)
    P.dump(bank/'c2.json',{'r0':[['A','B'],['C','D']]});P.dump(bank/'c7.json',{'r0':[['A','B']]*8});P.dump(bank/'c6.pairs.json',{'s':[[0,'A','B']]})
    P.jsonl(bank/'c6.input.jsonl',[{'id':f's{i}','feature':'s','ids':[1]} for i in range(600)])
    np.save(bank/'reference44.npy',np.ones((4704,2)));np.save(bank/'c6.reference44.npy',np.ones((600,2)));P.seal(bank,[x.name for x in bank.iterdir()],'mock')
    plan=tmp_path/'plan.json';P.dump(plan,{'source_files':{},'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),'modal14_sha256':'fixed'})
    q=tmp_path/'assignment.json';now=time.time();P.dump(q,{'issuer':'integrator','experiment':'E24','pod_id':'p','slot':0,'plan_sha256':P.sha(plan),'source_files':{},'previous_gpu_seconds':0,'pod_count':1,'pregen_freeze_published':True,'source_published':True,'external_hardstop_verified':True,'modal14_hash_correction_commit':'x','modal14_corrected_sha256':'fixed','provider_created_epoch':now-1,'deadline_epoch':now+10000,'allocated_gpu_seconds':10001})
    calls=[]
    class Fake:
        def __init__(self,*a):self.ol=SimpleNamespace(tok=SimpleNamespace(encode=lambda s:list(s)));self.tok=self.ol.tok
        def capture(self,items,layers):
            self.last_capture_metadata=[{'id':x['id'],'token_count':len(x['ids']),'padding_length':0,'capture_mode':mode} for x in items]
            h=torch.ones(len(items),2)
            if bad_parity:h[-1]*=-1
            return {l:h for l in layers}
        def asked(self,h,l,pairs,prefix=''):calls.append('score');return torch.zeros(len(pairs),len(h))
        def free(self,h,l):calls.append('score');return [['readout'] for _ in h]
        def reconstruct(self,texts,l):calls.append('score');return torch.ones(len(texts),2)
    monkeypatch.setattr(E,'Engine',Fake);monkeypatch.setattr(C,'release',lambda *a:mode);monkeypatch.setenv('RUNPOD_POD_ID','p')
    monkeypatch.setattr(E.W,'_assets',lambda *a,**k:{});monkeypatch.setattr(E.W,'_labels_absent',lambda *a:None);monkeypatch.setattr(ar_tests,'_assets',lambda *a:None)
    monkeypatch.setattr(torch.cuda,'synchronize',lambda:None);monkeypatch.setattr(torch.cuda,'manual_seed_all',lambda *a:None)
    monkeypatch.setattr(E.signal,'signal',lambda *a:None);monkeypatch.setattr(E.signal,'setitimer',lambda *a:None)
    admission=tmp_path/'admission.json';original_dump=P.dump
    def dump(path,value):
        original_dump(path,value)
        if Path(path).name=='FORECAST.tmp':
            decision=E.schedule([value],time.time());decision['forecasts']=[value];decision['forecast_sha256']={'0':P.sha(path)};original_dump(admission,decision)
    monkeypatch.setattr(P,'dump',dump)
    a=SimpleNamespace(bank=bank,plan=plan,assignment=q,assets=tmp_path/'assets',ar_source=tmp_path,whitener=tmp_path,out=tmp_path/'out',admission=admission,slot=0,capture=None,c6_capture=None,certificate=tmp_path,capture_context=tmp_path)
    if bad_parity:
        with pytest.raises(ValueError,match='parity failed'):E.run(a)
        assert calls==[] and (a.out/'capture/PARITY_FAILURE_ITEMS.jsonl').exists()
        assert not (a.out/'FORECAST.json').exists()
    else:
        E.run(a);P.verify(a.out,'SCORE_SEAL.json');assert len(P.rows(a.out/'L44/readouts.jsonl'))==2352
        assert set(E.read(a.out/'ADMISSION.json')['capture_seals'])=={'0'}
        assert len(P.rows(a.out/'capture/ITEM_ENVIRONMENT.jsonl'))==4704


@pytest.mark.parametrize('mode',['G','E','C','D'])
@pytest.mark.parametrize('content_ok',[True,False])
def test_e32_relaunch_worker_and_gate(tmp_path,monkeypatch,content_ok,mode):
    import json
    from projects.g_agreement.blindspot import protocol as P
    b=tmp_path/'bank';b.mkdir();items=[];refs={};pairs={'w1':{},'e30':{}}
    for i in range(25):
        f=f'r{i}';refs[f]={'D':1.,'class':'semantic' if i<9 else 'structure'}
        for cs in pairs:pairs[cs][f]=[['a','b'],['c','d']]
        for j in range(84):items.append(dict(id=f'{f}:{j}',feature=f,text='t',ids=[1],label=j%2,cluster=str(j//14)))
    P.jsonl(b/'items.jsonl',items);P.dump(b/'pairs.json',pairs);P.dump(b/'references.json',refs);P.dump(b/'DONORS.json',{})
    np.save(b/'reference44.npy',np.ones((2100,2),dtype=np.float32));P.seal(b,[p.name for p in b.iterdir()],'TEST')
    plan=tmp_path/'plan.json';P.dump(plan,{'remaining_gpu_seconds':1800,'source_files':{},'input_seal_sha256':P.sha(b/'INPUT_SEAL.json'),'high_D_rows':[f'r{i}' for i in range(9,17)]})
    assets=tmp_path/'assets.json';P.dump(assets,{})
    assignment=tmp_path/'assignment.json';now=R.time.time()
    P.dump(assignment,dict(issuer='integrator',experiment='E32',pod_id='test',plan_sha256=P.sha(plan),assets_manifest_sha256=P.sha(assets),previous_gpu_seconds=0,external_hardstop_verified=True,source_published=True,provider_created_epoch=now-1,deadline_epoch=now+1700))
    class Fake:
        def __init__(self,*a):self.tok=SimpleNamespace(encode=lambda *a,**k:[62])
        def capture(self,items):
            self.last_capture_metadata=[{'id':x['id'],'capture_mode':mode,'padding_length':0} for x in items]
            return {l:torch.ones(2100,2) for l in range(64)}
        def score(self,group,pairs,arm,*a):return [float(x['label']) if arm=='A' or content_ok else 0. for x in group]
    monkeypatch.setattr(C,'release',lambda *a:mode)
    monkeypatch.setattr(R,'Engine',Fake);monkeypatch.setenv('RUNPOD_POD_ID','test');monkeypatch.setattr(torch.cuda,'is_available',lambda:True);monkeypatch.setattr(torch.cuda,'synchronize',lambda:None)
    monkeypatch.setattr(R.signal,'signal',lambda *a:None);monkeypatch.setattr(R.signal,'setitimer',lambda *a:None)
    out=tmp_path/'out';R.run(SimpleNamespace(plan=plan,bank=b,assignment=assignment,assets=assets,out=out,certificate=tmp_path,capture_context=tmp_path))
    if content_ok:
        P.verify(out,'SCORE_SEAL.json');assert len(P.rows(out/'scores.jsonl'))==25200
    else:
        P.verify(out,'GATE_SEAL.json');assert not (out/'SCORE_SEAL.json').exists()
        assert all(x['arm']=='A' or refs[x['feature']]['class']=='semantic' for x in P.rows(out/'gate_scores.jsonl'))


def test_146_releases_only_certified_G_despite_C_disagreement(tmp_path):
    b,_=context(tmp_path);d=cert(tmp_path,failed=18)
    p={'capture_mode':'G','capture_context_seal_sha256':P.sha(b/'INPUT_SEAL.json'),'operations_authority':'d0f72b00'}
    q={'diagnostic_analysis_seal_sha256':P.sha(d/'ANALYSIS_SEAL.json')}
    assert C.release(p,q,d,b,False)=='G'
    p['capture_mode']='E'
    with pytest.raises(ValueError,match='uncertified'):C.release(p,q,d,b,False)
    p['capture_mode']='G';p['operations_authority']='e8d1035a'
    with pytest.raises(ValueError,match='all capture-dependent'):C.release(p,q,d,b,False)
