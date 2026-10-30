"""One integrator-operated process: E5 -> E8 -> E6, models loaded exactly once."""
from __future__ import annotations
import argparse,json,math,os,shutil,signal,statistics,time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
from . import core as K,e5,e8,e6
from projects.g_agreement.blindspot import protocol as P,run as W

ORDER=('E5','E8','E6')
CAPS={'E5':1080,'E8':3600,'E6':1800}
PROGRAM_STOP=datetime(2026,10,27,23,59,tzinfo=ZoneInfo('Europe/Zurich')).timestamp()


class BudgetStop(RuntimeError):pass


def prepare():
    children={}
    for name,module in (('E5',e5),('E8',e8),('E6',e6)):
        bank,frozen,plan=module.prepare();children[name]=(bank,frozen,plan)
    bank=P.ROOT/'cache/g_agreement/understand/packed-stage-v1';bank.mkdir(parents=True,exist_ok=False)
    frozen=K.RESULTS/'packed/freeze';frozen.mkdir(parents=True,exist_ok=False)
    child_info={}
    for name,(child,freeze,plan) in children.items():
        shutil.copytree(child,bank/name)
        child_info[name]={'directory':name,'input_seal_sha256':P.sha(child/'INPUT_SEAL.json'),
            'items':plan['items'],'cap_seconds':CAPS[name],'plan_sha256':P.sha(child/'plan.json')}
        for n in ('plan.json','INPUT_SEAL.json'):(frozen/(name+'.'+n)).write_bytes((child/n).read_bytes())
    plan={'experiment':'PACKED','status':'EXPLORATORY; every result and failure reported','order':ORDER,
        'source_files':K.source_hashes('PACKED'),'children':child_info,'cap_seconds':sum(CAPS.values()),
        'per_experiment_caps':CAPS,'setup_allowance_seconds':1500,'program_stop_epoch':PROGRAM_STOP,
        'forecast':'each experiment: one setup warm-up per code path, then median3timed units from its own first science; min(1.5F+360,own cap)',
        'shared_models':'one Oracle/target+adapter, one NLA verbalizer, one J projection; loaded once; no AR/reconstructor, no new target capture',
        'clock_rule':'one immutable first-science clock per named experiment; shared setup only before E5; no reset of an existing experiment',
        'continuation_prompt':e6.PROMPT,'no_new_capture':True}
    P.dump(bank/'plan.json',plan)
    names=[str(p.relative_to(bank)) for p in bank.rglob('*') if p.is_file()]
    P.seal(bank,names,'PACKED_EXPLORATORY_INPUTS_FROZEN')
    for n in ('plan.json','INPUT_SEAL.json'):(frozen/n).write_bytes((bank/n).read_bytes())
    return bank,frozen,plan


def launch_request(bank,frozen,archive):
    r=K.request(bank,frozen,archive)
    r.update(sequence=list(ORDER),per_experiment_science_cap_seconds=CAPS,
        science_cap_gpu_seconds=sum(CAPS.values()),shared_setup_allowance_seconds=1500,
        command='python -m projects.g_agreement.understand.packed run --bank STAGED_PACK --assignment ASSIGNMENT.json --assets VERIFIED_ASSETS.json --out NEW_PACK_OUTPUT',
        clock_rule='Separate immutable clock/forecast/output seal per experiment. Science measured from that experiment first timing unit, never pod creation. Shared load/warm-up once before E5.',
        loads_each_model_once=True,no_new_capture=True,output_directories=list(ORDER),
        continuation_format_policy='Report native prompt construction refusal and per-output explicit/descriptive markers. No replacement reader/scorer.',
        controlled_failure_policy='NO_FIT or own cap timeout seals a failure receipt and permits next independent experiment if absolute custody allows; unexpected model/runtime/lineage errors stop pack.',
        required_retrieval=['PACK_STATUS.json','each experiment: FORECAST.json,EXPERIMENT_CLOCK.json,SCORE_SEAL.json,scores.jsonl,provenance.json,SCIENCE_RECEIPT.json or FAILURE.json'])
    return r


