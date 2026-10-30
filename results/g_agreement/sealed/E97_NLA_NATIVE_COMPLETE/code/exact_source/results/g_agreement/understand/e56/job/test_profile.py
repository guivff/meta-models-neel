import sys,time
from pathlib import Path
import pytest
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from profile_single import profile_deadline,select_dev_units

def test_fresh_creation_clock_cannot_be_reset():
 now=time.time();a=dict(new_pod_allowed=True,gpu_count=1,cap_seconds=1800,pod_created_epoch=now-100,pod_id='fresh',absolute_deadline_epoch=now+1700)
 assert profile_deadline(a)==a['absolute_deadline_epoch']
 for change in ({'absolute_deadline_epoch':now+1800},{'cap_seconds':1801},{'new_pod_allowed':False}):
  with pytest.raises(ValueError):profile_deadline(dict(a,**change))

def test_test_items_rejected_before_model_load():
 items=[dict(id=str(i),feature='x',split='dev') for i in range(9)];cont={'x':{'pairs':[[' a',' b']]}}
 row,units=select_dev_units(items,cont);assert row=='x' and len(units)==8 and all(x['split']=='dev' for x in units)
 with pytest.raises(ValueError):select_dev_units(items+[dict(id='test',feature='x',split='test')],cont)

def test_timings_survive_later_failure(tmp_path):
 import json
 from profile_single import ProfileBudget
 p=tmp_path/'timings.jsonl';b=ProfileBudget(time.time()+1800,p)
 assert b.call('setup',lambda:42)==42
 with pytest.raises(RuntimeError):b.call('later',lambda:(_ for _ in ()).throw(RuntimeError('synthetic')))
 events=[json.loads(x) for x in p.read_text().splitlines()]
 assert [(x['phase'],x['status']) for x in events]==[('setup','started'),('setup','completed'),('later','started'),('later','failed')]
 assert events[1]['elapsed_seconds']>=0

def test_all_stages_tiny_models(tmp_path):
 from smoke_profile import smoke
 proof=smoke(tmp_path/'smoke')
 assert 'oracle_continuation' in proof['all']['phases']
 assert proof['nla_only_synthetic']['loads']==['nla']
