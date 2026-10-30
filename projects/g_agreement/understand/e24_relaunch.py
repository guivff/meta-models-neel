"""E24 §118 acquisition: §144 shard-local certified capture, unchanged scientific channels."""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import statistics
import sys
import time

from projects.g_agreement.blindspot import protocol as P, run as W

PRIORITY = (44,20,60,32,52,28,36,40,48,56,24)
C6_LAYERS = (20,36,44,60)
C7_LAYERS = (20,44,60)
CAP, SETUP, TOTAL, RESERVE = 10800, 2400, 32738, 180
BATCH = 32


def read(path):
    return json.loads(Path(path).read_text())


def shards(n):
    if n not in range(1,9): raise ValueError('one to eight pods')
    return [[44]+list(PRIORITY[1+i::n]) for i in range(n)]


def finite_positive(value):
    return math.isfinite(float(value)) and float(value)>0


def parity(actual, reference):
    import numpy as np
    x,y=np.asarray(actual,dtype=np.float64),np.asarray(reference,dtype=np.float64)
    if x.shape!=y.shape or x.ndim!=2 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('parity shape/nonfinite')
    norms=np.linalg.norm(x,axis=1)*np.linalg.norm(y,axis=1)
    if (norms<=0).any(): raise ValueError('zero parity vector')
    cosine=(x*y).sum(1)/norms
    result={'n':len(x),'minimum_cosine':float(cosine.min()),'threshold':.999}
    if (cosine<.999).any(): raise ValueError('block44 parity failed: '+str(result))
    return result


def seal(out, names, name, status):
    tmp=out/(name+'.tmp')
    P.dump(tmp,{'status':status,'files':{n:P.sha(out/n) for n in names}})
    tmp.replace(out/name)


def schedule(forecasts, now):
    """Longest global priority prefix; reserve each pod's full worst-case lifetime."""
    n=len(forecasts); layout=shards(n)
    if sorted(f['slot'] for f in forecasts)!=list(range(n)): raise ValueError('one forecast per slot')
    forecasts=sorted(forecasts,key=lambda f:f['slot'])
    if len({f['plan_sha256'] for f in forecasts})!=1:
        raise ValueError('inconsistent forecast source/capture binding')
    for i,f in enumerate(forecasts):
        if f['layers']!=layout[i] or not f['provider_created_epoch']<=f['first_science_epoch']<=f['forecast_epoch']<=now:
            raise ValueError('forecast layout/clock mismatch')
        if not all(math.isfinite(float(f[k])) for k in ('provider_created_epoch','provider_deadline_epoch','first_science_epoch','forecast_epoch')):
            raise ValueError('nonfinite forecast clock')
        if not finite_positive(f['c6_capture_and_transfer_s']) or not all(finite_positive(v) for key in ('C6','C7') for v in f[key].values()):
            raise ValueError('nonfinite tier2 forecast')
        for layer in layout[i]:
            if set(f['tier1'][str(layer)])!={'C1','C2','C4','C5'} or not all(finite_positive(v) for v in f['tier1'][str(layer)].values()):
                raise ValueError('complete finite tier1 forecast required')
    def allocate(prefix,c6=False,c7=False):
        result=[]
        for i,f in enumerate(forecasts):
            layers=[l for l in layout[i] if l in prefix]
            remain=sum(sum(f['tier1'][str(l)].values()) for l in layers)
            if c6:
                remain+=sum(f['C6'][str(l)] for l in layers if l in C6_LAYERS)
                # Each pod reserves its own C6 capture and operational allowance.
                remain+=f['c6_capture_and_transfer_s']
            if c7: remain+=sum(f['C7'][str(l)] for l in layers if l in C7_LAYERS)
            F=now-f['first_science_epoch']+remain
            cap=min(1.5*F+360,CAP)
            deadline=min(f['first_science_epoch']+cap, f['provider_deadline_epoch']-RESERVE)
            if now+remain>deadline: return None
            result.append({'slot':i,'layers':layers,'C6':c6,'C7':c7,'forecast_s':F,'science_cap_s':cap,
                           'deadline_epoch':deadline,'remaining_s':remain,
                           'reserved_gpu_s':deadline+RESERVE-f['provider_created_epoch']})
        if sum(x['reserved_gpu_s'] for x in result)>TOTAL: return None
        return result
    selected=None
    for size in range(len(PRIORITY),0,-1):
        prefix=list(PRIORITY[:size]);selected=allocate(prefix)
        if selected is not None:break
    if selected is None: return {'status':'NO_FIT','reason':'anchor-complete tier1 cannot fit; no retry'}
    # Tier2 cannot displace tier1 layers. Whole registered layer set per optional channel.
    c6=set(C6_LAYERS)<=set(prefix) and allocate(prefix,True) is not None
    c7=set(C7_LAYERS)<=set(prefix) and allocate(prefix,c6,True) is not None
    selected=allocate(prefix,c6,c7)
    return {'status':'FIT','layers_priority':prefix,'dropped_suffix':list(PRIORITY[len(prefix):]),
            'pods':selected,'reserved_gpu_s':sum(x['reserved_gpu_s'] for x in selected),
            'plan_sha256':forecasts[0]['plan_sha256'],'capture_seals':{str(f['slot']):f['capture_seal_sha256'] for f in forecasts},
            'created_epoch':now,'C6':bool(c6),'C7':bool(c7)}


