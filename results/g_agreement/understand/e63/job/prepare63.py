"""Freeze one paired-native-layer shared pool, uniformly over all five test banks."""
import argparse,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'e56/job'))
from contract56 import read,dump,verify,sha,seal,require
BANKS={'W1','E36','E56','E57','E59'}


def select_ids(records):
    require({x['bank'] for x in records}==BANKS,'all five registered banks required')
    eligible=sorted((x for x in records if x['split']=='test'),key=lambda x:(x['bank'],x['id']))
    require(len(eligible)>=200 and len({(x['bank'],x['id']) for x in eligible})==len(eligible),'unique test universe')
    rng=np.random.default_rng(20261028)
    return [eligible[int(i)] for i in rng.choice(len(eligible),200,replace=False)]


def gaussian_pool():return np.random.default_rng(20261027).standard_normal((200,5120)).astype(np.float32)


def prepare(manifest,out):
    # Integrator supplies complete capture manifests, not a hand-picked subset.
    sources=read(manifest);require(set(sources['banks'])==BANKS,'source bank universe');records=[];arrays={};source_pins={}
    for bank,source in sources['banks'].items():
        root=Path(source['root']);verify(root,source['seal_file'],source['seal_sha256']);metadata=read(root/source['items_file'])
        require(sha(root/source['items_file'])==source['items_sha256'],'metadata pin')
        require(all(isinstance(x['id'],str) and isinstance(x['row'],str) and x['split'] in ('dev','test') for x in metadata),'complete bank metadata')
        source_pins[bank]=source
        for layer in (42,44):
            path=root/source[f'acts{layer}_file'];require(sha(path)==source[f'acts{layer}_sha256'],'capture pin');arrays[bank,layer]=np.load(path,mmap_mode='r');require(arrays[bank,layer].shape==(len(metadata),5120),'native-layer capture shape')
        records.extend(dict(x,bank=bank,index=i) for i,x in enumerate(metadata))
    selected=select_ids(records);out.mkdir(parents=True,exist_ok=False)
    z=gaussian_pool();np.save(out/'random.npy',z)
    for layer in (42,44):
        vectors=np.array([arrays[x['bank'],layer][x['index']] for x in selected],dtype=np.float32);require(np.isfinite(vectors).all(),'finite real vectors');np.save(out/f'shuffled{layer}.npy',vectors)
    dump(out/'POOL_IDS.json',[{'pool_id':f'shuffled:{i:03d}',**x} for i,x in enumerate(selected)])
    dump(out/'SOURCE_BINDING.json',{'manifest_sha256':sha(manifest),'sources':source_pins,'random_seed':20261027,'shuffled_seed':20261028,'random_shared_across_native_layers':True,'sampling':'uniform test items without replacement over concatenated five-bank universe'})
    seal(out,'INPUT_SEAL.json',{'experiment':'E63','pools':2,'vectors_per_pool':200,'readouts_per_vector':4})
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--manifest',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();prepare(a.manifest,a.out)
