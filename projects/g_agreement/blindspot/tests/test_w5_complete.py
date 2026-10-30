from contextlib import nullcontext
import json
from types import SimpleNamespace
from pathlib import Path
import numpy as np
import pytest
import torch
from projects.g_agreement.blindspot import w5_complete as W
from projects.g_agreement.blindspot import protocol as P


def fixture(tmp_path, n_per_feature=2, n_features=1):
    bank=tmp_path/'bank'; capture=tmp_path/'capture';bank.mkdir();capture.mkdir()
    items=[{'id':str(i),'feature':f'f{i // n_per_feature}','ids':[9],'donor_id':str(i ^ 1)}
           for i in range(n_per_feature * n_features)]
    specs={f'f{j}':{'kind':'binary',**{r:[['a','b'],['c','d']] for r in ('olens','nla','jlens','logit')}}
           for j in range(n_features)}
    ids=[it['id'] for it in items]
    P.jsonl(bank/'items.input.jsonl',items);P.dump(bank/'templates.json',specs)
    P.dump(bank/'provenance.json',{});P.dump(bank/'sweep.input.json',ids);P.dump(bank/'runtime.json',P.RUNTIME)
    P.seal(bank,['items.input.jsonl','templates.json','provenance.json','sweep.input.json','runtime.json'],'INPUTS_FROZEN')
    for L in W.R.W5_LAYERS:np.save(capture/f'acts{L}.npy',np.arange(len(items)*2,dtype=np.float32).reshape(len(items),2))
    P.dump(capture/'items.order.json',ids);P.dump(capture/'provenance.capture.json',{'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json')})
    names=[f'acts{L}.npy' for L in W.R.W5_LAYERS]+['items.order.json','provenance.capture.json']
    P.dump(capture/'CAPTURE_SEAL.json',{'status':'CAPTURE_COMPLETE_SCORES_PENDING','files':{n:P.sha(capture/n) for n in names}})
    (capture/'scores.sweep.partial.jsonl').write_text('MUST NEVER BE READ')
    return bank,capture


def test_capture_exact_order_all_six_and_no_partial_read(tmp_path,monkeypatch):
    bank,capture=fixture(tmp_path); original=Path.read_text
    def guard(p,*a,**kw):
        assert 'partial' not in p.name
        return original(p,*a,**kw)
    monkeypatch.setattr(Path,'read_text',guard)
    items,donors,specs,h=W.verified_capture(bank,capture,P.sha(capture/'CAPTURE_SEAL.json'))
    assert donors==[1,0] and len(list(W.work_units(items,donors,specs)))==12 and len(h)==6
    np.save(capture/'acts60.npy',np.zeros((2,2)))
    with pytest.raises(ValueError,match='seal mismatch'):
        W.verified_capture(bank,capture,P.sha(capture/'CAPTURE_SEAL.json'))


def test_forecast_uses_each_warm_layer_median_and_charges_all_smoke_once():
    counts={L:80 for L in W.R.W5_LAYERS}
    smoke={L:[1.,2.,9.] for L in W.R.W5_LAYERS}
    smoke[60]=[3.,4.,15.]  # layer-specific speed and a high timed outlier
    b=W.forecast_budget(smoke,counts)
    assert b['smoke_seconds']==82 and b['fresh_pass_forecast_seconds']==1120
    assert b['forecast_seconds']==1202 and b['science_cap_seconds']==2163 and b['fits_one_gpu_hour']
    assert b['units_in_fresh_pass']==480 and b['median_unit_seconds_by_layer'][60]==4
    assert not W.forecast_budget({L:[10.,10.,10.] for L in counts},counts)['fits_one_gpu_hour']
    with pytest.raises(ValueError):W.forecast_budget({L:[0.,1.,2.] for L in counts},counts)
    with pytest.raises(ValueError):W.forecast_budget({L:[1.,2.,3.] for L in counts if L!=60},counts)


def test_forecast_headroom_is_capped_without_changing_existing_fit_gate():
    counts={L:80 for L in W.R.W5_LAYERS}
    b=W.forecast_budget({L:[4.5,4.5,4.5] for L in counts},counts)
    assert b['forecast_seconds']==2241
    assert b['science_cap_seconds']==3600
    assert b['fits_one_gpu_hour']  # 1.5F fits; the extra headroom clips at the ceiling
    b=W.forecast_budget({L:[5.,5.,5.] for L in counts},counts)
    assert b['science_cap_seconds']==3600
    assert not b['fits_one_gpu_hour']  # retain the original refusal to reduce scope


