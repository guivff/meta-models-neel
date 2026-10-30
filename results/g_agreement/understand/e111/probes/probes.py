"""E111 CPU reuse of sealed per-row, unhooked-dev block-44 probes; no fitting."""
import hashlib,json
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def target_logit_shift(natural,intervened,probe,target_label):
    """Class1 logit is ((h-mu)/sd)@w+b. Class0 target reverses its sign."""
    a=np.asarray(natural,dtype=np.float64);b=np.asarray(intervened,dtype=np.float64)
    t=np.asarray(target_label);assert a.shape==b.shape and a.shape[-1]==5120
    assert set(np.unique(t)) <= {0,1}
    return ((b-a)@(np.asarray(probe['w'],dtype=np.float64)/probe['sd']))*(2*t-1)
def verify_manifest():
    m=read(HERE/'PROBE_MANIFEST.json')
    for p,h in m['pins'].items():assert sha(p)==h,p
    for row in m['probes']:
        p=np.load(row['weights_path'],allow_pickle=False)
        assert set(p.files)=={'w','b','mu','sd'}
        assert all(p[k].shape==(5120,) and np.isfinite(p[k]).all() for k in ('w','mu','sd'))
        assert np.asarray(p['b']).shape==() and np.isfinite(p['b']) and np.all(p['sd']>0)
        assert sha(row['weights_path'])==row['weights_sha256']
    return m
if __name__=='__main__':
    m=verify_manifest();print(json.dumps(dict(status='VERIFIED_REUSE_ONLY',probes=len(m['probes']),new_fits=0,gpu_hours=0)))
