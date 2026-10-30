import unittest
import numpy as np
from sparse_primary import fraction,primary_label

class SparseContracts(unittest.TestCase):
    def test_fraction_is_reconstruction_energy_not_residual_reduction(self):
        self.assertAlmostEqual(fraction([[1,0]],[[.5,.25]])[0],.3125)

    def test_primary_thresholds_and_empty_sets(self):
        yes={'status':'EVALUABLE','readable':True};no={'status':'EVALUABLE','readable':False};empty={'status':'NOT EVALUABLE','readable':None}
        self.assertEqual(primary_label(.2,.1,.2,yes),'IN-J');self.assertEqual(primary_label(.2,.1,.2,no),'DIFFUSE')
        self.assertEqual(primary_label(.1,.1,.2,no),'OUT-J');self.assertEqual(primary_label(.1,.1,.2,yes),'DIFFUSE')
        self.assertEqual(primary_label(.2,.1,.2,empty),'IN-J');self.assertEqual(primary_label(.1,.1,.2,empty),'OUT-J')

    def test_suraj_pursuit_recovers_nonnegative_toy_dictionary(self):
        import sys,torch
        from build_basis import ROOT
        sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
        from mats.jspace import nn_pursuit
        atoms=torch.eye(4,dtype=torch.bfloat16);h=torch.tensor([[.6,.8,0,0]])
        idx,coef,recon=nn_pursuit(h,atoms,k=2)
        self.assertTrue(torch.all(coef>=0));self.assertTrue(torch.allclose(h,recon,atol=1e-6))
        self.assertAlmostEqual(fraction(h.numpy(),recon.numpy())[0],1.)

if __name__=='__main__':unittest.main()
