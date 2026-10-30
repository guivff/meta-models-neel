import pytest
from .e114_intake import make_units


def fixture():
    values = [dict(id=str(i), property='Frozen property', values=dict(A='3', B='4'), gold='CPU_ONLY') for i in range(504)]
    records = [(dict(member='batch.json', keys=[i, 'output', 'text']),
                dict(id=str(i), output=dict(text='The value is 3.', malformed=True))) for i in range(504)]
    return records, values


def test_full_grid_native_text_and_candidate_bytes_unchanged_no_gold_on_wire():
    records, values = fixture()
    units, joins = make_units(records, values, 'fixed original rubric')
    assert len(units) == len(joins) == 504
    assert all(set(x['data']) == {'id', 'property', 'values', 'readout'} for x in units)
    assert all(x['data']['readout'] == 'The value is 3.' for x in units)
    assert 'CPU_ONLY' not in str(units) and all(x['kind'] == 'original57' for x in units)


def test_partial_or_duplicate_native_grid_rejected():
    records, values = fixture()
    with pytest.raises(ValueError):make_units(records[:-1], values, 'fixed')
    with pytest.raises(ValueError):make_units(records[:-1]+[records[0]], values, 'fixed')