def test_collection_scores_every_unit_afresh_without_capture(tmp_path,monkeypatch):
    bank,capture=fixture(tmp_path,n_per_feature=66,n_features=2)
    a=SimpleNamespace(bank=bank,capture=capture,out=tmp_path/'out',batch=32,assignment=tmp_path/'assignment.json',
                      receipt=tmp_path/'receipt.json',execution_plan=tmp_path/'plan.json',w1_analysis=tmp_path/'w1',assets=tmp_path/'assets.json')
    P.dump(a.assignment,{});P.dump(a.assets,{})
    receipt={'source_files':P.code_hashes(),'budget_amendment_commit':P.W5_COMPLETION_AMENDMENT,
             'timing_amendment_commit':W.TIMING_AMENDMENT,
             'capture_seal_sha256':P.sha(capture/'CAPTURE_SEAL.json'),'w1_analysis_seal_sha256':'d'*64,'n_items':132,'n_scoring_units':24}
    P.dump(a.receipt,receipt)
    assigned={'pod_id':'fixture','science_cap_gpu_seconds':3600,'allocated_gpu_seconds':4500,'staging_allowance_seconds':900,'deadline_epoch':4500,
              'completion_receipt_sha256':P.sha(a.receipt),'_science_clock_path':str(tmp_path/'clock.json')}
    monkeypatch.setattr(P,'admit',lambda *args,**kw:assigned)
    monkeypatch.setattr(P,'logged',lambda *args,**kw:nullcontext())
    monkeypatch.setattr(P,'compute_window',lambda *args,**kw:nullcontext())
    monkeypatch.setattr(P,'science_deadline',lambda *args,**kw:3700)
    def start(_):
        if not (tmp_path/'clock.json').exists():
            assert len(calls)==6  # every complete warm-up precedes first science
            P.dump(tmp_path/'clock.json',{'first_science_epoch':100,'science_deadline_epoch':3700})
    monkeypatch.setattr(P,'science_checkpoint',start)
    monkeypatch.setattr(W.R,'_require_w1_before_sweep',lambda *args:'d'*64)
    monkeypatch.setattr(W.R,'_assets',lambda *args,**kw:{})
    calls=[]
    class Oracle:
        def paired_logodds_templates(self,h,L,pairs):
            calls.append((L,h.clone()));return torch.full((2,len(h)),float(len(calls)))
    monkeypatch.setattr(W.R,'_load_oracle',lambda *args:Oracle())
    monkeypatch.setattr(torch.cuda,'synchronize',lambda:None)
    monkeypatch.setattr(W.signal,'setitimer',lambda *args:None)
    monkeypatch.setattr(W.time,'time',lambda:100)
    ticks=iter(map(float,range(36)));monkeypatch.setattr(W.time,'perf_counter',lambda:next(ticks))
    W.collect(a)
    seal=P.verify(a.out,'SCORE_SEAL.json'); rows=P.rows(a.out/'scores.sweep.jsonl')
    assert len(calls)==6+18+24 and len(rows)==24*66
    assert [L for L,_ in calls[:6]]==list(W.R.W5_LAYERS)
    assert [L for L,_ in calls[6:24]]==[L for L in W.R.W5_LAYERS for _ in range(3)]
    assert all(len(h)==66 for _,h in calls)  # warm-up must not truncate to batch=32
    assert {r['scores'][0] for r in rows}==set(map(float,range(25,49)))
    forecast=json.loads((a.out/'FORECAST.json').read_text())
    assert forecast['smoke_seconds']==18 and forecast['forecast_seconds']==42
    assert forecast['science_cap_seconds']==423
    assert all(f'acts{L}.npy' in seal['files'] for L in W.R.W5_LAYERS)
    assert all(P.sha(a.out/f'acts{L}.npy')==P.sha(capture/f'acts{L}.npy') for L in W.R.W5_LAYERS)
    with pytest.raises(FileExistsError):W.collect(a)


def test_old_timing_receipt_rejected_before_model_or_capture(tmp_path,monkeypatch):
    a=SimpleNamespace(assignment=tmp_path/'assignment.json',receipt=tmp_path/'receipt.json',
                      bank=tmp_path/'bank',execution_plan=tmp_path/'plan.json')
    P.dump(a.receipt,{'source_files':P.code_hashes(),'budget_amendment_commit':P.W5_COMPLETION_AMENDMENT})
    monkeypatch.setattr(P,'admit',lambda *args,**kw:{'completion_receipt_sha256':P.sha(a.receipt)})
    monkeypatch.setattr(W,'verified_capture',lambda *args:pytest.fail('old timing receipt reached capture'))
    monkeypatch.setattr(W.R,'_load_oracle',lambda *args:pytest.fail('old timing receipt reached model'))
    with pytest.raises(ValueError,match='receipt not bound'):
        W.collect(a)
