from types import SimpleNamespace
import numpy as np
import pytest
from projects.g_agreement.understand import e21 as E, e21_analyse as A


def fixture():
    templates={f:{'values':['A','B'],'olens':[['- A','- B'],['- sentence A.','- sentence B.']]}
               for f in ('paired','fallback')}
    items=[{'id':f'{split}-{f}-{v}-{j}','feature':f,'split':split,'value':v,'cluster':f'{split}-{j}'}
           for split in ('dev','test') for f in templates for v in ('A','B') for j in range(2)]
    cont={r['id']:{'ids':list(range(16)),'text':'raw continuation '+r['id']} for r in items}
    e15={'rows':{'paired':{'pairs':[{'A':')','B':'('},{'A':')\n','B':'(\n'}]}}}
    donors=E.pair_donors([r for r in items if r['split']=='test'])
    return items,templates,cont,e15,donors


def test_assembly_keeps_both_variants_exact_and_real_fallback():
    items,t,c,e,d=fixture(); out=E.assemble(items,t,c,e,d)
    for item in items:
        rr=[r for r in out if r['item']==item['id']]
        if item['split']=='dev':
            assert len(rr)==1 and rr[0]['text']==c[item['id']]['text']
            continue
        side=t[item['feature']]['values'].index(item['value'])
        for arm,offset in [('describe_true',side),('describe_opposite',1-side)]:
            assert [r['text'] for r in rr if r['arm']==arm]==[p[offset] for p in t[item['feature']]['olens']]
        if item['feature']=='paired':
            assert [r['text'] for r in rr if r['arm']=='exhibit_true']==[p['AB'[side]] for p in e['rows']['paired']['pairs']]
            assert len(rr)==8
        else:
            assert next(r['text'] for r in rr if r['arm']=='exhibit_true')==c[item['id']]['text']
            assert next(r['text'] for r in rr if r['arm']=='exhibit_opposite')==c[d[item['id']]]['text']
            assert len(rr)==6
    assert len({r['id'] for r in out})==len(out)


def test_donors_opposite_same_test_row_and_reproducible():
    items,t,c,e,d=fixture(); test=[r for r in items if r['split']=='test']; ix={r['id']:r for r in test}
    assert E.pair_donors(list(reversed(test)))==d
    for k,v in d.items():
        assert ix[k]['feature']==ix[v]['feature'] and ix[k]['value']!=ix[v]['value']


def test_no_prefix_or_generation_fallback_and_exact_16():
    items,t,c,e,d=fixture(); c[items[0]['id']]['ids']=[1]*15
    with pytest.raises(ValueError,match='sixteen'): E.assemble(items,t,c,e,d)


def test_split_guard_rejects_template_or_item_leakage():
    items,t,*_=fixture(); E.check_splits(items,t,count=4)
    bad=[dict(r) for r in items]; bad[-1]['cluster']=bad[0]['cluster']
    with pytest.raises(ValueError,match='leakage'): E.check_splits(bad,t,count=4)
    with pytest.raises(ValueError,match='duplicate'): E.check_splits(items+[items[0]],t,count=4)


def test_probe_fitting_has_only_dev_statistics():
    import torch
    items,t,*_=fixture(); dev=[r for r in items if r['feature']=='paired' and r['split']=='dev']; test=[r for r in items if r['feature']=='paired' and r['split']=='test']
    x=np.array([[2.,3.],[3.,4.],[-2.,-3.],[-3.,-4.]])
    m=A.fit_probe(x,dev,test,'A')
    assert torch.equal(m.mu,torch.as_tensor(x,dtype=torch.float32).mean(0))
    assert m.decision(torch.as_tensor(x)).tolist()[0]>m.decision(torch.as_tensor(x)).tolist()[2]
    with pytest.raises(ValueError,match='dev-only'): A.fit_probe(x,[{**dev[0],'split':'test'},*dev[1:]],test,'A')
    with pytest.raises(ValueError,match='dev-only'): A.fit_probe(x,dev,[{**test[0],'cluster':dev[0]['cluster']},*test[1:]],'A')


def test_cosine_precedes_variant_average():
    records=[{'item':'i','split':'test','arm':a} for a in ('describe_true','describe_true','describe_opposite','exhibit_true','exhibit_opposite')]
    x=np.array([[1.,0.],[0.,100.],[-1.,0.],[1.,1.],[-1.,-1.]])
    got=A.contrasts(records,x,['i'],np.array([[1.,0.]]))['i']
    assert got['describe_true']==.5
    assert got['describe_opposite']==-1
    assert not np.isclose(.5,A.cosine(x[:2].mean(0,keepdims=True),np.array([[1.,0.]]))[0])


def test_exact_ties_half_and_bootstrap_items():
    d=np.array([1.,0.,-2.,3.]); ids=['a','b','c','d']; got=A.reward(d,ids)
    assert got['reward']==.625 and got['ties']==1 and got['n']==4
    from mats.metrics import cluster_bootstrap
    expected=cluster_bootstrap(lambda ix:float(np.array([1.,.5,0.,1.])[ix].mean()),ids,n_boot=2000,seed=20261025)
    assert got['ci95']==list(expected)


def test_zero_norm_is_not_silently_imputed():
    with pytest.raises(ValueError,match='zero norm'): A.cosine(np.zeros((1,3)),np.ones((1,3)))


def test_verified_whitening_formula_and_raw_unchanged():
    x=np.array([[4.,5.],[6.,7.]],dtype=np.float32); old=x.copy(); mu=np.array([1.,2.]); w=np.array([[2.,1.],[1.,3.]])
    assert np.array_equal(A.whiten(x,mu,w),(x-mu)@w.T)
    assert np.array_equal(x,old)


def test_row_bootstrap_primary_and_falsifier():
    x=np.arange(25,dtype=float)
    high=A.correlation(x,x); low=A.correlation(x,-x)
    assert high['held'] and high['ci95'][0]>0
    assert low['rho_falsifier'] and not low['held']
    undefined=A.correlation(np.ones(25),x)
    assert undefined['rho'] is None and not undefined['held']
