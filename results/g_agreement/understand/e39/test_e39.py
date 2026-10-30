"""CPU checks of E39 scope, registered boundaries, admission and input lineage."""
from pathlib import Path
import copy
import json
import tempfile
import unittest
from unittest import mock
import contract as C
import analyze as A
import prepare_inputs as P


def cells():
    out=[]
    for row,arm in C.RUNS:
        values=[.5, .85, .9, .9, .9, .9, .9] if arm=='L' else [.5,.5,.5,.5,.85,.9,.9] if arm=='B' else [.5]*7
        out.append({'row':row,'arm':arm,'fast':arm=='L', 'asked':[{'step':s,'auroc':v,'ci95':[v-.05,v+.05]} for s,v in zip(C.CHECKPOINTS,values)]})
    return out


def set_curve(xs,row,arm,values,fast=False):
    c=next(c for c in xs if (c['row'],c['arm'])==(row,arm));c['fast']=fast
    for x,v in zip(c['asked'],values):x['auroc']=v


class RegisteredRules(unittest.TestCase):
    def test_all_interpretable_fast_and_l_faster(self):
        r=A.evaluate_rules(cells())
        self.assertTrue(r['R1prime']['met']);self.assertTrue(r['R3prime']['met'])
        self.assertEqual(r['R1prime']['n_interpretable'],16)
        self.assertEqual(r['R3prime']['ci95'],[-175.,-175.])
    def test_all_checkpoints_and_step0_exclusions(self):
        xs=cells();s=next(x for x in xs if (x['row'],x['arm'])==(C.STRUCTURE[0],'S'))
        s['asked'][-1]['auroc']=.60001
        set_curve(xs,C.STRUCTURE[1],'L',[.65001,.9,.9,.9,.9,.9,.9],True)
        r=A.evaluate_rules(xs);self.assertEqual(r['excluded_structure_rows'],list(C.STRUCTURE[:2]))
        s['asked'][-1]['auroc']=.60
        set_curve(xs,C.STRUCTURE[1],'L',[.65,.9,.9,.9,.9,.9,.9],True)
        self.assertEqual(A.evaluate_rules(xs)['R1prime']['n_interpretable'],16)
    def test_minimum_eight_and_sixty_percent(self):
        xs=cells()
        for row in C.STRUCTURE[10:]:set_curve(xs,row,'S',[.61]*7)
        for row in C.STRUCTURE[6:10]:next(c for c in xs if (c['row'],c['arm'])==(row,'L'))['fast']=False
        self.assertTrue(A.evaluate_rules(xs)['R1prime']['met'])
        next(c for c in xs if (c['row'],c['arm'])==(C.STRUCTURE[5],'L'))['fast']=False
        self.assertFalse(A.evaluate_rules(xs)['R1prime']['met'])
        for row in C.STRUCTURE[7:]:set_curve(xs,row,'S',[.61]*7)
        self.assertIsNone(A.evaluate_rules(xs)['R1prime']['met'])
    def test_clarified_both_censoring_strict_majority(self):
        xs=cells()
        for row in C.STRUCTURE[:8]:
            set_curve(xs,row,'L',[.5]*7);set_curve(xs,row,'B',[.5]*7)
        r=A.evaluate_rules(xs)['R3prime'];self.assertIsNotNone(r['met'])
        self.assertEqual(r['paired_rows'][0]['L_minus_B_steps'],0)
        set_curve(xs,C.STRUCTURE[8],'L',[.5]*7);set_curve(xs,C.STRUCTURE[8],'B',[.5]*7)
        self.assertEqual(A.evaluate_rules(xs)['R3prime']['not_evaluable_reason'],'more_than_half_both_censored')
    def test_l_only_censored_and_crossing_exactly800(self):
        xs=cells();row=C.STRUCTURE[0]
        set_curve(xs,row,'L',[.5]*7)
        r=A.evaluate_rules(xs)['R3prime']['paired_rows'][0]
        self.assertEqual(r['L_minus_B_steps'],600);self.assertTrue(r['L_censored'])
        set_curve(xs,row,'L',[.5]*6+[.8])
        self.assertFalse(A.evaluate_rules(xs)['R3prime']['paired_rows'][0]['L_censored'])
    def test_semantic_excluded_from_confirmatory_denominator(self):
        xs=cells()
        for row in C.SEMANTIC:set_curve(xs,row,'L',[.99]*7,False)
        self.assertEqual(A.evaluate_rules(xs)['R1prime']['n_interpretable'],16)
    def test_missing_cell_and_bad_checkpoint_rejected(self):
        with self.assertRaises(ValueError):A.evaluate_rules(cells()[:-1])
        xs=cells();xs[0]['asked'].pop()
        with self.assertRaises(ValueError):A.evaluate_rules(xs)


