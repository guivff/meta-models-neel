"""Measured post-warm-up forecasts. No invented GPU performance estimates."""
import math


def profile_receipt(events,phases):
    if not phases or any(not p['sample_seconds'] or any(not math.isfinite(t) or t<=0 for t in p['sample_seconds']) for p in phases):
        raise ValueError('positive measured timings for every phase')
    setup=sum(e['seconds'] for e in events if e['phase'].endswith(('_setup','_warmup_discarded')))
    work=sum(p['jobs']*p['mean_job_seconds'] for p in phases)
    return dict(status='TIMING_ONLY_NOT_SCIENCE',margin=1.25,phases=phases,setup_warmup_seconds=setup,
                measured_work_seconds=work,total_seconds_with_margin=1.25*(setup+work),
                profile_outputs_discarded=True,note='Add measured staging and retrieval before custody admission.')


def bind_profile(out,assignment,input_sha,source_sha,hardware):
    from .contract import read,write
    p=out/'MEASURED_PROFILE.json';r=read(p)
    r.update(experiment=assignment['experiment'],input_sha256=input_sha,source_sha256=source_sha,gpu_type=hardware['gpu_type'],
             actual_gpu_name=hardware['actual_gpu_name'],staging_seconds=read(out/'STAGING.json')['seconds'])
    r['total_seconds_with_margin']=1.25*(r['setup_warmup_seconds']+r['measured_work_seconds']+r['staging_seconds']+60)
    p.unlink();write(p,r)


def _measured(r):
    values=[r[k] for k in ('setup_warmup_seconds','measured_work_seconds','staging_seconds')]
    if any(not math.isfinite(v) or v<0 for v in values) or values[1]<=0:
        raise ValueError('finite nonnegative measured setup/staging and positive work')
    expected=1.25*(sum(values)+60)
    if not math.isclose(expected,r['total_seconds_with_margin']):raise ValueError('measured forecast arithmetic')


def admit(profile_path,ass,input_sha,source_sha,*,setup_profiles=()):
    from .contract import read,sha
    if not profile_path or sha(profile_path)!=ass['profile_sha256']:raise ValueError('sealed measured profile required')
    r=read(profile_path)
    if (r['status']!='TIMING_ONLY_NOT_SCIENCE' or r['input_sha256']!=input_sha or r['source_sha256']!=source_sha
        or r['gpu_type']!=ass['gpu_type'] or r['margin']!=1.25):raise ValueError('exact input/source/hardware timing binding')
    _measured(r)
    policy=ass.get('timing_cap_policy','legacy')
    if policy not in ('legacy','standing217','e105_amendment2'):raise ValueError('unknown timing cap policy')
    extra=0
    if policy=='e105_amendment2':
        if (ass.get('experiment')!='E105' or ass.get('cap_authority')!='157fb545'
            or ass.get('restart_round')!=1
            or set(ass.get('analysis_unit_gpu_types',{})) not in ({'indent_level'},{'fact_recall'})):
            raise ValueError('E105 amendment2 authorized first restart rows only')
        extra=300
    if policy in ('standing217','e105_amendment2'):
        # The assignment seals the supplied experiment-wide inventory. Include the
        # target row's profile even if the operator omitted it from that inventory.
        if sorted(sha(p) for p in setup_profiles)!=sorted(ass.get('setup_profile_sha256',[])):
            raise ValueError('sealed setup profile inventory required')
        setups=[r['setup_warmup_seconds']+r['staging_seconds']]
        for p in (profile_path,*setup_profiles):
            q=read(p);_measured(q)
            if q['status']!='TIMING_ONLY_NOT_SCIENCE' or q['margin']!=1.25:
                raise ValueError('discarded measured timing profile required')
            # Older profiles predate the experiment field; their original custody
            # assignment provides the experiment binding without editing receipts.
            owner=read(p.parent/'ASSIGNMENT.json')
            if (owner['experiment']!=ass['experiment'] or q.get('experiment',owner['experiment'])!=ass['experiment']
                or owner['source_sha256']!=q['source_sha256'] or owner['input_sha256']!=q['input_sha256']
                or owner['gpu_type']!=q['gpu_type']):raise ValueError('experiment timing profile binding')
            setups.append(q['setup_warmup_seconds']+q['staging_seconds'])
        expected=max(setups)+1.25*r['measured_work_seconds']
    else:
        if setup_profiles or ass.get('setup_profile_sha256'):raise ValueError('setup profiles require standing217 policy')
        expected=1.25*(r['setup_warmup_seconds']+r['measured_work_seconds']+r['staging_seconds']+60)
    base=expected;expected+=extra
    if ass['cap_seconds']>math.ceil(expected):raise ValueError('custody cap exceeds measured forecast')
    if ass['cap_seconds']<expected:raise ValueError('full run does not fit custody cap')
    return dict(policy=policy,forecast_seconds=expected,cap_seconds=math.ceil(expected),
                base_forecast_seconds=base,amendment_extra_seconds=extra,
                setup_profile_sha256=[sha(p) for p in setup_profiles])
