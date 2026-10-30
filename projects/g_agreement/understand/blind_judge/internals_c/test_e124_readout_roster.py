from copy import deepcopy
import json
import pytest
from .e124_readout_roster import merge


def fixture():
    return ([dict(id='a', rendered=dict(user=json.dumps(dict(id='a', context='NEVER_ON_WIRE', readout='Original A'))))],
        [dict(id='a', item_id='itemA', condition='PRIVATE_CONDITION', readout_ref={'original': True})],
        [dict(id='b', context='NEVER_ON_WIRE', readout='Original B')],
        [dict(id='b', item_id='itemB', position=9, original_label_refs={'belief': 'PRIVATE_LABEL'})])


def test_exact_readout_copy_no_context_reference_or_labels_fabricated():
    rows, joins = merge(*fixture())
    assert {x['readout'] for x in rows} == {'Original A', 'Original B'}
    assert all(set(x) == {'id', 'readout'} for x in rows)
    assert 'PRIVATE' not in str(rows) and 'NEVER_ON_WIRE' not in str(rows)
    assert {x['source_set'] for x in joins} == {'E118a', 'E118b'}


@pytest.mark.parametrize('fault', ['missing_a_join', 'missing_b_join', 'wrong_source_id'])
def test_no_partial_or_order_inferred_join(fault):
    a, aj, b, bj = deepcopy(fixture())
    if fault == 'missing_a_join': aj.clear()
    if fault == 'missing_b_join': bj.clear()
    if fault == 'wrong_source_id': aj[0]['id'] = 'wrong'
    with pytest.raises(ValueError): merge(a, aj, b, bj)
