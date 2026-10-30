import unittest
from analysis import signed, rate, rule, bound_rule, analyze, normalize_source_polarity

def row(k, oracle, text, bounds=None):
    return dict(key=k, oracle_S=oracle,S=text,S_missing_bounds=bounds or [text,text])

class Tests(unittest.TestCase):
    def test_a_b_label_orientation(self):
        for label,value in [(1,'A'),(0,'B')]:
            self.assertEqual(signed(dict(category='states_value',values=[value]),label),1)
            self.assertEqual(signed(dict(category='states_value',values=['B' if value=='A' else 'A']),label),-1)
    def test_both_and_exhibits_zero(self):
        self.assertEqual(signed(dict(category='states_value',values=['A','B']),1),0)
        self.assertEqual(signed(dict(category='exhibits',values=[]),1),0)
    def test_missing_not_silent(self):
        x=rate([1,None,0,-1,None]);self.assertEqual(x['kept'],3);self.assertEqual(x['missing'],2)
        self.assertEqual(x['S_missing_bounds'],[-.4,.4])
    def test_all_missing(self):
        x=rate([None]*10);self.assertIsNone(x['S']);self.assertEqual(x['S_missing_bounds'],[-1,1])
    def test_bootstrap_deterministic(self):
        self.assertEqual(rate([1,0,-1]*20),rate([1,0,-1]*20))
    def test_inclusive_thresholds_and_exact_80_50(self):
        rs=[row(str(i),.1,.1 if i<4 else .2) for i in range(5)]+[row('a',.2,.2),row('b',.2,.11)]
        self.assertTrue(rule(rs)['R_T1_conditions_met']);self.assertFalse(rule(rs)['channel_insensitive_falsifier'])
    def test_falsifier_90_including_reported(self):
        rs=[row(str(i),.1 if i<5 else .2,0 if i<9 else .3) for i in range(10)]
        self.assertEqual(rule(rs)['status'],'NOT_EVALUABLE_CHANNEL_INSENSITIVE')
    def test_empty_stratum_not_vacuous_pass(self):
        self.assertFalse(rule([row('x',0,0)])['R_T1_conditions_met'])
    def test_joint_bounds_opposite_directions(self):
        rs=[row('miss',0,0,[-.5,.5]),row('report',.5,.5,[0,1])]
        x=bound_rule(rs);self.assertTrue(x['R_T1_conditions_possible']);self.assertFalse(x['R_T1_conditions_definite'])
    def test_middle_oracle_rows_only_falsifier_denominator(self):
        r=rule([row('m',0,0),row('r',1,1),row('middle',.15,0)])
        self.assertEqual(r['all_rows'],3);self.assertEqual(r['oracle_missed_rows'],1);self.assertEqual(r['oracle_reported_rows'],1)
    def test_secondary_cannot_change_primary_and_missing_preserved(self):
        js=[];xs=[]
        for arm in ('generic','oracle_wording'):
            for i,o in enumerate([0,.5]):
                ident=arm+str(i);js.append(dict(id=ident,bank='b',row=str(i),arm=arm,source_id=str(i),label=1))
                xs.append(dict(id=ident,status='KEPT',code=dict(id=ident,category='states_value' if arm=='oracle_wording' or i else 'silent',values=['A'] if arm=='oracle_wording' or i else [])))
        b={f'b/{i}':dict(S=o,source_kind='synthetic') for i,o in enumerate([0,.5])}
        d=analyze(js,xs,xs,b);self.assertEqual(d['primary_verdict'],'MET');self.assertEqual(d['arms']['oracle_wording']['rule']['status'],'NOT_MET')
        with self.assertRaises(AssertionError):analyze(js,xs+xs[:1],xs,b)
        with self.assertRaises(AssertionError):analyze(js,xs[:-1],xs,b)
    def test_e73_opposite_label_polarity_bound_to_original_key(self):
        js=[dict(id='a',bank='e73',source_id='source',row='W7',label=1)]
        keys={'source':dict(label=1,state='W7',value='B')}
        normalized=normalize_source_polarity(js,keys)
        self.assertEqual(normalized[0]['label'],0)
        self.assertEqual(js[0]['label'],1)
        self.assertEqual(signed(dict(category='states_value',values=['B']),normalized[0]['label']),1)
        with self.assertRaises(AssertionError):normalize_source_polarity(js,{'source':dict(label=1,state='W7',value='A')})
    def test_invalid_values_fail_closed(self):
        with self.assertRaises(AssertionError):signed(dict(category='silent',values=['A']),1)
        with self.assertRaises(AssertionError):signed(dict(category='states_value',values=['C']),1)

if __name__=='__main__':unittest.main()
