"""§241 runner orchestration: existing E109/E126/E131 arithmetic only."""
from pathlib import Path
from types import FunctionType
import time
import numpy as np
from projects.g_agreement.e100.contract import read,write,sha,verify
from projects.g_agreement.e101 import runner109
from projects.g_agreement.e126 import hook as patch126
from projects.g_agreement.e131 import runner as text131
CAPTURE=(36,44,48,52,56,60)
READ=(44,52,60)
PATCH=(44,48,52,56,60)
# Isolated original functions, unchanged code objects; configuration only.
_natural=FunctionType(runner109.natural_capture.__code__,dict(runner109.natural_capture.__globals__,CAPTURE=CAPTURE))
_generate=FunctionType(text131.generate_batch.__code__,dict(text131.generate_batch.__globals__,MAX_NEW_TOKENS=32))


def generation_batch(model,tok,items,vocab_out=None):
    xs=[dict(x,base_id=x['pair_id']+':'+str(x['member']),condition='unhooked',delta_index=None)for x in items]
    generate=_generate
    if vocab_out is not None:
        def raw_scorer(z,source_items):
            vocab_out.append(z.detach().float().cpu().numpy().copy())
            return text131.pairs_from_logits(z,source_items)
        generate=FunctionType(text131.generate_batch.__code__,dict(text131.generate_batch.__globals__,MAX_NEW_TOKENS=32,pairs_from_logits=raw_scorer))
    result=generate(model,tok,xs,np.empty((0,0),np.float32))
    # E131's output field is a literal64; actual inherited loop is configured32.
    for x,r in zip(items,result):
        r.pop('pair_mean_a_minus_b',None) # Global-vocabulary average is NOT an item preference.
        r.update(pair_id=x['pair_id'],family=x['family'],member=x['member'],greedy_max_new_tokens=32,candidate_ids=x['candidate_ids'])
    return result


def capture_batch(model,tok,items):
    values=_natural(model,items);vocab=[];answers=generation_batch(model,tok,items,vocab)
    if len(vocab)!=1:raise ValueError('one same-prefill raw vocabulary capture')
    return dict(activations=values,answers=answers,vocab_logits=vocab[0])


def patch_batch(model,items,replacement,block,control):
    """Natural paired swap, E126 insert path: upstream hook NEVER installed."""
    if block not in PATCH or control not in ('read','earlier','random'):raise ValueError('registered block/control')
    target=np.asarray(replacement);dimension=target.shape[1]
    if target.shape!=(len(items),dimension):raise ValueError('paired replacement shape')
    payload=[];xs=[]
    for x,v in zip(items,target):
        earlier,unit=patch126.controls(x['id'],x['read_index'],block,dimension,'insert')
        payload.append(np.concatenate([np.zeros(dimension,np.float32),v.astype(np.float32),unit,np.array([earlier],np.float32)]))
        xs.append(dict(x,base_id=x['pair_id']+':'+str(x['member']),block=block,direction='insert',control=control))
    observed=[]
    z=patch126.forward(model,[x['ids']for x in xs],[x['read_index']for x in xs],np.stack(payload),block,1,direction='insert',control=control,observations=observed)[:,0]
    # All candidate strings are single tokens: E131 same-pass scorer is exact.
    # Do not repeat identical prefixes for each of45global contrasts.
    scores=text131.pairs_from_logits(z,xs)
    return [dict(r,id=x['id'],input_id=x['id'],block=block,direction='insert',control=control,patch=m,candidate_ids=x['candidate_ids'])for x,r,m in zip(xs,scores,observed)]


def batches(items,size=8):
    groups={}
    for i,x in enumerate(items):groups.setdefault((x['family'],len(x['ids'])),[]).append(i)
    for _,ix in sorted(groups.items()):
        for j in range(0,len(ix),size):yield ix[j:j+size]


