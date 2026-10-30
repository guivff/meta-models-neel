from copy import deepcopy
import numpy as np
import pytest
from . import rules as r


def code(v=(),category=None):
    return dict(id='synthetic',category=category or ('states_value' if v else 'silent'),values=list(v),evidence='x' if v else '')


def item(i,*,stale=True,detect=True,false_alarm=False):
    old=code(('A',));new=code(('B',));silent=code()
    return dict(item_id=str(i),old_value='A',conditions={
        'steered':{'44':old if stale else new,'52':new if detect else old},
        'random':{'44':silent,'52':silent},
        'unhooked':{'44':silent,'52':new if false_alarm else silent}})


def test_exact_value_disagreement_not_correctness_classes():
    assert r.disagreement(code(('A',)),code(('B',)))==1
    assert r.disagreement(code(('A',)),code(('A',)))==0
    assert r.disagreement(code(),code(('A',)))==1
    assert r.disagreement(code(),code((),category='exhibits'))==0
    assert r.disagreement(code(('A','B')),code(('B','A')))==0
    assert r.disagreement(code(('A','B')),code(('A',)))==1


def test_missing_not_no_mention_or_zero():
    missing=code((),category='UNPARSEABLE')
    assert r.disagreement(missing,code()) is None
    assert r.stale(missing,'A') is None
    assert r.stale(code(('A','B')),'A')==0
    with pytest.raises(ValueError):r.values(code(('C',)))
    with pytest.raises(ValueError):r.values(code(('A',),category='silent'))


def test_auc_ties_orientation_and_one_class():
    assert r.auc([1,1],[0,0])==1
    assert r.auc([0],[1])==0
    assert r.auc([1],[1])==.5
    assert r.auc([], [0]) is None
    from sklearn.metrics import roc_auc_score
    p=[0,1,1];n=[0,1]
    assert r.auc(p,n)==pytest.approx(roc_auc_score([1]*3+[0]*2,p+n))


def test_perfect_detector_and_registered_thresholds():
    result=r.summarize([item(i) for i in range(20)],draws=100)
    assert result['R_DIS1']=='MET'
    assert result['AUROC']['estimate']==1 and result['AUROC']['CI95']==[1,1]
    assert result['false_positive_rate']['rate']==0
    assert result['random_direction_control']['AUROC_vs_unhooked']==.5


def test_false_positive_gate_even_high_auc():
    xs=[item(i,false_alarm=i<4) for i in range(20)]
    result=r.summarize(xs,draws=100)
    assert result['AUROC']['estimate']==.9
    assert result['false_positive_rate']['rate']==.2
    assert result['R_DIS1']=='NOT MET'


def test_stale_only_positive_class_and_original_item_bootstrap():
    xs=[item(i,stale=i==0) for i in range(12)]
    result=r.summarize(xs,draws=100)
    assert result['AUROC']['n_stale']==1 and result['AUROC']['n_unhooked']==12
    assert result['bootstrap']['undefined_draws']>0
    assert result==r.summarize(xs,draws=100)
    # Every source item, not each layer/readout, is one resampling unit.
    assert result['n_source_items']==12


def test_missing_denominators_separate_conditions_and_layers():
    xs=[item(i) for i in range(4)];missing=code((),category='UNPARSEABLE')
    xs[0]['conditions']['steered']['52']=missing
    xs[1]['conditions']['unhooked']['44']=missing
    xs[2]['conditions']['random']['52']=missing
    result=r.summarize(xs,draws=50)
    assert result['AUROC']['n_stale']==3 and result['AUROC']['n_unhooked']==3
    assert result['missing']['steered']['stale_score_missing']==1
    assert result['random_direction_control']['disagreement']['n']==3


def test_no_stale_not_evaluable_and_no_implicit_negative():
    xs=[item(i,stale=False) for i in range(3)]
    result=r.summarize(xs,draws=10)
    assert result['R_DIS1']=='NOT EVALUABLE' and result['AUROC']['CI95'] is None
    assert result['bootstrap']['undefined_draws']==10


def test_unchanged_rows_counts_and_duplicate_rejection():
    data={row:[item(i) for i in range(n)] for row,n in r.ROWS.items()}
    result=r.analyze(data,draws=10)
    assert set(result['rows'])==set(r.ROWS)
    assert result['rows']['fact_recall']['n_source_items']==84
    assert result['rows']['language_plan']['n_source_items']==50
    data['language_plan'].pop()
    with pytest.raises(ValueError):r.analyze(data,draws=10)
    with pytest.raises(ValueError):r.summarize([item(1),item(1)],draws=10)


def test_partial_layer_grid_and_changed_conditions_rejected():
    x=item(1);x['conditions']['steered'].pop('52')
    with pytest.raises(ValueError):r.summarize([x],draws=10)
    x=item(1);x['conditions']['extra']=x['conditions']['random']
    with pytest.raises(ValueError):r.summarize([x],draws=10)


def test_registered_inclusive_and_strict_boundaries():
    assert r.disposition(.80,[.700001,.9],.15)=='MET'
    assert r.disposition(.80,[.70,.9],.15)=='NOT MET'
    assert r.disposition(.799999,[.71,.9],.15)=='NOT MET'
    assert r.disposition(.80,[.71,.9],.150001)=='NOT MET'
    assert r.disposition(None,None,.1)=='NOT EVALUABLE'
