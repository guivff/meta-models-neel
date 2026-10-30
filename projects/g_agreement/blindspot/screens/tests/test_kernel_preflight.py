import copy
import pytest
from projects.g_agreement.blindspot.screens import kernel_preflight as K


def metadata():
 return {'packages':dict(K.EXPECTED,**{'causal-conv1d':'1.7.0','triton':'3.4.0'}),'system':'Linux','machine':'x86_64','python_minor':'3.12','cxx11_abi':True,'cuda_version':'12.8','cuda_available':True,'device':'NVIDIA H200'}

@pytest.mark.parametrize('name',list(K.EXPECTED)+['causal-conv1d'])
def test_package_upgrade_or_missing_rejected(name):
 m=metadata();K.validate_metadata(m);m['packages'][name]='decoy-version'
 with pytest.raises(ValueError,match=name):K.validate_metadata(m)

@pytest.mark.parametrize('name,value',[('system','Darwin'),('machine','aarch64'),('python_minor','3.11'),('cxx11_abi',False),('cuda_version','12.6')])
def test_wrong_wheel_platform_is_named(name,value):
 m=metadata();m[name]=value
 with pytest.raises(ValueError,match=name):K.validate_metadata(m)

def wrap(module,active=True):
 def implementation():pass
 implementation.__module__=module
 is_new_implementation=active
 def fn():return implementation,is_new_implementation
 return fn

def test_dispatch_requires_actual_fast_closure():
 fs={n:wrap(prefix+'.ops') for n,prefix in K.SYMBOLS.items()}
 assert set(K.dispatch_proof(fs))==set(K.SYMBOLS)
 for name in K.SYMBOLS:
  for decoy in [wrap('transformers.reference',True),wrap(K.SYMBOLS[name]+'.ops',False),None]:
   changed=dict(fs);changed[name]=decoy
   with pytest.raises(ValueError,match=name):K.dispatch_proof(changed)

def test_decorated_fast_closure_and_loop_guard():
 import functools
 fs={n:wrap(prefix+'.ops') for n,prefix in K.SYMBOLS.items()}
 name=next(iter(fs));inner=fs[name]
 @functools.wraps(inner)
 def outer():return inner()
 fs[name]=outer;assert K.dispatch_proof(fs)
 outer.__wrapped__=outer
 with pytest.raises(ValueError,match=name):K.dispatch_proof(fs)

def test_cpu_device_rejected_before_any_forward():
 m=metadata();m['cuda_available']=False
 with pytest.raises(ValueError,match='H200'):K.validate_metadata(m)


def test_wheel_payload_hash_and_coverage_decoys(tmp_path):
 import hashlib,json
 from projects.g_agreement.blindspot.screens.bundle import verify_wheels
 d=tmp_path/'wheels';d.mkdir();p=d/'kernel.whl';p.write_bytes(b'fixed fixture bytes')
 manifest=tmp_path/'manifest.json';manifest.write_text(json.dumps({'files':[{'filename':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}]}))
 assert verify_wheels(d,manifest)=={p.name:p.read_bytes()}
 p.write_bytes(b'changed fixture bytes')
 with pytest.raises(ValueError,match='kernel.whl'):verify_wheels(d,manifest)
 p.write_bytes(b'fixed fixture bytes');(d/'extra.whl').touch()
 with pytest.raises(ValueError,match='extra.whl'):verify_wheels(d,manifest)
 (d/'extra.whl').unlink();p.unlink()
 with pytest.raises(ValueError,match='kernel.whl'):verify_wheels(d,manifest)


def test_science_budget_separates_new_allowance_and_prior_attempts():
 from projects.g_agreement.blindspot.screens import protocol as P
 assert P.PRIOR_SCIENCE_SECONDS==1145.1
 assert P.SCIENCE_SECONDS==7200
 assert P.CAP_SECONDS==P.STAGING_SECONDS+P.SCIENCE_SECONDS+P.RETRIEVAL_SECONDS+P.GUARD_SLACK_SECONDS


def test_parallel_volume_hashes_keep_exact_integrity(tmp_path):
 from concurrent.futures import ThreadPoolExecutor
 import hashlib,time
 from projects.g_agreement.blindspot.screens import stage as S
 volume=tmp_path/'volume';volume.mkdir();jobs=[];expected={};progress=S.Progress(tmp_path/'progress',tmp_path/'own_cache')
 asset={'repo':'fixture/repo','revision':'fixed','hashes':{}}
 for i in range(12):
  p=volume/f'{i}.bin';p.write_bytes(bytes([i])*100);expected[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest();jobs.append((asset,volume,p.name))
 with ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(lambda job:S.verify_volume_file(job,expected,progress,volume,time.time()+60),jobs))
 assert [r['file'] for r in rows]==[j[2] for j in jobs]
 assert progress.completed==len(jobs) and progress.hash_bytes==sum(r['file_bytes'] for r in rows)
 with pytest.raises(ValueError,match='0.bin'):S.verify_volume_file(jobs[0],{**expected,str(volume/'0.bin'):'bad'},progress,volume,time.time()+60)
 with pytest.raises(TimeoutError,match='0.bin'):S.verify_volume_file(jobs[0],expected,progress,volume,0)
 with pytest.raises(ValueError,match='outside'):S.verify_volume_file((asset,volume,'../outside'),expected,progress,volume,time.time()+60)
