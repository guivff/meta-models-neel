"""§99 44ff2b5f: preserve sealed scores; complete only missing context units.

No analysis or test-label join here. The original E12 scorer/prompt implementation
is imported unchanged. The observed-rate forecast is fixed before a GPU launch.
"""
import argparse,math,os,time
from pathlib import Path
import numpy as np
from .cpu import ROOT,read,rows,dump,sha,verify,seal
from .e12 import carrier
from .e12_retry import Residents
from .followup_packed import score_unit,jsonl

BRIEF='results/g_agreement/understand/e12/completion_44ff2b5f/BRIEF_UNDERSTAND.authority.md'
STOP=__import__('datetime').datetime(2026,10,28,22,59,tzinfo=__import__('datetime').timezone.utc).timestamp()


class NoFit(TimeoutError):pass


def forecast(remaining,bulk_mean,warmed_timings,bulk_upper_bound=None):
    if type(remaining) is not int or remaining<=0 or len(warmed_timings)!=3 or any(not math.isfinite(t) or t<=0 for t in warmed_timings):raise ValueError('three finite positive original warmed timings required')
    # §99 22:15 excludes only the first timing from throughput, not its score.
    slowest_warmed=max(warmed_timings[1:])
    if bulk_mean is None:
        # The pull flattened all mtimes and did not store individual bulk durations.
        # Use the sealed whole-clock upper bound conservatively, never label it
        # an exact measured bulk mean or replace it with the reported ~0.73 s.
        if bulk_upper_bound is None or not math.isfinite(bulk_upper_bound) or bulk_upper_bound<=0:raise ValueError('finite positive bulk mean upper bound required')
        rate=max(bulk_upper_bound,slowest_warmed);method='conservative upper bound on max(bulk mean, slowest remaining warmed unit)'
    else:
        if not math.isfinite(bulk_mean) or bulk_mean<=0:raise ValueError('positive bulk mean required')
        rate=max(bulk_mean,slowest_warmed);method='max(observed bulk mean, slowest remaining warmed unit)'
    F=remaining*rate;cap=min(1.5*F+360,1200.)
    return {'remaining_units':remaining,'observed_bulk_mean_seconds':bulk_mean,'bulk_mean_upper_bound_seconds':bulk_upper_bound,
        'slowest_warmed_unit_seconds':slowest_warmed,'selected_rate_seconds_per_unit':rate,'method':method,
        'F_seconds':F,'formula':'min(1.5F+360,1200)','science_cap_seconds':cap,'retrieval_reserve_seconds':180,
        'fits_even_without_retrieval':F<=cap,'fits_with_retrieval':F+180<=cap,
        'excluded_first_warmed_unit_seconds':warmed_timings[0],'eligible_warmed_timings_seconds':list(warmed_timings[1:]),
        'forecast_is_upper_bound':bulk_mean is None and bulk_upper_bound>slowest_warmed,
        'first_warmed_unit_excluded_from_forecast_only':True,'no_fresh_rate_remeasurement':True,'hard_stop_seconds':1200}


def check_unit(value,unit,items):
    if not isinstance(value,list) or len(value)!=len(unit['indices']):raise ValueError('unit row count mismatch')
    for r,i in zip(value,unit['indices']):
        if (r['id'],r['feature'],r['reader'],r['layer'],r['arm'])!=(items[i]['id'],unit['feature'],'nla',42,unit['arm']):raise ValueError('unit identity/order/native site mismatch')
        if len(r['scores'])!=2 or not np.isfinite([*r['scores'],r['score']]).all():raise ValueError('invalid original two-phrasing score record')


