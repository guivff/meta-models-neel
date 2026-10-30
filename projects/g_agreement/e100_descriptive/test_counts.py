import pytest
from counts import category

@pytest.mark.parametrize('cat,values,target,want', [
    ('states_value',['A'],'A','correct-only'), ('states_value',['A'],'B','wrong-only'),
    ('states_value',['B'],'B','correct-only'), ('states_value',['B'],'A','wrong-only'),
    ('states_value',['A','B'],'A','both'), ('states_value',['B','A'],'B','both'),
    ('names_property_without_value',[],'A','property-only'), ('exhibits',[],'B','exhibits'),
    ('silent',[],'A','silent'), ('UNPARSEABLE',[],'B','missing')])
def test_categories(cat,values,target,want):
    assert category(dict(category=cat, values=values, evidence=''), target) == want

def test_no_invented_category():
    with pytest.raises(KeyError):
        category(dict(category='UNKNOWN', values=[]), 'A')
