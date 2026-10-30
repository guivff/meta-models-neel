import datetime,json,pathlib,hashlib,math,os,time
import pytest
from projects.g_agreement.e102 import gate_custody as g

def fixture(root):
 out=root/'out';out.mkdir();expected=[{'id':str(i),'expected_text':'- sealed '+str(i)} for i in range(3)]
 parity=[{'id':x['id'],'actual':x['expected_text'],'expected_sha256':hashlib.sha256(x['expected_text'].encode()).hexdigest(),'byte_equal':True} for x in expected]
 g.write(out/'PARAMETERS.json',{'gpu':'NVIDIA B200','base_requires_grad':False,'trainable_names':['m.lora_A.default.weight']})
 g.write(out/'PARITY.json',parity);pt=(out/'PARITY.json').stat().st_mtime
 g.write(out/'LOSS.json',[{'step':i,'loss':.1,'utc':datetime.datetime.fromtimestamp(pt+1+i,datetime.timezone.utc).isoformat()} for i in range(1,11)])
 g.write(out/'REPORT.json',{'status':'PASS','steps':10,'base_before_sha256':'a'*64,'base_after_sha256':'a'*64,'adapter_tensors_changed':1})
 reseal(root);return expected

def reseal(root):
 out=root/'out';g.write(out/'OUTPUT_SEAL.json',{'files':{p.name:g.sha(p) for p in out.iterdir() if p.is_file() and p.name!='OUTPUT_SEAL.json'}})

def test_exact_greedy_bytes_and_frozen_base_proof(tmp_path):
 expected=fixture(tmp_path);r=g.validate(tmp_path,expected,'B200');assert r['status']=='PASS' and r['greedy_reproductions']==3 and r['steps']==10
 assert all(x['first_divergence_utf8_byte'] is None for x in r['sealed_greedy_comparison'])

@pytest.mark.parametrize('failure',['changed-base','early-step','nan-loss','wrong-parity'])
def test_gate_evidence_failures_cannot_pass(tmp_path,failure):
 expected=fixture(tmp_path);out=tmp_path/'out'
 if failure=='changed-base':
  p=out/'REPORT.json';d=json.loads(p.read_text());d['base_after_sha256']='changed';g.write(p,d)
 elif failure in ('early-step','nan-loss'):
  p=out/'LOSS.json';d=json.loads(p.read_text());d[0]['utc']='2000-01-01T00:00:00+00:00' if failure=='early-step' else d[0]['utc']
  if failure=='nan-loss':d[0]['loss']=float('nan')
  g.write(p,d)
 else:
  p=out/'PARITY.json';d=json.loads(p.read_text());d[0]['actual']='different';g.write(p,d)
 reseal(tmp_path)
 with pytest.raises(ValueError):g.validate(tmp_path,expected,'B200')

def test_worker_failure_is_archived_not_a_pass(tmp_path):
 expected=fixture(tmp_path);g.write(tmp_path/'out/FAILURE.json',{'type':'RuntimeError','reason':'sealed parity mismatch'});reseal(tmp_path)
 r=g.validate(tmp_path,expected,'B200');assert r['status']=='GATE_DID_NOT_PASS' and r['training_admitted'] is False

def test_first_divergence_uses_utf8_bytes():
 assert g.divergence('éa','éb')==2 and g.divergence('abc','ab')==2 and g.divergence('same','same') is None

def test_explicit_load_exit_is_pulled_before_stop(monkeypatch,tmp_path):
 g.write(tmp_path/'STATE.json',{'created_epoch':time.time(),'pod_id':'owned','gpu_type':'B200','ssh':{'publicPort':22}});g.write(tmp_path/'EXPECTED_PARITY.json',[])
 monkeypatch.setattr(g,'owned',lambda s:{'desiredStatus':'RUNNING'});monkeypatch.setattr(g,'ssh',lambda *a,**k:type('R',(),{'stdout':'EXITED','returncode':0})());order=[];archive=tmp_path/'diagnostics.tar.gz';archive.write_bytes(b'fixture')
 def backup(*a,**k):order.append('backup');return archive
 monkeypatch.setattr(g,'backup',backup)
 def close(root,s,verified,reason):assert (root/'GATE_VERIFIED.json').exists();assert verified;order.append('stop')
 monkeypatch.setattr(g,'close',close);g.supervise(tmp_path);assert order==['backup','stop']

def test_hardstop_keeps_original_creation_and_does_not_block_on_backup(monkeypatch,tmp_path):
 created=time.time()-3400;g.write(tmp_path/'STATE.json',{'created_epoch':created});seen=[]
 monkeypatch.setattr(g,'backup',lambda *a,**k:pytest.fail('blocking harddeadline backup'))
 monkeypatch.setattr(g,'close',lambda root,s,verified,reason:seen.append(s['created_epoch']))
 g.hardstop(tmp_path);assert seen==[created]
