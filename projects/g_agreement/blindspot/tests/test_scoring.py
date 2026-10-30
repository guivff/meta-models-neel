from contextlib import contextmanager
from types import SimpleNamespace

import numpy as np
import json
import pytest
import torch

from projects.g_agreement.blindspot.run import (
    capture_and_score, capture_sweep, probe_scores, native_baseline_contrasts,
    collect_unasked, UNASKED_POLICY, W5_LAYERS, LogitLens, _score_rows,
)
from projects.g_agreement.blindspot.ar_tests import decompose,kl_to


def test_capture_adapter_off_and_real_mismatched_forward(monkeypatch):
    import mats.capture as capture
    active={'off':False}
    class OL:
        model=object();tok=SimpleNamespace(pad_token_id=0)
        @contextmanager
        def base(self):
            active['off']=True
            try:yield
            finally:active['off']=False
        def paired_logodds_templates(self,h,layer,pairs):
            assert not active['off'] and layer==44
            assert len(pairs)==2
            return h[:,0].repeat(2,1)
    class J:
        def paired_logodds(self,h,layer,a,b):
            assert layer==44
            assert len(a)==len(b)==1 and (a[0],b[0]) in [('a','b'),('c','d')]
            return h[:,0]
    def fake(model,seqs,layers,positions,**kwargs):
        assert active['off'] and layers==[42,44] and positions==[[-1],[-1]]
        return {42:torch.tensor([[[1.,0.]],[[2.,0.]]]),44:torch.tensor([[[3.,0.]],[[4.,0.]]])}
    monkeypatch.setattr(capture,'capture',fake)
    items=[{'id':'a','ids':[1],'feature':'f'},{'id':'b','ids':[2],'feature':'f'}]
    _,rows=capture_and_score(items,[1,0],{'f':{'olens':[['- a','- b'],['second a','second b']],
        'jlens':[['a','b'],['c','d']],'logit':[['a','b'],['c','d']]}},OL(),J(),logit=J())
    lookup={(r['id'],r['reader'],r['layer'],r['arm']):r['scores'][0] for r in rows}
    assert lookup['a','olens',44,'true']==3
    assert lookup['a','olens',44,'mismatched']==4
    assert lookup['b','jlens',44,'mismatched']==3
    assert lookup['a','logit',44,'true']==3
    assert {r['layer'] for r in rows}=={44}
    assert len(rows)==12 and all(len(r['scores'])==2 for r in rows)


def test_sweep_captures_the_six_registered_layers_and_both_arms(monkeypatch):
    import mats.capture as capture
    active={'off':False}
    class OL:
        model=object();tok=SimpleNamespace(pad_token_id=0)
        @contextmanager
        def base(self):
            active['off']=True
            try:yield
            finally:active['off']=False
        def paired_logodds_templates(self,h,layer,pairs):
            assert not active['off']
            return h[:,0].repeat(len(pairs),1)
    def fake(model,seqs,layers,positions,**kwargs):
        assert active['off'] and tuple(layers)==W5_LAYERS
        return {L:torch.tensor([[[float(L)]],[[float(L+1)]]]) for L in layers}
    monkeypatch.setattr(capture,'capture',fake)
    items=[{'id':'a','ids':[1],'feature':'f'},{'id':'b','ids':[2],'feature':'f'}]
    acts,rows=capture_sweep(items,[1,0],{'f':{'olens':[['a','b'],['c','d']]}},OL())
    assert set(acts)==set(W5_LAYERS) and len(rows)==24
    assert {r['layer'] for r in rows}==set(W5_LAYERS)
    assert all(r['reader']=='olens' and len(r['scores'])==2 for r in rows)


