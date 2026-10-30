"""E106 ordering, prompt preservation, and differentiable injection tests."""
import json,tempfile,time,unittest,sys,copy
from pathlib import Path
from unittest.mock import patch
from projects.g_agreement.e106.worker import admission,full_forecast,setup_binding,gate_work_forecast
from projects.g_agreement.e106 import runtime
from projects.g_agreement.e96.reconstructor_check import write,digest


class Ordering(unittest.TestCase):
    def test_gate_forecast_retains_unknown_work_and_charges_full_remaining_custody(self):
        self.assertEqual(gate_work_forecast(0,1379,300,230,[240],[],9,50)['status'],'TIMING_REQUIRED')
        f=gate_work_forecast(0,1379,400,230,[240],[40],9,50)
        self.assertTrue(f['fits']);self.assertEqual(f['future_upper_seconds'],702.5)
        f=gate_work_forecast(0,1379,800,230,[240],[40],9,50)
        self.assertFalse(f['fits'])

    def test_setup_missing_staging_adds_registered_fallback_or_own_maximum(self):
        profiles={'prior_e106_setup_seconds':{'oracle':[300]},'prior_e106_setup_profiles':{'nla':[{'seconds':400,'includes_staging':True}]}}
        setup,allowance,source=setup_binding(profiles)
        self.assertEqual(allowance,150)
        self.assertEqual(setup,{'oracle':[450],'nla':[400]})
        profiles['measured_e106_staging_seconds']=[100,180]
        setup,allowance,source=setup_binding(profiles)
        self.assertEqual(allowance,180)
        self.assertEqual(setup,{'oracle':[480],'nla':[400]})
        profiles['measured_e106_staging_seconds']=[float('nan')]
        with self.assertRaisesRegex(ValueError,'staging'):setup_binding(profiles)

    def test_independent_gate_accepts_absent_arm_p_but_rejects_expired_deadline(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);inputs=root/'in';inputs.mkdir();write(inputs/'INPUT_SEAL.json',{'files':{}})
            a={'experiment':'E106','phase':'gate','gpu_count':1,'external_guard_armed':True,'incremental_backup_armed':True,'input_seal_sha256':digest(inputs/'INPUT_SEAL.json'),'planning_envelope_usd':2000,'created_epoch':time.time(),'deadline_epoch':time.time()+1700,'arm_p_output_directory':str(root/'missing')}
            a.update(analysis_adapter_cpu_tests_passed=True,analysis_adapter_commit='a'*40,analysis_adapter_seal_sha256='b'*64)
            write(root/'a.json',a)
            self.assertEqual(admission(root/'a.json',inputs,'gate')['phase'],'gate')
            with patch('projects.g_agreement.e106.worker.time.time',return_value=1793278800.):
                with self.assertRaisesRegex(ValueError,'deadline passed'):admission(root/'a.json',inputs,'gate')

    def test_phase_budget_cannot_reset_after_staging(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);write(root/'INPUT_SEAL.json',{'files':{}})
            a={'experiment':'E106','phase':'arm_p','gpu_count':1,'external_guard_armed':True,'incremental_backup_armed':True,'input_seal_sha256':digest(root/'INPUT_SEAL.json'),'planning_envelope_usd':2000,'created_epoch':1.,'deadline_epoch':1802.}
            a.update(analysis_adapter_cpu_tests_passed=True,analysis_adapter_commit='a'*40,analysis_adapter_seal_sha256='b'*64)
            write(root/'a.json',a)
            with self.assertRaisesRegex(ValueError,'phase cap'):admission(root/'a.json',root,'arm_p')

    def test_full_forecast_covers_both_readers_worst_setup_and_elapsed_staging(self):
        f=full_forecast(0,1800,400,{'oracle':[80,200],'nla':[120]},
                        {'oracle':[4],'nla':[20]}, {'oracle':20,'nla':20},1)
        self.assertEqual(f['complete_custody_upper_seconds'],1320)
        self.assertEqual(f['max_measured_setup_seconds'],200)
        self.assertTrue(f['fits'])
        g=full_forecast(0,1800,1000,{'oracle':[80,200],'nla':[120]},
                        {'oracle':[4],'nla':[20]}, {'oracle':20,'nla':20},1)
        self.assertFalse(g['fits'])
        unknown=full_forecast(0,1800,400,{'oracle':[80],'nla':[]},
                        {'oracle':[4],'nla':[]}, {'oracle':20,'nla':21},1)
        self.assertEqual(unknown['status'],'TIMING_REQUIRED')


