"""E23 integrator-only collection. One process, one load/model, no label-based scoring."""
import argparse
import os
from pathlib import Path
import time
import numpy as np
from .cpu import ROOT, read, rows, dump, sha, verify, seal
from .e23 import PATHS, TARGET_PATHS, AR_PATHS, LAYERS, UNIQUE_ARMS, BATCH, PLAN, schedule, assemble_texts
from .e23_runtime import Gate, NoFit
from .followup_packed import greedy16, jsonl


def capture(model, records, layers=(40,42,44)):
    """Own block-output hooks, last actual prefix token, right-pad/masked batch."""
    import torch
    import common
    from mats.capture import decoder_blocks
    blocks=decoder_blocks(model); saved={}; hooks=[]
    seqs=[r['ids'] for r in records]; device=model.device
    ids=torch.zeros((len(seqs),max(map(len,seqs))),dtype=torch.long,device=device)
    mask=torch.zeros_like(ids); positions=torch.tensor([len(s)-1 for s in seqs],device=device)
    for i,s in enumerate(seqs): ids[i,:len(s)]=torch.tensor(s,device=device); mask[i,:len(s)]=1
    class Captured(Exception): pass
    def hook(layer):
        def take(module,args,out):
            h=out[0] if isinstance(out,tuple) else out
            saved[layer]=h[torch.arange(len(seqs),device=device),positions].detach().float().cpu().numpy().copy()
            if layer==max(layers): raise Captured()
        return take
    try:
        for layer in layers: hooks.append(blocks[layer].register_forward_hook(hook(layer)))
        with torch.inference_mode():
            try: model(input_ids=ids,attention_mask=mask,use_cache=False,logits_to_keep=1)
            except Captured: pass
    finally:
        for h in hooks: h.remove()
    if set(saved)!=set(layers): raise ValueError('capture hooks incomplete')
    return saved


def reconstruct(ar,tok,texts,layer):
    """E1b raw output path, with the registered layer index as the only extension."""
    import torch
    if layer not in LAYERS: raise ValueError('only tags44/40 registered')
    tokens=tok(texts,add_special_tokens=False,return_tensors='pt',padding=True,truncation=False)
    if not bool((tokens['attention_mask'].sum(1)>0).all()): raise ValueError('empty AR input')
    limit=int(getattr(ar.backbone.config,'text_config',ar.backbone.config).max_position_embeddings)
    if tokens['input_ids'].shape[1]+ar.tag_ids.shape[1]>limit: raise ValueError('AR context overflow; no truncation')
    device=next(ar.parameters()).device
    with torch.inference_mode():
        x=ar(tokens['input_ids'].to(device),tokens['attention_mask'].to(device),layer_idx=ar.layers.index(layer))[:,0].float().cpu().numpy()
    if x.shape!=(len(texts),5120) or not np.isfinite(x).all(): raise ValueError('finite raw AR output required')
    return x


def parity_check(actual,expected):
    report={}; passed=True
    for layer in (40,42,44):
        a=np.asarray(actual[layer],dtype=np.float64); b=np.asarray(expected[layer],dtype=np.float64)
        if a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all(): raise ValueError('parity grid mismatch')
        denominator=np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1)
        if (denominator<=0).any(): raise ValueError('zero norm parity vector')
        cos=(a*b).sum(1)/denominator
        report[str(layer)]={'cosines':cos.tolist(),'minimum':float(cos.min()),'pass':bool((cos>=.999).all())}
        passed=passed and report[str(layer)]['pass']
    return {'status':'PASS' if passed else 'FAIL','all_items_all_layers':passed,'layers':report,'threshold':.999}


def asked(reader,h,layer,pairs):
    import torch
    x=reader.paired_logodds_templates(torch.as_tensor(h,dtype=torch.float32),layer,pairs).numpy().T
    if x.shape!=(len(h),len(pairs)) or not np.isfinite(x).all(): raise ValueError('asked score grid invalid')
    return x


def load(a,g):
    import torch
    from .e18_worker import load_reader
    from projects.g_agreement.blindspot.run import _assets
    from projects.g_agreement.blindspot.ar_tests import _assets as ar_assets
    from projects.g_agreement.w_claims.ar import load_reconstructor
    g.setup_guard()
    if torch.cuda.get_device_properties(0).total_memory<120*1024**3: raise MemoryError('E23 requires >=120GiB for two resident backbones; no reload/offload fallback')
    assets=_assets(a.assets,('model','olens')); ar_assets(a.assets,('ar',))
    g.load_attempts={'AR':1,'Oracle_base_backbone':0,'Oracle_adapter':0}
    ar,tok,ruler=load_reconstructor(a.official,a.whitener,assets['ar'],assets['model']); ar.eval()
    g.setup_guard(); g.load_attempts.update(Oracle_base_backbone=1,Oracle_adapter=1)
    reader=load_reader(a,g); g.setup_guard()
    return reader,ar,tok


