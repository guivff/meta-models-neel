import sys,importlib.util
from pathlib import Path
import pytest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
spec=importlib.util.spec_from_file_location('supp_worker',HERE/'worker.py');w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
def assignment(existing=True):
 return dict(gpu_count=1,measured_forecast_seconds=2000.1,cap_seconds=7150,daily_budget_verified=True,projected_daily_USD=149,existing_pod=existing,custody_started_epoch=100,pod_created_epoch=100,absolute_deadline_epoch=7250)
def test_existing_and_fresh():
 for existing in (True,False):assert w.custody(assignment(existing),110)==7250
def test_no_reset_or_overrun():
 for changes in ({'cap_seconds':5200},{'cap_seconds':7151},{'cap_seconds':1800},{'absolute_deadline_epoch':2700},{'projected_daily_USD':260.01},{'measured_forecast_seconds':float('nan')}):
  with pytest.raises(ValueError):w.custody(dict(assignment(),**changes),110)
 with pytest.raises(ValueError):w.custody(assignment(),7250)

def test_track_q_gate_and_integrator_check():
 for amount in (200,259.99,260):assert w.custody(dict(assignment(),projected_daily_USD=amount),110)==7250
 for changes in ({'projected_daily_USD':261},{'projected_daily_USD':300},{'daily_budget_verified':False}):
  with pytest.raises(ValueError):w.custody(dict(assignment(),**changes),110)


def test_warmup_synthetic_and_discarded(monkeypatch):
 import numpy as np
 seen=[]
 def native(nla,h,k):seen.append(h.copy());return 'COLD_OUTPUT_MUST_NOT_BE_RETURNED'
 monkeypatch.setattr(w,'native_nla',native)
 assert w.warmup(None) is None
 assert len(seen)==1 and seen[0].shape==(8,5120) and seen[0].dtype==np.float32
 assert np.array_equal(seen[0],np.random.default_rng(20261028).standard_normal((8,5120)).astype(np.float32))
