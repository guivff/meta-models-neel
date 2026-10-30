"""CPU-only synthetic TP8 tests; real author constructor is AST-isolated with stub vLLM."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import Mock, patch
from . import hardware as h, ops, resident, smoke50
from .test_operator import Engine, admission, go
from .test_smoke50 import fixtures
from .test_smoke import runtime

NOW = h.HOPPER_NOT_BEFORE + 10


def hopper():
    return dict(admission(NOW), gpu_type='H200',gpu_count=8,replica_hourly_usd=1,cap_usd=120,limit_authority=h.TP8_LIMIT_AUTHORITY,
                hopper_fallback={'authority':h.HOPPER_AUTHORITY,'not_before_epoch':h.HOPPER_NOT_BEFORE,
                                 'checked_epoch':NOW,'no_b200_claim_by_deadline':True,'single_node':True},
                phase_forecast_seconds={'boot':2040,'smoke':120,'capture':1633,'readouts':840},
                hardware_forecast_sha256='a'*64)


class HardwareTests(unittest.TestCase):
    def test_hopper_gate_date_timezone_and_bound_conditions(self):
        self.assertEqual(h.HOPPER_NOT_BEFORE,1793163600)
        self.assertEqual(h.profile(hopper(),NOW)['tensor_parallel_size'],8)
        self.assertTrue(h.profile(hopper(),NOW)['undocumented_hardware_path'])
        with self.assertRaises(ValueError):h.profile(hopper(),h.HOPPER_NOT_BEFORE-1)
        for field,value in [('no_b200_claim_by_deadline',False),('single_node',False),
                            ('authority','wrong'),('checked_epoch',h.HOPPER_NOT_BEFORE-1),
                            ('checked_epoch',NOW+1),('not_before_epoch',h.HOPPER_NOT_BEFORE-3600)]:
            a=hopper();a['hopper_fallback'][field]=value
            with self.assertRaises(ValueError):h.profile(a,NOW)
        a=hopper();a['allocation_start_epoch']=h.HOPPER_NOT_BEFORE-1
        with self.assertRaises(ValueError):h.profile(a,NOW)
    def test_no_implicit_other_hardware_or_worker_count(self):
        for kind,count in [('H100',8),('H200',4),('H200',7),('B300',8),('B200',8),('H200',True)]:
            with self.assertRaises(ValueError):h.profile(dict(hopper(),gpu_type=kind,gpu_count=count),NOW)
        self.assertEqual(h.profile(admission())['tensor_parallel_size'],4)
    def test_h200_requires_explicit_forecast_not_b200_proxy_or_longer_deadline(self):
        for field in ['phase_forecast_seconds','hardware_forecast_sha256']:
            a=hopper();del a[field]
            with self.assertRaises(ValueError):h.profile(a,NOW)
        for value in [float('nan'),-1,True,2881]:
            a=hopper();a['phase_forecast_seconds']['boot']=value
            with self.assertRaises(ValueError):h.profile(a,NOW)
        self.assertEqual(h.phase_forecast(hopper())['boot'],2040)
    def test_tp8_limits_do_not_raise_tp4_limits(self):
        a=hopper(); b=admission(NOW)
        self.assertEqual(h.limits(a),{'boot_smoke_seconds':3000,'cap_usd':120})
        self.assertEqual(h.limits(b),{'boot_smoke_seconds':1200,'cap_usd':100})
        for authority in [None,'wrong']:
            with self.assertRaises(ValueError):h.profile(dict(a,limit_authority=authority),NOW)
        q={'allocation_start_epoch':1000,'weight_staging_started_epoch':1000,'weight_staging_finished_epoch':4600,
           'archive_staging_started_epoch':4600,'archive_staging_finished_epoch':5500,'science_start_epoch':5500,'deadline_epoch':8500}
        smoke50.validate_clocks(q,5501,a)
        with self.assertRaises(ValueError):smoke50.validate_clocks(q|{'deadline_epoch':8501},5501,a)
        with self.assertRaises(ValueError):smoke50.validate_clocks(q,5501,b)
        smoke50.validate_clocks(q|{'deadline_epoch':6700},5501,b)
        a=dict(a,replica_hourly_usd=3600,other_cost_upper_bound_usd=0,allocation_start_epoch=NOW)
        self.assertEqual(ops.budget(a,96,NOW)['forecast_times_1_25_usd'],120)
        with self.assertRaises(ops.NoFit) as cm:ops.budget(a,96.01,NOW)
        self.assertEqual(cm.exception.evidence['cap_usd'],120)
        with self.assertRaises(ValueError):ops.budget(dict(a,cap_usd=100),0,NOW)
        with self.assertRaises(ValueError):ops.budget(dict(b,cap_usd=120),0,NOW)

    def test_only_tp_changes_in_author_engine_settings(self):
        a=h.engine_kwargs(h.profile(admission()));b=h.engine_kwargs(h.profile(hopper(),NOW))
        self.assertEqual(a|{'tp':8},b)
        self.assertEqual(b['moe_backend'],'marlin');self.assertTrue(b['w4a16'])
    def test_exact_eight_h200_devices_and_rpc_workers_required(self):
        cfg=h.profile(hopper(),NOW);e=Engine();e.n_workers=8;e._stats=Mock(return_value=[{}]*8)
        constructor=Mock(return_value=e)
        cuda=types.SimpleNamespace(device_count=lambda:8,get_device_name=lambda i:'NVIDIA H200',get_device_capability=lambda i:(9,0))
        result=h.construct(types.SimpleNamespace(GlmOlensEngine=constructor),types.SimpleNamespace(cuda=cuda),'synthetic',cfg)
        self.assertIs(result,e);constructor.assert_called_once_with('synthetic',**h.engine_kwargs(cfg));e._stats.assert_called_once_with(reset=False)
        for count,name,cap in [(4,'NVIDIA H200',(9,0)),(8,'NVIDIA GH200',(9,0)),(8,'NVIDIA H100',(9,0)),(8,'NVIDIA H200',(10,0))]:
            fake=types.SimpleNamespace(device_count=lambda:count,get_device_name=lambda i:name,get_device_capability=lambda i:cap)
            with self.assertRaises(ValueError):h.construct(types.SimpleNamespace(GlmOlensEngine=constructor),types.SimpleNamespace(cuda=fake),'synthetic',cfg)
        e._stats.return_value=[{}]*7
        with self.assertRaises(ValueError):h.construct(types.SimpleNamespace(GlmOlensEngine=constructor),types.SimpleNamespace(cuda=cuda),'synthetic',cfg)
    def test_smoke50_tp8_has_identical_metrics_and_generation_contract(self):
        a=Engine();b=Engine();b.n_workers=8
        x=smoke50.run50(fixtures(),runtime(),a,'adapter')
        y=smoke50.run50(fixtures(),runtime(),b,'adapter',expected_workers=8)
        for key in ['passed','n','exact_match_count','median_token_set_jaccard','grammar_violation_count','generated_count','read_block']:
            self.assertEqual(x[key],y[key])
        self.assertEqual(a.calls,b.calls)
        with self.assertRaises(ValueError):smoke50.run50(fixtures(),runtime(),Engine(),'adapter',expected_workers=8)
    def test_h200_one_engine_smoke_failure_still_stops_before_capture(self):
        with tempfile.TemporaryDirectory() as td,patch('time.time',return_value=NOW):
            e=Engine();e.n_workers=8;req={'adapter_dir':'adapter','admission_obj':hopper(),'deadline_epoch':NOW+1200,'boot_seconds':0}
            with patch.object(smoke50,'run50',return_value={'passed':False}) as run:
                with self.assertRaises(ValueError):resident.run_resident(req,Path(td),e,runtime(),[],[],[])
            self.assertEqual(run.call_args.kwargs,{'expected_workers':8})
            self.assertFalse((Path(td)/'capture').exists());self.assertFalse(e.calls)
            self.assertTrue(json.loads((Path(td)/'smoke/STATISTICS.json').read_text())['hardware']['undocumented_hardware_path'])
    def test_h200_complete_one_engine_synthetic_lifecycle(self):
        with tempfile.TemporaryDirectory() as td,patch('time.time',return_value=NOW):
            out=Path(td);e=Engine();e.n_workers=8
            items=[{'id':hashlib.sha256(str(i).encode()).hexdigest(),'ids':[10+i,20],'read_position':1} for i in range(6)]
            ids=[x['id'] for x in items[:3]]
            req={'adapter_dir':'adapter','admission_obj':hopper(),'deadline_epoch':NOW+1200,'boot_seconds':0,
                 'source_seal_sha256':'d'*64,'reader_plan_sha256':'c'*64,'go_file':str(out/'GO.json')}
            actual_wait=resident.await_go
            def external_i2(req,out,digest,epoch):
                self.assertTrue((out/'capture/SEAL.json').exists());self.assertFalse((out/'readers').exists())
                ops.write(Path(req['go_file']),go(req,digest,epoch));actual_wait(req,out,digest,epoch)
            with patch.object(resident,'BATCH',3),patch.object(resident,'await_go',external_i2):
                resident.run_resident(req,out,e,runtime(),fixtures(),items,ids)
            self.assertEqual([x[1] for x in e.calls if x[0]=='capture'],[50,3,3])
            self.assertEqual([x[1] for x in e.calls if x[0]=='read'],[50,3])
            self.assertEqual(ops.verify_seal(out/'readers/SEAL.json')['n'],3)
            with self.assertRaises(FileExistsError):resident.run_resident(req,out,e,runtime(),fixtures(),items,ids)
    def test_real_admission_rejects_hopper_before_worker_or_weights(self):
        with tempfile.TemporaryDirectory() as td,patch('time.time',return_value=h.HOPPER_NOT_BEFORE-1):
            a=dict(hopper(),issuer='I-2',experiment='E74',admitted=True,authorized_phases=['weight_staging','resident_smoke_capture'],
                   provider_stop_verified=True,environment_lock_verified=True,environment_lock_sha256='b'*64)
            p=Path(td)/'admission.json';ops.write(p,a)
            with self.assertRaises(ValueError):ops.admission(p,ops.sha(p),'weight_staging')
            req={'admission':str(p),'admission_sha256':ops.sha(p)}
            with patch.object(resident.subprocess,'Popen') as popen:
                with self.assertRaises(ValueError):resident.supervise(req,Path(td)/'run')
                popen.assert_not_called()
            self.assertFalse((Path(td)/'run').exists())
    def test_exact_author_constructor_forwards_tp8_to_stub_llm(self):
        root=Path(__file__).resolve().parents[3]
        path=root/'runtime/olens_glm53_usage.py'
        if not path.exists():path=root/'results/g_agreement/e74/evidence/olens_glm53_usage.py'
        self.assertEqual(ops.sha(path),'ebbd4a1fb0b1cf7673ebbe5e75ee102d6652a789ae3b9f9287c06a9011fcfa42')
        tree=ast.parse(path.read_text());cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='GlmOlensEngine')
        fn=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='__init__')
        llm=Mock(return_value=object());quant=Mock(return_value=75)
        vllm=types.ModuleType('vllm');vllm.LLM=llm
        mm=types.ModuleType('vllm_lens.metamodel');mm.capabilities=lambda obj:dict(hooks_installed=True,num_layers=78,unreduced_layer_output=True,lora_merge=True)
        env={'os':os,'time':time,'log':lambda *a:None,'quant_override_w4a16':quant,'_VllmAdapterLP':type('Stub',(),{}),
             'N_LAYERS':78,'GlmBulletGrammarLP':object,'load_tokenizer':lambda path:object(),
             'lens_prompt_ids':lambda tok:([1]*63+[154518]+[1]*6,63)}
        module=ast.Module(body=[fn],type_ignores=[])
        with patch.dict(sys.modules,{'vllm':vllm,'vllm_lens.metamodel':mm}),patch.dict(os.environ,{},clear=False):
            exec(compile(module,str(path),'exec'),env)
            obj=types.SimpleNamespace();env['__init__'](obj,'synthetic-no-weights',**h.engine_kwargs(h.profile(hopper(),NOW)))
        kw=llm.call_args.kwargs
        self.assertEqual(kw['tensor_parallel_size'],8);self.assertFalse(kw['enable_expert_parallel'])
        self.assertEqual(kw['kernel_config'],{'moe_backend':'marlin'});self.assertEqual(obj.n_workers,8)
        self.assertFalse(kw['enable_prefix_caching']);quant.assert_called_once_with('synthetic-no-weights')


if __name__=='__main__':unittest.main()