def load(root,digest,stage):
    root=Path(root);seal=verify(root,'INPUT_SEAL.json',digest)
    if seal['experiment']!='E133'or seal['stage']!=stage or seal['labels_on_pod']is not False:raise ValueError('public stage-bound E133 seal')
    allowed={'items.json','MANIFEST.json'}|({'SCREEN_SELECTION_SEAL.json'}if stage=='main'else set())
    if set(seal['files'])!=allowed:raise ValueError('E133 public members/labels excluded')
    xs=read(root/'items.json');validate_items(xs,stage)
    if stage=='main':
        selected=read(root/'SCREEN_SELECTION_SEAL.json')
        if selected.get('selection_basis')!='behaviour_only_both_members_correct' or selected.get('reader_calls_before_selection')!=0 or not selected.get('screen_output_seal_sha256'):raise ValueError('frozen behaviour-only roster seal required')
        if selected.get('kept_item_ids')!=[x['id']for x in xs]:raise ValueError('exact frozen main roster')
    return xs


def validate_items(xs,stage):
    fields={'id','pair_id','family','member','ids','read_index','candidate_ids'}
    if stage not in ('screen','main')or not xs or len({x['id']for x in xs})!=len(xs):raise ValueError('unique stage item IDs')
    pairs={}
    for x in xs:
        if set(x)!=fields or x['family']not in ('multi_hop','one_hop','babi')or x['member']not in (0,1):raise ValueError('label-free E133 fields')
        if x['read_index']!=len(x['ids'])-1 or x['read_index']<=8 or not x['candidate_ids']or any(len(p)!=2 or any(len(c)!=1 for c in p)for p in x['candidate_ids']):raise ValueError('final read and frozen single-token pairs')
        pairs.setdefault(x['pair_id'],[]).append(x)
    counts={'multi_hop':0,'one_hop':0,'babi':0}
    for pair in pairs.values():
        if len(pair)!=2 or {x['member']for x in pair}!={0,1} or len({x['family']for x in pair})!=1:raise ValueError('both original pair members')
        if pair[0]['candidate_ids'][0]!=pair[1]['candidate_ids'][0]:raise ValueError('first pair is common ordered recipient contrast')
        counts[pair[0]['family']]+=1
    if counts['babi']:
        if counts['multi_hop']or counts['one_hop']or(stage=='main'and counts['babi']>42):raise ValueError('separate descriptive bAbI arm only')
        return counts
    counts.pop('babi')
    if stage=='screen'and counts!={'multi_hop':300,'one_hop':150}:raise ValueError('full450 candidate pairs/900prompts')
    if stage=='main'and not(0<=counts['multi_hop']<=84 and 0<=counts['one_hop']<=42):raise ValueError('frozen up-to84/42pairs; no silent refill')
    return counts


class Writer:
    def __init__(self,out,stage,check_work,gpu_type,arm):
        self.out=Path(out)
        if self.out.exists():raise FileExistsError('fresh attempt only; no partial reuse')
        if not callable(check_work)or not gpu_type:raise ValueError('original operator clock/GPU required')
        self.out.mkdir(parents=True);self.check=check_work;self.gpu=gpu_type;self.stage=stage;self.arm=arm;self.start=time.monotonic();self.times=[];self.setup_times=[];self.index=[]
        write(self.out/'ONCE.json',dict(experiment='E133',stage=stage,arm=arm))
    def admit(self,remaining):return self.check(remaining,time.monotonic()-self.start,max(self.times,default=0.0))
    def finish(self,status):
        write(self.out/'INDEX.json',self.index);write(self.out/'TIMING.json',dict(call_seconds=self.times,setup_seconds=self.setup_times,elapsed=time.monotonic()-self.start))
        write(self.out/'OUTPUT_SEAL.json',dict(experiment='E133',stage=self.stage,arm=self.arm,status=status,gpu_type=self.gpu,max_new_tokens=32,files={str(p.relative_to(self.out)):sha(p)for p in self.out.rglob('*')if p.is_file()}))
        return status


def screen(model,tok,items,out,check_work,*,gpu_type,batch=8):
    validate_items(items,'screen');w=Writer(out,'screen',check_work,gpu_type,'babi'if items[0]['family']=='babi'else 'synthetic');(w.out/'jobs').mkdir();jobs=list(batches(items,batch))
    for j,ix in enumerate(jobs):
        if not w.admit(len(jobs)-j):return w.finish('NO_FIT')
        t=time.monotonic();r=generation_batch(model,tok,[items[i]for i in ix]);w.times.append(time.monotonic()-t)
        name=f'jobs/{j:06d}.json';write(w.out/name,r);w.index.extend(dict(id=x['id'],member=name,record=k)for k,x in enumerate(r))
    return w.finish('COMPLETE')


