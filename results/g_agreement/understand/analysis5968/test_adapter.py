"""Synthetic sealed pulls only: no production reader output is read."""
import unittest,tempfile,copy
from unittest.mock import patch
import adapter as a
from pathlib import Path

def put(p,x):p.parent.mkdir(parents=True,exist_ok=True);a.dump(p,x)
def fixture(e,path):
 s=a.read(a.HERE/(e+'_SPEC.json'));items,pr=a.inputs(s)
 for k,n in [('receipt','receipt.json'),('cpu_out','cpu'),('probe_capture_receipt','probe_receipt.json'),('blind_out','blind'),('private_key','key.json'),('rubric_out','rubric'),('judgments','judge/JUDGMENTS.json'),('analysis_out','analysis')]:s[k]=str(path/n)
 root=path/'out';cap=root/'capture';cap.mkdir(parents=True);put(cap/'items.order.json',[x['id'] for x in items]);binding=dict(experiment=e,input_seal_sha256=s['input_seal_sha256'],source_seal_sha256=s['worker_source_sha256'],cohort_id=a.COHORT)
 a.seal(cap,'CAPTURE_SEAL.json',binding);cs=a.sha(cap/'CAPTURE_SEAL.json');cpu=Path(s['cpu_out']);cpu.mkdir()
 if e=='E68':
  put(Path(s['probe_capture_receipt']),dict(verified=True,shards={'0':dict(capture=str(cap),capture_seal_sha256=cs)}))
  for l in (42,44):
   scores=[dict(id=x['id'],feature=x['feature']+'|'+x['position'],score=float(pr[x['id']]['label'])) for x in items if x['split']=='test']
   put(cpu/f'PROBE{l}.json',dict(fit_split='dev',eval_split='test',scores=scores,AUROC={x['feature']:1. for x in scores}))
  a.seal(cpu,'PROBE_SEAL.json',dict(private_items_sha256=s['private_items_sha256'],request_sha256=s['request_sha256'],receipt_sha256=a.sha(s['probe_capture_receipt'])))
 else:
  put(cpu/'PROBE.json',[dict(id=x['id'],feature=x['feature'],score=float(pr[x['id']]['label'])) for x in items if x['split']=='test'])
  a.seal(cpu,'CPU_SEAL.json',dict(capture_seal_sha256=cs,private_items_sha256=s['private_items_sha256']))
 def native(x,r):
  return dict(id=x['id']+':'+r+':0',unit_id=x['id'],feature=x['feature'],reader=r,reader_native_layer=44 if r=='oracle' else 42,repeat=0,text='SYNTHETIC value',raw='<explanation>SYNTHETIC value</explanation>')
 if e=='E59':
  a.sys.path.insert(0,str(a.U/'e62/job'));from second_worker import jobs_for
  jobs=jobs_for({e:dict(items=items,acts={42:a.np.empty((len(items),0)),44:a.np.empty((len(items),0))},plan=a.read(Path(s['inputs'])/'PLAN.json'))})
  put(root/'JOB_GRID.json',[{k:v for k,v in j.items() if k!='h'} for j in jobs]);put(root/'COMPLETED.json',list(range(len(jobs))))
  for j in jobs:
   records=[native(x,j['reader']) if j['kind']=='native' else dict(id=x['id'],feature=x['feature'],reader=j['reader'],arm=j['arm'],scores=[float(pr[x['id']]['label'])]*len(j['pairs'])) for x in j['units']]
   put(root/'jobs'/f'{j["number"]:06d}.json',records)
  ass=dict(experiment=e,shard=0,gpu_count=1,pod_id='stub',cohort_id=a.COHORT,compute_cap_seconds=7200,prior_compute_seconds=0,staging_cap_seconds=900,go_wait_cap_seconds=2700,pod_created_epoch=100,staging_start_epoch=100,absolute_deadline_epoch=10900,daily_budget_verified=True,projected_daily_USD=200,dependency_receipt=dict(verified=True,cohort_id=a.COHORT,E57_output_seals=['a'*64,'b'*64,'c'*64]))
  ready=dict(pod_id='stub',cohort_id=a.COHORT,capture_seals={e:cs},input_seals={e:s['input_seal_sha256']},ready_epoch=200)
  go=dict(ready,issued_epoch=300,reader_launch_authorized=True,forecast_commit='d'*40,forecast_seal_sha256='e'*64)
  put(root/'CAPTURE_READY.json',ready);put(root/'GO_RECEIPT.json',go);put(root/'TIMING.json',dict(compute_from_GO=300,deadline_epoch=7500,completed_epoch=7000));put(root/'parity/PARITY_RESULT.json',dict(status='PASS'));put(root/'FORECAST.json',dict(status='ADMIT'))
 else:
  records=[]
  for r in ('oracle','nla'):
   for x in items:
    if x['split']!='test':continue
    v=native(x,r);v.pop('unit_id');v.update(id=x['id'],position=x['position'],base_item_id=x['base_item_id'],source_layer=v['reader_native_layer']);records.append(v)
   put(root/(r+'_STAGE.json'),dict(status='COMPLETE'))
  put(root/'RECORDS.json',records)
  ass=dict(experiment=e,shard=0,pod_id='stub',gpu_count=1,cap_seconds=5664,pod_created_epoch=100,absolute_deadline_epoch=5764,daily_budget_verified=True,projected_daily_USD=200)
 put(root/'ASSIGNMENT.json',ass);a.seal(root,'OUTPUT_SEAL.json',dict(binding,status='COMPLETE',pod_id='stub',capture_seal_sha256=cs))
 receipt=dict(verified=True,experiment=e,output=str(root),pod_id='stub',capture_seal_sha256=cs,output_seal_sha256=a.sha(root/'OUTPUT_SEAL.json'),completion_commit='cc2a1920',completed_epoch=5000);put(Path(s['receipt']),receipt)
 return s

