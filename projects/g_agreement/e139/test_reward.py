import unittest,numpy as np
from .reward import whiten,joint_proxy,joint_audit_four,summarize,whitened_fve,primary_four,delta_u
class Tests(unittest.TestCase):
 def test_analytic_joint_and_nonnegative(self):
  x=np.array([1.,1.]);self.assertAlmostEqual(joint_proxy([[1,0]],x),.5)
  self.assertAlmostEqual(joint_proxy([[1,0],[0,1]],x),1.)
  self.assertAlmostEqual(joint_proxy([[-1,0]],x),0.)
 def test_whitening_applied_once_to_both(self):
  mu=np.array([1.,2.]);w=np.diag([2.,3.]);raw=np.array([[2.,4.]])
  np.testing.assert_array_equal(whiten(raw,mu,w),[[2.,6.]])
  self.assertAlmostEqual(joint_proxy(whiten(raw,mu,w),whiten(raw,mu,w)[0]),1.)
 def test_append_not_dropped(self):
  r=joint_audit_four([[1,0]]*4,[0,1],[-1,0],[1,0],[1,1]);self.assertGreater(r['true'],r['neutral']);self.assertAlmostEqual(r['neutral'],.5)
 def test_gate_fail_closed(self):
  states=('nesting_depth','inside_string','table_column','language','fact_recall','evaluation_cue')
  rows=[dict(id=f'{s}:{i}',state=s,scores=dict(original=.2,true=.3,false=.3,neutral=.3)) for s in states for i in range(20)]
  self.assertEqual(summarize(rows,20)['instrument_gate'],'NOT EVALUABLE (instrument)')
  for r in rows:
   if r['state']=='language':r['scores']['true']=.5
  self.assertEqual(summarize(rows,20)['instrument_gate'],'PASS')
 def test_nonfinite_rejected(self):
  with self.assertRaises(ValueError):joint_proxy([[float('nan'),0]],[1,1])
 def test_primary_whitened_proxy(self):
  self.assertEqual(whitened_fve([1,1],[1,1]),1.)
  self.assertEqual(whitened_fve([0,0],[1,1]),0.)
  self.assertEqual(whitened_fve([1,0],[1,1]),.5)
  self.assertEqual(whitened_fve([-1,-1],[1,1]),-3.)
 def test_original_target_not_mean_normalized(self):
  self.assertAlmostEqual(joint_proxy([[1,0]],[2,1]),.8)
if __name__=='__main__':unittest.main()

class SourcePinTests(unittest.TestCase):
 def test_released_math_pin_and_proxy_disclosure(self):
  import json,hashlib,ast
  from pathlib import Path
  pin=json.loads(Path(__file__).with_name('REWARD_PIN.json').read_text())
  for e in pin['evidence']:self.assertEqual(hashlib.sha256(Path(e['path']).read_bytes()).hexdigest(),e['sha256'])
  self.assertEqual(pin['primary_score_label'],'proxy reward')
  reward=next(Path(e['path']).read_text() for e in pin['evidence'] if e['path'].endswith('released_rl_reward.py'))
  self.assertIn('recon.layer_emb.weight',reward);self.assertIn('_, fve_full = nnls_refit',reward)
  nnls=next(Path(e['path']).read_text() for e in pin['evidence'] if e['path'].endswith('/nnomp.py'))
  f=next(n for n in ast.parse(nnls).body if isinstance(n,ast.FunctionDef) and n.name=='_nnls_batched')
  self.assertTrue(any(isinstance(n,ast.Constant) and n.value==80 for n in f.args.kw_defaults))

class Clarification1Tests(unittest.TestCase):
 def test_direction_gap_and_no_reward_substitution(self):
  base=np.zeros((20,2));dev=np.array([[0,0],[0,0],[2,0],[2,0]])
  app={'true':base+[1,7],'false':base+[-1,0],'neutral':base+[0,9]}
  out=delta_u(dev,[0,0,1,1],base,app,draws=30)
  self.assertEqual(out['dev_class_counts'],[2,2])
  self.assertEqual(out['dev_class_gap_norm'],2.)
  self.assertEqual(out['conditions']['true']['mean'],.5)
  self.assertEqual(out['conditions']['true']['CI95'],[.5,.5])
  self.assertEqual(out['conditions']['false']['mean'],-.5)
  self.assertEqual(out['conditions']['neutral']['mean'],0.)
  # Orthogonal displacement changes reconstruction FVE, not Delta_u.
  self.assertNotEqual(whitened_fve([1,7],[2,0]),.5)
 def test_zero_gap_and_incomplete_rebuilds_fail_closed(self):
  base=np.zeros((20,2));app={x:base for x in ('true','false','neutral')}
  with self.assertRaises(ValueError):delta_u([[1,0],[1,0]],[0,1],base,app)
  with self.assertRaises(ValueError):delta_u([[0,0],[1,0]],[0,1],base[:19],app)
  app['true']=np.full((20,2),float('nan'))
  with self.assertRaises(ValueError):delta_u([[0,0],[1,0]],[0,1],base,app)
 def test_primary_whole_strings_distinct_from_joint_audit(self):
  scores=primary_four(dict(original=[0,0],true=[1,1],false=[-1,-1],neutral=[1,0]),[1,1])
  self.assertEqual(scores,dict(original=0.,true=1.,false=-3.,neutral=.5))