def test_ordinal_has_true_arm_only_and_two_frozen_phrasings(monkeypatch):
    import mats.capture as capture
    class OL:
        model=object();tok=SimpleNamespace(pad_token_id=0)
        @contextmanager
        def base(self):yield
        def paired_logodds_templates(self,h,layer,pairs):return h[:,0].repeat(len(pairs),1)
    monkeypatch.setattr(capture,'capture',lambda *a,**k:{L:torch.ones(2,1,2) for L in (42,44)})
    items=[{'id':str(i),'ids':[i+1],'feature':'ordinal'} for i in range(2)]
    _,rows=capture_and_score(items,[None,None],{'ordinal':{'olens':[['deep','shallow'],['many','few']]}},OL(),None)
    assert len(rows)==2 and all(r['arm']=='true' for r in rows)
    with pytest.raises(ValueError,match='two frozen'):
        capture_and_score(items,[None,None],{'ordinal':{'olens':[['a','b']]}},OL(),None)


def test_native_baselines_use_max_token_variants_and_logit_normalizer_cancels():
    from mats.readers.jlens import JLensReader
    class Tok:
        def encode(self,text,**kw):
            value=text.strip().lower();space=text.startswith(' ')
            return [{'a':int(space),'b':2+int(space),'c':1,'d':0}[value]]
    h=torch.tensor([[1.,4.,2.,3.],[-1.,2.,8.,6.]])
    reader=JLensReader(J={44:torch.eye(4)},W_U=torch.eye(4),tok=Tok(),final_norm=torch.nn.LayerNorm(4),device='cpu')
    pairs=[['a','b'],['c','d']]
    result=native_baseline_contrasts(reader,h,44,pairs)
    expected=torch.stack([h[:,:2].max(1).values-h[:,2:].max(1).values,h[:,1]-h[:,0]])
    assert torch.allclose(result,expected) and result.shape==(2,2)
    logit=LogitLens(reader);logp=logit.scores(h,44).log_softmax(-1)
    expected=torch.stack([logp[:,:2].max(1).values-logp[:,2:].max(1).values,logp[:,1]-logp[:,0]])
    assert torch.allclose(native_baseline_contrasts(logit,h,44,pairs),expected)


def test_missing_single_token_variant_preserves_grid_without_baseline_scores(monkeypatch):
    import mats.capture as capture
    from mats.readers.jlens import JLensReader
    class Tok:
        def encode(self,text,**kw):
            return [0,1] if text.strip().lower()=='missing' else [int(text.strip().lower()=='b')]
    class OL:
        model=object();tok=SimpleNamespace(pad_token_id=0)
        @contextmanager
        def base(self):yield
        def paired_logodds_templates(self,h,layer,pairs):return torch.ones(len(pairs),len(h))
    j=JLensReader(J={44:torch.eye(2)},W_U=torch.eye(2),tok=Tok(),final_norm=torch.nn.LayerNorm(2),device='cpu')
    monkeypatch.setattr(capture,'capture',lambda *a,**k:{L:torch.ones(2,1,2) for L in (42,44)})
    items=[{'id':str(i),'ids':[i+1],'feature':'f'} for i in range(2)]
    specs={'f':{'olens':[['a','b'],['x','y']], 'jlens':[['a','b'],['missing','b']], 'logit':[['a','b'],['missing','b']]}}
    _,rows=capture_and_score(items,[1,0],specs,OL(),j,logit=LogitLens(j))
    assert len(rows)==12
    assert all(r['status']=='COMPLETE' and len(r['scores'])==2 for r in rows if r['reader']=='olens')
    assert all(r['status']=='NOT_EVALUABLE_NO_TOKEN_VARIANT' and r['scores'] is None for r in rows if r['reader']!='olens')


def test_logit_lens_uses_target_norm_without_jacobian():
    norm=torch.nn.LayerNorm(2)
    j=SimpleNamespace(W_U=torch.eye(2),final_norm=norm,tok=object(),device='cpu')
    h=torch.tensor([[1.,4.],[-3.,2.]])
    lens=LogitLens(j)
    assert torch.allclose(lens.scores(h,44),norm(h).detach())


def test_unasked_two_free_readouts_and_extraction_failures_preserved():
    class NLA:
        def verbalize_raw(self,h,k,sampling,batch):
            assert k==1
            return [['<explanation>some fact</explanation>'] if sampling.temperature==0 else ['missing tags'] for _ in h]
    items=[{'id':'a'},{'id':'b'}]
    rows=list(collect_unasked(items,torch.ones(2,3),NLA(),42,'nla',UNASKED_POLICY))
    assert len(rows)==4
    assert {(r['id'],r['sample']) for r in rows}=={('a',0),('a',1),('b',0),('b',1)}
    assert [r['status'] for r in rows].count('EXTRACTION_FAILED')==2
    assert all(r['raw']=='missing tags' and r['text'] is None for r in rows if r['sample']==1)


