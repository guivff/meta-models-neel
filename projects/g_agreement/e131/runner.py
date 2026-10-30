"""§239 generation only; sealed E104 U hook and same-pass frozen pairs."""
import time
from pathlib import Path
import numpy as np
from projects.g_agreement.e100.contract import read,write,sha,verify
from projects.g_agreement.e101.intervention104 import intervene_forward
from projects.g_agreement.e127.runner import pairs_from_logits
CONDITIONS=('e104_steered_8','e104_random_8','unhooked','e128_steered_2','e128_random_2','e128_steered_4','e128_random_4','context_update','neutral_prefix','none')
MAX_NEW_TOKENS=64


def source_gate():
    root=Path(__file__).resolve().parents[3]
    seal=read(Path(__file__).with_name('SOURCE_SEAL.json'))
    for name,digest in seal['files'].items():
        if sha(root/name)!=digest:raise ValueError('changed sealed E131 runtime source: '+name)


def generate_batch(model,tok,items,deltas):
    import torch
    if not items or len({(x['condition'],len(x['ids'])) for x in items})!=1:raise ValueError('homogeneous unpadded condition batch')
    if any(x['condition']not in CONDITIONS or x['read_index']!=len(x['ids'])-1 for x in items):raise ValueError('registered condition/answer position')
    hooked=[x['delta_index']is not None for x in items]
    if len(set(hooked))!=1:raise ValueError('uniform hook state')
    delta=np.asarray(deltas)[[x['delta_index']for x in items]].copy() if hooked[0] else None
    before=None if delta is None else delta.tobytes()
    sequences=[list(x['ids'])for x in items];positions=[x['read_index']for x in items]
    eos=getattr(tok,'eos_token_id',None);eos=set(eos if isinstance(eos,(list,tuple))else [] if eos is None else [eos])
    generated=[[]for _ in items];done=[False]*len(items);first=None;first_greedy=None
    for step in range(MAX_NEW_TOKENS):
        if hooked[0]:
            # Original U implementation: same composed delta, eight ORIGINAL positions,
            # no read-token/new-token patch, no dose multiplier, no extra observation pass.
            z,_,_=intervene_forward(model,sequences,positions,delta,'U',1,observe=False)
        else:
            ids=torch.tensor(sequences,device=model.get_input_embeddings().weight.device)
            with torch.inference_mode():z=model(input_ids=ids,attention_mask=torch.ones_like(ids),use_cache=False,logits_to_keep=1).logits
        z=z[:,0].float()
        if not torch.isfinite(z).all():raise ValueError('finite generation logits')
        chosen=z.argmax(-1).cpu().tolist()
        if step==0:first=pairs_from_logits(z,items);first_greedy=chosen.copy()
        for i,t in enumerate(chosen):
            if not done[i]:generated[i].append(t);done[i]=t in eos
            sequences[i].append(t)
        if all(done):break
    if delta is not None and delta.tobytes()!=before:raise ValueError('sealed delta mutated')
    return [dict(id=x['id'],base_id=x['base_id'],condition=x['condition'],token_ids=ts,
      text=tok.decode(ts,skip_special_tokens=True),text_with_special_tokens=tok.decode(ts,skip_special_tokens=False),
      first_greedy_token_id=g,greedy_max_new_tokens=64,stop_reason='eos'if ts and ts[-1]in eos else 'length',
      pair_mean_a_minus_b=float(np.mean([a-b for a,b in r['pair_logprobs']])),**r)
      for x,ts,r,g in zip(items,generated,first,first_greedy)]


def load(root,digest):
    source_gate()
    root=Path(root);s=verify(root,'INPUT_SEAL.json',digest)
    if s['experiment']!='E131'or s['labels_on_pod']is not False or set(s['files'])!={'items.json','deltas.npy','MANIFEST.json'}:raise ValueError('public E131 packet only')
    xs=read(root/'items.json');d=np.load(root/'deltas.npy',allow_pickle=False)
    if len(xs)!=840 or len({x['id']for x in xs})!=840 or d.shape!=(504,5120)or d.dtype!=np.float32 or not np.isfinite(d).all():raise ValueError('full840/504finite sealed deltas')
    fieldset={'id','base_id','condition','ids','read_index','candidate_ids','delta_index'}
    for x in xs:
        if set(x)!=fieldset or x['read_index']!=len(x['ids'])-1 or any(len(c)!=1 for pair in x['candidate_ids']for c in pair):raise ValueError('exact public fields/answer site/frozen single-token pairs')
        expected=x['condition'].startswith(('e104_','e128_'))
        if expected!=(x['delta_index']is not None):raise ValueError('hook condition binding')
    if sorted(x['delta_index']for x in xs if x['delta_index']is not None)!=list(range(504)):raise ValueError('one exact delta per hooked cell')
    groups={}
    for x in xs:groups.setdefault(x['condition'],set()).add(x['base_id'])
    if set(groups)!=set(CONDITIONS)or any(len(v)!=84 for v in groups.values())or len(set.union(*groups.values()))!=84:raise ValueError('same84/all10conditions')
    return xs,d


def batches(items,size=8):
    if type(size)is not int or size<1:raise ValueError('positive batch size')
    groups={}
    for x in items:groups.setdefault((x['condition'],len(x['ids'])),[]).append(x)
    for _,xs in sorted(groups.items()):
        for i in range(0,len(xs),size):yield xs[i:i+size]


def acquire(model,tok,items,deltas,out,check_work,*,gpu_type,batch=8):
    """Q callback owns ORIGINAL whole-need clock, setup, warmup and hard stop."""
    if not callable(check_work)or not gpu_type:raise ValueError('operator clock callback and actual GPU required')
    out=Path(out)
    if out.exists():raise FileExistsError('fresh E131 attempt required; no partial reuse')
    out.mkdir(parents=True);write(out/'ONCE.json',dict(experiment='E131',cells=len(items),reader_calls=0))
    jobs=list(batches(items,batch));(out/'jobs').mkdir();durations=[];index=[];status='COMPLETE';start=time.monotonic()
    for j,xs in enumerate(jobs):
        if not check_work(len(jobs)-j,time.monotonic()-start,max(durations,default=0.0)):
            status='NO_FIT';break
        t=time.monotonic();r=generate_batch(model,tok,xs,deltas);durations.append(time.monotonic()-t)
        for x in r:x['gpu_type']=gpu_type
        name=f'jobs/{j:06d}.json';write(out/name,r)
        index.extend(dict(id=x['id'],member=name,record=k)for k,x in enumerate(r));write(out/'INDEX.json',index)
    write(out/'TIMING.json',dict(batch_seconds=durations,elapsed_seconds=time.monotonic()-start))
    files={str(p.relative_to(out)):sha(p)for p in out.rglob('*')if p.is_file()}
    write(out/'OUTPUT_SEAL.json',dict(experiment='E131',status=status,cells=len(index),max_new_tokens=64,reader_calls=0,judging_calls=0,gpu_type=gpu_type,files=files))
    return status


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--input-sha',required=True);p.add_argument('--validate-only',action='store_true');a=p.parse_args()
    xs,d=load(a.input,a.input_sha)
    if a.validate_only:print('E131 VALIDATE_OK840/504; no model loaded');return
    raise SystemExit('Use acquire with sole Track Q subject model and original operator whole-need clock; no standalone unguarded launch')
if __name__=='__main__':main()
