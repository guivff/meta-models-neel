from copy import deepcopy
import numpy as np
import pytest
from projects.g_agreement.e105_analysis.rules import statistic
from . import rules as r

ORDER=['hedge','self','stop','formal']


def cells():
    return [dict(id=f'{q}:{g}:{a}',source_id=f'source:{q}:{g}:{a}',quartet_id=q,genre=g,addressed=a,
                 split='dev' if q<50 else 'test') for q in range(150) for g in (0,1) for a in (0,1)]


def native(split='dev', shifts=(1.,2.,-50.,.1), selected=None):
    return [dict(x,scores={c:float(v*x['addressed']) for c,v in zip(ORDER,shifts) if selected is None or c==selected})
            for x in cells() if x['split']==split]


def transplanted(t=1.,s=0.):
    return [dict(x,scores={'T':t,'S':s}) for x in cells() if x['split']=='test' and x['addressed']==0]


def test_signed_dev_only_selection_and_frozen_order_ties():
    assert r.select_dev(native(),ORDER)['selected_contrast_id']=='self'  # not abs(-50)
    tied=native(shifts=(2.,2.,-2.,0.))
    assert r.select_dev(tied,ORDER)['selected_contrast_id']=='hedge'
    with pytest.raises(ValueError):r.select_dev(native('test'),ORDER)


def test_test_does_not_reselect_and_n_is100_quartets():
    rows=native('test',shifts=(500.,2.,-1.,0.),selected='self')
    gate=r.native_test(rows,'self')
    assert gate['R_BEV1']=='MET' and gate['native_addressed_shift']==statistic([2.]*100)
    assert gate['native_addressed_shift']['n']==100 and gate['bootstrap']['unit']=='quartet'
    with pytest.raises(ValueError):r.native_test(native('test'),'self')


def test_genres_are_pooled_within_quartet_before_bootstrap():
    rows=native('test',selected='self')
    for x in rows:
        x['scores']['self']=x['addressed']*(1+(x['quartet_id']-49)*(1 if x['genre']==0 else -1))
    gate=r.native_test(rows,'self')
    assert gate['native_addressed_shift']==statistic([1.]*100)
    assert gate['per_genre']['0']['n']==gate['per_genre']['1']['n']==100


def test_nonpositive_test_gate_prevents_transplant_inference():
    gate=r.native_test(native('test',shifts=(0.,0.,0.,0.),selected='self'),'self')
    assert gate['R_BEV1']=='NOT MET' and gate['transplant_disposition']=='NOT RUN'
    with pytest.raises(ValueError,match='gate'):r.transplant(transplanted(),gate)


def test_paired_delta_and_fraction_recovered_no_donor_sign_switch():
    gate=r.native_test(native('test',selected='self'),'self')
    result=r.transplant(transplanted(t=-1.,s=-2.),gate)
    assert result['R_BEV2']=='MET' and result['delta']==statistic([1.]*100)
    assert result['fraction_recovered']['estimate']==.5
    assert r.transplant(transplanted(t=5.,s=0.),gate)['fraction_recovered']['estimate']==2.5
    zero=r.transplant(transplanted(t=0.,s=0.),gate)
    assert zero['R_BEV2']=='NOT MET' and zero['delta']['CI95'][0]==0 and zero['fraction_recovered']['estimate']==0


def test_exact_grid_no_missing_duplicate_or_nonfinite_coercion():
    rows=native('test',selected='self')
    for kind in ('missing','duplicate','nan'):
        xs=deepcopy(rows)
        if kind=='missing':xs.pop()
        if kind=='duplicate':xs[0]=xs[1]
        if kind=='nan':xs[0]['scores']['self']=float('nan')
        with pytest.raises(ValueError):r.native_test(xs,'self')
    with pytest.raises(ValueError):r.transplant(transplanted()[:-1],r.native_test(rows,'self'))


def test_clarified_same_value_seeded_donors_and_twins():
    xs=cells();pairs=r.same_condition_pairs(xs)
    assert pairs==r.same_condition_pairs(xs) and len(pairs)==200
    by={x['id']:x for x in xs}
    for p in pairs:
        own=by[p['id']];t=by[p['T_donor_id']];s=by[p['S_donor_id']]
        assert t['quartet_id']==own['quartet_id'] and t['genre']==own['genre'] and t['addressed']==1
        assert s['quartet_id']!=own['quartet_id'] and s['genre']==own['genre'] and s['addressed']==1 and s['split']=='test'
    xs[0]['split']='test'
    with pytest.raises(ValueError):r.same_condition_pairs(xs)


def test_exact_frozen_runner_seed_recipe():
    xs=cells();by={(x['quartet_id'],x['genre'],x['addressed']):x for x in xs}
    test=sorted({x['quartet_id'] for x in xs if x['split']=='test'})
    rng=np.random.default_rng(20261030);expected={}
    for genre in (0,1):
        p=[test[k] for k in rng.permutation(len(test))]
        for k,q in enumerate(p):expected[by[q,genre,0]['id']]=by[p[(k+1)%len(p)],genre,1]['id']
    actual={x['id']:x['S_donor_id'] for x in r.same_condition_pairs(xs)}
    assert actual==expected
    assert len(set(actual.values()))==200
