"""E32: integrator-only base-model residual interface test, §127 / 5731e92e."""
import argparse,json,os,signal,time,statistics,math
from pathlib import Path
from contextlib import contextmanager
import numpy as np
from projects.g_agreement.blindspot import protocol as P
from . import e32_e25_reference as E
from .e24_analysis import auc,draws,metric
from .e24_worker import parity,seal

SEED=20261025
ARMS=('A','B','Bprime','same','opposite','random')


def donors(items):
    rng=np.random.default_rng(SEED);out={}
    for x in sorted(items,key=lambda x:x['id']):
        pool=sorted((z for z in items if z['feature']==x['feature'] and z['id']!=x['id']),key=lambda z:z['id'])
        out[x['id']]={k: str(rng.choice([z['id'] for z in pool if k=='random' or (z['value']==x['value'])==(k=='same')])) for k in ('same','opposite','random')}
    return out


@contextmanager
def patch(model, layers, vectors, positions):
    """Replace only placeholder block outputs; leave candidate and newline tokens intact."""
    import torch
    from mats.capture import decoder_blocks,_hidden,_replace_hidden
    handles=[]
    def hook_for(layer):
        def hook(_m,_i,out):
            h=_hidden(out).clone();v=vectors[layer].to(device=h.device,dtype=h.dtype)
            h[torch.arange(len(positions),device=h.device),torch.tensor(positions,device=h.device)]=v
            return _replace_hidden(out,h)
        return hook
    try:
        blocks=decoder_blocks(model)
        for l in layers:handles.append(blocks[l].register_forward_hook(hook_for(l)))
        yield
    finally:
        for h in handles:h.remove()


def summarise(records,items,refs):
    by={x['id']:x for x in items};rows={}
    for f in sorted(refs):
        ids=sorted(x['id'] for x in items if x['feature']==f);y=[by[i]['label'] for i in ids]
        rr={}
        for candidate_set in ('w1','e30'):
            scores={}
            for arm in ARMS:
                selected={r['id']:r['score'] for r in records if r['feature']==f and r['set']==candidate_set and r['arm']==arm}
                if set(selected)==set(ids):scores[arm]=auc(y,[selected[i] for i in ids])
            rr[candidate_set]=scores
        rows[f]=rr
    return rows


def rules(rows,refs,high):
    baseline=all('A' in rows[f]['w1'] and abs(rows[f]['w1']['A']-refs[f]['D'])<=.03+1e-12 for f in refs)
    out={}
    for c in ('w1','e30'):
        content=[f for f in refs if refs[f]['class']=='semantic']
        passed=sum(rows[f][c].get('B',-1)>=.75 for f in content)
        valid=baseline and passed>=7
        low=sum(rows[f][c].get('B',1) <=.60 for f in high)
        high_n=sum(rows[f][c].get('B',0)>=.70 for f in high)
        out[c]={'content_pass':passed,'interpretable':valid,'low_rows':low,'high_rows':high_n,
            'verdict':'NOT EVALUABLE' if not valid else 'NOT_LENS_SPECIFIC' if low>=5 else 'LENS_POLICY' if high_n>=5 else 'MIXED'}
    return {'A_reproduces_E25':baseline,'candidate_sets':out}


