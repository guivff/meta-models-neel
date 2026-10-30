"""§99 f70894e1: NLA-only E12, all paths warmed/timed before bulk admission.

The original scoring function and frozen inputs are reused verbatim. First three
timed units per path are retained once and count as science. Missing timings are
unknown, never zero. No production beyond these pilots until the full gate passes.
"""
import argparse
import math
import os
import statistics
import time
from pathlib import Path
import numpy as np
from .cpu import ROOT,read,rows,dump,sha,verify,seal
from .e12 import carrier
from .followup_packed import score_unit,jsonl

BRIEF='results/g_agreement/understand/e12/BRIEF_UNDERSTAND.f70894e1.md'
PATHS=('nla_native','nla_context')
STOP=__import__('datetime').datetime(2026,10,28,22,59,tzinfo=__import__('datetime').timezone.utc).timestamp()
REQUIRED={'projects/g_agreement/understand/'+n+'.py' for n in ['e12_retry','followup_packed','followup_analyse','cpu','e12']}


class NoFit(TimeoutError):pass


class Gate:
    def __init__(self,path,counts):
        a=read(path);self.assignment=a;self.counts=counts;self.started=None;self.first_science_epoch=None
        self.samples={k:[] for k in PATHS};self.completed={k:0 for k in PATHS};self.warmups={}
        self.status='SETUP';self.admitted=False
        if set(counts)!=set(PATHS) or any(type(n) is not int or n<3 for n in counts.values()):raise ValueError('both frozen timing paths required')
        if a.get('issuer')!='integrator' or a.get('experiment')!='E12' or a.get('readers')!=['nla'] or a.get('gpu_count')!=1 or not a.get('pod_id'):raise ValueError('exact integrator NLA-only one-pod assignment required')
        for k in ['external_hardstop_verified','hold_renewer_verified','brief_registered','brief_pushed']:
            if a.get(k) is not True:raise ValueError(k+' evidence required')
        if a.get('brief_sha256')!=sha(ROOT/BRIEF):raise ValueError('f70894e1 authority mismatch')
        if not REQUIRED<=set(a.get('source_files',{})):raise ValueError('complete source pins required')
        for name,digest in a['source_files'].items():
            p=(ROOT/name).resolve()
            if not p.is_relative_to(ROOT) or sha(p)!=digest:raise ValueError('source pin mismatch')
        for k in ['allocated_gpu_seconds','previous_gpu_seconds','provider_created_epoch','setup_deadline_epoch','deadline_epoch','setup_allowance_seconds']:
            if not isinstance(a.get(k),(int,float)) or not math.isfinite(a[k]):raise ValueError('finite timing fields required')
        self.reserved=float(a['allocated_gpu_seconds'])
        if not 180<self.reserved<=3600 or a['previous_gpu_seconds']!=0:raise ValueError('fresh attempt <=3600 seconds required')
        if not 0<a['setup_allowance_seconds']<=2400 or a['provider_created_epoch']>time.time():raise ValueError('setup/provider clock invalid')
        if a['setup_deadline_epoch']>a['provider_created_epoch']+a['setup_allowance_seconds']:raise ValueError('setup exceeds 2400 seconds')
        if a['deadline_epoch']>min(STOP,a['provider_created_epoch']+a['setup_allowance_seconds']+self.reserved):raise ValueError('absolute deadline exceeds reservation/programme')
        if a.get('forecast_method')!='all_paths_one_unscored_warmup_plus_three_retained_units':raise ValueError('full warmed timing method required')
        self.cap=None  # unknown full F is not a provisional zero contribution
        self.setup_guard()
        os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',WANDB_MODE='disabled')

    def setup_guard(self):
        if self.started is not None:return self.guard()
        if time.time()>=min(self.assignment['setup_deadline_epoch'],self.assignment['deadline_epoch']-180,STOP-180):raise TimeoutError('setup allowance or absolute hardstop reached')

    def start(self):
        if self.started is None:
            self.setup_guard()
            if set(self.warmups)!=set(PATHS):raise ValueError('one unscored warm-up on every path required before science')
            self.started=time.monotonic();self.first_science_epoch=time.time();self.status='RUNNING'
        self.write_state();self.guard()

    def elapsed(self):return 0. if self.started is None else time.monotonic()-self.started

    def forecast(self):
        paths={}
        for key in PATHS:
            values=self.samples[key];median=statistics.median(values) if len(values)==3 else None
            paths[key]={'units':self.counts[key],'completed_units':self.completed[key],
                'unscored_warmup':self.warmups.get(key),'timed_unit_seconds':values,
                'median_seconds':median,'forecast_seconds':None if median is None else median*self.counts[key]}
        complete=all(p['median_seconds'] is not None for p in paths.values())
        total=sum(p['forecast_seconds'] for p in paths.values()) if complete else None
        cap=min(self.reserved,1.5*total+360,3600.) if complete else None
        return {'paths':paths,'all_paths_measured':complete,'F_seconds':total,'science_cap_seconds':cap,
            'first_science_epoch':self.first_science_epoch,'elapsed_science_seconds':self.elapsed(),
            'science_clock_resets':0,'bulk_admitted':self.admitted,'reserved_ceiling_seconds':self.reserved,
            'unknown_paths_are_zero':False,'timed_units_retained_once':True,'timed_units_count_as_science':True,
            'status':self.status,'retrieval_reserve_seconds':180,
            'pilot_watchdog_seconds':self.reserved if cap is None else None}

    def write_state(self):
        if not hasattr(self,'out'):return
        temp=self.out/'CLOCK.tmp';dump(temp,self.forecast());os.replace(temp,self.out/'CLOCK.json')

    def guard(self):
        if self.started is None:return self.setup_guard()
        # During the bounded six-unit pilot only, the reservation is the hard limit.
        # The complete formula is applied to the original first-science clock before bulk.
        limit=self.reserved if self.cap is None else self.cap
        if self.elapsed()>=limit-180 or time.time()>=min(STOP,self.assignment['deadline_epoch'])-180:raise TimeoutError('science cap or retrieval reserve reached')

    def warm(self,key,seconds,unit_index):
        self.setup_guard()
        if self.started is not None or key not in PATHS or key in self.warmups or not math.isfinite(seconds) or seconds<=0:raise ValueError('exactly one setup warm-up per path required')
        self.warmups[key]={'seconds':seconds,'unit_index':unit_index,'scored':False,'retained':False}
        self.write_state()

    def record(self,key,seconds):
        if key not in PATHS or not math.isfinite(seconds) or seconds<=0:raise ValueError('positive real unit timing required')
        if not self.admitted and self.completed[key]>=3:raise ValueError('bulk forbidden before every path is measured and admitted')
        if self.completed[key]>=self.counts[key]:raise ValueError('duplicate or excess unit')
        self.completed[key]+=1
        if len(self.samples[key])<3:self.samples[key].append(seconds)
        self.write_state();self.guard()

    def admit_remaining(self):
        report=self.forecast()
        if not report['all_paths_measured'] or set(self.warmups)!=set(PATHS):raise ValueError('every path needs unscored warm-up plus 3 timed units before admission')
        self.cap=report['science_cap_seconds']
        remaining=sum(p['median_seconds']*(p['units']-p['completed_units']) for p in report['paths'].values())
        report.update(remaining_forecast_seconds=remaining,fit=self.elapsed()+1.5*remaining+180<=self.cap)
        dump(self.out/'FULL_WARMED_FORECAST.json',report)
        dump(self.out/'FORECAST_SEAL.json',{'status':'E12_ALL_PATH_FORECAST_BEFORE_BULK_ADMISSION',
            'files':{'FULL_WARMED_FORECAST.json':sha(self.out/'FULL_WARMED_FORECAST.json')}})
        self.write_state()
        if not report['fit']:raise NoFit('NO_FIT: full warmed forecast exceeds min(1.5F+360,3600) including retrieval reserve')
        self.guard();self.admitted=True;self.write_state();return report


