from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from runtime57 import E56
sys.path.insert(0,str(E56))
def test_complete_joint_and_nofit(tmp_path):
 from smoke_joint import smoke_joint
 smoke_joint(tmp_path/'smoke')

def test_prior_custody_and_exact_deadline():
 import pytest
 from admission import validate_allocation
 a=dict(slot=0,gpu_count=1,pod_created_epoch=100,absolute_deadline_epoch=100+5000+3000+3000,allocation_by_slot={'E56':{'0':5000,'1':5000,'2':5000},'E57':{'0':3000,'1':3000,'2':3000},'E61':{'0':3000}},prior_custody_seconds={'E56':3000,'E57':0,'E61':0})
 validate_allocation(a)
 a['prior_custody_seconds']['E56']=3001
 with pytest.raises(Exception):validate_allocation(a)
 a['prior_custody_seconds']['E56']=3000;a['absolute_deadline_epoch']+=1
 with pytest.raises(Exception):validate_allocation(a)