class Engine:
    def __init__(self, assets, source, whitener):
        import torch
        from projects.g_agreement.w_claims.ar import load_reconstructor
        # Explicit hardware contract permits both 27B instances to remain resident.
        if torch.cuda.get_device_properties(0).total_memory<140_000_000_000:
            raise ValueError('E24 requires >=140GB VRAM; no silent offload/batch change')
        self.ol=W._load_oracle(assets)
        self.ar,self.tok,_=load_reconstructor(source,whitener,assets['ar'],assets['model'])
        if not set(PRIORITY)<=set(self.ar.layers): raise ValueError('missing trained AR layer tag')

    def capture(self, items, layers):
        from .certified_capture import capture
        result,self.last_capture_metadata=capture(self.ol,items,layers,self.capture_mode,self.capture_context)
        return result

    def asked(self,h,layer,pairs,prefix=''):
        import torch
        scores=self.ol.paired_logodds_templates(h,layer,pairs,prefix=prefix)
        if scores.shape!=(len(pairs),len(h)) or not torch.isfinite(scores).all(): raise ValueError('invalid likelihood grid')
        return scores.cpu()

    def free(self,h,layer):
        from mats.readers.olens import Sampling
        return self.ol.verbalize(h,layer,k=1,sampling=Sampling(temperature=0,top_p=1.,top_k=0,max_new_tokens=128),batch=BATCH)

    def reconstruct(self,texts,layer):
        import torch
        tokens=self.tok(texts,add_special_tokens=False,return_tensors='pt',padding=True,truncation=False)
        if not bool((tokens['attention_mask'].sum(1)>0).all()): raise ValueError('empty frozen AR text')
        cfg=getattr(self.ar.backbone.config,'text_config',self.ar.backbone.config)
        if tokens['input_ids'].shape[1]+self.ar.tag_ids.shape[1]>cfg.max_position_embeddings:
            raise ValueError('AR context exceeded; no truncation')
        with torch.inference_mode():
            result=self.ar(tokens['input_ids'].cuda(),tokens['attention_mask'].cuda(),
                layer_idx=self.ar.layers.index(layer))[:,0].float().cpu()
        if result.shape!=(len(texts),5120) or not torch.isfinite(result).all():raise ValueError('invalid raw AR vectors')
        return result


