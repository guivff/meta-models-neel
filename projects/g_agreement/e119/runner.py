"""E119 requires a matching four-dev-item PASS before production is admissible."""
import argparse,os,time,signal,threading
from pathlib import Path
import numpy as np
from projects.g_agreement.e100.contract import ROOT,read,write,sha,verify,require
from projects.g_agreement.e100.worker import hardware
from . import reader

def inputs(root,input_sha,mode):
    s=verify(root,'INPUT_SEAL.json',input_sha);items=read(root/'items.json');h=np.load(root/'H.npy',allow_pickle=False)
    require(s['experiment']=='E119' and s['labels_on_pod'] is False and set(s['files'])=={'items.json','H.npy','MANIFEST.json'},'sealed public-only input')
    require(h.shape==(len(items),5120) and h.dtype==np.float32 and np.isfinite(h).all() and np.all(np.linalg.norm(h,axis=1)>0),'finite original vectors')
    require(len({x['id'] for x in items})==len(items),'unique public cells')
    allowed={'id','row','source_layer','part','condition','vector_index','split'}
    require(all(set(x)<=allowed and x['vector_index']==i for i,x in enumerate(items)),'public field allowlist/order')
    if mode=='smoke':
        require(len(items)==4 and {x['row'] for x in items}==set(reader.contract()['smoke']['rows']) and all(x['split']=='dev' and x['source_layer']==44 for x in items),'exact four dev smoke cells')
    else:
        require(len(items)==672 and all(x['split']=='test' for x in items),'registered672 test cells')
        for layer in (44,52):
            for condition in ('steered','random'):require(sum(x['part']=='a' and x['row']=='fact_recall' and x['source_layer']==layer and x['condition']==condition for x in items)==84,'part a exact source44/52 steered/random')
        for row in reader.contract()['smoke']['rows']:require(sum(x['part']=='b' and x['row']==row and x['source_layer']==44 and x['condition']=='transplant' for x in items)==84,'part b exact four transplants')
    return items,h

def production_gate(smoke,smoke_sha,source_sha):
    require(smoke is not None and smoke_sha is not None,'four-dev smoke PASS required before production')
    s=verify(smoke,'SMOKE_SEAL.json',smoke_sha)
    require(s['experiment']=='E119' and s['status']=='PASS' and s['items']==4 and s['split']=='dev','nondegenerate four-dev PASS')
    require(s['contract_sha256']==sha(reader.CONTRACT_PATH) and s['weights_sha256']==reader.contract()['checkpoint']['weights_sha256'] and s['source_sha256']==source_sha,'same frozen contract/weights/exact runner')

def main():
    p=argparse.ArgumentParser()
    for n in ('inputs','assignment','weights','base','source-seal','out'):p.add_argument('--'+n,type=Path,required=True)
    for n in ('source-sha','input-sha'):p.add_argument('--'+n,required=True)
    p.add_argument('--mode',choices=('smoke','production'),required=True);p.add_argument('--smoke',type=Path);p.add_argument('--smoke-sha');p.add_argument('--validate-only',action='store_true');a=p.parse_args()
    verify(ROOT,str(a.source_seal.resolve().relative_to(ROOT)),a.source_sha);items,h=inputs(a.inputs,a.input_sha,a.mode)
    if a.mode=='production':production_gate(a.smoke,a.smoke_sha,a.source_sha)
    require(sha(a.weights)==reader.contract()['checkpoint']['weights_sha256'],'pinned weight hash')
    if a.validate_only:return
    ass=read(a.assignment)
    require(ass['experiment']=='E119' and ass['mode']==a.mode and ass['pod_id']==os.environ.get('RUNPOD_POD_ID') and ass['gpu_type']=='H200' and ass['gpu_count']==1,'exact owner-assigned single H200')
    require(ass['source_sha256']==a.source_sha and ass['input_sha256']==a.input_sha and ass['base_revision']==reader.contract()['base']['revision'],'source/input/base revision')
    require(ass['allocation_verified'] is True and ass['daily_budget_verified'] is True and ass['priority_release_verified'] is True,'budget and registered priority release')
    require(0<ass['cap_seconds'] and ass['cap_seconds']*5.29/3600<=25 and ass['pod_created_epoch']<1793296800 and ass['absolute_deadline_epoch']==ass['pod_created_epoch']+ass['cap_seconds'],'fixed creation cap and19CET cutoff')
    gpu=hardware(ass);a.out.mkdir(parents=True,exist_ok=False);write(a.out/'ASSIGNMENT.json',ass);status='FAILED';timings=[];results=[]
    timer=threading.Timer(max(0,ass['absolute_deadline_epoch']-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
    try:
        start=time.monotonic();model,tok,audit=reader.load(a.base,a.weights);timings.append(dict(phase='load',seconds=time.monotonic()-start));write(a.out/'LOAD_AUDIT.json',audit)
        for first in range(0,len(items),4 if a.mode=='smoke' else 8):
            require(time.time()<ass['absolute_deadline_epoch']-60,'NO_FIT creation custody reserve')
            group=items[first:first+(4 if a.mode=='smoke' else 8)]
            # Mixed source layers are separate native carrier calls, no layer substitution.
            for layer in sorted({x['source_layer'] for x in group}):
                xs=[x for x in group if x['source_layer']==layer];start=time.monotonic()
                values=reader.read(model,tok,h[[x['vector_index'] for x in xs]],layer)
                results.extend(dict(v,id=x['id'],row=x['row'],part=x.get('part'),condition=x.get('condition'),gpu_type=gpu) for x,v in zip(xs,values))
                timings.append(dict(phase='read',source_layer=layer,items=len(xs),seconds=time.monotonic()-start));write(a.out/'READOUTS.json',results);write(a.out/'TIMINGS.json',timings)
            if a.mode=='production':
                need=1.25*(len(items)-len(results))*sum(x['seconds'] for x in timings if x['phase']=='read')/len(results)
                if time.time()+need>=ass['absolute_deadline_epoch']-60:status='NO_FIT';break
        else:status='PASS' if a.mode=='smoke' and all(reader.nondegenerate(v) for v in results) else ('NOT_RUN_OPERATIONAL_FAILED_SMOKE' if a.mode=='smoke' else 'COMPLETE')
    finally:
        timer.cancel();write(a.out/('SMOKE_SEAL.json' if a.mode=='smoke' else 'OUTPUT_SEAL.json'),dict(experiment='E119',status=status,items=len(results),split='dev' if a.mode=='smoke' else 'test',source_sha256=a.source_sha,input_sha256=a.input_sha,contract_sha256=sha(reader.CONTRACT_PATH),weights_sha256=reader.contract()['checkpoint']['weights_sha256'],files={str(p.relative_to(a.out)):sha(p) for p in a.out.rglob('*') if p.is_file()}))
if __name__=='__main__':main()
