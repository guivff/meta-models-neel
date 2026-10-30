import pytest
from .phase236 import unopened_report


def test_owner_pre_judgment_receipt_uses_actual_source_field():
    good=dict(experiment='E118',part='b',e118b_judgments_opened=False,synthetic_tests=12,status='PRE_JUDGMENT')
    unopened_report(good)
    for change in [dict(e118b_judgments_opened=True),dict(synthetic_tests=0),dict(part='a'),dict(status='AFTER_JUDGMENT')]:
        with pytest.raises(ValueError):unopened_report(dict(good,**change))
    with pytest.raises(ValueError):unopened_report(dict(outputs_opened=False,synthetic_tests=12))