class Residents:
    """Only the NLA verbalizer; one object shared by setup, pilots and production."""
    def __init__(self,a,gate):
        self.a=a;self.gate=gate;self.reader=None;self.loads={};self.events=[]
        gate.setup_guard()
        from projects.g_agreement.blindspot.run import _assets
        self.assets=_assets(a.assets,('nla',));self.assets_sha=sha(a.assets);gate.setup_guard()

    def get(self):
        if sha(self.a.assets)!=self.assets_sha:raise ValueError('asset manifest changed')
        if self.reader is None:
            if self.gate.started is not None or self.loads:raise RuntimeError('NLA checkpoint load/reload inside science forbidden')
            self.gate.setup_guard()
            import common
            from mats.readers.nla import load_nla
            self.loads['nla_verbalizer']=1
            self.reader=load_nla(root=self.assets['nla'],load_ar=False)
            self.events.append({'event':'load','model':'nla_verbalizer','PID':os.getpid(),'epoch':time.time(),'load_ar':False})
            self.gate.setup_guard()
        return self.reader


def collect(a,resident,g,root):
    items=rows(a.inputs/'items.input.jsonl');templates=read(a.inputs/'templates.json')
    plans=read(a.inputs/'nla_units.json');h=np.load(a.inputs/'acts42.npy',allow_pickle=False)
    spec=read(a.inputs/'provenance.json')['native_carriers']['nla'];reader=resident.get()
    if sha(Path(resident.assets['nla'])/'av_base/tokenizer.json')!=spec['tokenizer_json_sha256']:raise ValueError('runtime tokenizer mismatch')
    if carrier(reader.tok,spec['request'],'','activation_only',spec['marker_token_id'])!=(reader.prompt_ids,reader.marker):raise ValueError('native carrier mismatch')
    functions={phase:(lambda u:score_unit(reader,'nla',u,items,h,templates,spec)) for phase in ['native','context']}
    # Exactly one discarded warm-up per timing path, using a frozen maximum-size unit.
    for phase in ['native','context']:
        units=plans[phase];ix=max(range(len(units)),key=lambda i:(units[i].get('head_length',0),len(units[i]['indices'])))
        g.setup_guard();t=time.monotonic();functions[phase](units[ix]);g.warm('nla_'+phase,time.monotonic()-t,ix)
    dump(root/'PREFIX_PREFLIGHT.json',{'nla':'SUPPORTED_NATIVE_PREFIX','olens':{'status':'COMPLETE_SEALED_PRIMARY_IN_PRIOR_PACK','rerun':False}})
    results={phase:{} for phase in plans}
    for phase in ['native','context']:(root/f'nla-{phase}-units').mkdir()
    g.start()
    def unit(phase,i):
        if not g.admitted and g.completed['nla_'+phase]>=3:raise ValueError('no bulk scoring before full admission')
        g.guard();t=time.monotonic();value=functions[phase](plans[phase][i]);elapsed=time.monotonic()-t
        results[phase][i]=value;dump(root/f'nla-{phase}-units'/f'unit-{i:05d}.json',value)
        g.record('nla_'+phase,elapsed)
    # All timing paths first. Each timed output is retained and is never rescored.
    for phase in ['native','context']:
        for i in range(3):unit(phase,i)
    g.admit_remaining()
    for phase in ['native','context']:
        for i in range(3,len(plans[phase])):unit(phase,i)
        directory=root/f'nla-{phase}-units';dump(directory/'WARMED_FORECAST.json',g.forecast()['paths']['nla_'+phase])
        seal(directory,[p.name for p in directory.iterdir() if p.is_file()],'FOLLOWUP_PHASE_COMPLETE_BEFORE_LABEL_JOIN')
    scores=[r for phase in ['native','context'] for i in range(len(plans[phase])) for r in results[phase][i]]
    expected={(r['id'],arm) for r in items for arm in ['activation_only','text_activation','text_only','text_wrong_activation']}
    if len(scores)!=len(expected) or {(r['id'],r['arm']) for r in scores}!=expected:raise ValueError('incomplete four-arm grid')
    out=root/'nla';out.mkdir();jsonl(out/'scores.jsonl',scores)
    dump(out/'provenance.json',{'input_seal_sha256':sha(a.inputs/'INPUT_SEAL.json'),'reader':'nla','native_prefix':'SUPPORTED_NATIVE_PREFIX',
        'right_padding_only':True,'text_only':'no injection; own placeholder embedding/residual retained',
        'batch':'both candidates jointly;equal-headlength context units;frozen order',
        'operational_authority':'f70894e1','all_paths_timed_before_bulk':True})
    seal(out,['scores.jsonl','provenance.json'],'E12_FOUR_ARM_SCORES_SEALED_BEFORE_LABEL_JOIN');g.guard()


