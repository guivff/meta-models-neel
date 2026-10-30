"""Synthetic only; no actual experiment imports or inputs."""
import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location('r2_forecast', Path(__file__).with_name('reproduce_e107b.py'))
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def row(i, a, b, an=True, bn=True):
    return dict(row='synthetic', item_id=str(i), oracle=dict(belief=a,named=an), forecast=dict(belief=b,named=bn))

class Reproduction(unittest.TestCase):
    def test_separate_naming_and_missing_denominators(self):
        out=m.compare([row(0,1,0),row(1,0,1,False,True),row(2,None,0,None,False)],draws=50)
        self.assertEqual(out['oracle']['estimate'],1)
        self.assertEqual(out['forecast']['estimate'],.5)
        self.assertEqual(out['difference']['estimate'],.5)
        self.assertEqual(out['counts']['oracle'],dict(planned=3,kept=1,missing=1,not_stating_value=1))
        self.assertEqual(out['counts']['forecast']['kept'],2)
        self.assertIsNone(out['difference']['CI95'])  # undefined draws retained
    def test_joint_pairing_zero_difference(self):
        out=m.compare([row(i,i%2,i%2) for i in range(12)],draws=50)
        self.assertEqual(out['difference']['CI95'],[0,0])
        self.assertEqual(out['descriptive_R_OL1'],'NOT MET')
    def test_positive_constant_and_order(self):
        xs=[row(i,1,0) for i in range(8)]
        out=m.compare(xs,draws=50)
        self.assertEqual(out,m.compare(xs[::-1],draws=50))
        self.assertEqual(out['difference']['CI95'],[1,1])
        self.assertEqual(out['descriptive_R_OL1'],'MET')
    def test_empty_missing_and_bad_bindings(self):
        self.assertEqual(m.compare([],draws=5)['descriptive_R_OL1'],'NOT EVALUABLE')
        with self.assertRaises(ValueError):m.compare([row(0,1,0)]*2)
        with self.assertRaises(ValueError):m.compare([row(0,2,0)])
        x=row(0,1,0);del x['forecast']
        with self.assertRaises(KeyError):m.compare([x])

if __name__=='__main__':unittest.main()
