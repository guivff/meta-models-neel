"""CPU-only original family/value targets for the once-only E101 adapter."""
import argparse,hashlib
from pathlib import Path
import numpy as np
from .contract import read,write,sha,verify,ROWS
from .bind_owner import BANKS,member
ROOT=Path(__file__).resolve().parents[3]


def build(owner,owner_sha,out):
    verify(owner,'VECTOR_SEAL.json',owner_sha);sources=read(owner/'cpu_only/SOURCES.json')
    e100=ROOT/'results/g_agreement/understand/e100/vectors/artifacts/public'
    seal=read(e100/'INPUT_SEAL.json')
    if sha(e100/'Q_J.npy')!=seal['files']['Q_J.npy']:raise ValueError('sealed E58b basis')
    q=np.load(e100/'Q_J.npy',allow_pickle=False);fractions={}
    for row in ROWS:
        fractions[row]={}
        for block in (42,44):
            d=np.load(owner/'cpu_only'/f'{row}.raw_d{block}.npy',allow_pickle=False)
            fractions[row][str(block)]=float(np.linalg.norm(q@(q.T@d))/np.linalg.norm(d))
    targets=[];joins={};source_pins=[]
    for bank,src in sources.items():
        meta=Path(src['metadata_path']);names=[meta.name]+(['ANNOTATIONS.PRIVATE.json'] if bank=='E57' else [])
        member(meta.parent,'BANK_SEAL.json',src['bank_seal_sha256'],names)
        all_items=read(meta);ann=read(meta.parent/'ANNOTATIONS.PRIVATE.json') if bank=='E57' else {}
        source_pins.append(dict(bank=bank,bank_seal_sha256=src['bank_seal_sha256'],metadata_sha256=sha(meta)))
        for x in all_items:
            row=x['feature']
            if x['split']!='test' or row not in ROWS or BANKS[row]!=bank:continue
            if row=='page_range_digit':values=ann[x['id']]['answer_pair']
            else:
                values=[]
                for label in (1,0):
                    v={z['value'] for z in all_items if z['feature']==row and z['label']==label}
                    if len(v)!=1:raise ValueError('fixed original binary values')
                    values.append(next(iter(v)))
            ident=hashlib.sha256(f'E101:{bank}:{x["id"]}'.encode()).hexdigest()
            targets.append(dict(id=ident,row=row,split='test',property=row,values=dict(A=values[0],B=values[1]),target='B' if x['label']==1 else 'A',contrast_target_sign=1-2*x['label'],J_fraction=fractions[row]))
            joins[ident]=dict(bank=bank,source_id=x['id'],label=x['label'],value=x['value'])
    if len(targets)!=588 or any(sum(x['row']==r for x in targets)!=84 for r in ROWS):raise ValueError('exact588 test targets')
    out.mkdir(parents=True,exist_ok=False);write(out/'TARGETS.json',targets);write(out/'ORIGINAL_IDS.json',joins)
    write(out/'TARGET_SEAL.json',dict(experiment='E101',labels_cpu_only=True,owner_vector_seal_sha256=owner_sha,source_pins=source_pins,
        J_basis_sha256=sha(e100/'Q_J.npy'),J_basis_block=44,J_fraction_42_note='Descriptive projection of d42 into the sealed block44 E58b basis; not a newly fitted block42 Jacobian basis',
        candidate_orientation='Frozen candidate A is label1; target is the opposite label; page_range_digit uses each frozen answer_pair family',
        files={p.name:sha(p) for p in out.iterdir() if p.is_file()},GPU_calls=0))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--owner',type=Path,required=True);p.add_argument('--owner-sha',required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();build(a.owner,a.owner_sha,a.out)
