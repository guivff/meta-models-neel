"""TH-2-F1 synthetic numerical tests; no real outcome rows or state cache reads."""
from pathlib import Path
import sys
import numpy as np
import pytest
from scipy.optimize._numdiff import approx_derivative

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0,str(REPO))
from projects.g_agreement.r_bench import th2_f1_models as M
from projects.g_agreement.tests import _write_guard as WG

_GUARD = WG.ModuleWriteGuard([REPO/'results'/'g_agreement',REPO/'cache'/'g_agreement'])
_write_guard = _GUARD.fixture()


@pytest.fixture
def synthetic():
    rng=np.random.default_rng(20261023)
    p=rng.uniform(.04,.70,size=(20,6))
    a=np.array([.35,.55,.68,.8,-.6,.45])
    counts=750*M.pair_probabilities(p,a[M.PAIR_I]*a[M.PAIR_J])
    return p,a,counts


def test_pair_count_mapping_and_little_endian_bits():
    counts=np.zeros(64);counts[0]=3;counts[1]=5;counts[16]=7;counts[63]=11
    actual=M.pair_counts(counts)
    for k,(i,j) in enumerate(M.PAIRS):
        expected=np.bincount(2*M.BITS[:,i]+M.BITS[:,j],weights=counts,minlength=4)
        np.testing.assert_array_equal(actual[k],expected)
    batch=M.pair_counts(np.stack([counts,2*counts]))
    np.testing.assert_array_equal(batch[1],2*actual)
    np.testing.assert_array_equal(M.BITS[16],[0,0,0,0,1,0])


def test_signed_analytic_gradient(synthetic):
    p,a,counts=synthetic
    obj=M._PairObjective(p,counts)
    candidate=a+np.array([.06,-.04,.02,.03,.05,-.07])
    numeric=approx_derivative(lambda x:obj.factor(x)[0],candidate,method='3-point').ravel()
    np.testing.assert_allclose(obj.factor(candidate)[1],numeric,atol=2e-8,rtol=2e-6)


def test_signed_factor_recovers_generator_and_keeps_multistarts(synthetic):
    p,a,counts=synthetic
    fit=M.fit_factor(p,counts,start=np.zeros(6))
    assert fit['success'],fit
    assert fit['n_starts']>=5
    assert fit['orientation_identified']
    np.testing.assert_allclose(fit['loadings'],a,atol=6e-5)
    warm=M.fit_factor(p,counts,start=fit['loadings'])
    assert warm['success'],warm
    assert warm['n_starts']>=5
    np.testing.assert_allclose(warm['loadings'],a,atol=6e-5)


@pytest.mark.parametrize('external',[(.5,.4),(-.5,-.4),(.5,-.4)])
def test_all_external_sign_quadrants(synthetic,external):
    p,a,_=synthetic
    a=a.copy();a[4:]=external
    counts=750*M.pair_probabilities(p,a[M.PAIR_I]*a[M.PAIR_J])
    fit=M.fit_factor(p,counts)
    assert fit['success'],fit
    np.testing.assert_allclose(fit['loadings'],a,atol=7e-5)


def test_marginals_pairs_and_unconditional_posterior(synthetic):
    p,a,_=synthetic
    joint,d=M.joint_posterior(p,a)
    assert joint.shape==(20,64) and d.shape==(20,64)
    assert np.isfinite(joint).all() and np.isfinite(d).all()
    np.testing.assert_allclose(joint.sum(1),1,atol=1e-14)
    np.testing.assert_allclose(joint@M.BITS,p,atol=3e-11)
    np.testing.assert_allclose(M.pair_counts(joint),M.pair_probabilities(p,a[M.PAIR_I]*a[M.PAIR_J]),atol=3e-11)
    np.testing.assert_allclose((joint*d).sum(1),0,atol=3e-11)


def test_posterior_orientation_and_negative_loading():
    p=np.full((1,6),.3)
    q,d=M.joint_posterior(p,np.repeat(.6,6))
    assert d[0,63]>0 and d[0,0]<0
    _,signed=M.joint_posterior(p,np.array([.5,.5,.5,.5,-.6,0.]))
    assert signed[0,1]>signed[0,0]  # positive reader error -> harder
    assert signed[0,16]<signed[0,0]  # negative external loading reverses evidence
    independent,zero=M.joint_posterior(p,np.zeros(6))
    np.testing.assert_allclose(zero,0,atol=1e-14)
    np.testing.assert_allclose(independent[0,63],.3**6,atol=1e-15)


def test_four_reader_posterior_is_marginal_of_six(synthetic):
    p,a,_=synthetic
    q6,d6=M.joint_posterior(p,a,n_nodes=256)
    q4,d4=M.posterior_four(p,a,n_nodes=256)
    expected=q6.reshape(len(p),4,16).sum(1)
    weighted=(q6*d6).reshape(len(p),4,16).sum(1)/expected
    np.testing.assert_allclose(q4,expected,atol=2e-14)
    np.testing.assert_allclose(d4,weighted,atol=2e-13)


def test_extreme_signed_quadrature_against_1024_and_2048():
    p=np.array([[.005,.01,.5,.995,.98,.02],[.1,.3,.7,.9,.2,.8],[.02,.98,.04,.96,.01,.99]])
    a=np.array([.98,.98,.98,.98,.98,-.98])
    joint,posterior=M.joint_posterior(p,a)
    q1024,d1024=M.joint_posterior(p,a,n_nodes=1024)
    q2048,d2048=M.joint_posterior(p,a,n_nodes=2048)
    np.testing.assert_array_equal(joint,q1024)
    np.testing.assert_array_equal(posterior,d1024)
    np.testing.assert_allclose(joint,q2048,atol=3e-12,rtol=0)
    np.testing.assert_allclose(posterior,d2048,atol=1e-6,rtol=0)
    np.testing.assert_allclose(joint@M.BITS,p,atol=3e-12,rtol=0)


def test_very_rare_posteriors_stay_finite():
    p=np.array([[1e-12,1-1e-12,.01,.99,.2,.8]])
    a=np.array([.98,.98,.98,.98,-.98,.98])
    joint,d=M.joint_posterior(p,a)
    assert np.isfinite(joint).all() and np.isfinite(d).all()
    assert (joint>=0).all()
    assert np.max(abs(d))<50
    np.testing.assert_allclose(joint.sum(1),1,atol=1e-14)


def test_empty_invalid_and_pair_only_inputs(synthetic):
    p,a,counts=synthetic
    assert not M.fit_factor(p,np.zeros_like(counts))['success']
    with pytest.raises(ValueError):M.fit_factor(p,np.ones((len(p),64)))
    with pytest.raises(ValueError):M.fit_factor(np.zeros((2,6)),np.ones((2,15,4)))
    with pytest.raises(ValueError):M.joint_posterior(p,np.ones(6))
    with pytest.raises(ValueError):M.pair_counts(np.ones(16))


def test_zz_results_and_cache_untouched():
    _GUARD.assert_clean()
