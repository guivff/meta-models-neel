"""Synthetic numerical tests; no outcome data loaded."""
import sys

import time
import unittest
import numpy as np
from scipy.integrate import quad
from scipy.special import ndtr, ndtri
from scipy.optimize._numdiff import approx_derivative
from projects.g_agreement.r_bench import th2_models as m

class ModelsTest(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(20261019)
        self.p = rng.uniform(.04, .68, size=(12, 4))
        self.a = np.array([.3, .55, .7, .85])
        self.rho = self.a[m.PAIR_I] * self.a[m.PAIR_J]
        self.counts = 1000 * m.pair_probabilities(self.p, self.rho)

    def test_pair_cdf_against_independent_integration(self):
        p = np.array([[.004, .026, .31, .985], [.8, .9, .5, .15]])
        rho = np.array([-.8, 0., .3, .5, .9, .98])
        q = m.pair_probabilities(p, rho)
        for f in range(len(p)):
            for k, (i, j) in enumerate(m.PAIRS):
                h, t = ndtri(p[f, i]), ndtri(p[f, j])
                r = rho[k]
                reference = quad(lambda z: np.exp(-z*z/2)/np.sqrt(2*np.pi) * ndtr((t-r*z)/np.sqrt(1-r*r)),
                                 -np.inf, h, epsabs=1e-12, epsrel=1e-11)[0]
                self.assertAlmostEqual(q[f,k,3], reference, delta=3e-10)
        np.testing.assert_allclose(q.sum(axis=2), 1, atol=1e-14)

    def test_gradient(self):
        obj = m._PairObjective(self.p, self.counts)
        test_a = np.array([.4, .5, .65, .9])
        numeric = approx_derivative(lambda a: obj.factor(a)[0], test_a, method='3-point').ravel()
        np.testing.assert_allclose(obj.factor(test_a)[1], numeric, atol=1e-8, rtol=2e-6)

    def test_fit_recovers_lower_order_generator(self):
        result = m.fit_factor(self.p, self.counts)
        self.assertTrue(result['success'], result)
        np.testing.assert_allclose(result['loadings'], self.a, atol=4e-5)
        warm = m.fit_factor(self.p, self.counts, start=result['loadings'])
        self.assertTrue(warm['success'])
        self.assertEqual(warm['n_starts'], 1)
        self.assertLess(abs(warm['nll'] - result['nll']), 1e-7)

    def test_equal_fit(self):
        a = np.repeat(.65, 4)
        counts = 1000*m.pair_probabilities(self.p, a[m.PAIR_I]*a[m.PAIR_J])
        result = m.fit_equal(self.p, counts)
        self.assertTrue(result['success'])
        np.testing.assert_allclose(result['loadings'], a, atol=2e-5)

    def test_joint_bits_marginals_and_pair_recovery(self):
        joint = m.joint_factor(self.p, self.a)
        np.testing.assert_allclose(joint.sum(axis=1), 1, atol=2e-15)
        np.testing.assert_allclose(joint @ m.BITS, self.p, atol=2e-10)
        for k, (i,j) in enumerate(m.PAIRS):
            both = joint[:, (m.BITS[:,i] == 1) & (m.BITS[:,j] == 1)].sum(axis=1)
            np.testing.assert_allclose(both, self.counts[:,k,3]/1000, atol=2e-10)
        independent = m.joint_factor(self.p, np.zeros(4))
        np.testing.assert_allclose(independent[:,15], self.p.prod(axis=1), atol=1e-15)
        np.testing.assert_allclose(independent[:,1], self.p[:,0]*np.prod(1-self.p[:,1:],axis=1), atol=1e-15)

    def test_joint_extreme_loading_convergence(self):
        p = np.array([[.005,.01,.5,.995], [.1,.3,.7,.9], [.02,.98,.04,.96]])
        a = np.array([.98,.98,.98,.98])
        joint = m.joint_factor(p,a)
        high = m.joint_factor(p,a,n_nodes=1024)
        np.testing.assert_allclose(joint, high, atol=2e-9)
        np.testing.assert_allclose(joint @ m.BITS,p,atol=2e-9)

    def test_beta_toy_vector_probability(self):
        p = np.repeat(np.array([[.2],[.7]]),4,axis=1)
        rho=.3
        joint=m.joint_beta(p,rho)
        np.testing.assert_allclose(joint.sum(axis=1),1,atol=1e-14)
        np.testing.assert_allclose(joint @ m.BITS,p,atol=1e-14)
        counts=np.empty((2,6,4))
        for k,(i,j) in enumerate(m.PAIRS):
            for category in range(4):
                mask=(m.BITS[:,i]==category//2)&(m.BITS[:,j]==category%2)
                counts[:,k,category]=1000*joint[:,mask].sum(axis=1)
        result=m.fit_beta(p,counts)
        self.assertTrue(result['success'])
        self.assertAlmostEqual(result['rho'],rho,delta=1e-6)
        np.testing.assert_allclose(m.joint_beta(p,0),m.joint_independence(p),atol=1e-14)

    def test_unrestricted_and_seeded_cdf(self):
        result=m.fit_unrestricted(self.p,self.counts,start=self.a)
        self.assertTrue(result['success'],result)
        np.testing.assert_allclose(result['correlations'],self.rho,atol=5e-5)
        self.assertGreater(result['min_eigenvalue'],0)
        joint,info=m.joint_gaussian(self.p[:2],result['correlation'],return_info=True)
        same=m.joint_gaussian(self.p[:2],result['correlation'])
        np.testing.assert_array_equal(joint,same)
        np.testing.assert_allclose(joint,m.joint_factor(self.p[:2],self.a),atol=3e-6)
        self.assertLess(info['raw_sum_error'],3e-6)
        self.assertLess(info['marginal_error'],3e-6)

    def test_weighting_empty_and_validation(self):
        weighted=m.fit_factor(self.p,self.counts,weights=np.arange(1,13))
        np.testing.assert_allclose(weighted['loadings'],self.a,atol=1e-4)
        self.assertFalse(m.fit_factor(self.p,np.zeros_like(self.counts))['success'])
        with self.assertRaises(ValueError):
            m.fit_factor(np.ones((2,4)),np.zeros((2,6,4)))

if __name__ == '__main__':
    unittest.main(verbosity=2)


from pathlib import Path as _GuardPath
from projects.g_agreement.tests import _write_guard as WG
_GUARD_ROOT = _GuardPath(__file__).resolve().parents[3]
_GUARD = WG.ModuleWriteGuard([_GUARD_ROOT / "results" / "g_agreement", _GUARD_ROOT / "cache" / "g_agreement"])
_write_guard = _GUARD.fixture()

def test_zz_outputs_untouched():
    _GUARD.assert_clean()