def judging(s,d):
 a.blind(s,d);pack=a.read(Path(s['blind_out'])/'JUDGE_PACKET.json');rows=[]
 for i,p in enumerate(pack):rows.append(dict(id=p['id'],category='UNPARSEABLE' if i==0 else 'states_value',values=[] if i==0 else ['A'],evidence='' if i==0 else 'SYNTHETIC value'))
 put(Path(s['judgments']),rows);a.seal(Path(s['judgments']).parent,'JUDGMENT_SEAL.json',dict(blind_seal_sha256=a.sha(Path(s['blind_out'])/'BLIND_SEAL.json')))
 return a.judgments(s,d)

class Tests(unittest.TestCase):
 def test_complete_sealed_e68_roundtrip(self):
  with tempfile.TemporaryDirectory() as t:
   s=fixture('E68',Path(t));d=a.collect(s);self.assertEqual(len(d['native']),1512);jj=judging(s,d)
   fields=a.read(Path(s['rubric_out'])/'RUBRIC_FIELDS.json');self.assertEqual(set(fields[0]),{'id','property','value_A','value_B','readout'})
   self.assertEqual(len({x['id'] for x in fields}),1512);a.analyze(s,d,jj)
   counts=a.read(Path(s['analysis_out'])/'UNPARSEABLE_COUNTS.json');self.assertEqual(counts['pooled']['UNPARSEABLE'],1)
   with self.assertRaises(FileExistsError):a.analyze(s,d,jj)
 def test_complete_e59_roundtrip(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);s=fixture('E59',p);d=a.collect(s);self.assertEqual(len(d['native']),1008);jj=judging(s,d)
   parent=p/'parent';parent.mkdir();put(parent/'RESULTS.json',dict(R_B=dict(reporting_rows={'oracle':0,'nla':0})));a.seal(parent,'ANALYSIS_SEAL.json',dict(experiment='E57',status='COMPLETE',cohort_id=a.COHORT));s['e57_analysis']=str(parent)
   s['cohort_receipt']=str(p/'cohort.json');put(Path(s['cohort_receipt']),dict(verified=True,cohort_id=a.COHORT,e57_analysis_seal_sha256=a.sha(parent/'ANALYSIS_SEAL.json'),E57_output_seals=d['assignment']['dependency_receipt']['E57_output_seals']))
   jr=p/'j_input';s['j_input']=str(jr);put(jr/'J_ROWS.json',{row:dict(J_label='IN-J') for row in d['probe']});a.seal(jr,'J_SEAL.json',dict(capture_seal_sha256=a.sha(d['cap']/'CAPTURE_SEAL.json'),input_seal_sha256=s['input_seal_sha256']))
   a.analyze(s,d,jj);result=a.read(Path(s['analysis_out'])/'RESULTS.json');self.assertEqual(result['R2_IN_J'],6);self.assertIn('continuation',result)
   with self.assertRaises(FileExistsError):a.analyze(s,d,jj)
 def test_no_output_read_without_probe(self):
  with tempfile.TemporaryDirectory() as t:
   s=fixture('E68',Path(t));(Path(s['cpu_out'])/'PROBE_SEAL.json').unlink();original=a.verify;opened=[]
   def guard(root,name,*args):
    opened.append(name);return original(root,name,*args)
   with patch.object(a,'verify',side_effect=guard):
    with self.assertRaises(FileNotFoundError):a.collect(s)
   self.assertNotIn('OUTPUT_SEAL.json',opened)
 def test_tampered_output_fails(self):
  for e in ('E59','E68'):
   with self.subTest(e=e),tempfile.TemporaryDirectory() as t:
    s=fixture(e,Path(t));r=a.read(s['receipt']);p=Path(r['output'])/('RECORDS.json' if e=='E68' else 'jobs/000000.json');p.write_text('[]')
    with self.assertRaisesRegex(ValueError,'sealed file changed'):a.collect(s)
 def test_duplicate_or_wrong_position_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   s=fixture('E68',Path(t));d=a.collect(s);items,_=a.inputs(s)
   with self.assertRaises(ValueError):a.native_grid(d['native']+[d['native'][0]],items,'E68')
   xs=copy.deepcopy(d['native']);xs[0]['position']='midpoint'
   with self.assertRaises(ValueError):a.native_grid(xs,items,'E68')
 def test_rules_boundaries(self):
  rates={(r,row+'|'+pos):{'S':(.3 if pos=='pre_answer' and row!='topic_twin' else 0)} for r in ('oracle','nla') for row in ('container_after_move','holder_after_handovers','topic_twin') for pos in ('registered','midpoint','pre_answer')}
  self.assertEqual(a.rules68(rates)['oracle']['R_O1'],'MET');rates['oracle','topic_twin|pre_answer']['S']=.15;self.assertEqual(a.rules68(rates)['oracle']['R_O1'],'NOT MET')
  rates['oracle','topic_twin|pre_answer']['S']=0;rates['oracle','holder_after_handovers|pre_answer']['S']=.299;self.assertEqual(a.rules68(rates)['oracle']['R_O1'],'NOT MET')
  rates['oracle','holder_after_handovers|pre_answer']['S']=None;self.assertEqual(a.rules68(rates)['oracle']['R_O1'],'NOT EVALUABLE')
  probe={str(i):.90 for i in range(6)};bow={k:dict(instruction_only_test_auroc=.65) for k in probe};rs={(r,k):dict(S=.2,CI95=[.01,.3]) for r in ('oracle','nla') for k in probe}
  out=a.rules59(probe,bow,rs,dict(oracle=1,nla=2));self.assertEqual(out['readers']['oracle']['R1'],'MET');self.assertEqual(out['readers']['nla']['R1'],'NOT MET')
  bow['0']['instruction_only_test_auroc']=.65001;self.assertFalse(a.rules59(probe,bow,rs,dict(oracle=0,nla=0))['probe_and_BOW_gates']['0'])
