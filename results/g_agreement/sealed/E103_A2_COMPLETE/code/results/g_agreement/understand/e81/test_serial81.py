import time
import pytest
import serial81 as S
import worker81 as W
from test_worker81 import fixture,Tiny81

class Serial(Tiny81):
    def text(self,sequences,max_new_tokens=128):
        assert len(sequences)==1
        return super().text(sequences,max_new_tokens)


def test_shards_complete_disjoint():
    xs=fixture()
    for n in (1,4,8):
        parts=S.roster(xs,n);flat=sum(parts,[])
        assert len(flat)==len(set(flat))==11064 and set(flat)=={x['id'] for x in xs}
        assert max(map(len,parts))-min(map(len,parts))<=1
    with pytest.raises(ValueError):S.roster(xs,9)


def test_serial_profile_no_parity_and_full_shard(tmp_path):
    xs=fixture();plan=dict(authority=S.AUTHORITY,mode='profile',shard=None,shards=8,shard_ids=S.roster(xs,8))
    now=time.time();ass=dict(pod_id='CPU_STUB',pod_created_epoch=now-250,custody_start_epoch=now-250)
    W.write(tmp_path/'ASSIGNMENT.json',ass)
    b=Serial();S.acquire(xs,plan,b,W.Clock(tmp_path,time.time()+3600,{},b),tmp_path,dict(synthetic=True))
    assert len(list((tmp_path/'jobs').glob('*.json')))==48 and not list(tmp_path.glob('PARITY*'))
    m=W.read(tmp_path/'MEASURED_PROFILE.json')
    assert m['batch_size']==1 and m['parity_gate'] is False and len(m['shards'])==8
    assert sum(x['items'] for x in m['shards'])==11064
    assert m['staging']['assignment_sha256']==W.sha(tmp_path/'ASSIGNMENT.json')
    for x in m['shards']:
        expected=1.25*(sum(x['phase_counts'][k]*x['seconds_per_item'][k] for k in ('128','32'))+x['staging_seconds']+x['setup_warmup_seconds']+60)
        assert x['forecast_seconds']==pytest.approx(expected) and x['staging_seconds']>=250
    for x in m['shards']:assert x['cap_seconds']>=x['forecast_seconds'] and set(x['seconds_per_item'])=={'128','32'}
    out=tmp_path/'full';out.mkdir();W.write(out/'ASSIGNMENT.json',ass);plan.update(mode='production',shard=0)
    S.acquire(xs,plan,b,W.Clock(out,time.time()+3600,{},b),out,{})
    records=[x for f in sorted((out/'jobs').glob('*.json')) for x in W.read(f)]
    assert [x['id'] for x in records]==plan['shard_ids'][0]
    assert W.read(out/'COUNTS.json')['items']==1383


def test_production_packager_rejects_synthetic_profile(tmp_path):
    import package_serial81 as P
    W.write(tmp_path/'REQUEST.json',{})
    W.write(tmp_path/'MEASURED_PROFILE.json',{})
    W.seal(tmp_path,'OUTPUT_SEAL.json',status='PROFILE_ONLY',synthetic=True)
    with pytest.raises(ValueError,match='actual serial timing'):
        P.production(tmp_path/'REQUEST.json',tmp_path/'MEASURED_PROFILE.json',tmp_path/'production',0)


def test_staging_uses_original_creation_not_reset_custody():
    a=dict(pod_id='CPU_STUB',pod_created_epoch=1000,custody_start_epoch=1000)
    r=S.staging_receipt(a,1275,'a'*64)
    assert r['staging_seconds']==275 and r['provider_created_epoch']==1000 and r['worker_ready_epoch']==1275
    with pytest.raises(ValueError,match='original provider creation'):
        S.staging_receipt(dict(a,custody_start_epoch=1200),1275,'a'*64)
    with pytest.raises(ValueError,match='finite'):
        S.staging_receipt(a,999,'a'*64)
