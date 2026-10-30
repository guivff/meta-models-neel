import unittest
import numpy as np
from coherence import item_acf,row_coherence
class CoherenceTests(unittest.TestCase):
    def test_registered_full_series_denominator(self):
        x=np.arange(1.,21.);v=x-x.mean();r=item_acf(x)
        expected=[sum(v[t]*v[t+k] for t in range(20-k))/sum(v*v) for k in range(1,9)]
        np.testing.assert_allclose(r['acf'],expected)
        self.assertNotAlmostEqual(r['acf'][0],1.) # Pearson of these linear slices would be1.
    def test_affine_and_probe_sign_invariance(self):
        x=np.tile(np.array([2,1,4,0,6,3,8,1,5,7,2,6.]),2)
        np.testing.assert_allclose(item_acf(x)['acf'],item_acf(-3*x+80)['acf'])
    def test_equal_item_weighting(self):
        w=np.zeros(5120);w[0]=1
        xs=[np.arange(16.),np.sin(np.arange(20.))]
        hs=[]
        for i,x in enumerate(xs):
            h=np.zeros((len(x),5120));h[:,0]=x;hs.append((str(i),h))
        r=row_coherence(hs,w)
        self.assertAlmostEqual(r['C'],np.mean([item_acf(x)['mean_lag_acf'] for x in xs]))
    def test_undefined_is_not_zero_or_dropped(self):
        self.assertEqual(item_acf(np.ones(20))['status'],'NOT EVALUABLE')
        self.assertEqual(item_acf(np.arange(8))['status'],'SKIPPED_SHORT')
        w=np.ones(5120);h=np.ones((16,5120))
        self.assertIsNone(row_coherence([('constant',h)],w)['C'])
    def test_short_items_skipped_and_counted(self):
        w=np.zeros(5120);w[0]=1
        short=np.zeros((15,5120));long=np.zeros((16,5120));long[:,0]=np.arange(16.)
        result=row_coherence([('short',short),('long',long)],w)
        self.assertEqual(result['n_skipped_short'],1);self.assertEqual(result['n_items'],1)
        self.assertAlmostEqual(result['C'],item_acf(np.arange(16.))['mean_lag_acf'])
if __name__=='__main__':unittest.main()
