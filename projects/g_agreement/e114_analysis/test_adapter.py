import pytest
from projects.g_agreement.e114_analysis import adapter as e

def cells():
    return {(r,'oracle',a):{str(i):1 if a=='stated' else -1 for i in range(84)} for r in e.ROWS for a in e.ARMS}
def old():return {r:dict(estimate=.1,CI95=[0,.2]) for r in e.ROWS}

def test_paired_and_descriptive():
    z=e.analyze(cells(),old());assert z['status']=='DESCRIPTIVE'
    for r in e.ROWS:
        assert z['rows'][r]['stated_minus_opposite']['estimate']==2
        assert z['rows'][r]['stated_minus_opposite']['CI95']==[2,2]
        assert z['rows'][r]['E100_transplant']==old()[r]

@pytest.mark.parametrize('s,t,expected',[(.30,.10,'token-shaped'),(.29,.1,'not met'),(.3,.11,'not met'),(None,.1,'NOT EVALUABLE'),(.3,None,'NOT EVALUABLE')])
def test_readings(s,t,expected):assert expected in e.reading(s,t)

def test_missing_not_zero():
    x=cells();x[(e.ROWS[0],'oracle','stated')]={str(i):None for i in range(84)}
    z=e.analyze(x,old())['rows'][e.ROWS[0]]
    assert z['stated']['kept']==0 and z['stated']['CI95'] is None
    assert z['pre_stated_reading']=='NOT EVALUABLE'
    assert e.analyze(cells(),{r:None for r in e.ROWS})['rows'][e.ROWS[0]]['pre_stated_reading']=='NOT EVALUABLE'

def test_exact_grid():
    x=cells();x.pop(next(iter(x)))
    with pytest.raises(ValueError):e.analyze(x,old())
    x=cells();x[next(iter(x))].pop('0')
    with pytest.raises(ValueError):e.analyze(x,old())

def test_scoring_original_gold_in_both_arms():
    c=dict(id='synthetic',category='states_value',values=['B'],evidence='value B')
    assert e.core.score(c,'A','value B')==-1
    c['values']=['A','B'];assert e.core.score(c,'A','value B')==0
    c.update(category='UNPARSEABLE',values=[],evidence='');assert e.core.score(c,'A','') is None

def test_global_guard(tmp_path):
    assert '/e114/' in str(e.GUARD)
    s=dict(analysis=str(tmp_path/'a'),guard=str(tmp_path/'g'),output_sha256='synthetic')
    e.core.claim(s,'synthetic');s['analysis']=str(tmp_path/'b')
    with pytest.raises(FileExistsError):e.core.claim(s,'synthetic')