class Window:
    def __init__(self,name,out,absolute,pod,now=time.time):
        self.name=name;self.out=Path(out);self.now=now;self.first=now();self.cap=CAPS[name]
        self.deadline=min(self.first+self.cap,absolute)
        if self.first>=self.deadline:raise BudgetStop('no remaining absolute custody')
        # Logical experiment scope, not a falsified pod creation or reset setup allowance.
        with (self.out/'EXPERIMENT_CLOCK.json').open('x') as f:
            json.dump({'experiment':name,'pod_id':pod,'first_science_epoch':self.first,
                'own_cap_seconds':self.cap,'initial_science_deadline_epoch':self.deadline},f,sort_keys=True)
        signal.setitimer(signal.ITIMER_REAL,max(.01,self.deadline-self.now()))
    def check(self):
        if self.now()>=self.deadline:raise BudgetStop(self.name+' science or absolute deadline reached')
        signal.setitimer(signal.ITIMER_REAL,max(.01,self.deadline-self.now()))
    def gate(self,remaining,timings):
        F=self.now()-self.first+remaining;allocation=min(1.5*F+360,self.cap)
        fits=math.isfinite(F) and F>0 and F<=allocation and self.now()+remaining<=self.deadline
        P.dump(self.out/'FORECAST.json',{'experiment':self.name,'status':'FIT' if fits else 'NO_FIT',
            'forecast_s':F,'allocation_s':allocation,'first_science_epoch':self.first,'timings':timings})
        if not fits:raise BudgetStop('NO_FIT: unchanged full '+self.name+' work')
        self.deadline=min(self.deadline,self.first+allocation);self.check()


def timed(fn,window):
    import torch
    window.check();torch.cuda.synchronize();start=time.monotonic();value=fn();torch.cuda.synchronize()
    return value,time.monotonic()-start


