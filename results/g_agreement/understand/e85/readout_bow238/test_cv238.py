"""Synthetic tests only; no real readout or source key accessed."""
import unittest
import numpy as np
from cv238 import folds,validate,analyze,reading


def rows():
    return [dict(id=f'{q}-{g}-{a}',quartet=q,genre=g,addressed=a,
        text=('hedged ' if a else 'direct ')+('benchmark ' if g else 'ordinary ')+f'onlygroup{q}')
        for q in range(10) for g in (0,1) for a in (0,1)]


class Synthetic(unittest.TestCase):
    def test_quartet_grouping_and_exact_strata(self):
        data=rows();f=folds(data)
        np.testing.assert_array_equal(f,folds(data))
        for q in range(10):self.assertEqual(len(set(f[i] for i,r in enumerate(data) if r['quartet']==q)),1)
        for k in range(5):
            for g in (0,1):
                for a in (0,1):self.assertEqual(sum(f[i]==k and r['genre']==g and r['addressed']==a for i,r in enumerate(data)),2)

    def test_oof_and_control_orientation(self):
        result,p,f,_,_=analyze(rows(),bootstrap=20)
        for target in ('addressed','genre'):
            self.assertEqual(result[target]['oof_auroc'],1.)
            self.assertEqual(result[target]['item_bootstrap_95ci'],[1.,1.])
            self.assertTrue(np.isfinite(p[target]).all())
        self.assertEqual(result['addressed']['registered_reading'],'CARRIED_IN_WORDS')

    def test_no_heldout_word_in_training_vocabulary(self):
        data=rows();_,_,fold,vocabs,_=analyze(data,bootstrap=2)
        for i,r in enumerate(data):self.assertNotIn(f'onlygroup{r["quartet"]}',vocabs[fold[i]])

    def test_bad_original_groups(self):
        validate(rows(),10)
        for bad in (rows()[1:],rows()+[rows()[0]]):
            with self.assertRaises(ValueError):validate(bad,10)

    def test_thresholds_and_no_extra_all_item_refit(self):
        self.assertEqual(reading(.8),'CARRIED_IN_WORDS')
        self.assertEqual(reading(.6),'HIDDEN_STATE_TO_OUTPUT_BOTTLENECK')
        self.assertEqual(reading(.7),'INTERMEDIATE')
        result,_,_,vocabs,_=analyze(rows(),bootstrap=2)
        self.assertEqual(len(vocabs),5)
        self.assertIn('no full-corpus refit',result['weights'])
        self.assertIn('hedged',[x['word'] for x in result['addressed']['top_positive']])


if __name__=='__main__':unittest.main()
