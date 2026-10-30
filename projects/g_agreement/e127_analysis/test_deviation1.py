from copy import deepcopy
from pathlib import Path
import pytest
from . import deviation1 as d, transport as t
from .test_transport import fixture
from .test_rules import records as records127, code
from projects.g_agreement.e128_analysis.test_rules import records as records128


def test_e104_exact_mean_orientation_strict_tie_and_no_greedy_substitution():
    raw=dict(pair_logits=[[7,2],[0,3]],text='unrelated greedy')
    assert d.pair_answer(raw,'A')=='new' and d.pair_answer(raw,'B')=='old'
    assert d.pair_answer(dict(pair_logits=[[1,2],[2,1]]),'A')=='other'
    assert d.pair_answer(None,'A') is None
    for bad in [[],[[1]],[[float('nan'),1]]]:
        with pytest.raises(ValueError):d.pair_answer(dict(pair_logits=bad),'B')
    with pytest.raises(ValueError):d.pair_answer(dict(text='new'),'B')


def test_127_only_flip_source_changes_reader_rates_and_neutral_population_unchanged():
    xs=records127()
    for i,x in enumerate(xs):
        for c,z in x['conditions'].items():
            z['answer']='other';z['pair_answer_deviation1']='new' if c=='context_update' and i<60 else 'old'
    before=deepcopy(xs);r=d.analyze127(xs)
    assert r['flipped_n']==60 and r['R_NAT1']=='MET'
    assert r['flipped_set_rates']['neutral_prefix']['44']['old']['planned_n']==60
    assert xs==before
    xs[0]['conditions']['no_prefix']['pair_answer_deviation1']='other'
    assert d.analyze127(xs)['flipped_n']==59
    for x in xs:x['conditions']['context_update']['oracle'][44]=code(None,'UNPARSEABLE')
    r=d.analyze127(xs);assert r['flipped_n']==59
    assert r['flipped_set_rates']['context_update']['44']['old']['missing_n']==59


@pytest.mark.parametrize('counts,selected', [((42,60,84),2),((41,42,84),4),((41,41,84),8)])
def test_128_same_pair_measure_all_three_doses_and_unchanged_rule(counts,selected):
    xs=records128()
    for i,x in enumerate(xs):
        for j,a in enumerate((2,4,8)):
            for c,z in x['doses'][a].items():z['pair_preference_flip_descriptive']=i<counts[j] if c=='steered' else False
    r=d.analyze128(xs)
    assert r['alpha_min']==selected and r['flip_counts']['8']==84
    assert r['R_DOSE1']==('NOT EVALUABLE' if selected==8 else 'MET')
    assert r['alpha8_pair_logit_reference']['used_for_alpha_min']
    assert r['doses']['8']['flipped_set_rates']['random']['44']['old']['planned_n']==84


def test_128_lowerdose_unknown_not_skipped():
    xs=records128()
    for i,x in enumerate(xs):
        for a in (2,4,8):
            for c,z in x['doses'][a].items():z['pair_preference_flip_descriptive']= i<41 if a==2 else True
    xs[50]['doses'][2]['steered']['pair_preference_flip_descriptive']=None
    r=d.analyze128(xs);assert r['alpha_min'] is None and r['selection_ambiguous']


@pytest.mark.parametrize('experiment',['E127','E128'])
def test_full_sealed_source_deviation_has_separate_guard_and_keeps_greedy_guard(tmp_path,monkeypatch,experiment):
    spec=fixture(tmp_path,monkeypatch,experiment)
    # Real original guard may already be consumed; no reset or conflict.
    old=t.CUSTODY/experiment.lower()/'ANALYSIS_ONCE.json';old.parent.mkdir(parents=True);t.core.write(old,dict(original='immutable'))
    oldbytes=old.read_bytes()
    seal=d.run(spec,experiment,'synthetic')
    result=t.core.read(seal.parent/'RESULTS.json')
    assert result['deviation']==1 and 'deviation 1' in result['analysis_label']
    assert old.read_bytes()==oldbytes
    assert result['flipped_n']==0 if experiment=='E127' else result['alpha_min']==8
    with pytest.raises(ValueError,match='guard consumed'):d.run(spec,experiment,'synthetic')
