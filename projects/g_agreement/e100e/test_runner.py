import copy,json,time
from pathlib import Path
import numpy as np
import pytest
import torch
from .build import pairings,ROWS,SEED
from .runner import validate,jobs,acquire,cap_formula,assignment

def fixture():
    items=[dict(id=str(i),row=ROWS[i//84],slot=i,row_slot=i%84,donor_slot=(i//84)*84+(i+42)%84) for i in range(168)]
    arrays={b:(np.arange(168*3).reshape(168,3)+b).astype(np.float32) for b in (42,44)}
    return items,arrays

def test_pairing_frozen_different_value_reproducible():
    xs=[dict(id=str(i),value=i%3) for i in range(84)]
    a=pairings(xs,np.random.default_rng(SEED));assert a==pairings(xs,np.random.default_rng(SEED))
    assert all(xs[i]['value']!=xs[j]['value'] for i,j in enumerate(a))
    with pytest.raises(ValueError):pairings([dict(id=str(i),value=0) for i in range(84)],np.random.default_rng(SEED))

def test_public_and_grid():
    items,a=fixture();validate(items,a,3);jj=jobs(items)
    assert len(jj)==44 and sum(len(j['indices']) for j in jj)==336
    assert {j['phase'] for j in jj}=={'oracle:8','oracle:4','nla:8','nla:4'}
    bad=copy.deepcopy(items);bad[0]['label']=1
    with pytest.raises(ValueError):validate(bad,a,3)
    bad=copy.deepcopy(items);bad[0]['donor_slot']=84
    with pytest.raises(ValueError):validate(bad,a,3)

class TinyBackend:
    def __init__(self):self.calls=[];self.loads=[];self.model=torch.nn.Linear(3,2,bias=False)
    def load_oracle(self):self.loads.append('oracle')
    def load_nla(self):self.loads.append('nla')
    def native_one(self,reader,h):
        self.calls.append((reader,h.copy()))
        with torch.inference_mode():ids=self.model(torch.tensor(h)).argmax(-1).tolist()
        return [[dict(raw=str(i),text=str(i))] for i in ids]
class Clock:
    def __init__(self):self.end=time.time()+10000;self.cost={}
    def call(self,k,fn):
        v=fn()
        if k in self.cost:self.cost[k].append(.001)
        return v

def test_tiny_native_transplant_once_per_cell(tmp_path):
    items,a=fixture();before={b:h.tobytes() for b,h in a.items()};b=TinyBackend()
    assert acquire(items,a,b,Clock(),tmp_path,'synthetic CPU')
    assert b.loads==['oracle','nla'] and len(b.calls)==46 #44 retained batches+2warmups
    got=[json.loads(p.read_text()) for p in sorted((tmp_path/'jobs').glob('*.json'))]
    assert sum(map(len,got))==336 and len({x['id'] for group in got for x in group})==336
    for j,records in zip(jobs(items),got):
        block=44 if j['reader']=='oracle' else 42
        target=a[block][[items[i]['donor_slot'] for i in j['indices']]]
        call=next(h for r,h in b.calls if r==j['reader'] and np.array_equal(h,target))
        assert np.array_equal(call,target)
        for x,i in zip(records,j['indices']):
            assert x['norm_ratio']==pytest.approx(np.linalg.norm(a[block][items[i]['donor_slot']])/np.linalg.norm(a[block][i]))
            assert x['read_block']==block and x['repeat']==0
    assert all(a[k].tobytes()==v for k,v in before.items())

def test_cap_uses_max_setup_and_cumulative(monkeypatch):
    ps=[dict(experiment='E100e',measured=True,staging_seconds=30,setup_warmup_seconds=100,work_seconds=dict(oracle=100,nla=150)),dict(experiment='E100e',measured=True,staging_seconds=50,setup_warmup_seconds=200,work_seconds=dict(oracle=90,nla=160))]
    assert cap_formula(ps)==755
    monkeypatch.setenv('RUNPOD_POD_ID','synthetic')
    a=dict(experiment='E100e',gpu_type='H200',gpu_count=1,input_seal_sha256='i',source_seal_sha256='s',assets_sha256='a',prior_seconds=100,cap_seconds=800,authorized_cumulative_seconds=1800,pod_created_epoch=1,custody_start_epoch=1,absolute_deadline_epoch=801,pod_id='synthetic',allocation_verified=True,daily_budget_verified=True,projected_daily_USD=1,daily_budget_USD=2,mode='production',measured_profiles=ps)
    assignment(a,'i','s','a')
    a.update(cap_seconds=1701,absolute_deadline_epoch=1702)
    with pytest.raises(ValueError):assignment(a,'i','s','a')


def test_no_fit_seals_retained_pilots_without_replay(tmp_path):
    items,a=fixture();b=TinyBackend();clock=Clock();clock.end=time.time()+59
    assert acquire(items,a,b,clock,tmp_path,'synthetic CPU') is False
    assert b.loads==['oracle'] and len(b.calls)==3
    records=[json.loads(p.read_text()) for p in (tmp_path/'jobs').glob('*.json')]
    assert sum(map(len,records))==12
    assert json.loads((tmp_path/'FORECAST_oracle.json').read_text())['status']=='NO_FIT'

def test_invalid_native_group_stops(tmp_path):
    items,a=fixture();b=TinyBackend();b.native_one=lambda reader,h:[[] for _ in h]
    with pytest.raises(ValueError,match='one native'):acquire(items,a,b,Clock(),tmp_path,'synthetic CPU')


def retry_fixture(tmp_path,monkeypatch):
    from projects.g_agreement.e100.contract import write,sha
    from .runner import OPERATIONAL_NOTE
    monkeypatch.setenv('RUNPOD_POD_ID','synthetic')
    old=tmp_path/'attempt1';old.mkdir()
    write(old/'PHASE_TIMINGS.json',[dict(phase='oracle_setup',status='COMPLETE',seconds=100)])
    write(old/'FORECAST_oracle.json',dict(status='NO_FIT',remaining_seconds=2000))
    write(old/'COMPLETED.json',[0,1]);(old/'jobs').mkdir();write(old/'jobs/000000.json',[dict(raw='earlier attempt must never be reused')])
    write(old/'OUTPUT_SEAL.json',dict(experiment='E100e',status='NO_FIT',input_sha256='i',files={str(p.relative_to(old)):sha(p) for p in old.rglob('*') if p.is_file()}))
    profile=tmp_path/'attempt1_profile.json'
    write(profile,dict(experiment='E100e',attempt=1,output_root=str(old),output_seal_sha256=sha(old/'OUTPUT_SEAL.json'),custody_seconds=1700,staging_seconds=100,setup_warmup_seconds=200,work_seconds=dict(oracle=1000,nla=1000)))
    a=dict(experiment='E100e',gpu_type='H200',gpu_count=1,input_seal_sha256='i',source_seal_sha256='s',assets_sha256='a',prior_seconds=1700,cap_seconds=2935,authorized_cumulative_seconds=4635,pod_created_epoch=1,custody_start_epoch=1,absolute_deadline_epoch=2936,pod_id='synthetic',allocation_verified=True,daily_budget_verified=True,projected_daily_USD=5,daily_budget_USD=25,mode='production',measured_profiles=[],operational_note_commit=OPERATIONAL_NOTE,attempt=2,attempt1_profile=str(profile),attempt1_profile_sha256=sha(profile))
    return a,old

def test_per_attempt_override_default_unchanged_and_fresh_only(tmp_path,monkeypatch):
    from .runner import fresh_attempt
    a,old=retry_fixture(tmp_path,monkeypatch);fresh=tmp_path/'attempt2'
    # Omitted/default argument still enforces the original1800s cumulative ceiling.
    with pytest.raises(ValueError,match='half GPU-hour'):assignment(a,'i','s','a')
    with pytest.raises(ValueError,match='half GPU-hour'):assignment(a,'i','s','a',1800,fresh)
    assignment(a,'i','s','a',2935,fresh);fresh_attempt(fresh)
    with pytest.raises(ValueError,match='fresh independent'):assignment(a,'i','s','a',2935,fresh)
    with pytest.raises(FileExistsError):fresh_attempt(fresh)
    for earlier in (old,old/'new_subdirectory',old.parent):
        with pytest.raises(ValueError,match='fresh independent'):assignment(a,'i','s','a',2935,earlier)

def test_retry_never_reuses_earlier_outputs(tmp_path,monkeypatch):
    from .runner import fresh_attempt
    from projects.g_agreement.e100.contract import sha
    a,old=retry_fixture(tmp_path,monkeypatch);before={str(p):sha(p) for p in old.rglob('*') if p.is_file()}
    fresh=tmp_path/'attempt2';assignment(a,'i','s','a',2935,fresh);fresh_attempt(fresh)
    assert list(fresh.iterdir())==[]
    items,arrays=fixture();b=TinyBackend();assert acquire(items,arrays,b,Clock(),fresh,'synthetic CPU')
    assert len(b.calls)==46 and len(list((fresh/'jobs').glob('*.json')))==44
    assert all(sha(Path(p))==h for p,h in before.items())
    copied=tmp_path/'copied_attempt';copied.mkdir();(copied/'COMPLETED.json').write_text('[0,1]')
    with pytest.raises(ValueError,match='fresh independent'):assignment(a,'i','s','a',2935,copied)
    with pytest.raises(FileExistsError):fresh_attempt(copied)

@pytest.mark.parametrize('field,value', [('attempt',3),('operational_note_commit','unapproved'),('attempt1_profile_sha256','wrong'),('prior_seconds',1),('cap_seconds',2936)])
def test_retry_authority_profile_and_formula_are_bound(tmp_path,monkeypatch,field,value):
    a,old=retry_fixture(tmp_path,monkeypatch);a[field]=value
    with pytest.raises(ValueError):assignment(a,'i','s','a',2935,tmp_path/'attempt2')

def test_retry_requires_postload_nofit_and_cost_ceiling(tmp_path,monkeypatch):
    from projects.g_agreement.e100.contract import read,write,sha
    a,old=retry_fixture(tmp_path,monkeypatch);profile=Path(a['attempt1_profile']);p=read(profile)
    p.update(staging_seconds=20000);write(profile,p);a['attempt1_profile_sha256']=sha(profile)
    a.update(cap_seconds=18000,authorized_cumulative_seconds=19700,absolute_deadline_epoch=18001)
    with pytest.raises(ValueError,match='25 USD'):assignment(a,'i','s','a',18000,tmp_path/'attempt2')
    s=read(old/'OUTPUT_SEAL.json');s['status']='COMPLETE';write(old/'OUTPUT_SEAL.json',s);p['output_seal_sha256']=sha(old/'OUTPUT_SEAL.json');write(profile,p);a['attempt1_profile_sha256']=sha(profile)
    with pytest.raises(ValueError,match='terminal NO_FIT'):assignment(a,'i','s','a',2935,tmp_path/'attempt2')
