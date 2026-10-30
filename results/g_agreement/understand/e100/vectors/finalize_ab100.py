"""Active E100 a/b package under 69f8c08e4; c/d preparation is CPU-only history."""
import argparse
import math
import shutil
import tarfile
from pathlib import Path
import numpy as np
from build100 import ROWS,sha,read,write,inputs,verified_members,opaque
from math100 import pair_other


def finalize(base,core,out):
    receipt=read(core/'CORE_RECEIPT.json')
    for n,h in receipt['files'].items():assert sha(core/n)==h,'core unchanged'
    data,old,qpath,prov=inputs(base);assert prov==read(core/'cpu_only/SOURCES.json')
    out.mkdir(parents=True,exist_ok=False);public=out/'public';public.mkdir();cpu=out/'cpu_only'
    shutil.copytree(core/'cpu_only',cpu);(cpu/'prepared_directions').mkdir()
    for name in ['Q_J.npy','Q_R.npy']:shutil.copyfile(core/'public'/name,public/name)
    (public/'pairings').mkdir();q=np.load(public/'Q_J.npy',allow_pickle=False)
    rows=read(cpu/'ROWS.json');joins=[];manifest=[];counts={}
    for ri,(bank,row) in enumerate(ROWS):
        shutil.copytree(core/'public'/row,cpu/'prepared_directions'/row)
        records,acts=data[bank];test=[x for x in records if x['feature']==row and x['split']=='test']
        assert len(test)==84 and sum(x['label'] for x in test)==42
        original=[x['id'] for x in test];ids=[opaque(bank,x) for x in original];labels=[x['label'] for x in test]
        donors=pair_other(ids,labels);folder=public/row;folder.mkdir()
        h44=np.stack([acts[x] for x in original]).astype(np.float32);other={};sources42=[]
        for cap in prov['banks'][bank]['captures']:
            cs=Path(cap['seal_path']);s=verified_members(cs,['acts42.npy','items.order.json'],cap['seal_sha256'])
            order=read(cs.parent/'items.order.json');h=np.load(cs.parent/'acts42.npy',mmap_mode='r',allow_pickle=False)
            for i,ident in enumerate(order):
                if ident in set(original):other[ident]=h[i].copy()
            sources42.append(dict(seal_sha256=sha(cs),acts42_sha256=s['files']['acts42.npy']))
        assert set(other)==set(original);h42=np.stack([other[x] for x in original])
        for layer,h in [(44,h44),(42,h42)]:
            assert h.shape==(84,5120) and np.isfinite(h).all();np.save(folder/f'h{layer}.npy',h,allow_pickle=False)
        pairs=[dict(id=ids[i],slot=i,donor_id=ids[j],donor_slot=j) for i,j in enumerate(donors)]
        assert all(labels[i]!=labels[j] for i,j in enumerate(donors))
        write(public/'pairings'/(row+'.json'),pairs)
        manifest.append(dict(row=row,group='missed' if ri<3 else 'reported',items=84,ids=ids,h44=row+'/h44.npy',h42=row+'/h42.npy',
            pairings='pairings/'+row+'.json',conditions=['transplant','J_swap','perp_J_swap','R_swap','perp_R_swap'],
            u_tok_status='WITHDRAWN_69f8c08e4',injection_status='WITHDRAWN_69f8c08e4',upstream_status='WITHDRAWN_69f8c08e4'))
        joins.extend(dict(id=ids[i],bank=bank,row=row,source_item_id=x['id'],true_label=x['label'],source_value=x['value'],
            donor_id=ids[donors[i]],donor_source_item_id=original[donors[i]],donor_label=labels[donors[i]],donor_value=test[donors[i]]['value'])
            for i,x in enumerate(test))
        d=np.load(cpu/(row+'_raw_d.npy'),allow_pickle=False)
        rows[ri].update(J_fraction=float(np.linalg.norm(q@(q.T@d))/np.linalg.norm(d)),random_rank_chance=math.sqrt(384/5120),
            test_count=84,capture42_sources=sources42)
        counts[row]=84*5*2
    write(cpu/'FINAL_ROWS.json',rows);write(cpu/'JOIN.DO_NOT_STAGE.json',joins)
    write(cpu/'PREPARATION_DISPOSITION.json',dict(authority='69f8c08e4',status='E100_C_D_WITHDRAWN',
        direction_arrays='prepared CPU-only before withdrawal; preserved, not launched',
        u_tok='No token-unembedding vectors manufactured after withdrawal; mapped strings/code retained as preparation history',
        manipulation_adapter='CPU-only dev-probe adapter preserved; injection cells withdrawn',
        not_E101_admission=True))
    write(public/'MANIFEST.json',dict(experiment='E100',authority=['f425a5e2','fd07c12a','69f8c08e4'],seed=20261028,
        rank=384,dimension=5120,Q_J='Q_J.npy',Q_R='Q_R.npy',projector='Q @ Q.T',basis_shape=[5120,384],rows=manifest,
        oracle_readouts=3360,nla_readouts=3360,total_readouts=6720,no_baselines=True,
        per_row_readouts=counts,parts=['a','b'],parts_c_d='WITHDRAWN_NOT_RUN',
        gate='R-PC gates scientific evaluation of b; integrator controls execution/release',NLA_status='exploratory; block42 with block44 basis'))
    write(public/'INPUT_SEAL.json',dict(experiment='E100',labels_on_pod=False,files={str(p.relative_to(public)):sha(p) for p in public.rglob('*') if p.is_file()}))
    write(out/'VECTOR_SEAL.json',dict(experiment='E100',authority=['f425a5e2','fd07c12a','69f8c08e4'],status='AB_SEALED_BEFORE_GPU_CD_WITHDRAWN',
        GPU_calls=0,reader_calls=0,CPU_only=['cpu_only'],public_input_seal_sha256=sha(public/'INPUT_SEAL.json'),
        core_receipt_sha256=sha(core/'CORE_RECEIPT.json'),files={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['base','core','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();finalize(a.base,a.core,a.out)
