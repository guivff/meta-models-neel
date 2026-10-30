import importlib.util
from pathlib import Path
import pytest
spec=importlib.util.spec_from_file_location('e110runner',Path(__file__).with_name('e110_filter_runner223.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
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
 assert m.fit(300,[1,3,2],300)['status']=='ADMIT'
