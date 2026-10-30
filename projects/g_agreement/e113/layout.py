"""Lossless CPU-only dev/test separation; no probe or outcome computation."""
import argparse
from pathlib import Path
import numpy as np
from projects.g_agreement.e101.contract import read,write,sha,verify


def export(source,digest,out):
    seal=verify(source,'OUTPUT_SEAL.json',digest)
    if seal['experiment']!='E113' or seal['status']!='COMPLETE':raise ValueError('complete original capture required')
    index=read(source/'INDEX.json');cache={};groups={}
    if len({x['id'] for x in index})!=len(index):raise ValueError('unique original IDs')
    for x in index:groups.setdefault((x['row'],x['split']),[]).append(x)
    out.mkdir(parents=True,exist_ok=False);order={};checks=0
    for (row,split),xs in groups.items():
        first=xs[0]
        if first['member'] not in cache:cache[first['member']]=np.load(source/first['member'],allow_pickle=False,mmap_mode='r')
        shape=cache[first['member']].shape[1:]
        target=np.lib.format.open_memmap(out/f'{row}_{split}.npy',mode='w+',dtype=np.float32,shape=(len(xs),*shape))
        for i,x in enumerate(xs):
            if x['member'] not in cache:cache[x['member']]=np.load(source/x['member'],allow_pickle=False,mmap_mode='r')
            original=cache[x['member']][x['vector_index_in_file']]
            target[i]=original
            if target[i].tobytes()!=original.tobytes():raise ValueError('lossless state copy')
            checks+=1
        target.flush();order[f'{row}:{split}']=xs
    write(out/'ORDER.json',order)
    write(out/'LAYOUT_SEAL.json',dict(experiment='E113',status='LOSSLESS_DEV_TEST_LAYOUT',source_output_sha256=digest,
       bit_identical_items=checks,scientific_values_transformed=False,probe_fits=0,
       files={p.name:sha(p) for p in out.iterdir()}))
    return sha(out/'LAYOUT_SEAL.json')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--sha',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(export(a.source,a.sha,a.out))
