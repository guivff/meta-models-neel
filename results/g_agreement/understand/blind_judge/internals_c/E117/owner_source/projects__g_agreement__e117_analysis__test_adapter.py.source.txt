import pytest
from .adapter import degenerate,analyze,ROWS,ARMS,ALPHAS,classify

@pytest.mark.parametrize('tokens,expected',[([1,2,1,3],False),([1,1,1,2,3,4],False),([1,1,1,1,2,3,4,5],True),([1,2,1,3,1],True),([],True)])
def test_repetition(tokens,expected):assert degenerate(tokens,'text',False)==expected

def test_empty_and_unparseable():
    assert degenerate([1,2],'',False) and degenerate([1,2],'text',True)

def fixture():return [dict(id=f'{row}{i}',row=row,arms={a:{arm:dict(score=1 if arm=='T' else 0,degenerate=False,norm_ratios=[1.1]) for arm in ARMS} for a in ALPHAS}) for row in ROWS for i in range(84)]

def test_full_grid_rules_and_bootstrap():
    r=analyze(fixture());assert r['rules']['R_IR1']=='MET';assert r['rules']['falsifier']=='NOT MET'
    assert r['rows'][ROWS[0]][1]['T_minus_R']['CI95']==[1.,1.]

def test_pooled_guard_and_descriptive_retention():
    xs=fixture()
    for x in xs[:51]:x['arms'][1]['T']['degenerate']=True
    r=analyze(xs);z=r['rows'][ROWS[0]][1]
    assert z['excluded_degeneracy'] and z['T']['estimate']==1
    assert not r['rows'][ROWS[0]][2]['excluded_degeneracy']

def test_falsifier():
    xs=fixture()
    for x in xs:
        if x['row']!='fact_recall':
            for a in ALPHAS:x['arms'][a]['T']['score']=0
    assert analyze(xs)['rules']['falsifier']=='MET'

def test_exact_grid():
    with pytest.raises(ValueError):analyze(fixture()[:-1])
