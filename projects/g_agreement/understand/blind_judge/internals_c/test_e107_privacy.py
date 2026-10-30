from copy import deepcopy
import pytest
from .e107_privacy import copy_units
from .e109_privacy import raw_evidence_guard


def test_same_scope_candidates_rubrics_and_raw_retained_copy_only():
    data = dict(id='opaque', property='State', values=dict(A='first', B='second'),
                readout='The state is first, saved in /tmp/example/data.')
    units = [dict(id='opaque', kind=k, data=deepcopy(data), rubric=k) for k in ('value', 'old_value')]
    before = deepcopy(units)
    copied, audit, original = copy_units(units)
    assert units == before and audit['bank'] == 'E107' and audit['redacted_records'] == 1
    assert original['opaque'] == data['readout']
    assert all(x['data']['readout'] == 'The state is first, saved in [REDACTED_PATH].' for x in copied)
    assert all(x['data']['values'] == data['values'] and x['rubric'] == x['kind'] for x in copied)


def test_existing_address_copy_and_key_original_evidence_guards():
    unit = dict(id='opaque', kind='value', rubric='fixed', data=dict(id='opaque', property='State',
                values=dict(A='first', B='second'), readout='Endpoint '+'127'+'.0.0.1:9000'))
    copies, audit, raw = copy_units([unit])
    assert copies[0]['data']['readout'] == 'Endpoint [REDACTED_ADDRESS]'
    assert audit['address_authority'] == '25c32f25' and audit['redacted_records'] == 1
    assert raw['opaque'] == unit['data']['readout']
    unit['data']['readout'] = 'sk-'+'or-v1-'+'x'*20
    with pytest.raises(ValueError):copy_units([unit])
    _, guard = raw_evidence_guard(lambda u: ('call', lambda value: None), dict(id='opaque'),
                                  dict(opaque='The state is first.'))
    guard(dict(records=[dict(evidence='state is first')]))
    with pytest.raises(ValueError):
        guard(dict(records=[dict(evidence='[REDACTED_PATH]')]))
