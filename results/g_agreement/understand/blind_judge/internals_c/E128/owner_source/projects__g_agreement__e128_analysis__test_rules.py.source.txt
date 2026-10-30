from copy import deepcopy
import pytest
from . import rules as r
from projects.g_agreement.e127_analysis.test_rules import code


def records(counts=(50,60,84)):
    return [dict(item_id=str(i),old_value='A',new_value='B',doses={a:{c:dict(flipped=None if a==8 else (i<counts[j]if c=='steered'else False),oracle={44:code(),52:code('B')})for c in r.CONDITIONS}for j,a in enumerate(r.DOSES)})for i in range(84)]


def test_smallest_dose_and_no_reader_selection():
    xs=records();result=r.analyze(xs)
    assert result['alpha_min']==2 and result['R_DOSE1']=='MET'
    for x in xs:x['doses'][2]['steered']['oracle'][44]=code('B')
    result=r.analyze(xs)
    assert result['alpha_min']==2 and result['R_DOSE1']=='NOT MET'


def test_42_flip_boundary_selects4_without_ci_gate():
    assert r.analyze(records((41,42,84)))['alpha_min']==4
    assert r.analyze(records((42,84,84)))['alpha_min']==2


def test_only8_keeps_strong_steer_caveat():
    result=r.analyze(records((41,41,84)))
    assert result['alpha_min']is None and result['R_DOSE1']=='NOT EVALUABLE'
    assert 'strong-steer caveat'in result['reading']
    assert 'the flip needs α = 8' in result['reading']
    assert result['doses']['8']['behaviour_missing_n']==84 and result['doses']['8']['flipped_n']is None
    assert result['alpha8_pair_logit_reference']['flipped_n']==84
    assert result['alpha8_pair_logit_reference']['used_for_alpha_min']is False


def test_no_qualifying_dose_unknown_not_false_negative():
    result=r.analyze(records((10,20,30)))
    assert result['alpha_min']is None and result['R_DOSE1']=='NOT EVALUABLE'
    xs=records((41,60,84));xs[50]['doses'][2]['steered']['flipped']=None
    result=r.analyze(xs)
    assert result['alpha_min']is None and result['selection_ambiguous']is True


def test_random_control_on_same_selected_steered_cohort():
    xs=records();result=r.analyze(xs)
    assert result['doses']['2']['random_behaviour_flipped_n']==0
    assert result['doses']['2']['flipped_set_rates']['random']['44']['old']['planned_n']==50
    assert result['doses']['2']['flipped_set_rates']['random']['44']['old']['estimate']==1


def test_missing_judgment_never_changes_dose_selection():
    xs=records();xs[0]['doses'][2]['steered']['oracle'][44]=code(None,'UNPARSEABLE')
    result=r.analyze(xs)
    assert result['alpha_min']==2 and result['doses']['2']['flipped_n']==50
    s=result['doses']['2']['flipped_set_rates']['steered']['44']['old'];assert s['missing_n']==1 and s['n']==49


def test_original8_and_same_dose_random_grid_required():
    xs=records();xs[0]['doses'].pop(8)
    with pytest.raises(ValueError):r.analyze(xs)
    xs=records();xs[0]['doses'][2].pop('random')
    with pytest.raises(ValueError):r.analyze(xs)
    with pytest.raises(ValueError):r.analyze(records()[:-1])


def test_alpha8_imputation_rejected_and_missing_lower_dose_not_called_failure():
    xs=records((41,41,84));xs[0]['doses'][8]['steered']['flipped']=True
    with pytest.raises(ValueError,match='never impute'):r.analyze(xs)
    xs=records((41,41,84));xs[50]['doses'][4]['steered']['flipped']=None
    result=r.analyze(xs)
    assert result['selection_ambiguous']is True
    assert 'the flip needs'not in result['reading']