def validate_assignment(q,plan,plan_hash,slot,pod_id):
    if (q.get('issuer')!='integrator' or q.get('experiment')!='E24' or not pod_id or q.get('pod_id')!=pod_id
        or q.get('slot')!=slot or q.get('plan_sha256')!=plan_hash or q.get('source_files')!=plan['source_files']
        or q.get('previous_gpu_seconds')!=0 or q.get('pod_count') not in range(1,9)
        or any(q.get(k) is not True for k in ('pregen_freeze_published','source_published','external_hardstop_verified'))):
        raise ValueError('exact published E24 assignment required')
    if q.get('modal14_hash_correction_commit') is None or q.get('modal14_corrected_sha256')!=plan['modal14_sha256']:
        raise ValueError('clarification hash correction must be published before launch')
    duration=float(q['deadline_epoch'])-float(q['provider_created_epoch'])
    if not finite_positive(duration) or duration>float(q['allocated_gpu_seconds']): raise ValueError('invalid custody deadline')
    if q['allocated_gpu_seconds']>TOTAL/q['pod_count']: raise ValueError('equal custody shares exceed remaining32738s')
    if slot not in range(q['pod_count']): raise ValueError('invalid slot')


def run(a):
    import numpy as np
    import torch
    plan=read(a.plan);q=read(a.assignment)
    validate_assignment(q,plan,P.sha(a.plan),a.slot,os.environ.get('RUNPOD_POD_ID'))
    from .certified_capture import release,parity_gate
    mode=release(plan,q,a.certificate,a.capture_context)
    P.verify(a.bank,'INPUT_SEAL.json');W._labels_absent(a.bank)
    if list(a.bank.rglob('*.DO_NOT_STAGE.*')):raise ValueError('private labels in staged bank')
    if P.sha(a.bank/'INPUT_SEAL.json')!=plan['input_seal_sha256']:raise ValueError('bank binding')
    for name,digest in plan['source_files'].items():
        if P.sha(P.ROOT/name)!=digest:raise ValueError('unbound source: '+name)
    if a.capture is not None or a.c6_capture is not None:raise ValueError('section144 requires fresh local capture on every shard')
    layout=shards(q['pod_count']);layers=layout[a.slot]
    created=float(q['provider_created_epoch']);absolute=float(q['deadline_epoch'])-RESERVE
    end=min(created+SETUP,absolute);first=None
    a.out.mkdir(parents=True,exist_ok=False)
    # Assignment-scoped create-only lock, outside the output directory, rejects alternate-output retries.
    lock=a.assignment.with_suffix('.e24.lock')
    with lock.open('x') as f:f.write(P.sha(a.assignment)+'\n')
    def expired(*_):raise TimeoutError('E24 setup/science/custody deadline')
    def check():
        if not created<=time.time()<end:expired()
        signal.setitimer(signal.ITIMER_REAL,max(.001,end-time.time()))
    old=signal.signal(signal.SIGALRM,expired)
    def call(fn,*args):
        check();v=fn(*args);torch.cuda.synchronize();check();return v
    def wait_for(path):
        while not path.exists():check();time.sleep(.25)
        check()
    try:
        check();torch.manual_seed(20261025);torch.cuda.manual_seed_all(20261025)
        assets=W._assets(a.assets,names=('model','olens'))
        from projects.g_agreement.blindspot.ar_tests import _assets
        _assets(a.assets,('ar',))
        engine=Engine(assets,a.ar_source,a.whitener);engine.capture_mode=mode;engine.capture_context=a.capture_context;check()
        items=P.rows(a.bank/'items.input.jsonl');cont=P.rows(a.bank/'continuations.jsonl')
        specs=read(a.bank/'templates.json');c2=read(a.bank/'c2.json');c7=read(a.bank/'c7.json');c6=read(a.bank/'c6.pairs.json')
        lookup={x['id']:i for i,x in enumerate(items)}
        if len(items)!=4704 or len(lookup)!=4704 or len(cont)!=2100:raise ValueError('incomplete fixed bank')
        first=time.time();end=min(first+CAP,absolute)
        P.dump(a.out/'CLOCK.json',{'first_science_epoch':first,'provider_created_epoch':created})
        capture=a.out/'capture'
        if True:
            capture.mkdir();start=time.time()
            hs=call(engine.capture,items,layers)
            P.jsonl(capture/'ITEM_ENVIRONMENT.jsonl',engine.last_capture_metadata)
            p=parity_gate(hs[44].numpy(),np.load(a.bank/'reference44.npy',allow_pickle=False),capture,items)
            P.dump(capture/'ORDER.json',[x['id'] for x in items]);P.dump(capture/'PARITY.json',p)
            P.dump(capture/'BINDING.json',{'input_seal_sha256':plan['input_seal_sha256'],'plan_sha256':P.sha(a.plan),
                'assignment_sha256':P.sha(a.assignment),'slot':a.slot,'capture_mode':mode})
            for l,h in hs.items():
                np.save(capture/f'acts{l}.npy',h.numpy(),allow_pickle=False)
                seal(capture,[f'acts{l}.npy','ORDER.json','PARITY.json','BINDING.json'],f'L{l}_SEAL.json','SEALED_BEFORE_SCORING')
            P.dump(capture/'TIMING.json',{'capture_s':time.time()-start})
            seal(capture,[f'L{l}_SEAL.json' for l in layers]+['ITEM_ENVIRONMENT.jsonl','ORDER.json','PARITY.json','BINDING.json','TIMING.json'],
                 'CAPTURE_SEAL.json','SHARD_LOCAL_CAPTURE_PARITY_PASS')
            del hs
        wait_for(capture/'CAPTURE_SEAL.json');P.verify(capture,'CAPTURE_SEAL.json')
        if read(capture/'ORDER.json')!=[x['id'] for x in items] or read(capture/'BINDING.json')['input_seal_sha256']!=plan['input_seal_sha256'] or read(capture/'BINDING.json')['plan_sha256']!=P.sha(a.plan):
            raise ValueError('shared capture input binding')
        for l in layers:P.verify(capture,f'L{l}_SEAL.json')
        acts={l:torch.from_numpy(np.load(capture/f'acts{l}.npy',allow_pickle=False)) for l in layers}
        parity(acts[44].numpy(),np.load(a.bank/'reference44.npy',allow_pickle=False))
        test={f:[i for i,x in enumerate(items) if x['feature']==f and x['split']=='test'] for f in specs}
        both={f:[i for i,x in enumerate(items) if x['feature']==f] for f in c7}
        timing=[]
        def measure(channel,l,fn,units):
            call(fn);ts=[]
            for _ in range(3):
                t=time.perf_counter();call(fn);ts.append(time.perf_counter()-t)
            estimate=statistics.median(ts)*units
            timing.append({'channel':channel,'layer':l,'seconds':ts,'units':units,'estimate_s':estimate})
            return estimate
        tier1={};fc6={};fc7={}
        # Longest candidate pair for each native path; forecast based on full batch32 units.
        f1=max(specs,key=lambda f:sum(len(engine.ol.tok.encode(s)) for p in specs[f]['olens'] for s in p))
        f2=max(c2,key=lambda f:sum(len(engine.ol.tok.encode(s)) for p in c2[f] for s in p))
        f7=max(c7,key=lambda f:sum(len(engine.ol.tok.encode(s)) for p in c7[f] for s in p))
        text_sample=sorted([x['text'] for x in cont],key=lambda s:len(engine.tok.encode(s)),reverse=True)[:BATCH]
        for l in layers:
            h=acts[l]
            tier1[str(l)]={
                'C1':measure('C1',l,lambda:engine.asked(h[test[f1][:BATCH]],l,specs[f1]['olens']),sum(math.ceil(len(v)/BATCH) for v in test.values())),
                'C2':measure('C2',l,lambda:engine.asked(h[test[f2][:BATCH]],l,c2[f2],'- '),2*sum(math.ceil(len(test[f])/BATCH) for f in c2)),
                'C4':measure('C4',l,lambda:engine.free(h[test[f1][:BATCH]],l),sum(math.ceil(len(v)/BATCH) for v in test.values())),
                'C5':measure('C5',l,lambda:engine.reconstruct(text_sample,l),math.ceil(len(cont)/BATCH))}
            if l in C6_LAYERS:
                texts=[s for pairs in c6.values() for _,aa,bb in pairs for s in (aa,bb)]
                fc6[str(l)]=measure('C6',l,lambda:engine.reconstruct(texts,l),1)
            if l in C7_LAYERS:
                fc7[str(l)]=measure('C7',l,lambda:engine.asked(h[both[f7][:BATCH]],l,c7[f7]),sum(math.ceil(len(v)/BATCH) for v in both.values()))
        forecast={'slot':a.slot,'layers':layers,'plan_sha256':P.sha(a.plan),'capture_seal_sha256':P.sha(capture/'CAPTURE_SEAL.json'),
            'provider_created_epoch':created,'provider_deadline_epoch':q['deadline_epoch'],'first_science_epoch':first,
            'forecast_epoch':time.time(),'tier1':tier1,'C6':fc6,'C7':fc7,
            'c6_capture_and_transfer_s':read(capture/'TIMING.json')['capture_s']*600/4704+180,
            'timings':timing,'timing_outputs_retained':False}
        P.dump(a.out/'FORECAST.tmp',forecast);(a.out/'FORECAST.tmp').replace(a.out/'FORECAST.json')
        wait_for(a.admission);admission=read(a.admission)
        if admission.get('status')!='FIT' or admission['plan_sha256']!=P.sha(a.plan) or admission['capture_seals'][str(a.slot)]!=P.sha(capture/'CAPTURE_SEAL.json'):
            raise ValueError('NO_FIT or unbound global admission')
        if admission['forecast_sha256'][str(a.slot)]!=P.sha(a.out/'FORECAST.json'):raise ValueError('admission forecast changed')
        # Admission carries all forecasts: recompute allocator at its frozen timestamp, never trust a handwritten subset.
        if schedule(admission['forecasts'],admission['created_epoch'])!={k:v for k,v in admission.items() if k not in ('forecasts','forecast_sha256')}:
            raise ValueError('admission is not the registered global allocator output')
        own=admission['pods'][a.slot];end=min(end,own['deadline_epoch']);check()
        if time.time()+own['remaining_s']>end:raise TimeoutError('admission delivery consumed available science')
        P.dump(a.out/'ADMISSION.json',admission)
        # Each shard captures and parity-checks the optional bank after global tier2 fit.
        if own['C6']:
            c6dir=a.out/'c6_capture'
            if c6dir is None:raise ValueError('C6 requires shared capture destination on other slots')
            if True:
                c6dir.mkdir();ci=P.rows(a.bank/'c6.input.jsonl');hs=call(engine.capture,ci,list(C6_LAYERS))
                P.jsonl(c6dir/'ITEM_ENVIRONMENT.jsonl',engine.last_capture_metadata)
                P.dump(c6dir/'ORDER.json',[x['id'] for x in ci]);parity_gate(hs[44].numpy(),np.load(a.bank/'c6.reference44.npy',allow_pickle=False),c6dir,ci)
                P.dump(c6dir/'BINDING.json',{'input_seal_sha256':plan['input_seal_sha256'],'admission_sha256':P.sha(a.admission)})
                for l,h in hs.items():np.save(c6dir/f'acts{l}.npy',h.numpy(),allow_pickle=False)
                seal(c6dir,[f'acts{l}.npy' for l in C6_LAYERS]+['ITEM_ENVIRONMENT.jsonl','ORDER.json','PARITY.json','BINDING.json'],'CAPTURE_SEAL.json','C6_FRESH_CAPTURE')
            wait_for(c6dir/'CAPTURE_SEAL.json');P.verify(c6dir,'CAPTURE_SEAL.json')
            if read(c6dir/'BINDING.json')!={'input_seal_sha256':plan['input_seal_sha256'],'admission_sha256':P.sha(a.admission)}:raise ValueError('C6 capture binding')
        for l in own['layers']:
            dest=a.out/f'L{l}';dest.mkdir();h=acts[l];records=[]
            for f,indices in test.items():
                for start in range(0,len(indices),BATCH):
                    ii=indices[start:start+BATCH];v=call(engine.asked,h[ii],l,specs[f]['olens']);texts=call(engine.free,h[ii],l)
                    cv=sv=None
                    if f in c2:
                        cv=call(engine.asked,h[ii],l,c2[f],'- ')
                        # Deliberately index only h for this same layer; no block44 fallback.
                        di=[lookup[items[i]['donor_id']] for i in ii]
                        sv=call(engine.asked,h[di],l,c2[f],'- ')
                    for j,i in enumerate(ii):
                        if len(texts[j])!=1:raise ValueError('one greedy readout required')
                        records.append({'id':items[i]['id'],'feature':f,'C1':v[:,j].tolist(),'C4':texts[j][0],
                            'C2':None if cv is None else cv[:,j].tolist(),'C2_swap':None if sv is None else sv[:,j].tolist()})
            P.jsonl(dest/'readouts.jsonl',records)
            recon=[]
            for start in range(0,len(cont),BATCH):recon.append(call(engine.reconstruct,[x['text'] for x in cont[start:start+BATCH]],l))
            np.save(dest/'C5.npy',torch.cat(recon).numpy(),allow_pickle=False);P.dump(dest/'C5_ORDER.json',[x['id'] for x in cont])
            names=['readouts.jsonl','C5.npy','C5_ORDER.json']
            if own['C7'] and l in C7_LAYERS:
                rows=[]
                for f,indices in both.items():
                    for start in range(0,len(indices),BATCH):
                        ii=indices[start:start+BATCH];v=call(engine.asked,h[ii],l,c7[f])
                        rows.extend({'id':items[i]['id'],'feature':f,'scores':v[:,j].tolist()} for j,i in enumerate(ii))
                P.jsonl(dest/'C7.jsonl',rows);names.append('C7.jsonl')
            if own['C6'] and l in C6_LAYERS:
                texts=[s for pairs in c6.values() for _,aa,bb in pairs for s in (aa,bb)]
                v=call(engine.reconstruct,texts,l);np.save(dest/'C6.npy',v.numpy(),allow_pickle=False)
                P.dump(dest/'C6_ORDER.json',[[f,p[0],side] for f,pairs in c6.items() for p in pairs for side in ('A','B')]);names+=['C6.npy','C6_ORDER.json']
            P.dump(dest/'BINDING.json',{'layer':l,'input_seal_sha256':plan['input_seal_sha256'],
                'capture_layer_seal_sha256':P.sha(capture/f'L{l}_SEAL.json'),'assignment_sha256':P.sha(a.assignment),
                'admission_sha256':P.sha(a.admission),'plan_sha256':P.sha(a.plan)})
            seal(dest,names+['BINDING.json'],'SCORE_SEAL.json','E24_LAYER_COMPLETE_BEFORE_LABEL_JOIN')
        seal(a.out,[f'L{l}/SCORE_SEAL.json' for l in own['layers']]+['ADMISSION.json','CLOCK.json','FORECAST.json'],
             'SCORE_SEAL.json','E24_POD_COMPLETE_BEFORE_LABEL_JOIN');check()
    except Exception as exc:
        P.dump(a.out/'FAILURE.json',{'status':'INCOMPLETE','reason':str(exc),'retry_authorized':False,'slot':a.slot,'layers':layers,'capture_mode':mode,'cells_status':'INCOMPLETE'});raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
        P.dump(a.out/'RECEIPT.json',{'slot':a.slot,'setup_seconds':(first or time.time())-created,
            'science_seconds':0 if first is None else time.time()-first,'total_elapsed_s':time.time()-created,'carry_forward_required':True})


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    r=sub.add_parser('run')
    for n in ('bank','plan','assignment','assets','ar-source','whitener','out','admission','certificate','capture-context'):
        r.add_argument('--'+n,type=Path,required=True)
    for n in ('capture','c6-capture'):r.add_argument('--'+n,type=Path)
    r.add_argument('--slot',type=int,required=True)
    s=sub.add_parser('admit');s.add_argument('--forecasts',nargs='+',type=Path,required=True);s.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.command=='run':run(a)
    else:
        if a.out.exists():raise FileExistsError('admission immutable')
        fs=[read(p) for p in a.forecasts];decision=schedule(fs,time.time())
        decision['forecasts']=fs;decision['forecast_sha256']={str(f['slot']):P.sha(p) for f,p in zip(fs,a.forecasts)}
        # Atomic publication: workers must never observe a partial admission.
        tmp=a.out.with_suffix('.tmp');P.dump(tmp,decision);tmp.replace(a.out)


if __name__=='__main__':main()
