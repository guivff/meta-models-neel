import json,time
import numpy as np
import pytest
from projects.g_agreement.e101.test_e101 import Tiny
from projects.g_agreement.e101.materialize import compose
from projects.g_agreement.e101.contract import select
from projects.g_agreement.e101.runner import acquire,dependencies
from projects.g_agreement.e101.timing import profile_receipt,admit


def test_independent_test_doses_and_commit_barrier(monkeypatch):
    from projects.g_agreement.e101 import materialize
    rows=['language_plan','format_plan','fact_recall','language_continuation','nesting_depth','indent_level','page_range_digit']
    doses={f'{r}:{b}':dict(alpha=(1. if b==44 else 2.) if r=='format_plan' else None) for r in rows for b in (42,44)}
    receipt=dict(experiment='E101',dev_count=84,dose_policy='independent_blocks',scoring_mode='continuation',selected_doses=doses)
    monkeypatch.setattr(materialize,'committed_dose',lambda *a:receipt)
    records=[dict(id=str(i),row='format_plan',split='test',ids=[1],candidate_ids=[[[2],[3]]],label=i%2,contrast_target_sign=1) for i in range(84)]
    u=np.zeros(5120);u[0]=1
    carriers={('format_plan',b):{str(i):np.ones(5120) for i in range(84)} for b in (42,44)}
    ds={('format_plan',b):u for b in (42,44)}
    xs,h,_,selected=compose(records,carriers,ds,{k:2. for k in ds},{42:u,44:u},'test',ruling_commit='takeover')
    assert len(xs)==336 and {x['alpha'] for x in xs}=={1.,2.}
    assert selected['format_plan:42']['alpha']==2. and selected['format_plan:44']['alpha']==1.


def test_timing_excludes_warmup_and_caps(tmp_path):
    from projects.g_agreement.e101.contract import write,sha
    profile=profile_receipt([dict(phase='base_setup',seconds=2),dict(phase='text_warmup_discarded',seconds=5)],
        [dict(phase='text',jobs=10,sample_seconds=[1,2,3],mean_job_seconds=2)])
    profile.update(input_sha256='i',source_sha256='s',gpu_type='H200',staging_seconds=1)
    profile['total_seconds_with_margin']=1.25*(7+20+1+60)
    p=tmp_path/'p.json';write(p,profile)
    a=dict(profile_sha256=sha(p),gpu_type='H200',cap_seconds=110)
    admit(p,a,'i','s')
    with pytest.raises(ValueError):admit(p,dict(a,cap_seconds=111),'i','s')
    with pytest.raises(ValueError):admit(p,a,'wrong','s')


def test_serial_baseline_exact_count_and_no_adapter(tmp_path):
    from projects.g_agreement.e101.text_baseline import acquire as text_acquire
    old,_,_,_,_=dependencies()
    class RT:
        hardware_assignment={'gpu_type':'CPU_SYNTHETIC'}
        def __init__(self):self.calls=[]
        def load_base(self):pass
        def check_tokens(self,x):pass
        def synthetic(self):return [[1,2]]
        def text(self,seq,max_new_tokens):
            assert len(seq)==1 and max_new_tokens==128
            self.calls.append(seq);return [dict(raw='x',token_ids=[1])]
    rt=RT();xs=[dict(id=str(i),row='format_plan',input_ids=[1,2],prompt='x') for i in range(84)]
    assert text_acquire(xs,None,rt,old.Clock(tmp_path,time.time()+3600),tmp_path)=='COMPLETE'
    assert len(rt.calls)==85 and len(list((tmp_path/'jobs').glob('*.json')))==84
