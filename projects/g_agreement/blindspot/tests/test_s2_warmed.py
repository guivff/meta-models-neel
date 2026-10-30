import pytest
from projects.g_agreement.blindspot.s2_warmed import warmed_gate


def test_median_not_cold_or_max_and_load_included():
    g=warmed_gate(1000,[.5,.4,9],890,1010,3,3000,0)
    assert g['forecast_seconds']==1445
    assert g['cap_seconds']==2527.5
    assert g['median_unit_seconds']==.5


def test_prior_charges_and_elapsed_are_not_reset():
    with pytest.raises(TimeoutError):warmed_gate(1000,[.5]*3,890,1010,3,3000,1400)
    with pytest.raises(TimeoutError):warmed_gate(1000,[.5]*3,890,2400,3,3000,0)


def test_over_cap_reports_before_full_run():
    with pytest.raises(TimeoutError,match='remaining forecast'):warmed_gate(2200,[1]*3,890,2205,3,3600,0)


@pytest.mark.parametrize('timings',[[],[.4,.5],[.4,.5,.6,.7],[.4,0,.6],[.4,float('nan'),.6]])
def test_three_finite_positive_units_required(timings):
    with pytest.raises(ValueError):warmed_gate(1000,timings,890,1010,3,3000,0)


def test_collect_discards_warmup_and_preserves_exact_frozen_grid(tmp_path,monkeypatch):
    from contextlib import nullcontext
    from types import SimpleNamespace
    import json
    import torch
    import numpy as np
    from projects.g_agreement.blindspot import s2_warmed as S
    from projects.g_agreement.w_claims import ar as adapter
    texts=tmp_path/'texts';texts.mkdir()
    definitions={'synthetic':{'row_class':'state-like','values':[True,False],
        'descriptions':['inside parentheses','outside parentheses']}}
    records,_=S.AR.freeze_text_records(definitions)
    S.P.jsonl(texts/'texts.input.jsonl',records);S.P.dump(texts/'definitions.json',definitions)
    S.P.dump(texts/'provenance.json',{'synthetic':True})
    S.P.seal(texts,['texts.input.jsonl','definitions.json','provenance.json'],'INPUTS_FROZEN_AR_STATEMENTS')
    assignment=tmp_path/'a.json';S.P.dump(assignment,{'experiment':'S2','entrypoint_files':{
        'projects/g_agreement/blindspot/s2_warmed.py':S.P.sha(S.__file__)},
        'allocated_gpu_seconds':3000,'previous_gpu_seconds':0,'deadline_epoch':1e12})
    assets=tmp_path/'assets';assets.write_text('{}');whitener=tmp_path/'w';whitener.write_text('fixture')
    monkeypatch.setattr(S.AR,'_compute',lambda *a:nullcontext())
    monkeypatch.setattr(S.AR,'_assets',lambda *a:{'model':'fixture','ar':'fixture'})
    monkeypatch.setattr(adapter,'load_reconstructor',lambda *a:(None,lambda text,**kw:{'input_ids':text.split()},None))
    calls=[]
    def reconstruct(model,tok,batch):
        calls.append(batch)
        return torch.tensor([[float(len(t)),1.] for t in batch])
    monkeypatch.setattr(adapter,'reconstruct',reconstruct)
    clock=iter(range(1000));monkeypatch.setattr(S.time,'monotonic',lambda:float(next(clock)))
    out=tmp_path/'out'
    S.collect(SimpleNamespace(texts=texts,assets=assets,assignment=assignment,official=tmp_path/'official',whitener=whitener,out=out,batch=8))
    assert len(calls)==6  # one discarded warm-up, five retained batches
    assert [t for b in calls[1:] for t in b]==[r['text'] for r in records]
    assert json.loads((out/'ids.json').read_text())==[r['id'] for r in records]
    assert np.load(out/'recon.npy',allow_pickle=False).shape==(40,2)
    assert len(json.loads((out/'WARMED_FORECAST.json').read_text())['timed_units_seconds'])==3
    assert set(S.P.verify(out,'SCORE_SEAL.json')['files'])=={'recon.npy','ids.json','provenance.json'}


def test_cap_clamps_at_3600_without_dropping_prior_charge():
    g=warmed_gate(2000,[.5]*3,890,2010,3,3600,0)
    assert g['cap_seconds']==3600