class Engine:
    def __init__(self,assets):
        import torch
        from transformers import AutoModelForCausalLM,AutoTokenizer
        a=E.read(assets);path=Path(a['model_path'])
        if a.get('model_id')!=E.MODEL or a.get('revision')!=E.REVISION or a.get('adapter') is not None:raise ValueError('base checkpoint required')
        required=set(E.read(path/'model.safetensors.index.json')['weight_map'].values())|{'config.json','tokenizer.json','tokenizer_config.json','model.safetensors.index.json'}
        if not required<=set(a['files']):raise ValueError('incomplete assets')
        for n,h in a['files'].items():
            if Path(n).is_absolute() or '..' in Path(n).parts or E.sha(path/n)!=h:raise ValueError('asset binding')
        if E.sha(path/'tokenizer.json')!=E.TOKENIZER_SHA or (path/'adapter_config.json').exists():raise ValueError('tokenizer/adapter')
        self.tok=AutoTokenizer.from_pretrained(path,local_files_only=True)
        self.model=AutoModelForCausalLM.from_pretrained(path,local_files_only=True,dtype=torch.bfloat16,device_map='cuda').eval()
        if hasattr(self.model,'peft_config'):raise ValueError('adapter forbidden')
        self.pad=self.tok.pad_token_id if self.tok.pad_token_id is not None else self.tok.eos_token_id

    def capture(self,items):
        from contextlib import nullcontext
        from types import SimpleNamespace
        from mats.capture import decoder_blocks
        from .certified_capture import capture
        base=SimpleNamespace(model=self.model,tok=self.tok,base=nullcontext)
        result,self.last_capture_metadata=capture(base,items,list(range(len(decoder_blocks(self.model)))),self.capture_mode,self.capture_context)
        return result

    def score(self,group,pairs,arm,acts,index,maps):
        import torch
        result=np.zeros(len(group))
        for pair in pairs:
            values=[]
            for candidate in pair:
                frames=[E.encode_frame(self.tok,x['text'] if arm=='A' else '_',candidate) for x in group]
                if arm=='A':v=E.score_batch(self.model,frames,self.pad)
                else:
                    if self.tok.encode('_',add_special_tokens=False)!=frames[0]['ids'][:1]:raise ValueError('placeholder boundary')
                    width=max(len(f['ids']) for f in frames);positions=[width-len(f['ids']) for f in frames]
                    ix=[index[x['id'] if arm in ('B','Bprime') else maps[x['id']][arm]] for x in group]
                    layers=sorted(acts) if arm=='Bprime' else [l for l in acts if l>=44]
                    vectors={l:acts[l if arm=='Bprime' else 44][ix] for l in layers}
                    with patch(self.model,layers,vectors,positions):v=E.score_batch(self.model,frames,self.pad)
                values.append(np.asarray(v))
            result+=(values[0]-values[1])/len(pairs)
        return result.tolist()


