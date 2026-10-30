"""Synthetic integrity and budget tests; no E39 scientific analysis invocation."""
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
import contract as C
import rerun_159 as R
import recovery_159 as V
import analysis_once_recovered_159 as O

def ledger_fixture():
    s=R.scope();pods=[]
    for old in s['original_pods']:
        seconds=old['minimum_observed_worker_gpu_seconds']+10
        pods.append({'pod_id':old['pod_id'],'provider_created_epoch':old['provider_created_epoch'],
                     'provider_terminated_epoch':old['provider_created_epoch']+seconds,'gpu_seconds':seconds})
    return {'issuer':'integrator','experiment':'E39','status':'CUSTODY_AND_RECOVERY_VERIFIED','all_original_pods_stopped':True,
        'recovery_complete':True,'unrecoverable_runs':s['rerun_runs'],'retained_complete_runs':50,'pods':pods,
        'total_gpu_seconds':sum(x['gpu_seconds'] for x in pods)}

class Recovery(unittest.TestCase):
    def test_fixed50plus4_coverage(self):
        kept=[tuple(r) for slot in range(6) for r in V.retained_runs(slot)];re=[tuple(r) for r in R.scope()['rerun_runs']]
        self.assertEqual(len(kept),50);self.assertEqual(len(re),4);self.assertFalse(set(kept)&set(re));self.assertEqual(set(kept+re),set(C.RUNS))
    def test_original_scientific_analysis_is_byte_identical(self):
        marker='    # Validate every scientific score'
        original=(C.HERE/'analyze.py').read_text();recovery=(C.HERE/'analyze_recovered_159.py').read_text()
        self.assertEqual(original[original.index(marker):],recovery[recovery.index(marker):])
    def test_actual_provider_custody_and_recovery_required(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'custody';v=ledger_fixture();C.dump(p,v);R.custody(p)
            for change in ({'recovery_complete':False},{'total_gpu_seconds':81000},{'unrecoverable_runs':[]}):
                C.dump(p,{**v,**change})
                with self.assertRaises(ValueError):R.custody(p)
            v['pods'][0]['gpu_seconds']-=1;C.dump(p,v)
            with self.assertRaises(ValueError):R.custody(p)
    def test_assignment_exact_runs_and_cap(self):
        v=ledger_fixture();now=time.time();a={'issuer':'integrator','experiment':'E39','recovery_authority':'§159 item4',
            'pod_count':1,'slot':0,'pod_id':'synthetic','seed':C.SEED,'runs':R.scope()['rerun_runs'],
            'plan_sha256':C.sha(C.HERE/'PLAN.json'),'source_manifest_sha256':R.scope()['original_source_manifest_sha256'],
            'rerun_source_manifest_sha256':'synthetic','input_seal_sha256':R.scope()['input_seal_sha256'],
            'target_mapping_sha256':C.sha(C.HERE/'LORA_TARGETS.json'),'source_published':True,'external_hardstop_verified':True,
            'allocated_gpu_seconds':13500,'previous_gpu_seconds':v['total_gpu_seconds'],'provider_created_epoch':now,'deadline_epoch':now+13500}
        real_sha=C.sha
        with patch.object(C,'sha',side_effect=lambda p:'synthetic' if Path(p)==R.MANIFEST else real_sha(p)):
            R.assignment(a,v,now)
            for change in ({'runs':a['runs'][:-1]},{'seed':1},{'allocated_gpu_seconds':30000},{'previous_gpu_seconds':0},{'pod_count':2}):
                with self.assertRaises(ValueError):R.assignment({**a,**change},v,now)
    def test_admission_uses_original_science_cap(self):
        a={'allocated_gpu_seconds':13500,'previous_gpu_seconds':50925,'input_seal_sha256':'x'}
        f={'status':'WARMED_FORECAST','slot':0,'pod_count':1,'plan_sha256':C.sha(C.HERE/'PLAN.json'),
            'input_seal_sha256':'x','allocated_gpu_seconds':13500,'previous_gpu_seconds':50925,
            'forecast_remaining_seconds':5000,'elapsed_science_seconds':200,'elapsed_provider_seconds':900,
            'setup_elapsed_seconds':700,'forecast_sha256':'synthetic'}
        result=R.admit(f,a);self.assertEqual(result['status'],'ADMIT_FULL_GRID');self.assertEqual(result['total_experiment_reserved_gpu_seconds'],64425)
        self.assertEqual(result['pods'][0]['science_seconds'],8160)
        self.assertEqual(R.admit({**f,'forecast_remaining_seconds':11000},a)['status'],'NO_FIT_STOP')
    def test_partial_pull_ignores_only_explicit_lost_run(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'out/retained__L').mkdir(parents=True);f=root/'out/retained__L/score';f.write_text('synthetic')
            sums=root/'PULL_SUMS';sums.write_text(C.sha(f)+'  out/retained__L/score\n'+'a'*64+'  out/python_string__B/missing\n')
            V.verify_selected_pull(root,C.sha(sums),[['python_string','B']])
            with self.assertRaises(ValueError):V.verify_selected_pull(root,C.sha(sums))
            f.write_text('changed')
            with self.assertRaises(ValueError):V.verify_selected_pull(root,C.sha(sums),[['python_string','B']])
    def test_seven_pull_receipt_requires_every_run_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);entries=[];mapping={};paths=[]
            for slot in range(7):
                relative='pull'+str(slot);paths.append(relative);out=root/relative/'out';out.mkdir(parents=True)
                runs=V.retained_runs(slot) if slot<6 else R.scope()['rerun_runs']
                ident='original_slot'+str(slot) if slot<6 else 'rerun_159';pod='synthetic'+str(slot)
                C.dump(out/'assignment.json',{'pod_id':pod})
                for row,arm in runs:
                    folder=out/(row+'__'+arm);folder.mkdir();C.dump(folder/'SCORE_SEAL.json',{'synthetic':True})
                    mapping[row+'__'+arm]={'pull_id':ident,'score_seal_sha256':C.sha(folder/'SCORE_SEAL.json')}
                manifest=root/relative/'PULL_SUMS'
                manifest.write_text(''.join(C.sha(f)+'  '+f.relative_to(root/relative).as_posix()+'\n' for f in sorted(out.rglob('*')) if f.is_file()))
                entries.append({'pull_id':ident,'pod_id':pod,'directory':relative,'selected_runs':runs,'pull_sums_sha256':C.sha(manifest)})
            receipt={'issuer':'integrator','experiment':'E39','schema':'E39_VERIFIED_RECOVERY_PULLS_159_v1',
                'status':'VERIFIED_COMPLETE','production_complete':True,'original_pod_count':6,'rerun_pod_count':1,
                'input_seal_sha256':R.scope()['input_seal_sha256'],'pulls':entries,'run_sources':mapping}
            with patch.object(C,'ROOT',root):
                roots,proofs=V.receipt_preflight({'pull_directories':paths},receipt)
                self.assertEqual(len(roots),7);self.assertEqual(len(proofs),7)
                mapping.pop('table_row__B')
                with self.assertRaises(ValueError):V.receipt_preflight({'pull_directories':paths},receipt)

    def test_once_lock_is_shared_with_original_and_failure_sticks(self):
        import analysis_once_2026_10_26 as original
        self.assertEqual(O.CLAIM,original.CLAIM)
        with tempfile.TemporaryDirectory() as d,patch.object(O,'CLAIM',Path(d)/'CLAIM'),patch.object(O,'STATUS',Path(d)/'STATUS'),patch.object(O,'preflight',side_effect=ValueError),patch.object(O,'execute') as execute:
            self.assertEqual(O.run_once(),2);self.assertEqual(O.run_once(),3);execute.assert_not_called()

if __name__=='__main__':unittest.main()
