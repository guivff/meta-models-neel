"""Integrator-only E1b -> E12, single process, one load per model, independent clocks."""
import argparse
import gc
import os
import time
from pathlib import Path
import numpy as np
from .cpu import ROOT,read,rows,dump,sha,verify,seal
from .e12 import carrier,activation_for
from .followup_runtime import Gate,collect


def greedy16(model,tok,records):
    import torch
    seqs=[r['ids'] for r in records]
    if len({len(s) for s in seqs})!=1:raise ValueError('generation forbids padding heterogeneous prefixes')
    ids=torch.tensor(seqs,device=model.device)
    # Explicit kwargs override inherited model EOS settings. Do not suppress EOS logits: exact argmax,
    # including any EOS tokens, continues for 16 steps. min_new_tokens=16 would alter that argmax.
    options=dict(do_sample=False,num_beams=1,max_new_tokens=16,min_new_tokens=0,eos_token_id=None,
        forced_eos_token_id=None,forced_bos_token_id=None,stop_strings=None,repetition_penalty=1.,
        no_repeat_ngram_size=0,bad_words_ids=None,suppress_tokens=None,begin_suppress_tokens=None,
        pad_token_id=tok.pad_token_id or tok.eos_token_id,use_cache=True)
    with torch.inference_mode():generated=model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),**options)
    continuation=generated[:,ids.shape[1]:].cpu().tolist()
    if any(len(c)!=16 for c in continuation):raise ValueError('incomplete 16-token continuation')
    return [{'id':r['id'],'feature':r['feature'],'ids':c,
        'text':tok.decode(c,skip_special_tokens=False,clean_up_tokenization_spaces=False)} for r,c in zip(records,continuation)]


def context_pair(reader,name,records,acts,spec,pair,arm):
    """Native transforms and answer registers; same candidate pair always shares a forward."""
    import torch
    tok=reader.tok;model=reader.model if name=='olens' else reader.av;device=reader.device
    carriers=[carrier(tok,spec['request'],r['text'],arm,spec['marker_token_id']) for r in records]
    if len({len(x[0]) for x in carriers})!=1:raise ValueError('context units must have equal head lengths')
    suffix=[] if name=='olens' else tok.encode('<explanation>\n',add_special_tokens=False)
    heads=[x[0]+suffix for x in carriers];headlen=len(heads[0]);cands=[tok.encode(c,add_special_tokens=False) for c in pair]
    if any(not c for c in cands):raise ValueError('empty candidate')
    size=headlen+max(map(len,cands));pad=tok.pad_token_id or 0
    ids=torch.full((len(records)*2,size),pad,dtype=torch.long,device=device);mask=torch.zeros_like(ids)
    for i,head in enumerate(heads):
        for c in range(2):
            seq=head+cands[c];ids[2*i+c,:len(seq)]=torch.tensor(seq,device=device);mask[2*i+c,:len(seq)]=1
    slots=torch.tensor([x[1] for x in carriers],device=device).repeat_interleave(2)
    v=None if acts is None else torch.as_tensor(acts,device=device,dtype=torch.float32).repeat_interleave(2,dim=0)
    hook=None
    with torch.inference_mode():
        if name=='olens':
            emb=model.get_input_embeddings()(ids).clone()
            if v is not None:emb[torch.arange(len(ids),device=device),slots]=(reader.alpha*v/v.norm(dim=-1,keepdim=True).clamp_min(1e-9)).to(emb.dtype)
            kwargs={'inputs_embeds':emb}
        else:
            if reader._vec.get('v') is not None:raise RuntimeError('native NLA hook unexpectedly active')
            if v is not None:
                def inject(_m,_i,out):
                    h=out[0] if isinstance(out,tuple) else out;ix=torch.arange(len(ids),device=h.device)
                    hp=h[ix,slots,:];vu=(v/(v.norm(dim=-1,keepdim=True)+1e-9)).to(h.dtype)
                    h[ix,slots,:]=hp+hp.norm(dim=-1,keepdim=True)*vu
                    return out
                blocks=[m for n,m in model.named_modules() if n.endswith('model.layers.1')]
                if len(blocks)!=1:raise ValueError('unique native NLA block1 hook required')
                hook=blocks[0].register_forward_hook(inject)
            kwargs={'input_ids':ids}
        try:
            logits=model(**kwargs,attention_mask=mask,logits_to_keep=size-headlen+1,use_cache=False).logits
            lp=torch.log_softmax(logits[:,:-1].float(),dim=-1)
            token_lp=lp.gather(-1,ids[:,headlen:].unsqueeze(-1)).squeeze(-1)
            out=[float(token_lp[2*i,:len(cands[0])].sum()-token_lp[2*i+1,:len(cands[1])].sum()) for i in range(len(records))]
        finally:
            if hook is not None:hook.remove()
    if not np.isfinite(out).all():raise ValueError('nonfinite context score')
    return out