class Collection:
    def __init__(self,a,g,reader,ar,tok):
        self.a,self.g,self.reader,self.ar,self.tok=a,g,reader,ar,tok
        self.items=rows(a.inputs/'items.input.jsonl'); self.units=read(a.inputs/'units.json')
        self.pilot=read(a.inputs/'pilot.json'); self.pairs=read(a.inputs/'pairs.json'); self.donors=read(a.inputs/'donors.json')
        self.cont={r['id']:r for r in rows(a.inputs/'O.continuations.jsonl')}
        self.si=[i for i,r in enumerate(self.items) if r['set']=='S']; self.oi=[i for i,r in enumerate(self.items) if r['set']=='O']
        self.h={l:np.full((len(self.items),5120),np.nan,dtype=np.float32) for l in (40,42,44)}
        for l in (42,44): self.h[l][self.oi]=np.load(a.inputs/f'O.acts{l}.npy',allow_pickle=False)
        self.texts=None; self.recon={}; self.scores={}
        for key in PATHS: (a.out/key).mkdir()

    def call(self,key,unit=None,pilot=False):
        if key in ('capture','generation'):
            records=self.pilot['target'] if pilot else [self.items[i] for i in unit]
            with self.reader.base():
                return capture(self.reader.model,records) if key=='capture' else greedy16(self.reader.model,self.reader.tok,records)
        if key in AR_PATHS:
            # Even neutral AR warm-up waits for the full continuation seal.
            verify(self.a.out/'continuations')
            if read(self.a.out/'continuations/SCORE_SEAL.json')['status']!='E23_ALL_F16_FROZEN_BEFORE_ANY_AR': raise ValueError('wrong continuation seal')
            _,layer,arm=key.split('_')
            texts=[self.pilot['AR_neutral_text'][arm]]*BATCH if pilot else [self.texts[arm][i] for i in unit]
            return reconstruct(self.ar,self.tok,texts,int(layer))
        _,layer,phrasing=key.split('_'); layer=int(layer)
        if pilot:
            ix=next(i for i in self.oi if self.items[i]['split']=='dev' and self.items[i]['feature']=='table_column')
            h=np.repeat(self.h[layer][ix:ix+1],BATCH,axis=0)
        else: h=self.h[layer][unit]
        return asked(self.reader,h,layer,self.pairs[phrasing])

    def warm(self,key):
        self.g.setup_guard(); t=time.monotonic(); self.call(key,pilot=True)
        self.g.warm(key,time.monotonic()-t)

    def timed_pilot(self,key):
        for j in range(3):
            self.g.guard(); t=time.monotonic(); self.call(key,pilot=True)
            self.g.record(key,time.monotonic()-t,retained=False)

    def production(self,key):
        received={}
        for j,unit in enumerate(self.units[key]):
            self.g.guard(); t=time.monotonic(); out=self.call(key,unit)
            folder=self.a.out/key
            if key=='capture':
                np.savez(folder/f'unit-{j:05d}.npz',**{str(l):x for l,x in out.items()})
                for l,x in out.items(): self.h[l][unit]=x
            elif key=='generation':
                jsonl(folder/f'unit-{j:05d}.jsonl',out)
                for r in out:
                    if r['id'] in self.cont: raise ValueError('duplicate generated continuation')
                    self.cont[r['id']]=r
            else:
                np.save(folder/f'unit-{j:05d}.npy',out,allow_pickle=False)
                received.update(zip(unit,out))
            self.g.record(key,time.monotonic()-t,retained=True)
        if key in AR_PATHS:
            if set(received)!=set(range(len(self.items))): raise ValueError('incomplete AR grid')
            np.save(self.a.out/(key+'.npy'),np.stack([received[i] for i in range(len(self.items))]),allow_pickle=False)
        elif key.startswith('asked_'):
            expected=[i for u in self.units[key] for i in u]
            jsonl(self.a.out/(key+'.jsonl'),[{'id':self.items[i]['id'],'set':self.items[i]['set'],'scores':received[i].tolist(),'score':float(np.mean(received[i]))} for i in expected])

    def run(self):
        for key in TARGET_PATHS: self.warm(key)
        self.g.start()
        for key in TARGET_PATHS: self.timed_pilot(key)
        self.g.admit_prefix()
        self.production('capture')
        expected={l:np.load(self.a.inputs/f'S.parity{l}.npy',allow_pickle=False) for l in (40,42,44)}
        report=parity_check({l:self.h[l][self.si] for l in expected},expected)
        dump(self.a.out/'PARITY.json',report)
        if not report['all_items_all_layers']: raise ValueError('native capture parity FAIL; no score; report/fix hooks before retry')
        for l in (40,42,44): np.save(self.a.out/f'S.acts{l}.npy',self.h[l][self.si],allow_pickle=False)
        self.production('generation')
        self.texts=assemble_texts(self.items,self.cont,self.donors)
        cont=self.a.out/'continuations'; cont.mkdir()
        jsonl(cont/'continuations.jsonl',[self.cont[r['id']] for r in self.items])
        dump(cont/'provenance.json',{'input_seal_sha256':sha(self.a.inputs/'INPUT_SEAL.json'),'all_items':len(self.items),'tokens':16,'before_any_AR_forward':True,'source_audit_sha256':read(self.a.inputs/'provenance.json')['source_audit_sha256']})
        seal(cont,['continuations.jsonl','provenance.json'],'E23_ALL_F16_FROZEN_BEFORE_ANY_AR')
        for arm in UNIQUE_ARMS:
            bound=len(self.tok.encode(self.pilot['AR_neutral_text'][arm],add_special_tokens=False))
            if any(len(self.tok.encode(t,add_special_tokens=False))>bound for t in self.texts[arm]):
                raise ValueError('AR timing pilot does not cover production lengths; stop without truncation')
        for key in AR_PATHS:
            self.warm(key); self.timed_pilot(key)
        self.g.admit()
        for key in TARGET_PATHS[2:]+AR_PATHS: self.production(key)
        if any(self.g.completed[k]!=len(self.units[k]) for k in PATHS): raise ValueError('incomplete production schedule')