def main_job(runtime,items,out,check_work,*,gpu_type,batch=8):
    """Existing Backend87; Q owns timed subject/Oracle setup and original deadline."""
    validate_items(items,'main');w=Writer(out,'main',check_work,gpu_type,'babi'if items[0]['family']=='babi'else 'synthetic');model,tok,cm=runtime.subject();captures={};jobs=list(batches(items,batch))
    mate={}
    for x in items:mate[(x['pair_id'],x['member'])]=x['id']
    patch_jobs=[]
    for L in PATCH:
        eligible=[x for x in items if x['family']in ('multi_hop','babi')or L in (44,52)]
        for ix in batches(eligible,batch):
            for control in ('read','earlier','random'):patch_jobs.append((L,control,[eligible[i]for i in ix]))
    remaining=len(jobs)+len(patch_jobs)+len(jobs)*len(READ)
    (w.out/'capture').mkdir();(w.out/'patch').mkdir();(w.out/'oracle').mkdir()
    with cm:
        for j,ix in enumerate(jobs):
            if not w.admit(remaining):return w.finish('NO_FIT')
            xs=[items[i]for i in ix];t=time.monotonic();result=capture_batch(model,tok,xs);w.times.append(time.monotonic()-t);remaining-=1
            write(w.out/f'capture/{j:06d}.json',result['answers'])
            np.save(w.out/f'capture/{j:06d}-vocab.npy',result['vocab_logits'],allow_pickle=False)
            for L,h in result['activations'].items():
                np.save(w.out/f'capture/{j:06d}-{L}.npy',h,allow_pickle=False)
                for x,v in zip(xs,h):captures[(x['id'],L)]=v.copy()
            w.index.extend(dict(id=x['id'],kind='capture_answer',member=f'capture/{j:06d}.json',record=k,raw_vocab_logits=dict(member=f'capture/{j:06d}-vocab.npy',index=k),layers={str(L):dict(member=f'capture/{j:06d}-{L}.npy',index=k)for L in CAPTURE})for k,x in enumerate(xs))
        for j,(L,control,xs)in enumerate(patch_jobs):
            if not w.admit(remaining):return w.finish('NO_FIT')
            target=np.stack([captures[(mate[(x['pair_id'],1-x['member'])],L)]for x in xs]);t=time.monotonic()
            records=patch_batch(model,xs,target,L,control);w.times.append(time.monotonic()-t);remaining-=1
            name=f'patch/{j:06d}.json';write(w.out/name,records);w.index.extend(dict(id=x['id'],kind='patch',block=L,control=control,member=name,record=k)for k,x in enumerate(xs))
    # Call operator-controlled Oracle setup only after all subject work; no new reader code.
    if not w.admit(remaining+1):return w.finish('NO_FIT')
    runtime.model=runtime.tok=None
    del model,tok
    t=time.monotonic();runtime.load_oracle();w.setup_times.append(time.monotonic()-t)
    for L in READ:
        for j,ix in enumerate(jobs):
            if not w.admit(remaining):return w.finish('NO_FIT')
            xs=[items[i]for i in ix];h=np.stack([captures[(x['id'],L)]for x in xs]);t=time.monotonic()
            records=runtime.sweep('oracle',h,L);w.times.append(time.monotonic()-t);remaining-=1
            name=f'oracle/{L}-{j:06d}.json';write(w.out/name,records);w.index.extend(dict(id=x['id'],kind='oracle',block=L,member=name,record=k)for k,x in enumerate(xs))
    return w.finish('COMPLETE')


def source_gate():
    root=Path(__file__).resolve().parents[3]
    seal=read(Path(__file__).with_name('SOURCE_SEAL.json'))
    for name,digest in seal['files'].items():
        if sha(root/name)!=digest:raise ValueError('changed sealed E133 runtime '+name)


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--input-sha',required=True);p.add_argument('--stage',choices=['screen','main'],required=True);p.add_argument('--validate-only',action='store_true');a=p.parse_args()
    source_gate();xs=load(a.input,a.input_sha,a.stage)
    if a.validate_only:print('E133 VALIDATE_OK',a.stage,len(xs),'no model loaded');return
    raise SystemExit('Use screen/main_job under Track Q original clock/admission; no standalone unguarded production')
if __name__=='__main__':main()
