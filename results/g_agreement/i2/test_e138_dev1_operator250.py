import importlib.util
from pathlib import Path
import pytest
p=Path(__file__).with_name('e138_dev1_operator250.py')
s=importlib.util.spec_from_file_location('e138_dev1',p);op=importlib.util.module_from_spec(s);s.loader.exec_module(op)
def test_a1_measured_maximum_full_scope_fits_new_cap():
 f=op.forecast(0,2006,248,{'oracle_setup':1,'native':21},{'oracle_setup':[196.58878472691868],'native':[42.705082369968295]})
 assert f['status']=='ADMIT' and f['projected_total_cap_seconds']<2006
 assert op.forecast(0,1200,248,{'oracle_setup':1,'native':21},{'oracle_setup':[196.58878472691868],'native':[42.705082369968295]})['status']=='NO_FIT'
def test_measured_slowdown_still_stops_without_clock_reset():
 assert op.forecast(0,2006,700,{'native':20},{'native':[60]})['status']=='NO_FIT'
def test_missing_phase_refused():
 with pytest.raises(AssertionError,match='ALL_PENDING_PHASES'):op.forecast(0,2006,0,{'oracle_setup':1},{})
def test_original_science_worklist_unchanged():
 run=p.read_text().split('def run(')[1].split('def main')[0]
 original=p.with_name('e138_operator250.py').read_text().split('def run(')[1].split('def main')[0]
 assert run==original
