"""Synthetic logit orientation tests; no source activations or fits."""
import importlib.util
from pathlib import Path
import numpy as np
s=importlib.util.spec_from_file_location('probes',Path(__file__).with_name('probes.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def test_target_logit_shift():
 a=np.zeros((2,5120));b=a.copy();b[:,0]=6
 p=dict(w=np.ones(5120),sd=np.full(5120,2.),mu=np.full(5120,100.),b=21.)
 np.testing.assert_allclose(m.target_logit_shift(a,b,p,[1,0]),[3,-3])
 # Intercept and centering cancel; using unit-normalized weights would be wrong.
 p['mu']*=7;p['b']=-200
 np.testing.assert_allclose(m.target_logit_shift(a,b,p,[1,0]),[3,-3])
def test_reject_nonbinary_target():
 try:m.target_logit_shift(np.zeros((1,5120)),np.zeros((1,5120)),dict(w=np.ones(5120),sd=np.ones(5120)),[2])
 except AssertionError:return
 raise AssertionError('nonbinary target admitted')
if __name__=='__main__':test_target_logit_shift();test_reject_nonbinary_target();print('2 synthetic tests PASS')
