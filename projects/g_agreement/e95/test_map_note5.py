import copy
import pytest
from projects.g_agreement.e95.test_oracle_only import fixture
from projects.g_agreement.e95.map_note5 import summarize, validate_plan, layer_summary


def test_layer_map_first_mentions_exclude_placebo():
    _, join, codes, plan = fixture()
    for j, c in zip(join, codes):
        j['positions'] = [-1, 0]; c['first_position'] = -1 if j['arm'] == 'real' else 0
    r = summarize(plan, codes, join)['rows'][0]
    assert r['layer_map']['44']['S_layer_minus_placebo'] == 2
    assert r['first_mention_position']['n'] == 3
    assert r['first_mention_by_layer']['44']['counts'] == {'-1': 3}
    assert r['statistics']['D'] == 2


def test_unparseable_stays_missing_not_zero():
    _, join, codes, plan = fixture()
    codes[0].update(category='UNPARSEABLE', values=[], first_position=None)
    r = summarize(plan, codes, join)['rows'][0]['layer_map']['44']
    assert r['real']['kept'] == 2 and r['real']['UNPARSEABLE'] == 1
    assert r['real']['S'] == 1 and r['S_layer_minus_placebo'] == 2


def test_missing_entire_arm_cannot_become_missed():
    _, join, codes, plan = fixture()
    for j, c in zip(join, codes):
        if j['arm'] == 'placebo': c.update(category='UNPARSEABLE', values=[], first_position=None)
    r = summarize(plan, codes, join)
    assert r['rows'][0]['map_verdict'] is None
    assert r['H_M1']['status'] == 'NOT EVALUABLE'
    assert r['rows'][0]['layer_map']['44']['difference_ci95'] is None


def test_maxima_are_separate_not_max_of_differences():
    # Layer1: 1-.5=.5; layer2: .5-(-1)=1.5. Registered D=1-.5=.5.
    cells = {}
    for L, real, plac in [(36, [1, 1], [1, 0]), (44, [1, 0], [-1, -1])]:
        for arm, scores in [('real', real), ('placebo', plac)]:
            cells[('row', 'oracle', arm, L)] = dict(zip(['a', 'b'], scores))
    from projects.g_agreement.e95.oracle_only import row_stat
    assert row_stat(cells, 'row', [36, 44])['D'] == .5
    assert layer_summary(cells, 'row', 'oracle', 44)['S_layer_minus_placebo'] == 1.5


def test_hm1_low_j_counterexample_even_when_agreement_passes():
    _, join, codes, plan = fixture(); plan['rows'][0]['J_fraction'] = .1
    z = summarize(plan, codes, join)
    assert z['H_M1']['agreement_observed'] == 1
    assert z['H_M1']['status'] == 'NOT MET'
    assert z['H_M1']['low_J_counterexamples'] == ['row']


def test_exact_median_not_below_and_missing_j_is_ne():
    _, join, codes, plan = fixture(); plan['rows'][0]['J_fraction'] = plan['E62_median']
    assert summarize(plan, codes, join)['H_M1']['status'] == 'MET'
    plan['rows'][0]['J_fraction'] = None
    assert summarize(plan, codes, join)['H_M1']['status'] == 'NOT EVALUABLE'


def test_nonstatement_and_unacquired_rows_remain_visible():
    _, join, codes, plan = fixture();plan['rows'][0]['statement_score_registered'] = False
    r = copy.deepcopy(plan['rows'][0]);r.update(key='missing',status='NOT RUN',stage='failed',reason='operational')
    plan['rows'].append(r);z=summarize(plan,codes,join)
    assert len(z['rows']) == 2 and z['H_M1']['eligible_rows'] == 0
    assert z['coverage_summary']['not_run_rows'] == 1


def test_nla_complete_coverage_is_separate():
    _, join, codes, plan = fixture();nj=copy.deepcopy(join);nc=copy.deepcopy(codes)
    for x in nj+nc:x['id']='nla-'+x['id']
    for x in nj:x['reader']='nla'
    r=copy.deepcopy(plan['rows'][0]);r.update(reader='nla',stage='nla-stage');plan['rows'].append(r)
    z=summarize(plan,codes+nc,join+nj)
    assert z['NLA']['rows'][0]['statistics']==z['rows'][0]['statistics']
    assert z['NLA']['coverage_summary']['complete_rows']==1
    assert z['NLA']['rows'][0]['first_mention_by_layer']['44']['n'] == 3


@pytest.mark.parametrize('bad',[float('nan'),-1,1.01])
def test_invalid_j_refused(bad):
    _,_,_,plan=fixture();plan['rows'][0]['J_fraction']=bad
    with pytest.raises(ValueError):validate_plan(plan)


def test_first_mention_must_be_achieved_offset():
    _,join,codes,plan=fixture()
    for j in join:j['positions']=[-1,0]
    codes[0]['first_position']=3
    with pytest.raises(ValueError):summarize(plan,codes,join)


def test_partial_group_refused_before_map():
    _,join,codes,plan=fixture()
    with pytest.raises(ValueError):summarize(plan,codes[:-1],join[:-1])


def test_side_binding_rejects_wrong_population_or_fraction():
    from projects.g_agreement.e95.map_note5 import validate_side_bindings
    _,_,_,plan=fixture()
    j=dict(k=16,recipe_authority='synthetic original',source_seals=['sealed'],rows=[dict(reader='oracle',key='row',bank='synthetic',row='row',source='original-hash',fraction=.5)])
    pop=dict(source='original-hash',population_definition='synthetic population',fractions=[.2,.6])
    rules=dict(verdict_rule=plan['verdict_rule'],single_site_verdicts=[dict(reader='oracle',key='row',source='original-hash',verdict='REPORTED')])
    validate_side_bindings(plan,j,pop,rules)
    pop['fractions']=[.1,.3]
    with pytest.raises(ValueError):validate_side_bindings(plan,j,pop,rules)
    pop['fractions']=[.2,.6];j['rows'][0]['fraction']=.7
    with pytest.raises(ValueError):validate_side_bindings(plan,j,pop,rules)


def test_unknown_normalized_code_fails_not_silent_zero():
    _,join,codes,plan=fixture();codes[0]['category']='unknown'
    with pytest.raises(ValueError):summarize(plan,codes,join)
