"""E96 retained stochastic sampling and answer-blind reconstruction; one row per shard.

Only sealed IDs/native activations reach this worker. Greedy is never generated.
All calls use immutable global batch seeds; completed batch files are never replaced.
External creation-based pod shutdown is required in addition to this watchdog.
"""
import argparse
import datetime
import gc
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from .reconstructor_check import digest, write
from .prepare_smoke_inputs import verify
from .aggregate import reconstruction_error

SEED=20261028
BATCH=32
CLOSE='</explanation>'


def utc(epoch=None):
    return datetime.datetime.fromtimestamp(time.time() if epoch is None else epoch,datetime.timezone.utc).isoformat()


def jobs(plan,slot,reader):
    for row in plan['rows']:
        if row['slot']==slot and reader in row['readers']:
            for start in range(0,640,BATCH):
                yield row,start


def check_assignment(a,plan):
    if a['experiment']!='E96' or a['slot'] not in range(3) or a['gpu_count']!=1:raise ValueError('assignment')
    if a['input_seal_sha256']!=digest(a['inputs_path']+'/INPUT_SEAL.json'):raise ValueError('input binding')
    if a['deadline_epoch']-a['created_epoch']>36000 or time.time()>=a['deadline_epoch']-180:raise ValueError('allocation deadline')
    if a['projected_all_track_upper_usd']>1500 or not a['external_guard_armed']:raise ValueError('spend/custody admission')
    if plan['aggregator_sha256']!=digest(Path(__file__).with_name('aggregate.py')):raise ValueError('aggregator changed')
    if plan['total_samples']!=53120 or sum(len(r['readers']) for r in plan['rows'])!=83:raise ValueError('clarified inventory')
    return a['deadline_epoch']


class Clock:
    def __init__(self,out,end):self.out,self.end,self.events=out,end,[];self.first=None
    def check(self):
        if time.time()>=self.end-180:raise TimeoutError('retrieval reserve')
    def call(self,phase,fn):
        self.check();t=time.monotonic();v=fn();seconds=time.monotonic()-t
        self.events.append({'phase':phase,'seconds':seconds,'completed_utc':utc()})
        write(self.out/'TIMING.json',self.events);print(json.dumps(self.events[-1]),flush=True);self.check();return v
    def output(self,path):
        if self.first is None:
            self.first=utc(path.stat().st_mtime)
            write(self.out/'FIRST_OUTPUT.json',{'first_output_utc':self.first,'source':'pod output file mtime','file':str(path.relative_to(self.out)),'mtime_ns':path.stat().st_mtime_ns})
            print('FIRST_OUTPUT_UTC '+self.first,flush=True)


class Backend:
    def __init__(self,assets,official,whitener):self.assets,self.official,self.whitener=assets,official,whitener;self.model=None
    def release(self):
        import torch
        self.model=None;gc.collect();torch.cuda.empty_cache()
    def load(self,reader,phase):
        import common
        import torch
        self.release()
        from projects.g_agreement.blindspot.run import _load_oracle
        from mats.readers.nla import load_nla
        from .reconstructor_check import load_decoder_only
        from projects.g_agreement.w_claims.ar import load_reconstructor
        if phase=='generate':
            self.model=_load_oracle(self.assets) if reader=='oracle' else load_nla(root=self.assets['nla'],load_ar=False,enable_thinking=False)
        elif reader=='oracle':self.model=load_reconstructor(self.official,self.whitener,self.assets['ar'],self.assets['model'])
        else:
            # Same tested decoder-only wrapper and pinned manifest as the smoke.
            self.model=load_decoder_only(Path(self.assets['_manifest']))
    def generate(self,reader,h,seed):
        import torch
        from mats.readers.nla import Sampling,extract_explanation
        torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
        v=torch.as_tensor(h).float()
        if reader=='oracle':
            raw=[x[0] for x in self.model.verbalize(v,44,k=1,sampling=Sampling(temperature=1.,top_p=.95,top_k=0,max_new_tokens=128),batch=BATCH)]
            return [dict(raw=x,text=x,malformed=False,truncated=None,max_new_tokens=128) for x in raw]
        from transformers import StoppingCriteria,StoppingCriteriaList
        tok=self.model.tok;prompt=self.model.prompt_ids
        class Closed(StoppingCriteria):
            def __call__(self,ids,scores,**kw):
                text=tok.batch_decode(ids[:,len(prompt):],skip_special_tokens=True)
                return torch.tensor([CLOSE in s for s in text],device=ids.device,dtype=torch.bool)
        ids=torch.tensor([prompt]*len(v),device=self.model.device)
        with torch.inference_mode(),self.model._inject(v.to(self.model.device)):
            output=self.model.av.generate(input_ids=ids,attention_mask=torch.ones_like(ids),do_sample=True,temperature=1.,top_p=.95,top_k=0,max_new_tokens=512,pad_token_id=tok.pad_token_id,stopping_criteria=StoppingCriteriaList([Closed()]))
        raw=tok.batch_decode(output[:,len(prompt):],skip_special_tokens=True)
        return [dict(raw=s,text=extract_explanation(s) or s,malformed=extract_explanation(s) is None,truncated=CLOSE not in s,max_new_tokens=512) for s in raw]
    def reconstruct(self,reader,texts):
        from projects.g_agreement.w_claims.ar import reconstruct
        return reconstruct(*self.model[:2],texts) if reader=='oracle' else self.model.reconstruct(texts,batch=8)


