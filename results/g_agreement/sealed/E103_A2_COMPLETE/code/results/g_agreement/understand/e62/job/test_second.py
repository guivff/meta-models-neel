import sys,time
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from second_worker import allocation

@pytest.mark.parametrize('experiments',[{'E62','E62P'},{'E59','E63','D4A'}])
def test_all_stage_smoke(tmp_path,experiments):
 from smoke_second import smoke
 smoke(tmp_path/'smoke',experiments)

def test_no_reset_of_prior_or_deadline():
 now=time.time();caps={'E59':7200,'E63':2880,'D4A':1080};a=dict(existing_pod=True,gpu_count=1,caps=caps,prior_custody_seconds=dict.fromkeys(caps,0),pod_created_epoch=now,custody_start_epoch=now,absolute_deadline_epoch=now+sum(caps.values()),provider_deadline_epoch=now+sum(caps.values()))
 allocation(a);a['prior_custody_seconds']['E63']=1
 with pytest.raises(ValueError):allocation(a)
 a['prior_custody_seconds']['E63']=0;a['absolute_deadline_epoch']+=1
 with pytest.raises(ValueError):allocation(a)

def test_ladder_rules_gate_before_correlations():
 from analysis_second import rules62
 probe={f'S{s}_L{i}':.95 for s in range(1,6) for i in range(5)}
 rates={(r,c):{'S':int(c[-1])*.2} for r in ('oracle','nla') for c in probe};j={c:{'J_fraction':int(c[-1])*.2} for c in probe}
 result=rules62(probe,rates,j)
 assert result['readers']['oracle']['R_L1']=='MET' and result['readers']['oracle']['R_L2']=='MET'
 for c in probe:probe[c]=.5
 result=rules62(probe,rates,j)
 assert result['readers']['oracle']['R_L1']=='NOT EVALUABLE'


def test_fresh_pod_rejects_delayed_clock():
 now=time.time();caps={'E62':14000,'E62P':4000};a=dict(fresh_dedicated_pod=True,gpu_count=1,caps=caps,prior_custody_seconds=dict.fromkeys(caps,0),pod_created_epoch=now-100,custody_start_epoch=now,absolute_deadline_epoch=now+sum(caps.values()),provider_deadline_epoch=now+sum(caps.values()))
 with pytest.raises(ValueError):allocation(a)
 a.update(pod_created_epoch=now,existing_pod=True)
 with pytest.raises(ValueError):allocation(a)
