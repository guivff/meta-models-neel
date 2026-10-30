"""§247 E109 natural capture and Oracle, no intervention or bank generation."""
from pathlib import Path
from types import FunctionType
import numpy as np
from projects.g_agreement.e100.contract import read,verify,sha
from projects.g_agreement.e101 import runner109
from projects.g_agreement.e127.runner import pairs_from_logits
LAYERS=(44,52,60)
BANK_SHA='8333875388b59cd90eb2e0f9bcd6a226234022f38fd1e415424c884d447f4e50'
TOKENIZER_REVISION='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'
# Original code object, isolated capture-layer configuration only.
_natural=FunctionType(runner109.natural_capture.__code__,dict(runner109.natural_capture.__globals__,CAPTURE=LAYERS))


def validate_items(items):
    if not items or len({x['id']for x in items})!=len(items):raise ValueError('unique nonempty E136 IDs')
    for x in items:
        if set(x)!={'id','ids','read_index','candidate_ids'}:raise ValueError('public opaque ID/token fields only')
        if not x['ids']or any(type(t)is not int or t<0 for t in x['ids'])or x['read_index']!=len(x['ids'])-1:
            raise ValueError('original full prompt/final token; no truncation')
        pairs=x['candidate_ids']
        if len(pairs)!=1 or any(len(c)!=1 or type(c[0])is not int or c[0]<0 for c in pairs[0])or len(pairs[0])!=2 or pairs[0][0][0]>=pairs[0][1][0]:
            raise ValueError('one frozen ascending single-token answer pair, sign CPU-only')


def load(root,digest):
    if digest!=BANK_SHA:raise ValueError('exact W-text E136 bank required')
    root=Path(root);s=verify(root,'INPUT_SEAL.json',digest)
    if s['experiment']!='E136'or s['labels_on_pod']is not False or set(s['files'])!={'items.json','MANIFEST.json'}:
        raise ValueError('public E136 seal members only')
    items=read(root/'items.json');manifest=read(root/'MANIFEST.json');validate_items(items)
    if len(items)!=800 or manifest['pairs']!=400 or manifest['prompts']!=800 or manifest['labels_on_pod']is not False:
        raise ValueError('complete original800/400 bank, no subset/refill')
    if manifest['tokenizer_revision']!=TOKENIZER_REVISION or manifest['render']!=dict(add_generation_prompt=True,add_special_tokens=False,enable_thinking=False,read='last token of exact rendered chat; final assistant onset',truncation=False):
        raise ValueError('pinned original chat-template rendering')
    return items,manifest


def batches(items,size=8):
    if type(size)is not int or size<1:raise ValueError('positive operator batch size')
    groups={}
    for x in items:groups.setdefault(len(x['ids']),[]).append(x)
    for _,xs in sorted(groups.items()):
        for i in range(0,len(xs),size):yield xs[i:i+size]


def capture_batch(model,items):
    """One unchanged unsteered E109 forward; pair logits from SAME output.

    The read-only model-output observer returns None and changes no tensor.
    The only block observers are E109's original natural_capture observers.
    No steering, patch, generation, sampling or extra forward is installed.
    """
    validate_items(items)
    if len({len(x['ids'])for x in items})!=1:raise ValueError('equal unpadded prompts')
    observed=[]
    def logits_observer(module,args,output):
        z=output.logits
        if z.ndim!=3 or z.shape[:2]!=(len(items),1):raise ValueError('one original final-token logit vector')
        z=z[:,0].float()
        if not np.isfinite(z.detach().cpu().numpy()).all():raise ValueError('finite raw pair logits')
        records=pairs_from_logits(z,items)
        observed.append([dict(id=x['id'],first_greedy_token_id=int(g),candidate_ids=x['candidate_ids'],**r)
                         for x,g,r in zip(items,z.argmax(-1).cpu().tolist(),records)])
    h=model.register_forward_hook(logits_observer)
    try:captures=_natural(model,items)
    finally:h.remove()
    if len(observed)!=1:raise ValueError('one same-pass logit observation')
    return dict(captures=captures,pair_records=observed[0],
                read_norms={str(L):np.linalg.norm(v.astype(np.float64),axis=-1).tolist()for L,v in captures.items()},
                intervention_installed=False,behaviour_mode='same_unhooked_prefill_pair_logits',generation_calls=0)


def oracle_batch(runtime,vectors,layer):
    if layer not in LAYERS:raise ValueError('original E109 reader layers44/52/60')
    v=np.asarray(vectors)
    if v.ndim!=2 or v.shape[1]!=5120 or not np.isfinite(v).all():raise ValueError('original raw5120 activation vectors')
    before=v.tobytes()
    result=runner109.backend87().sweep(runtime,'oracle',v,layer)
    if len(result)!=len(v)or v.tobytes()!=before:raise ValueError('unaltered vectors/one native read per item')
    return result


def source_gate():
    root=Path(__file__).resolve().parents[3];s=read(Path(__file__).with_name('SOURCE_SEAL.json'))
    for name,digest in s['files'].items():
        if sha(root/name)!=digest:raise ValueError('changed sealed E136 source '+name)


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--input-sha',required=True);p.add_argument('--validate-only',action='store_true');a=p.parse_args()
    source_gate();items,_=load(a.input,a.input_sha)
    if a.validate_only:print('E136 VALIDATE_OK',len(items),'capture_batches',len(list(batches(items,8))),'native_readouts',3*len(items),'no model loaded');return
    raise SystemExit('I-2 assignment/original creation-clock custody required; no standalone production')

if __name__=='__main__':main()