def execute(inputs,plan,slot,backend,clock,out):
    import numpy as np
    for phase in ('generate','reconstruct'):
        for reader in ('oracle','nla'):
            own=list(jobs(plan,slot,reader))
            if not own:continue
            clock.call(phase+'_'+reader+'_setup',lambda:backend.load(reader,phase))
            observed=[]
            for n,(row,start) in enumerate(own):
                dest=out/row['key']/reader;dest.mkdir(parents=True,exist_ok=True)
                source=inputs/row['key'];ids=json.loads((source/'ids.json').read_text())
                layer=44 if reader=='oracle' else 42
                h=np.load(source/f'acts{layer}.npy',allow_pickle=False)
                ix=[k//16 for k in range(start,start+BATCH)]
                file=dest/f'{phase}.{start:04d}.json'
                if file.exists():raise ValueError('completed output must never be overwritten: '+str(file))
                if phase=='generate':
                    seed=SEED+row['batch_seed_offset']+start
                    records=clock.call('generate_'+reader,lambda:backend.generate(reader,h[ix],seed))
                    if len(records)!=BATCH:raise ValueError('generation grid')
                    for k,r in enumerate(records):
                        r.update(id=ids[ix[k]],sample_index=(start+k)%16,reader=reader,row_key=row['key'],batch_seed=seed)
                else:
                    records=json.loads((dest/f'generate.{start:04d}.json').read_text())
                    valid=[i for i,r in enumerate(records) if not r['malformed']]
                    pred=clock.call('reconstruct_'+reader,lambda:backend.reconstruct(reader,[records[i]['text'] for i in valid])) if valid else None
                    if pred is not None:
                        pred=pred.detach().float().cpu().numpy()
                        if pred.shape!=(len(valid),5120):raise ValueError('reconstruction shape')
                    errors={i:reconstruction_error(p,h[ix[i]]) for i,p in zip(valid,pred if pred is not None else [])}
                    records=[{'id':r['id'],'sample_index':r['sample_index'],'reader':reader,'row_key':row['key'],'parsed':not r['malformed'],'raw_native_mse':errors.get(i)} for i,r in enumerate(records)]
                write(file,records);clock.output(file)
                if clock.events[-1]['phase']==phase+'_'+reader:observed.append(clock.events[-1]['seconds'])
                # Retain all measurements and all outputs. No cap reset or output reselection.
                forecast=1.5*(sum(observed)/len(observed))*(len(own)-n-1) if observed else 0
                write(out/'FORECAST.json',{'phase':phase+'_'+reader,'remaining_same_phase_seconds':forecast,'deadline_epoch':clock.end,'observed_batches':len(observed),'completed_utc':utc()})
                if time.time()+forecast>=clock.end-180:raise TimeoutError('remaining same-phase forecast does not fit')
            backend.release()


def main():
    p=argparse.ArgumentParser()
    for k in ('inputs','assignment','assets','official','whitener','out','source-seal'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--preflight-only',action='store_true');a=p.parse_args()
    verify(a.source_seal.parent,a.source_seal.name)
    verify(a.inputs,'INPUT_SEAL.json');plan=json.loads((a.inputs/'PLAN.json').read_text())
    ass=json.loads(a.assignment.read_text());end=check_assignment(ass,plan)
    if a.preflight_only:print('PREFLIGHT_PASS');return
    a.out.mkdir(parents=True,exist_ok=False);clock=Clock(a.out,end)
    # Independent watchdog remains effective across native/CUDA hangs.
    read_fd,write_fd=os.pipe()
    code='import os,select,signal,sys,time; ready,_,_=select.select([int(sys.argv[1])],[],[],max(0,float(sys.argv[3])-time.time())); os.kill(int(sys.argv[2]),signal.SIGKILL) if not ready else None'
    guard=subprocess.Popen([sys.executable,'-c',code,str(read_fd),str(os.getpid()),str(end-120)],pass_fds=(read_fd,));os.close(read_fd)
    status='INCOMPLETE'
    try:
        import common
        import torch
        if not torch.cuda.is_available() or torch.cuda.device_count()!=1:raise ValueError('exactly one GPU required')
        from projects.g_agreement.blindspot.run import _assets
        assets=clock.call('verify_assets',lambda:_assets(a.assets,('model','olens','nla')))
        assets['_manifest']=str(a.assets)
        os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
        backend=Backend(assets,a.official,a.whitener)
        execute(a.inputs,plan,ass['slot'],backend,clock,a.out);status='COMPLETE'
    except BaseException as exc:
        write(a.out/'FAILURE.json',{'type':type(exc).__name__,'error':str(exc),'utc':utc()});raise
    finally:
        write(a.out/'RUN.json',{'status':status,'slot':ass['slot'],'pod_id':ass['pod_id'],'input_seal_sha256':digest(a.inputs/'INPUT_SEAL.json'),'source_seal_sha256':digest(a.source_seal),'assignment_sha256':digest(a.assignment),'first_output_utc':clock.first or 'unknown','greedy_generation_calls':0,'completed_utc':utc()})
        if status=='COMPLETE':write(a.out/'OUTPUT_SEAL.json',{'status':status,'first_output_utc':clock.first or 'unknown','first_output_source':'FIRST_OUTPUT.json; pod file mtime and log','files':{str(f.relative_to(a.out)):digest(f) for f in sorted(a.out.rglob('*')) if f.is_file() and f.name!='OUTPUT_SEAL.json'}})
        os.close(write_fd);guard.wait(timeout=5)

if __name__=='__main__':main()
