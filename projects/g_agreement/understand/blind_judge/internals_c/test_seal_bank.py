import pytest
from .seal_bank import disposition


def test_release_only_unused_lifetime_cap_not_a_phase_reset():
    assert disposition(6, '0.75', 0) == dict(cap_usd='6', actual_usd='0.75',
        unresolved_reserve_usd='0', unused_allocation_released_usd='5.25', allocation_reset=False)


@pytest.mark.parametrize('actual,unknown', [('0.75', '0.01'), ('6.01', '0'), ('-1', '0'), ('NaN', '0')])
def test_unresolved_invalid_or_overcap_cost_cannot_release(actual, unknown):
    with pytest.raises(ValueError):
        disposition(6, actual, unknown)