def inventory(inputs,prior):
    verify(inputs,'INPUT_SEAL.json');parent=verify(prior);run=read(prior/'run.json')
    if run['status']!='INCOMPLETE' or not parent['status'].endswith('_INCOMPLETE'):raise ValueError('sealed incomplete NLA attempt required')
    if run['input_seal_sha256']!=sha(inputs/'INPUT_SEAL.json'):raise ValueError('prior input lineage mismatch')
    plans=read(inputs/'nla_units.json');items=rows(inputs/'items.input.jsonl');present={};files={}
    for phase in ['native','context']:
        paths=sorted((prior/f'nla-{phase}-units').glob('unit-*.json'));indices=[]
        for p in paths:
            i=int(p.stem.split('-')[1])
            if not 0<=i<len(plans[phase]) or p.name!=f'unit-{i:05d}.json':raise ValueError('invalid unit filename/index')
            relative=str(p.relative_to(prior))
            if relative not in parent['files']:raise ValueError('retained unit absent from original top seal')
            check_unit(read(p),plans[phase][i],items);indices.append(i);files[relative]=sha(p)
        if len(indices)!=len(set(indices)):raise ValueError('duplicate retained unit')
        present[phase]=indices
        if run['forecast']['paths']['nla_'+phase]['completed_units']!=len(indices):raise ValueError('run count and sealed unit inventory differ')
    if present['native']!=list(range(len(plans['native']))):raise ValueError('native path must already be complete; no native rerun is authorised')
    verify(prior/'nla-native-units')
    missing=[i for i in range(len(plans['context'])) if i not in set(present['context'])]
    if not missing or present['context']!=list(range(missing[0])):raise ValueError('exact original completed prefix and missing suffix required')
    return {'prior_parent_seal_sha256':sha(prior/'SCORE_SEAL.json'),'prior_run_sha256':sha(prior/'run.json'),
        'prior_input_seal_sha256':run['input_seal_sha256'],'native_units':len(plans['native']),'context_units':len(plans['context']),
        'retained_native_units':present['native'],'retained_context_units':present['context'],'missing_context_units':missing,
        'retained_unit_hashes':files,'old_files_preserved':True,'test_labels_joined':False}


def prepare(inputs,prior,out):
    inv=inventory(inputs,prior);run=read(prior/'run.json')
    if (inv['native_units'],inv['context_units'],len(inv['retained_context_units']),len(inv['missing_context_units']))!=(150,1671,1514,157):raise ValueError('§99 exact150/1514retained+157missing scope required')
    timings=run['forecast']['paths']['nla_context']['timed_unit_seconds']
    if len(timings)!=3 or any(not math.isfinite(t) or t<=0 for t in timings):raise ValueError('original three warmed timings required')
    bulk_units=len(inv['retained_context_units'])-3;upper=run['elapsed_science_seconds']/bulk_units
    f=forecast(157,None,timings,upper)
    out.mkdir(parents=True,exist_ok=False);dump(out/'RETAINED_MANIFEST.json',inv)
    plan={'schema':'E12_CONTEXT_157_COMPLETION_44ff2b5f','authority_commit':'44ff2b5f','input_seal_sha256':sha(inputs/'INPUT_SEAL.json'),
        'prior_booking':'2ebafd9d','prior_pod':'nzt9h77aqb9o4w','prior_output_path':str(prior.resolve()),
        'prior_parent_seal_sha256':inv['prior_parent_seal_sha256'],'retained_manifest_sha256':sha(out/'RETAINED_MANIFEST.json'),
        'missing_context_units':inv['missing_context_units'],'unit_order':'exact frozen original context-unit ascending order;1514..1670;no native or retained context rescoring',
        'remaining_records':sum(len(read(inputs/'nla_units.json')['context'][i]['indices']) for i in inv['missing_context_units']),
        'forecast':f,'observed_timing_evidence':{'original_context_warmed_timings_seconds':timings,
            'prior_elapsed_science_seconds':run['elapsed_science_seconds'],'observed_bulk_context_units':bulk_units,
            'bulk_mean_exact_value':'NOT_STORED; local pull flattened all unit mtimes; do not infer a measured exact mean from those timestamps',
            'bulk_mean_upper_bound_proof':'sum bulk context durations <= whole prior science elapsed; divide by1511retained nonpilot context units',
            'coordinator_reported_bulk_approx_seconds':.73,'approximation_used_in_forecast':False},
        'setup_allowance_seconds':2400,'fresh_completion_previous_gpu_seconds':0,
        'prior_science_seconds_preserved_not_recharged':run['elapsed_science_seconds'],
        'scorer':'unchanged followup_packed.score_unit/context_pair;originalnativeNLA42/batch boundaries/two phrasing pairs',
        'models':'NLA verbalizer only,load_ar=False,load once in same process as discarded synthetic setup warmup and science',
        'warmup':'one discarded synthetic neutral context unit,not any completed test unit;does not change the frozen observed forecast',
        'join':'CPU-only verify old topseal/eachretainedunit +new completionseal; disjoint union must cover150native+1671context; original canonical order/full8400four-arm grid; label-free',
        'analysis':'once only after joined COMPLETE seal:followup_analyse e12 --reader-scope nla;Oracleprimaryunchanged',
        'status':'FIT' if f['fits_with_retrieval'] else 'NO_FIT_UNDER_44ff2b5f_TIMINGS'}
    dump(out/'PLAN.json',plan)
    dump(out/'FORECAST_SEAL.json',{'status':'E12_OBSERVED_RATE_FORECAST_FROZEN_BEFORE_COMPLETION','files':{n:sha(out/n) for n in ['PLAN.json','RETAINED_MANIFEST.json']}})
    return plan