def execute(a,g,loaded=None):
    status,error,loads='COMPLETE',None,{}
    try:
        if loaded is None:
            loaded=load(a,g); loads={'AR':1,'Oracle_base_backbone':1,'Oracle_adapter':1}
        Collection(a,g,*loaded).run()
    except Exception as exc:
        status='NO_FIT' if isinstance(exc,NoFit) else 'INCOMPLETE'; error=type(exc).__name__+': '+str(exc)
    g.status=status; g.write_state()
    dump(a.out/'run.json',{'status':status,'error':error,'experiment':'E23','PID':os.getpid(),
        'checkpoint_load_counts':getattr(g,'load_attempts',loads),'input_seal_sha256':sha(a.inputs/'INPUT_SEAL.json'),
        'source_commit':g.assignment['source_commit'],'assignment_sha256':g.assignment_sha256,
        'science_seconds':g.elapsed(),'first_science_epoch':g.first_science_epoch,'science_clock_resets':0,
        'probe_fits_on_pod':0,'native_layers':[40,42,44],'AR_tags':[44,40],'whitening_applied':False})
    seal(a.out,[str(p.relative_to(a.out)) for p in a.out.rglob('*') if p.is_file()],'E23_'+status)
    return status


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('inputs','assets','assignment','official','whitener','out'): p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args(); verify(a.inputs,'INPUT_SEAL.json')
    plan=read(ROOT/PLAN); units=read(a.inputs/'units.json')
    if units!=schedule(rows(a.inputs/'items.input.jsonl')): raise ValueError('schedule drift')
    if plan['input_seal_sha256']!=sha(a.inputs/'INPUT_SEAL.json'): raise ValueError('input plan mismatch')
    g=Gate(a.assignment,{k:len(v) for k,v in units.items()})
    if g.assignment.get('assets_sha256')!=sha(a.assets) or g.assignment.get('input_seal_sha256')!=sha(a.inputs/'INPUT_SEAL.json'): raise ValueError('asset/input assignment mismatch')
    if any(a.inputs.rglob('*.DO_NOT_STAGE.*')): raise ValueError('private labels cannot be staged')
    a.out.mkdir(parents=True,exist_ok=False); g.out=a.out; g.write_state()
    status=execute(a,g); print('HANDOFF E23',status,a.out/'SCORE_SEAL.json')
    if status!='COMPLETE': raise SystemExit(2)


if __name__=='__main__': main()
