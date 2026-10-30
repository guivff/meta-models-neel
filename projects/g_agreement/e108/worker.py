"""§219 single-pod capture/base64/native readers, with retained timing pilots."""
import argparse,json,math,os,signal,threading,time
from pathlib import Path
import numpy as np
from .runtime import ROOT,Runtime108
from contract import read,write,sha,seal,verify,require,deadline
from hardware204 import production_gate,finite
from worker import batches,Clock,NoFit

SEED=20261029;N=1008;P=84;DIM=5120;BATCH=32;CAP=5400
INPUT_FIELDS={'id','prompt','input_ids','read_position'}


def load(inp,input_sha):
    s=verify(inp,'INPUT_SEAL.json',input_sha)
    names={'PUBLIC_INPUTS.json','PLACEBO_SPECS.json','STAGE_REQUEST.json'}
    require(set(s['files'])==names and {p.name for p in inp.iterdir()}==names|{'INPUT_SEAL.json'},'public-only E108 archive')
    raw=read(inp/'PUBLIC_INPUTS.json');spec=read(inp/'PLACEBO_SPECS.json');ids=[x['id'] for x in raw]
    require(len(raw)==N and len(set(ids))==N and all(set(x)==INPUT_FIELDS for x in raw),'1008 unchanged public prefixes')
    for x in raw:
        require(isinstance(x['prompt'],str) and x['prompt'].endswith(':') and x['input_ids'] and
            all(type(t)is int and t>=0 for t in x['input_ids']) and x['read_position']==len(x['input_ids'])-1,'raw final read token')
    require(len(spec)==P and len({x['id'] for x in spec})==P and not set(ids)&{x['id'] for x in spec},'84 unique placebo IDs')
    require(all(set(x)=={'id','reference_id','generator','seed'} and x['reference_id'] in ids and
        x['generator']=='E76' and x['seed']==SEED for x in spec),'frozen placebo references')
    return [dict(id=x['id'],text=x['prompt'],ids=x['input_ids'],read_index=x['read_position']) for x in raw],spec,read(inp/'STAGE_REQUEST.json')


def text_jobs(items):
    return sorted(batches(items,BATCH,equal_length=True),key=lambda xs:(-len(xs),-len(xs[0]['ids'])))


def make_placebos(items,spec,acts):
    import sys
    sys.path.insert(0,str(ROOT/'results/g_agreement/understand/e76'))
    from common76 import norm_match
    ix={x['id']:i for i,x in enumerate(items)}
    z=np.random.default_rng(SEED).standard_normal((P,DIM)).astype(np.float32)
    output={};norms={}
    for layer in (42,44):
        require(acts[layer].shape==(N,DIM) and np.isfinite(acts[layer]).all(),'finite complete native capture')
        targets=np.linalg.norm(acts[layer][[ix[x['reference_id']] for x in spec]].astype(np.float64),axis=1)
        output[layer]=norm_match(z,targets);norms[layer]=targets.tolist()
    return output,dict(seed=SEED,generator='E76 standard_normal fp32 + common76.norm_match',
        reference_ids=[x['reference_id'] for x in spec],native_reference_norms=norms,
        gaussian_sha256=__import__('hashlib').sha256(z.tobytes()).hexdigest(),normalization='individual frozen reference prompt, each native layer separately')


class RunClock(Clock):
    def __init__(self,out,end,b,created):
        super().__init__(out,end,{},b);self.created=created;self.setup=[];self.frozen=False;self.timer=None
    def arm(self):
        if self.timer:self.timer.cancel()
        self.timer=threading.Timer(max(0,self.end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));self.timer.daemon=True;self.timer.start()
    def stop(self):
        if self.timer:self.timer.cancel()
    def setup_call(self,phase,load,warm):
        start=time.monotonic();self.call(phase,load);self.call(phase+'_warmup_discarded',warm)
        elapsed=time.monotonic()-start
        # Own transfer/extract/import is actual creation-through-first-load-start.
        staging=max(0,time.time()-self.created-elapsed) if not self.setup else self.setup[0]['staging_seconds']
        self.setup.append(dict(phase=phase,load_and_warmup_seconds=elapsed,staging_seconds=staging,includes_staging=True,seconds=staging+elapsed))
        write(self.out/'SETUP_PROFILES.json',self.setup,replace=True)
    def forecast_all(self,remaining,reloads):
        self.check();require(set(remaining)=={'base64','oracle_native','nla_native'},'all three work phases')
        require(all(self.observed.get(k) for k in remaining),'real timing pilots before complete admission')
        rates={k:max(self.observed[k]) for k in remaining}
        setup=max(x['seconds'] for x in self.setup)
        upper=time.time()-self.created+reloads*setup+1.25*sum(remaining[k]*rates[k] for k in remaining)+60
        fits=self.created+upper<=self.end
        value=dict(experiment='E108',status='ADMIT' if fits else 'NO_FIT',estimator='elapsed original custody + max own measured setup incl staging per future reload +1.25 remaining measured work +60s retrieval',
            original_created_epoch=self.created,maximum_measured_setup_seconds=setup,remaining=remaining.copy(),max_measured_batch_seconds=rates,
            future_reloads=reloads,projected_total_custody_seconds=upper,deadline_epoch=self.end,timing_on_production_pod=True,pilots_retained=True)
        write(self.out/'FORECAST.json',value,replace=True)
        if not fits:raise NoFit('complete E108 forecast exceeds fixed creation cap')
        if not self.frozen:
            self.end=min(self.end,self.created+math.ceil(upper));self.frozen=True
            write(self.out/'CAP_ADMISSION.json',dict(value,production_cap_seconds=self.end-self.created,absolute_deadline_epoch=self.end))
            if self.timer:self.arm()