class Gate:
    def __init__(self,path,plan):
        a=read(path);self.assignment=a;self.assignment_sha256=sha(path);self.plan=plan;self.started=None;self.first_science_epoch=None;self.completed=[];self.status='SETUP'
        if a.get('issuer')!='integrator' or a.get('experiment')!='E12_CONTEXT_COMPLETION' or a.get('gpu_count')!=1 or not a.get('pod_id'):raise ValueError('exact integrator E12 completion assignment required')
        for k in ['brief_registered','brief_pushed','external_hardstop_verified','hold_renewer_verified']:
            if a.get(k) is not True:raise ValueError(k+' evidence required')
        if a.get('brief_sha256')!=sha(ROOT/BRIEF):raise ValueError('44ff2b5f authority mismatch')
        required={'projects/g_agreement/understand/'+n+'.py' for n in ['e12_completion','e12_retry','followup_packed','followup_analyse','e12','cpu']}
        if not required<=set(a.get('source_files',{})):raise ValueError('complete source pins required')
        for name,digest in a['source_files'].items():
            p=(ROOT/name).resolve()
            if not p.is_relative_to(ROOT) or sha(p)!=digest:raise ValueError('source pin mismatch')
        for k in ['allocated_gpu_seconds','previous_gpu_seconds','provider_created_epoch','setup_deadline_epoch','deadline_epoch','setup_allowance_seconds']:
            if not isinstance(a.get(k),(float,int)) or not math.isfinite(a[k]):raise ValueError('finite timing fields required')
        if not 180<a['allocated_gpu_seconds']<=1200 or a['previous_gpu_seconds']!=0:raise ValueError('freshcompletioncap<=1200required')
        if not 0<a['setup_allowance_seconds']<=2400 or a['provider_created_epoch']>time.time():raise ValueError('setup/provider invalid')
        if a['setup_deadline_epoch']>a['provider_created_epoch']+a['setup_allowance_seconds'] or a['deadline_epoch']>min(STOP,a['provider_created_epoch']+a['setup_allowance_seconds']+a['allocated_gpu_seconds']):raise ValueError('setup/provider/programme deadline exceeds authority')
        if a.get('forecast_method')!='observed_bulk_mean_max_remaining_warmed_units_excluding_first':raise ValueError('22:15 observed rate rule required')
        self.cap=min(plan['forecast']['science_cap_seconds'],a['allocated_gpu_seconds']);self.setup_guard()
        os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',WANDB_MODE='disabled')

    def setup_guard(self):
        if self.started is not None:return self.guard()
        if time.time()>=min(self.assignment['setup_deadline_epoch'],self.assignment['deadline_epoch']-180,STOP-180):raise TimeoutError('setup or absolute deadline reached')

    def guard(self):
        if self.started is None:return self.setup_guard()
        if self.elapsed()>=self.cap-180 or time.time()>=min(STOP,self.assignment['deadline_epoch'])-180:raise TimeoutError('completion science/retrieval deadline reached')

    def elapsed(self):return 0. if self.started is None else time.monotonic()-self.started

    def start(self):
        if self.plan['forecast']['F_seconds']+180>self.cap:raise NoFit('observed forecast must fit before first science')
        if self.started is None:self.setup_guard();self.started=time.monotonic();self.first_science_epoch=time.time();self.status='RUNNING'
        self.write_state();self.guard()

    def write_state(self):
        if not hasattr(self,'out'):return
        p=self.out/'CLOCK.tmp';dump(p,{'status':self.status,'first_science_epoch':self.first_science_epoch,'science_cap_seconds':self.cap,'F_seconds':self.plan['forecast']['F_seconds'],
            'completed_context_units':self.completed,'expected_context_units':self.plan['missing_context_units'],'science_clock_resets':0,'retrieval_reserve_seconds':180});os.replace(p,self.out/'CLOCK.json')


