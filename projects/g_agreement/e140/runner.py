"""§252 scope/transport only: original E131 greedy32 and E109 capture/native."""
from pathlib import Path
from types import FunctionType
import time
import numpy as np
from projects.g_agreement.e100.contract import read,write,sha,verify
from projects.g_agreement.e133 import runner as old133
from projects.g_agreement.e136 import runner as old136
from projects.g_agreement.e140.pair_binding import AUTHORITY
LAYERS=(44,52,60)
SCOPE_AUTHORITY='252_deviation2_b10b2694e'
PARENT_INPUT_SHA='5daa0c676bb9cbe561ba1e37e698ac807b38b4eb8965376e7a6e9d5f8fad5819'
PREFIX_INPUT_SHA='76dd4da7a78f210d903b29958b61b55818978a128bfe0e69731fd737cf70fdaa'
PARENT_ITEMS_SHA='453c1bbbb4f73cfa488477547efdade58883c1b21aea38267b24bc821da78641'


def screen_scope(root,digest,items):
    n=validate_items(items,'screen')
    if n==600:return dict(screen_candidates=600,screen_input_sha256=digest)
    m=read(Path(root)/'MANIFEST.json')
    if digest!=PREFIX_INPUT_SHA or m.get('parent_input_sha256')!=PARENT_INPUT_SHA or m.get('parent_items_sha256')!=PARENT_ITEMS_SHA or m.get('authority')!='section252 deviation2 b10b2694e' or m.get('pairs')!=300 or m.get('prompts')!=600:
        raise ValueError('exact sealed authorized first300 parent-bound prefix required')
    return dict(screen_candidates=300,screen_input_sha256=digest,screen_scope_authority=SCOPE_AUTHORITY,parent_input_sha256=PARENT_INPUT_SHA,parent_items_sha256=PARENT_ITEMS_SHA)

generation_batch=old133.generation_batch
oracle_batch=old136.oracle_batch
pair_logits_from_raw_vocab=old136.pairs_from_logits # CPU owner uses original scorer after exact axis binding
batches=old133.batches


def validate_items(items,stage):
    if stage not in ('screen','main')or not items or len({x['id']for x in items})!=len(items):raise ValueError('unique stage-bound IDs')
    groups={}
    for x in items:
        if set(x)!={'id','pair_id','family','member','ids','read_index','candidate_ids'}or x['family']!='paraphrase'or x['member']not in (0,1)or x['candidate_ids']!=[]:
            raise ValueError('opaque paraphrase structure only; no X/Y labels or candidate shortcut')
        if not x['ids']or x['read_index']!=len(x['ids'])-1 or any(type(t)is not int or t<0 for t in x['ids']):raise ValueError('full original tokens/final read position')
        groups.setdefault(x['pair_id'],[]).append(x)
    if any(len(g)!=2 or {x['member']for x in g}!={0,1}for g in groups.values()):raise ValueError('both frozen paraphrases')
    if stage=='screen'and len(groups)not in (300,600) or stage=='main'and not 40<=len(groups)<=84:raise ValueError('full600 or authorized first300 screen / frozen40..84 main')
    return len(groups)


def load(root,digest,stage):
    root=Path(root);s=verify(root,'INPUT_SEAL.json',digest)
    allowed={'items.json','MANIFEST.json'}|({'SCREEN_SELECTION_SEAL.json'}if stage=='main'else set())
    if s.get('experiment')!='E140'or s.get('stage')!=stage or s.get('labels_on_pod')is not False or set(s['files'])!=allowed:raise ValueError('exact label-free E140 stage seal')
    xs=read(root/'items.json');validate_items(xs,stage)
    if stage=='screen':screen_scope(root,digest,xs)
    if stage=='main':
        p=read(root/'SCREEN_SELECTION_SEAL.json')
        if p.get('selection_basis')!='nonempty_different_paraphrase_answers'or p.get('reader_calls_before_selection')!=0 or not p.get('screen_output_seal_sha256')or p.get('kept_item_ids')!=[x['id']for x in xs]:raise ValueError('new complete screen/frozen exact roster before readers')
        if p.get('screen_candidates',600)==300 and (p.get('screen_scope_authority')!=SCOPE_AUTHORITY or p.get('screen_input_sha256')!=PREFIX_INPUT_SHA or p.get('parent_input_sha256')!=PARENT_INPUT_SHA or p.get('parent_items_sha256')!=PARENT_ITEMS_SHA):raise ValueError('sealed first300 parent/source scope required')
        if p.get('screen_candidates',600)not in (300,600):raise ValueError('registered screen census')
        if p.get('pair_measurement_rule_authority')!=AUTHORITY:raise ValueError('c33fcfb40 exact leading-space first-token rule required')
    return xs


def _capture_schema(xs):
    if any(set(x)!={'id','ids','read_index','candidate_ids'}or x['candidate_ids']!=[] for x in xs):raise ValueError('no answer-role transport')


