"""Post-gate E106 leakage, lineage, and fixed-custody boundaries (synthetic only)."""
import json,tempfile,unittest
from pathlib import Path
import numpy as np
from projects.g_agreement.e106.production import verified_gate,check_admission
from projects.g_agreement.e106.finalize_t import finalize
from projects.g_agreement.e96.reconstructor_check import write,digest


def seal(root,name='OUTPUT_SEAL.json',**meta):write(root/name,dict(meta,files={p.name:digest(p) for p in root.iterdir() if p.is_file() and p.name!=name}))


def gate_fixture(root):
    root.mkdir();write(root/'REPORT.json',{'status':'PASS','steps':10,'parity_byte_equal':3,'frozen_before_sha256':'same','frozen_after_sha256':'same','adapter_tensors_changed':1})
    write(root/'PARITY.json',[{'byte_equal':True,'expected_sha256':'x','actual_sha256':'x'} for _ in range(3)])
    for i in range(1,11):write(root/f'STEP_{i:02d}.json',{'loss':1.0/i})
    seal(root)


class ProductionBoundary(unittest.TestCase):
    def test_saved_rank16_reload_preserves_trained_outputs(self):
        import sys,torch
        from peft import get_peft_model,LoraConfig
        from projects.g_agreement.e106.runtime import attach_rank16
        sys.path.insert(0,str(Path('external/mats-nla-workspace/src').resolve()))
        from mats.readers.nla import NLA
        class Tiny(torch.nn.Module):
            def __init__(self):super().__init__();self.q_proj=torch.nn.Linear(5,5);self.layer=torch.nn.Identity()
            def forward(self,x,**kw):return self.layer(self.q_proj(x))
        def fresh():
            torch.manual_seed(11);av=get_peft_model(Tiny(),LoraConfig(r=64,lora_alpha=16,target_modules=['q_proj']))
            nla=NLA(av=av,tok=None,ar=None,value_head=None,meta={},prompt_ids=[1,2,3],marker=1,device='cpu')
            av.base_model.model.layer.register_forward_hook(nla._hook);attach_rank16(nla);return nla
        nla=fresh();x=torch.randn(2,3,5);v=torch.randn(2,5)
        optimizer=torch.optim.AdamW([p for p in nla.av.parameters() if p.requires_grad],lr=1e-4)
        with nla._inject(v):loss=nla.av(x).square().sum()
        loss.backward();optimizer.step();nla.av.eval()
        with nla._inject(v):expected=nla.av(x).detach()
        with tempfile.TemporaryDirectory() as t:
            nla.av.save_pretrained(t,selected_adapters=['e106_repair']);loaded=fresh()
            loaded.av.load_adapter(str(Path(t)/'e106_repair'),adapter_name='e106_repair',is_trainable=False)
            original=next(k for k in loaded.av.peft_config if k!='e106_repair');loaded.av.base_model.set_adapter([original,'e106_repair']);loaded.av.eval()
            with loaded._inject(v):actual=loaded.av(x).detach()
            self.assertTrue(torch.equal(expected,actual))

    def test_nonpass_gate_cannot_release_production(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);gate_fixture(root/'g');p=root/'g/REPORT.json';d=json.loads(p.read_text());d['status']='GATE_DID_NOT_PASS';write(p,d);seal(root/'g')
            with self.assertRaisesRegex(ValueError,'PASS required'):verified_gate(root/'g')

    def test_custody_caps_include_gate_and_prior_teacher_cost(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'in').mkdir();write(root/'in/INPUT_SEAL.json',{'files':{}});gate_fixture(root/'g')
            a={'experiment':'E106','phase':'train','gpu_count':1,'external_guard_armed':True,'incremental_backup_armed':True,'planning_envelope_usd':2000,'input_seal_sha256':digest(root/'in/INPUT_SEAL.json'),'gate_seal_sha256':digest(root/'g/OUTPUT_SEAL.json'),'analysis_adapter_cpu_tests_passed':True,'analysis_adapter_commit':'a'*40,'analysis_adapter_seal_sha256':'b'*64,'created_epoch':1000,'deadline_epoch':4000,'closed_T_custody_seconds':1800,'closed_phase_bucket_seconds':700,'dataset_manifest_commit':'c'*40,'dataset_manifest_sha256':'d'*64}
            with self.assertRaisesRegex(ValueError,'bucket|shared teacher'):check_admission(a,'train',root/'in',root/'g')
            a['closed_phase_bucket_seconds']=600;check_admission(a,'train',root/'in',root/'g')
            a['closed_T_custody_seconds']=12000
            with self.assertRaisesRegex(ValueError,'4GPUh'):check_admission(a,'train',root/'in',root/'g')

    def test_finalizer_rejects_test_teacher_and_preserves_exact_native_targets(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);gate_fixture(root/'g');selection=root/'s';selection.mkdir();teacher=root/'t';teacher.mkdir()
            pairs=[{'key':f'dev:{i}','split':'dev','role':'target' if i<252 else 'replay','text':'- frozen description'} for i in range(504)]
            write(selection/'DEV_PAIRS.json',pairs);np.save(selection/'acts42.npy',np.ones((504,5120),np.float32),allow_pickle=False);seal(selection,'INPUT_SEAL.json')
            records=[{'key':p['key'],'split':'dev','role':'replay','raw':'<explanation>own raw</explanation>'} for p in pairs[252:]]
            records[0]['split']='test';write(teacher/'TEACHER_000.json',records)
            write(teacher/'REPORT.json',{'status':'COMPLETE','items':252,'reader':'nla','original_adapter_sha256':'b54e23e4e36dbd04023b307e3abfd4618b5db2b31b8e7c650a957ebb1c90c358','decoding':{'do_sample':False,'batch':8,'max_new_tokens':512,'stop':'</explanation>'},'first_output_utc':'synthetic'})
            seal(teacher,gate_seal_sha256=digest(root/'g/OUTPUT_SEAL.json'),input_seal_sha256=digest(selection/'INPUT_SEAL.json'))
            with self.assertRaisesRegex(ValueError,'no test substitution'):finalize(selection,teacher,root/'g',root/'out',root/'manifest.json')
            self.assertFalse((root/'out').exists())
            records[0]['split']='dev';write(teacher/'TEACHER_000.json',records);seal(teacher,gate_seal_sha256=digest(root/'g/OUTPUT_SEAL.json'),input_seal_sha256=digest(selection/'INPUT_SEAL.json'))
            finalize(selection,teacher,root/'g',root/'out',root/'manifest.json')
            result=json.loads((root/'out/TRAINING.json').read_text())
            self.assertEqual(result[0]['text'],'<explanation>\n- frozen description\n</explanation>')
            self.assertEqual(result[-1]['text'],'<explanation>own raw</explanation>')
            self.assertEqual(len(result),504)
            self.assertEqual(json.loads((root/'manifest.json').read_text())['test_optimizer_items'],0)

if __name__=='__main__':unittest.main()
