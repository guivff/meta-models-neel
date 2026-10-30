import json,time
from pathlib import Path
import numpy as np
import pytest
from projects.g_agreement.e79_extension.runner import original,validate


def grid():
    xs=[]
    for row in ['user_expertise','unit_system']:
        for condition,alpha in [('baseline',0)]+[(d,a)for a in (1,2,4,.25,.5)for d in ('J','nonJ','random')]:
            for j in range(84):
                i=len(xs);xs.append(dict(id=f'{i:032x}',index=i,row=row,arm='A',condition=condition,alpha=alpha,block=44))
    return xs

def test_scope_and_no_labels():
    items=grid();h=np.zeros((2688,5120),np.float32);assert len(validate(items,h))==2688
    for key,value in [('label',1),('arm','B'),('row','nesting_depth')]:
        bad=[dict(x)for x in items];bad[0][key]=value
        with pytest.raises(ValueError):validate(bad,h)


def test_reused_native_loop_no_continuation_or_repeat(tmp_path):
    module,acquire=original();h=np.zeros((2688,5120),np.float32);items=validate(grid(),h)
    class Fake:
        calls=0
        def load_oracle(self):pass
        def native_one(self,reader,v):
            assert reader=='oracle';self.calls+=1
            return [[dict(text='fixture',raw='fixture')]for _ in v]
        def continuation(self,*a):raise AssertionError('No ArmB calls')
    b=Fake();assert acquire(items,h,b,module.Clock(tmp_path,time.time()+600),tmp_path)
    assert b.calls==337 # one discarded synthetic warmup +336 realjobs
    jobs=json.loads((tmp_path/'JOB_GRID.json').read_text());assert len(jobs)==336
    assert all(x['kind']=='native'for x in jobs)
    assert json.loads((tmp_path/'COMPLETED.json').read_text())==list(range(336))
    ids=[]
    for p in sorted((tmp_path/'jobs').glob('*.json')):ids.extend(x['id']for x in json.loads(p.read_text()))
    assert ids==[x['id']for x in items]and len(set(ids))==2688
    assert all(x['phase']!='continuation_warmup_discarded'for x in json.loads((tmp_path/'PHASE_TIMINGS.json').read_text()))
