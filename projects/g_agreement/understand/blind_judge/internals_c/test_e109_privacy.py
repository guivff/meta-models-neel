import pytest
from .e109_privacy import copy_units,raw_evidence_guard


def test_path_copy_preserves_original_and_old_comparison_metadata():
    data=dict(id='a'*32,property='language',values=dict(A='English',B='French'),readout='English text mentions /tmp/example.txt')
    units=[dict(id=data['id'],kind=k,data=data,rubric='exact')for k in ('value','old_value')]
    copied,audit,original=copy_units(units)
    assert all(x['data']['readout']=='English text mentions [REDACTED_PATH]'for x in copied)
    assert units[0]['data']['readout']==original[data['id']]
    assert audit['redacted_records']==1
    assert copied[0]['data']==copied[1]['data']


def test_marker_evidence_cannot_become_a_valid_native_code():
    base=lambda u:({},lambda v:None)
    _,guard=raw_evidence_guard(base,dict(id='opaque'),{'opaque':'English /tmp/example.txt'})
    guard(dict(records=[dict(evidence='English')]))
    with pytest.raises(ValueError):guard(dict(records=[dict(evidence='[REDACTED_PATH]')]))
