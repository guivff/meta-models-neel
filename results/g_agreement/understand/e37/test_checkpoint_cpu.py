"""Synthetic CPU coverage for clarification 3; never scores an E37 item."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import torch
from safetensors.torch import save_file

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('cpu_test',HERE/'checkpoint_cpu.py')
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)

def unverified_fixture():
    hf=C.read(C.MANIFEST)['readers']['olens_s3d_student_step251']
    return {'schema':'E37_CPU_CHECKPOINT_SELECTION_v1','manifest_sha256':C.sha(C.MANIFEST),
        'hf_adapter_sha256':hf['adapter_model_sha256'],'cpu_only':True,'model_forwards':0,
        'anonymous_single_file_only':True,'readme_identity_claim_verified':False,
        'download':{'status':'NOT_POSSIBLE','anonymous':True,'file_requests':1,'http_status':401},
        'comparison':None,'selected_branch':'lora_hf_UNVERIFIED','received_epoch':1000,
        'selected_files':{'adapter_model.safetensors':hf['adapter_model_sha256'],'adapter_config.json':hf['adapter_config_sha256']}}

class IdentityTests(unittest.TestCase):
    def test_names_shapes_dtypes_values_and_missing_tensors(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a',Path(d)/'b';x=torch.arange(8).reshape(2,4).float()
            save_file({'base_model.model.model.layers.0.q_proj.lora_A.default.weight':x},str(a))
            key='base_model.model.model.language_model.layers.0.q_proj.lora_A.weight'
            save_file({key:x},str(b));self.assertTrue(C.compare_tensors(a,b)['all_equal'])
            for y in (x+1,x.double(),x.reshape(4,2)):
                save_file({key:y},str(b));self.assertFalse(C.compare_tensors(a,b)['all_equal'])
            save_file({key:x,'different.lora_B.weight':x.clone()},str(b));self.assertFalse(C.compare_tensors(a,b)['all_equal'])

    def test_collision_and_corrupt_files_stop(self):
        with tempfile.TemporaryDirectory() as d:
            a,b=Path(d)/'a',Path(d)/'b';x=torch.ones(2,2)
            save_file({'model.q.lora_A.weight':x,'base_model.model.q.lora_A.weight':x.clone()},str(a))
            save_file({'q.lora_A.weight':x},str(b))
            with self.assertRaises(ValueError):C.compare_tensors(a,b)
            a.write_bytes(b'corrupt')
            with self.assertRaises(Exception):C.compare_tensors(a,b)

    def test_three_preparation_branches_and_corrupt_not_fallback(self):
        for mode in ('same','differ','unavailable','corrupt'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
                root=Path(d)/'cache';root.mkdir();hf=root/'hf';hf.mkdir();x=torch.ones(2,2)
                save_file({'base_model.model.model.q_proj.lora_A.weight':x},str(hf/'adapter_model.safetensors'))
                (hf/'adapter_config.json').write_text('{"peft_type":"LORA","r":2,"target_modules":["q_proj"]}')
                manifest=C.read(C.MANIFEST);pin=manifest['readers']['olens_s3d_student_step251']
                pin['adapter_model_sha256']=C.sha(hf/'adapter_model.safetensors');pin['adapter_config_sha256']=C.sha(hf/'adapter_config.json')
                mf=root/'manifest.json';mf.write_text(json.dumps(manifest))
                def fake_download(dest,pin):
                    if mode=='unavailable':return {'status':'NOT_POSSIBLE','anonymous':True,'file_requests':1}
                    if mode=='corrupt':dest.write_bytes(b'bad')
                    else:save_file({'base_model.model.model.q_proj.lora_A.default.weight':x+(mode=='differ')},str(dest))
                    return {'status':'DOWNLOADED','sha256':C.sha(dest),'anonymous':True,'file_requests':1}
                with patch.object(C,'MANIFEST',mf),patch.object(C,'download_one',side_effect=fake_download):
                    if mode=='corrupt':
                        with self.assertRaises(Exception):C.prepare(hf,root/'out',1000)
                        self.assertFalse((root/'out/CHECKPOINT_RECEIPT.json').exists())
                    else:
                        result=C.prepare(hf,root/'out',1000)
                        self.assertEqual(result['selected_branch'],{'same':'lora_hf_MATCH','differ':'lora_EXACT_RL_INIT','unavailable':'lora_hf_UNVERIFIED'}[mode])
                        C.validate_selection(result,root/'out/selected')
                        (root/'out/selected/adapter_model.safetensors').write_bytes(b'drift')
                        with self.assertRaises(ValueError):C.validate_selection(result,root/'out/selected')

    def test_selection_receipt_tampering_rejected(self):
        r=unverified_fixture();C.validate_selection(r,check_files=False)
        for change in ({'selected_branch':'lora_hf_MATCH'},{'model_forwards':1},{'cpu_only':False},{'readme_identity_claim_verified':True}):
            with self.subTest(change=change),self.assertRaises(ValueError):C.validate_selection({**r,**change},check_files=False)

    def test_download_refuses_repository_or_wrong_path(self):
        source=C.read(C.MANIFEST)['comparison_source']
        for change in ({'repo_type':'model'},{'revision':'main'},{'file':'optim.pt'}):
            with self.assertRaises(ValueError):C.download_one(Path('/never'),{**source,**change})

if __name__=='__main__':unittest.main()
