import json,datetime,time
from pathlib import Path
import pytest
from . import custody as c,launch as l

def reseal(root):
 out=root/'out';c.write(out/'OUTPUT_SEAL.json',{'files':{str(p.relative_to(out)):c.sha(p) for p in out.rglob('*') if p.is_file() and p.name!='OUTPUT_SEAL.json'}})

def test_exact_P_grid_and_tamper(tmp_path):
 out=tmp_path/'out';out.mkdir();keys=[str(i) for i in range(672)]
 for reader in ['oracle','nla']:
  c.write(out/(reader+'_0000.json'),[{'reader':reader,'item_key':k,'raw':'fixture'} for k in keys])
 c.write(out/'REPORT.json',{'status':'COMPLETE','outputs':1344});reseal(tmp_path)
 assert c.validate(tmp_path,{'phase':'arm_p','item_keys':keys},'H200')['outputs']==1344
 (out/'oracle_0000.json').write_text('[]')
 with pytest.raises(ValueError,match='hash'):c.validate(tmp_path,{'phase':'arm_p','item_keys':keys},'H200')
 reseal(tmp_path)
 with pytest.raises(ValueError,match='grid'):c.validate(tmp_path,{'phase':'arm_p','item_keys':keys},'H200')

def test_gate_raw_bytes_and_frozen_update_proof(tmp_path):
 out=tmp_path/'out';out.mkdir();expected={'phase':'gate','parity':{'compare_indices':[0,1,2],'records':[{'raw':'a'},{'raw':'b'},{'raw':'c'}]}}
 c.write(out/'PARITY_RAW.json',[{'raw':'a'},{'raw':'b'},{'raw':'c'}]);c.write(out/'PARITY.json',[{'byte_equal':True}]*3)
 c.write(out/'PARAMETERS.json',{'new_adapter_rank':16,'base_and_original_adapter_frozen':True,'merge_used':False,'gpu':'NVIDIA H200'})
 for i in range(1,11):c.write(out/f'STEP_{i:02d}.json',{'step':i,'loss':1./i})
 c.write(out/'REPORT.json',{'status':'PASS','steps':10,'frozen_before_sha256':'a'*64,'frozen_after_sha256':'a'*64,'adapter_tensors_changed':1});reseal(tmp_path)
 assert c.validate(tmp_path,expected,'H200')['status']=='PASS'
 c.write(out/'PARITY_RAW.json',[{'raw':'different'},{'raw':'b'},{'raw':'c'}]);reseal(tmp_path)
 with pytest.raises(ValueError,match='byteexact'):c.validate(tmp_path,expected,'H200')

def test_failed_outputs_never_scored(tmp_path):
 out=tmp_path/'out';out.mkdir();c.write(out/'FAILURE.json',{'reason':'NO_FIT'});reseal(tmp_path)
 assert c.validate(tmp_path,{'phase':'arm_p'},'H200')['status']=='NOT_RUN'

def test_duplicate_allocation_stops_before_network(tmp_path,monkeypatch):
 (tmp_path/'CREATE_REQUEST.json').write_text('{}');monkeypatch.setattr(l,'query',lambda q:pytest.fail('network onduplicate'))
 with pytest.raises(ValueError,match='existing'):l.launch(tmp_path)

def test_phase_deadlines_never_renewed():
 source=Path(c.__file__).read_text();assert "s['deadline_epoch']-240" in source and "s['deadline_epoch']-180" in source
 assert 'idle' not in source[source.index('def supervise'):].lower()

def test_failure_archive_before_normal_close(monkeypatch,tmp_path):
 state={'pod_id':'own','status':'RUNNING','ssh':{'publicPort':1},'deadline_epoch':time.time()+1800,'gpu_type':'H200'};c.write(tmp_path/'STATE.json',state);c.write(tmp_path/'EXPECTED_PARITY.json',{'phase':'arm_p'});order=[]
 monkeypatch.setattr(c,'owned',lambda s:{'desiredStatus':'RUNNING'})
 monkeypatch.setattr(c,'ssh',lambda *a,**kw:type('R',(),{'returncode':0,'stdout':'EXITED'})())
 def backup(*a,**kw):order.append('backup');p=tmp_path/'diagnostic';p.write_text('saved');return p
 monkeypatch.setattr(c,'backup',backup);monkeypatch.setattr(c,'close',lambda *a,**kw:order.append('close'))
 c.supervise(tmp_path);assert order==['backup','close'] and (tmp_path/'GATE_VERIFIED.json').exists()

def test_unreported_running_pod_rejected_before_CREATE(tmp_path,monkeypatch):
 c.write(tmp_path/'PREFLIGHT.json',{'phase':'arm_p','files':{}})
 c.write(tmp_path/'ALLOCATION_ADMISSION.json',{'phase':'arm_p','cap_seconds':1800,'launch_admitted':True,'posted_shared_commit':'frozen','as_of_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pod_name':'ours','evidenced_pod_ids':[],'parallel_pod_names':['ours','other_ours']})
 monkeypatch.setattr(l,'query',lambda q:{'myself':{'pods':[{'id':'foreign','name':'unregistered','desiredStatus':'RUNNING','costPerHr':5.29}]},'gpuTypes':[{'securePrice':5.29}]})
 with pytest.raises(ValueError,match='unreconciled'):l.launch(tmp_path)
 assert not (tmp_path/'CREATE_REQUEST.json').exists()
