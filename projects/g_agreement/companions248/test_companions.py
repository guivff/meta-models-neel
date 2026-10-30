import copy
import numpy as np
import pytest
from . import coverage as a,predictors as c

def items():
    return [dict(row='r',item_id=str(i),systems={s:dict(named=int(i%2==0),belief=int(i%4==0),truth=int(i%4==2)) for s in ('oracle','outside')}) for i in range(199)]

def test_identical_paired_outputs_zero():
    r=a.analyze(items(),ceiling())
    for key in ('coverage_difference','unconditional_difference'):
        assert r[key]['observed']['CI95']==[0.,0.]
        assert r[key]['complete_pair']['estimate']==0
    assert r['reading']=='higher precision at lower coverage'
    assert sum(map(sum,r['who_states_belief_2x2']))==199

def test_missing_is_not_abstention_or_zero():
    xs=items();xs[0]['systems']['oracle']=dict(named=None,belief=None,truth=None)
    r=a.analyze(xs,ceiling());q=r['systems']['oracle']
    assert q['missing']==1 and q['abstention']==99
    assert q['unconditional_full199_bounds'][1]-q['unconditional_full199_bounds'][0]==pytest.approx(1/199)
    assert r['table_missing_pairs']==1

def test_precision_and_unconditional_separate():
    xs=items()
    for x in xs:x['systems']['oracle']=dict(named=1,belief=1,truth=0)
    r=a.analyze(xs,ceiling())
    assert r['systems']['oracle']['precision']==1
    assert r['unconditional_difference']['observed']['estimate']>0

def test_all_missing_unknown():
    xs=items()
    for x in xs:
        for s in x['systems']:x['systems'][s]=dict(named=None,belief=None,truth=None)
    r=a.analyze(xs,ceiling())
    assert r['unconditional_difference']['observed']['estimate'] is None
    assert r['systems']['oracle']['unconditional_full199_bounds']==[0.,1.]

@pytest.mark.parametrize('mutation',['duplicate','partial','inconsistent'])
def test_a_rejects(mutation):
    xs=items()
    if mutation=='duplicate':xs[-1]=copy.deepcopy(xs[0])
    if mutation=='partial':xs.pop()
    if mutation=='inconsistent':xs[0]['systems']['oracle']=dict(named=0,belief=1,truth=0)
    with pytest.raises(ValueError):a.analyze(xs,ceiling())

@pytest.mark.parametrize('flips,expected',[
 ({'2':False,'4':True,'6':True,'8':True},4),
 ({'2':False,'4':False,'6':False,'8':True},8),
 ({'2':None,'4':True,'6':True,'8':True},None),
 ({'2':False,'4':False,'6':False,'8':False},None)])
def test_minimum_no_unknown_imputation(flips,expected):assert c.min_dose(flips)[0]==expected

def test_auc_ties_and_direction():
    assert c.auc_ci([0,0,0,0],[0,1,0,1])['estimate']==.5
    assert c.auc_ci([0,1,0,1],[0,1,0,1])['estimate']==1
    assert c.auc_ci([1,0,1,0],[0,1,0,1])['estimate']==0

def test_missing_and_single_class_auc():
    assert c.auc_ci([None,2],[0,0])['estimate'] is None

def test_loo_fixed_two_predictors_and_missing():
    x=[[i,i%3] for i in range(10)]+[[float('nan'),1]];y=[int(i>=5) for i in range(10)]+[1]
    r=c.loo(x,y);assert r['kept']==10 and 0<=r['auroc']<=1
    assert c.loo([[0,0],[1,1],[2,2]],[0,0,1])['auroc'] is None

def test_c_full_grid(monkeypatch):
    monkeypatch.setattr(c,'DRAWS',20)
    rows=[dict(id=str(i),flips={d:i%2==0 or d=='8' for d in c.DOSES},codes={d:{'44':'old' if i%2 else 'new','52_new':True} for d in c.DOSES},unhooked_margin=i,probe_unhooked=i%2,probe_alpha8=i%2) for i in range(84)]
    r=c.analyze(rows)
    assert r['min_dose_by_old44']==[[42,0],[0,42]]
    assert r['original_alpha4_complement_audit']['old44_at8']==42
    assert len(r['PRIVATE_TABLE'])==84
    with pytest.raises(ValueError):c.analyze(rows[:-1])


def ceiling():
    return [dict(row='r',item_id=str(i),answer_value='belief',belief_value='belief',truth_value='truth') for i in range(199)]

def test_truth_and_ceiling_are_distinct_endpoints():
    r=a.analyze(items(),ceiling())
    assert r['systems']['oracle']['truth']['states_truth']==50
    assert r['systems']['same_model_ceiling']['precision']==1
    assert r['systems']['same_model_ceiling']['truth']['precision']==0
    assert r['oracle_minus_same_model_ceiling']['belief']['observed']['estimate']<0
    assert r['outside_defaults_to_truth_clause_eligible'] is False

def test_truth_wording_requires_higher_unconditional_forecast_truth():
    xs=items()
    for x in xs:x['systems']['outside']=dict(named=1,belief=0,truth=1)
    r=a.analyze(xs,ceiling())
    assert r['outside_defaults_to_truth_clause_eligible'] is True
    assert r['truth_unconditional_difference']['observed']['estimate']<0
    assert r['given_value_differences']['truth']['estimate']<0

@pytest.mark.parametrize('change',['partial','wrong_answer','right_belief'])
def test_ceiling_source_join_rejected(change):
    cs=ceiling()
    if change=='partial':cs.pop()
    if change=='wrong_answer':cs[0]['answer_value']='other'
    if change=='right_belief':cs[0]['truth_value']='belief'
    with pytest.raises(ValueError):a.analyze(items(),cs)


def test_truth_dual_presence_and_missing_preserved():
    xs=items();xs[0]['systems']['oracle']=dict(named=1,belief=1,truth=1)
    xs[1]['systems']['outside']=dict(named=None,belief=None,truth=None)
    r=a.analyze(xs,ceiling())
    assert r['systems']['oracle']['truth']['states_truth']==51
    assert r['systems']['outside']['truth']['missing']==1
    assert r['oracle_minus_same_model_ceiling_given_value']['truth']['estimate']>0
    xs[1]['systems']['outside']['truth']=0
    with pytest.raises(ValueError):a.analyze(xs,ceiling())
