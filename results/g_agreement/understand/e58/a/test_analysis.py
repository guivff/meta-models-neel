import unittest
from analyze_once import evaluate,category_rows

class RegisteredRa1(unittest.TestCase):
    def records(self):
        a=[{'bank':'W1','row':'a'+str(i),'category':['bookkeeping','delimiter','syntactic'][i%3],'J_fraction':.01+i*.001,'label':'OUT-J' if i<7 else 'IN-J','probe_auroc':.85} for i in range(10)]
        b=[{'bank':'E36','row':'b'+str(i),'category':'content','J_fraction':.1+i*.001,'label':'DIFFUSE' if i<3 else 'IN-J','probe_auroc':.9} for i in range(10)]
        return a+b

    def test_registered_inclusive_rate_boundaries_and_one_sided_test(self):
        rows=self.records();r=evaluate(rows)
        self.assertTrue(r['met']);self.assertLess(r['one_sided_p'],.05)
        self.assertEqual(r['bookkeeping_delimiter_syntactic']['OUT_J_or_DIFFUSE_rate'],.7)
        self.assertEqual(r['content']['OUT_J_or_DIFFUSE_rate'],.3)
        rows[6]['label']='IN-J';self.assertFalse(evaluate(rows)['met'])
        rows=self.records();rows[13]['label']='DIFFUSE';self.assertFalse(evaluate(rows)['met'])

    def test_probe_threshold_format_exclusion_and_bank_row_keys(self):
        rows=self.records();rows.append({'bank':'E49','row':'a0','category':'format','J_fraction':.1,'label':'IN-J','probe_auroc':.9})
        r=evaluate(rows);self.assertEqual(r['format_rows_not_in_R_a1_contrast'],1)
        rows[0]['probe_auroc']=.84999;r=evaluate(rows)
        self.assertEqual(len(r['excluded']),1)
        with self.assertRaises(ValueError):evaluate(rows+[rows[1]])

    def test_undefined_eligible_labels_are_held_not_silently_excluded(self):
        rows=self.records();rows[0]['label']='NOT APPLICABLE';rows[0]['J_fraction']=None
        with self.assertRaises(ValueError):evaluate(rows)
        self.assertIsNone(evaluate(self.records()[:10])['met'])

    def test_blind_category_packet_has_unique_registered_categories(self):
        self.assertEqual(category_rows({'rows':[{'bank':'W1','row':'x','category':'content'}]}),{('W1','x'):'content'})
        with self.assertRaises(ValueError):category_rows({'rows':[{'bank':'W1','row':'x','category':'invented'}]})

    def test_only_registered_count_only_capacity_has_no_probe(self):
        row={'bank':'E57','row':'capacity_list','category':'content','J_fraction':None,'label':'NOT APPLICABLE','probe_auroc':None,'probe_not_applicable_reason':'REGISTERED_COUNT_ONLY_NO_PROBE'}
        r=evaluate(self.records()+[row]);self.assertTrue(r['met']);self.assertEqual(len(r['excluded']),1)
        row['row']='other_missing_row'
        with self.assertRaises(ValueError):evaluate(self.records()+[row])

if __name__=='__main__':unittest.main()