def score_unit(reader,name,unit,items,h,templates,spec):
    import torch
    ix=unit['indices'];rs=[items[i] for i in ix];arm=unit['arm'];pairs=templates[unit['feature']][name]
    if len(pairs)!=2:raise ValueError('exact two frozen W1 phrasing pairs required')
    values=activation_for(arm,h[ix],h[[r['wrong_activation_index'] for r in rs]])
    if arm=='activation_only':
        v=torch.as_tensor(values,dtype=torch.float32)
        if name=='olens':scores=reader.paired_logodds_templates(v,44,pairs).numpy().T.tolist()
        else:
            from mats.readers.nla import paired_logodds_templates
            scores=paired_logodds_templates(reader,v,pairs,batch=32).numpy().T.tolist()
    else:scores=np.array([context_pair(reader,name,rs,values,spec,pair,arm) for pair in pairs]).T.tolist()
    if np.asarray(scores).shape!=(len(rs),2) or not np.isfinite(scores).all():raise ValueError('invalid score grid')
    return [{'id':r['id'],'feature':r['feature'],'reader':name,'layer':44 if name=='olens' else 42,
        'arm':arm,'scores':v,'score':float(np.mean(v))} for r,v in zip(rs,scores)]


class Residents:
    def __init__(self,a,gates):
        self.a=a;self.gates=gates;self.objects={};self.loads={};self.active=None;self.current=None;self.completed_science=0.;self.events=[]
        self.setup_guard()
        from projects.g_agreement.blindspot.run import _assets
        from projects.g_agreement.blindspot.ar_tests import _assets as ar_assets
        self.assets=_assets(a.assets,('model','olens','nla'));ar_assets(a.assets,('ar',));self.assets_sha=sha(a.assets)
        self.setup_guard()

    def setup_guard(self):
        a=next(iter(self.gates.values())).assignment
        if time.time()-a['provider_created_epoch']-self.completed_science>=a['setup_allowance_seconds']:raise TimeoutError('shared 2400s setup exhausted')
        if time.time()>=a['deadline_epoch']-180:raise TimeoutError('packed hardstop reserve')

    def module(self,name):
        obj=self.objects[name]
        return obj[0] if name in ['target','ar'] else (obj.model if name=='olens' else obj.av)

    def move(self,name,device):
        import torch
        module=self.module(name)
        if device=='cpu' and Path('/proc/meminfo').exists():
            info={r.split(':')[0]:int(r.split()[1])*1024 for r in Path('/proc/meminfo').read_text().splitlines() if len(r.split())>1 and r.split()[1].isdigit()}
            need=sum(p.numel()*p.element_size() for p in module.parameters() if p.device.type=='cuda')
            if info.get('MemAvailable',0)<need+8*1024**3:raise MemoryError('insufficient RAM for persistent offload; no reload allowed')
        module.to(device)
        if name in ['olens','nla']:self.objects[name].device=device
        self.events.append({'event':'move','model':name,'device':device,'PID':os.getpid(),'epoch':time.time()})
        if device=='cpu':gc.collect();torch.cuda.empty_cache()

    def load(self,name):
        if name=='ar':
            from projects.g_agreement.w_claims.ar import load_reconstructor
            return load_reconstructor(self.a.official,self.a.whitener,self.assets['ar'],self.assets['model'])
        if name=='olens':
            from mats.readers.olens import load_olens
            if 'target' not in self.objects:raise RuntimeError('Oracle must reuse the already loaded target backbone; no base reload')
            model,tok=self.objects.pop('target');model.to('cuda')
            self.events.append({'event':'reuse_target_backbone_for_Oracle','PID':os.getpid(),'epoch':time.time()})
            return load_olens(model=model,tok=tok,lora_dir=self.assets['olens'])
        if name=='nla':
            import common
            from mats.readers.nla import load_nla
            return load_nla(root=self.assets['nla'],load_ar=False)
        if name!='target':raise ValueError('unexpected model')
        import torch
        from transformers import AutoModelForCausalLM,AutoTokenizer
        return (AutoModelForCausalLM.from_pretrained(self.assets['model'],dtype=torch.bfloat16,device_map='cuda',local_files_only=True).eval(),AutoTokenizer.from_pretrained(self.assets['model'],local_files_only=True))

    def get(self,name):
        if sha(self.a.assets)!=self.assets_sha:raise ValueError('asset manifest changed')
        if self.active!=name:
            if self.active is not None:self.move(self.active,'cpu');self.active=None
            if name not in self.objects:
                if self.current is not None and self.gates[self.current].started is not None:raise RuntimeError('checkpoint first load inside science forbidden')
                if self.loads.get(name,0):raise RuntimeError('checkpoint reload forbidden')
                self.setup_guard();self.loads[name]=1;self.events.append({'event':'load','model':name,'PID':os.getpid(),'epoch':time.time()})
                self.objects[name]=self.load(name);self.setup_guard()
            else:self.move(name,'cuda')
            self.active=name
        return self.objects[name]

    def release(self,name):
        if name in self.objects:self.move(name,'cpu')
        self.objects.pop(name,None)
        if self.active==name:self.active=None
        import torch
        gc.collect();torch.cuda.empty_cache()

    def park(self,name):
        self.move(name,'cpu')
        if self.active==name:self.active=None


