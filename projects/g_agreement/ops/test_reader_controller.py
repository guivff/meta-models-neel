from projects.g_agreement.ops import i5_reader_controller as R
import pytest


def test_no_allocation_without_registered_cap_and_published_go(tmp_path,monkeypatch):
    (tmp_path/'PLAN.json').write_text('{}')
    monkeypatch.setattr(R.C,'api',lambda *a:pytest.fail('API reached without admission'))
    with pytest.raises(ValueError,match='admission'):R.run_job(tmp_path)
    p=dict(reader='oracle',cap_seconds=6500,GO_git_verified=True,authorization_commit='f'*40,projected_upper_usd=800)
    R.validate_plan(p)
    for change in [dict(cap_seconds=7400),dict(GO_git_verified=False),dict(projected_upper_usd=1501)]:
        with pytest.raises(ValueError):R.validate_plan(dict(p,**change))


def test_complete_native_grid_and_cross_reader_control_rejected():
    ids=[f'{i:024x}'for i in range(3360)];plan=dict(reader='oracle',item_ids=ids,source_seal_sha256='s',input_sha256='i',payload_hashes={'GO.json':'g'});state=dict(gpu_type='H200')
    seal=dict(status='COMPLETE',experiment='E97',reader='oracle',gpu_type='H200',source_sha256='s',input_sha256='i',go_sha256='g')
    records=[dict(id=i,reader='oracle',reader_native_layer=44,repeat=0,raw='fixture')for i in ids]
    R.complete_grid(seal,records,plan,state)
    with pytest.raises(ValueError,match='roster'):R.complete_grid(seal,records[:-1],plan,state)
    for change in [dict(reader='nla'),dict(repeat=1),dict(reader_native_layer=42)]:
        wrong=[dict(records[0],**change),*records[1:]]
        with pytest.raises(ValueError,match='native'):R.complete_grid(seal,wrong,plan,state)
    with pytest.raises(ValueError,match='binding'):R.complete_grid(dict(seal,go_sha256='other'),records,plan,state)
