import importlib.util,math
from pathlib import Path
import pytest
ROOT=Path(__file__).parent
spec=importlib.util.spec_from_file_location('clock',ROOT/'e140_dev3_clock254.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
def test_correct_grouped_complete_forecast_and_explicit_cap():
 f=c.initial();assert f['status']=='ADMIT';assert math.ceil(f['projected_total_cap_seconds'])==9205
 assert c.forecast(248,f['remaining'],c.SEEDS,6600)['status']=='NO_FIT'
def test_original_creation_elapsed_slowdown_fails_without_reset():
 f=c.initial();assert c.forecast(400,f['remaining'],c.SEEDS,9300)['status']=='NO_FIT'
def test_every_pending_phase_has_retained_positive_maximum():
 with pytest.raises(ValueError):c.forecast(0,{'native':1},{},9300)
 m=c.SEEDS.copy();c.retain(m,'native',55);c.retain(m,'native',10);assert m['native']==55
 with pytest.raises(ValueError):c.forecast(0,{},m,9301)
def test_actual_callback_oracle_boundary_preserves_setup():
 for n in (10,28,36):
  assert c.main_remaining(n,n)=={'capture':0,'oracle_setup':1,'native':3*n}
  assert c.main_remaining(n,n+1)=={'capture':0,'oracle_setup':0,'native':3*n}
  assert c.main_remaining(n,4*n)['native']==1
 assert c.screen_remaining(85,0)['generation_post']==84
 assert c.screen_remaining(85,84)['generation_post']==1
