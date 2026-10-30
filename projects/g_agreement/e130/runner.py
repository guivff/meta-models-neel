"""E130 acquisition only: label-free exp24 rebuilds, no probes or E125 space check."""
import json,random,time
from pathlib import Path
from unittest.mock import patch
import numpy as np
from projects.g_agreement.e100.contract import read,write,sha,verify
from .protocol import token_rows
from .gates import e130_admit
AR_REV='c95215d5d2f6250f20c305ae55c6e4d7569f92dc'
BASE_REV='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'


def source_gate():
    here=Path(__file__).resolve().parent
    seal=read(here/'SOURCE_SEAL.json')
    for name,digest in seal['files'].items():
        if sha(here/name)!=digest:raise ValueError('changed E130 source '+name)


def resolve_snapshot(root,revision,ar=False):
    p=Path(root).resolve()
    if p.name!=revision or not p.is_dir():raise ValueError('explicit local pinned revision snapshot required')
    required=['ar_ptag_pooled/'+n for n in ('heads.pt','meta.json','lora/adapter_model.safetensors','lora/adapter_config.json')] if ar else ['config.json','tokenizer.json']
    if any(not(p/n).is_file()for n in required)or not ar and not any(p.glob('*.safetensors')):
        raise ValueError('incomplete local snapshot')
    return p


def load_model(base,ar,device):
    """Only project-owned port executes; local pinned snapshots, no remote fallback."""
    from . import olens_ar
    import torch
    torch.manual_seed(0)
    old=olens_ar.BASE;olens_ar.BASE=str(base)
    def local_only(repo,**kwargs):
        if repo!='agu18dec/olens_and_ar':raise ValueError('unexpected remote asset request')
        return str(ar)
    try:
        with patch('huggingface_hub.snapshot_download',side_effect=local_only):
            model=olens_ar.OLensAR(device=device)
    finally:olens_ar.BASE=old
    model.variant=('li','ln')
    return model


def acquire(model,dev,test,out,check_work,*,gpu_type,batch=16):
    """Operator callback owns whole-need forecast/deadline; no trigger or budget inference."""
    out=Path(out)
    if out.exists():raise FileExistsError('fresh E130 attempt folder required')
    if batch!=16 or not isinstance(gpu_type,str) or not gpu_type:raise ValueError('exp24 batch16 and recorded GPU type')
    rows=token_rows(dev,test,lambda t:model.tok.encode(t,add_special_tokens=False))
    if not rows or len({(x['id'],x['condition'])for x in rows})!=len(rows):raise ValueError('unique condition/id rows')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    write(out/'ONCE.json',dict(experiment='E130',rows=len(rows),labels_read=False))
    write(out/'TOKEN_ROWS.json',rows)
    jobs=[]
    for condition in ('span_32','ol_readout','ol_readout_shuffled'):
        indices=[i for i,x in enumerate(rows)if x['condition']==condition]
        jobs.extend(indices[j:j+batch]for j in range(0,len(indices),batch))
    started=time.monotonic();durations=[];index=[];status='COMPLETE'
    for job in jobs:
        if not check_work(len(jobs)-len(durations),time.monotonic()-started,max(durations,default=0.0)):
            status='NO_FIT';break
        t=time.monotonic()
        values=model.reconstruct([rows[i]['ids']for i in job],44,variant=('li','ln'),batch=16)
        if hasattr(values,'numpy'):values=values.numpy()
        values=np.asarray(values)
        if values.shape!=(len(job),5120)or values.dtype!=np.float32 or not np.isfinite(values).all():
            raise ValueError('finite native fp32 reconstructor output')
        name=f'rebuild-{len(durations):04d}.npy';np.save(out/name,values,allow_pickle=False)
        durations.append(time.monotonic()-t)
        index.extend(dict(id=rows[i]['id'],split=rows[i]['split'],condition=rows[i]['condition'],file=name,index=k,gpu_type=gpu_type)for k,i in enumerate(job))
        write(out/'INDEX.json',index)
    write(out/'TIMING.json',dict(batch_seconds=durations,elapsed_seconds=time.monotonic()-started))
    write(out/'OUTPUT_SEAL.json',dict(experiment='E130',status=status,labels_included=False,probe_fit=False,probe_score=False,
          alignment_fit=False,whitening_applied=False,tag=44,variant=['li','ln'],seed=20261031,
          files={p.name:sha(p)for p in out.iterdir()if p.is_file()}))
    return status


def main():
    import argparse
    from datetime import datetime,timezone
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--input-sha',required=True)
    p.add_argument('--admission',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--base-snapshot',required=True);p.add_argument('--ar-snapshot',required=True);p.add_argument('--device',default='cuda')
    # Admission/forecast is supplied by the existing sole TrackQ controller, not recreated here.
    p.add_argument('--validate-only',action='store_true');args=p.parse_args()
    seal=verify(args.input,'INPUT_SEAL.json',args.input_sha)
    e130_admit(read(args.admission),args.input_sha,seal['sealed_at_utc'],datetime.now(timezone.utc))
    base=resolve_snapshot(args.base_snapshot,BASE_REV);ar=resolve_snapshot(args.ar_snapshot,AR_REV,ar=True)
    if args.validate_only:print('E130 INPUT/CONDITIONAL/LOCAL_ASSET admission PASS; no model loaded');return
    raise SystemExit('Use runner.acquire with the existing TrackQ measured whole-need clock callback; standalone unguarded production is disabled')



def prepare(input_root,input_sha,admission,now):
    """Gate before parsing readout content; original packet roster is immutable."""
    source_gate()
    root=Path(input_root);seal=verify(root,'INPUT_SEAL.json',input_sha)
    e130_admit(admission,input_sha,seal['sealed_at_utc'],now)
    dev=read(root/'DEV_SPANS.json');test=read(root/'READOUTS.json');order=read(root/'TEST_ORDER.json')
    if len(dev)!=200 or len(test)!=400 or len(order)!=400 or len(set(order))!=400 or [x['id']for x in test]!=order:
        raise ValueError('original sealed E85 dev200/test400/order')
    if any(set(x)!={'id','ids'}or len(x['ids'])!=32 or any(type(t)is not int or t<0 for t in x['ids'])for x in dev):
        raise ValueError('exact label-free true32 token spans')
    if any(set(x)!={'id','text'}or not isinstance(x['text'],str)for x in test):raise ValueError('original label-free readout text records')
    return dev,test

if __name__=='__main__':main()
