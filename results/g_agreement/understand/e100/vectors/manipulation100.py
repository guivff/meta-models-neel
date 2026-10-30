"""CPU adapter for returned patched cells; no fitting, selection or reader scoring."""
import argparse
from pathlib import Path
import numpy as np
from build100 import read,write,sha
from math100 import manipulation


def run(package,metadata,patched,out):
    seal=read(package/'VECTOR_SEAL.json')
    if seal['status']=='AB_SEALED_BEFORE_GPU_CD_WITHDRAWN':
        raise ValueError('E100 injection arms withdrawn by69f8c08e4; adapter retained as CPU-only preparation, not an authorized E101 analysis')
    for n,h in seal['files'].items():assert sha(package/n)==h,'sealed vector/probe source changed'
    public=package/'public';manifest=read(public/'MANIFEST.json');rows={x['row']:x for x in manifest['rows']}
    joins={(x['row'],x['id']):x for x in read(package/'cpu_only/JOIN.DO_NOT_STAGE.json')}
    cells=read(metadata);values=np.load(patched,allow_pickle=False)
    assert values.shape==(len(cells),5120) and np.isfinite(values).all(),'aligned finite patched cells'
    expected={(r['row'],ident,d,a) for r in manifest['rows'] for ident in r['ids'] for d in r['delta_files'] for a in [.5,1.,2.,4.]}
    identities=[(x['row'],x['id'],x['direction'],x['alpha']) for x in cells]
    assert len(set(identities))==len(identities) and set(identities)==expected,'all registered new injection cells exactly once'
    output=[]
    for row,r in rows.items():
        h=np.load(public/r['h44'],allow_pickle=False);byid={i:j for j,i in enumerate(r['ids'])}
        probe=np.load(package/'cpu_only'/(row+'_probe.npz'),allow_pickle=False)
        ix=[i for i,c in enumerate(cells) if c['row']==row]
        stats=manipulation(h[[byid[cells[i]['id']] for i in ix]],values[ix],probe['w'],probe['sd'],
            [joins[row,cells[i]['id']]['target_label'] for i in ix])
        for j,i in enumerate(ix):output.append(dict(cells[i],probe_logit_shift=float(stats['probe_logit_shift'][j]),
            target_signed_probe_logit_shift=float(stats['target_signed_probe_logit_shift'][j]),norm_ratio=float(stats['norm_ratio'][j]),
            norm_ratio_above_1_5=bool(stats['norm_ratio_above_1_5'][j])))
    out.mkdir(parents=True,exist_ok=False)
    write(out/'MANIPULATION.json',dict(fit_split='dev_only_presealed',n=len(output),cells=output,exclusions_applied=False))
    write(out/'MANIPULATION_SEAL.json',dict(vector_seal_sha256=sha(package/'VECTOR_SEAL.json'),cell_metadata_sha256=sha(metadata),
        patched_vectors_sha256=sha(patched),files={'MANIPULATION.json':sha(out/'MANIPULATION.json')}))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['package','metadata','patched','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();run(a.package,a.metadata,a.patched,a.out)