def acquire(items,spec,b,c,out,binding):
    jobs=out/'jobs';jobs.mkdir();capture=out/'capture';capture.mkdir()
    tj=text_jobs(items);require(len(tj)>=3 and all(len(x)==BATCH for x in tj[:3]),'three full base timing pilots')
    units=[dict(id=x['id'],kind='native') for x in items]+[dict(id=x['id'],kind='placebo') for x in spec]
    nj=[list(range(i,min(i+BATCH,len(units)))) for i in range(0,len(units),BATCH)]
    remaining=dict(base64=len(tj),oracle_native=len(nj),nla_native=len(nj));complete={'base64':set(),'oracle_native':set(),'nla_native':set()}
    b.native_batch_size=BATCH;b.seed(SEED)
    def warm_text():return b.text64(b.synthetic())
    c.setup_call('base_setup',b.load_base,warm_text);b.check_tokens(items)
    c.call('capture_warmup_discarded',b.warm_capture)
    parts={42:[],44:[]}
    for chunk in batches(items,BATCH):
        got=c.call('capture',lambda:b.capture(chunk),real=True)
        for l in parts:
            require(got[l].shape==(len(chunk),DIM) and np.isfinite(got[l]).all(),'finite native captures')
            parts[l].append(np.asarray(got[l],dtype=np.float32))
    acts={l:np.concatenate(h) for l,h in parts.items()}
    for l,h in acts.items():np.save(capture/f'acts{l}.npy',h,allow_pickle=False)
    write(capture/'ORDER.json',[x['id'] for x in items]);seal(capture,'CAPTURE_SEAL.json',**binding,status='COMPLETE')
    placebo,audit=make_placebos(items,spec,acts);pd=out/'placebo';pd.mkdir()
    for l,h in placebo.items():np.save(pd/f'acts{l}.npy',h,allow_pickle=False)
    write(pd/'CALIBRATION.json',audit);write(pd/'ORDER.json',[x['id'] for x in spec]);seal(pd,'PLACEBO_SEAL.json',**binding,status='COMPLETE_BEFORE_READERS')
    arrays={l:np.concatenate([acts[l],placebo[l]]) for l in acts}
    def base_job(i):
        chunk=tj[i];raw=c.call('base64',lambda:b.text64([x['ids'] for x in chunk]),real=True)
        require(len(raw)==len(chunk) and finite(raw),'finite exact greedy64 outputs')
        write(jobs/f'base64_{i:04d}.json',[dict(id=x['id'],channel='base64',max_new_tokens=64,**r) for x,r in zip(chunk,raw)])
        complete['base64'].add(i);remaining['base64']-=1
    def native_job(reader,i):
        ix=nj[i];layer=44 if reader=='oracle' else 42;h=arrays[layer][ix].copy();before=h.tobytes()
        raw=c.call(reader+'_native',lambda:b.native(reader,h),real=True)
        require(len(raw)==len(ix) and all(len(g)==1 for g in raw) and finite(raw) and h.tobytes()==before,'one finite native readout and immutable vector')
        write(jobs/f'{reader}_{i:04d}.json',[dict(id=units[k]['id'],kind=units[k]['kind'],reader=reader,layer=layer,repeat=0,**g[0]) for k,g in zip(ix,raw)])
        complete[reader+'_native'].add(i);remaining[reader+'_native']-=1
    def warm_native(reader):
        h=np.zeros((BATCH,DIM),np.float32);h[:,0]=1
        return b.native(reader,h)
    for i in range(3):base_job(i)
    c.setup_call('oracle_setup',b.load_oracle,lambda:warm_native('oracle'));native_job('oracle',0)
    c.setup_call('nla_setup',b.load_nla,lambda:warm_native('nla'));native_job('nla',0)
    c.forecast_all(remaining,2)
    for i in range(1,len(nj)):c.forecast_all(remaining,2);native_job('nla',i)
    # Release NLA explicitly before reloading the base via the existing loader.
    b.readers=None
    import gc
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():torch.cuda.empty_cache()
    except ImportError:pass
    c.forecast_all(remaining,2);c.setup_call('base_reload',b.load_base,warm_text)
    for i in range(3,len(tj)):c.forecast_all(remaining,1);base_job(i)
    c.forecast_all(remaining,1);c.setup_call('oracle_reload',b.load_oracle,lambda:warm_native('oracle'))
    for i in range(1,len(nj)):c.forecast_all(remaining,0);native_job('oracle',i)
    require(not any(remaining.values()),'full 1008/2184 grid; no shrinking')
    c.forecast_all(remaining,0)
    write(out/'COUNTS.json',dict(base_continuations=N,base_max_new_tokens=64,oracle_native=N,nla_native=N,oracle_placebo=P,nla_placebo=P,readers=2,all_items_preserved=True))
    seal(jobs,'JOBS_SEAL.json',**binding,status='COMPLETE')
    return 'COMPLETE'


