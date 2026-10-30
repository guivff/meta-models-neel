from pathlib import Path
import sys,json,tarfile,hashlib,shutil,datetime,decimal,os
import numpy as np
sys.path.insert(0,'projects/g_agreement/ops');import i5_controller as C
r=Path('/Users/guivff/repl/activation-readers-i5/e98-capture-20261029-a1');p=C.read(r/'PLAN.json')
root=Path('cache/g_agreement/understand/e98/capture_v1');assert not(root/'PUBLICATION.json').exists();root.mkdir(parents=True,exist_ok=True);os.chmod(root,0o700)
archive=next((x for x in [r/'final.pax.tar.gz',r/'final.pax.tar.gz.part']if x.exists()),None);assert archive
# Copy a complete, immutable permanent archive before any controller cleanup. Stream all bytes once, no random gzip seeks.
permanent=root/'capture_verified.pax.tar.gz';shutil.copy2(archive,permanent);os.chmod(permanent,0o600)
hashes={};meta={};first=None;ids=[]
with tarfile.open(permanent,'r|gz')as t:
 for m in t:
  if not m.isfile():continue
  assert not m.name.startswith('/')and'..'not in Path(m.name).parts
  data=t.extractfile(m).read();hashes[m.name]=hashlib.sha256(data).hexdigest()
  dst=root/m.name;dst.parent.mkdir(parents=True,exist_ok=True);os.chmod(dst.parent,0o700);dst.write_bytes(data);os.chmod(dst,0o600)
  if m.name.startswith('out/records/'):
   a=np.load(dst,allow_pickle=False);assert a.shape==(2560,)and a.dtype==np.dtype('float32')and np.isfinite(a).all();ids.append(dst.stem)
   ns=int(decimal.Decimal(m.pax_headers.get('mtime',str(m.mtime)))*1000000000)
   if first is None or ns<first['mtime_ns']:first=dict(path=m.name,mtime_ns=ns,pax_mtime=m.pax_headers.get('mtime',str(m.mtime)))
seal=C.read(root/'out/CAPTURE_SEAL.json');assert seal['status']=='COMPLETE'and seal['experiment']=='E98'and seal['layer']==18 and seal['reader_outputs_opened']is False
assert seal['card_sha256']==p['card_sha256']and seal['input_sha256']==p['input_sha256']
assert all(hashes['out/'+n]==h for n,h in seal['files'].items());assert {n[4:]for n in hashes if n.startswith('out/')and n!='out/CAPTURE_SEAL.json'}==set(seal['files'])
assert len(ids)==4368 and set(ids)==set(p['item_ids'])
public=Path('results/g_agreement/sealed/E98_CAPTURE');assert not(public/'SEAL.json').exists();public.mkdir(parents=True,exist_ok=True)
for path in (root/'out').iterdir():
 if path.is_file():shutil.copy2(path,public/path.name)
for n in ['assignment.json','HARDWARE.json','worker.log']:shutil.copy2(root/n,public/n)
code=public/'code';code.mkdir(exist_ok=True)
for n in ['controller.py','i5_controller.py']:shutil.copy2(r/n,code/n)
with tarfile.open(r/'source.tar.gz')as t:
 for m in t:
  if m.isfile():
   dest=code/'exact_source'/m.name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(t.extractfile(m).read())
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
receipt=dict(experiment='E98',phase='capture',status='COMPLETE',timestamp_utc=now,source_admission_commit='27d6d66f34908b4005d2530479705e86471f0085',launch_commit='40b4a54a7b768cf50629b3f33552f6ea8ab34091',authorization=p['authorization_commit'],items=4368,test_items=2184,dropped_rows=[],site=18,shape=[4368,2560],dtype='float32',all_finite=True,exact_public_order_and_ids=True,all_member_hashes_verified=True,card_sha256=p['card_sha256'],input_sha256=p['input_sha256'],worker_sha256=p['worker_sha256'],capture_seal_sha256=C.sha(root/'out/CAPTURE_SEAL.json'),pax_sha256=C.sha(permanent),permanent_archive=str(permanent.resolve()),private_raw_root=str((root/'out').resolve()),first_output_utc='unknown',first_output_evidence=seal['first_output_evidence'],first_capture_file=first,first_capture_utc=datetime.datetime.fromtimestamp(first['mtime_ns']/1e9,datetime.timezone.utc).isoformat(),hardware=C.read(root/'HARDWARE.json'),R3b_readers_opened=False,cleanup_and_cost_closeout='PENDING original controller archive verification; not rebooked; active7.29reserved',registered_model='Qwen/Qwen3-4B@1cfa9a7208912126459214e8b04321603b3df60c',jlens='neuronpedia/jacobian-lens@e166deb5ad540932100ef803c8c9bcc2a5453694',jlens_sha256='9c94a43ac2db2debbab36acb74480f49a3ac411fb3d7fa8e5461377028e74606')
C.write(public/'CAPTURE_RECEIPT.json',receipt);C.write(root/'PUBLICATION.json',receipt)
C.write(public/'SEAL.json',dict(experiment='E98',phase='capture',status='COMPLETE',timestamp_utc=now,files={str(x.relative_to(public)):C.sha(x)for x in public.rglob('*')if x.is_file()and x.name!='SEAL.json'},first_output_utc='unknown',first_capture_file=first))
# durable administrator helper retains exact executed source.
shutil.copy2('/private/tmp/e98_capture_seal.py',r/'capture_publication.py')
print(json.dumps({k:receipt[k]for k in ['status','items','capture_seal_sha256','pax_sha256','first_capture_utc','first_output_utc']}))
