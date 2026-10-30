import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from projects.g_agreement.r_bench import remainder_r6 as R


def fixture():
    rows=[]
    for case in R.CASES:
        for i in range(20):
            for arm in ('focal','control'):
                iid=f'{case}-{i}-{arm}'
                rows.append({'case':case,'pair_id':f'{case}-{i}','arm':arm,'item_id':iid,'dataset':case,'corpus':case,
                    'capture_text':'Example source.','prompt_text':'Example source.','candidates':['positive','negative'],'label':1,
                    'states':{str(L):{'kind':'natural','path':f'{iid}_{L}.npy','index_path':f'{iid}.json','item_id':iid,'layer':L} for L in (42,44,56)},
                    'model_key':{'choice':False},'edited_report_pos':False})
    return rows


def rated_fixture():
    manifest=fixture();rows=R.jobs(manifest)
    grade={'grammaticality':'neither','final_period':'absent','candidate':'neither','confidence':'neither'}
    double={r['gen_id'] for r in R.double_sample(rows)}
    return manifest,[{**r,'mock':False,'text':'report','rating1':dict(grade),
                     **({'rating2':dict(grade)} if r['gen_id'] in double else {})} for r in rows]


class RemainderR6Tests(unittest.TestCase):
    def test_five_cell_grid_and_decode_profiles(self):
        rows=R.jobs(fixture());self.assertEqual(len(rows),4000)
        self.assertEqual(len(R.jobs(fixture(),'r3-sampling')),6400)
        self.assertEqual({(r['reader'],r['layer']) for r in rows},set(R.CELLS))
        self.assertEqual({r['mode'] for r in R.jobs(fixture(),'r3-sampling')},{'sample'})
        self.assertEqual({r['sample_idx'] for r in R.jobs(fixture(),'r3-sampling')},set(range(8)))
        self.assertEqual(len({r['gen_id'] for r in rows}),4000)
        self.assertEqual(R.jobs(fixture())[0]['seed'],rows[0]['seed'])

    def test_smoke_requires_every_live_arm_site_mode(self):
        rows=[{**r,'text':'a report'} for r in R.jobs(fixture(),smoke=True)]
        self.assertEqual(R.assert_coverage(rows),80)
        with self.assertRaisesRegex(RuntimeError,'SMOKE FAILED'):
            R.assert_coverage([r for r in rows if not (r['case']=='C4' and r['arm']=='control' and r['layer']==56 and r['reader']=='nla')])
        with self.assertRaisesRegex(RuntimeError,'SMOKE FAILED'):
            R.assert_coverage([{**r,'text':''} for r in rows])

    def test_original_r5_never_falls_back_to_natural(self):
        item={'dataset':'fact','item_id':'i'}
        ref=R.r5_ref(item,44,'d_olens_L38',.5)
        self.assertEqual(ref['kind'],'r5_original');self.assertIn('readback_L44',ref['path'])
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=root/R.natural_ref(item,44)['path'];p.parent.mkdir(parents=True);np.save(p,np.ones((1,4)))
            (p.parent/'index.json').write_text(json.dumps({'item_ids':['i']}))
            self.assertFalse(R.state_status(ref,root)['ok'])

    def test_majority_key_validates_coverage_and_no_fallback(self):
        items={'a':{'dataset':'f','label':1,'split':'test'},'b':{'dataset':'f','label':0,'split':'test'}}
        rows=[{'item_id':'a','dataset':'f','label':1,'n_votes':3,'key_model_pos':False,'stable':False,'frozen_model_pos':True}]
        keys,audit=R.majority_keys(rows,items,{'a':{'choice':True}})
        self.assertFalse(keys['a']['choice']);self.assertFalse(keys['a']['stable']);self.assertNotIn('b',keys)
        self.assertEqual(audit['missing_test_keys'],['b']);self.assertFalse(audit['complete_test_coverage'])
        with self.assertRaisesRegex(ValueError,'duplicate'):R.majority_keys(rows+rows,items,{})
        with self.assertRaisesRegex(ValueError,'mismatch'):R.majority_keys(rows,items,{'a':{'choice':False}})

    def test_capture_context_reports_the_actual_truncation(self):
        class Tokenizer:
            def __call__(self,text,**kwargs):return {'input_ids':list(text)}
            def decode(self,ids):return ''.join(ids)
        r=R.capture_context({'prompt_text':'a'*300+'.'},Tokenizer())
        self.assertTrue(r['capture_truncated']);self.assertFalse(r['capture_final_period'])
        self.assertEqual(r['capture_text'],'a'*256)

    def test_state_index_and_finiteness_checked(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);ref={'path':'h.npy','index_path':'idx.json','item_id':'b','layer':42}
            np.save(root/'h.npy',np.array([[1.,2.],[3.,4.]]));(root/'idx.json').write_text(json.dumps({'item_ids':['a','b']}))
            np.testing.assert_array_equal(R.load_vector(ref,root),[3.,4.])
            (root/'idx.json').write_text(json.dumps({'item_ids':['b','b']}))
            self.assertFalse(R.state_status(ref,root)['ok'])
            (root/'idx.json').write_text(json.dumps({'item_ids':['a','b']}));np.save(root/'h.npy',[[1.,2.],[float('nan'),4.]])
            self.assertFalse(R.state_status(ref,root)['ok'])

    def test_judge_payload_blinds_roles_and_validates_evidence(self):
        row={**fixture()[0],'reader':'olens','layer':42,'text':'This is ungrammatical.'}
        payload=R.judge_payload(row)
        user=json.loads(payload['user']);self.assertEqual(set(user),{'source_text','candidate_A','candidate_B','report'})
        self.assertNotIn('arm',user);self.assertNotIn('label',user)
        answer={'grammaticality':'ungrammatical','final_period':'absent','candidate':'neither','confidence':'asserted','evidence':'ungrammatical'}
        calls=[]
        def transport(p):
            calls.append(p)
            return {'choices':[{'message':{'content':json.dumps(answer)}}]}
        self.assertEqual(R.judge_one(row,transport)['grammaticality'],'ungrammatical');self.assertEqual(len(calls),1)
        answer['evidence']='not in report'
        with self.assertRaisesRegex(ValueError,'evidence'): R.judge_one(row,transport)

    def test_double_rating_has100_no_missing_case_padding(self):
        rows=[{**r,'text':'example'} for r in R.jobs(fixture())]
        selected=R.double_sample(rows)
        self.assertEqual(len(selected),100)
        self.assertEqual({c:sum(r['case']==c for r in selected) for c in R.CASES},{c:25 for c in R.CASES})
        with self.assertRaisesRegex(ValueError,'requires25'):R.double_sample([r for r in rows if r['case']!='C4'])

    def test_ratings_require_complete_population_and_identity(self):
        manifest,rows=rated_fixture()
        self.assertTrue(R.validate_ratings(rows,manifest)['complete'])
        without_cell=[r for r in rows if not (r['case']=='C4' and r['reader']=='olens' and r['layer']==56 and r['arm']=='control')]
        with self.assertRaisesRegex(ValueError,'incomplete judged population'):R.validate_ratings(without_cell,manifest)
        with self.assertRaisesRegex(ValueError,'duplicate judged'):R.validate_ratings(rows+[rows[0]],manifest)
        changed=[dict(r) for r in rows];changed[0]['sample_idx']=999
        with self.assertRaisesRegex(ValueError,'metadata mismatch'):R.validate_ratings(changed,manifest)
        with self.assertRaisesRegex(ValueError,'complete20-pair'):R.validate_ratings(rows,manifest[:-1])

    def test_ratings_require_exact_frozen_double_set(self):
        manifest,rows=rated_fixture();changed=[dict(r) for r in rows]
        old=next(r for r in changed if 'rating2' in r);new=next(r for r in changed if 'rating2' not in r)
        new['rating2']=old.pop('rating2')
        self.assertEqual(sum('rating2' in r for r in changed),100)
        with self.assertRaisesRegex(ValueError,'frozen100'):R.validate_ratings(changed,manifest)

    def test_ratings_reject_mock_and_missing_first_rating(self):
        manifest,rows=rated_fixture();changed=[dict(r) for r in rows];changed[0]['mock']=True
        with self.assertRaisesRegex(ValueError,'mock reports'):R.validate_ratings(changed,manifest)
        changed=[dict(r) for r in rows];changed[0].pop('rating1')
        with self.assertRaisesRegex(ValueError,'invalid rating1'):R.validate_ratings(changed,manifest)

    def test_effect_pairing_and_kappa(self):
        rows=[]
        for r in R.jobs(fixture()):
            grade={'grammaticality':'ungrammatical' if r['arm']=='focal' else 'grammatical','final_period':'explicit' if r['arm']=='focal' else 'absent',
                'candidate':'B' if r['arm']=='focal' else 'A','confidence':'asserted'}
            rows.append({**r,'rating1':grade,'rating2':grade})
        effect=R.effects(rows,n_boot=20)
        self.assertEqual(len(effect),40)
        self.assertTrue(all(x['estimate']==1 and x['wider_ci']==[1.,1.] for x in effect))
        self.assertEqual(R.kappa(['a','b'],['a','b']),1)
        self.assertEqual(R.kappa(['a','b'],['b','a']),-1)
        self.assertIsNone(R.kappa(['a','a'],['a','a']))
        bad=[r for r in rows if r['arm']=='focal']
        with self.assertRaisesRegex(ValueError,'missing paired'):R.effects(bad,n_boot=2)

    def test_preflight_and_pod_identity_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(RuntimeError,'PREFLIGHT BLOCKED'):R.preflight(fixture(),Path(d))
        with self.assertRaisesRegex(RuntimeError,'pod'):R.check_pod('not-the-pod')

    def test_shared_guards_and_immutable_deadline(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with self.assertRaisesRegex(RuntimeError,'receipt/ARMED'): R.verify_guards('pod','r6',root,100)
            receipt={'pod':'pod','experiment':'r6','started_epoch':100,'deadline_epoch':1300}
            (root/'guard.json').write_text(json.dumps(receipt));(root/'ARMED').touch()
            for name in ('watchdog','hardstop'):
                (root/f'{name}.pid').write_text(str(os.getpid()));(root/f'{name}.log').write_text('armed: fixture')
            self.assertEqual(R.verify_guards('pod','r6',root,200)['deadline_epoch'],1300)
            with self.assertRaisesRegex(RuntimeError,'mismatch'):R.verify_guards('pod','r3',root,200)
            with self.assertRaisesRegex(RuntimeError,'expired'):R.verify_guards('pod','r6',root,1190)
            (root/'watchdog.log').write_text('')
            with self.assertRaisesRegex(RuntimeError,'not armed'):R.verify_guards('pod','r6',root,200)
            (root/'watchdog.log').write_text('armed: fixture');(root/'watchdog.pid').write_text('0')
            with self.assertRaisesRegex(RuntimeError,'not alive'):R.verify_guards('pod','r6',root,200)

    def test_controls_not_reused_and_hash_order_stable(self):
        item={'dataset':'f','label':1,'item_id':'a','prompt_text':'five!'}
        candidates=[{'dataset':'f','label':1,'item_id':i,'prompt_text':'test!'} for i in ('b','c')]
        used=set();first=R.match_control(item,candidates,used,'C1');second=R.match_control(item,candidates,used,'C1')
        self.assertNotEqual(first['item_id'],second['item_id']);self.assertIsNone(R.match_control(item,candidates,used,'C1'))
        self.assertEqual(R.round_robin(candidates,2,'C1'),R.round_robin(list(reversed(candidates)),2,'C1'))

if __name__=='__main__':unittest.main()

class AvailableCohortTests(unittest.TestCase):
    def test_frozen_cohort_never_pads_or_reselects(self):
        full=fixture();full=[r for r in full if not (r['case']=='C1' and int(r['pair_id'].split('-')[1])>=13)]
        full=[r for r in full if not (r['case']=='C2' and r['arm']=='control' and int(r['pair_id'].split('-')[1])>=16)]
        paired=[r for r in full if not (r['case']=='C2' and int(r['pair_id'].split('-')[1])>=16)]
        with patch.object(R,'FROZEN_FULL_ID_SHA',R.cohort_identity(full)),patch.object(R,'FROZEN_AVAILABLE_ID_SHA',R.cohort_identity(paired)):
            actual=R.available_cohort(full)
            self.assertEqual(R.population_counts(actual,True),R.AVAILABLE_COUNTS)
            self.assertEqual(len(R.jobs(actual)),3450);self.assertEqual(len(R.jobs(actual,'r3-sampling')),5520)
            with self.assertRaisesRegex(ValueError,'complete20'):R.population_counts(actual)
            changed=[dict(r) for r in actual];changed[0]['item_id']='replacement'
            with self.assertRaisesRegex(ValueError,'frozen'):R.available_cohort(changed)
            jobs=R.jobs(actual);double={r['gen_id'] for r in R.double_sample(jobs)}
            grade={'grammaticality':'neither','final_period':'absent','candidate':'neither','confidence':'neither'}
            rated=[{**r,'text':'report','rating1':grade,**({'rating2':grade} if r['gen_id'] in double else {})} for r in jobs]
            self.assertEqual(R.validate_ratings(rated,actual,available=True)['expected_reports'],3450)
            self.assertFalse(R.validate_ratings(rated,actual,available=True)['original_target_met'])
            with self.assertRaisesRegex(ValueError,'incomplete judged'):R.validate_ratings(rated[:-1],actual,available=True)

    def test_replay_requires_explicit_permission_and_passed_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);ref={'kind':'r5_replay','path':'h.npy','index_path':'idx.json','item_id':'i','layer':42,'recovery_receipt':'receipt.json'}
            np.save(root/'h.npy',np.ones((1,3)));(root/'idx.json').write_text(json.dumps({'item_ids':['i'],'read_layer':42}))
            receipt={'complete_pass':True,'source_identity_sha':R.FROZEN_FULL_ID_SHA};(root/'receipt.json').write_text(json.dumps(receipt))
            ref['recovery_receipt_sha']=R.sha(root/'receipt.json')
            row={**fixture()[0],'states':{'42':ref}}
            self.assertTrue(any('explicit' in e for e in R.preflight([row],root,strict=False)))
            self.assertFalse(any('replay' in e for e in R.preflight([row],root,strict=False,allow_recaptured=True)))
            (root/'receipt.json').write_text('{}')
            self.assertTrue(any('receipt' in e for e in R.preflight([row],root,strict=False,allow_recaptured=True)))


