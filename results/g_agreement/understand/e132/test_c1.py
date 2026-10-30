"""Synthetic E132 C1 tests; no real source or label is accessed."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from sklearn.metrics import roc_auc_score
from bind_c1 import Store,template
from analyze_c1 import fold_ids,predict_category,bootstrap_weights,weighted_auc,contains,analyze


def fixture():
    rows=[]
    for category in ('first','second'):
        for t in range(6):
            for pick,cue in [('alpha','warm'),('beta','cold')]:
                text=(pick+' ' if t%2==0 else '')+cue+' surrounding wording'
                rows.append(dict(id=f'{category}{t}{pick}',template_group=f't{t}',item_group=f'{category}{t}{pick}',
                    category=category,pick=pick,prompt=f'pick a {category} member template{t}',
                    nonmodal=pick=='beta',readouts={'60':text,'52':text}))
    return rows


class ClarificationOne(unittest.TestCase):
    def test_item_and_template_grouping_across_categories(self):
        rows=fixture();f=fold_ids(rows)
        np.testing.assert_array_equal(f,fold_ids(rows))
        for t in range(6):self.assertEqual(len({f[i] for i,r in enumerate(rows) if r['template_group']==f't{t}'}),1)
        self.assertEqual(len(set(f)),5)

    def test_candidate_features_excluded_and_no_heldout_vocab(self):
        rows=fixture()[:12];f=fold_ids(rows)
        p,missing,models=predict_category(rows,f,['alpha','beta'],60,'B','combined')
        self.assertFalse(missing)
        for art in models:
            if art['vectorizer'] is not None:
                vocab=art['vectorizer'].vocabulary_
                self.assertNotIn('alpha',vocab);self.assertNotIn('beta',vocab)
                held_templates={r['template_group'].replace('t','template') for r in rows if r['id'] in art['heldout_ids']}
                self.assertTrue(vocab.keys().isdisjoint(held_templates))
        self.assertTrue(np.isfinite(p).all())

    def test_missing_training_member_is_unavailable(self):
        rows=fixture()[:12];f=fold_ids(rows)
        p,missing,_=predict_category(rows,f,['alpha','beta','absent'],60,'B','readout')
        self.assertTrue(np.isnan(p[:,2]).all())
        self.assertTrue(any(z['reason']=='member_absent_from_train' for z in missing))

    def test_weighted_auc_matches_expanded_item_resample(self):
        y=np.array([True,False,True,False]);s=np.array([.5,.2,.5,.9]);w=np.array([[1,1,1,1],[2,1,0,3]])
        vals=weighted_auc(y,s,w)
        for j in range(2):
            ix=np.repeat(np.arange(4),w[j]);self.assertAlmostEqual(vals[j],roc_auc_score(y[ix],s[ix]))

    def test_bootstrap_preserves_class_counts_and_pairing(self):
        rows=fixture();w=bootstrap_weights(rows,5)
        np.testing.assert_array_equal(w,bootstrap_weights(rows,5))
        for c in ('first','second'):
            for pick in ('alpha','beta'):
                ix=[i for i,r in enumerate(rows) if r['category']==c and r['pick']==pick]
                np.testing.assert_array_equal(w[:,ix].sum(axis=1),np.full(5,6))

    def test_endpoint_literal_and_full_analysis(self):
        self.assertTrue(contains('ALPHA is named','alpha'));self.assertFalse(contains('warm wording','alpha'))
        rows=fixture()
        # Keep both labels in the synthetic nonmodal subset for a defined macro.
        for r in rows:r['nonmodal']=True
        result,_,_,_=analyze(rows,draws=8)
        report=result['headline']
        self.assertEqual(report['B_rule'],'MET')
        self.assertAlmostEqual(report['macro_ovr_auroc']['readout'],1.)
        self.assertAlmostEqual(report['macro_ovr_auroc']['prompt'],.5)
        self.assertEqual(result['blocks']['60']['A']['all']['B_rule'],'NOT_APPLICABLE_ENDPOINT_A_DESCRIPTIVE')
        self.assertNotIn('44',result['blocks'])

    def test_original_template_parser_and_hash_tamper(self):
        self.assertEqual(template('c03t5s6'),'t5')
        with self.assertRaises(ValueError):template('made_up_family')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'data.json').write_text('[1]')
            h=hashlib.sha256((p/'data.json').read_bytes()).hexdigest()
            (p/'seal.json').write_text(json.dumps({'files':{'data.json':h}}));sh=hashlib.sha256((p/'seal.json').read_bytes()).hexdigest()
            self.assertEqual(Store().member(p/'seal.json',sh,'data.json'),[1])
            (p/'data.json').write_text('[2]')
            with self.assertRaises(ValueError):Store().member(p/'seal.json',sh,'data.json')


if __name__=='__main__':unittest.main()
