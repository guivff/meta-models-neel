import unittest
from forecast_once import assemble
class ForecastTests(unittest.TestCase):
    def sample(self):
        units=[{'id':str(i),'source_row':'row','binary':i<3,'condition':str(i)} for i in range(4)]
        labels=[{'row':str(i),'label':label,'J_fraction':.02 if i<3 else None} for i,label in enumerate(['IN-J','OUT-J','DIFFUSE','NOT APPLICABLE'])]
        return units,labels
    def test_mapping_and_nonbinary_exclusion(self):
        rows,excluded=assemble(*self.sample())
        self.assertEqual([r['oracle_prediction'] for r in rows],['REPORTED','MISSED','MISSED'])
        self.assertTrue(all(r['oracle_prediction']==r['nla_prediction'] for r in rows))
        self.assertEqual([r['row'] for r in excluded],['3'])
    def test_partial_coverage_rejected(self):
        u,l=self.sample()
        with self.assertRaises(ValueError):assemble(u,l[:-1])
    def test_missing_binary_label_rejected(self):
        u,l=self.sample();l[0]['label']='NOT APPLICABLE'
        with self.assertRaises(ValueError):assemble(u,l)
    def test_nonbinary_contrast_rejected(self):
        u,l=self.sample();l[3]['J_fraction']=.1
        with self.assertRaises(ValueError):assemble(u,l)
if __name__=='__main__':unittest.main()
