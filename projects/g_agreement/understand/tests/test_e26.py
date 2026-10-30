import numpy as np
from projects.g_agreement.understand.e26_bank import descriptions,draw_items
from projects.g_agreement.understand.e26_metrics import item_measures,raw_scores,summarize


def test_disjoint_recipients_and_real_donors_with_frozen_balance():
    items=[{'id':f'{s}-{v}-{i}','split':s,'value':v} for s in ('dev','test') for v in ('A','B') for i in range(42)]
    a,b=draw_items(items,['A','B'],np.random.default_rng(20261025))
    assert len(a)==len(b)==80
    assert not {r['id'] for r in a}&{r['id'] for r in b}
    assert all(r['split']=='test' for r in a)
    assert all(sum(r['value']==v for r in pool)==40 for v in ('A','B') for pool in (a,b))
    assert (a,b)==draw_items(list(reversed(items)),['A','B'],np.random.default_rng(20261025))


def test_frames_preserve_payload_and_both_variants():
    result=descriptions([['- inside','- outside'],['- It is inside.','- It is outside.']])
    assert len(result)==16
    assert [r['text'] for r in result[:4]]==['inside','- inside','The cursor is inside.','Note: inside.']
    assert result[10]['text']=='The cursor is It is inside..'
    assert all(sum(r['value']==v for r in result)==8 for v in (0,1))


def test_raw_cosine_matches_E21_with_norms_and_no_whitening():
    from projects.g_agreement.understand.e21_analyse import cosine
    x=np.array([[3.,4.],[-4.,3.],[1.,-2.]])
    h=np.array([[1.,0.],[2.,3.]])
    actual=raw_scores(x,h)
    assert np.array_equal(actual,np.stack([cosine(x,np.repeat(v[None,:],3,axis=0)) for v in h]))


def test_boundary_ties_are_fractional_and_candidate_order_invariant():
    scores=np.array([[9.,8.,7.,6.,5.,4.,3.,2.,1.,1.,1.,1.]])
    category=np.array(['continuation']*8+['description']*4)
    values=np.array([0]*6+[1]*2+[0,0,1,1])
    r=item_measures(scores,category,values,[0])[0]
    assert r['M1']==.6 and r['M3']==.2
    assert r['best_true_description_rank']==10.5
    order=np.arange(12)[::-1]
    assert item_measures(scores[:,order],category[order],values[order],[0])[0]==r


def test_registered_R1_R2_strict_CI_and_rank_direction():
    item={'M1':.7,'M3':0.,'best_true_description_rank':30.,'median_own_continuation_rank':10.}
    r=summarize([item]*80,n_boot=20)
    assert r['R1'] and r['R2'] and r['M2_rank_difference']['estimate']==20
    assert not summarize([{**item,'M1':.64}]*80,n_boot=20)['R1']
    assert not summarize([{**item,'best_true_description_rank':10.}]*80,n_boot=20)['R2']


def test_candidate_categories_not_inferred_from_rank_or_text():
    scores=np.arange(12)[None,:]
    categories=['noise']*8+['description']*2+['continuation']*2
    r=item_measures(scores,categories,[0]*12,[0])[0]
    assert r['M1']==.2 and r['M3']==.2