if __name__=='__main__':unittest.main()

class CustodyTests(unittest.TestCase):
 def test_bad_go_resealed_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   s=fixture('E59',Path(t));r=a.read(s['receipt']);root=Path(r['output']);outer=a.read(root/'OUTPUT_SEAL.json');go=a.read(root/'GO_RECEIPT.json');go['issued_epoch']=199
   (root/'GO_RECEIPT.json').unlink();put(root/'GO_RECEIPT.json',go);(root/'OUTPUT_SEAL.json').unlink();a.seal(root,'OUTPUT_SEAL.json',{k:v for k,v in outer.items() if k!='files'});r['output_seal_sha256']=a.sha(root/'OUTPUT_SEAL.json');Path(s['receipt']).unlink();put(Path(s['receipt']),r)
   with self.assertRaisesRegex(ValueError,'capture then GO'):a.collect(s)
 def test_e68_wrong_capture_probe_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   s=fixture('E68',Path(t));p=Path(s['probe_capture_receipt']);r=a.read(p);r['shards']['0']['capture_seal_sha256']='0'*64;p.unlink();put(p,r)
   with self.assertRaises(ValueError):a.collect(s)
 def test_held_unparseable_and_pair_order(self):
  a.validate_judgment(dict(id='x',category='states_value',values=['B','A'],evidence='VALUE'),'value')
  from missingness import rate,signed_value
  j=dict(id='x',category='UNPARSEABLE',values=[],evidence='');self.assertIsNone(signed_value(j,1));self.assertIsNone(rate([[None]])['S']);self.assertEqual(rate([[None],[1]])['items'],1)
 def test_sealed_commands_and_inputs(self):
  for e in ('E59','E68'):
   s=a.spec(a.HERE/(e+'_SPEC.json'));items,_=a.inputs(s);self.assertEqual(len(items),1008 if e=='E59' else 1512)
