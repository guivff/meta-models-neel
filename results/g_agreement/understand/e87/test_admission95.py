import copy,time
from collections import Counter
import pytest
import worker87 as W
import representative95 as R
import admission95 as A
from test_timing95 import base_inputs,completed_profiles
from test_representative95 import scope
from test_worker87 import Tiny87


def test_shard_3_5_first_admit_exact_sealed_arithmetic():
    # Forecast571c37cc / PHASE_TIMINGS hash-bound metadata, no generated values.
    remaining=dict(capture=179,oracle_native=945,nla_native=315,nla_setup=1,oracle_setup=0,placebo_build=1)
    seeds=dict(capture=.48035051790066063,oracle_native=10.440106604124479,nla_native=22.16403395733131,
               nla_setup=382.79238488699775,oracle_setup=0,placebo_build=255.57229802641086)
    native=Counter({'oracle:real:36:8':945,'nla:real:42:8':315})
    rates={'oracle:real:36:8':seeds['oracle_native'],'nla:real:42:8':seeds['nla_native']}
    f=A.forecast(remaining,seeds,{},native,rates,{}, {})
    old=1.25*sum(n*seeds[p] for p,n in remaining.items())
    assert old==pytest.approx(21964.898578843276)
    assert f['remaining_forecast_seconds']==pytest.approx(seeds['nla_setup']+1.15*(old/1.25-seeds['nla_setup']))
    assert f['margin']==1.15
    assert old>21931.6>f['remaining_forecast_seconds']
    # Placebo construction is work in the sealed representative binder: preserve work margin1.15.
    assert f['remaining_work_seconds']>=seeds['placebo_build']


def test_per_batch_drift_only_reprices_its_measured_native_stratum():
    left=Counter({'oracle:real:36:8':159,'oracle:placebo:56:8':680})
    rates={'oracle:real:36:8':9.933244172328463,'oracle:placebo:56:8':10.4}
    f=A.forecast({'nla_setup':1},{'nla_setup':382.79238488699775},{},left,rates,
                  {'oracle:real:36:8':[10.82287625502795]}, {})
    assert f['native_seconds_per_batch']['oracle:placebo:56:8']==10.4
    assert f['remaining_work_seconds']==pytest.approx(159*10.82287625502795+680*10.4)
    assert f['remaining_setup_seconds']==382.79238488699775


def test_full_original_engine_grid_and_per_batch_admission(tmp_path,monkeypatch):
    s=scope(tmp_path);profiles=completed_profiles(s,tmp_path,monkeypatch)
    book=R.rates(s,profiles);inv=W.read(s/'ROW_INVENTORY.json')
    xs,p=R.row_inputs(s,inv['rows'][0],0);out=tmp_path/'run';out.mkdir()
    m=dict(method=A.METHOD,rate_book=book)
    seeds={k:book['other'].get(k,0) for k in ['oracle_setup','nla_setup','capture','placebo_build']}
    b=Tiny87();c=A.AdmissionClock95(out,time.time()+36000,seeds,b,xs,p,m)
    W.acquire(s/'row0/inputs',xs,p,b,c,out,dict(experiment='E95',synthetic=True))
    assert not any(c.left.values()) and W.read(out/'FORECAST.json')['status']=='ADMIT'
    assert all('native_stratum' in e for e in c.events if e['real'] and e['phase'].endswith('_native'))
    c.end=time.time()+60
    with pytest.raises(W.NoFit):c.admit()


def test_unobserved_warmups_are_reserved_without_padding():
    f=A.forecast({'oracle_setup':1},{'oracle_setup':100},{},Counter(),{}, {},{'oracle_44_warmup_discarded':7})
    assert f['remaining_forecast_seconds']==107 and f['remaining_work_seconds']==0
    with pytest.raises(ValueError):A.forecast({'nla_setup':1},{'nla_setup':float('nan')},{},Counter(),{}, {},{})


def test_amendment_runtime_dispatch_requires_live115_entrypoint(tmp_path,monkeypatch):
    import timing95 as T
    s=scope(tmp_path);profiles=completed_profiles(s,tmp_path,monkeypatch);book=R.rates(s,profiles)
    inv,_=R.reduce_inventory(W.read(s/'ROW_INVENTORY.json'),3);row=inv['rows'][0];xs,p=R.row_inputs(s,row,3)
    inp=tmp_path/'prospective';inp.mkdir();W.write(inp/'PLAN.json',p);W.write(inp/'items.json',xs)
    f=R.estimate(xs,p,book,margin=1.15);source='f'*64
    m=dict(method=A.METHOD,amendment_authority=A.AUTHORITY,margin=1.15,ceiling_seconds=194400,
        prior_custody_seconds=9924.6,programme_projected_custody_seconds=9924.6+f['cap_seconds'],
        source_seal_sha256=source,plan_sha256=W.sha(inp/'PLAN.json'),items_sha256=W.sha(inp/'items.json'),
        row_indices=p['row_indices'],reduction_step=3,rate_book=book,forecast=f,cap_seconds=f['cap_seconds'],
        profile_set_sha256=book['profile_set_sha256'],measured_decision_sha256='d'*64,
        scope_seal_sha256='a'*64,inventory_sha256='b'*64,index_sha256='c'*64,**book['hardware'])
    limits=dict(timing95=m,cap_seconds=f['cap_seconds'])
    ass={k:m[k] for k in ['gpu_type','image_digest','stack_sha256','assets_sha256','scope_seal_sha256','inventory_sha256','index_sha256']}
    ass.update(pod_created_epoch=100,custody_start_epoch=100,measured_profile_set_sha256=m['profile_set_sha256'],
               measured_decision_sha256=m['measured_decision_sha256'],e95_integrator_admission_sha256='e'*64)
    with pytest.raises(ValueError,match='entrypoint'):T.validate_production(ass,limits,p,inp,source)
    monkeypatch.setattr(W,'_admission95_active',True,raising=False)
    T.validate_production(ass,limits,p,inp,source)
    limits['timing95']['margin']=1.25
    with pytest.raises(ValueError,match='work margin'):T.validate_production(ass,limits,p,inp,source)


def test_repricing_uses_maximum_actual_mean_without_changing_nla_or_scope(tmp_path,monkeypatch):
    import reprice95 as P
    s=scope(tmp_path);profiles=completed_profiles(s,tmp_path,monkeypatch);book=R.rates(s,profiles);old=copy.deepcopy(book)
    records=[dict(profile_sha256='a'*64,oracle_measured_batches=1,oracle_mean_seconds=11.3,oracle_setup_seconds=500.)]
    new=P.price_book(book,records)
    assert book==old and all(v>=11.3 for k,v in new['native'].items() if k.startswith('oracle:'))
    assert all(v==old['native'][k] for k,v in new['native'].items() if k.startswith('nla:'))
    assert new['amendment1_pricing']['work_margin']==1.15
    inv,_=R.reduce_inventory(W.read(s/'ROW_INVENTORY.json'),3);xs,p=R.row_inputs(s,inv['rows'][0],3)
    f=R.estimate(xs,p,new,margin=1.15);cost=f['measured_phase_cost_seconds']
    assert f['cap_seconds']==__import__('math').ceil(cost['fixed']+1.15*sum(cost[k] for k in ['capture','placebo_build','native']))
