from copy import deepcopy
import pytest
from .e82_consistency_units import roster


def fixture():
    public = [dict(id='item', prompt='Original prompt', read_positions=[4, 7])]
    joins = [dict(id='group', reader='oracle', source_public_id='item', family='knowledge_cutoff')]
    grouped = [dict(id='group', positions=[dict(position=4, readout='First'), dict(position=7, readout='Second')])]
    native = [dict(unit_id='item', position=7, reader='oracle', text='Second'), dict(unit_id='item', position=4, reader='oracle', text='First')]
    return public, joins, grouped, native


def test_all_positions_literal_context_readout_and_item_identity():
    units, pointers = roster(*fixture())
    assert len(units) == 2 and len({x['item_id'] for x in pointers}) == 1
    assert [x['readout'] for x in units] == ['First', 'Second']
    assert all(set(x) == {'id', 'context', 'readout'} and x['context'] == 'Original prompt' for x in units)
    assert pointers[0]['native_index'] == 1  # Explicit identity join, not source order.


@pytest.mark.parametrize('fault', ['drop_position', 'changed_native', 'duplicate_position', 'extra_native', 'missing_item'])
def test_no_selection_concatenation_or_unbound_source(fault):
    public, joins, grouped, native = deepcopy(fixture())
    if fault == 'drop_position': grouped[0]['positions'].pop()
    if fault == 'changed_native': native[0]['text'] = 'Changed'
    if fault == 'duplicate_position': grouped[0]['positions'][1]['position'] = 4
    if fault == 'extra_native': native.append(dict(unit_id='item', position=9, reader='oracle', text='extra'))
    if fault == 'missing_item': joins.clear()
    with pytest.raises(ValueError): roster(public, joins, grouped, native)
