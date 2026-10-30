import copy
import unittest
from adapter import gate, describe, FORECAST


def fixture():
    b=dict(experiment='E98',status='FINAL_BOUND',forecast_sha256=FORECAST,
           final_binding_committed=True,adapter_committed_before_judging_seal=True,
           capture_seal_sha256='c',input_seal_sha256='i',native_seal_sha256='n',
           judgment_seal_sha256='j',rubric_sha256='r',original_qwen_metrics_sealed=True,
           normalized_files_verified=True)
    n=dict(experiment='E98',status='COMPLETE',items=2184,unique_items=2184,
           capture_seal_sha256='c',input_seal_sha256='i',sha256='n')
    j=dict(n,sha256='j',native_seal_sha256='n',rubric_sha256='r',terminal=True)
    return b,n,j


class Tests(unittest.TestCase):
    def test_gate(self): self.assertTrue(gate(*fixture()))
    def test_incomplete_or_wrong_lineage(self):
        for field,value in [('status','FAILED'),('items',2183),('unique_items',2183),('capture_seal_sha256','other'),('native_seal_sha256','other'),('rubric_sha256','other'),('terminal',False)]:
            b,n,j=fixture();j[field]=value
            with self.assertRaises(ValueError): gate(b,n,j)
    def test_uncommitted_or_forecast_changed(self):
        for field,value in [('forecast_sha256','other'),('final_binding_committed',False),('adapter_committed_before_judging_seal',False),('normalized_files_verified',False),('original_qwen_metrics_sealed',False)]:
            b,n,j=fixture();b[field]=value
            with self.assertRaises(ValueError): gate(b,n,j)
    def test_grid_failure_before_statistics(self):
        with self.assertRaises(ValueError): describe([],{}, {}, {'rows':[]}, {})
    def test_full_synthetic_grid_and_nonbinary_retention(self):
        units=[]; judgments={}; native={}; qwen={}; forecasts=[]
        for row in range(26):
            binary=row<23; key='E57|synthetic_'+str(row)
            u=dict(bank='E57',row='synthetic_'+str(row),binary=binary,items=[])
            qwen[key]={'S':0.5,'source':'SYNTHETIC'}
            if binary: forecasts.append(dict(bank=u['bank'],row=u['row'],oracle_prediction='REPORTED'))
            for i in range(84):
                k=str(row)+'_'+str(i); label=i%2
                u['items'].append(dict(id=k,label=label))
                native[k]='A' if label else 'B'
                judgments[k]=dict(id=k,category='states_value',values=[native[k]],evidence=native[k])
            units.append(u)
        out=describe(units,judgments,native,{'rows':forecasts},qwen)
        self.assertEqual(len(out['rows']),26)
        self.assertEqual(sum(r['J_agrees'] is True for r in out['rows']),23)
        self.assertEqual(sum(r['S'] is None for r in out['rows']),3)
        self.assertTrue(all(r['S']['S']==1 for r in out['rows'] if r['binary']))
        judgments.pop('0_0')
        with self.assertRaises(ValueError): describe(units,judgments,native,{'rows':forecasts},qwen)

    def test_count_only_original_objects_without_fake_categories(self):
        units=[];judgments={};native={};qwen={};forecast=[];counts={}
        names=['binary_'+str(i) for i in range(23)]+['capacity_list','category_switch','focus_none']
        for i,name in enumerate(names):
            binary=i<23;u=dict(bank='E57',row=name,binary=binary,items=[])
            qwen['E57|'+name]={'source':'SYNTHETIC'}
            if binary:forecast.append(dict(bank='E57',row=name,oracle_prediction='REPORTED'))
            for j in range(84):
                k=name+'_'+str(j);u['items'].append(dict(id=k,label=j%2));native[k]='A' if j%2 else 'B'
                if name in ('capacity_list','category_switch'):
                    counts[k]=dict(id=k,measurement=dict(original_count=j,source='SYNTHETIC'))
                else:judgments[k]=dict(id=k,category='states_value',values=[native[k]],evidence=native[k])
            units.append(u)
        out=describe(units,judgments,native,{'rows':forecast},qwen,counts)
        cr=[r for r in out['rows'] if 'registered_count_measurements' in r]
        self.assertEqual(sum(len(r['registered_count_measurements']) for r in cr),168)
        self.assertTrue(all(r['S'] is None and r['J_agrees'] is None for r in cr))
        self.assertEqual({x['id']:x for r in cr for x in r['registered_count_measurements']},counts)
        focus=next(r for r in out['rows'] if r['row']=='focus_none')
        self.assertEqual(len(focus['registered_mention_judgments']),84)
        for mutation in ('missing','overlap','wrong_id','binary_routing','focus_unjudged'):
            c=copy.deepcopy(counts);j=copy.deepcopy(judgments);us=copy.deepcopy(units)
            if mutation=='missing':c.pop(next(iter(c)))
            elif mutation=='overlap':j[next(iter(c))]=dict(id=next(iter(c)))
            elif mutation=='wrong_id':c[next(iter(c))]['id']='other'
            elif mutation=='binary_routing':us[23]['binary']=True
            else:j.pop('focus_none_0')
            with self.assertRaises(ValueError):describe(us,j,native,{'rows':forecast},qwen,c)

    def test_distinct_native_and_judge_packet_inputs(self):
        b,n,j=fixture();b['judge_packet_input_sha256']='packet';j['input_seal_sha256']='packet'
        self.assertTrue(gate(b,n,j))
        j['input_seal_sha256']='i'
        with self.assertRaises(ValueError):gate(b,n,j)

    def test_old_rubric_matched_subset_and_nonbinary(self):
        from runner import old_sensitivity
        u=[dict(bank='E57',row='binary',binary=True,items=[dict(id='a',label=1),dict(id='b',label=0)]),dict(bank='E57',row='focus_none',binary=False,items=[dict(id='c',label=None)])]
        n={'a':'A','b':'B','c':'none'}
        p={'a':dict(id='a',category='states_value',values=['A'],evidence='A'),'b':dict(id='b',category='states_value',values=['B'],evidence='B'),'c':dict(id='c',category='silent',values=[],evidence='')}
        old=[dict(id='a',category='UNPARSEABLE',values=[],evidence=''),p['c']]
        out=old_sensitivity(u,p,old,n,['a','c'])
        self.assertEqual(out['items'],2);self.assertEqual(out['rows'][0]['primary']['S'],1)
        self.assertIsNone(out['rows'][0]['original']['S']);self.assertIsNone(out['rows'][1]['original'])
        with self.assertRaises(ValueError):old_sensitivity(u,p,old,n,['a','b'])

    def test_missingness_and_sign_unchanged(self):
        from adapter import rate, signed_value, reported
        self.assertIsNone(signed_value({'category':'UNPARSEABLE'},1))
        self.assertEqual(signed_value({'category':'states_value','values':['B']},1),-1)
        self.assertEqual(signed_value({'category':'states_value','values':['A','B']},1),0)
        r=rate([[None],[1],[-1]])
        self.assertEqual(r['S'],0);self.assertEqual(r['items'],2);self.assertFalse(reported(r))
        self.assertIsNone(rate([[None]])['S'])

if __name__ == '__main__': unittest.main()
