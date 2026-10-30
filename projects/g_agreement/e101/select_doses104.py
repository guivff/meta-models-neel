"""CPU-only E104 dose freeze; no test materialization in this command."""
import argparse
from pathlib import Path
import numpy as np
from .contract104 import read,write,sha,verify,validate,select,validate_doses,SEED


def run(binding,key_path,key_sha,out,partial=False):
    if sha(key_path)!=key_sha:raise ValueError('CPU key identity')
    key=read(key_path);items=[];records=[];scorers=set()
    for shard in binding['shards']:
        inp=Path(shard['input_root']);res=Path(shard['output_root'])
        verify(inp,'INPUT_SEAL.json',shard['input_sha256']);seal=verify(res,'OUTPUT_SEAL.json',shard['output_sha256']);m=read(inp/'MANIFEST.json')
        if m['stage']!='dev' or seal['experiment']!='E104' or seal['status']!='COMPLETE' or seal['input_sha256']!=shard['input_sha256']:raise ValueError('complete bound dev acquisition')
        xs=read(inp/'items.json');validate(xs,np.load(inp/'deltas.npy',allow_pickle=False),m);scorers.add(m['behaviour_scorer_sha256'])
        jj=read(res/'JOB_GRID.json')
        if sorted(read(res/'COMPLETED.json'))!=list(range(len(jj))) or any(j['kind']!='logits' for j in jj):raise ValueError('complete dev logits grid only')
        rr=[]
        for i,j in enumerate(jj):
            rs=read(res/'jobs'/f'{i:06d}.json')
            if [r['id'] for r in rs]!=[xs[k]['id'] for k in j['indices']]:raise ValueError('exact dev job order')
            rr.extend(rs)
        items.extend(xs);records.extend(rr)
    if len(scorers)!=1:raise ValueError('one frozen scorer across all arms/rows')
    selected=select(items,records,key)
    if not partial:validate_doses(selected)
    out.mkdir(parents=True,exist_ok=False);name='E104_DOSES.PARTIAL.json' if partial else 'E104_DOSES.json'
    write(out/name,dict(experiment='E104',status='PARTIAL_NOT_FOR_TEST' if partial else 'FROZEN_PENDING_GIT_COMMIT',stage='DEV_ONLY',authority='5e075c6af',dev_count=84,seed=SEED,
        selected_doses=selected,behaviour_scorer_sha256=next(iter(scorers)),dose_score_field='pair_logits',shards=binding['shards'],cpu_key_sha256=key_sha,test_outputs_opened=False))
    write(out/'DOSE_SEAL.json',dict(experiment='E104',files={name:sha(out/name)},GPU_calls=0))
    # Stop. The Integrator commits the final complete receipt before test construction.

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('binding','cpu-key','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--cpu-key-sha',required=True);p.add_argument('--partial',action='store_true');a=p.parse_args();run(read(a.binding),a.cpu_key,a.cpu_key_sha,a.out,a.partial)