def run(a):
    import torch
    plan=E.read(a.plan);assign=E.read(a.assignment);now=time.time()
    if (assign.get('issuer')!='integrator' or assign.get('experiment')!='E32' or not assign.get('pod_id') or assign['pod_id']!=os.getenv('RUNPOD_POD_ID') or assign.get('plan_sha256')!=P.sha(a.plan) or assign.get('assets_manifest_sha256')!=P.sha(a.assets) or assign.get('previous_gpu_seconds')!=0 or assign.get('external_hardstop_verified') is not True or assign.get('source_published') is not True):raise ValueError('integrator assignment')
    from .certified_capture import release,parity_gate
    mode=release(plan,assign,a.certificate,a.capture_context)
    if plan['remaining_gpu_seconds']<=0:raise ValueError('E32 zero remaining budget; coordinator allocation required')
    created=assign['provider_created_epoch'];end=assign['deadline_epoch']
    if not all(isinstance(v,(float,int)) and math.isfinite(v) for v in (created,end)) or not created<=now<end<=created+plan['remaining_gpu_seconds']:raise ValueError('0.5 GPU-hour total custody cap')
    for n,h in plan['source_files'].items():
        if P.sha(P.ROOT/n)!=h:raise ValueError('source binding: '+n)
    P.verify(a.bank,'INPUT_SEAL.json')
    if P.sha(a.bank/'INPUT_SEAL.json')!=plan['input_seal_sha256']:raise ValueError('input binding')
    with a.assignment.with_suffix('.e32-relaunch.lock').open('x') as f:f.write(P.sha(a.plan))
    a.out.mkdir(parents=True,exist_ok=False)
    def timeout(*_):raise TimeoutError('E32 deadline')
    signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,max(.001,end-time.time()-120))
    try:
        if not torch.cuda.is_available():raise ValueError('CUDA required')
        engine=Engine(a.assets);engine.capture_mode=mode;engine.capture_context=a.capture_context;items=P.rows(a.bank/'items.jsonl');pairs=E.read(a.bank/'pairs.json');maps=E.read(a.bank/'DONORS.json');refs=E.read(a.bank/'references.json');index={x['id']:i for i,x in enumerate(items)}
        if engine.tok.encode('_',add_special_tokens=False)!=[62]:raise ValueError('frozen placeholder token changed')
        first=time.time();E.dump(a.out/'SCIENCE_CLOCK.json',{'epoch':first})
        acts=engine.capture(items)
        P.jsonl(a.out/'ITEM_ENVIRONMENT.jsonl',engine.last_capture_metadata)
        for l,h in acts.items():np.save(a.out/f'acts{l}.npy',h.numpy())
        E.dump(a.out/'ORDER.json',[x['id'] for x in items]);parity_gate(acts[44].numpy(),np.load(a.bank/'reference44.npy'),a.out,items)
        seal(a.out,[f'acts{l}.npy' for l in acts]+['ITEM_ENVIRONMENT.jsonl']+['ORDER.json','PARITY.json'],'CAPTURE_SEAL.json','PARITY_PASS')
        records=[];jobs=[]
        for f in sorted(refs):
            group=[x for x in items if x['feature']==f]
            for cs in ('w1','e30'):
                for arm in ARMS:
                    for i in range(0,len(group),4):jobs.append((f,cs,arm,group[i:i+4]))
        # Unscored warm-up + three timed units per candidate set and arm. All costs count.
        timings={}
        for cs in ('w1','e30'):
            for arm in ARMS:
                eligible=[j for j in jobs if j[1:3]==(cs,arm)]
                warm=max(eligible,key=lambda j:max(len(x['ids']) for x in j[3]) if arm=='A' else max(len(engine.tok.encode(c,add_special_tokens=False)) for pair in pairs[cs][j[0]] for c in pair))
                f,_,_,ch=warm
                engine.score(ch,pairs[cs][f],arm,acts,index,maps);units=[]
                for _ in range(3):
                    torch.cuda.synchronize();start=time.monotonic();engine.score(ch,pairs[cs][f],arm,acts,index,maps);torch.cuda.synchronize();units.append(time.monotonic()-start)
                timings[cs+':'+arm]={'units':units,'median_s':statistics.median(units),'batches':len(eligible)}
        remaining=sum(t['median_s']*t['batches'] for t in timings.values())
        deadline=min(end-120,first+min(1.5*(time.time()-first+remaining)+360,1800))
        fit=time.time()+remaining<=deadline;E.dump(a.out/'FORECAST.json',{'remaining_s':remaining,'timings':timings,'deadline':deadline,'status':'FIT' if fit else 'NO_FIT'})
        if not fit:raise ValueError('NO_FIT, no scope reduction or retry')
        signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.time()))
        def phase(j):
            f,cs,arm,ch=j
            return 0 if arm=='A' else 1 if arm=='B' and refs[f]['class']=='semantic' else 2
        for stage in range(3):
            for f,cs,arm,ch in (j for j in jobs if phase(j)==stage):
                v=engine.score(ch,pairs[cs][f],arm,acts,index,maps)
                records.extend(dict(id=x['id'],feature=f,set=cs,arm=arm,score=s) for x,s in zip(ch,v))
            if stage<2:
                gate=rules(summarise(records,items,refs),refs,plan['high_D_rows'])
                E.dump(a.out/f'GATE_PHASE_{stage}.json',gate)
                if not gate['A_reproduces_E25'] or (stage==1 and not any(v['interpretable'] for v in gate['candidate_sets'].values())):
                    P.jsonl(a.out/'gate_scores.jsonl',records)
                    seal(a.out,[f'GATE_PHASE_{stage}.json','gate_scores.jsonl','FORECAST.json','CAPTURE_SEAL.json'],'GATE_SEAL.json','NOT_EVALUABLE_STOPPED')
                    return
        if len(records)!=25200 or len({(x['id'],x['set'],x['arm']) for x in records})!=25200:raise ValueError('incomplete grid')
        P.jsonl(a.out/'scores.jsonl',records);summary=summarise(records,items,refs);E.dump(a.out/'GATES.json',rules(summary,refs,plan['high_D_rows']))
        E.dump(a.out/'BINDING.json',{'plan_sha256':P.sha(a.plan),'input_seal_sha256':plan['input_seal_sha256'],'assignment_sha256':P.sha(a.assignment)})
        seal(a.out,['scores.jsonl','GATES.json','BINDING.json','FORECAST.json','CAPTURE_SEAL.json'],'SCORE_SEAL.json','COMPLETE_GATES_RECORDED')
    except Exception as e:
        E.dump(a.out/'INCOMPLETE.json',{'error':type(e).__name__,'message':str(e),'retry':False});raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('bank','plan','assignment','assets','out','certificate','capture-context'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
