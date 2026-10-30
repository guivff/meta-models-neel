import pytest
from . import adapter as a

def fixture():
    rows=[dict(id=f'{r}:{k}:{i}',item=str(i),row=r,direction=k,target='A' if i<42 else 'B',score=(0 if k=='J' else 1)) for r in a.ROWS for k in a.CELLS for i in range(84)]
    b={'auroc':{k:{r:.8 for r in a.ROWS} for k in ('none','d_J','d_perp','random')}}
    d={'rows':[dict(arm='B',row=r,cells={'random':{'norm_ratio':1.2}}) for r in a.ROWS]+[dict(arm='A')]}
    return rows,b,d

def test_both_states_and_original_behaviour():
    r=a.analyze(*fixture());assert r['R_C2']=='MET' and r['falsifier']=='NOT MET'
    assert len(r['diagnostics'])==2 and all('random' in x['rates'] for x in r['states'].values())

def test_behaviour_exact_boundary():
    rows,b,d=fixture()
    b['auroc']['d_J']['format_plan']=.7
    assert a.analyze(rows,b,d)['R_C2']=='MET'
    b['auroc']['d_J']['format_plan']=.699
    assert a.analyze(rows,b,d)['R_C2']=='NOT MET'

def test_extra_drop_not_absolute_drop():
    rows,b,d=fixture()
    for x in rows:
        if x['direction']=='nonJ':x['score']=0
    assert a.analyze(rows,b,d)['R_C2']=='NOT MET'

def test_missing_is_not_zero():
    rows,b,d=fixture()
    for x in rows:
        if x['direction']=='J':x['score']=None
    r=a.analyze(rows,b,d);assert r['R_C2']=='NOT EVALUABLE'
    assert r['states']['format_plan']['rates']['J']['UNPARSEABLE']==84

def test_grid_rejects_duplicate_missing_or_target_switch():
    rows,_,_=fixture()
    with pytest.raises(ValueError):a.grid(rows[:-1])
    with pytest.raises(ValueError):a.grid(rows[:-1]+[rows[0]])
    rows[-1]['target']='A'
    with pytest.raises(ValueError):a.grid(rows)

def test_falsifier_both_states():
    rows,b,d=fixture()
    for x in rows:x['score']=1
    assert a.analyze(rows,b,d)['falsifier']=='MET'

def test_ci_zero_does_not_pass(monkeypatch):
    old=a.c.stats
    def stats(x,y=None):
        r=old(x,y)
        if y is not None:r.update(estimate=.3,CI95=[0,.6])
        return r
    monkeypatch.setattr(a.c,'stats',stats)
    assert a.analyze(*fixture())['R_C2']=='NOT MET'

def test_point_boundary_and_seed_backend(monkeypatch):
    old=a.c.stats
    def stats(x,y=None):
        r=old(x,y)
        if y is not None:r.update(estimate=.3,CI95=[.01,.6])
        return r
    monkeypatch.setattr(a.c,'stats',stats)
    assert a.analyze(*fixture())['R_C2']=='MET'
