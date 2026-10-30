"""Four first-in-frozen-order dev activations; no test output or labels loaded."""
import argparse,json,tarfile
from pathlib import Path
import numpy as np
from projects.g_agreement.e100.contract import read,write,sha,verify,require
from .reader import contract

def build(source,source_sha,out):
    s=verify(source,'INPUT_SEAL.json',source_sha);require(s['experiment']=='E113' and s['labels_on_pod'] is False,'original sealed E113 input carriers')
    items=read(source/'items.json');h=np.load(source/'h44.npy',allow_pickle=False,mmap_mode='r');chosen=[];vectors=[]
    for row in contract()['smoke']['rows']:
        x=next(x for x in items if x['row']==row and x['split']=='dev')
        chosen.append(dict(id=x['id'],row=row,split='dev',source_layer=44,part='smoke',condition='unpatched',vector_index=len(vectors)))
        vectors.append(h[x['vector_index']].copy())
    out.mkdir(parents=True,exist_ok=False);public=out/'inputs';public.mkdir();write(public/'items.json',chosen);np.save(public/'H.npy',np.asarray(vectors,np.float32),allow_pickle=False)
    write(public/'MANIFEST.json',dict(experiment='E119',stage='smoke',selection=contract()['smoke']['selection'],source_input_sha256=source_sha,source_files=s['files'],labels_on_pod=False))
    write(public/'INPUT_SEAL.json',dict(experiment='E119',labels_on_pod=False,files={p.name:sha(p) for p in public.iterdir()}))
    arc=out/'inputs.tar.gz'
    with tarfile.open(arc,'w:gz',compresslevel=1) as t:
        for p in public.iterdir():t.add(p,arcname='inputs/'+p.name,recursive=False)
    receipt=dict(experiment='E119',stage='smoke',items=4,split='dev',public_root=str(public.resolve()),input_sha256=sha(public/'INPUT_SEAL.json'),archive=str(arc.resolve()),archive_sha256=sha(arc))
    write(out/'PACKAGE.json',receipt);return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--source-sha',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.source,a.source_sha,a.out),indent=2))
