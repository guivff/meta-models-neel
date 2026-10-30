import importlib.util
from pathlib import Path
import pytest
P=Path(__file__).with_name('e138_operator250.py')
s=importlib.util.spec_from_file_location('e138_operator',P);op=importlib.util.module_from_spec(s);s.loader.exec_module(op)
def test_elapsed_staging_and_warmup_max_retained():
    f=op.forecast(0,1200,248,{'oracle_setup':1,'native':21},{'oracle_setup':[196.588785],'native':[20.7744475,1]})
    assert f['status']=='ADMIT' and 1161<f['projected_total_cap_seconds']<1162

def test_real_staging_overrun_fails_closed_without_clock_reset():
    f=op.forecast(0,1200,300,{'oracle_setup':1,'native':21},{'oracle_setup':[196.588785],'native':[20.7744475]})
    assert f['status']=='NO_FIT'
def test_missing_phase_measurement_refused():
    with pytest.raises(AssertionError,match='ALL_PENDING_PHASES'):op.forecast(0,1200,0,{'oracle_setup':1},{})
def test_scope_uses_sealed_vectors_and_no_subject_forward():
    text=P.read_text().split('def run(')[1].split('def main')[0]
    assert 'load_base' not in text and 'capture_batch' not in text and 'subject(' not in text
    assert 'len(jobs)==21' in text and 'planned=168' in text and 'runner.oracle_batch(rt,v,44)' in text