def test_nonfinite_or_single_phrasing_scores_cannot_be_sealed_as_complete():
    items=[{'id':'a'}]
    for values in (torch.ones(1,1),torch.tensor([[float('nan')],[0.]]),torch.ones(2,2)):
        with pytest.raises(ValueError,match='shape/value'):
            _score_rows(items,[0],values,'olens',44,'true','summed_sequence_logodds')


def test_capture_and_completed_score_batches_survive_a_later_timeout(monkeypatch):
    import mats.capture as capture
    persisted={};partial=[]
    class OL:
        model=object();tok=SimpleNamespace(pad_token_id=0)
        calls=0
        @contextmanager
        def base(self):yield
        def paired_logodds_templates(self,h,layer,pairs):
            self.calls+=1
            if self.calls==2:raise TimeoutError('retrieval reserve')
            return torch.ones(2,len(h))
    monkeypatch.setattr(capture,'capture',lambda *a,**k:{L:torch.ones(2,1,2) for L in (42,44)})
    items=[{'id':str(i),'ids':[i+1],'feature':'f'} for i in range(2)]
    with pytest.raises(TimeoutError,match='reserve'):
        capture_and_score(items,[1,0],{'f':{'olens':[['a','b'],['c','d']]}},OL(),None,
            on_capture=lambda h:persisted.update(h),on_scores=lambda r:partial.extend(r))
    assert set(persisted)=={42,44}
    assert len(partial)==2 and all(r['arm']=='true' for r in partial)


def test_free_timeout_preserves_asked_seal_and_does_not_seal_partial_readouts(tmp_path,monkeypatch):
    from projects.g_agreement.blindspot import run as R
    asked=tmp_path/'SCORE_SEAL.json';asked.write_text('existing asked seal')
    monkeypatch.setattr(R,'_decoding',lambda bank:R.UNASKED_POLICY)
    def partial(*args,**kwargs):
        yield {'id':'a','sample':0,'text':'first completed readout'}
        raise TimeoutError('reserve')
    monkeypatch.setattr(R,'collect_unasked',partial)
    args=SimpleNamespace(out=tmp_path,bank=tmp_path/'bank',batch=8)
    with pytest.raises(TimeoutError,match='reserve'):
        R._unasked_file(args,[{'id':'a'}],[('olens',44,object(),torch.ones(1,2))],'target',lambda:None)
    assert asked.read_text()=='existing asked seal'
    assert len((tmp_path/'unasked.target.jsonl').read_text().splitlines())==1
    assert not (tmp_path/'FREE_SEAL.json').exists()


@pytest.mark.parametrize('name',['model','olens','nla','jlens'])
def test_self_consistent_unpinned_assets_are_rejected(tmp_path,monkeypatch,name):
    from projects.g_agreement.blindspot import run as R
    from projects.g_agreement.blindspot import protocol as P
    root=tmp_path/'repo';mp=root/'projects/g_agreement/manifest';mp.mkdir(parents=True)
    files={}
    for key,relative in {'model':'model/tokenizer.json','olens':'olens/adapter_model.safetensors',
            'nla':'nla/av_rl_adapters/iter_000400/adapter_model.safetensors','jlens':'jlens.pt'}.items():
        f=tmp_path/relative;f.parent.mkdir(parents=True,exist_ok=True);f.write_text(key+' fixed bytes');files[key]=f
    pins={'target':{'revision':'model-revision','files_needed':{'tokenizer.json_sha256':P.sha(files['model'])}},
        'readers':{'olens':{'revision':'olens-revision','adapter_model_sha256':P.sha(files['olens'])},
        'nla':{'revision':'nla-revision','adapter':'av_rl_adapters/iter_000400','adapter_model_sha256':P.sha(files['nla'])},
        'jlens':{'revision':'jlens-revision','file_sha256':P.sha(files['jlens'])}}}
    P.dump(mp/'assets.json',pins);monkeypatch.setattr(P,'ROOT',root)
    assets={'model':str(tmp_path/'model'),'olens':str(tmp_path/'olens'),'nla':str(tmp_path/'nla'),
        'jlens':str(files['jlens']),'revisions':{k:k+'-revision' for k in files},
        'files':[{'path':str(f),'sha256':P.sha(f)} for f in files.values()]}
    path=tmp_path/'assets.json';P.dump(path,assets)
    assert R._assets(path,names=(name,))[name]==assets[name]
    files[name].write_text('self consistent but unregistered bytes')
    for item in assets['files']:item['sha256']=P.sha(item['path'])
    P.dump(path,assets)
    with pytest.raises(ValueError,match='registered SHA256'):R._assets(path,names=(name,))


