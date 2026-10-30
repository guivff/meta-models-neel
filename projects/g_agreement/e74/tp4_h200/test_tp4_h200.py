"""CPU-only TP4 H200 admission, fixed-settings and pre-verdict OOM tests."""
import hashlib,json,subprocess,sys,tempfile,time,types,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from . import hardware as h,ops,resident as r,smoke50
from .test_operator import admission,Engine
from .test_hardware import hopper
from .test_smoke import runtime
from .test_smoke50 import fixtures


def tp4():
    a=dict(admission(),gpu_type='H200',gpu_count=4,cap_usd=100,limit_authority=h.TP4_H200_AUTHORITY,
        phase_forecast_seconds={'boot':660,'smoke':120,'capture':1633,'readouts':840},hardware_forecast_sha256='a'*64,
        issuer='I-2',experiment='E74',admitted=True,authorized_phases=['resident_smoke_capture','weight_staging'],
        provider_stop_verified=True,environment_lock_verified=True,environment_lock_sha256='b'*64)
    a['tp4_h200']=dict(authority=h.TP4_H200_AUTHORITY,memory_receipt_sha256=h.TP4_MEMORY_RECEIPT,
        secure_cloud=True,single_node=True,attempt_ordinal=1,prior_tp4_h200_oom_count=0,one_attempt_only=True,attempt_ledger_sha256='c'*64)
    return a


