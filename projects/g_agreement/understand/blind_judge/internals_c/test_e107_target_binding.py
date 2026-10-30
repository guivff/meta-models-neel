from copy import deepcopy
import pytest
from .e107_target_binding import target_binding
from .banks import opaque
from ..rubric202 import original_ids


def fixture():
    plans = [dict(inventory_id='%032x' % i, bank='E81', target='truth', property='stated value', values={'A': ['Cedar'], 'B': []}) for i in range(8)]
    units = []
    for p in plans:
        ident = opaque('E107', 'outside_judge', p['inventory_id'], p['target'])
        units.append(dict(id=ident, kind='value', data=dict(id=ident, property=p['property'], values=p['values'], readout='Cedar'), rubric='primary'))
    selected = original_ids([u['id'] for u in units], 'E107')
    units += [dict(u, kind='old_value', rubric='original') for u in units if u['id'] in selected]
    main = [dict(id=u['id'], kind=u['kind']) for u in units if u['kind'] == 'value'][::-1]
    old = [dict(id=u['id'], kind=u['kind']) for u in units if u['kind'] == 'old_value'][::-1]
    return plans, units, main, old


def test_identity_not_order_and_original_same_description():
    plans, units, main, old = fixture()
    result = target_binding(plans, units[::-1], main, old)
    assert len(result) == 10
    for r in result:
        assert r['judgment_id'] == opaque('E107', 'outside_judge', r['inventory_id'], r['target'])
        assert plans[r['plan_index']]['inventory_id'] == r['inventory_id']
    assert all(r['comparison'] == 'same outside description, original E56 rubric' for r in result if r['kind'] == 'old_value')


@pytest.mark.parametrize('fault', ['missing', 'wrong_target', 'changed_original', 'duplicate'])
def test_no_inferred_missing_or_mismatched_source(fault):
    plans, units, main, old = deepcopy(fixture())
    if fault == 'missing': main.pop()
    if fault == 'wrong_target': plans[0]['target'] = 'belief'
    if fault == 'changed_original': units[-1]['data'] = dict(units[-1]['data'], readout='different')
    if fault == 'duplicate': main[0] = main[1]
    with pytest.raises(ValueError):
        target_binding(plans, units, main, old)