class Injection(unittest.TestCase):
    def test_real_peft_additive_adapter_preserves_original_and_freezes_it(self):
        import torch
        from peft import get_peft_model,LoraConfig
        sys.path.insert(0,str(Path('external/mats-nla-workspace/src').resolve()))
        from mats.readers.nla import NLA
        class Tiny(torch.nn.Module):
            def __init__(self):super().__init__();self.q_proj=torch.nn.Linear(5,5);self.layer=torch.nn.Identity()
            def forward(self,x,**kw):return self.layer(self.q_proj(x))
        av=get_peft_model(Tiny(),LoraConfig(r=64,lora_alpha=16,target_modules=['q_proj']))
        nla=NLA(av=av,tok=None,ar=None,value_head=None,meta={},prompt_ids=[1,2,3],marker=1,device='cpu')
        av.base_model.model.layer.register_forward_hook(nla._hook)
        x=torch.randn(2,3,5);v=torch.randn(2,5)
        with nla._inject(v):before=av(x).detach()
        trainable=runtime.attach_rank16(nla)
        frozen={n:p.detach().clone() for n,p in av.named_parameters() if n not in trainable}
        with nla._inject(v):after=av(x)
        self.assertTrue(torch.equal(before,after.detach()))
        after.square().sum().backward()
        self.assertTrue(all(p.grad is None for n,p in av.named_parameters() if n not in trainable))
        optimizer=torch.optim.AdamW(list(trainable.values()),lr=1e-4,weight_decay=0.)
        optimizer.step()
        self.assertTrue(all(torch.equal(frozen[n],p.detach()) for n,p in av.named_parameters() if n not in trainable))
        self.assertTrue(any(p.detach().count_nonzero() for n,p in trainable.items() if '.lora_B.' in n))

    def test_native_arithmetic_preserved_and_backward_finite(self):
        import torch
        sys.path.insert(0,str(Path('external/mats-nla-workspace/src').resolve()))
        from mats.readers.nla import NLA
        class Model(torch.nn.Module):
            def __init__(self):super().__init__();self.layer=torch.nn.Identity()
        av=Model();nla=NLA(av=av,tok=None,ar=None,value_head=None,meta={},prompt_ids=[1,2,3],marker=1,device='cpu')
        av.layer.register_forward_hook(nla._hook)
        h=torch.randn(2,3,5);v=torch.randn(2,5)
        with nla._inject(v):original=av.layer(h.clone()).detach()
        runtime.differentiable_hook(nla)
        x=h.clone().requires_grad_(True)
        with nla._inject(v):actual=av.layer(x*1.)
        self.assertTrue(torch.equal(original,actual.detach()))
        actual.square().sum().backward();self.assertTrue(torch.isfinite(x.grad).all())
        with nla._inject(v):
            small=av.layer(torch.ones(2,1,5))
        self.assertTrue(torch.equal(small,torch.ones(2,1,5)))

    def test_nla_prefix_rerenders_marker_without_mutating_original_meta(self):
        import torch
        sys.path.insert(0,str(Path('external/mats-nla-workspace/src').resolve()))
        from mats.readers.nla import NLA
        class Tok:
            def apply_chat_template(self,messages,**kw):return messages[0]['content']
            def encode(self,text,**kw):return ([2,2] if text.startswith('prefix') else [])+[4,9,5]
        meta={'tokens':{'injection_char':'X','injection_token_id':9,'injection_left_neighbor_id':4,'injection_right_neighbor_id':5},'prompt_templates':{'actor':'original {injection_char}'}}
        saved=copy.deepcopy(meta);nla=NLA(av=None,tok=Tok(),ar=None,value_head=None,meta=meta,prompt_ids=[4,9,5],marker=1,device='cpu')
        runtime.prefix_nla(nla,'prefix\n')
        self.assertEqual(nla.marker,3);self.assertEqual(meta,saved)
        self.assertTrue(nla.meta['prompt_templates']['actor'].endswith('original {injection_char}'))

if __name__=='__main__':unittest.main()
