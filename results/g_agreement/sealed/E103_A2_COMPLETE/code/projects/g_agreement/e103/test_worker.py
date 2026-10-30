from pathlib import Path
from types import SimpleNamespace
import json
import os
import pytest
import torch
from projects.g_agreement.e103 import worker as W

def test_assignment_cap_and_original_creation_clock(tmp_path,monkeypatch):
    assets=tmp_path/'assets.json';assets.write_text('{}');monkeypatch.setenv('RUNPOD_POD_ID','own')
    a=dict(experiment='E103',gpu_count=1,gpu_type='H200',cap_seconds=3500,prior_seconds=0,pod_created_epoch=10,custody_start_epoch=10,absolute_deadline_epoch=3510,daily_budget_verified=True,projected_daily_USD=1425,assets=dict(sha256=W.sha(assets)),pod_id='own',analysis_unit_gpu_types={'E103_primary':'H200'})
    W.validate_assignment(a,11,assets)
    for patch in [dict(cap_seconds=3600),dict(custody_start_epoch=11),dict(absolute_deadline_epoch=3511),dict(projected_daily_USD=1501),dict(analysis_unit_gpu_types={'E103_primary':'B200'})]:
        with pytest.raises(ValueError):W.validate_assignment(dict(a,**patch),12,assets)

@pytest.mark.parametrize('finite',[True,False])
def test_b200_three_item_smoke_reports_divergence_or_fails(tmp_path,finite):
    head=torch.nn.Linear(1,2);b=SimpleNamespace(model=SimpleNamespace(get_output_embeddings=lambda:head))
    def text(b,ids,max_new_tokens):
        head(torch.ones(1,1)if finite else torch.full((1,1),float('nan')))
        return [dict(raw='candidate')]
    ref=dict(gpu_type='H200',source_output_seal_sha256='old',items=[dict(id=str(i),input_ids=[i],max_new_tokens=32,H200_raw='old')for i in range(3)])
    if finite:
        W.smoke_base(b,text,ref,tmp_path);d=json.loads((tmp_path/'B200_SMOKE.json').read_text());assert d['status']=='PASS'and d['items']==3 and d['first_divergence']==dict(item='0',character=0)
        assert W.first_output(tmp_path)['first_output_evidence']['scope']=='hardware smoke'
    else:
        with pytest.raises(ValueError,match='Nonfinite'):W.smoke_base(b,text,ref,tmp_path)
        assert not(tmp_path/'B200_SMOKE.json').exists()
