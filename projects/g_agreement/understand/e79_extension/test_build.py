import numpy as np
from projects.g_agreement.understand.e79_extension.build import fit_row,load_original
from projects.g_agreement.readerbench.io import read
from pathlib import Path


def test_dev_only_directions_and_target_independence():
    spec=read(Path(__file__).resolve().parents[4]/'results/g_agreement/understand/e79_extension/INPUTS.json')
    original=load_original(spec);rng=np.random.default_rng(1)
    meta=[dict(id=f'{s}-{v}-{i:02}',feature='row',split=s,value=v) for s in ('dev','test') for v in ('A','B') for i in range(42)]
    order=[m['id'] for m in meta];acts=rng.normal(size=(168,8));q=np.eye(8)[:,:3]
    result=fit_row(meta,order,acts,'row',['A','B'],original,q,5)
    changed=acts.copy();changed[84:]*=100
    other=fit_row(meta,order,changed,'row',['A','B'],original,q,5)
    for i in (2,3,4,6):assert np.array_equal(result[i],other[i])
    swapped=[dict(m,value=('B' if m['value']=='A' else 'A')) if m['split']=='test' else m for m in meta]
    second=fit_row(swapped,order,acts,'row',['A','B'],original,q,5)
    assert np.array_equal(result[6],second[6])
    assert (result[6]==1).sum()==(result[6]==-1).sum()==42
    d,u=result[3:5]
    assert np.allclose(np.linalg.norm(u,axis=1),1) and abs(u[2]@d)<1e-10
    assert np.allclose(q.T@u[1],0) and np.allclose(u[0][3:],0)
