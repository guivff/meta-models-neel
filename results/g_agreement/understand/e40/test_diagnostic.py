"""Synthetic checks for E40 diagnostic aggregation, not model outcomes."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
from diagnostic import strata, Summaries, metadata


def test_deciles_are_stable_equal_frequency_and_axes_partition():
    x = np.ones((20, 2), dtype=np.float32)
    positions = np.array([0,1,7,8]*5)
    domains = np.array(['a','b']*10)
    norms, groups = strata(x, positions, domains)
    np.testing.assert_allclose(norms, np.sqrt(2))
    for i in range(10):
        np.testing.assert_array_equal(np.flatnonzero(groups[f'norm_decile:{i+1}']), [2*i,2*i+1])
    assert sum(groups[k].sum() for k in ('position:0','position:1-7','position:8+')) == 20
    assert groups['domain:a'].sum() == 10


def test_pooled_fvu_is_centered_within_group_and_dead_uses_positive_values():
    x = np.array([[1., 0.], [3., 0.], [10.,0.], [12.,0.]])
    groups = {'all':np.ones(4,dtype=bool),'first':np.array([1,1,0,0],dtype=bool),
              'empty':np.zeros(4,dtype=bool)}
    r = x + 1
    index = np.array([[0,1],[1,2],[2,3],[3,0]])
    value = np.array([[1.,0.],[1.,0.],[1.,0.],[1.,0.]])
    a=Summaries(x,groups,4)
    a.update(0,x[:2],r[:2],index[:2],value[:2]);a.update(2,x[2:],r[2:],index[2:],value[2:])
    result=a.result()
    assert result['first']['total_variance'] == 2
    assert result['first']['fvu'] == 2
    assert result['first']['dead_fraction'] == .5
    assert result['all']['dead_latents'] == 0
    assert result['empty']['fvu'] is None and result['empty']['dead_fraction'] is None
    assert result['first']['variance_about_global_mean'] > result['first']['total_variance']


@pytest.mark.parametrize('x', [np.array([[np.nan]]),np.array([[np.inf]])])
def test_nonfinite_norm_rejected(x):
    with pytest.raises(ValueError):strata(x,np.array([0]),np.array(['a']))


def test_zero_variance_is_undefined_instead_of_dividing():
    x=np.ones((2,1));a=Summaries(x,{'all':np.ones(2,dtype=bool)},2)
    a.update(0,x,x,np.array([[0],[0]]),np.ones((2,1)))
    assert a.result()['all']['fvu'] is None


def test_metadata_rejects_incomplete_population():
    with pytest.raises(ValueError):metadata({'documents':[{'id':'a','domain':'a','positions':[0]}]})