def execute(a,g,resident=None):
    a.out.mkdir(parents=True,exist_ok=False);g.out=a.out;g.write_state();error=None;status='COMPLETE'
    try:
        f=g.plan['forecast'];dump(a.out/'FORECAST.json',f)
        dump(a.out/'FORECAST_SEAL.json',{'status':'E12_FROZEN_OBSERVED_RATE_BEFORE_MODEL_LOAD','files':{'FORECAST.json':sha(a.out/'FORECAST.json')}})
        if f['F_seconds']+180>g.cap:raise NoFit('NO_FIT: literal observed max-rate forecast and retrieval exceed1200s cap; no model load or science')
        if resident is None:resident=Residents(a,g)
        reader=resident.get();items=rows(a.inputs/'items.input.jsonl');templates=read(a.inputs/'templates.json');units=read(a.inputs/'nla_units.json')['context'];h=np.load(a.inputs/'acts42.npy',allow_pickle=False);spec=read(a.inputs/'provenance.json')['native_carriers']['nla']
        if sha(Path(resident.assets['nla'])/'av_base/tokenizer.json')!=spec['tokenizer_json_sha256']:raise ValueError('runtime tokenizer mismatch')
        if carrier(reader.tok,spec['request'],'','activation_only',spec['marker_token_id'])!=(reader.prompt_ids,reader.marker):raise ValueError('native carrier drift')
        # Warm unchanged scoring on neutral synthetic inputs; never re-score retained test units.
        first=units[g.plan['missing_context_units'][0]];n=len(first['indices']);synthetic=[{'id':f'WARMUP-{i}','feature':first['feature'],'text':'A neutral passage.','wrong_activation_index':i} for i in range(n)]
        score_unit(reader,'nla',{**first,'indices':list(range(n))},synthetic,np.ones((n,5120),np.float32),templates,spec);g.setup_guard()
        directory=a.out/'nla-context-units';directory.mkdir();g.start()
        for i in g.plan['missing_context_units']:
            g.guard();value=score_unit(reader,'nla',units[i],items,h,templates,spec);check_unit(value,units[i],items)
            dump(directory/f'unit-{i:05d}.json',value);g.completed.append(i);g.write_state();g.guard()
        if g.completed!=g.plan['missing_context_units']:raise ValueError('incomplete requested suffix')
    except Exception as exc:status='NO_FIT' if isinstance(exc,NoFit) else 'INCOMPLETE';error=type(exc).__name__+': '+str(exc)
    g.status=status;g.write_state();dump(a.out/'run.json',{'experiment':'E12_CONTEXT_COMPLETION','status':status,'error':error,'first_science_epoch':g.first_science_epoch,'elapsed_science_seconds':g.elapsed(),
        'science_clock_resets':0,'completed_context_units':g.completed,'expected_context_units':g.plan['missing_context_units'],'input_seal_sha256':g.plan['input_seal_sha256'],
        'prior_parent_seal_sha256':g.plan['prior_parent_seal_sha256'],'assignment_sha256':g.assignment_sha256,'assets_sha256':g.assignment.get('assets_sha256'),
        'checkpoint_load_counts':{} if resident is None else resident.loads,'Oracle_or_native_rerun':False})
    seal(a.out,[str(p.relative_to(a.out)) for p in a.out.rglob('*') if p.is_file()],'E12_CONTEXT_COMPLETION_'+status)
    print('HANDOFF E12 CONTEXT COMPLETION',status,a.out/'SCORE_SEAL.json',flush=True);return status


