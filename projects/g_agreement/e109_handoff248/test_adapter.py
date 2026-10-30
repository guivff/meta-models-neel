import numpy as np
import pytest
from .adapter import margins


def test_original_fact_sign_intercept_and_unscaled_vectors():
    x=np.array([[2.,3.],[4.,1.]],dtype=np.float32);before=x.copy()
    assert margins(x,np.array([2.,-1.]),np.array(.5),['A','B']).tolist()==[1.5,-7.5]
    assert np.array_equal(x,before)


@pytest.mark.parametrize('x,w,b,letters',[(np.ones((2,2)),[1,1],0.,['A']), (np.ones((2,2)),[1],0.,['A','B']), (np.ones((2,2)),[1,1],0.,['A','other']), (np.array([[np.nan,1]]),[1,1],0.,['A'])])
def test_missing_or_ambiguous_original_source_fails_closed(x,w,b,letters):
    with pytest.raises(ValueError):margins(x,w,b,letters)
