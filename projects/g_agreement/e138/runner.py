"""§250 envelope over original E100 transplant, E76 placebo and native E87."""
from pathlib import Path
import numpy as np
from projects.g_agreement.e100.contract import read,verify,sha
from projects.g_agreement.e100.interventions import transform
from results.g_agreement.understand.e76.common76 import norm_match
from results.g_agreement.understand.e100.vectors.math100 import pair_other
from projects.g_agreement.e136.dev2.runner import oracle_batch


INPUT_SHA='71e04529a3b76ea812f1bfafb4256cf8f22572f64af745de0c333e98b56ec01b'

def load(root,digest):
    if digest!=INPUT_SHA:raise ValueError('exact E138 original84 sealed vector packet required')
    root=Path(root);s=verify(root,'INPUT_SEAL.json',digest)
    if s.get('experiment')!='E138'or s.get('labels_on_pod')is not False or set(s['files'])!={'items.json','vectors.npy','MANIFEST.json'}:
        raise ValueError('exact public vector-only E138 members')
    items=read(root/'items.json');m=read(root/'MANIFEST.json');v=np.load(root/'vectors.npy',allow_pickle=False)
    if len(items)!=168 or len({x['id']for x in items})!=168 or any(set(x)!={'id','vector_index'}for x in items)or [x['vector_index']for x in items]!=list(range(168)):
        raise ValueError('exact168 opaque original cells, no labels')
    if v.shape!=(168,5120)or v.dtype!=np.float32 or not np.isfinite(v).all()or not(np.linalg.norm(v.astype(np.float64),axis=1)>0).all():
        raise ValueError('unaltered finite nonzero168x5120 native vectors')
    if m.get('oracle_block')!=44 or m.get('readouts')!=168 or m.get('source_items')!=84 or m.get('labels_on_pod')is not False:
        raise ValueError('registered84x2 Oracle44 only')
    return items,v,m


def batches(items,size=8):
    if type(size)is not int or size<1:raise ValueError('positive batch size')
    for i in range(0,len(items),size):yield items[i:i+size]


def source_gate():
    root=Path(__file__).resolve().parents[3]
    for n,h in read(Path(__file__).with_name('SOURCE_SEAL.json'))['files'].items():
        if sha(root/n)!=h:raise ValueError('changed E138 source '+n)


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--input-sha',required=True);p.add_argument('--validate-only',action='store_true');a=p.parse_args()
    source_gate();items,_,_=load(a.input,a.input_sha)
    if a.validate_only:print('E138 VALIDATE_OK',len(items),'native_batches',len(list(batches(items))),'no model loaded');return
    raise SystemExit('I2 soleoperator/original1200s creation-clock/custody required; no standalone production')

if __name__=='__main__':main()
