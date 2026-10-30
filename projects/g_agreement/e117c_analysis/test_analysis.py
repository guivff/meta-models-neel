import pytest
from . import analysis as a
from . import adapter


def fixture():
    return [dict(id=f'{r}:{i}',row=r,arms={'targeted':{'score':1 if i<42 else -1,'yes':None},'sham':{'score':0,'yes':i<16}})for r in a.ROWS for i in range(84)]


def test_signed_score_not_accuracy():
    out=a.summarize(fixture())
    for r in a.ROWS:
        assert out['rows'][r]['targeted_S']['estimate']==0
        assert out['rows'][r]['sham_yes']['rate']==16/84
    assert out['rows']['fact_recall']['role']=='control'
    assert out['bootstrap']==dict(draws=2000,seed=20261027,unit='original item',source='unchanged E100/E57 signed-score bootstrap')


def test_original_extraction_no_search_or_numeric_guess():
    assert a.extract(' YES, absent') is True
    assert a.extract('No.') is False
    assert a.extract('4. The depth is four.') is None
    assert a.extract('The answer is yes.') is None
    assert a.extract('yesterday') is None


def test_unknown_never_no():
    items=fixture();items[0]['arms']['sham']['yes']=None;items[0]['arms']['targeted']['score']=None
    out=a.summarize(items)['rows'][a.ROWS[0]]
    assert out['sham_yes']['kept']==83 and out['sham_yes']['missing']==1
    assert out['targeted_S']['kept']==83 and out['targeted_S']['missing']==1


def test_full_census_no_dropped_or_duplicate_items():
    items=fixture()
    with pytest.raises(ValueError):a.summarize(items[:-1])
    with pytest.raises(ValueError):a.summarize(items[:-1]+[items[0]])


def test_arm_and_row_scope_enforced():
    items=fixture();items[0]['arms'].pop('sham')
    with pytest.raises(ValueError):a.summarize(items)
    items=fixture();items[0]['row']='unregistered'
    with pytest.raises(ValueError):a.summarize(items)


def test_control_does_not_change_bookkeeping_sham_summary():
    items=fixture()
    for x in items:
        if x['row']=='fact_recall':x['arms']['sham']['yes']=True
    out=a.summarize(items)
    assert out['sham_pooled_bookkeeping']['rate']==16/84
    assert out['sham_pooled_all']['rate']>(16/84)


def test_no_fractional_signed_score():
    items=fixture();items[0]['arms']['targeted']['score']=.5
    with pytest.raises(ValueError):a.summarize(items)



def summary(targets=(.30,.30,.0),shams=(.20,.20,.0)):
    return {'rows':{r:dict(targeted_S=dict(estimate=targets[i] if i<3 else 1.,missing=0,CI95=[-1,1]),sham_yes=dict(rate=shams[i] if i<3 else 1.,missing=0))for i,r in enumerate(a.ROWS)}}


def test_rowwise_inclusive_boundaries_no_ci_gate():
    out=a.readings(summary())
    assert out['elicitation']=='MET' and out['qualifying_bookkeeping_rows']==list(a.BOOK[:2])


def test_low_pooled_sham_cannot_rescue_bad_qualifying_row():
    out=a.readings(summary(shams=(.21,0,0)))
    assert out['elicitation']=='NOT MET'


def test_control_and_nonqualifying_sham_do_not_disqualify():
    assert a.readings(summary(shams=(.2,.2,1)))['elicitation']=='MET'


def test_negative_requires_all_three_at_inclusive_boundary():
    assert a.readings(summary(targets=(.1,.1,.1),shams=(1,1,1)))['not_recoverable_by_asking']=='MET'
    assert a.readings(summary(targets=(.1,.1,.10001)))['not_recoverable_by_asking']=='NOT MET'


def test_unknown_row_not_imputed_or_pooled():
    s=summary();s['rows'][a.BOOK[0]]['sham_yes'].update(rate=None,missing=84)
    assert a.readings(s)['elicitation']=='NOT EVALUABLE'
    s=summary();s['rows'][a.BOOK[2]]['targeted_S'].update(estimate=None,missing=84)
    assert a.readings(s)['elicitation']=='MET'


def test_fewer_than_79_in_either_arm_is_unevaluable():
    s=summary();s['rows'][a.BOOK[0]]['sham_yes'].update(rate=None,missing=84)
    s['rows'][a.BOOK[0]]['targeted_S']['estimate']=.1
    assert a.readings(s)['elicitation']=='NOT EVALUABLE'


def test_79_observed_boundary_and_worst_signed_score():
    s=summary(targets=(.31,.31,0),shams=(.2,.2,0))
    for row in a.BOOK[:2]:
        s['rows'][row]['targeted_S']['missing']=5
        s['rows'][row]['sham_yes']['missing']=5
    r=a.readings(s)
    assert r['elicitation']=='MET'
    assert r['elicitation_missingness']=='met, not robust to missingness'
    bound=r['missingness_bounds'][a.BOOK[0]]
    assert bound['targeted_S_worst']==pytest.approx((.31*79-5)/84)
    assert bound['sham_yes_worst']==pytest.approx((.2*79+5)/84)
    s['rows'][a.BOOK[0]]['targeted_S']['missing']=6
    assert a.readings(s)['elicitation']=='NOT EVALUABLE'


def test_83_observed_strong_effect_remains_robust():
    s=summary(targets=(1,1,1),shams=(0,0,0))
    for row in a.BOOK:s['rows'][row]['targeted_S']['missing']=1
    r=a.readings(s)
    assert r['elicitation']=='MET' and r['not_robust_bookkeeping_rows']==[]
    assert r['missingness_bounds'][a.BOOK[0]]['targeted_S_worst']==82/84
