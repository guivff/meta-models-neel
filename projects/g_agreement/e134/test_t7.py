import pytest
from .t7 import stated

def test_t7_original_opaque_values_single_dual_and_missing():
    names={'opaque1':'Alpha','opaque2':'Beta','opaque3':'Gamma'}
    code=lambda v:dict(category='states_value',values=v,evidence='stated')
    assert stated(code(['opaque2']),'stated',names,'Alpha','Beta')=='Beta'
    assert stated(code(['opaque1','opaque2']),'stated',names,'Alpha','Beta') is None
    assert stated(None,'',names,'Alpha','Beta') is None
    assert stated(dict(category='silent',values=[],evidence=''),'',names,'Alpha','Beta') is None
    with pytest.raises(ValueError):stated(code(['new-alias']),'stated',names,'Alpha','Beta')
    with pytest.raises(ValueError):stated(code(['opaque1']),'missing evidence',names,'Alpha','Beta')
    names['OTHER']='__OTHER_EXPLICITLY_NAMED_VALUE__'
    with pytest.raises(ValueError,match='not a scalar identity'):stated(code(['OTHER']),'stated',names,'Alpha','Beta')
    assert stated(code(['opaque1','OTHER']),'stated',names,'Alpha','Beta') is None


def test_t7_other_direct_user_fixed_name_rule():
    from .t7 import other_literal
    names=['Alice','Bob','Erin','Rome']
    assert other_literal('It is by **ALICE** now.',names)=='Alice'
    assert other_literal('Alice then alice',names)=='Alice'
    assert other_literal('Alice and Bob',names) is None
    assert other_literal('Malice Bobcat Rome2',names) is None
    assert other_literal('Eva and Eve',names) is None
    assert other_literal('Eve',['Eva']) is None
    code=dict(category='states_value',values=['OTHER'],evidence='Alice')
    assert stated(code,'Alice',{'OTHER':'sentinel'},'Bob','Erin',names)=='Alice'
    code['values']=['A','OTHER']
    assert stated(code,'Alice',{'A':'Bob','OTHER':'sentinel'},'Bob','Erin',names) is None
