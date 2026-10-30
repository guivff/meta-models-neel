"""Bounded three-item §204 B200 image smoke; operator must stop on failure."""
import argparse
import os,signal,threading,time
from pathlib import Path
import worker87 as W
from hardware204 import actual_gpu,smoke,smoke_provenance
from runtime import Runtime


def main():
    p=argparse.ArgumentParser()
    for n in ('inputs','assignment','assets','out'):p.add_argument('--'+n,type=Path,required=True)
    for n in ('source-sha','input-sha'):p.add_argument('--'+n,required=True)
    a=p.parse_args();W.verify(W.HERE,'SOURCE_SEAL.json',a.source_sha)
    for n,h in W.read(W.HERE/'DEPENDENCIES.json').items():W.require(W.sha(W.ROOT/n)==h,'dependency '+n)
    s=W.verify(a.inputs,'SMOKE_INPUT_SEAL.json',a.input_sha)
    W.require(set(s['files'])=={'items.json','REFERENCE_RECEIPT.json'} and
        {x.name for x in a.inputs.iterdir()}==set(s['files'])|{'SMOKE_INPUT_SEAL.json'},'strict public smoke package')
    ref=W.read(a.inputs/'REFERENCE_RECEIPT.json')
    W.require(ref['items_sha256']==W.sha(a.inputs/'items.json'),'CPU verified H200 reference item bytes')
    ass=W.read(a.assignment)
    W.require(ass['custody_start_epoch']==ass['pod_created_epoch'],'creation-based smoke custody')
    W.deadline(ass,dict(experiment=ass['experiment'],cap_seconds=1800,cumulative_cap_seconds=ass['prior_seconds']+1800,account_gate_USD=1500),time.time())
    ass['actual_gpu_name']=actual_gpu(ass);ass['source_seal_sha256']=a.source_sha
    W.require(ass['input_seal_sha256']==a.input_sha and ass['absolute_deadline_epoch']>time.time()+60,'assigned smoke custody')
    a.out.mkdir(parents=True,exist_ok=False);W.write(a.out/'ASSIGNMENT.json',ass)
    b=Runtime(a.assets) if ref['mode']=='text' else W.Backend87(a.assets);b.hardware_assignment=ass
    timer=threading.Timer(max(0,ass['absolute_deadline_epoch']-time.time()-60),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
    status='FAILED'
    try:
        smoke(W.read(a.inputs/'items.json'),ref,ass,b,a.out,W.sha(a.assets));status='PASS'
    finally:
        timer.cancel()
        W.seal(a.out,'SMOKE_OUTPUT_SEAL.json',status=status,gpu_type=ass['gpu_type'],pod_id=ass['pod_id'],
            source_seal_sha256=a.source_sha,input_seal_sha256=a.input_sha,**smoke_provenance(a.out))

if __name__=='__main__':main()
