import unittest
import numpy as np
import core
from prepare import words_for

class ScientificContracts(unittest.TestCase):
    def test_shared_words_removed_and_numbers_expanded(self):
        words,removed=words_for([['- column one','- column 1'],['- column five','- column 5']])
        self.assertEqual(words,[['1','one'],['5','five']]);self.assertEqual(removed,['column'])
        words,_=words_for([['carry'],['no_carry']]);self.assertEqual(words,[[],['no']])

    def test_full_vocabulary_not_top10_and_permutation_null(self):
        y=np.array([0,1]*42)
        ranks=np.array([[100 if value else 900,900 if value else 100] for value in y])
        result=core.g3(ranks,y)
        self.assertEqual(result['auroc'],1.);self.assertTrue(result['readable']);self.assertEqual(result['permutations'],200)
        self.assertEqual(result,core.g3(ranks,y))
        tied=core.g3(np.ones((84,2))*100,y);self.assertEqual(tied['auroc'],.5);self.assertFalse(tied['readable'])

    def test_label_boundaries_and_empty_readability_uses_enrichment(self):
        def classify(a,b,read=None):return core.label({'384':{'enrichment':a},'1536':{'enrichment':b}},{'readable':read})
        self.assertEqual(classify(1.5,1.5),'IN-J');self.assertEqual(classify(1.2,1.2),'OUT-J')
        self.assertEqual(classify(1.5,1.4999),'DIFFUSE');self.assertEqual(classify(1.,1.,True),'IN-J')
        self.assertEqual(classify(1.20001,1.2),'DIFFUSE')

    def test_unit_mean_direction_enrichment_and_orientation(self):
        q=np.eye(5120,1536,dtype=np.float32);x=np.zeros((4,5120));x[2:,0]=2;y=np.array([0,0,1,1])
        ref={str(r):{'values':np.linspace(.8,1.2,200).tolist()} for r in (384,1536)}
        e,means,d,n=core.enrich(x,y,q,ref);reverse=core.enrich(x,1-y,q,ref)[0]
        self.assertAlmostEqual(e['384']['enrichment'],5120/384);self.assertEqual(e,reverse);self.assertEqual(n,2)
        self.assertEqual(e['384']['percentile'],100)
        with self.assertRaises(ValueError):core.enrich(x*0,y,q,ref)

    def test_R2_prefers_native_and_filters_probes(self):
        rr=[{'row':str(i),'class':'structure','probe_auroc':.9,'unprompted_mention_rate':.2 if i<8 else 0.,'forced_choice_auroc':1.,'E1536':3.+i/100 if i<8 else 1.+i/100} for i in range(16)]
        result=core.rule_r2(rr);self.assertTrue(result['met']);self.assertTrue(all(r['measure']=='unprompted mention' for r in result['rows']))
        for r in rr[:8]:r['probe_auroc']=.84
        self.assertEqual(core.rule_r2(rr)['status'],'NOT EVALUABLE')

if __name__=='__main__':unittest.main()
