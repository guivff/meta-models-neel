import pytest
from projects.g_agreement.ops.i5_e98_normalize import combine

def code(i):return dict(id=i,category='silent',values=[],evidence='')
def test_counts_never_get_fake_category():
 j,c=combine([code('a')],[dict(code('b'),source='regex')],[dict(id='c',measurement={'distinct_count':2})],['a','b','c'])
 assert set(j)=={'a','b'} and c=={'c':{'distinct_count':2}}
def test_overlapping_ids_fail():
 with pytest.raises(ValueError):combine([code('a')],[code('a')],[],['a'])
def test_missing_native_fails():
 with pytest.raises(ValueError):combine([code('a')],[],[],['a','b'])
def test_missing_remains_unparseable():
 x=dict(code('a'),category='UNPARSEABLE');j,c=combine([x],[],[],['a']);assert j['a']==x and c=={}
def test_unknown_category_fails():
 x=dict(code('a'),category='count')
 with pytest.raises(ValueError):combine([x],[],[],['a'])
