from decimal import Decimal
from projects.g_agreement.e95.judge_pipeline import exposure


def test_accounting_adds_only_remaining_existing_bank_not_another_sixty():
    s=dict(actual_plus_open_caps_usd='100',open_banks={})
    assert exposure(s,'2','.05')==Decimal('157.95')
    s['open_banks']['E95']=dict(cap='60')
    assert exposure(s,'2','.05')==Decimal('100')