def test_runtime_batch_and_native_oracle_batch_are_frozen(tmp_path):
    from projects.g_agreement.blindspot import run as R
    from projects.g_agreement.blindspot import protocol as P
    P.dump(tmp_path/'runtime.json',P.RUNTIME)
    P.seal(tmp_path,['runtime.json'],'INPUTS_FROZEN')
    assert R._runtime(tmp_path,32)==P.RUNTIME
    with pytest.raises(ValueError,match='--batch differs'):R._runtime(tmp_path,8)
    with pytest.raises(ValueError,match='--batch differs'):R._runtime(tmp_path,True)
    P.dump(tmp_path/'runtime.json',{'batch':32,'oracle_pair_native_batch':16})
    P.seal(tmp_path,['runtime.json'],'INPUTS_FROZEN')
    with pytest.raises(ValueError,match='policy differs'):R._runtime(tmp_path,32)


def test_production_cli_defaults_to_frozen_batch32(monkeypatch):
    from projects.g_agreement.blindspot import run as R
    seen=[];monkeypatch.setattr(R,'target_phase',lambda a:seen.append(a))
    R.main(['target','--assignment','receipt.json','--bank','bank','--assets','assets.json',
        '--out','capture','--asked-only'])
    assert len(seen)==1 and seen[0].batch==32 and seen[0].asked_only