def capture_batch(model,items):
    """Original E136 SAME capture-forward output observer; raw vocabulary only.

    Original E127 pair scorer is unchanged and receives no staged answer labels.
    The CPU owner resolves the registered X/Y axis without a first-token guess.
    """
    vocab=[]
    def scorer(z,xs):
        vocab.append(z.detach().float().cpu().numpy().copy())
        return old136.pairs_from_logits(z,xs)
    run=FunctionType(old136.capture_batch.__code__,dict(old136.capture_batch.__globals__,validate_items=_capture_schema,pairs_from_logits=scorer))
    xs=[{k:x[k]for k in ('id','ids','read_index','candidate_ids')}for x in items]
    out=run(model,xs)
    if len(vocab)!=1:raise ValueError('exactly one original capture-pass vocabulary tensor')
    out['vocab_logits']=vocab[0]
    return out


class Writer:
    def __init__(self,out,stage,check,gpu):
        self.out=Path(out)
        if self.out.exists():raise FileExistsError('fresh attempt; no partial reuse')
        if not callable(check)or not gpu:raise ValueError('original operator creation-clock callback and actual GPU')
        self.out.mkdir(parents=True);self.stage=stage;self.check=check;self.gpu=gpu;self.start=time.monotonic();self.times=[];self.setup=[];self.index=[]
        write(self.out/'ONCE.json',dict(experiment='E140',stage=stage))
    def admit(self,n):return self.check(n,time.monotonic()-self.start,max(self.times,default=0.0))
    def finish(self,status):
        write(self.out/'INDEX.json',self.index);write(self.out/'TIMING.json',dict(batch_seconds=self.times,setup_seconds=self.setup,elapsed_seconds=time.monotonic()-self.start))
        write(self.out/'OUTPUT_SEAL.json',dict(experiment='E140',stage=self.stage,status=status,gpu_type=self.gpu,labels_on_pod=False,files={str(p.relative_to(self.out)):sha(p)for p in self.out.rglob('*')if p.is_file()}))
        return status


def screen(model,tok,items,out,check_work,*,gpu_type,batch=8):
    validate_items(items,'screen');w=Writer(out,'screen',check_work,gpu_type);(w.out/'jobs').mkdir();jobs=list(batches(items,batch))
    for j,ix in enumerate(jobs):
        if not w.admit(len(jobs)-j):return w.finish('NO_FIT')
        t=time.monotonic();records=generation_batch(model,tok,[items[i]for i in ix]);w.times.append(time.monotonic()-t)
        name=f'jobs/{j:06d}.json';write(w.out/name,records);w.index.extend(dict(id=x['id'],member=name,record=k)for k,x in enumerate(records))
    return w.finish('COMPLETE')


def main_job(runtime,items,out,check_work,*,gpu_type,batch=8):
    """I2 supplies SAME already-loaded screen model; no second subject loader."""
    if runtime.model is None:raise ValueError('SAME preloaded screen model required; no extra loader')
    model,tok,cm=runtime.subject()
    validate_items(items,'main');w=Writer(out,'main',check_work,gpu_type)
    for n in ['capture','oracle']:(w.out/n).mkdir()
    jobs=list(batches(items,batch));captures={};remaining=len(jobs)*4
    with cm:
        for j,ix in enumerate(jobs):
            if not w.admit(remaining):return w.finish('NO_FIT')
            xs=[items[i]for i in ix];t=time.monotonic();v=capture_batch(model,xs);w.times.append(time.monotonic()-t);remaining-=1
            np.save(w.out/f'capture/{j:06d}-vocab.npy',v['vocab_logits'],allow_pickle=False)
            for L,h in v['captures'].items():
                np.save(w.out/f'capture/{j:06d}-{L}.npy',h,allow_pickle=False)
                for x,z in zip(xs,h):captures[x['id'],L]=z.copy()
            w.index.extend(dict(id=x['id'],kind='capture',raw_vocab_logits=dict(member=f'capture/{j:06d}-vocab.npy',index=k),layers={str(L):dict(member=f'capture/{j:06d}-{L}.npy',index=k)for L in LAYERS})for k,x in enumerate(xs))
    if not w.admit(remaining+1):return w.finish('NO_FIT')
    runtime.model=runtime.tok=None;del model,tok
    t=time.monotonic();runtime.load_oracle();w.setup.append(time.monotonic()-t)
    for L in LAYERS:
        for j,ix in enumerate(jobs):
            if not w.admit(remaining):return w.finish('NO_FIT')
            xs=[items[i]for i in ix];h=np.stack([captures[x['id'],L]for x in xs]);t=time.monotonic();records=oracle_batch(runtime,h,L);w.times.append(time.monotonic()-t);remaining-=1
            name=f'oracle/{L}-{j:06d}.json';write(w.out/name,records);w.index.extend(dict(id=x['id'],kind='oracle',block=L,member=name,record=k)for k,x in enumerate(xs))
    return w.finish('COMPLETE')


def source_gate():
    root=Path(__file__).resolve().parents[3]
    for n,h in read(Path(__file__).with_name('SOURCE_SEAL.json'))['files'].items():
        if sha(root/n)!=h:raise ValueError('changed E140 source '+n)


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--input-sha',required=True);p.add_argument('--stage',choices=['screen','main'],required=True);p.add_argument('--validate-only',action='store_true');a=p.parse_args()
    source_gate();xs=load(a.input,a.input_sha,a.stage)
    if a.validate_only:print('E140 VALIDATE_OK',a.stage,len(xs),'no weights loaded');return
    raise SystemExit('I2 registered whole-work creationclock/once/custody only; no standalone production')
if __name__=='__main__':main()
