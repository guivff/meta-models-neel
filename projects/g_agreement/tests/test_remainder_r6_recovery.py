import unittest
from types import SimpleNamespace
import torch
from projects.g_agreement.r_bench import remainder_r6_recovery as R

class RecoveryTests(unittest.TestCase):
    def rows(self):
        return [{'pair_id':f'C4-{i:02d}','arm':arm,'model_lo_error':.01,'oracle42_lo_error':.01,
                 'oracle42_positive':arm=='focal','original_oracle42_positive':arm=='focal','original42_cos':.9999}
                for i in range(20) for arm in ('focal','control')]

    def test_numeric_gate_keeps_full_cohort(self):
        rows=self.rows();self.assertEqual(R.validate_numeric(rows),[])
        with self.assertRaisesRegex(ValueError,'40 unique'):R.validate_numeric(rows[:-1])
        rows[0]['oracle42_lo_error']=.101;self.assertTrue(R.validate_numeric(rows))
        rows=self.rows();rows[0]['oracle42_positive']=False;self.assertTrue(R.validate_numeric(rows))
        rows=self.rows();rows[0]['original42_cos']=.998;self.assertTrue(R.validate_numeric(rows))
        rows=self.rows();rows[0]['model_lo_error']=float('nan');self.assertTrue(R.validate_numeric(rows))
        rows=self.rows();rows[0]['original42_cos']=float('nan');self.assertTrue(R.validate_numeric(rows))
        self.assertEqual(R.validate_numeric(self.rows()[:2],require_full=False),[])

    def test_failed_or_nonfinite_smoke_receipt_cannot_unlock_recovery(self):
        rec={'smoke':True,'numerical_errors':[],'coverage_cells':6,'state_cells':6,
             'zero_delta_max_abs':{str(L):0. for L in R.LAYERS},'seconds_per_group':1.,'load_seconds':1.}
        R.validate_smoke_receipt(rec)
        for change in ({'smoke':False},{'numerical_errors':['numeric drift']},{'coverage_cells':5},
                       {'zero_delta_max_abs':{'42':float('nan'),'44':0.,'56':0.}},
                       {'seconds_per_group':float('nan')},{'state_cells':3}):
            with self.assertRaises(RuntimeError):R.validate_smoke_receipt({**rec,**change})

    def test_smoke_covers_every_frozen_dose_and_paired_natural(self):
        groups=[]
        for i,dose in enumerate((.5,1.,2.)):
            pair=f'C4-{i:02d}'
            for arm,direction,alpha in [('focal','d_olens_L38',dose),('control','natural',0.)]:
                groups.append({'direction':direction,'alpha':alpha,'selected':[{'pair_id':pair,'arm':arm}]})
        result=R.smoke_groups({'groups':groups})
        self.assertEqual(len(result),6)
        conditions={(g['direction'],g['alpha']) for g in groups}
        rec={'smoke':True,'numerical_errors':[],'coverage_cells':6,'state_cells':18,
             'zero_delta_max_abs':{str(L):0. for L in R.LAYERS},'seconds_per_group':1.,'load_seconds':1.,
             'condition_site_cells':[(d,a,L) for d,a in conditions for L in R.LAYERS]}
        R.validate_smoke_receipt(rec,conditions)
        with self.assertRaisesRegex(RuntimeError,'condition/site'):R.validate_smoke_receipt({**rec,'condition_site_cells':rec['condition_site_cells'][:-1]},conditions)

    def test_native_edit_and_three_read_sites_with_cleanup(self):
        class Block(torch.nn.Module):
            def forward(self,h):return h+1
        class Tiny(torch.nn.Module):
            def __init__(self):
                super().__init__();self.anchor=torch.nn.Parameter(torch.tensor(0.));self.model=torch.nn.Module()
                self.model.layers=torch.nn.ModuleList([Block() for _ in range(58)])
            def forward(self,input_ids,attention_mask,**kw):
                h=input_ids.float()[...,None].repeat(1,1,3)
                for block in self.model.layers:h=block(h)
                return SimpleNamespace(logits=h)
        model=Tiny();rows=[[1,2],[3]];spans=[(1,2),(0,1)]
        natural=R.capture_multi(model,rows,spans,None,0)
        edited=R.capture_multi(model,rows,spans,torch.tensor([[5.,5.,5.],[-2.,-2.,-2.]]),0)
        for layer in R.LAYERS:
            torch.testing.assert_close(natural[layer],torch.tensor([[2.+layer+1]*3,[3.+layer+1]*3]))
            torch.testing.assert_close(edited[layer]-natural[layer],torch.tensor([[5.]*3,[-2.]*3]))
        self.assertTrue(all(not block._forward_hooks for block in model.model.layers))

if __name__=='__main__':unittest.main()


class JointRecoveryTests(unittest.TestCase):
    def test_standalone_cannot_expand_and_joint_keeps_final_pull_reserve(self):
        from unittest.mock import patch
        with patch.object(R,'plan') as plan:
            for budget,joint in [(4200,False),(1201,False),(300,True),(5401,True),(float('nan'),True),(float('inf'),True),(True,True)]:
                with self.assertRaisesRegex(RuntimeError,'original cap'):
                    R.run([],'p',None,budget,joint_run=joint)
            plan.assert_not_called()
