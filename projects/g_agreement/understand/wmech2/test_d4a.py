import pytest
from . import d4a as a

def fixture():
    return [dict(id=f'{r}:{c}:{arm}:{i}',reader=r,row=c,arm=arm,pair=f'{c}:{i}',
                 probability=.9,text=c if arm in ('think','mention','none','cross') else '')
            for r in ('oracle','nla') for c in a.CONCEPTS for arm in a.ARMS for i in range(42)]

def test_d4a_pairs_rules_and_ratios():
    rows=fixture();a.validate(rows);lex={c:[c] for c in a.CONCEPTS};probes={c:{arm:1 for arm in a.ARMS} for c in a.CONCEPTS}
    v=a.evaluate(rows,lex,probes);assert all(x['R_W2']=='MET' for x in v['readers'].values())
    assert v['readers']['oracle']['concepts']['birds']['base_ignore_over_none']['CI95']==[1,1]
    for x in rows:
        if x['arm']=='ignore':x['probability']=.1
        x['text']=''
    v=a.evaluate(rows,lex,probes);assert v['readers']['oracle']['R_W2']=='NOT MET'
    assert a.ratio({'x':0},{'x':0})['CI95'] is None
    with pytest.raises(ValueError):a.validate(rows[:-1])

def test_unknown_not_silent_success():
    rows=fixture()
    for x in rows:x['text']=''
    v=a.evaluate(rows,{c:[c] for c in a.CONCEPTS},{c:{arm:1 for arm in a.ARMS} for c in a.CONCEPTS})
    assert v['readers']['oracle']['R_W2']=='NOT EVALUABLE'