def execute(a,g):
    a.out.mkdir(exist_ok=False,parents=True);g.out=a.out;g.write_state();resident=None;error=None;status='COMPLETE'
    try:
        resident=Residents(a,g);collect(a,resident,g,a.out)
    except Exception as exc:
        status='NO_FIT' if isinstance(exc,NoFit) else 'INCOMPLETE';error=type(exc).__name__+': '+str(exc)
    g.status=status;g.write_state()
    dump(a.out/'run.json',{'experiment':'E12','readers':['nla'],'status':status,'error':error,'PID':os.getpid(),
        'first_science_epoch':g.first_science_epoch,'elapsed_science_seconds':g.elapsed(),'clock_resets':0,
        'science_cap_seconds':g.cap,'reserved_ceiling_seconds':g.reserved,'forecast':g.forecast(),
        'checkpoint_load_counts':{} if resident is None else resident.loads,'events':[] if resident is None else resident.events,
        'input_seal_sha256':sha(a.inputs/'INPUT_SEAL.json'),'Oracle_rerun':False,'E1b_E7_executed':False})
    seal(a.out,[str(p.relative_to(a.out)) for p in a.out.rglob('*') if p.is_file()],'EXPLORATORY_E12_'+status)
    print('HANDOFF E12 NLA-only',status,a.out/'SCORE_SEAL.json',flush=True)
    return status


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['inputs','assets','assignment','out']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();verify(a.inputs,'INPUT_SEAL.json')
    if len(rows(a.inputs/'items.input.jsonl'))!=2100:raise ValueError('all 2100 frozen items required')
    if any(a.inputs.rglob('*.DO_NOT_STAGE.*')):raise ValueError('label-bearing files forbidden')
    plans=read(a.inputs/'nla_units.json');g=Gate(a.assignment,{'nla_'+k:len(plans[k]) for k in ['native','context']})
    if g.assignment.get('input_seal_sha256')!=sha(a.inputs/'INPUT_SEAL.json') or g.assignment.get('assets_sha256')!=sha(a.assets):raise ValueError('assignment input/assets binding mismatch')
    execute(a,g)


if __name__=='__main__':main()