def jsonl(path,rs):path.write_text(''.join(__import__('json').dumps(r,sort_keys=True,ensure_ascii=False)+'\n' for r in rs))


def e1b(a,resident,g,root):
    inp=a.inputs/'e1b';items=rows(inp/'items.input.jsonl');units=read(inp/'generation_units.json')
    target,tok=resident.get('target');warm=max(units,key=lambda u:(u['length'],len(u['indices'])))
    greedy16(target,tok,[items[i] for i in warm['indices']]);g.setup_guard()
    ar,atok,_=resident.get('ar')
    from projects.g_agreement.w_claims.ar import reconstruct
    # Only this frozen neutral synthetic text warms AR. No item continuation enters AR before its seal.
    neutral=tok.decode(tok.encode('A neutral passage about ordinary daily activities. '*8,add_special_tokens=False)[:16],skip_special_tokens=False,clean_up_tokenization_spaces=False)
    reconstruct(ar,atok,[neutral]*8);g.setup_guard()
    # Reuse the exact same objects that were loaded and warmed in setup.
    target,tok=resident.get('target');fn=lambda u:greedy16(target,tok,[items[i] for i in u['indices']])
    result=collect(units,fn,g,'generation',root/'generation-units');resident.park('target')
    expected=[r['id'] for r in items];mapping={r['id']:r for r in result}
    if set(mapping)!=set(expected) or len(result)!=len(expected):raise ValueError('incomplete continuation population')
    cont=root/'continuations';cont.mkdir();jsonl(cont/'continuations.jsonl',[mapping[key] for key in expected]);dump(cont/'ids.json',expected)
    dump(cont/'provenance.json',{'input_seal_sha256':sha(inp/'INPUT_SEAL.json'),'greedy_tokens':16,'dev_count':2100,'test_count':2100,'frozen_before_any_retained_AR_call':True})
    seal(cont,['continuations.jsonl','ids.json','provenance.json'],'E1B_GREEDY_CONTINUATIONS_SEALED_BEFORE_AR_AND_LABEL_JOIN');g.guard()
    test=read(inp/'test_ids.json');records=[mapping[key] for key in test];ar,atok,_=resident.get('ar')
    batches=[records[i:i+8] for i in range(0,len(records),8)]
    def run(batch):
        x=reconstruct(ar,atok,[r['text'] for r in batch]).numpy()
        if x.shape!=(len(batch),5120) or not np.isfinite(x).all():raise ValueError('invalid continuation reconstruction')
        return [{'id':r['id'],'recon':v.tolist()} for r,v in zip(batch,x)]
    recon=collect(batches,run,g,'ar',root/'ar-units');out=root/'ar';out.mkdir();dump(out/'ids.json',[r['id'] for r in recon])
    np.save(out/'recon.npy',np.array([r['recon'] for r in recon],dtype=np.float32),allow_pickle=False)
    dump(out/'provenance.json',{'input_seal_sha256':sha(inp/'INPUT_SEAL.json'),'continuation_seal_sha256':sha(cont/'SCORE_SEAL.json'),'reader':'AR44','text':'continuation only; no source prefix or label'})
    seal(out,['ids.json','recon.npy','provenance.json'],'E1B_AR_CONTINUATION_RECONSTRUCTIONS_SEALED_BEFORE_LABEL_JOIN');resident.release('ar')


