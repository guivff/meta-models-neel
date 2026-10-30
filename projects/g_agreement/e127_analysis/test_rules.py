from copy import deepcopy
import pytest
from . import rules as r
from .common import rate,criterion


def code(value='A',category=None):
    values=[] if value is None else value if isinstance(value,list) else [value]
    return dict(id='synthetic',category=category or ('states_value'if values else 'silent'),values=values,evidence='x'if values else '')


def records(flips=60):
    return [dict(item_id=str(i),old_value='A',new_value='B',conditions={c:dict(answer='new'if c=='context_update'and i<flips else 'old',oracle={44:code(),52:code('B'),60:code('B')})for c in r.CONDITIONS})for i in range(84)]


def test_native_rule_and_same_flipped_neutral_control():
    xs=records()
    for x in xs[60:]:x['conditions']['neutral_prefix']['oracle'][44]=code('B')
    result=r.analyze(xs)
    assert result['R_NAT1']=='MET'and result['flipped_n']==60
    assert result['flipped_set_rates']['neutral_prefix']['44']['old']['estimate']==1
    assert result['all84_descriptive']['neutral_prefix']['44']['old']['estimate']<.8


def test_flipped_set_requires_context_new_and_no_prefix_old():
    xs=records()
    xs[0]['conditions']['no_prefix']['answer']='new'
    xs[1]['conditions']['context_update']['answer']='other'
    xs[2]['conditions']['no_prefix']['answer']=None
    result=r.analyze(xs)
    assert result['flipped_n']==57 and result['behaviour_unknown_n']==1
    for x in xs:x['conditions']['context_update']['oracle'][44]=code('B')
    assert r.analyze(xs)['flipped_n']==57


def test_low_flip_count_descriptive_only_even_falsifier():
    xs=records(flips=49)
    for x in xs:x['conditions']['context_update']['oracle'][44]=code('B')
    result=r.analyze(xs)
    assert result['R_NAT1']==result['falsifier']=='DESCRIPTIVE ONLY'
    assert result['reading']=='context update did not take'
    assert r.analyze(records(flips=50))['informative']is True


def test_falsifier_current_under_natural_update():
    xs=records()
    for x in xs:x['conditions']['context_update']['oracle'][44]=code('B')
    result=r.analyze(xs)
    assert result['falsifier']=='MET'and result['R_NAT1']=='NOT MET'


def test_neutral_is_primary_gate_not_extra_falsifier_gate():
    xs=records()
    for x in xs:x['conditions']['neutral_prefix']['oracle'][44]=code('B')
    assert r.analyze(xs)['R_NAT1']=='NOT MET'
    for x in xs:x['conditions']['context_update']['oracle'][44]=code('B')
    assert r.analyze(xs)['falsifier']=='MET'


def test_wilson_strict_bounds_and_inclusive_rates():
    s=dict(estimate=.5,Wilson95=[.350001,.7]);assert criterion(s,.5,.35)is True
    s['Wilson95'][0]=.35;assert criterion(s,.5,.35)is False
    assert criterion(dict(estimate=.7,Wilson95=[.1,.9]),.7)is True
    assert criterion(rate([1]*8+[0]*2),.8)is True


def test_missing_not_zero_and_dual_value_not_exclusive():
    xs=records();xs[0]['conditions']['context_update']['oracle'][44]=code(None,'UNPARSEABLE')
    xs[1]['conditions']['context_update']['oracle'][44]=code(['A','B'])
    result=r.analyze(xs)['flipped_set_rates']['context_update']['44']
    assert result['old']['planned_n']==60 and result['old']['n']==59 and result['old']['k']==58 and result['old']['missing_n']==1
    assert result['new']['k']==0


def test_exact_grid_empty_cohort_and_invalid_categories():
    assert r.analyze(records(flips=0))['flipped_set_rates']['context_update']['44']['old']['estimate']is None
    xs=records()
    with pytest.raises(ValueError):r.analyze(xs[:-1])
    with pytest.raises(ValueError):r.analyze(xs[:-1]+[xs[0]])
    xs[0]['conditions'].pop('neutral_prefix')
    with pytest.raises(ValueError):r.analyze(xs)
