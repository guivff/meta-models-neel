from copy import deepcopy
from decimal import Decimal
import pytest
from . import accounting_e79b as a
from projects.g_agreement.readerbench.io import write


def test_active_separate_e79b_included_once_and_unknown_not_zero(tmp_path,monkeypatch):
    monkeypatch.setattr(a,'SHARED',tmp_path);monkeypatch.setattr(a,'bank_actual',lambda p:(Decimal('.2'),Decimal('.1')))
    root=tmp_path/'E79_ARM_B';root.mkdir();base=dict(open_banks={},open_caps_remaining_usd='4',actual_plus_open_caps_usd='5')
    assert a.add_e79b(deepcopy(base))==base
    write(root/'ADMISSION.json',dict(bank='E79_ARM_B',cap_usd='3',records=672,cap_binding_sha256='fa1911a10694734d45b127d50a043b158e3cb8a887eb1bf77c974222cd80739f'));write(root/'STATUS.json',dict(status='RUNNING'))
    out=a.add_e79b(deepcopy(base));assert out['open_banks']['E79_ARM_B']['open_usd']=='2.7' and out['actual_plus_open_caps_usd']=='7.7'
    assert a.add_e79b(deepcopy(out))==out