def work(name,data,models,out,absolute,pod,support):
    import torch
    bank,plan,items,specs,acts=data
    window=Window(name,out,absolute,pod)
    groups={f:[i for i,x in enumerate(items) if x['feature']==f] for f in plan['features']}
    records=[];timings=[];remaining=0.;batch=8 if name=='E6' else 16
    doses=plan.get('alphas',[0]);directions=np.load(bank/'directions.npz',allow_pickle=False) if name=='E8' else None
    readers=K.READERS[:2] if name=='E6' else K.READERS
    active=lambda reader: support.get(reader,True) if name=='E6' else reader!='jlens' or any(specs[f].get('jlens_supported',True) for f in groups)
    try:
        for f,indices in groups.items():
            for reader,site in readers:
                if not active(reader):continue
                h=acts[site][indices[:batch]]
                if name=='E8':h=h+8*torch.from_numpy(directions[f+'__L'+str(site)])
                times=[]
                for _ in range(3):
                    if name=='E6':
                        generated,seconds=timed(lambda:e6.generate(reader,models[reader],h),window)
                        n=min(max(1,len(models[reader].tok.encode(s,add_special_tokens=False))) for s in generated)
                        times.append(seconds*32/min(32,n))
                    else:
                        _,seconds=timed(lambda:K.score(reader,models[reader],h,specs[f][reader]),window);times.append(seconds)
                median=statistics.median(times);remaining+=median*math.ceil(len(indices)/batch)*len(doses)
                timings.append({'feature':f,'reader':reader,'warmed_units_s':times,'median_s':median})
        window.gate(remaining,timings)
        for f,indices in groups.items():
            for reader,site in readers:
                for alpha in doses:
                    if not active(reader):
                        records.extend({'id':items[i]['id'],'feature':f,'reader':reader,'layer':site,'alpha':alpha,
                            'status':'FORMAT_UNSUPPORTED' if name=='E6' else 'UNSUPPORTED_SEQUENCE_QUERY_WITH_W1_J_LENS',
                            'scores':None,'text':None} for i in indices)
                        continue
                    for start in range(0,len(indices),batch):
                        window.check();idx=indices[start:start+batch];h=acts[site][idx]
                        if name=='E8':h=h+float(alpha)*torch.from_numpy(directions[f+'__L'+str(site)])
                        if name=='E6':
                            values=e6.generate(reader,models[reader],h)
                            if len(values)!=len(idx):raise ValueError('generation row mismatch')
                            chunk=[{'id':items[i]['id'],'feature':f,'reader':reader,'layer':site,'alpha':alpha,
                                'status':'COMPLETE','text':values[j],'format_status':e6.format_status(values[j])} for j,i in enumerate(idx)]
                        else:
                            values=K.score(reader,models[reader],h,specs[f][reader])
                            if values.shape!=(len(specs[f][reader]),len(idx)) or not torch.isfinite(values).all():raise ValueError('invalid score matrix')
                            chunk=[{'id':items[i]['id'],'feature':f,'reader':reader,'layer':site,'alpha':alpha,
                                'status':'COMPLETE','scores':values[:,j].tolist()} for j,i in enumerate(idx)]
                        records.extend(chunk)
                        with (Path(out)/'scores.partial.jsonl').open('a') as stream:
                            for r in chunk:stream.write(json.dumps(r,sort_keys=True)+'\n')
                            stream.flush();os.fsync(stream.fileno())
        P.jsonl(Path(out)/'scores.jsonl',records)
        P.dump(Path(out)/'provenance.json',{'experiment':name,'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),
            'source_files':plan['source_files'],'packed_pod_id':pod,'no_new_capture':True,'model_loads':'shared once in setup'})
        window.check()
        P.dump(Path(out)/'SCIENCE_RECEIPT.json',{'experiment':name,'first_science_epoch':window.first,
            'completed_epoch':time.time(),'elapsed_s':time.time()-window.first,'effective_deadline_epoch':window.deadline,
            'own_cap_seconds':CAPS[name]})
        names=['scores.jsonl','provenance.json','FORECAST.json','EXPERIMENT_CLOCK.json','SCIENCE_RECEIPT.json']
        P.dump(Path(out)/'SCORE_SEAL.json',{'status':'EXPLORATORY_SCORES_SEALED_BEFORE_LABEL_JOIN',
            'files':{n:P.sha(Path(out)/n) for n in names}})
        return {'experiment':name,'status':'SEALED','records':len(records)}
    except BudgetStop as exc:
        P.dump(Path(out)/'FAILURE.json',{'experiment':name,'status':'INCOMPLETE','reason':str(exc),
            'first_science_epoch':window.first,'elapsed_s':time.time()-window.first,'no_automatic_retry':True})
        return {'experiment':name,'status':'INCOMPLETE','reason':str(exc)}


