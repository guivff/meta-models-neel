from copy import deepcopy
import pytest
from . import coordinator as c
from .test_rules import records
from projects.g_agreement.e127_analysis.test_rules import code
from projects.g_agreement.e127_analysis.test_transport import fixture
from projects.g_agreement.e127_analysis import transport as t


def pairs(counts=(42,60,84)):
    xs=records()
    for i,x in enumerate(xs):
        for j,a in enumerate((2,4,8)):
            for condition,z in x['doses'][a].items():
                z['pair_preference_flip_descriptive']=i<counts[j] if condition=='steered' else False
                z['flipped']=None if a==8 else False  # greedy disagrees intentionally
    return xs

@pytest.mark.parametrize('counts,selected',[((42,60,84),2),((41,42,84),4),((41,41,84),None)])
def test_selection_pair_only_lower_doses(counts,selected):
    xs=pairs(counts); before=deepcopy(xs);r=c.analyze(xs)
    assert r['alpha_min']==selected and xs==before
    assert r['alpha8_pair_logit_reference']['used_for_alpha_min'] is False
    assert r['doses']['8']['flipped_n']==84
    if selected is None: assert r['R_DOSE1']=='NOT EVALUABLE'

def test_unknown_lower_dose_not_skipped():
    xs=pairs((41,60,84));xs[50]['doses'][2]['steered']['pair_preference_flip_descriptive']=None
    r=c.analyze(xs);assert r['alpha_min'] is None and r['selection_ambiguous']

def test_missing_bound_can_remove_robustness_not_observed_success():
    xs=pairs((42,60,84))
    for i in range(21,42):xs[i]['doses'][2]['steered']['oracle'][44]=code('B')
    xs[20]['doses'][2]['steered']['oracle'][44]=code(None,'UNPARSEABLE')
    r=c.analyze(xs);s=r['doses']['2']['flipped_set_rates']['steered']['44']['old']
    assert s['k']==20 and s['n']==41 and s['missing_n']==1
    assert s['missingness_bounds']['lower']['estimate']==20/42
    assert s['missingness_bounds']['upper']['estimate']==21/42
    assert r['alpha_min']==2 and r['worst_case_R_DOSE1']=='NOT MET'

def test_robustness_at_new52_boundary():
    xs=pairs((50,60,84))
    for i in range(35,50):xs[i]['doses'][2]['steered']['oracle'][52]=code('A')
    xs[34]['doses'][2]['steered']['oracle'][52]=code(None,'UNPARSEABLE')
    r=c.analyze(xs)
    assert r['doses']['2']['flipped_set_rates']['steered']['52']['new']['missingness_bounds']['upper']['estimate']==.70
    assert r['worst_case_R_DOSE1']=='NOT MET'
    xs[34]['doses'][2]['steered']['oracle'][52]=code('B')
    assert c.analyze(xs)['worst_case_R_DOSE1']=='MET'

def test_random_same_cohort_and_all_missing_unknown():
    xs=pairs()
    for x in xs:x['doses'][2]['random']['oracle'][44]=code(None,'UNPARSEABLE')
    r=c.analyze(xs);s=r['doses']['2']['flipped_set_rates']['random']['44']['old']
    assert s['planned_n']==42 and s['estimate'] is None
    assert s['missingness_bounds']['lower']['estimate']==0 and s['missingness_bounds']['upper']['estimate']==1
    assert c.bounds(dict(planned_n=0,k=0,missing_n=0))['lower']['estimate'] is None

def test_full_transport_existing_guard_replay_and_seal(tmp_path,monkeypatch):
    spec=fixture(tmp_path,monkeypatch,'E128')
    seal=c.run(spec,'synthetic'); t.core.verify(seal,t.core.sha(seal))
    assert t.core.read(seal.parent/'RESULTS.json')['alpha_min'] is None
    with pytest.raises(ValueError,match='guard consumed'):c.run(spec,'synthetic')
