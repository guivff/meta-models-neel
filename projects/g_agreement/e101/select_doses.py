"""CPU-only exact dev-logit join; write E101_DOSES.json before any test input exists."""
import argparse
from pathlib import Path
from .contract import read,write,sha,verify,validate,select,ROWS
import numpy as np


def run(binding,key_path,key_sha,out):
    if sha(key_path)!=key_sha:raise ValueError('CPU key identity')
    key=read(key_path);all_items=[];all_records=[];provenance=[];mode=None
    for shard in binding['shards']:
        inp=Path(shard['input_root']);res=Path(shard['output_root'])
        verify(inp,'INPUT_SEAL.json',shard['input_sha256'])
        seal=verify(res,'OUTPUT_SEAL.json',shard['output_sha256'])
        m=read(inp/'MANIFEST.json')
        if m['stage']!='dev' or m['dev_count']!=84 or m['dose_policy']!='independent_blocks' or not m['ruling_commit']:
            raise ValueError('clarification 1 dev ruling')
        if mode is None:mode=m['scoring_mode']
        if mode!=m['scoring_mode'] or seal['status']!='COMPLETE' or seal['stage']!='dev' or seal['input_sha256']!=shard['input_sha256']:raise ValueError('complete matching dev output')
        xs=read(inp/'items.json');validate(xs,np.load(inp/'vectors.npy',allow_pickle=False),'dev',84)
        jj=read(res/'JOB_GRID.json');done=read(res/'COMPLETED.json')
        if sorted(done)!=list(range(len(jj))) or any(j['kind']!='logits' for j in jj):raise ValueError('complete dev logits only')
        rr=[]
        for i,j in enumerate(jj):
            records=read(res/'jobs'/f'{i:06d}.json')
            if [r['id'] for r in records]!=[xs[k]['id'] for k in j['indices']]:raise ValueError('exact job order')
            rr.extend(records)
        all_items.extend(xs);all_records.extend(rr);provenance.append(dict(shard))
    doses=select(all_items,all_records,key,mode,84)
    if set(doses)!={f'{r}:{b}' for r in ROWS for b in (42,44)}:raise ValueError('all seven rows and both blocks required')
    out.mkdir(parents=True,exist_ok=False)
    write(out/'E101_DOSES.json',dict(experiment='E101',stage='DEV_ONLY',authority=['69f8c08e4','2bdde763'],
        status='FROZEN_PENDING_GIT_COMMIT',scoring_mode=mode,dose_policy='independent_blocks',dev_count=84,
        selected_doses=doses,shards=provenance,cpu_key_sha256=key_sha,test_outputs_opened=False))
    write(out/'DOSE_SEAL.json',dict(experiment='E101',files={'E101_DOSES.json':sha(out/'E101_DOSES.json')},GPU_calls=0))


def main():
    p=argparse.ArgumentParser()
    for n in ('binding','cpu-key','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--cpu-key-sha',required=True);a=p.parse_args();run(read(a.binding),a.cpu_key,a.cpu_key_sha,a.out)
if __name__=='__main__':main()
