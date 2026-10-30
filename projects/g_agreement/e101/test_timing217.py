"""Operational-only cap amendment; no model or scientific outputs."""
import math
import pytest
from projects.g_agreement.e101.contract import write,sha
from projects.g_agreement.e101.timing import admit


def profile(root,name,setup,work=100,experiment='E104',**changes):
    out=root/name;out.mkdir()
    r=dict(status='TIMING_ONLY_NOT_SCIENCE',margin=1.25,setup_warmup_seconds=setup,
           measured_work_seconds=work,staging_seconds=3,input_sha256=name,source_sha256='s',gpu_type='H200')
    r.update(changes)
    r['total_seconds_with_margin']=1.25*(r['setup_warmup_seconds']+r['measured_work_seconds']+r['staging_seconds']+60)
    p=out/'MEASURED_PROFILE.json';write(p,r)
    write(out/'ASSIGNMENT.json',dict(experiment=experiment,input_sha256=name,source_sha256='s',gpu_type='H200'))
    return p


def assignment(p,extra=(),cap=148):
    return dict(experiment='E104',profile_sha256=sha(p),gpu_type='H200',cap_seconds=cap,
                timing_cap_policy='standing217',setup_profile_sha256=[sha(x) for x in extra])


def test_max_setup_uses_other_row_and_target_work_only(tmp_path):
    p=profile(tmp_path,'target',10);q=profile(tmp_path,'other',20,work=900)
    a=assignment(p,[q]);r=admit(p,a,'target','s',setup_profiles=[q])
    assert r['forecast_seconds']==148 and r['cap_seconds']==148
    assert r['policy']=='standing217'
    for cap in (147,149):
        with pytest.raises(ValueError):admit(p,dict(a,cap_seconds=cap),'target','s',setup_profiles=[q])


def test_target_setup_always_included_and_rounding(tmp_path):
    p=profile(tmp_path,'target',20.1);q=profile(tmp_path,'other',5)
    r=admit(p,assignment(p,[q],cap=149),'target','s',setup_profiles=[q])
    assert r['cap_seconds']==math.ceil(148.1)


@pytest.mark.parametrize('defect',['wrong_experiment','tampered_profile','missing_inventory','different_owner_binding','nonfinite'])
def test_foreign_or_invalid_setup_cannot_admit(tmp_path,defect):
    p=profile(tmp_path,'target',10)
    q=profile(tmp_path,'other',20,experiment='E100' if defect=='wrong_experiment' else 'E104')
    a=assignment(p,[q])
    if defect=='tampered_profile':q.write_text(q.read_text()+' ')
    if defect=='missing_inventory':a['setup_profile_sha256']=[]
    if defect=='different_owner_binding':
        f=q.parent/'ASSIGNMENT.json';f.unlink();write(f,dict(experiment='E104',input_sha256='different',source_sha256='s',gpu_type='H200'))
    if defect=='nonfinite':
        import json
        r=json.loads(q.read_text());r['setup_warmup_seconds']=float('inf');q.write_text(json.dumps(r))
        a['setup_profile_sha256']=[sha(q)]
    with pytest.raises(ValueError):admit(p,a,'target','s',setup_profiles=[q])


def test_policy_opt_in_and_exact_main_binding(tmp_path):
    p=profile(tmp_path,'target',10);a=assignment(p,cap=217)
    with pytest.raises(ValueError):admit(p,a,'wrong','s')
    with pytest.raises(ValueError):admit(p,dict(a,timing_cap_policy='unknown'),'target','s')
    # Legacy cap arithmetic remains available for already assigned runners.
    r=admit(p,dict(a,timing_cap_policy='legacy'),'target','s')
    assert r['cap_seconds']==217


def test_max_is_whole_measured_setup_plus_staging(tmp_path):
    p=profile(tmp_path,'target',40,staging_seconds=1)
    q=profile(tmp_path,'other',10,staging_seconds=50)
    r=admit(p,assignment(p,[q],cap=185),'target','s',setup_profiles=[q])
    # max(40+1,10+50), not max(setup)+max(staging), and not setup alone.
    assert r['forecast_seconds']==60+1.25*100


def test_e105_amendment2_exact_extra_and_boundary(tmp_path):
    p=profile(tmp_path,'target',40,staging_seconds=1,experiment='E105')
    q=profile(tmp_path,'other',10,staging_seconds=50,experiment='E105')
    a=assignment(p,[q],cap=485)
    a.update(experiment='E105',timing_cap_policy='e105_amendment2',cap_authority='157fb545',restart_round=1,
             analysis_unit_gpu_types={'indent_level':'H200'})
    r=admit(p,a,'target','s',setup_profiles=[q])
    assert r['base_forecast_seconds']==185 and r['forecast_seconds']==485
    assert r['amendment_extra_seconds']==300 and r['cap_seconds']==485
    assert admit(p,dict(a,analysis_unit_gpu_types={'fact_recall':'H200'}),'target','s',setup_profiles=[q])['cap_seconds']==485
    for cap in (484,486):
        with pytest.raises(ValueError):admit(p,dict(a,cap_seconds=cap),'target','s',setup_profiles=[q])
    for change in (dict(experiment='E104'),dict(restart_round=2),dict(cap_authority='unregistered'),
                   dict(analysis_unit_gpu_types={'format_plan':'H200'})):
        with pytest.raises(ValueError,match='amendment2'):admit(p,dict(a,**change),'target','s',setup_profiles=[q])