def join(inputs,prior,completion,out):
    inv=inventory(inputs,prior);verify(completion)
    if read(completion/'SCORE_SEAL.json')['status']!='E12_CONTEXT_COMPLETION_COMPLETE':raise ValueError('completion must be COMPLETE before join/analysis')
    run=read(completion/'run.json');missing=inv['missing_context_units']
    if run['completed_context_units']!=missing or run['expected_context_units']!=missing or run['input_seal_sha256']!=sha(inputs/'INPUT_SEAL.json') or run['prior_parent_seal_sha256']!=inv['prior_parent_seal_sha256']:raise ValueError('completion scope/lineage differs')
    plans=read(inputs/'nla_units.json');items=rows(inputs/'items.input.jsonl');scores=[];newpaths=sorted((completion/'nla-context-units').glob('unit-*.json'))
    if [int(p.stem.split('-')[1]) for p in newpaths]!=missing:raise ValueError('completion must contain exactly unscored units, no overlap')
    source_seals={prior:read(prior/'SCORE_SEAL.json'),completion:read(completion/'SCORE_SEAL.json')}
    for phase in ['native','context']:
        for i,unit in enumerate(plans[phase]):
            parent=completion if phase=='context' and i in missing else prior;p=parent/f'nla-{phase}-units'/f'unit-{i:05d}.json'
            relative=str(p.relative_to(parent))
            if relative not in source_seals[parent]['files']:raise ValueError('joined unit not bound by source seal')
            value=read(p);check_unit(value,unit,items);scores+=value
    expected={(r['id'],arm) for r in items for arm in ['activation_only','text_activation','text_only','text_wrong_activation']}
    if len(scores)!=len(expected) or {(r['id'],r['arm']) for r in scores}!=expected:raise ValueError('joined four-arm grid is incomplete/duplicated')
    out.mkdir(parents=True,exist_ok=False);reader=out/'nla';reader.mkdir();jsonl(reader/'scores.jsonl',scores)
    dump(reader/'provenance.json',{'reader':'nla','input_seal_sha256':sha(inputs/'INPUT_SEAL.json'),'native_prefix':'SUPPORTED_NATIVE_PREFIX','prior_parent_seal_sha256':inv['prior_parent_seal_sha256'],
        'completion_seal_sha256':sha(completion/'SCORE_SEAL.json'),'reused_native_units':len(inv['retained_native_units']),'reused_context_units':len(inv['retained_context_units']),
        'new_context_units':missing,'canonical_original_order':True,'no_model_calls_in_join':True,'labels_joined':False})
    seal(reader,['scores.jsonl','provenance.json'],'E12_FOUR_ARM_SCORES_SEALED_BEFORE_LABEL_JOIN');dump(out/'UNIT_JOIN.json',{'retained':inv,'completion_seal_sha256':sha(completion/'SCORE_SEAL.json'),'new_context_unit_hashes':{p.name:sha(p) for p in newpaths},'row_count':len(scores),'no_model_or_label_calls':True})
    (out/'PREFIX_PREFLIGHT.json').write_bytes((prior/'PREFIX_PREFLIGHT.json').read_bytes());dump(out/'run.json',{'experiment':'E12','readers':['nla'],'status':'COMPLETE','CPU_join_only':True,'new_GPU_hours':0,'original_NLA_run_status_preserved':'INCOMPLETE'})
    seal(out,[str(p.relative_to(out)) for p in out.rglob('*') if p.is_file()],'EXPLORATORY_E12_COMPLETE')


def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    a=s.add_parser('prepare')
    for k in ['inputs','prior','out']:a.add_argument('--'+k,type=Path,required=True)
    a=s.add_parser('preflight');a.add_argument('--plan',type=Path,required=True)
    a=s.add_parser('run')
    for k in ['inputs','plan','assets','assignment','out']:a.add_argument('--'+k,type=Path,required=True)
    a=s.add_parser('join')
    for k in ['inputs','prior','completion','out']:a.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    if a.command=='prepare':print(prepare(a.inputs,a.prior,a.out)['forecast'])
    elif a.command=='preflight':
        plan=read(a.plan);print(plan['status'],plan['forecast'])
        if not plan['forecast']['fits_with_retrieval']:raise SystemExit(2)
    elif a.command=='join':join(a.inputs,a.prior,a.completion,a.out)
    else:
        verify(a.inputs,'INPUT_SEAL.json');plan=read(a.plan);assignment=read(a.assignment)
        if assignment.get('completion_plan_sha256')!=sha(a.plan) or assignment.get('input_seal_sha256')!=sha(a.inputs/'INPUT_SEAL.json') or plan['input_seal_sha256']!=sha(a.inputs/'INPUT_SEAL.json') or assignment.get('assets_sha256')!=sha(a.assets):raise ValueError('plan/input/assets assignment binding mismatch')
        if len(plan['missing_context_units'])!=157 or plan['missing_context_units']!=list(range(1514,1671)):raise ValueError('only registered157unit suffix authorised')
        execute(a,Gate(a.assignment,plan))


if __name__=='__main__':main()