def main():
    p=argparse.ArgumentParser()
    for k in ('inputs','assets','assignment','out','source-seal'):p.add_argument('--'+k,type=Path,required=True)
    for k in ('input-sha','source-sha'):p.add_argument('--'+k,required=True)
    p.add_argument('--hardware-receipt',type=Path);a=p.parse_args()
    verify(ROOT,str(a.source_seal.resolve().relative_to(ROOT)),a.source_sha)
    items,spec,limits=load(a.inputs,a.input_sha);ass=read(a.assignment)
    require(limits['status']=='READY_E108_OPERATOR_ADMISSION_REQUIRED' and limits['cap_seconds']==CAP and limits['cumulative_cap_seconds']==CAP,'registered E108 cap')
    require(ass['source_seal_sha256']==a.source_sha and ass['input_seal_sha256']==a.input_sha and ass['assets_sha256']==sha(a.assets),'source/input/asset binding')
    require(ass['pod_id']==os.environ.get('RUNPOD_POD_ID') and ass['pod_created_epoch']==ass['custody_start_epoch'] and ass['external_guard_armed'] and ass['incremental_backup_armed'],'own original creation and guards')
    require(ass['gpu_type']=='H200','registered one-pod H200 operator binding')
    require(ass.get('analysis_adapter_cpu_tests_passed') is True and len(ass.get('analysis_adapter_commit',''))==40 and len(ass.get('analysis_adapter_sha256',''))==64,'precommitted analysis adapter and tests')
    end=deadline(ass,limits,time.time());hardware=production_gate(ass,a.hardware_receipt,a.assets,['oracle','nla','text'])
    a.out.mkdir(parents=True,exist_ok=False);write(a.out/'ASSIGNMENT.json',ass);write(a.out/'HARDWARE.json',hardware)
    b=Runtime108(a.assets);b.hardware_assignment=ass;c=RunClock(a.out,end,b,ass['pod_created_epoch']);c.arm();status='FAILED'
    binding=dict(experiment='E108',source_seal_sha256=a.source_sha,input_seal_sha256=a.input_sha,pod_id=ass['pod_id'],gpu_type=ass['gpu_type'])
    try:status=acquire(items,spec,b,c,a.out,binding)
    except NoFit as e:status='NO_FIT';write(a.out/'NO_FIT.json',dict(reason=str(e),model_loaded=b.model is not None or b.readers is not None,scope_reduced=False))
    except BaseException as e:write(a.out/'FAILURE.json',dict(error_type=type(e).__name__,model_loaded=b.model is not None or b.readers is not None));raise
    finally:
        c.stop()
        generated=sorted((q for q in (a.out/'jobs').glob('*.json') if q.is_file()),key=lambda q:q.stat().st_mtime_ns)
        first=generated[0] if generated else None
        seal(a.out,'OUTPUT_SEAL.json',**binding,status=status,first_output_utc=__import__('datetime').datetime.fromtimestamp(first.stat().st_mtime,__import__('datetime').timezone.utc).isoformat() if first else 'unknown',
            first_output_evidence=dict(member=str(first.relative_to(a.out)),sha256=sha(first),mtime_ns=first.stat().st_mtime_ns) if first else None)

if __name__=='__main__':main()
