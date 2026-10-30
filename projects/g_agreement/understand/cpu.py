"""Seal checks and PCA shared by the exploratory E-runs; no model imports."""
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy.linalg import eigh

ROOT = Path(__file__).resolve().parents[3]
SEED = 20261024


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def read(path): return json.loads(Path(path).read_text())
def rows(path): return [json.loads(x) for x in Path(path).read_text().splitlines()]
def dump(path, obj): Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False)+'\n')


def verify(directory, name='SCORE_SEAL.json'):
    directory = Path(directory); s = read(directory/name)
    for f, digest in s['files'].items():
        p = (directory/f).resolve()
        if not p.is_relative_to(directory.resolve()) or sha(p) != digest:
            raise ValueError(f'seal mismatch: {f}')
    return s


def seal(directory, names, status):
    directory = Path(directory)
    dump(directory/'SCORE_SEAL.json', {'status':status, 'files':{n:sha(directory/n) for n in names}})


def pca(x, k=64):
    """Exact centered top-k PCA via smaller Gram covariance; rows are observations."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 2 or not np.isfinite(x).all() or min(x.shape) <= k:
        raise ValueError('PCA requires finite matrix with more observations/dimensions than k')
    mean = x.mean(axis=0); z = x-mean
    total = float(np.square(z).sum())
    if total <= 0: raise ValueError('zero PCA variance')
    if len(z) < z.shape[1]:
        gram = z@z.T
        eig, vectors = eigh(gram, subset_by_index=[len(z)-k,len(z)-1], driver='evr')
        eig, vectors = eig[::-1], vectors[:,::-1]
        if eig[-1] <= eig[0]*1e-12: raise ValueError('insufficient numerical rank for requested k')
        basis = (vectors.T@z)/np.sqrt(eig)[:,None]
    else:
        eig, vectors = eigh(z.T@z, subset_by_index=[z.shape[1]-k,z.shape[1]-1], driver='evr')
        eig, basis = eig[::-1], vectors[:,::-1].T
        if eig[-1] <= eig[0]*1e-12: raise ValueError('insufficient numerical rank for requested k')
    if not np.allclose(basis@basis.T,np.eye(k),atol=1e-6): raise ValueError('nonorthonormal PCA basis')
    return {'basis':basis,'eigenvalues':eig,'mean':mean,'variance_fraction':eig/total,'total_centered_ss':total}


def image_fraction(directions, basis):
    d = np.asarray(directions,dtype=np.float64)
    if not np.allclose(np.linalg.norm(d,axis=-1),1,atol=1e-5): raise ValueError('unit directions required')
    return np.square(d@basis.T).sum(axis=-1)
