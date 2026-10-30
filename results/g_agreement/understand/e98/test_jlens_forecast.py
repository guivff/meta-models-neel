import unittest
import numpy as np
import torch
from transformers.models.qwen3.modeling_qwen3 import Qwen3RMSNorm
from jlens_forecast import custody,mean_direction,logits,CAPTURE_SHA,CARD_SHA

class Tests(unittest.TestCase):
    def receipt(self):return dict(status='COMPLETE',R3b_readers_opened=False,capture_seal_sha256=CAPTURE_SHA,card_sha256=CARD_SHA)
    def test_opened_or_failed_capture_rejected(self):
        custody(self.receipt())
        for k,v in [('R3b_readers_opened',True),('status','FAILED'),('card_sha256','other'),('capture_seal_sha256','other')]:
            d=self.receipt();d[k]=v
            with self.assertRaises(ValueError):custody(d)
    def test_model_specific_norm_not_27b_additive_gain(self):
        h=torch.tensor([[1.,2.,-3.,4.]])
        j=torch.eye(4);wu=torch.tensor([[1.,0.,0.,0.],[0.,1.,0.,0.]])
        w=torch.tensor([2.,3.,4.,5.],dtype=torch.bfloat16)
        norm=Qwen3RMSNorm(4,eps=1e-6).to(torch.bfloat16)
        with torch.no_grad():norm.weight.copy_(w)
        actual=logits(h,j,wu,norm)
        x=h.to(torch.bfloat16).float();scaled=(x*torch.rsqrt(x.square().mean(-1,keepdim=True)+1e-6)).to(torch.bfloat16)
        expected=(w*scaled).float()@wu.T
        torch.testing.assert_close(actual,expected)
        self.assertFalse(torch.allclose(actual,((1+w)*scaled).float()@wu.T))
    def test_A_orientation_and_model_width(self):
        h=np.zeros((84,2560),np.float32);y=np.array([1]*42+[0]*42);h[y==1,17]=3;h[y==0,17]=-2
        means,d,n=mean_direction(h,y)
        self.assertEqual(n,5);self.assertEqual(d[17],1);self.assertEqual(np.linalg.norm(d),1)
        self.assertEqual(means[0,17],3);self.assertEqual(means[1,17],-2)
    def test_degenerate_or_nonfinite_stops(self):
        y=np.array([1,0]);h=np.ones((2,2560))
        with self.assertRaises(ValueError):mean_direction(h,y)
        h[0,0]=np.nan
        with self.assertRaises(ValueError):mean_direction(h,y)
    def test_pursuit_is_width_generic_without_27b_dictionary(self):
        from mats.jspace import nn_pursuit
        atoms=torch.eye(4,dtype=torch.bfloat16);h=torch.tensor([[1.,0.,2.,0.]])
        idx,coef,r=nn_pursuit(h,atoms,k=2)
        torch.testing.assert_close(r,h);self.assertEqual(set(idx[0].tolist()),{0,2})

if __name__=='__main__':unittest.main()
