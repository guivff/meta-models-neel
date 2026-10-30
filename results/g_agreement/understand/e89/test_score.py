import unittest
import numpy as np
from sklearn.metrics import roc_auc_score
import score as s
class Tests(unittest.TestCase):
 def test_auc_ties(self):
  y=np.array([0,1,0,1]);x=np.array([.2,.2,.6,.8]);self.assertEqual(s.weighted_auc(y,x,np.ones(4)),roc_auc_score(y,x))
 def test_auc_weighted(self):
  y=np.array([0,1,0,1]);x=np.array([.2,.4,.4,.9]);w=np.array([2,1,3,2]);self.assertAlmostEqual(s.weighted_auc(y,x,w),roc_auc_score(y,x,sample_weight=w))
 def test_cluster_split(self):
  rows=[{'group':str(g)}for g in range(10)for _ in range(4)];sp=s.split_groups(rows);self.assertEqual(sp,s.split_groups(rows));self.assertEqual(sp.count('train'),20)
  for g in range(10):self.assertEqual(len(set(sp[g*4:g*4+4])),1)
 def test_generic_no_supported(self):self.assertEqual(s.outcomes({'generic':True,'claims':[]}),{'contradicted':0,'no_supported':1})
 def test_both(self):self.assertEqual(s.outcomes({'generic':False,'claims':[{'verdict':'CONTRADICTED'},{'verdict':'SUPPORTED'}]}),{'contradicted':1,'no_supported':0})
 def test_one_class(self):self.assertIsNone(s.metric([{'outcomes':{'x':0},'score':.5,'group':'a'}],'x',10)['AUROC'])
 def test_unparseable(self):
  r=s.metric([{'outcomes':None,'score':.4,'group':'a'}],'x',10);self.assertEqual(r['unparseable'],1);self.assertIsNone(r['AUROC'])
 def test_pipeline(self):
  m=s.model();m.fit(['real passage meaning','real content description','random gibberish','random noisy noise'],[0,0,1,1]);self.assertEqual(m.predict_proba(['unseen text']).shape,(1,2));self.assertEqual(m['logistic'].C,1)
if __name__=='__main__':unittest.main()
