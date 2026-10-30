"""E63 append-only existing-pod stage. One greedy call per vector, no row loop."""
import argparse,json,sys,time,threading,os,signal
from pathlib import Path
import numpy as np
from prepare63 import HERE
from contract56 import ROOT,read,dump,verify,sha,seal,require
from worker56 import Backend


def native_one(backend,reader,h):
    if reader=='nla':
        from native_nla512 import native_nla
        return native_nla(backend.nla,h,k=1,batch=8)
    import torch
    from mats.readers.nla import Sampling,extract_explanation
    # Raw Gaussian and real vectors receive no carrier, centering, scaling or normalization here.
    acts=torch.from_numpy(np.array(h,copy=True));sampling=Sampling(temperature=0,top_p=1.,top_k=0,max_new_tokens=128)
    with torch.no_grad():raw=backend.oracle.verbalize(acts,44,k=1,sampling=sampling,batch=8)
    require(len(raw)==len(h) and all(len(x)==1 for x in raw),'one native output')
    return [[{'raw':x,'text':x} for x in group] for group in raw]


def run(inp,backend,out,end):
    pools={'random':np.load(inp/'random.npy'),'shuffled42':np.load(inp/'shuffled42.npy'),'shuffled44':np.load(inp/'shuffled44.npy')}
    require(all(h.shape==(200,5120) and h.dtype==np.float32 and np.isfinite(h).all() for h in pools.values()),'fixed pool matrix')
    before={k:v.tobytes() for k,v in pools.items()};timing={}
    def call(phase,fn,left=0):
        require(time.time()<end-60,'E63 retrieval reserve');start=time.monotonic();v=fn();timing[phase]=max(time.monotonic()-start,timing.get(phase,0));require(time.time()+1.5*timing[phase]*left<end-60,'E63 NO_FIT '+phase);return v
    for reader in ('oracle','nla'):
        call(reader+'_setup',backend.load_oracle if reader=='oracle' else backend.load_nla)
        with (out/(reader+'.jsonl')).open('x') as stream:
            for arm in ('random','shuffled'):
                h=pools['random' if arm=='random' else ('shuffled44' if reader=='oracle' else 'shuffled42')]
                for start in range(0,200,8):
                    outputs=call(reader+'_native',lambda:native_one(backend,reader,h[start:start+8]),(200-start-8)//8)
                    for offset,group in enumerate(outputs):
                        for repeat,value in enumerate(group):stream.write(json.dumps(dict(pool=arm,vector_id=f'{arm}:{start+offset:03d}',reader=reader,layer=44 if reader=='oracle' else 42,repeat=repeat,**value),allow_nan=False)+'\n')
    require(all(v.tobytes()==before[k] for k,v in pools.items()),'native adapters changed input pool')
    from native_nla512 import truncation_summary
    dump(out/'NLA_TRUNCATION.json',truncation_summary([json.loads(line) for line in (out/'nla.jsonl').read_text().splitlines()],row_key='pool'))
    dump(out/'TIMING.json',{'completed_epoch':time.time(),'deadline_epoch':end,'phase_max_seconds':timing})


def main():
    p=argparse.ArgumentParser()
    for name in ('inputs','assets','assignment','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();assignment=read(a.assignment)
    require(assignment['existing_pod'] is True and assignment['gpu_count']==1 and assignment['cap_seconds']==1440,'existing single-GPU pod stage cap')
    start=time.time();end=min(start+1440,assignment['absolute_deadline_epoch']);require(start<end-60,'remaining custody')
    verify(HERE,'SOURCE_SEAL.json',assignment['source_seal_sha256']);verify(a.inputs,'INPUT_SEAL.json',assignment['input_seal_sha256'])
    for path,digest in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/path)==digest,'dependency pin')
    a.out.mkdir(parents=True,exist_ok=False);dump(a.out/'ASSIGNMENT.json',dict(assignment,stage_started_epoch=start));timer=threading.Timer(end-time.time(),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
    try:
        run(a.inputs,Backend(ROOT,a.assets,{'gpu_type':'H200'}),a.out,end)
        seal(a.out,'OUTPUT_SEAL.json',{'experiment':'E63','pod_id':assignment['pod_id'],'source_seal_sha256':assignment['source_seal_sha256'],'input_seal_sha256':assignment['input_seal_sha256'],'status':'COMPLETE'})
    except BaseException as error:dump(a.out/'FAILURE.json',{'error':str(error)});raise
    finally:timer.cancel()
if __name__=='__main__':main()
