"""CPU-only, fail-closed E100 vector builder; no model forward or GPU access."""
import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
import numpy as np
from math100 import directions,unit,random_basis,pair_other

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
SEED=20261028
ROWS=[('E57','nesting_depth'),('E57','indent_level'),('E57','page_range_digit'),
      ('E59','format_plan'),('E59','language_plan'),('E56','tense_implicit'),
      ('E56','language_continuation'),('E56','fact_recall')]


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()


def read(p):return json.loads(Path(p).read_text())
def write(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2,allow_nan=False);f.write('\n')
def opaque(bank,identity):return hashlib.sha256(f'E100:{bank}:{identity}'.encode()).hexdigest()[:32]


def verified_members(seal_path,names,expected=None):
    if expected is not None:assert sha(seal_path)==expected,'source seal identity'
    s=read(seal_path)
    for n in names:assert sha(seal_path.parent/n)==s['files'][n],('sealed member',n)
    return s


def inputs(base):
    old=base/'wt-blindspot-internals/results/g_agreement/understand/e79'
    spec=read(old/'INPUTS.json');receipt=read(old/'BUILD_RECEIPT.json')
    verified_members(old/'RESULT_SEAL.json',['INPUTS.json','BUILD_RECEIPT.json'],
        '2d1b9c7d15601db03f6dbb869c9fdcc97b66ed83dc7fa3d492bdb3affbe78e06')
    assert sha(old/'INPUTS.json')==receipt['input_spec_sha256']
    archive=base/'wt-blindspot-internals/cache/g_agreement/understand/e79/inputs_v1/CPU_DIRECTIONS.npz'
    assert sha(archive)==receipt['cpu_directions_sha256']=='839bc5ee7e87aa91dc3a1cf2ad30b92fd7f34212653b6a1e874cc8140db996bc'
    qpath=Path(spec['basis']);qs=qpath.parent/'INPUT_SEAL.json'
    verified_members(qs,[qpath.name],spec['seals'][str(qs)])
    sources=spec['sources'];sources['E56']=dict(metadata=str(base/'wt-wtext/results/g_agreement/understand/e56/cache/bank_2026-10-27_v1/items.PRIVATE.json'),
        captures=[dict(root=str(base/f'wt-wmech/cache/g_agreement/understand/e56_e57/verified_pull_single_v1/shard_{i}/out/e56/capture'),acts='acts44.npy',order='items.order.json') for i in range(3)])
    provenance=dict(e79_result_seal_sha256=sha(old/'RESULT_SEAL.json'),e79_directions_sha256=sha(archive),
        basis_seal_sha256=sha(qs),basis_sha256=sha(qpath),banks={})
    data={}
    for bank,src in sources.items():
        meta=Path(src['metadata']);bs=meta.parent/'BANK_SEAL.json';s=verified_members(bs,[meta.name],spec['seals'].get(str(bs)))
        records=read(meta);by={x['id']:x for x in records};acts={};captures=[]
        for cap in src['captures']:
            folder=Path(cap['root']);cs=folder/'CAPTURE_SEAL.json'
            c=verified_members(cs,[cap['acts'],cap['order']],spec['seals'].get(str(cs)))
            if c.get('bank_seal_sha256') is not None:assert c['bank_seal_sha256']==sha(bs),'bank to capture identity'
            order=read(folder/cap['order']);a=np.load(folder/cap['acts'],mmap_mode='r',allow_pickle=False)
            assert a.shape==(len(order),5120) and len(order)==len(set(order))
            for i,ident in enumerate(order):
                if (bank,by[ident]['feature']) in ROWS:
                    assert ident not in acts;acts[ident]=np.asarray(a[i],np.float64)
            captures.append(dict(seal_path=str(cs),seal_sha256=sha(cs),acts_sha256=c['files'][cap['acts']],order_sha256=c['files'][cap['order']]))
        data[bank]=(records,acts)
        provenance['banks'][bank]=dict(metadata_path=str(meta),metadata_sha256=sha(meta),bank_seal_sha256=sha(bs),captures=captures)
    return data,np.load(archive,allow_pickle=False),qpath,provenance


