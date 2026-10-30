"""Reuse exact selected-dose E104 U public cells; no new vectors or labels."""
import argparse,tarfile
from pathlib import Path
import numpy as np
from .contract109 import DOSES,CAPTURE,READ,SEED,DIRECTION_SHA,identity,validate,read,write,sha,verify
from .runner104 import load as load104


def build(parents,out,rows=None):
    rows=list(rows or DOSES);items=[];deltas=[];provenance=[];seen=set()
    for parent in parents:
        root=Path(parent['root']);verify(root,'INPUT_SEAL.json',parent['sha256'])
        xs,data=load104(root);m=data['manifest']
        present={x['row'] for x in xs};split=m['stage']
        if split not in ('dev','test') or m['provenance']['U_direction_seal_sha256']!=DIRECTION_SHA:raise ValueError('original dev/test sealed d40 parents')
        if any(x['arm']!='U' for x in xs):raise ValueError('only E104 U parents')
        for row in sorted(present & set(rows)):
            if (row,split) in seen:raise ValueError('duplicate parent row/split')
            seen.add((row,split));selected=[x for x in xs if x['row']==row and x['alpha']==DOSES[row]]
            if len(selected)!=168:raise ValueError('all 84 selected-dose steered/random items')
            for base in dict.fromkeys(x['base_id'] for x in selected):
                pair=[x for x in selected if x['base_id']==base]
                if len(pair)!=2 or {x['condition'] for x in pair}!={'steered','random'}:raise ValueError('frozen matched pair')
                original=pair[0]
                for condition in ('unhooked','steered','random'):
                    ix=None
                    if condition!='unhooked':
                        x=next(x for x in pair if x['condition']==condition)
                        if x['ids']!=original['ids']:raise ValueError('matched source prompt')
                        ix=len(deltas);deltas.append(data['deltas'][x['delta_index']].copy())
                    items.append(dict(id=identity(split,row,base,condition),base_id=base,row=row,split=split,
                      condition=condition,alpha=DOSES[row],ids=original['ids'],read_index=original['read_index'],delta_index=ix))
        provenance.append(dict(input_sha256=parent['sha256'],manifest_sha256=sha(root/'MANIFEST.json'),stage=split,rows=sorted(present),provenance=m['provenance'],dose_sha256=m.get('dose_sha256'),dose_commit=m.get('dose_commit')))
    if seen!={(r,s) for r in rows for s in ('dev','test')}:raise ValueError('both original dev/test parents for each row')
    d=np.asarray(deltas,np.float32);m=dict(experiment='E109',authority='2d470093a',seed=SEED,rows=rows,items_per_split_row=84,
      capture_blocks=list(CAPTURE),oracle_blocks=list(READ),direction_sha256=DIRECTION_SHA,write_block=40,
      write_positions='read-8..read-1',read_token_patched=False,provenance=provenance,
      oracle_conditions=['steered','random'],oracle_split='test',oracle_max_new_tokens=128)
    validate(items,d,m);out.mkdir(parents=True,exist_ok=False)
    write(out/'items.json',items);write(out/'MANIFEST.json',m);np.save(out/'deltas.npy',d,allow_pickle=False)
    write(out/'INPUT_SEAL.json',dict(experiment='E109',labels_on_pod=False,files={p.name:sha(p) for p in out.iterdir()}))
    archive=out.parent/(out.name+'.tar.gz')
    with tarfile.open(archive,'w:gz',compresslevel=1) as t:
        for p in out.iterdir():t.add(p,arcname='inputs/'+p.name,recursive=False)
    return dict(row_scope=rows,root=str(out),input_sha256=sha(out/'INPUT_SEAL.json'),archive=str(archive),archive_sha256=sha(archive),capture_cells=len(items),capture_vectors=len(items)*5,oracle_readouts=sum(x['split']=='test' and x['condition']!='unhooked' for x in items)*3)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--parents',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--row',choices=list(DOSES),action='append');a=p.parse_args();print(build(read(a.parents),a.out,a.row))
