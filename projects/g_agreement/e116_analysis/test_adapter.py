import pytest
from .adapter import classify,analyze


def rates(p,lo):return {b:dict(estimate=p,CI95=[lo,1.]) for b in (52,60)}

def test_strict_baseline_lower_bound():
    assert classify(rates(.8,.66))['R_CH3']=='NOT MET'
    assert classify(rates(.8,.66001))['R_CH3']=='MET'

def test_low_and_missing():
    assert classify(rates(.48,.1))['not_at_read_token_by60'] is True
    assert classify(rates(.48001,.1))['not_at_read_token_by60'] is False
    assert classify({b:dict(estimate=None,CI95=None) for b in (52,60)})['R_CH3']=='NOT EVALUABLE'

def fixture():return [dict(id=f'{arm}{i}',arm=arm,hits={52:True,60:True}) for arm,n in [('immediate',329),('delayed',47)] for i in range(n)]

def test_full_cohort_item_bootstrap():
    r=analyze(fixture());assert r['rules']['R_CH3']=='MET';assert r['bootstrap']['draws']==5000
    assert r['arms']['delayed'][60]['kept']==47

def test_missing_retains_denominator():
    xs=fixture();xs[0]['hits'][52]=None;r=analyze(xs)
    assert r['arms']['immediate'][52]['missing']==1 and r['arms']['immediate'][52]['total']==329

def test_incomplete_duplicate_or_wrong_code_rejected():
    xs=fixture()
    with pytest.raises(ValueError):analyze(xs[:-1])
    with pytest.raises(ValueError):analyze(xs+[xs[0]])
    xs[0]['hits'][52]='yes'
    with pytest.raises((ValueError,TypeError)):analyze(xs)