class TP4H200Tests(unittest.TestCase):
    def test_limit_authority_and_fixed_memory_settings(self):
        a=tp4();cfg=h.profile(a)
        self.assertEqual(h.limits(a),{'boot_smoke_seconds':3000,'cap_usd':100})
        self.assertEqual(h.limits(admission()),{'boot_smoke_seconds':1200,'cap_usd':100})
        self.assertEqual(h.limits(hopper()),{'boot_smoke_seconds':3000,'cap_usd':160})
        self.assertEqual(h.engine_kwargs(cfg),h.engine_kwargs(h.profile(admission())))
        self.assertEqual(h.engine_kwargs(cfg),dict(tp=4,gpu_mem=.88,moe_backend='marlin',kv_cache_dtype='fp8',max_model_len=1152,max_num_seqs=512,max_num_batched_tokens=32768,w4a16=True,seed=0))
        e=Engine();e._stats=Mock(return_value=[{}]*4);ctor=Mock(return_value=e)
        cuda=types.SimpleNamespace(device_count=lambda:4,get_device_name=lambda i:'NVIDIA H200',get_device_capability=lambda i:(9,0))
        self.assertIs(h.construct(types.SimpleNamespace(GlmOlensEngine=ctor),types.SimpleNamespace(cuda=cuda),'unused',cfg),e)
        ctor.assert_called_once_with('unused',**h.engine_kwargs(cfg))
    def test_secure_memory_and_no_retry_attestations_required(self):
        for field,value in [('secure_cloud',False),('single_node',False),('attempt_ordinal',2),('attempt_ordinal',True),('prior_tp4_h200_oom_count',1),('prior_tp4_h200_oom_count',False),('one_attempt_only',False),('memory_receipt_sha256','0'*64),('attempt_ledger_sha256',None),('authority','wrong')]:
            a=tp4();a['tp4_h200'][field]=value
            with self.assertRaises(ValueError):h.profile(a)
        for count in [5,6,True]:
            with self.assertRaises(ValueError):h.profile(dict(tp4(),gpu_count=count))
    def test_clock_and_budget_boundaries(self):
        a=tp4();q={'allocation_start_epoch':1000,'weight_staging_started_epoch':1000,'weight_staging_finished_epoch':4600,'archive_staging_started_epoch':4600,'archive_staging_finished_epoch':5500,'science_start_epoch':5500,'deadline_epoch':8500}
        smoke50.validate_clocks(q,5501,a)
        with self.assertRaises(ValueError):smoke50.validate_clocks(q|{'deadline_epoch':8501},5501,a)
        priced=dict(a,allocation_start_epoch=1000,provider_stop_epoch=99999,replica_hourly_usd=3600,other_cost_upper_bound_usd=0)
        self.assertEqual(ops.budget(priced,70,1010)['forecast_times_1_25_usd'],100)
        with self.assertRaises(ops.NoFit):ops.budget(priced,70.01,1010)
        with self.assertRaises(ValueError):ops.budget(priced|{'cap_usd':160},0,1010)
    def test_smoke_hook_preserves_outputs_and_precedes_scoring(self):
        e1,e2=Engine(),Engine();events=[];score=smoke50.agreement
        def agreement(*args):
            self.assertEqual(events,['before']);events.append('scoring');return score(*args)
        a=smoke50.run50(fixtures(),runtime(),e1,'adapter')
        with patch.object(smoke50,'agreement',side_effect=agreement):
            b=smoke50.run50(fixtures(),runtime(),e2,'adapter',expected_workers=4,before_verdict=lambda:events.append('before'))
        for k in ['passed','exact_match_count','median_token_set_jaccard','grammar_violation_count']:self.assertEqual(a[k],b[k])
        self.assertEqual(e1.calls,e2.calls)
    def make_req(self,root):
        path=root/'admission.json';ops.write(path,tp4());return {'admission':str(path),'admission_sha256':ops.sha(path)}
    def test_oom_only_pre_verdict_and_only_this_path(self):
        import torch
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);req=self.make_req(root);out=root/'run';out.mkdir();ops.write(out/'ENGINE_ONCE.json',{})
            self.assertFalse(r.record_operational_oom(req,out,RuntimeError('ordinary setup error')))
            self.assertTrue(r.record_operational_oom(req,out,torch.cuda.OutOfMemoryError('CUDA out of memory: synthetic')))
            d=json.loads((out/'OPERATIONAL_OOM.json').read_text());self.assertTrue(d['no_tp4_h200_retry']);self.assertFalse(d['smoke_verdict_computed'])
            self.assertFalse(d['provider_release_verified'])
            ops.write(out/'SMOKE_VERDICT_STARTED.json',{})
            self.assertFalse(r.record_operational_oom(req,out,torch.cuda.OutOfMemoryError('CUDA out of memory: synthetic')))
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);path=root/'admission.json';ops.write(path,admission());ops.write(root/'ENGINE_ONCE.json',{})
            self.assertFalse(r.record_operational_oom({'admission':str(path),'admission_sha256':ops.sha(path)},root,RuntimeError('CUDA out of memory')))
    def test_worker_cli_and_supervisor_seal_operational_oom_no_retry(self):
        real_popen=subprocess.Popen;children=[]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);req=self.make_req(root);now=time.time();req.update(allocation_start_epoch=now-1,weight_staging_started_epoch=now-1,weight_staging_finished_epoch=now-1,archive_staging_started_epoch=now-1,archive_staging_finished_epoch=now-1,science_start_epoch=now,deadline_epoch=now+30)
            def start(argv,**kwargs):
                # Exercise actual worker main exception path and parent sealing.
                script="from pathlib import Path;from unittest.mock import patch;from projects.g_agreement.e74 import resident as r,ops;import sys,torch\ndef fail(req,out):\n ops.write(out/'ENGINE_ONCE.json',{});raise torch.cuda.OutOfMemoryError('CUDA out of memory: synthetic')\nsys.argv=%r\nwith patch.object(r,'worker',side_effect=fail):raise SystemExit(r.main())"%(['resident',*argv[3:]],)
                child=real_popen([sys.executable,'-c',script],**kwargs);children.append(child);return child
            with patch.object(r.subprocess,'Popen',side_effect=start):
                self.assertEqual(r.supervise(req,root/'run'),5)
            children[0].wait(timeout=5)
            seal=ops.verify_seal(root/'run/SEAL.json')
            self.assertEqual(seal['status'],'OPERATIONAL_OOM_PRE_SMOKE_VERDICT');self.assertTrue(seal['no_automatic_retry'])
            self.assertFalse((root/'run/capture').exists())
            with self.assertRaises(FileExistsError):r.supervise(req,root/'run')
    def test_smoke_failure_still_stops_science_and_cannot_be_oom_exception(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);req={'admission_obj':tp4(),'adapter_dir':'adapter','deadline_epoch':time.time()+3000,'boot_seconds':1}
            def failed(*args,**kwargs):kwargs['before_verdict']();return {'passed':False}
            with patch.object(smoke50,'run50',side_effect=failed):
                with self.assertRaisesRegex(ValueError,'STOP_SMOKE_CRITERION_FAILED'):r.run_resident(req,out,Engine(),runtime(),[],[],[])
            self.assertTrue((out/'SMOKE_VERDICT_STARTED.json').exists());self.assertFalse((out/'capture').exists())
            self.assertFalse(r.record_operational_oom(req,out,RuntimeError('CUDA out of memory')))

if __name__=='__main__':unittest.main()