class ScopeBudget(unittest.TestCase):
    def test_exact_registration_and_partition(self):
        C.validate_plan(C.plan());self.assertEqual(C.SEMANTIC,('json_status','latex_role'))
        self.assertEqual(len(C.RUNS),54)
        for n in range(1,7):
            flat=[tuple(x) for i in range(n) for x in C.assigned_runs(i,n)]
            self.assertEqual(len(flat),54);self.assertEqual(set(flat),set(C.RUNS))
        for key,value in [('steps',400),('seed',20261025),('rank',16),('total_gpu_seconds',54001)]:
            p=C.plan();p[key]=value
            with self.assertRaises(ValueError):C.validate_plan(p)
    def test_800_paired_schedules_and_fixed_shuffle(self):
        rows=[{'id':str(i),'feature':C.ROWS[0],'y':i%2,'cluster':str(i//14)} for i in range(84)]
        l=C.training_schedule(rows,C.ROWS[0],'L');b=C.training_schedule(rows,C.ROWS[0],'B');s=C.training_schedule(rows,C.ROWS[0],'S')
        self.assertEqual(l,b);self.assertEqual(len(l),800);self.assertTrue(all(len(x)==8 for x in l))
        self.assertEqual([[x['id'] for x in batch] for batch in l],[[x['id'] for x in batch] for batch in s])
        self.assertNotEqual(l,s);self.assertEqual(s,C.training_schedule(rows,C.ROWS[0],'S'))
    def forecasts(self):
        return [{'slot':i,'pod_count':6,'previous_gpu_seconds':0,'allocated_gpu_seconds':9000,
            'plan_sha256':C.sha(C.HERE/'PLAN.json'),'status':'WARMED_FORECAST',
            'forecast_remaining_seconds':4000,'setup_elapsed_seconds':600,'elapsed_provider_seconds':1000,
            'elapsed_science_seconds':400,'forecast_sha256':str(i)} for i in range(6)]
    def test_six_pod_cap_and_real_elapsed_setup(self):
        fs=self.forecasts();r=C.admit(fs);self.assertEqual(r['status'],'ADMIT_FULL_GRID');self.assertEqual(r['total_experiment_reserved_gpu_seconds'],54000)
        fs[0]['forecast_remaining_seconds']=7000
        self.assertEqual(C.admit(fs)['status'],'NO_FIT_STOP')
        fs=self.forecasts();fs[0]['allocated_gpu_seconds']=9001
        with self.assertRaises(ValueError):C.admit(fs)
        fs=self.forecasts();fs[0]['elapsed_provider_seconds']=8500
        self.assertEqual(C.admit(fs)['status'],'NO_FIT_STOP')
        with self.assertRaises(ValueError):C.admit(self.forecasts()[:-1])
    def test_late_admission_never_resets_budget(self):
        self.assertFalse(C.full_scope_still_fits(600,1000,1100,500))
        self.assertTrue(C.full_scope_still_fits(400,1000,1100,500))


class PreparedInputs(unittest.TestCase):
    def test_original_e28_parity_payload_with_new_v2_input(self):
        import worker as W
        a={'parity_input_seal_sha256':C.read(C.HERE/'PARITY_PREPARATION_2026-10-25.json')['parity_input_seal_sha256'],
           'input_seal_sha256':'different-v2-input'}
        items,labels,templates,acts,reference=W.parity_inputs(C.ROOT/'cache/g_agreement/understand/e28-parity-v1',a)
        self.assertEqual(len(items),252);self.assertEqual(acts.shape,(252,5120))
        self.assertEqual(reference['max_abs_auroc_delta'],.03)

    def test_stage_source_pins_and_semantic_selection(self):
        stage=C.ROOT/'cache/g_agreement/understand/e39-stage-v1'
        C.verify(stage,'STAGE_SEAL.json');dev=C.rows(stage/'dev.jsonl');test=C.rows(stage/'test.jsonl')
        self.assertEqual(len(dev),1512);self.assertEqual(len(test),1512)
        self.assertTrue(all(set(x)=={'id','feature'} for x in test))
        templates=C.read(stage/'templates.json')
        self.assertEqual(set(templates),set(C.ROWS))
        self.assertEqual(C.read(stage/'provenance.json')['source_bank_seal'],P.BANK_SEAL)
    def test_empty_captures_cannot_prepare_or_launch(self):
        stage=C.ROOT/'cache/g_agreement/understand/e39-stage-v1'
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'3024'):
                P.prepare(stage,[],Path(tmp)/'cache/out')
            self.assertFalse((Path(tmp)/'cache/out').exists())


if __name__=='__main__':unittest.main()
