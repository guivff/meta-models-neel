"""CPU probe/class means from capture-only pull, before reader authorization."""
import argparse
from pathlib import Path
import numpy as np
from runtime62 import *
from cpu_capture import compute

def main():
 p=argparse.ArgumentParser()
 for k in ('capture','receipt','private-items','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--private-sha256',required=True);a=p.parse_args()
 r=read(a.receipt);require(r['verified'] is True and r['experiment']=='E62','verified E62 capture receipt');s=verify(a.capture,'CAPTURE_SEAL.json',r['capture_seal_sha256'])
 require(s['source_seal_sha256']==sha(HERE/'SOURCE_SEAL.json'),'source identity');verify(HERE,'SOURCE_SEAL.json')
 for path,digest in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/path)==digest,'CPU dependencies')
 require(sha(a.private_items)==a.private_sha256,'sealed private labels');lookup={x['id']:x for x in read(a.private_items)};order=read(a.capture/'items.order.json');items=[lookup[k] for k in order]
 allowed={x['feature'] for x in items if x['state']!='S6'};h=np.load(a.capture/'acts44.npy');require(h.shape==(len(items),5120),'readpoint matrix')
 scores,means=compute(items,h,allowed);a.out.mkdir(parents=True,exist_ok=False);dump(a.out/'PROBE.json',scores);np.savez(a.out/'CLASS_MEANS.npz',**means)
 seal(a.out,'CPU_SEAL.json',{'experiment':'E62','capture_seal_sha256':sha(a.capture/'CAPTURE_SEAL.json'),'private_items_sha256':a.private_sha256,'device':'cpu','probe_fit_split':'dev','means':['dev','test'],'S6':'no A/B; excluded'})
if __name__=='__main__':main()