class JointR6Tests(unittest.TestCase):
    def test_joint_generation_rejects_parked_or_unfrozen_profile_before_output(self):
        for profile,available,recovered in [('r3-sampling',True,True),('r6',False,True),('r6',True,False)]:
            with self.assertRaisesRegex(RuntimeError,'joint job requires'):
                R.generate([],profile,'pod',4200,mock=True,available=available,allow_recaptured=recovered,joint_run=True)

    def test_joint_verification_requires_original_guard_and_mac_checkpoint(self):
        from projects.g_agreement.r_bench import remainder_joint as J
        with tempfile.TemporaryDirectory() as d:
            run=Path(d);receipt={'pod':'pod','experiment':'r2_r6','started_epoch':100,'deadline_epoch':5500}
            (run/'guard.json').write_text(json.dumps(receipt))
            with patch.object(J,'guard',return_value=receipt) as guard,patch.object(J,'require_r2_checkpoint') as checkpoint:
                g=R.verify_guards('pod','r6',run,joint_run=True)
                self.assertEqual(g['started_epoch'],100);self.assertEqual(g['deadline_epoch'],5500)
                self.assertEqual(g['receipt_sha'],R.sha(run/'guard.json'))
                guard.assert_called_once_with('pod',run)
                checkpoint.assert_called_once_with('pod',run,g=receipt)
                checkpoint.side_effect=ValueError('R2 Mac checkpoint missing')
                with self.assertRaisesRegex(ValueError,'checkpoint missing'):
                    R.verify_guards('pod','r6',run,joint_run=True)
                guard.side_effect=ValueError('invalid joint guard')
                with self.assertRaisesRegex(ValueError,'invalid joint guard'):
                    R.verify_guards('pod','r6',run,joint_run=True)
                with self.assertRaisesRegex(RuntimeError,'parked'):
                    R.verify_guards('pod','r3',run,joint_run=True)
            with self.assertRaisesRegex(RuntimeError,'receipt/ARMED'):
                R.verify_guards('pod','r6',run)

    def test_standalone_generation_cannot_use_joint_duration(self):
        with tempfile.TemporaryDirectory() as d, patch.object(R,'CACHE',Path(d)),patch.object(R,'provenance',return_value={}):
            with self.assertRaisesRegex(RuntimeError,'1200-second cap'):
                R.generate([],'r6','pod',4200,smoke=True)
            for budget in (300,5401,float('nan'),float('inf'),True):
                with self.assertRaisesRegex(RuntimeError,'5400-second cap'):
                    R.generate([],'r6','pod',budget,smoke=True,joint_run=True,available=True,allow_recaptured=True)
