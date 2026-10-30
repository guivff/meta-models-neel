import numpy as np
import pytest
from math100 import directions,random_basis,pair_other,manipulation


def test_components_random_rank_and_seed():
    q=random_basis(12,3);assert np.allclose(q.T@q,np.eye(3))
    assert np.array_equal(q,random_basis(12,3))
    x=np.random.default_rng(4).normal(size=(10,12));y=[0]*5+[1]*5
    d,u=directions(x,y,q,np.random.default_rng(20261028))
    assert all(np.isclose(np.linalg.norm(v),1) for v in u.values())
    assert np.allclose(q@(q.T@u['d_perp']),0)
    assert np.isclose(u['r']@d,0)


def test_pairs_only_opposite_and_repeatable():
    ids=list('abcdef');y=[0,1,0,1,0,1];p=pair_other(ids,y)
    assert p==pair_other(ids,y)
    assert all(y[i]!=y[j] and i!=j for i,j in enumerate(p))


def test_probe_shift_matches_standardized_decision_and_flags_without_filtering():
    rng=np.random.default_rng(8);h=rng.normal(size=(4,12));hp=h*2;w=rng.normal(size=12);sd=np.arange(1,13);mu=rng.normal(size=12)
    r=manipulation(h,hp,w,sd,[0,1,0,1])
    expected=((hp-mu)/sd)@w-((h-mu)/sd)@w
    assert np.allclose(r['probe_logit_shift'],expected)
    assert np.allclose(r['target_signed_probe_logit_shift'],expected*[-1,1,-1,1])
    assert r['norm_ratio_above_1_5'].all() and len(r['norm_ratio'])==4
    with pytest.raises(ValueError):manipulation(h,hp*np.nan,w,sd)


def test_token_shared_prefix_and_explicit_differing_token_rules():
    from finalize100 import tokens,MAPPING
    from types import SimpleNamespace
    encoded={' ]':[2205],' ]]]':[2205,4891],'\n    pass':[198,262,1440],'\n            pass':[198,309,1440],' 3':[220,18],' 7':[220,22]}
    class TinyTokenizer:
        def encode(self,s,add_special_tokens=False):return SimpleNamespace(ids=encoded[s],tokens=[str(i) for i in encoded[s]])
        def id_to_token(self,i):return str(i)
        def decode(self,ids,skip_special_tokens=False):return str(ids[0])
    t=TinyTokenizer()
    assert tokens(t,'page_range_digit','not_run')['status']=='NOT_RUN'
    assert [x['token_id'] for x in tokens(t,'indent_level','not_run')['values']]==[262,309]
    assert tokens(t,'nesting_depth','not_run')['status']=='NOT_RUN'
    assert [x['token_id'] for x in tokens(t,'nesting_depth','2205_vs_4891')['values']]==[2205,4891]
