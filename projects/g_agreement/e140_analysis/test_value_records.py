import copy
import itertools
import pytest
from .value_records import preserve_record


def record(values=None, category='states_value', evidence='synthetic'):
    return dict(id='opaque', status='KEPT', code=dict(id='opaque', category=category,
        values=['X'] if values is None else values, evidence=evidence))


@pytest.mark.parametrize('values', [list(v) for n in (1, 2, 3) for v in itertools.combinations(('X', 'Y', 'OTHER'), n)])
def test_preserves_every_asserted_set_without_mutation(values):
    original=record(values); before=copy.deepcopy(original)
    output=preserve_record(original, 'synthetic')
    assert output == original['code'] and original == before
    output['values'].append('mutation')
    assert original == before


@pytest.mark.parametrize('category', ['names_property_without_value', 'exhibits', 'silent'])
def test_preserves_nonstating_categories(category):
    r=record([], category, '' if category == 'silent' else 'synthetic')
    assert preserve_record(r, 'synthetic') == r['code']


def test_null_missing_is_not_observed_none():
    assert preserve_record(dict(id='opaque', status='UNPARSEABLE', code=None), '') is None


@pytest.mark.parametrize('field,value', [('id','wrong'), ('category','unknown'), ('values','X'),
    ('values',['X','X']), ('values',['other']), ('values',[]), ('evidence','absent'), ('evidence','')])
def test_rejects_invalid_code(field,value):
    r=record(); r['code'][field]=value
    with pytest.raises((ValueError,AssertionError)): preserve_record(r,'synthetic')


def test_rejects_missing_with_record_or_nonstating_values():
    r=record();r['status']='UNPARSEABLE'
    with pytest.raises((ValueError,AssertionError)): preserve_record(r,'synthetic')
    with pytest.raises((ValueError,AssertionError)): preserve_record(record(['X'],'exhibits'),'synthetic')
