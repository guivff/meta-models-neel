"""E76 fixed scope, label-free input contract and custody primitives."""
import hashlib,json,math
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
CACHE=ROOT/'cache/g_agreement/understand/e76'
DIM=5120
N=500
CAP=7000
RESERVE=180
STOP=1793314740
BANKS=('W1','E36','E56','E57','E59')
READERS=('oracle','nla')
ARMS=('random','shuffled')


def require(ok,message):
    if not ok:raise ValueError(message)


def read(p):return json.loads(Path(p).read_text())


def dump(p,value):
    with Path(p).open('x') as f:f.write(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False,allow_nan=False)+'\n')


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def verify(base,record):
    base=Path(base).resolve()
    for name,digest in record['files'].items():
        p=(base/name).resolve();require(p.is_relative_to(base) and not (base/name).is_symlink() and sha(p)==digest,'Sealed file mismatch')


def source_verify():verify(ROOT,read(HERE/'POD_SOURCE_SEAL.json'))


def validate_bank(bank):
    require(set(bank)=={'experiment','schema','items','selected_indices','source_bank_count'} and bank['experiment']=='E76'
        and bank['schema']=='E76_BLIND_V1' and bank['source_bank_count']==5,'Exact blind schema required')
    items=bank['items'];selected=bank['selected_indices']
    require(len(items)>=N and len({x['id'] for x in items})==len(items),'Unique full test population required')
    require(len(selected)==N and len(set(selected))==N and all(type(i) is int and 0<=i<len(items) for i in selected),'500 unique frozen shuffled selections required')
    require({x['bank'] for x in items}==set(range(5)),'All five source banks required')
    for x in items:
        require(set(x)=={'id','ids','bank'} and isinstance(x['id'],str) and len(x['id'])==32
            and all(c in '0123456789abcdef' for c in x['id']),'Opaque item schema required')
        require(type(x['bank']) is int and 0<=x['bank']<5 and isinstance(x['ids'],list) and x['ids']
            and all(type(t) is int and t>=0 for t in x['ids']),'Frozen test token IDs and numeric source covariate required')
    return items,selected


def load_inputs():
    import numpy as np
    p=CACHE/'pod_inputs'
    require({str(x.relative_to(p)) for x in p.rglob('*') if x.is_file()}=={'BANK.json','gaussian.npy','INPUT_SEAL.json'}
        and not any(x.is_symlink() for x in p.rglob('*')),'Positive pod data whitelist required')
    seal=read(p/'INPUT_SEAL.json');require(set(seal['files'])=={'BANK.json','gaussian.npy'},'Exact input seal required');verify(p,seal)
    bank=read(p/'BANK.json');items,selected=validate_bank(bank);z=np.load(p/'gaussian.npy',allow_pickle=False)
    require(z.shape==(N,DIM) and z.dtype==np.float32 and np.isfinite(z).all(),'Fixed Gaussian matrix required')
    require(np.array_equal(z,np.random.default_rng(20261027).standard_normal((N,DIM)).astype(np.float32)),'Gaussian seed/bytes mismatch')
    return bank,items,selected,z


def norm_match(vectors,target):
    import numpy as np
    x=np.asarray(vectors,dtype=np.float32);target=np.asarray(target,dtype=np.float64)
    norms=np.linalg.norm(x.astype(np.float64),axis=1)
    require(x.ndim==2 and x.shape[1]==DIM and target.shape==(len(x),) and np.isfinite(x).all()
        and np.isfinite(target).all() and (target>0).all() and (norms>0).all(),'Finite nonzero norm references required')
    out=(x.astype(np.float64)*(target/norms)[:,None]).astype(np.float32)
    require(np.allclose(np.linalg.norm(out.astype(np.float64),axis=1),target,rtol=1e-6,atol=0),'Norm scaling numerical failure')
    return out


def make_pools(bank,norms,selected_raw,z):
    import numpy as np
    items,selected=validate_bank(bank);banks=np.array([items[i]['bank'] for i in selected])
    require(set(norms)==set(selected_raw)=={42,44},'Both native layers required')
    medians={};pools={}
    for layer in (42,44):
        v=np.asarray(norms[layer],dtype=np.float64)
        require(v.shape==(len(items),) and np.isfinite(v).all() and (v>0).all(),'Complete native norm reference population required')
        median=np.array([np.median(v[[i for i,x in enumerate(items) if x['bank']==b]]) for b in range(5)])
        medians[str(layer)]=median.tolist();target=median[banks]
        pools[layer,'random']=norm_match(z,target);pools[layer,'shuffled']=norm_match(selected_raw[layer],target)
    return pools,{'source_bank_median_norms':medians,'source_bank_indices_by_pool_index':banks.tolist(),
        'median_population':'All frozen test read-point norms per bank/native layer, no label or probe filtering',
        'random_paired_reference':True,'adapter_transform':'Unchanged native reader adapter follows this input scaling'}
