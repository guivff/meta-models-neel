import pytest
from .adapter import summarize,select

def row(i,a=True,b=False,o=False):return dict(id=str(i),arm='immediate',hits={44:b,52:b,60:a},outside=o)
def test_exact_gain():
    z=summarize([row(i) for i in range(8)]);assert z['oracle60_minus_outside']['estimate']==1 and z['oracle60_minus_outside']['CI95']==[1,1]
def test_paired_missing_not_zero():
    z=summarize([row(0,o=None),row(1,o=True)]);assert z['outside_hit']['missing']==1 and z['oracle60_minus_outside']['paired']==1 and z['oracle60_minus_outside']['estimate']==0

def test_absent_outside():
    z=summarize([row(0,o=None)]);assert z['outside_hit']['status']=='NOT AVAILABLE' and z['oracle60_minus_outside']['CI95'] is None

def test_same110_selection_excludes_only_missing60():
    xs=[row(0),row(1,a=None),row(2)];allg,g=select(xs,{'0':0,'1':0,'2':1});assert len(allg)==2 and [x['id'] for x in g]==['0']

def test_negative_gain():
    z=summarize([row(i,a=False,o=True) for i in range(5)]);assert z['oracle60_minus_outside']['CI95']==[-1,-1]

def test_no_invented_code():
    with pytest.raises(ValueError):select([row(0,o='yes')],{'0':0})