def e12(a,resident,g,root):
    inp=a.inputs/'e12';items=rows(inp/'items.input.jsonl');templates=read(inp/'templates.json');specs=read(inp/'provenance.json')['native_carriers']
    plans={name:read(inp/(name+'_units.json')) for name in ['olens','nla']};hs={name:np.load(inp/f'acts{layer}.npy',allow_pickle=False) for name,layer in [('olens',44),('nla',42)]}
    native_status={};available=[]
    # Each reader's actual context forward is checked and all paths warmed before E12 science.
    for name in ['olens','nla']:
        try:
            reader=resident.get(name);spec=specs[name]
            from .cpu import sha as digest
            if digest(Path(resident.assets['model'] if name=='olens' else resident.assets['nla']+'/av_base')/'tokenizer.json')!=spec['tokenizer_json_sha256']:raise ValueError('runtime tokenizer mismatch')
            if name=='olens':native=reader.carrier(44)
            else:native=(reader.prompt_ids,reader.marker)
            if carrier(reader.tok,spec['request'],'','activation_only',spec['marker_token_id'])!=native:raise ValueError('native carrier mismatch')
            for phase in ['native','context']:
                warm=max(plans[name][phase],key=lambda u:(u.get('head_length',0),len(u['indices'])))
                if phase=='context':
                    for arm in ['text_activation','text_only','text_wrong_activation']:
                        score_unit(reader,name,{**warm,'arm':arm},items,hs[name],templates,spec)
                else:score_unit(reader,name,warm,items,hs[name],templates,spec)
            g.setup_guard();native_status[name]='SUPPORTED_NATIVE_PREFIX';available.append(name)
        except Exception as exc:
            if name=='olens' or isinstance(exc,(TimeoutError,MemoryError)):raise
            native_status[name]={'status':'NLA_PREFIX_UNAVAILABLE','error':type(exc).__name__+': '+str(exc)}
            resident.release(name)
            for phase in ['native','context']:g.forecasts[name+'_'+phase]=0.;g.phases[name+'_'+phase]={'unavailable':True}
    dump(root/'PREFIX_PREFLIGHT.json',native_status)
    for name in available:
        reader=resident.get(name);score=[]
        for phase in ['native','context']:
            fn=lambda u:score_unit(reader,name,u,items,hs[name],templates,specs[name])
            score+=collect(plans[name][phase],fn,g,name+'_'+phase,root/(name+'-'+phase+'-units'))
        out=root/name;out.mkdir();jsonl(out/'scores.jsonl',score)
        expected={(r['id'],arm) for r in items for arm in ['activation_only','text_activation','text_only','text_wrong_activation']}
        if len(score)!=len(expected) or {(r['id'],r['arm']) for r in score}!=expected:raise ValueError('incomplete four-arm grid')
        dump(out/'provenance.json',{'input_seal_sha256':sha(inp/'INPUT_SEAL.json'),'reader':name,'native_prefix':native_status[name],'right_padding_only':True,'text_only':'no injection; own placeholder embedding/residual retained','batch':'both candidates jointly;equal-headlength context units;frozen order'})
        seal(out,['scores.jsonl','provenance.json'],'E12_FOUR_ARM_SCORES_SEALED_BEFORE_LABEL_JOIN');resident.release(name)


