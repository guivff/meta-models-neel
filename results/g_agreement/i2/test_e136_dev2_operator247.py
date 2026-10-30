import importlib.util
from pathlib import Path
import pytest
P=Path(__file__).with_name('e136_dev2_operator247.py')
spec=importlib.util.spec_from_file_location('e136_operator',P);op=importlib.util.module_from_spec(spec);spec.loader.exec_module(op)
def test_original_deadline_includes_elapsed_and_reserve():
    x=op.forecast(1000,1100,1020,{'native':2},{'native':[10,15]})
    assert x['projected_total_cap_seconds']==122.5 and x['status']=='NO_FIT'
def test_missing_pending_phase_measurement_fails_before_call():
    with pytest.raises(AssertionError,match='ALL_PENDING_PHASES'):op.forecast(0,1000,0,{'native':1},{})
def test_measured_max_retains_slow_warmup():
    x=op.forecast(0,1000,0,{'native':2},{'native':[100,1,1]})
    assert x['projected_total_cap_seconds']==310

def test_scope_and_literal_forward_contract():
    text=P.read_text();assert op.LAYERS==(44,)
    assert "assert len(xs)==400 and runner.LAYERS==(44,)" in text
    assert "with cm:return runner.capture_batch(model,job)" in text
    assert "runner.oracle_batch(rt,v,44)" in text
    assert "planned=400" in text
