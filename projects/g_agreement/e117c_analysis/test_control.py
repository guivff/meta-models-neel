import pytest
from .analysis import fact_control

def cell(s=.5, sham=.2, tm=0, sm=0):
    return {'targeted_S':{'estimate':s,'missing':tm},'sham_yes':{'rate':sham,'missing':sm}}

def test_positive_boundary():
    x=fact_control(cell());assert x['reading']=='interface works; E120c null is state-specific'
    assert x['robust_to_missingness'] is True

def test_low_boundary():
    assert fact_control(cell(.2,None,0,84))['reading']=='question interface unvalidated'

@pytest.mark.parametrize('s,sham',[(.3,.1),(.5,.21),(.499,.2)])
def test_other_cases(s,sham):
    assert fact_control(cell(s,sham))['reading']=='intermediate; report observed values'

def test_missing_is_unknown():
    assert fact_control(cell(None,None,84,84))['reading']=='NOT EVALUABLE'
    assert fact_control(cell(.6,None,0,84))['reading']=='NOT EVALUABLE'

def test_missing_bounds_do_not_replace_observed_rule():
    x=fact_control(cell(.5,.2,5,5));assert x['reading']=='interface works; E120c null is state-specific'
    assert x['robust_to_missingness'] is False
    assert x['targeted_S_bounds'][0] < .5
    assert x['sham_yes_bounds'][1] > .2
