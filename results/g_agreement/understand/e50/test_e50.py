import copy
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch,MagicMock
from contextlib import ExitStack
import numpy as np
import contract as C
import worker as W
import analyze as A
import analysis_once_2026_10_26 as O
from secondary import load_secondary

def dev():return [{'id':f+'-'+str(i),'feature':f,'y':i%2,'cluster':str(i//14)} for f in C.STRUCTURE for i in range(84)]

def fixture_cells():
    return [{'split':s,'arm':a,'row':r,'auroc':(.8 if a=='L' and r in C.STRUCTURE else .95 if r in C.CONTENT else .5),
        'naming':{'correct_only':21 if a=='L' else 0,'wrong_only':0,'both':0,'neither':63 if a=='L' else 84}}
        for s in ('A','B') for a in ('L','S') for r in C.ROWS]

def parity():return {s:{r:{'pre':.5,'post':.5} for r in A.PARITY_ROWS} for s in ('A','B')}

class Contracts(unittest.TestCase):
    def test_exact_reverse_split_and_full_rows(self):
        p=C.plan()['splits'];self.assertEqual(p['A']['train'],p['B']['heldout']);self.assertEqual(p['B']['train'],p['A']['heldout'])
        self.assertEqual(set(p['A']['train'])|set(p['B']['train']),set(C.STRUCTURE));self.assertFalse(set(p['A']['train'])&set(p['B']['train']))

    def test_schedule_shared_order_and_within_row_label_shuffle(self):
        for split in ('A','B'):
            l=C.training_schedule(dev(),split,'L');s=C.training_schedule(dev(),split,'S')
            self.assertEqual(len(l),400);self.assertEqual(l,C.training_schedule(dev(),split,'L'))
            lf=[x for b in l for x in b];sf=[x for b in s for x in b]
            self.assertEqual(len(lf),3200);self.assertEqual(len({x['id'] for x in lf[:672]}),672)
            self.assertEqual([{k:v for k,v in x.items() if k!='y'} for x in lf],[{k:v for k,v in x.items() if k!='y'} for x in sf])
            self.assertEqual({x['feature'] for x in lf},set(C.plan()['splits'][split]['train']))
            self.assertTrue(any(x['y']!=y['y'] for x,y in zip(lf,sf)))
            self.assertEqual([x['phrasing'] for x in lf],[i%2 for i in range(3200)])
            for row in C.plan()['splits'][split]['train']:
                self.assertEqual(sum(x['y'] for x in sf[:672] if x['feature']==row),42)

    def test_rules_thresholds_single_split_and_undertraining(self):
        cells=fixture_cells();p=parity();r=A.evaluate_rules(cells,p)
        self.assertTrue(all(r[k]['met'] for k in ('R1','R2','R3')));self.assertFalse(r['falsifier']['met'])
        for c in cells:
            if c['split']=='A' and c['arm']=='L' and c['row'] in C.plan()['splits']['A']['train']:c['auroc']=.79999
        r=A.evaluate_rules(cells,p);self.assertEqual(r['eligible_splits'],['B']);self.assertEqual(r['report_label'],'single-split (n = 8 rows)')
        self.assertEqual(r['R1']['required'],5);self.assertEqual(r['R2']['splits'],['B']);self.assertEqual(r['R3']['n_per_arm'],672)
        p['A']['prose_paren']['post']=.7;self.assertTrue(A.evaluate_rules(cells,p)['R2']['met'])
        for c in cells:
            if c['split']=='B' and c['arm']=='L' and c['row'] in C.plan()['splits']['B']['train']:c['auroc']=.79
        r=A.evaluate_rules(cells,p)
        for k in ('R1','R3','falsifier'):self.assertIsNone(r[k]['met'])

    def test_falsifier_training_medians_and_both_splits(self):
        cells=fixture_cells()
        for c in cells:
            if c['row'] in C.plan()['splits'][c['split']]['heldout'] and c['arm']=='L':c['auroc']=.60
        self.assertTrue(A.evaluate_rules(cells,parity())['falsifier']['met'])
        for c in cells:
            if c['split']=='B' and c['row'] in C.plan()['splits']['B']['heldout'] and c['arm']=='L':c['auroc']=.60001
        self.assertFalse(A.evaluate_rules(cells,parity())['falsifier']['met'])

    def test_auroc_and_correctness_partition_both_not_credit(self):
        self.assertEqual(A.auc([1,0,1,0],[1,0,1,0]),1)
        self.assertEqual(A.auc([1,1,1,1],[1,0,1,0]),.5)
        texts=['inside a string literal','outside a string literal','inside a string literal. outside a string literal','nothing']
        records=[{'id':str(i),'raw':t} for i,t in enumerate(texts)];labels={str(i):{'y':1} for i in range(4)}
        self.assertEqual(A.naming(records,labels,'python_string'),dict.fromkeys(('correct_only','wrong_only','both','neither'),1))

    def test_forecast_and_budget_boundaries(self):
        f={'forecast_remaining_seconds':1000,'science_started_epoch':100,'provider_deadline_epoch':3600}
        self.assertEqual(C.forecast_admission(f,200)['status'],'ADMIT_FULL_GRID')
        f['forecast_remaining_seconds']=4000;self.assertEqual(C.forecast_admission(f,200)['status'],'NO_FIT_STOP')
        self.assertEqual(C.CAP,14400)
        a={'issuer':'integrator','experiment':'E50','pod_count':2,'slot':0,'runs':[['A','L'],['A','S']],'pod_id':'x',
           'plan_sha256':C.sha(C.HERE/'PLAN.json'),'target_mapping_sha256':C.sha(C.HERE/'LORA_TARGETS.json'),
           'source_published':True,'external_hardstop_verified':True,'allocated_gpu_seconds':3600,'previous_gpu_seconds':0,
           'provider_created_epoch':100,'deadline_epoch':3700}
        C.assignment(a,now=100);a['allocated_gpu_seconds']=7201
        with self.assertRaises(ValueError):C.assignment(a,now=100)

    def test_optional_bank_requires_frozen_bound_capture(self):
        a={'secondary':{'status':'NOT_FROZEN_AT_LAUNCH','issuer':'integrator','checked_before_launch':True}}
        self.assertIsNone(load_secondary(None,a));a['secondary']['checked_before_launch']=False
        with self.assertRaises(ValueError):load_secondary(None,a)
        with self.assertRaises(ValueError):load_secondary(None,{'secondary':{'status':'FROZEN_VERIFIED'}})

    def test_once_failure_is_claimed_without_retry(self):
        with tempfile.TemporaryDirectory() as d,patch.object(O,'CLAIM',Path(d)/'CLAIM.json'),patch.object(O,'STATUS',Path(d)/'STATUS.json'),patch.object(O,'preflight',side_effect=ValueError),patch.object(O,'execute') as invoke:
            self.assertEqual(O.run_once(),2);self.assertEqual(O.run_once(),3);invoke.assert_not_called()

    def test_synthetic_analysis_publishes_single_split_label_and_no_rerun(self):
        # Synthetic CPU data only. Exercise private-key binding, all100 cells,
        # naming partitions, W1 comparisons and sealed report publication.
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);inp=root/'input';inp.mkdir();par=root/'parity';par.mkdir()
            labs=[{'id':r+'-'+str(i),'feature':r,'y':i%2,'cluster':str(i//14)} for r in C.ROWS for i in range(84)]
            test=[{'id':x['id'],'feature':x['feature']} for x in labs];C.jsonl(inp/'test.labels.DO_NOT_STAGE.jsonl',labs)
            C.dump(inp/'INPUT_SEAL.json',{});C.dump(par/'labels.json',{x['id']:x['y'] for x in labs if x['feature'] in A.PARITY_ROWS})
            scores={};free={};pre={s:{} for s in ('A','B')};post={}
            for s in ('A','B'):
                for arm in ('L','S'):
                    for row in C.ROWS:
                        scores[s,arm,row]={x['id']:(x['y'] if arm=='L' else 0.) for x in labs if x['feature']==row}
                        if s=='A' and row in C.plan()['splits'][s]['train']:scores[s,arm,row]={k:0. for k in scores[s,arm,row]}
                        if row in C.plan()['splits'][s]['heldout']:free[s,arm,row]=[{'id':x['id'],'raw':'nothing'} for x in labs if x['feature']==row]
                for row in A.PARITY_ROWS:
                    pre[s][row]={x['id']:float(x['y']) for x in labs if x['feature']==row};post[s,row]=pre[s][row]
            binding={'private_test_labels_sha256':C.sha(inp/'test.labels.DO_NOT_STAGE.jsonl')}
            oldread=C.read
            def read(path):return binding if Path(path)==C.HERE/'BOUND_INPUT.json' else oldread(path)
            collection=root/'collection';collection.mkdir();C.dump(collection/'OUTPUT_SEAL.json',{})
            data=(test,scores,free,pre,post,{}, {'status':'NOT_FROZEN_AT_LAUNCH'})
            with patch.object(A,'validate_collection',return_value=data),patch.object(C,'read',side_effect=read),patch.object(A,'bootstrap_ci',return_value=[0,1]),patch.object(A,'content_only_reference',return_value={'synthetic':True}):
                result=A.analysis(inp,[collection],par,root/'output')
                self.assertEqual(result['report_label'],'single-split (n = 8 rows)')
                self.assertEqual(len(result['cells']),100);self.assertTrue(result['R1']['met'])
                self.assertEqual((root/'output/RESULTS.md').read_text().count('single-split (n = 8 rows)'),5)
                C.verify(root/'output','ANALYSIS_SEAL.json')
                with self.assertRaises(FileExistsError):A.analysis(inp,[collection],par,root/'output')

    def test_existing_E44_reference_seal_without_rerun(self):
        value=A.content_only_reference();self.assertFalse(value['rerun']);self.assertEqual(set(value['step400']),set(C.ROWS))

    def test_bound_capture_exact_and_labels_off_worker_archive(self):
        p=C.ROOT/'cache/g_agreement/understand/e50-bound-v1/input';C.verify(p)
        self.assertEqual(len(C.rows(p/'dev.jsonl')),1344);self.assertEqual(len(C.rows(p/'test.jsonl')),2100)
        self.assertEqual({r['feature'] for r in C.rows(p/'dev.jsonl')},set(C.STRUCTURE))
        self.assertTrue(C.read(p/'provenance.json')['shared_e39_tensors_bit_exact'])
        self.assertFalse(any('DO_NOT_STAGE' in n for n in C.read(p/'INPUT_SEAL.json')['files']))

class SyntheticWorker(unittest.TestCase):
    def test_two_400step_arms_all_scores_free_and_parity_first(self):
        import torch
        test=[{'id':f+'-'+str(i),'feature':f} for f in C.ROWS for i in range(84)]
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'cache';root.mkdir();env=root/'environment.json';C.dump(env,{})
            assign={'issuer':'integrator','experiment':'E50','pod_id':'synthetic','pod_count':2,'slot':0,'runs':[['A','L'],['A','S']],
                'plan_sha256':C.sha(C.HERE/'PLAN.json'),'target_mapping_sha256':C.sha(C.HERE/'LORA_TARGETS.json'),
                'source_published':True,'external_hardstop_verified':True,'allocated_gpu_seconds':3600,'previous_gpu_seconds':0,
                'provider_created_epoch':1000,'deadline_epoch':4600,'training_environment_sha256':C.sha(env),
                'parity_input_seal_sha256':'fixture','input_seal_sha256':'fixture',
                'secondary':{'status':'NOT_FROZEN_AT_LAUNCH','issuer':'integrator','checked_before_launch':True}}
            a=SimpleNamespace(assignment=root/'assignment.json',out=root/'out',environment_manifest=env,parity_inputs=root/'parity',secondary_input=None)
            C.dump(a.assignment,assign);model=MagicMock();model.named_parameters.return_value=[]
            tok=SimpleNamespace(encode=lambda *a,**k:[1]);reader=SimpleNamespace(model=model,device='cuda')
            events=[]
            def parity_gate(*args,**kwargs):events.append('parity');C.dump(a.out/'PARITY_RESULT.json',{'status':'PASS'})
            def train(*args,**kwargs):
                events.append('train');return {'finite_loss':True,'finite_gradients':True,'frozen_parameter_grads_none':True} if kwargs.get('diagnostics') else .1
            def score(reader,items,acts,spec,row):events.append('score');return [{'id':x['id'],'scores':[.1,.2]} for x in items if x['feature']==row]
            def free(reader,items,acts,row,**kwargs):events.append('free');return [{'id':x['id'],'raw':'fixture'} for x in items if x['feature']==row]
            specs={r:{'olens':[['a','b'],['c','d']]} for r in C.ROWS}
            gate=(test,{},specs,np.ones((2100,1)),{})
            contexts=[patch.object(C,'assignment',return_value=assign),patch.object(W,'check_source'),patch.object(W,'arm_deadline'),patch.object(W,'check_time'),patch.object(W.time,'time',return_value=1100),patch.object(W.E,'verify_manifest'),patch.object(W.E,'runtime_ready',return_value={'status':'TRAINING_ENVIRONMENT_READY'}),patch.object(W,'runtime_inputs',return_value=(assign,{}, {},dev(),test,np.ones((1344,1)),np.ones((2100,1)),specs)),patch.object(W,'parity_inputs',return_value=gate),patch.object(W,'load_base',return_value=(model,tok)),patch.object(W,'make_reader',return_value=reader),patch.object(W,'parity_gate',side_effect=parity_gate),patch.object(W,'attach_lowrank',return_value=([],[])),patch.object(W,'detach_lowrank'),patch.object(W,'optimizer_for',return_value=None),patch.object(W,'train_step',side_effect=train),patch.object(W,'score',side_effect=score),patch.object(W,'free',side_effect=free),patch.object(W,'configure_audit'),patch('torch.cuda.empty_cache'),patch('torch.cuda.manual_seed_all')]
            with ExitStack() as stack:
                for context in contexts:stack.enter_context(context)
                self.assertEqual(W.run(a),0)
            self.assertEqual(events[0],'parity');self.assertEqual(events.count('train'),805)
            self.assertEqual(events.count('score'),54);self.assertEqual(events.count('free'),17)
            for arm,n in [('L',39),('S',36)]:
                folder=a.out/('A__'+arm);self.assertEqual(len(C.rows(folder/'train.jsonl')),400)
                seal=C.verify(folder,'SCORE_SEAL.json');self.assertEqual(len(seal['files']),n)
            self.assertEqual(C.read(a.out/'RUN_RECEIPT.json')['status'],'COMPLETE_FULL_ASSIGNED_GRID');C.verify(a.out,'OUTPUT_SEAL.json')

if __name__=='__main__':unittest.main()
