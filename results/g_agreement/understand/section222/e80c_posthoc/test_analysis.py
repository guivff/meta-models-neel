"""Synthetic verification; never opens experiment inputs."""
import importlib.util
from pathlib import Path
import numpy as np
s=importlib.util.spec_from_file_location('posthoc',Path(__file__).with_name('analyze.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def test_weighted_centering():
 x=np.array([[1.,2.],[3.,0.],[-1.,4.]])
 w=np.array([[1.,1.,1.],[2.,0.,1.]])
 expected=[]
 for row in w:
  z=np.repeat(x,row.astype(int),axis=0);expected.append(np.mean(np.sum((z-z.mean(0))**2,axis=1)))
 np.testing.assert_allclose(m.variance(x@x.T,w),expected)
def test_ratio_and_paired_bootstrap():
 x=np.array([[-2.,-2.],[-1.,1.],[1.,-1.],[2.,2.]])
 x=np.tile(x,(10,1));d=x*np.array([1.,0.]);r=m.summarize(x,{'J_ablated':d,'random_ablated':d,'PCA_ablated':d},{c:np.ones(len(x)) for c in m.CONDITIONS})
 assert r['conditions']['J_ablated']['variance_removed_share']==.5
 assert r['conditions']['J_ablated']['fall_per_variance_share']==2
 assert r['normalized_paired_contrasts']['J_minus_random_ablated']['ci95']==[0.,0.]
if __name__=='__main__':
 test_weighted_centering();test_ratio_and_paired_bootstrap();print('2 synthetic tests PASS')