def run(bank,assignment,assets,out):
    import torch
    bank,assignment,out=map(Path,(bank,assignment,out));P.verify(bank,'INPUT_SEAL.json')
    plan=json.loads((bank/'plan.json').read_text());a=json.loads(assignment.read_text())
    if (a.get('issuer')!='integrator' or not a.get('pod_id') or a['pod_id']!=os.environ.get('RUNPOD_POD_ID')
        or a.get('experiment')!='PACKED' or a.get('source_files')!=plan['source_files']
        or a.get('plan_sha256')!=P.sha(bank/'plan.json') or a.get('previous_gpu_seconds')!=0
        or any(a.get(k) is not True for k in ('brief_registered','brief_pushed','manifest_committed','external_hardstop_verified'))):raise ValueError('exact packed integrator assignment required')
    if P._science_budget(a)!=sum(CAPS.values()) or a.get('staging_allowance_seconds')!=1500:raise ValueError('wrong pack allocation')
    created=float(a['provider_created_epoch']);absolute=min(float(a['deadline_epoch'])-180,PROGRAM_STOP)
    if not 0<float(a['deadline_epoch'])-created<=float(a['allocated_gpu_seconds']):raise ValueError('invalid custody deadline')
    if not created<=time.time()<min(created+1500,absolute):raise ValueError('shared setup expired')
    for path,digest in plan['source_files'].items():
        if P.sha(P.ROOT/path)!=digest:raise ValueError('use exact archived source: '+path)
    if list(plan['order'])!=list(ORDER) or plan['per_experiment_caps']!=CAPS:raise ValueError('sequence/caps changed')
    data={}
    for name in ORDER:
        child=bank/name;P.verify(child,'INPUT_SEAL.json');W._labels_absent(child)
        if P.sha(child/'INPUT_SEAL.json')!=plan['children'][name]['input_seal_sha256']:raise ValueError('child seal changed')
        p=json.loads((child/'plan.json').read_text());items=P.rows(child/'items.input.jsonl');spec=json.loads((child/'templates.json').read_text())
        acts={s:torch.from_numpy(np.load(child/f'acts{s}.npy',allow_pickle=False)) for s in (42,44)}
        if any(h.ndim!=2 or len(h)!=len(items) or not torch.isfinite(h).all() for h in acts.values()):raise ValueError('bad staged arrays')
        data[name]=(child,p,items,spec,acts)
    out.mkdir(parents=True,exist_ok=False)
    def stop(*_):raise BudgetStop('current science/setup deadline reached')
    old=signal.signal(signal.SIGALRM,stop);signal.setitimer(signal.ITIMER_REAL,max(.01,min(created+1500,absolute)-time.time()))
    try:
        assets=W._assets(assets);ol=W._load_oracle(assets)
        from mats.readers.nla import load_nla
        from mats.readers.jlens import load_jlens
        nla=load_nla(root=assets['nla'],load_ar=False,enable_thinking=False)
        jl=load_jlens(ol.model,ol.tok,layers=[44],path=assets['jlens'])
        models={'olens':ol,'nla':nla,'jlens':jl};synthetic=torch.ones(16,data['E5'][4][42].shape[1]);support={}
        # Warm every distinct experiment path once in shared setup, before any scientific timing.
        for name in ('E5','E8'):
            spec=data[name][3][data[name][1]['features'][0]]
            for reader,_ in K.READERS:
                if name=='E5' and reader=='jlens':continue
                K.score(reader,models[reader],synthetic,spec[reader])
        for reader in ('olens','nla'):
            try:
                with e6.continuation_reader(reader,models[reader]) as value:
                    if reader=='olens':value.carrier(44)
            except (ValueError,RuntimeError) as exc:
                support[reader]=False;continue
            support[reader]=True;e6.generate(reader,models[reader],synthetic[:8])
        torch.cuda.synchronize()
        if time.time()>=min(created+1500,absolute):raise BudgetStop('shared setup/warm-up expired')
        setup_elapsed=time.time()-created;statuses=[]
        for name in ORDER:
            child_out=out/name;child_out.mkdir(exist_ok=False)
            result=work(name,data[name],models,child_out,absolute,a['pod_id'],support)
            statuses.append(result);P.dump(out/'PACK_STATUS.json',{'order':ORDER,'model_loads':{'olens':1,'nla':1,'jlens':1},
                'shared_setup_s':setup_elapsed,'experiments':statuses,'e6_native_prompt_supported':support})
        return statuses
    finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True);sub.add_parser('prepare')
    r=sub.add_parser('run')
    for n in ('bank','assignment','assets','out'):r.add_argument('--'+n,type=Path,required=True)
    args=p.parse_args()
    if args.command=='prepare':prepare()
    else:
        with P.logged('packed_E5_E8_E6_worker',gpu=True,extra={'per_experiment_caps':CAPS,'no_new_capture':True}):
            run(args.bank,args.assignment,args.assets,args.out)
