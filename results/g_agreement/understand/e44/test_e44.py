import copy
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch,MagicMock
import numpy as np
import contract as C
import worker as W
import analyze as A
import analysis_once_2026_10_26 as O

class Contracts(unittest.TestCase):
    def dev(self):return [{'id':f+'-'+str(i),'feature':f,'y':i%2,'cluster':str(i//14)} for f in C.CONTENT for i in range(84)]
    def test_pooled_schedule_content_only_deterministic_and_complete(self):
        dev=self.dev();s=C.training_schedule(dev)
        self.assertEqual(s,C.training_schedule(dev));self.assertEqual(len(s),400)
        flat=[x for b in s for x in b];self.assertEqual(len(flat),3200)
        self.assertEqual(len({x['id'] for x in flat[:756]}),756)
        self.assertEqual({x['feature'] for x in flat},set(C.CONTENT))
        self.assertEqual([x['phrasing'] for x in flat],[i%2 for i in range(3200)])
        dev[0]['feature']=C.STRUCTURE[0]
        with self.assertRaises(ValueError):C.training_schedule(dev)
    def test_rule_thresholds_and_no_extra_ci_condition(self):
        curves={r:{s:.5 for s in C.CHECKPOINTS} for r in C.ROWS};eligible=list(C.STRUCTURE[:8])
        for r in C.CONTENT:curves[r][400]=.9
        for r in eligible[:4]:curves[r][100]=.8
        for r in eligible[:4]:curves[r][400]=.8
        result=A.evaluate_rules(curves,eligible);self.assertTrue(result['R1']['met']);self.assertFalse(result['R2']['met'])
        curves[eligible[0]][400]=.65;self.assertTrue(A.evaluate_rules(curves,eligible)['R2']['met'])
        self.assertIsNone(A.evaluate_rules(curves,eligible[:7])['R1']['met'])
        for r in C.CONTENT:curves[r][400]=.8999
        self.assertIsNone(A.evaluate_rules(curves,eligible)['R2']['met'])
    def test_eligibility_uses_sealed_E39_rows_and_excludes_failed_shuffle(self):
        oldrows=list(C.STRUCTURE)+list(C.CONTENT[:2]);cells=[]
        for row in oldrows:
            for arm in ('L','B','S'):
                cells.append({'row':row,'arm':arm,'asked':[{'step':s,'auroc':.5} for s in (0,25,50,100,200,400,800)]})
        ref={'experiment':'E39','status':'COMPLETE_ANALYSIS','cells':cells,
             'row_eligibility':{r:{'interpretable':True} for r in oldrows}}
        self.assertEqual(A.eligibility(ref),list(C.STRUCTURE))
        row=C.STRUCTURE[0];next(x for x in cells if x['row']==row and x['arm']=='S')['asked'][-1]['auroc']=.60001
        ref['row_eligibility'][row]['interpretable']=False
        self.assertNotIn(row,A.eligibility(ref))
        ref['row_eligibility'][row]['interpretable']=True
        with self.assertRaises(ValueError):A.eligibility(ref)

    def test_forecast_charges_elapsed_and_no_fit(self):
        f={'forecast_remaining_seconds':1000,'science_started_epoch':100,'provider_deadline_epoch':4000}
        self.assertEqual(C.forecast_admission(f,200)['status'],'ADMIT_FULL_GRID')
        f['provider_deadline_epoch']=1700;self.assertEqual(C.forecast_admission(f,200)['status'],'NO_FIT_STOP')
    def test_once_failure_is_claimed_without_retry(self):
        with tempfile.TemporaryDirectory() as d,patch.object(O,'CLAIM',Path(d)/'CLAIM.json'),patch.object(O,'STATUS',Path(d)/'STATUS.json'),patch.object(O,'preflight',side_effect=ValueError),patch.object(O,'execute') as invoke:
            self.assertEqual(O.run_once(),2);self.assertEqual(O.run_once(),3);invoke.assert_not_called()
    def test_bound_pool_and_reference_tensors(self):
        p=C.ROOT/'cache/g_agreement/understand/e44-bound-v1/input';C.verify(p)
        self.assertEqual(len(C.rows(p/'dev.jsonl')),756);self.assertEqual(len(C.rows(p/'test.jsonl')),2100)
        self.assertEqual({r['feature'] for r in C.rows(p/'dev.jsonl')},set(C.CONTENT))
        self.assertTrue(C.read(p/'provenance.json')['shared_e39_tensors_bit_exact'])

class SyntheticWorker(unittest.TestCase):
    dev=Contracts.dev
    def test_400_steps_four_complete_checkpoints_and_parity_first(self):
        import torch
        dev=self.dev();test=[{'id':f+'-'+str(i),'feature':f} for f in C.ROWS for i in range(84)]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'cache';root.mkdir();env=root/'environment.json';C.dump(env,{})
            assign={'issuer':'integrator','experiment':'E44','pod_id':'synthetic','pod_count':1,'slot':0,'runs':[['pooled_content','C']],
                'plan_sha256':C.sha(C.HERE/'PLAN.json'),'target_mapping_sha256':C.sha(C.HERE/'LORA_TARGETS.json'),
                'source_published':True,'external_hardstop_verified':True,'allocated_gpu_seconds':14400,'previous_gpu_seconds':0,
                'provider_created_epoch':1000,'deadline_epoch':15400,'training_environment_sha256':C.sha(env),
                'release_gate_sha256':C.sha(C.HERE/'E39_RELEASE_GATE_2026-10-26.json'),'parity_input_seal_sha256':'fixture','input_seal_sha256':'fixture'}
            a=SimpleNamespace(assignment=root/'assignment.json',out=root/'out',release_gate=C.HERE/'E39_RELEASE_GATE_2026-10-26.json',environment_manifest=env,parity_inputs=root/'parity')
            C.dump(a.assignment,assign);model=MagicMock();model.named_parameters.return_value=[]
            tok=SimpleNamespace(encode=lambda *a,**k:[1]);reader=SimpleNamespace(model=model,device='cuda')
            events=[]
            def parity(*args,**kwargs):events.append('parity');C.dump(a.out/'PARITY_RESULT.json',{'status':'PASS'})
            def train(*args,**kwargs):
                events.append('train');return {'finite_loss':True,'finite_gradients':True,'frozen_parameter_grads_none':True} if kwargs.get('diagnostics') else .1
            def score(reader,items,acts,spec,row):return [{'id':x['id'],'scores':[.1,.2]} for x in items if x['feature']==row]
            contexts=[patch.object(C,'assignment',return_value=assign),patch.object(W,'check_source'),patch.object(W,'arm_deadline'),patch.object(W,'check_time'),patch.object(W.time,'time',return_value=1100),patch.object(W.E,'verify_manifest'),patch.object(W.E,'runtime_ready',return_value={'status':'TRAINING_ENVIRONMENT_READY'}),patch.object(W,'runtime_inputs',return_value=(assign,{}, {},dev,test,np.ones((756,1)),np.ones((2100,1)),{r:{'olens':[['a','b'],['c','d']]} for r in C.ROWS})),patch.object(W,'parity_inputs',return_value=()),patch.object(W,'load_base',return_value=(model,tok)),patch.object(W,'make_reader',return_value=reader),patch.object(W,'parity_gate',side_effect=parity),patch.object(W,'attach_lowrank',return_value=([],[])),patch.object(W,'detach_lowrank'),patch.object(W,'optimizer_for',return_value=None),patch.object(W,'train_step',side_effect=train),patch.object(W,'score',side_effect=score),patch.object(W,'configure_audit'),patch('torch.cuda.empty_cache'),patch('torch.cuda.manual_seed_all')]
            from contextlib import ExitStack
            with ExitStack() as stack:
                for context in contexts:stack.enter_context(context)
                self.assertEqual(W.run(a),0)
            self.assertEqual(events[0],'parity');self.assertEqual(events.count('train'),405)
            self.assertEqual(len(C.rows(a.out/'train.jsonl')),400)
            for step in C.CHECKPOINTS:
                seal=C.verify(a.out/f'step_{step}','CHECKPOINT_SEAL.json');self.assertEqual(len(seal['files']),26)
            self.assertEqual(C.read(a.out/'RUN_RECEIPT.json')['status'],'COMPLETE_FULL_ASSIGNED_GRID')
            C.verify(a.out,'OUTPUT_SEAL.json')

if __name__=='__main__':unittest.main()
