import pytest
from .analysis import extract,summarize

def rows():
    return [dict(id=f'{g}{a}{i}-{arm}',item_id=f'{g}{a}{i}',genre=g,addressed=a,arm=arm,yes=bool(a) if arm=='targeted' else False) for g in (0,1) for a in (0,1) for i in range(100) for arm in ('targeted','sham')]

@pytest.mark.parametrize('text,expected',[('Yes, because...',True),(' no. absent',False),('Yesterday',None),('I think yes',None),('',None),(None,None)])
def test_extraction(text,expected):assert extract(text) is expected

def test_balanced_accuracy_and_sham_rates():
    z=summarize(rows());assert z['targeted']['balanced_accuracy']==1
    assert z['sham']['balanced_accuracy']==.5 and z['sham']['yes_rate']==0

def test_missing_is_not_no():
    xs=rows();xs[0]['yes']=None
    z=summarize(xs);assert z['targeted']['missing']==1 and z['targeted']['by_addressed'][0]['kept']==199

def test_grid():
    with pytest.raises(ValueError):summarize(rows()[:-1])


def test_clarification_sham_false_positive_and_invalidation():
    from .analysis import readings
    xs=rows();assert readings(summarize(xs))['targeted_reading']=='reporting-priority failure'
    for x in xs:
        if x['arm']=='sham':x['yes']=True
    z=readings(summarize(xs));assert z['sham_invalidates'] and z['targeted_reading']=='INVALIDATED BY SHAM'


def test_cue_yes_bias_and_missing_reading():
    from .analysis import readings
    xs=rows()
    for x in xs:
        if x['arm']=='sham':x['yes']=bool(x['addressed'])
    assert readings(summarize(xs))['cue_driven_yes_bias']
    xs[0]['yes']=None
    assert readings(summarize(xs))['targeted_reading']=='NOT EVALUABLE'


def test_exact_point_two_bias_boundary():
    from .analysis import readings
    summary={'targeted':dict(balanced_accuracy=.75,missing=0),'sham':dict(yes_rate=.5,missing=0,by_addressed={0:dict(rate=.6),1:dict(rate=.6)})}
    assert readings(summary)['cue_driven_yes_bias'] is True
