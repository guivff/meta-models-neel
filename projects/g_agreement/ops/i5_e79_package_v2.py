"""Administrative E79 v2 exact-runtime packaging; no model/test/statistics call.
Preserves historical v1 and original inputs, adds frozen hardware dependencies.
"""
from pathlib import Path
import json,hashlib,shutil,tarfile,gzip,subprocess,os,datetime
ROOT=Path.cwd();BASE=ROOT/'cache/g_agreement/understand/e79_extension/package_v1';DEST=BASE.parent/'package_v2'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def main():
 assert not DEST.exists(),'inspect existing v2; never rebuild silently'
 old=read(ROOT/'results/g_agreement/understand/e79_extension/I5_EXACT_PREFLIGHT.json');assert sha(BASE/'source.tar.gz')==old['source_archive_sha256']and sha(BASE/'inputs.tar.gz')==old['input_archive_sha256']
 source=BASE/'source';seal=read(source/'E79_EXTENSION_SOURCE.json')
 for n,h in seal['files'].items():assert sha(source/n)==h,n
 hardware=read(ROOT/'results/g_agreement/understand/e79_extension/I5_HARDWARE_CPU_CODE_SEAL.json')
 for n,h in hardware['files'].items():assert sha(ROOT/n)==h,n
 fixtures=ROOT/'cache/g_agreement/understand/e97/reader_smoke_reference'
 for n,h in hardware['reference_fixture_hashes'].items():assert sha(fixtures/n)==h,n
 DEST.mkdir();os.chmod(DEST,0o700);runtime=DEST/'source';shutil.copytree(source,runtime)
 for n in hardware['files']:
  p=runtime/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,p)
 for n in hardware['reference_fixture_hashes']:
  p=runtime/'hardware_reference'/n;p.parent.mkdir(exist_ok=True);shutil.copyfile(fixtures/n,p)
 sealpath=runtime/'E79_EXTENSION_SOURCE.json'
 files={str(p.relative_to(runtime)):sha(p)for p in sorted(runtime.rglob('*'))if p.is_file()and p!=sealpath}
 assert len(files)==103,(len(files),'expected97+4hardwaredependencies+2fixtures')
 new=dict(experiment='E79_extension',stage='V2_EXACT_RUNTIME_HARDWARE_INCLUDED_NO_ALLOCATION',files=files,original_worker_sha256='721ce7680400df9a96b0ce1e54ea944a5c080acd94335bed08006d790a9a8f0c',original_v1_archive_sha256=old['source_archive_sha256'],native_one_unchanged=True,manipulation_rerun=False,first_output_utc='unknown',model_calls=0)
 sealpath.write_text(json.dumps(new,indent=2,sort_keys=True)+'\n')
 archive=DEST/'source.tar.gz'
 with archive.open('wb')as raw:
  with gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0)as gz:
   with tarfile.open(fileobj=gz,mode='w',format=tarfile.PAX_FORMAT)as tf:
    for p in sorted(runtime.rglob('*')):
     if not p.is_file():continue
     info=tf.gettarinfo(str(p),arcname=str(p.relative_to(runtime)));info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
     with p.open('rb')as f:tf.addfile(info,f)
 fresh=DEST/'fresh_import';fresh.mkdir()
 with tarfile.open(archive)as tf:
  members=tf.getmembers();assert len(members)==104 and all(m.isfile()and not Path(m.name).is_absolute()and'..'not in Path(m.name).parts for m in members)
  tf.extractall(fresh,filter='data')
 assert sha(fresh/'E79_EXTENSION_SOURCE.json')==sha(sealpath)
 for n,h in files.items():assert sha(fresh/n)==h,n
 env=os.environ.copy();env.update(PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONPATH=str(fresh))
 py='/Users/guivff/Documents/Neel_Exploration/activation-readers/.venv/bin/python3.12'
 script='from projects.g_agreement.e79_extension.runner import original; original(); from projects.g_agreement.e79_extension.hardware import backend; from projects.g_agreement.e97.hardware import smoke; from projects.g_agreement.e97.capture42 import load_b200; from projects.g_agreement.blindspot import run; print("E79_V2_FRESH_EXACT_IMPORT_PASS_NO_MODEL_LOAD")'
 done=subprocess.run([py,'-B','-c',script],cwd=fresh,env=env,capture_output=True,text=True,timeout=120);(DEST/'CPU_IMPORT.stdout').write_text(done.stdout);(DEST/'CPU_IMPORT.stderr').write_text(done.stderr);assert done.returncode==0,done.stderr[-1200:]
 receipt=dict(experiment='E79_extension',status='V2_EXACT_ARCHIVE_IMPORT_PASS_NO_ALLOCATION',at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_archive=str(archive),source_archive_sha256=sha(archive),source_seal_sha256=sha(sealpath),runtime_members=103,archive_members=104,source_hashes_verified=True,archive_fresh_extract_hashes_verified=True,unchanged_input_archive=str(BASE/'inputs.tar.gz'),unchanged_input_archive_sha256=sha(BASE/'inputs.tar.gz'),historical_v1_preserved=True,hardware_cpu_code_seal_sha256=sha(ROOT/'results/g_agreement/understand/e79_extension/I5_HARDWARE_CPU_CODE_SEAL.json'),hardware_reference_files=hardware['reference_fixture_hashes'],hardware_reference_runtime_path='hardware_reference',CPU_IMPORT=done.stdout.strip(),existing6CPUtests_not_repeated=True,model_calls=0,GPU_allocations=0,native_outputs=0,manipulation_rerun=False,first_output_utc='unknown',registered_creation_upper_seconds=7200,launch_allowed=False,pending=['Durable controller/asset binding/dual provider stops/final PAX lifecycle','Current §217 measured setup+1.25work production timing admission within7200upper','Current ordered CORE/parked pool/provider fresh financial admission'],builder_source_sha256=sha(__file__))
 p=ROOT/'results/g_agreement/understand/e79_extension/I5_V2_EXACT_PACKAGE_CPU_RECEIPT.json';p.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
