"""E27(c): S16 generation/averaging, pure swap code, native NLA scoring; integrator only."""
import argparse
import gc
import math
import os
import time
from pathlib import Path
import numpy as np
from .cpu import ROOT,read,dump,sha,seal
from .e27c import FEATURES,ARMS,PUBLIC,s16,validate
from .e27c_runtime import Gate,NoFit,PATHS,TOTAL_SECONDS


def counts(spec):
    return {'ol_generation':7*math.ceil(84/16),'nla_generation':7*math.ceil(84/32),
            'reconstruction':7*2*math.ceil(168/16),
            'asked':sum(2*math.ceil(84/(112//(2*len(spec[f]['pairs'])))) for f in FEATURES)}


class Residents:
    def __init__(self,a,g):
        import common
        from projects.g_agreement.blindspot.run import _assets
        self.a=a;self.g=g;self.objects={};self.active=None;self.moves=[];self.loads={}
        g.setup_guard();self.assets=_assets(a.assets,('model','olens','nla'));g.setup_guard()

    def modules(self,name):
        obj=self.objects[name]
        return [obj.model] if name=='ol' else ([obj.av] if name=='nla' else [obj.ar,obj.value_head])

    def move(self,name,device):
        import torch
        t=time.monotonic()
        for m in self.modules(name):m.to(device)
        self.objects[name].device=device
        if device=='cpu':gc.collect();torch.cuda.empty_cache()
        else:torch.cuda.synchronize()
        self.moves.append(time.monotonic()-t)

    def get(self,name):
        import torch
        self.g.guard()
        if self.active!=name:
            if self.active is not None:self.move(self.active,'cpu')
            self.active=None
            if name not in self.objects:
                if self.g.started is not None:raise ValueError('checkpoint load after science start forbidden')
                if name=='ol':
                    from transformers import AutoModelForCausalLM,AutoTokenizer
                    from mats.readers.olens import load_olens
                    tok=AutoTokenizer.from_pretrained(self.assets['model'],local_files_only=True)
                    model=AutoModelForCausalLM.from_pretrained(self.assets['model'],dtype=torch.bfloat16,device_map='cuda',local_files_only=True).eval()
                    obj=load_olens(model,tok,lora_dir=self.assets['olens'])
                elif name=='nla':
                    from mats.readers.nla import load_nla
                    obj=load_nla(root=self.assets['nla'],load_ar=False)
                elif name=='decoder':
                    from .worker import load_decoder_only
                    obj=load_decoder_only(self.a.assets)
                else:raise ValueError('unknown model')
                self.objects[name]=obj;self.loads[name]=1;self.g.setup_guard()
            else:self.move(name,'cuda')
            self.active=name
        self.g.guard();return self.objects[name]


class Collection:
    def __init__(self,a,g,res):
        import torch
        self.a,self.g,self.res=a,g,res
        self.spec=validate(a.inputs,g.a['input_seal_sha256'])
        self.h={L:torch.from_numpy(np.load(a.inputs/f'acts{L}.npy',allow_pickle=False)) for L in (42,44)}
        self.lib=s16()

    def generation(self,owner,h):
        from mats.readers import nla as NL
        from mats.readers.olens import WSBENCH_SAMPLING
        obj=self.res.get(owner)
        if owner=='ol':return obj.verbalize(h,44,k=2,sampling=WSBENCH_SAMPLING,batch=32)
        raw=obj.verbalize_raw(h,k=2,batch=64)
        return [[NL.extract_explanation(t) or t.split('</br>')[0].strip() for t in row] for row in raw]

    def score(self,h,pairs):
        from mats.readers.nla import logprob_of_strings_batch
        nla=self.res.get('nla');cands=[x for _,a,b in pairs for x in (a,b)]
        lp=logprob_of_strings_batch(nla,h,cands,batch=112)
        return (lp[:,1::2]-lp[:,::2]).T.numpy()

    def pilot(self,key):
        # Full canonical batches; no synthetic token added and all pilot outputs discarded.
        if key=='ol_generation':return self.generation('ol',self.h[44][:16])
        if key=='nla_generation':return self.generation('nla',self.h[42][:32])
        if key=='reconstruction':
            # Exact 256-token source cap, using a frozen input text chosen before dispatch.
            text=read(self.a.inputs/'pilot.json')['reconstruction_text']
            return self.res.get('decoder').reconstruct([text]*16,batch=16)
        feature=read(self.a.inputs/'pilot.json')['asked_feature']
        pairs=self.spec[feature]['pairs'];n=112//(2*len(pairs))
        return self.score(self.h[42][:n],pairs)

    def timed(self,key,fn,retained):
        import torch
        self.g.guard();torch.cuda.synchronize();t=time.monotonic()
        value=fn();torch.cuda.synchronize();self.g.record(key,time.monotonic()-t,retained)
        return value

    def setup_and_admit(self):
        import torch
        # All three loads and every warm-up precede the immutable science clock.
        for owner in ('ol','decoder','nla'):self.res.get(owner)
        for key in PATHS:
            self.g.setup_guard();t=time.monotonic()
            with torch.random.fork_rng(devices=[torch.cuda.current_device()]):self.pilot(key)
            torch.cuda.synchronize();self.g.warm(key,time.monotonic()-t)
        self.g.start()
        for key in PATHS:
            for _ in range(3):
                with torch.random.fork_rng(devices=[torch.cuda.current_device()]):
                    self.timed(key,lambda:self.pilot(key),False)
        self.g.admit(2*max(self.res.moves))

    def production(self):
        import torch
        text={};recon={}
        for owner,layer,batch,key in [('ol',44,16,'ol_generation'),('nla',42,32,'nla_generation')]:
            self.res.get(owner)
            for feature in FEATURES:
                torch.manual_seed(0)  # S14's source generation seed, restarted per row/reader.
                ix=self.spec[feature]['indices'];out=[]
                for s in range(0,84,batch):
                    out+=self.timed(key,lambda s=s:self.generation(owner,self.h[layer][ix[s:s+batch]]),True)
                    dump(self.a.out/f'{owner}-{feature}.json',out)
                if len(out)!=84 or any(len(v)!=2 for v in out):raise ValueError('two samples per recipient required')
                text[owner,feature]=out
        decoder=self.res.get('decoder')
        for owner in ('ol','nla'):
            for feature in FEATURES:
                flat=[t for row in text[owner,feature] for t in row];pieces=[]
                for s in range(0,168,16):
                    p=self.timed('reconstruction',lambda s=s:decoder.reconstruct(flat[s:s+16],batch=16).float(),True)
                    pieces.append(p)
                    np.save(self.a.out/f'recon-{owner}-{feature}-unit{s//16:03d}.npy',p.numpy(),allow_pickle=False)
                recon[owner,feature]=torch.cat(pieces).reshape(84,2,5120).mean(1)
        self.res.get('nla')
        for feature in FEATURES:
            r=self.spec[feature];ix=r['indices'];pairs=r['pairs'];n=112//(2*len(pairs))
            vecs=self.lib.construct(self.h[42][ix],recon['ol',feature],recon['nla',feature],np.array(r['partners']))
            for arm in ARMS:
                pieces=[]
                for s in range(0,84,n):
                    out=self.timed('asked',lambda s=s:self.score(vecs[arm][s:s+n],pairs),True)
                    pieces.append(out)
                    np.save(self.a.out/f'score-{feature}-{arm}-unit{s//n:03d}.npy',out,allow_pickle=False)
                result=np.concatenate(pieces,axis=1)
                if result.shape!=(len(pairs),84) or not np.isfinite(result).all():raise ValueError('complete finite follow-score grid required')
                np.save(self.a.out/f'scores-{feature}-{arm}.npy',result,allow_pickle=False)
        if self.g.completed!=self.g.counts:raise ValueError('full production counts not met')


def execute(a,g):
    res=None;status='COMPLETE';error=None
    try:
        res=Residents(a,g);c=Collection(a,g,res);c.setup_and_admit();c.production();g.guard()
    except Exception as exc:
        status='NO_FIT' if isinstance(exc,NoFit) else 'INCOMPLETE';error=type(exc).__name__+': '+str(exc)
    g.status=status;g.write()
    dump(a.out/'run.json',{'status':status,'error':error,'experiment':'E27C','PID':os.getpid(),
         'source_commit':g.a['source_commit'],'source_files':g.a['source_files'],
         'input_seal_sha256':g.a['input_seal_sha256'],'assignment_sha256':g.assignment_sha,
         'checkpoint_load_counts':res.loads if res else {},'science_seconds':g.elapsed(),
         'setup_and_science_budget_seconds':TOTAL_SECONDS,'test_labels_accessed':False,'paired_samples':2,
         'scorer':'S16 native NLA B-minus-A; mean and fixed summaries deferred to CPU'})
    seal(a.out,[str(p.relative_to(a.out)) for p in a.out.rglob('*') if p.is_file()],'E27C_'+status)
    return status


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','assets','assignment','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();spec=validate(a.inputs)
    if any(a.inputs.rglob('*.DO_NOT_STAGE.*')):raise ValueError('private labels forbidden on worker')
    g=Gate(a.assignment,counts(spec))
    if g.a.get('assets_sha256')!=sha(a.assets) or g.a.get('input_seal_sha256')!=sha(a.inputs/'INPUT_SEAL.json'):raise ValueError('assignment input/assets mismatch')
    a.out.mkdir(parents=True,exist_ok=False);g.out=a.out;g.write()
    status=execute(a,g);print('HANDOFF E27C',status,a.out/'SCORE_SEAL.json',flush=True)
    if status!='COMPLETE':raise SystemExit(2)
