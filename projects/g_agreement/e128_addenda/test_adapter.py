from copy import deepcopy
import pytest
from . import adapter as a
from projects.g_agreement.e128_analysis.test_coordinator import pairs
from projects.g_agreement.e127_analysis.test_rules import code

@pytest.mark.parametrize('value,cat,expected', [('A',None,'old'),('B',None,'new'),(['A','B'],None,'dual'),(None,None,'neither_or_unparseable'),(None,'UNPARSEABLE','neither_or_unparseable')])
def test_bins(value,cat,expected):
    assert a.category(code(value,cat),'A','B')==expected

def test_tables_partition_missing_and_random_fixed_cohort():
    xs=pairs((0,42,84)); before=deepcopy(xs)
    xs[0]['doses'][4]['steered']['oracle'][44]=code(None,'UNPARSEABLE')
    r=a.analyze(xs); tab=r['A']['4']['flipped']['steered']['44']
    assert sum(v['k'] for v in tab['categories'].values())==42
    assert tab['unparseable_n']==1 and tab['categories']['old']['n']==42
    assert r['A']['2']['flipped']['random']['44']['planned_n']==0
    assert r['B']['tables']['8']['random']['44']['planned_n']==42
    assert before[1:]==xs[1:]

def test_paired_perfect_difference_and_reordering():
    xs=pairs((0,42,84))
    for x in xs:
        x['doses'][4]['steered']['oracle'][44]=code('B')
        x['doses'][8]['steered']['oracle'][44]=code('A')
    r=a.analyze(xs)
    q=r['B']['differences']['steered']['44']['old']
    assert q==dict(n=42,estimate=1.,CI95=[1.,1.],valid_bootstraps=5000)
    assert a.analyze(list(reversed(xs)))==r

def test_invalid_fixed_cohort_and_missing_behaviour():
    with pytest.raises(ValueError,match='original42'):a.analyze(pairs((0,43,84)))
    xs=pairs((0,42,84));xs[0]['doses'][2]['steered']['pair_preference_flip_descriptive']=None
    with pytest.raises(ValueError,match='complete'):a.analyze(xs)

def test_guard_refuses_before_input_open(tmp_path,monkeypatch):
    monkeypatch.setattr(a.t,'CUSTODY',tmp_path)
    (tmp_path/'e128').mkdir();(tmp_path/'e128'/'ADDENDA243_ONCE.json').write_text('{}')
    with pytest.raises(ValueError,match='guard consumed'):a.run({},'synthetic')

def test_one_open_sealed_output(tmp_path,monkeypatch):
    monkeypatch.setattr(a.t,'CUSTODY',tmp_path)
    monkeypatch.setattr(a.t.core,'verify',lambda *args:{})
    monkeypatch.setattr(a.t,'cohort',lambda *args:([],{},{}))
    seen=[]
    def inputs(*args,**kwargs):
        assert (tmp_path/'e128'/'ADDENDA243_ONCE.json').exists()
        seen.append(1);return pairs((0,42,84))
    monkeypatch.setattr(a.t,'inputs',inputs)
    seal=a.run({'output_sha256':'synthetic'},'synthetic')
    assert seal.exists() and seen==[1]
    with pytest.raises(ValueError,match='guard consumed'):a.run({},'synthetic')
    assert seen==[1]
