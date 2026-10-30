import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('e110runner',Path(__file__).with_name('e110_dev2_filter_runner227.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def items():return[dict(id=f'{i:032x}',prompt='opaque',input_ids=[1]*(i%19+1),read_position=i%19)for i in range(10917)]
def test_complete_equal_length_once_and_immutable():
 xs=items();before=repr(xs);bs=m.groups(xs);flat=[x for b in bs for x in b];assert len(flat)==len({x['id']for x in flat})==10917 and repr(xs)==before
 assert all(len(b)<=64 and len({len(x['input_ids'])for x in b})==1 for b in bs)
 assert len(bs[0])*len(bs[0][0]['input_ids'])==max(len(b)*len(b[0]['input_ids'])for b in bs)
@pytest.mark.parametrize('change',[lambda x:x.pop(),lambda x:x[0].update(id=x[1]['id']),lambda x:x[0].update(read_position=3),lambda x:x[0].update(truth='private')])
def test_invalid_or_private_inputs_stop(change):
 xs=items();change(xs)
 with pytest.raises(AssertionError):m.groups(xs)
def test_max_profile_margin_and_original_cap():
 d=m.fit(300,[1,3,2],400);assert d['need_seconds']==1860 and d['status']=='NO_FIT'
 assert m.fit(300,[1,3,2],100)['status']=='ADMIT'


def test_amendment_shards_keep_original_sample():
 import json
 root=Path(__file__).resolve().parents[3]
 p=json.loads((root/'results/g_agreement/i2/E110_AMEND1_FROZEN_SHARD_PLAN.json').read_text())
 assert len(p['shards'])==4 and sum(x['candidates']for x in p['shards'])==3000
 assert p['total_projected_custody_seconds']<=10800 and p['old192_outputs_excluded'] is True
 assert all(x['cap_seconds']==2616 for x in p['shards'])

def test_all_shard_public_schema_and_no_duplicate_ids():
 import json
 root=Path(__file__).resolve().parents[3]/'cache/g_agreement/i2/e110_filter_amend1_v1';ids=[]
 for i in range(4):
  xs=json.loads((root/f'shard{i}/PUBLIC_FILTER_INPUTS.json').read_text());bs=m.groups(xs,expected_jobs=len(xs));assert sum(map(len,bs))==len(xs)
  ids.extend(x['id']for x in xs)
 assert len(ids)==len(set(ids))==11706
