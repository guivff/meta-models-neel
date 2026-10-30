import numpy as np
from .extend_low_doses import new_cells


def test_low_doses_preserve_carrier_and_target_signs():
    h=np.arange(24,dtype=np.float32).reshape(4,6);d=np.array([3.,4.,0,0,0,0]);u=np.eye(6)[:3];signs=np.array([1,-1,-1,1])
    cells=new_cells(h,d,u,signs)
    assert [(a,n) for a,n,v in cells]==[(a,n) for a in (.25,.5) for n in ('J','nonJ','random')]
    for i,(alpha,name,v) in enumerate(cells):
        assert v.dtype==np.float32 and np.allclose(v-h,alpha*5*signs[:,None]*u[i%3])
    assert np.array_equal(h,np.arange(24,dtype=np.float32).reshape(4,6))
