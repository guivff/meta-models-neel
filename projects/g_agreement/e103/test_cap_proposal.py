import pytest
from projects.g_agreement.e103 import worker_cap_proposal as W
from projects.g_agreement.ops import i5_sampling_cap_proposal as C

def test_proposal_cannot_allocate_or_run_without_direct_cap_ruling(tmp_path,monkeypatch):
    assets=tmp_path/'assets';assets.write_text('{}');monkeypatch.setenv('RUNPOD_POD_ID','new')
    a=dict(experiment='E103',gpu_count=1,gpu_type='H200',cap_seconds=11200,prior_seconds=0,pod_created_epoch=10,custody_start_epoch=10,absolute_deadline_epoch=11210,daily_budget_verified=True,projected_daily_USD=800,assets=dict(sha256=W.sha(assets)),pod_id='new',analysis_unit_gpu_types={'E103_primary':'H200'})
    with pytest.raises(ValueError,match='NOT AUTHORIZED'):W.validate_assignment(a,11,assets)
    (tmp_path/'PLAN.json').write_text('{}')
    with pytest.raises(ValueError,match='NOT AUTHORIZED'):C.run_job(tmp_path)
    a.update(operational_authorization='GUIV_DIRECT_CAP_RULING',operational_authorization_commit='f'*40,timing_pilot_output_seal_sha256='44c4d8586126afec07fd855a6af5c57cc4a865e6f528fbb4954775bce2a0328c',timing_pilot_disposition='TIMING_ONLY_ARCHIVE_EXCLUDED_FROM_JUDGE')
    W.validate_assignment(a,11,assets)
    with pytest.raises(ValueError):W.validate_assignment(dict(a,timing_pilot_disposition='use twice'),11,assets)
