"""CPU checks for the environment/parity evidence before private-label access."""
import copy
from pathlib import Path
import tempfile
import unittest
import analyze as A


class EnvironmentAnalysis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='e28-gate-test-')
        self.root = Path(self.tmp.name)
        self.refs = {'prose_sentiment': .9109977324263039, 'prose_paren': .4846938775510204,
                     'python_string': .6439909297052154}
        A.C.dump(self.root / 'TRAINING_ENVIRONMENT.json', {'synthetic': True})
        A.C.jsonl(self.root / 'PARITY_SCORES.jsonl', [])
        A.C.dump(self.root / 'PARITY_REFERENCE.json', {'reference_auc': self.refs, 'max_abs_auroc_delta': .03,
                                                     'original_e28_input_seal_sha256': 'original'})
        self.parity = {'schema':'E28_PRETRAIN_PARITY_RESULT_v1', 'status':'PASS', 'optimizer_steps_before_gate':0,
            'environment_manifest_sha256': A.C.sha(self.root/'TRAINING_ENVIRONMENT.json'),
            'parity_input_seal_sha256': A.C.read(A.C.HERE/'PARITY_PREPARATION_2026-10-25.json')['parity_input_seal_sha256'],
            'raw_scores_sha256': A.C.sha(self.root/'PARITY_SCORES.jsonl'),
            'reference_sha256': A.C.sha(self.root/'PARITY_REFERENCE.json'), 'completed_epoch':1792900000,
            'rows':{r:{'n':84,'observed':v,'reference':v,'absolute_delta':0,'threshold':.03} for r,v in self.refs.items()}}
        self.ready = {'schema':'E28_TRAINING_ENV_RUNTIME_v1','status':'TRAINING_ENVIRONMENT_READY','device':'cuda',
            'real_cuda_backward':True,'finite_loss':True,'finite_gradients':True,'fresh_lora_only':True,
            'optimizer_steps_in_readiness':1,'environment_manifest_sha256':self.parity['environment_manifest_sha256'],
            'completed_epoch':1792900001,'readiness_deadline_epoch':1793012400}

    def tearDown(self):
        self.tmp.cleanup()

    def check(self):
        A.C.dump(self.root/'PARITY_RESULT.json',self.parity)
        self.ready['parity_result_sha256']=A.C.sha(self.root/'PARITY_RESULT.json')
        A.C.dump(self.root/'ENVIRONMENT_RUNTIME_RESULT.json',self.ready)
        receipt={key:A.C.sha(self.root/name) for name,key in {
            'TRAINING_ENVIRONMENT.json':'environment_manifest_sha256',
            'PARITY_RESULT.json':'parity_result_sha256','PARITY_SCORES.jsonl':'parity_scores_sha256',
            'ENVIRONMENT_RUNTIME_RESULT.json':'environment_runtime_result_sha256'}.items()}
        receipt['parity_input_seal_sha256']=self.parity['parity_input_seal_sha256']
        assignment={'training_environment_sha256':receipt['environment_manifest_sha256'],
                    'parity_input_seal_sha256':receipt['parity_input_seal_sha256'],'input_seal_sha256':'original'}
        return A.validate_operational_gates(self.root,receipt,assignment)

    def test_exact_registered_gate_and_on_time_real_backward_pass(self):
        self.check()

    def test_false_pass_or_training_before_gate_rejected(self):
        for field,value in [('status','FAIL'),('optimizer_steps_before_gate',1)]:
            old=self.parity[field];self.parity[field]=value
            with self.assertRaises(ValueError):self.check()
            self.parity[field]=old
        self.parity['rows']['prose_paren']['observed']+=.031
        self.parity['rows']['prose_paren']['absolute_delta']=.031
        with self.assertRaises(ValueError):self.check()

    def test_cpu_or_late_or_nonfinite_readiness_rejected(self):
        for field,value in [('device','cpu'),('real_cuda_backward',False),('completed_epoch',1793012401),
                            ('completed_epoch',float('inf')),('finite_gradients',False),('fresh_lora_only',False)]:
            old=self.ready[field];self.ready[field]=value
            # The JSON writer itself rejects nonfinite values, which is also safe.
            with self.assertRaises(ValueError):self.check()
            self.ready[field]=old

    def test_reference_cannot_be_replaced_to_make_gate_pass(self):
        self.parity['rows']['prose_sentiment']['reference']=.5
        with self.assertRaises(ValueError):self.check()


if __name__=='__main__':
    unittest.main()
