import json
import numpy as np
import pytest
from sklearn.metrics import roc_auc_score
from projects.g_agreement.r_bench import remainder_r2_probe as P,remainder_r2_capture as C


def test_weighted_auc_ties_matches_expanded_samples():
    y=np.array([0,1,0,1,0,1]);s=np.array([.1,.1,.3,.2,.2,.9]);w=np.array([[1,2,0,3,2,1],[3,1,2,1,2,3]])
    expected=[roc_auc_score(np.repeat(y,r),np.repeat(s,r)) for r in w]
    np.testing.assert_allclose(P.weighted_auc(y,s,w),expected)


def test_settings_exclude_heldout_corpus_and_fixed_ties():
    rows=[dict(reader='olens',layer=20,corpus=corp,C=c,auroc=(1 if c==10 else 0) if corp=='held' else .5) for corp in ('held','other') for c in P.GRID]
    assert P.choose_c(rows,'olens',20,'held')==.01
    with pytest.raises(ValueError):P.choose_c(rows[:4],'olens',20,'held')
    y=np.array([0]*5+[1]*5);ids=list(map(str,range(10)));tr,va=P.pool_split(ids,y)
    assert not set(tr)&set(va) and set(tr)|set(va)==set(range(10))


def test_primary_classification_rules_and_small_denominator():
    def row(i,n,t,ic,nc):return {'status':'PASS','metrics':{'internal':{'estimate':i,'wider_ci':ic},'native':{'estimate':n,'wider_ci':nc},'target':{'estimate':t,'wider_ci':[.91,.99]}}}
    assert P.classify(row(.9,.6,.95,[.86,.94],[.55,.65]))=='unverbalised'
    assert P.classify(row(.6,.6,.95,[.5,.7],[.55,.65]))=='never_transmitted'
    assert P.classify(row(.9,.6,.95,[.5,.94],[.55,.65]))=='unclassified'
    assert P.classify(row(.9,.6,.95,None,[.55,.65]))=='unclassified'


def test_complete_probe_pipeline_synthetic_three_banks(tmp_path,monkeypatch):
    monkeypatch.setattr(C,'ROOT',tmp_path);monkeypatch.setattr(C.C,'D_MODEL',4)
    facts=[];banks={};rng=np.random.default_rng(123)
    for bank in C.A.BANKS:
        ds=bank;source=tmp_path/ds;source.mkdir();items=[];n=40;y=np.arange(n)%2
        x=rng.normal(size=(n,4)).astype(np.float16);x[:,0]=y*4-2
        states={}
        for layer in C.READERS.values():
            p=source/f'L{layer}.npy';np.save(p,x);states[str(layer)]={'path':str(p.relative_to(tmp_path)),'sha256':C.sha(p)}
        for i in range(n):
            split='pool' if i<24 else 'test';iid=f'{ds}-{i:03d}'
            item={'dataset':ds,'item_id':iid,'split':split,'label':int(y[i]),'primary':{'sided':'two','candidates':['a','b']}}
            items.append({'item_id':iid,'split':split,'label':int(y[i]),'state_row':i,'donor_item_id':f'{ds}-{i^1:03d}','donor_state_row':i^1,'label_info':{'kind':'construction'},'item':item})
        facts.append({'bank':bank,'dataset':ds,'tag':'TEST','states':states,'items':items});banks[bank]={'sha256':'fixture'}
    m={'facts':facts,'banks':banks,'items':120};meta={'pod':'synthetic-cpu','git_sha':'fixture','code_sha':'fixture'}
    capture=tmp_path/'capture';result=C.capture(m,capture,meta,False,32,None,mock=True)
    assert result['coverage']['arm_cells']==72
    monkeypatch.setattr(C,'provenance',lambda pod:{**meta,'pod':pod})
    output=tmp_path/'probes';result=P.run(m,capture,output,'synthetic-cpu',draws=32)
    assert result['arm_cells']==18 and result['evaluable_cells']==18
    rows=json.loads((output/'per_fact.json').read_text());assert all(set(r['metrics'])==set(P.METRICS) for r in rows)
    assert all(r['metrics']['internal']['estimate']==1 for r in rows)
    inputs=json.loads((output/'inputs.json').read_text())
    assert all(not set(r.get('pool_ids',[]))&set(r.get('test_ids',[])) for r in inputs)
    with pytest.raises(ValueError,match='existing'):P.run(m,capture,output,'synthetic-cpu',draws=32)