def test_execution_unit_remaps_donors_but_preserves_global_item_indices(monkeypatch,tmp_path):
    from projects.g_agreement.blindspot import run as R
    from projects.g_agreement.blindspot import execution as E
    items=[{'id':str(i),'feature':'f'+str(i//2),'ids':[i+1],'donor_id':str(i^1)} for i in range(8)]
    specs={'f'+str(i):{'kind':'binary'} for i in range(4)}
    binding={'execution_plan_sha256':'a'*64,'execution_unit':'priority'}
    def selected(*args):return {'items':[items[i] for i in (2,3,6,7)],'indices':[2,3,6,7],'binding':binding}
    monkeypatch.setattr(E,'select_unit',selected)
    args=SimpleNamespace(execution_plan=tmp_path/'plan.json',unit='priority',bank=tmp_path)
    subset,donors,templates,indices,got=R._execution_inputs(args,items,[i^1 for i in range(8)],specs)
    assert [it['id'] for it in subset]==['2','3','6','7']
    assert donors==[1,0,3,2] and indices==[2,3,6,7]
    assert set(templates)=={'f1','f3'} and got==binding
    monkeypatch.setattr(E,'select_unit',lambda *a:{'items':[items[i] for i in (6,7,2,3)],'indices':[6,7,2,3],'binding':binding})
    subset,_,templates,indices,_=R._execution_inputs(args,items,[i^1 for i in range(8)],specs)
    assert [it['id'] for it in subset]==['6','7','2','3'] and list(templates)==['f3','f1']
    assert indices==[6,7,2,3]
    monkeypatch.setattr(E,'select_unit',lambda *a:{'items':[items[2]],'indices':[2],'binding':binding})
    with pytest.raises(ValueError,match='donor closure'):R._execution_inputs(args,items,[i^1 for i in range(8)],specs)


def test_unit_unasked_seeds_use_canonical_batch_intersections():
    from projects.g_agreement.blindspot import run as R
    class NLA:
        def verbalize_raw(self,h,k,sampling,batch):return [['<explanation>test fixture</explanation>'] for _ in h]
    indices=[70,31,30,32];items=[{'id':str(i)} for i in indices]
    rows=list(R.collect_unasked(items,torch.ones(4,2),NLA(),42,'nla',R.UNASKED_POLICY,batch=32,canonical_indices=indices))
    assert len(rows)==8
    for row in rows:
        assert row['canonical_index']==int(row['id'])
        assert row['canonical_batch_start']==int(row['id'])//32*32
        assert row['seed']==R.UNASKED_POLICY['seeds'][row['sample']]+row['canonical_batch_start']
    with pytest.raises(ValueError,match='canonical'):
        list(R.collect_unasked(items,torch.ones(4,2),NLA(),42,'nla',R.UNASKED_POLICY,canonical_indices=[30,30,32,70]))


def test_native_scoring_preserves_priority_feature_order(monkeypatch):
    import mats.capture as capture
    calls=[]
    class OL:
        model=object();tok=SimpleNamespace(pad_token_id=0)
        @contextmanager
        def base(self):yield
        def paired_logodds_templates(self,h,layer,pairs):
            calls.append(pairs[0][0]);return torch.ones(len(pairs),len(h))
    monkeypatch.setattr(capture,'capture',lambda *a,**k:{L:torch.ones(4,1,2) for L in (42,44)})
    items=[{'id':str(i),'ids':[i+1],'feature':'z_table' if i<2 else 'a_parenthesis'} for i in range(4)]
    templates={f:{'olens':[[f,'other'],[f+' second','other second']]} for f in ('z_table','a_parenthesis')}
    capture_and_score(items,[1,0,3,2],templates,OL(),None)
    assert calls==['z_table','z_table','a_parenthesis','a_parenthesis']


def test_remainder_on_priority_pod_needs_both_priority_score_seals(tmp_path,monkeypatch):
    from projects.g_agreement.blindspot import run as R
    from projects.g_agreement.blindspot import protocol as P
    from projects.g_agreement.blindspot import execution as E
    a=SimpleNamespace(unit='remainder_a',priority_root=None,bank=tmp_path/'bank',execution_plan=tmp_path/'plan')
    with pytest.raises(ValueError,match='priority-root'):R._require_priority(a,{'execution_units':['priority','remainder_a']})
    assert R._require_priority(a,{'execution_units':['remainder_b']}) is None
    a.bank.mkdir();(a.bank/'INPUT_SEAL.json').write_text('frozen input receipt fixture')
    items=[{'id':str(i),'feature':'f','ids':[i+1],'donor_id':str(i^1)} for i in range(2)]
    P.jsonl(a.bank/'items.input.jsonl',items)
    specs={'f':{'kind':'binary',**{reader:[['a','b'],['c','d']] for reader,_ in R.NATIVE_READERS}}}
    P.dump(a.bank/'templates.json',specs)
    binding={'execution_plan_sha256':'a'*64,'execution_unit':'priority'}
    monkeypatch.setattr(E,'select_unit',lambda *args:{'items':items,'indices':[0,1],'binding':binding})
    monkeypatch.setattr(P,'code_hashes',lambda:{})
    a.priority_root=tmp_path/'priority';target=a.priority_root/'target';nla=a.priority_root/'nla'
    target.mkdir(parents=True);nla.mkdir()
    raw=[{'id':it['id'],'reader':reader,'layer':layer,'arm':arm,'scores':[0.,1.],'status':'COMPLETE'}
        for it in items for reader,layer in R.NATIVE_READERS for arm in ('true','mismatched')]
    for phase,path in [('target',target),('nla',nla)]:
        P.dump(path/'items.order.json',['0','1'])
        P.jsonl(path/f'scores.{phase}.jsonl',[r for r in raw if (r['reader']=='nla')==(phase=='nla')])
        provenance={'input_seal_sha256':P.sha(a.bank/'INPUT_SEAL.json'),'execution':binding,'source_files':{},'experiment':'W1'}
        names=[f'scores.{phase}.jsonl',f'provenance.{phase}.json','items.order.json']
        if phase=='target':
            for L in (42,44):np.save(path/f'acts{L}.npy',np.ones((2,2)))
            names+=['acts42.npy','acts44.npy']
        else:provenance['target_score_seal_sha256']=P.sha(target/'SCORE_SEAL.json')
        P.dump(path/f'provenance.{phase}.json',provenance);P.seal(path,names,'SCORES_SEALED_TEST_FIXTURE')
    receipt=R._require_priority(a,{'execution_units':['priority','remainder_a']})
    assert receipt['target_score_seal_sha256']==P.sha(target/'SCORE_SEAL.json')
    (nla/'scores.nla.jsonl').write_text('')
    P.seal(nla,['scores.nla.jsonl','provenance.nla.json','items.order.json'],'SCORES_SEALED_TEST_FIXTURE')
    with pytest.raises(ValueError,match='score grid'):R._require_priority(a,{'execution_units':['priority','remainder_a']})


def test_w5_requires_full_bank_w1_analysis_not_priority_exports(tmp_path):
    from projects.g_agreement.blindspot import run as R
    from projects.g_agreement.blindspot import protocol as P
    bank=tmp_path/'bank';bank.mkdir();(bank/'INPUT_SEAL.json').write_text('frozen bank test fixture')
    a=SimpleNamespace(bank=bank,w1_analysis=None)
    specs={'f':{'kind':'binary'},'g':{'kind':'binary'}}
    with pytest.raises(ValueError,match='full-bank'):R._require_w1_before_sweep(a,specs)
    root=tmp_path/'analysis';root.mkdir();a.w1_analysis=root
    cells=[{'feature':f,'reader':r,'layer':L} for f in specs for r,L in (*R.NATIVE_READERS,('probe',42),('probe',44))]
    metrics={'experiment':'W1','input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),'w1':{'status':'NOT MET'},'rows':cells}
    def write():
        P.dump(root/'metrics.json',metrics)
        P.dump(root/'ANALYSIS_SEAL.json',{'status':'ANALYSIS_SEALED_AFTER_SCORE_VERIFICATION','files':{'metrics.json':P.sha(root/'metrics.json')}})
    write();assert R._require_w1_before_sweep(a,specs)==P.sha(root/'ANALYSIS_SEAL.json')
    metrics['rows']=cells[:-1];write()
    with pytest.raises(ValueError,match='partial W1'):R._require_w1_before_sweep(a,specs)


def test_grouped_probe_scores_and_opposite_donors():
    groups=np.repeat(np.arange(10),2);y=np.tile([1,0],10)
    h=torch.tensor(np.column_stack([y*2-1,np.zeros(20)]),dtype=torch.float32)
    donors=np.arange(20).reshape(-1,2)[:,::-1].reshape(-1)
    true,mis=probe_scores(h,y,groups,donors)
    from mats.metrics import auroc_labels
    assert auroc_labels(true,y)==1 and auroc_labels(mis,y)==0
    assert np.allclose(mis,true[donors])
    with pytest.raises(ValueError,match='boundaries'):
        probe_scores(h,y,groups,np.roll(donors,2))


def test_whitened_decomposition_sums_back_and_is_metric_orthogonal():
    ruler=SimpleNamespace(w=torch.diag(torch.tensor([2.,1.,.5])))
    delta=torch.tensor([[1.,2.,3.],[-1.,0.,4.]])
    r=torch.tensor([1.,1.,0.])
    component,residual,u=decompose(delta,r,ruler)
    assert torch.allclose(component+residual,delta)
    assert torch.allclose((residual@ruler.w.T)@u,torch.zeros(2),atol=1e-6)
    with pytest.raises(ValueError,match='degenerate'):decompose(delta,torch.zeros(3),ruler)


def test_kl_zero_at_donor_and_positive_away():
    a=torch.tensor([[2.,-1.],[0.,0.]])
    assert torch.allclose(kl_to(a,a),torch.zeros(2))
    assert kl_to(a,torch.zeros_like(a))[0]>0
