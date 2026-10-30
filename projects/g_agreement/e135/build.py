"""CPU-only E135 dose list: registered scaling of sealed E104 alpha8 U deltas."""
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
    for alpha in (6,):
        for x in original:
            ident=f'E135-{bases[x["base_id"]]:04d}:{alpha}:{x["condition"]}';j=len(items)
            items.append(dict(id=ident,base_id=f'E135-{bases[x["base_id"]]:04d}',row='fact_recall',alpha=alpha,condition=x['condition'],ids=x['ids'],read_index=x['read_index'],candidate_ids=x['candidate_ids'],delta_index=j))
            vectors.append((raw[x['delta_index']]*(alpha/8)).astype(np.float32))
            pointers.append(dict(id=ident,original_base_id=x['base_id'],original_item_id=x['id'],original_delta_index=x['delta_index'],scale=alpha/8))
    np.save(p/'deltas.npy',np.stack(vectors),allow_pickle=False);write(p/'items.json',items);write(p/'SCORER.json',read(parent/'SCORER.json'))
    write(p/'MANIFEST.json',dict(experiment='E135',authority='§244 deviation1/026eea061',items=84,cells=168,doses=[6],conditions=['steered','random'],oracle_layers=[44,52],steered_readouts=168,random_readouts=168,total_readouts=336,greedy_answer_tokens=3,write_block=40,positions='eight_before_read',parent_input_sha256=sha(parent/'INPUT_SEAL.json'),parent_alpha=8,delta_policy='original signed composed alpha8 deltas scaled by6/8; random direction/seed preserved, no new fit/draw',seed=20261029))
    write(p/'INPUT_SEAL.json',dict(experiment='E135',labels_on_pod=False,files={x.name:sha(x)for x in p.iterdir()}));write(cpu/'ORIGINAL_POINTERS.PRIVATE.json',pointers);write(cpu/'POINTER_SEAL.json',dict(experiment='E135',input_sha256=sha(p/'INPUT_SEAL.json'),files={'ORIGINAL_POINTERS.PRIVATE.json':sha(cpu/'ORIGINAL_POINTERS.PRIVATE.json')}))
    with tarfile.open(out/'inputs.tar.gz','w:gz',compresslevel=1)as t:
        for x in p.iterdir():t.add(x,arcname=x.name)
    r=dict(experiment='E135',public_root=str(p),input_sha256=sha(p/'INPUT_SEAL.json'),archive=str(out/'inputs.tar.gz'),archive_sha256=sha(out/'inputs.tar.gz'),cpu_only=dict(root=str(cpu),seal_sha256=sha(cpu/'POINTER_SEAL.json'),stage_to_pod=False),parent_root=str(parent),parent_input_sha256=sha(parent/'INPUT_SEAL.json'),items=84,cells=168,steered_readouts=168,random_readouts=168,total_readouts=336,labels_on_pod=False,GPU_calls=0)

    for f in cpu.iterdir():f.chmod(0o600)
    write(ROOT/'results/g_agreement/understand/e135/INPUT_BINDING.json',r);return r
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.out),indent=2))
