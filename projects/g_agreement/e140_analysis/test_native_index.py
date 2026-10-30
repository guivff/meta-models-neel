import copy
import pytest
from .run import native_identity

def fixture():
    return ({'native_index':{'seal_index':0,'member':'main/INDEX.json','keys':[3]},'native':{'seal_index':0,'member':'main/oracle/x.json','keys':[2]}}, {'native_id':'sample-A'}, {'text':'synthetic','raw':'synthetic','malformed':False}, {'id':'sample-A','block':44,'kind':'oracle','member':'oracle/x.json','record':2})

def test_original_index_without_embedded_id():
    p,i,n,x=fixture(); before=copy.deepcopy(n)
    native_identity(p,i,n,44,lambda _:x)
    assert n==before and 'id' not in n

@pytest.mark.parametrize('target,key,value', [('x','id','wrong'),('x','block',52),('x','kind','capture'),('x','record',True),('x','record',-1),('x','member','other.json'),('n','id','wrong'),('np','seal_index',1),('np','keys',[1]),('ip','member','main/OTHER.json')])
def test_reject_mismatched_source_identity(target,key,value):
    p,i,n,x=fixture(); {'x':x,'n':n,'np':p['native'],'ip':p['native_index']}[target][key]=value
    with pytest.raises((ValueError,AssertionError)):native_identity(p,i,n,44,lambda _:x)

def test_legacy_embedded_id_preserved():
    native_identity({}, {'native_id':'old'}, {'id':'old'},44,lambda _:None)
    with pytest.raises((ValueError,AssertionError)):native_identity({}, {'native_id':'old'}, {'id':'different'},44,lambda _:None)
