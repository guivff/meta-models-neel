import numpy as np
import pytest
from .e112_input_audit import reference


def test_original_transform_and_site_means():
    h=np.array([[3,1,2],[5,4,8],[7,3,5]],dtype=np.float32)
    q=np.array([[1],[0],[0]],dtype=np.float32)
    v,_,mu=reference(h,q)
    assert np.array_equal(mu,h.mean(axis=0,dtype=np.float64))
    assert np.all(v[:,0]==5) and np.array_equal(v[:,1:],h[:,1:])
    shifted=h+np.array([100,-12,9],dtype=np.float32)
    exploratory,_,_=reference(shifted,q)
    assert np.array_equal(exploratory,v+np.array([100,-12,9],dtype=np.float32))


def test_saved_column_not_renormalized():
    h=np.array([[1,4],[2,2],[4,1]],dtype=np.float32)
    q=np.array([[np.float32(.99999994)],[0]],dtype=np.float32)
    v,_,_=reference(h,q)
    expected=h.astype(np.float64)-((h-h.mean(axis=0,dtype=np.float64))@q.astype(np.float64))@q.astype(np.float64).T
    assert v.dtype==np.float32 and np.array_equal(v,expected.astype(np.float32))


def test_invalid_data_fails_closed():
    with pytest.raises(ValueError):reference(np.ones((3,4),dtype=np.float32),np.eye(4)[:,:2])
    with pytest.raises(ValueError):reference(np.full((3,4),np.nan,dtype=np.float32),np.eye(4)[:,:1])
