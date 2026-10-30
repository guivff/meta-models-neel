import pytest
from .e121_close import pointers
from .seal_bank import disposition


def test_null_code_kept_as_direct_null_pointer_not_zero():
    rows = [dict(id='opaque', kind='original104', status='UNPARSEABLE', code=None)]
    result = pointers(rows, '/CPU/JUDGMENT_SEAL.json', 'sha', n=1)
    assert result[0]['original_code']['keys'] == [0, 'code']
    assert result[0]['status'] == 'UNPARSEABLE'
    with pytest.raises(ValueError): pointers(rows, '/CPU/seal', 'sha')


def test_incomplete_charge_or_later_cap_overrun_cannot_close():
    with pytest.raises(ValueError): disposition(1, .1, .01)
    with pytest.raises(ValueError): disposition(1, 1.01, 0)
