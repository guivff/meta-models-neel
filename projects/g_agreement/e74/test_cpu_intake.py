"""CPU-only checks of dev isolation and ordinal exclusion, using synthetic data."""
import numpy as np
from pathlib import Path
import sys
import unittest
import torch
from . import cpu_intake as c


class CpuIntakeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[3]
        sys.path.insert(0,str(root/'external/mats-nla-workspace/src'))
        from mats.probes import fit_logreg
        cls.fit=staticmethod(fit_logreg)
        torch.set_num_threads(1)
    def test_exact_existing_probe_dev_standardization_and_test_only_metric(self):
        xd=np.array([[-2.,0.],[-1.,1.],[1.,0.],[2.,1.]],dtype=np.float32); yd=np.array([0,0,1,1])
        xt=np.array([[-100.,2.],[-50.,3.],[50.,2.],[100.,3.]],dtype=np.float32)
        a=c.fit_binary(xd,yd,xt,yd,self.fit)
        b=c.fit_binary(xd,yd,xt,1-yd,self.fit)
        np.testing.assert_array_equal(a['raw_coefficient'],b['raw_coefficient'])
        np.testing.assert_array_equal(a['mu'],xd.mean(0))
        self.assertEqual(a['auroc'],1.0);self.assertEqual(b['auroc'],0.0)
    def test_ordinal_rows_retained_no_estimator_or_confirmatory_metric(self):
        rows=[]
        for row in c.ORDINAL:
            bank,name=row.split('/')
            for split in ['dev','test']:
                for i in range(144):
                    rows.append({'bank':bank,'row':name,'source_labels':{'split':split,'cluster':split+str(i)}})
        def forbidden(*a,**k):raise AssertionError('no ordinal estimator authorized')
        result,params,pred=c.fit_probes(rows,{},forbidden)
        self.assertEqual(len(result),2);self.assertFalse(params);self.assertFalse(pred)
        self.assertTrue(all(r['confirmatory_excluded'] and r['probe_auroc'] is None for r in result))
    def test_cluster_leakage_fails_before_fit(self):
        rows=[{'bank':'W1','row':'x','source_labels':{'split':s,'cluster':'same'}} for s in ['dev','test']]
        with self.assertRaises(ValueError):c.fit_probes(rows,{},self.fit)


if __name__=='__main__':unittest.main()
