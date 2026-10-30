from decimal import Decimal
import pytest
from . import e104_judging as e
from projects.g_agreement.readerbench.io import write

def test_separate_cap_and_source_gate():
    assert e.CAP==Decimal('5') and e.CACHE.name=='E104'
    e.source_gate()

def test_no_eligible_cells_never_exports(monkeypatch,tmp_path):
    from projects.g_agreement.e104_analysis import adapter
    monkeypatch.setattr(e,'source_gate',lambda:None)
    monkeypatch.setattr(e,'CACHE',tmp_path/'E104')
    monkeypatch.setattr(adapter,'inputs',lambda cfg:([],{}))
    p=tmp_path/'spec.json';write(p,dict(blind=str(e.CACHE/'blind'),private=str(e.CACHE/'PRIVATE.json'),judgments=str(e.CACHE/'judgments')))
    with pytest.raises(ValueError,match='no eligible'):e.prepare(p)
    assert not e.CACHE.exists()

def test_private_join_path_fails_before_inputs(monkeypatch,tmp_path):
    monkeypatch.setattr(e,'source_gate',lambda:None)
    p=tmp_path/'spec.json';write(p,dict(blind='/tmp/a',private='/tmp/a/PRIVATE.json',judgments='/tmp/j'))
    with pytest.raises(ValueError,match='paths agree'):e.prepare(p)
