import numpy as np
from .build import directions,injection,ablation


def test_projected_directions_signs_and_centered_ablation():
    q=np.eye(5)[:,:2];means=np.array([[2.,1.,3.,0.,0.],[0.,0.,0.,0.,0.]])
    d,u,f=directions(means,q,np.random.default_rng(20261028))
    assert np.allclose(np.linalg.norm(u,axis=1),1)
    assert np.allclose(q.T@u[1],0) and np.allclose(u[0][2:],0) and abs(u[2]@d)<1e-12
    assert np.isclose(f,np.sqrt(5/14))
    h=np.array([[2.,3.,4.,5.,6.],[1.,2.,3.,4.,5.]])
    assert np.array_equal(injection(h,d,u[0],[1,-1],0),h)
    shifted=injection(h,d,u[0],[1,-1],2)
    assert np.allclose((shifted-h)@u[0],[2*np.linalg.norm(d),-2*np.linalg.norm(d)])
    removed=ablation(h,means.mean(0),u[1])
    assert np.allclose((removed-means.mean(0))@u[1],0)
    assert np.allclose(ablation(removed,means.mean(0),u[1]),removed)
    assert np.array_equal(directions(means,q,np.random.default_rng(20261028))[1],u)
