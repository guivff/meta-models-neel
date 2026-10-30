"""Registered E79 dev-probe manipulation check, scoped to added states only."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,subprocess,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
ROWS=('user_expertise','unit_system')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
def run(plan_path,out):
    plan_path=Path(plan_path).resolve();out=Path(out);p=json.loads(plan_path.read_text())
    if subprocess.check_output(['git','show','HEAD:'+str(plan_path.relative_to(ROOT))],cwd=ROOT)!=plan_path.read_bytes():raise ValueError('Commit manipulation plan before compute')
    if sha(__file__)!=p['source_sha256']:raise ValueError('Frozen manipulation source')
    for path,digest in p['inputs'].items():
        if sha(path)!=digest:raise ValueError('Input hash '+path)
    spec=json.loads(Path(p['spec']).read_text());meta=json.loads(Path(spec['metadata']).read_text());order=json.loads(Path(spec['order']).read_text());ix={ident:i for i,ident in enumerate(order)};h=np.load(spec['acts44'],mmap_mode='r',allow_pickle=False)
    key=json.loads(Path(p['private_map']).read_text());items=json.loads(Path(p['items']).read_text());vectors=np.load(p['vectors'],mmap_mode='r',allow_pickle=False);index={x['id']:x['index']for x in items}
    if len(key)!=2688 or len(index)!=2688 or set(index)!={x['id']for x in key}:raise ValueError('Exact added-state join')
    out.mkdir(parents=True,exist_ok=False) # Exclusive, never reset/retry.
    sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
    import torch
    from mats.probes import fit_logreg
    torch.set_num_threads(1);torch.manual_seed(20261026);results={}
    for row in sorted(ROWS):
        dev=[x for x in meta if x['feature']==row and x['split']=='dev']
        if len(dev)!=84 or sum(x['label']for x in dev)!=42:raise ValueError('Exact84 balanced dev, no test fit')
        if any(x['label']!=int(x['value']==spec['values'][row][0])for x in dev):raise ValueError('Probe/target orientation')
        model=fit_logreg(torch.from_numpy(np.array([h[ix[x['id']]]for x in dev])),torch.tensor([x['label']for x in dev]))
        selected=[x for x in key if x['row']==row];values=model.decision(torch.from_numpy(vectors[[index[x['id']]for x in selected]].copy())).detach().numpy();scores={x['id']:float(v)for x,v in zip(selected,values)}
        baseline={x['source_item_id']:scores[x['id']]for x in selected if x['condition']=='baseline'};cells={}
        for x in selected:
            if x['condition']=='baseline':continue
            delta=(scores[x['id']]-baseline[x['source_item_id']])*(1 if x['target_label']==1 else -1)
            cells.setdefault(x['condition']+':'+str(x['alpha']),[]).append(delta)
        results[row]={cell:dict(n=len(v),minimum=float(np.min(v)),mean=float(np.mean(v)),positive=sum(x>0 for x in v),all_toward_target=all(x>0 for x in v))for cell,v in cells.items()}
    target=out/'MANIPULATION.json';write(target,dict(experiment='E79_extension',fit_split='dev',rows=results,random_control_reported_without_filtering=True,exclusions_applied=False,main_R_C1_R_C2_recomputed=False))
    write(out/'MANIPULATION_SEAL.json',dict(experiment='E79_extension',plan_sha256=sha(plan_path),input_seal_sha256=p['owner_input_sha256'],private_join_sha256=p['inputs'][p['private_map']],reader_outputs_opened=False,GPU_hours=0,first_output_utc=datetime.fromtimestamp(target.stat().st_mtime,timezone.utc).isoformat(),first_output_evidence=dict(source='local_file_mtime',path='MANIPULATION.json',mtime_ns=target.stat().st_mtime_ns,scope='registered dev-probe manipulation analysis'),files={'MANIPULATION.json':sha(target)}))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--plan',type=Path,required=True);parser.add_argument('--out',type=Path,required=True);a=parser.parse_args();run(a.plan,a.out)
