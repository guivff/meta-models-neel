from copy import deepcopy
import pytest
from . import exploratory_note1 as e,rules
from .test_rules import item,code


def cohort():
    return {r:[item(f'{r}-{i}')for i in range(n)]for r,n in rules.ROWS.items()}


def test_frozen35_consensus_requires_original_reader_pair_and_exact_census():
    rows=[dict(item_id=f'fact_recall-{i}',condition=c,reader=r,**{'class':'wrong'if i<35 else'correct'})for i in range(84)for c in ('steered','random')for r in ('oracle','nla')]
    assert e.consensus_ids(rows)=={f'fact_recall-{i}'for i in range(35)}
    rows[0]['class']='no mention'
    with pytest.raises(ValueError,match='35'):e.consensus_ids(rows)
    with pytest.raises(ValueError):e.consensus_ids(rows[:-1])


def test_35_share_wilson_and_later_baseline_all_conditions_same_subset():
    data=cohort();ids={f'fact_recall-{i}'for i in range(35)}
    for x in data['fact_recall']+data['language_plan']:
        for c in ('unhooked','random'):x['conditions'][c]['52']=code(('A',))
    report=e.analyze(data,ids);s=report['false_consensus35']
    assert s['disagreement']['k']==s['disagreement']['n']==35
    assert s['disagreement']['Wilson95'][0]>0.90
    later=report['block52_alone']['same_false_consensus35']['conditions']
    assert all(v['n']==35 and v['rate']==1 for v in later.values())
    assert later['steered']['target']=='new'and later['unhooked']['target']=='old'
    assert all(report[k]['label'].startswith('POST HOC')for k in ('false_consensus35','block52_alone','operating_point'))


def test_missing_not_false_negative_and_original_rule_not_changed():
    data=cohort();ids={f'fact_recall-{i}'for i in range(35)}
    data['fact_recall'][0]['conditions']['steered']['52']=code((),category='UNPARSEABLE')
    before=rules.analyze(data,draws=10);report=e.analyze(data,ids)
    assert report['false_consensus35']['missing_n']==1
    assert report['false_consensus35']['disagreement']['n']==34
    assert report['operating_point']['rows']['fact_recall']['stale_pair_missing_n']==1
    assert before==rules.analyze(data,draws=10)


def test_signal_coverage_precision_and_abstentions_separate():
    xs=[item(i)for i in range(4)]
    xs[0]['conditions']['unhooked']['52']=code(('B',)) # one-value flag, coverage false
    xs[1]['conditions']['unhooked']['52']=code((),category='UNPARSEABLE')
    result=e.operating(xs)
    assert result['sensitivity']['rate']==1
    assert result['unhooked_false_positive_rate']['rate']==pytest.approx(1/3)
    assert result['precision']['rate']==pytest.approx(4/5)
    u=result['coverage']['unhooked']
    assert u['missing_pairs']==1 and u['one_states']==1 and u['neither_states']==2
    assert u['observed_coverage']['n']==4 and u['observed_coverage']['rate']==0
    assert result['FP']==1 # coverage never filters registered one-value disagreement
    assert result['unhooked_missing_n']==1


def test_subset_is_join_not_reselection_and_source_inputs_immutable():
    data=cohort();before=deepcopy(data)
    e.analyze(data,{f'fact_recall-{i}'for i in range(35)})
    assert data==before
    with pytest.raises(ValueError):e.analyze(data,{f'language_plan-{i}'for i in range(35)})
