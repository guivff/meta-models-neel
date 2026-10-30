from copy import deepcopy
import pytest
from .e107_dispatch_binding import join_dispatch


def fixture():
    m = [dict(judgment_id=str(i), kind='old_value', inventory_id='item'+str(i), target='truth') for i in range(3)]
    v = [dict(unit=dict(id=str(i), kind='old_value', data={'id': str(i)}), calls=['call'+str(i)]) for i in (2, 0, 1)]
    c = [dict(id='call'+str(i), phase='original') for i in (1, 2, 0)]
    a = [dict(id='call'+str(i), unit_id=str(i), kind='old_value', attempt=0, phase='original', request_id='req'+str(i), response_sha256='sha'+str(i), status='UNPARSEABLE') for i in (1, 0, 2)]
    j = [dict(id=str(i), kind='old_value', attempts=0, request_id='req'+str(i), response_sha256='sha'+str(i), status='UNPARSEABLE') for i in (2, 1, 0)]
    return m, v, c, a, j


def test_original_dispatch_ids_match_after_every_file_is_shuffled():
    rows = join_dispatch(*fixture())
    assert len(rows) == 3
    for row in rows:
        assert row['physical_call_id'] == 'call'+row['judgment_id']
        assert row['request_id'] == 'req'+row['judgment_id']


@pytest.mark.parametrize('fault', ['missing_validation', 'wrong_call', 'wrong_request', 'wrong_response', 'duplicate', 'wrong_kind'])
def test_no_order_fallback_or_invented_dispatch_binding(fault):
    m, v, c, a, j = deepcopy(fixture())
    if fault == 'missing_validation': v.pop()
    if fault == 'wrong_call': v[0]['calls'] = ['call0']
    if fault == 'wrong_request': j[0]['request_id'] = 'different'
    if fault == 'wrong_response': j[0]['response_sha256'] = 'different'
    if fault == 'duplicate': a[0] = a[1]
    if fault == 'wrong_kind': a[0]['kind'] = 'value'
    with pytest.raises(ValueError):
        join_dispatch(m, v, c, a, j)
