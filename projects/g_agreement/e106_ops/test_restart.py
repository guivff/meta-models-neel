import unittest,importlib.util,sys,pathlib,subprocess,ast,shlex,tempfile
HERE=pathlib.Path(__file__).parent
spec=importlib.util.spec_from_file_location('custody',HERE/'custody_restart.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c);sys.modules['custody']=c
spec=importlib.util.spec_from_file_location('stage_restart',HERE/'stage_restart.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
class RestartTests(unittest.TestCase):
 def test_preload_smoke_before_model_and_no_guard_override(self):
  z=s.restart_script('gate')
  self.assertLess(z.index('backend_install.py'),z.index('backend_smoke.py'));self.assertLess(z.index('backend_smoke.py'),z.index('-m projects.g_agreement.e106.worker'))
  self.assertIn('unset FLA_TILELANG FLA_DISABLE_BACKEND_DISPATCH',z);self.assertNotIn('pip install torch',z)
  self.assertIn('set -e',z);self.assertIn('WORKER_EXIT.json',z)
 def test_both_scripts_parse_and_deadline_not_reset(self):
  for phase in ['gate','arm_p']:
   z=s.restart_script(phase);p=subprocess.run(['bash','-n'],input=z,text=True,capture_output=True);self.assertEqual(p.returncode,0,p.stderr)
   self.assertIn("created_epoch",z);self.assertNotIn("deadline_epoch",z)
   for line in z.splitlines():
    if line.startswith('/weights/venv-kernels/bin/python -c '):ast.parse(shlex.split(line)[2])
 def test_p_uses_separate_retime_no_backend(self):
  z=s.restart_script('arm_p');self.assertIn('-m projects.g_agreement.e106.p_retime',z);self.assertNotIn('backend_install',z)
 def test_large_fixed_payload_transfer_gets_bounded_360_seconds(self):
  z=(HERE/'stage_restart.py').read_text();self.assertIn('min(360 if transfer else 120,left)',z);self.assertIn('timeout=budget(transfer=True)',z);self.assertIn("s['deadline_epoch']-300",z)
 def test_b200_native_smoke_no_hopper_overlay(self):
  z=s.restart_script('gate','B200');self.assertIn('--hardware B200',z);self.assertNotIn('backend_install.py',z);self.assertNotIn('tilelang-final/site',z)
  self.assertLess(z.index('backend_smoke.py'),z.index('-m projects.g_agreement.e106.worker'))
  self.assertEqual(subprocess.run(['bash','-n'],input=z,text=True,capture_output=True).returncode,0)
 def test_gate_only_hardware_launcher_prices_and_source_proof_custody(self):
  z=(HERE/'launch_hardware.py').read_text();ast.parse(z);self.assertIn("pre['phase']!='gate'",z);self.assertIn("Decimal('7.99')",z);self.assertIn("'NVIDIA '+hardware",z)
  self.assertIn('GPU_SMOKE.TARGET.json',(HERE/'custody_restart.py').read_text())
 def test_custody_preserves_operational_evidence(self):
  z=(HERE/'custody_restart.py').read_text();self.assertIn("'GPU_SMOKE.json'",z);self.assertIn("r/'operational_backend'",z);self.assertIn("s['deadline_epoch']-180",z)
if __name__=='__main__':unittest.main()