def execute(a,resident):
    statuses={}
    for tag,fn in [('E1b',e1b),('E12',e12)]:
        g=resident.gates[tag];resident.current=tag;root=a.out/tag.lower();root.mkdir();g.state_path=root/'CLOCK.json';error=None;status='COMPLETE'
        try:fn(a,resident,g,root);g.guard()
        except Exception as exc:status='INCOMPLETE';error=type(exc).__name__+': '+str(exc)
        g.state_status=status;g.write_state()
        elapsed=time.monotonic()-g.started if g.started is not None else 0.
        dump(root/'run.json',{'experiment':tag,'status':status,'error':error,'PID':os.getpid(),'first_science_epoch':getattr(g,'first_science_epoch',None),'elapsed_science_seconds':elapsed,'clock_resets':0,'allocation_seconds':g.allocation,'paths':g.phases,'input_seal_sha256':sha(a.inputs/tag.lower()/'INPUT_SEAL.json')})
        names=[str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()]
        seal(root,names,'EXPLORATORY_'+tag+'_'+status);statuses[tag]=status
        resident.completed_science+=time.monotonic()-g.started if g.started is not None else 0.;resident.current=None
        for name in list(resident.objects):
            if tag=='E1b' and name=='target':resident.park(name)  # live backbone becomes Oracle in E12 setup
            else:resident.release(name)
        print('HANDOFF',tag,status,root/'SCORE_SEAL.json',flush=True)
    dump(a.out/'packed.json',{'order':['E1b','E12'],'same_process':True,'PID':os.getpid(),'checkpoint_load_counts':resident.loads,'events':resident.events,'status':statuses,'E1_E2_E7_executed':False})
    seal(a.out,['packed.json','e1b/SCORE_SEAL.json','e12/SCORE_SEAL.json'],'E1B_E12_PACKED_RECEIPT')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['inputs','assets','assignments','official','whitener','out']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();gates={tag:Gate(a.assignments/(tag.lower()+'.json'),tag) for tag in ['E1b','E12']}
    for key in ['pod_id','provider_created_epoch','packed_science_seconds','setup_allowance_seconds','deadline_epoch']:
        if len({g.assignment[key] for g in gates.values()})!=1:raise ValueError('packed assignments disagree: '+key)
    if sum(g.initial_allocation for g in gates.values())!=gates['E1b'].assignment['packed_science_seconds']:raise ValueError('packed allocated sum mismatch')
    if any(g.assignment.get('assets_sha256')!=sha(a.assets) for g in gates.values()):raise ValueError('assignment asset manifest binding mismatch')
    for tag,g in gates.items():
        verify(a.inputs/tag.lower(),'INPUT_SEAL.json')
        if g.assignment['input_seal_sha256']!=sha(a.inputs/tag.lower()/'INPUT_SEAL.json'):raise ValueError('input binding mismatch')
    if any(a.inputs.rglob('*.DO_NOT_STAGE.*')):raise ValueError('label-bearing data must not enter worker archive')
    a.out.mkdir(exist_ok=False,parents=True);resident=Residents(a,gates)
    for g in gates.values():g.setup_callback=resident.setup_guard
    execute(a,resident)


if __name__=='__main__':main()
