"""CPU-only E128 dose list: exact binary scaling of sealed E104 alpha8 U deltas."""
import json,tarfile
from pathlib import Path
import numpy as np
from projects.g_agreement.e100.contract import read,write,sha,verify
ROOT=Path(__file__).resolve().parents[3]

def build(out):
    parent=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r_ops/e104U_test_bind/fact_recall')
    verify(parent,'INPUT_SEAL.json','1e91a33f801d1eff72641fee56fa718957c65f57a7667fea5b5145a8db77b04a')
    original=read(parent/'items.json');raw=np.load(parent/'deltas.npy',allow_pickle=False)
    if len(original)!=168 or {x['alpha']for x in original}!={8.0}:raise ValueError('original84testitems/steered+random/alpha8')
    out=Path(out);out.mkdir(exist_ok=False);p=out/'inputs';p.mkdir();cpu=out/'cpu_only';cpu.mkdir();items=[];vectors=[];pointers=[]
    bases={x['base_id']:i for i,x in enumerate([x for x in original if x['condition']=='steered'])};assert len(bases)==84
    for alpha in (2,4):
        for x in original:
            ident=f'E128-{bases[x["base_id"]]:04d}:{alpha}:{x["condition"]}';j=len(items)
            items.append(dict(id=ident,base_id=f'E128-{bases[x["base_id"]]:04d}',row='fact_recall',alpha=alpha,condition=x['condition'],ids=x['ids'],read_index=x['read_index'],candidate_ids=x['candidate_ids'],delta_index=j))
            vectors.append((raw[x['delta_index']]*(alpha/8)).astype(np.float32))
            pointers.append(dict(id=ident,original_base_id=x['base_id'],original_item_id=x['id'],original_delta_index=x['delta_index'],scale=alpha/8))
    np.save(p/'deltas.npy',np.stack(vectors),allow_pickle=False);write(p/'items.json',items);write(p/'SCORER.json',read(parent/'SCORER.json'))
    write(p/'MANIFEST.json',dict(experiment='E128',authority='§236/2ebe22138',items=84,cells=336,doses=[2,4],conditions=['steered','random'],oracle_layers=[44,52],steered_readouts=336,random_readouts=336,total_readouts=672,greedy_answer_tokens=3,write_block=40,positions='eight_before_read',parent_input_sha256=sha(parent/'INPUT_SEAL.json'),parent_alpha=8,delta_policy='original signed composed alpha8 deltas scaled exactly.25/.5; random direction/seed preserved, no new fit/draw',seed=20261029))
    write(p/'INPUT_SEAL.json',dict(experiment='E128',labels_on_pod=False,files={x.name:sha(x)for x in p.iterdir()}));write(cpu/'ORIGINAL_POINTERS.PRIVATE.json',pointers);write(cpu/'POINTER_SEAL.json',dict(experiment='E128',input_sha256=sha(p/'INPUT_SEAL.json'),files={'ORIGINAL_POINTERS.PRIVATE.json':sha(cpu/'ORIGINAL_POINTERS.PRIVATE.json')}))
    with tarfile.open(out/'inputs.tar.gz','w:gz',compresslevel=1)as t:
        for x in p.iterdir():t.add(x,arcname=x.name)
    r=dict(experiment='E128',public_root=str(p),input_sha256=sha(p/'INPUT_SEAL.json'),archive=str(out/'inputs.tar.gz'),archive_sha256=sha(out/'inputs.tar.gz'),cpu_only=dict(root=str(cpu),seal_sha256=sha(cpu/'POINTER_SEAL.json'),stage_to_pod=False),parent_root=str(parent),parent_input_sha256=sha(parent/'INPUT_SEAL.json'),items=84,cells=336,steered_readouts=336,random_readouts=336,total_readouts=672,labels_on_pod=False,GPU_calls=0)
    write(ROOT/'results/g_agreement/understand/e128/INPUT_BINDING.json',r);return r
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.out),indent=2))
