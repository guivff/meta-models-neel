"""§245 bAbI-only envelope; all acquisition arithmetic is original E133 v3."""
from pathlib import Path
from projects.g_agreement.e133 import runner as v3
from projects.g_agreement.e100.contract import read,sha

# Literal existing functions, not ports or modified hook/generation code.
generation_batch=v3.generation_batch
capture_batch=v3.capture_batch
patch_batch=v3.patch_batch
batches=v3.batches
CAPTURE=v3.CAPTURE
READ=v3.READ
PATCH=v3.PATCH


def main_disposition(qualifying_pairs):
    if type(qualifying_pairs)is not int or not 0<=qualifying_pairs<=494:
        raise ValueError('qualifying count from original494 candidate pairs')
    return dict(qualifying_pairs=qualifying_pairs,kept_pairs=min(42,qualifying_pairs),
                action='SCREEN_RESULTS_ONLY'if qualifying_pairs<20 else 'MAIN',
                selection='first42 both-member-correct pairs in original source order; no refill')


def validate_babi(items,stage):
    counts=v3.validate_items(items,stage)
    if set(x['family']for x in items)!={'babi'}:
        raise ValueError('E133b accepts bAbI only; no synthetic arm')
    for x in items:
        p=x['candidate_ids']
        if len(p)!=1 or p[0][0][0]>=p[0][1][0]:
            raise ValueError('original one ascending unordered recipient contrast only')
    count=counts['babi']
    if stage=='screen'and count!=494:
        raise ValueError('complete unchanged494pair screen, no partial reuse')
    if stage=='main'and main_disposition(count)['action']!='MAIN':
        raise ValueError('fewer20 qualifying pairs: screen results only, no main')
    return count


def load(root,digest,stage):
    items=v3.load(root,digest,stage)
    validate_babi(items,stage)
    return items


def screen(model,tok,items,out,check_work,*,gpu_type,batch=8):
    validate_babi(items,'screen')
    return v3.screen(model,tok,items,out,check_work,gpu_type=gpu_type,batch=batch)


def main_job(runtime,items,out,check_work,*,gpu_type,batch=8):
    validate_babi(items,'main')
    return v3.main_job(runtime,items,out,check_work,gpu_type=gpu_type,batch=batch)


def source_gate():
    root=Path(__file__).resolve().parents[3]
    seal=read(Path(__file__).with_name('SOURCE_SEAL.json'))
    for name,digest in seal['files'].items():
        if sha(root/name)!=digest:raise ValueError('changed E133b source '+name)
    v3.source_gate()


def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--input-sha',required=True)
    p.add_argument('--stage',choices=['screen','main'],required=True)
    p.add_argument('--validate-only',action='store_true')
    a=p.parse_args();source_gate();items=load(a.input,a.input_sha,a.stage)
    if a.validate_only:
        print('E133b VALIDATE_OK',a.stage,len(items),'no model loaded');return
    raise SystemExit('Use screen/main_job inside TrackQ original creation clock/custody; no standalone production')

if __name__=='__main__':main()
