"""CPU-only copy binding from original sealed E104/E127/E128 inputs; no selection."""
import json,tarfile
from pathlib import Path
import numpy as np
from projects.g_agreement.e100.contract import read,write,sha,verify
from projects.g_agreement.e127.inputs import load as load127
from projects.g_agreement.e128.inputs import load as load128
from .runner import load
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT.parent

def key(x):return json.dumps([x['ids'],x['read_index'],x['candidate_ids']],separators=(',',':'))


def build(out):
    e104=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r_ops/e104U_test_bind/fact_recall')
    e127=BASE/'outputs/e127-inputs-v2/inputs';e128=BASE/'outputs/e128-inputs-v1/inputs'
    hashes=['1e91a33f801d1eff72641fee56fa718957c65f57a7667fea5b5145a8db77b04a','964b5fc3f7e9e638496b987207cb8eb2ea6af7c54018b764c35452ea5b8462dd','7e911f6591fb229474b132361b6e67f1696634d0001a3dd4e57823e87194b224']
    verify(e104,'INPUT_SEAL.json',hashes[0]);p104=read(e104/'items.json');d104=np.load(e104/'deltas.npy',allow_pickle=False)
    p127,_=load127(e127,hashes[1]);p128,d128,_=load128(e128,hashes[2])
    natural=[x for x in p127 if x['condition']=='none'];assert len(natural)==84
    by={key(x):f'E131-{i:04d}'for i,x in enumerate(natural)};assert len(by)==84
    base127={x['base_id']:by[key(x)]for x in natural}
    out=Path(out);out.mkdir(exist_ok=False);pub=out/'inputs';pub.mkdir();cpu=out/'cpu_only';cpu.mkdir();items=[];deltas=[];pointers=[]
    def add(x,base,condition,source,delta=None):
        ix=None
        if delta is not None:ix=len(deltas);deltas.append(np.array(delta,dtype=np.float32,copy=True))
        ident=base+':'+condition
        items.append(dict(id=ident,base_id=base,condition=condition,ids=x['ids'],read_index=x['read_index'],candidate_ids=x['candidate_ids'],delta_index=ix))
        pointers.append(dict(id=ident,source=source,source_id=x['id'],source_base_id=x['base_id']))
    assert len(p104)==168 and {x['alpha']for x in p104}=={8.0}
    for x in p104:
        assert x['condition']in ('steered','random');base=by[key(x)]
        add(x,base,'e104_'+x['condition']+'_8','E104',d104[x['delta_index']])
        if x['condition']=='steered':add(x,base,'unhooked','E104')
    for x in p128:add(x,by[key(x)],'e128_'+x['condition']+'_'+str(x['alpha']),'E128',d128[x['delta_index']])
    for x in p127:add(x,base127[x['base_id']],x['condition'],'E127')
    write(pub/'items.json',items);np.save(pub/'deltas.npy',np.stack(deltas),allow_pickle=False)
    sources=[dict(experiment=e,root=str(p),input_sha256=h)for e,p,h in zip(('E104','E127','E128'),(e104,e127,e128),hashes)]
    write(pub/'MANIFEST.json',dict(experiment='E131',authority='§239/19763a3d1',items=84,cells=840,max_new_tokens=64,temperature=0,reader_calls=0,judging_calls=0,write_block=40,write_positions='eight original positions before read; read/generated tokens never patched',delta_policy='sealed composed deltas copied byte-identical; alpha already included; no redraw/refit/rescale',pair_score='E104 ordered single-token pairs from first generation forward, full-vocabulary logsoftmax',source_inputs=sources,seed_inherited=20261029))
    write(pub/'INPUT_SEAL.json',dict(experiment='E131',labels_on_pod=False,files={p.name:sha(p)for p in pub.iterdir()}))
    write(cpu/'SOURCE_POINTERS.PRIVATE.json',pointers)
    labels=e127.parent/'cpu_only/LABELS.PRIVATE.json'
    write(cpu/'LABEL_SOURCE.json',dict(root=str(labels),sha256=sha(labels),e131_to_e127_base={v:k for k,v in base127.items()},labels_on_pod=False))
    write(cpu/'POINTER_SEAL.json',dict(experiment='E131',input_sha256=sha(pub/'INPUT_SEAL.json'),files={p.name:sha(p)for p in cpu.iterdir()}))
    load(pub,sha(pub/'INPUT_SEAL.json'))
    with tarfile.open(out/'inputs.tar.gz','w:gz',compresslevel=1)as tar:
        for p in sorted(pub.iterdir()):tar.add(p,arcname=p.name)
    result=dict(experiment='E131',input_root=str(pub),input_sha256=sha(pub/'INPUT_SEAL.json'),input_archive=str(out/'inputs.tar.gz'),input_archive_sha256=sha(out/'inputs.tar.gz'),CPU_only_root=str(cpu),CPU_only_seal_sha256=sha(cpu/'POINTER_SEAL.json'),sources=sources,items=84,cells=840,reader_calls=0,judging_calls=0,model_calls=0,labels_on_pod=False)
    write(ROOT/'results/g_agreement/understand/e131/INPUT_BINDING.json',result);return result
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.out),indent=2))