def core(base,out):
    data,old,qpath,provenance=inputs(base)
    q=np.asarray(np.load(qpath,allow_pickle=False),np.float64)
    if q.shape==(384,5120):q=q.T
    assert q.shape==(5120,384) and np.max(np.abs(q.T@q-np.eye(384)))<1e-4
    out.mkdir(parents=True,exist_ok=False);public=out/'public';public.mkdir();cpu=out/'cpu_only';cpu.mkdir()
    np.save(public/'Q_J.npy',q,allow_pickle=False)
    qr=random_basis();assert np.max(np.abs(qr.T@qr-np.eye(384)))<1e-10
    np.save(public/'Q_R.npy',qr,allow_pickle=False)
    sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
    import torch
    from mats.probes import fit_logreg
    torch.set_num_threads(1);torch.manual_seed(SEED)
    rows=[]
    for ri,(bank,row) in enumerate(ROWS):
        records,acts=data[bank];dev=sorted([x for x in records if x['feature']==row and x['split']=='dev'],key=lambda x:x['id'])
        assert len(dev)==84 and all(x['id'] in acts for x in dev)
        x=np.stack([acts[v['id']] for v in dev]);y=np.array([v['label'] for v in dev]);assert np.isfinite(x).all()
        folder=public/row;folder.mkdir()
        if ri<5:
            d=old[row+'__d'].copy();u0=old[row+'__unit_directions']
            us=dict(d=unit(d),d_J=u0[0].copy(),d_perp=u0[1].copy(),r=u0[2].copy())
            # Exact original arrays are copied; no new direction fit for missed rows.
            for k,i in [('d_J',0),('d_perp',1),('r',2)]:assert us[k].tobytes()==u0[i].tobytes()
            origin='sealed E79 CPU_DIRECTIONS; raw d/J/perp/random reused'
        else:
            d,us=directions(x,y,q,np.random.default_rng(np.random.SeedSequence([SEED,ri,0])))
            origin='sealed block44 dev class means only'
        assert all(np.isclose(np.linalg.norm(v),1.,rtol=1e-10) for v in us.values())
        for k,v in us.items():np.save(folder/(k+'.npy'),v,allow_pickle=False)
        probe=fit_logreg(torch.from_numpy(x.astype(np.float32)),torch.from_numpy(y))
        np.savez(cpu/(row+'_probe.npz'),w=probe.w.numpy(),b=np.array(probe.b),mu=probe.mu.numpy(),sd=probe.sd.numpy())
        np.save(cpu/(row+'_raw_d.npy'),d,allow_pickle=False)
        values={str(label):sorted({v['value'] for v in dev if v['label']==label}) for label in [0,1]}
        assert all(len(v)==1 for v in values.values())
        rows.append(dict(bank=bank,row=row,stream_index=ri,origin=origin,raw_d_norm=float(np.linalg.norm(d)),
            dev_ids=[v['id'] for v in dev],dev_labels=y.tolist(),values=values,
            raw_d_sha256=sha(cpu/(row+'_raw_d.npy')),probe_sha256=sha(cpu/(row+'_probe.npz'))))
    write(cpu/'ROWS.json',rows);write(cpu/'SOURCES.json',provenance)
    write(out/'CORE_RECEIPT.json',dict(status='CORE_ONLY_PENDING_TEST_AND_TOKEN_BINDINGS',authority='f425a5e2',
        block=44,seed=SEED,rank=384,dimension=5120,probe_fit_split='dev_only',GPU_calls=0,
        basis_max_orthogonality_error=float(np.max(np.abs(q.T@q-np.eye(384)))),
        random_basis_max_orthogonality_error=float(np.max(np.abs(qr.T@qr-np.eye(384)))),
        files={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();core(a.base,a.out)
