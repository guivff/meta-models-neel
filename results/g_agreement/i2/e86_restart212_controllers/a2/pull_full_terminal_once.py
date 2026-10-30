"""Read-only terminal pull: preserve bytes, verify every sealed output hash."""
import json,subprocess,hashlib,tarfile,os,sys
from pathlib import Path
HOME=Path(__file__).resolve().parent
sys.path.insert(0,str(HOME))
import stage_and_start as st
s=st.state();remote=s['remote_dir'];host,port=s['address'].split(':');dest=HOME/'full_terminal_pull';dest.mkdir(exist_ok=False)
program=f'''cd {remote}
/weights/venv-kernels/bin/python - <<'REMOTE'
import json,tarfile,sys,io
from pathlib import Path
assert json.loads(Path('EXIT_FULL.json').read_text())['code']==0 and json.loads(Path('full_outputs/OUTPUT_SEAL.json').read_text())['status']=='COMPLETE'
files=[p for p in Path('full_outputs').rglob('*') if p.is_file()]+[Path('EXIT_FULL.json'),Path('RUNTIME_STAGING.json'),Path('assignment_full.json')]
assert sum(p.stat().st_size for p in files)<600*1024*1024
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as t:
 for p in sorted(files):
  assert not p.is_symlink();t.add(p,arcname=str(p),recursive=False)
REMOTE
'''
args=['ssh','-i',str(st.KEY),'-p',port,'-o','BatchMode=yes','-o','ConnectTimeout=15','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null','root@'+host,'bash -s']
archive=HOME/'FULL_TERMINAL_PULL.private.tar'
with archive.open('xb') as out:
 r=subprocess.run(args,input=program.encode(),stdout=out,stderr=subprocess.PIPE,timeout=180)
assert r.returncode==0,'TERMINAL_PULL_FAILED'
with tarfile.open(archive) as t:
 for m in t.getmembers():
  p=Path(m.name);assert not p.is_absolute() and '..' not in p.parts and m.isfile() and not m.issym() and not m.islnk()
 t.extractall(dest)
seal=json.loads((dest/'full_outputs/OUTPUT_SEAL.json').read_text())
assert seal['experiment']==s['run_id'].split('-')[0].upper() and seal['pod_id']==s['pod_id'],'EXACT_SPECIALIZED_BINDING'
for name,h in seal['files'].items():
 p=dest/'full_outputs'/name;assert p.resolve().is_relative_to((dest/'full_outputs').resolve())
 assert hashlib.sha256(p.read_bytes()).hexdigest()==h,'SEALED_PULL_HASH_FAILED'
assert seal.get('synthetic',False) is False and seal['status'] in ['COMPLETE','CAPTURE_ONLY','PROFILE_ONLY']
receipt=dict(status=seal['status'],verified=True,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),output_seal_sha256=hashlib.sha256((dest/'full_outputs/OUTPUT_SEAL.json').read_bytes()).hexdigest(),files=len(seal['files']),readout_texts_opened=False)
(HOME/'FULL_PULL_VERIFIED.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

m=json.loads((HOME/'PREPARATION.json').read_text());assert seal['status']=='COMPLETE' and seal['source_seal_sha256']==m['source_sha'] and seal['input_seal_sha256']==m['input_sha']
a=json.loads((dest/'assignment_full.json').read_text());assert a['absolute_deadline_epoch']==s['hard_deadline_epoch'] and a['cap_seconds']==m['cap_seconds'] and a['profile_only'] is False
release=json.loads((HOME/'READER_RELEASE.json').read_text());ids=set(release['released_ids']);assert len(ids)==400
counts=json.loads((dest/'full_outputs/COUNTS.json').read_text());assert counts==dict(items=400,positions=400,oracle=400,nla=400)
for reader,layer in [('oracle',44),('nla',42)]:
 rows=[]
 for p in sorted((dest/'full_outputs/jobs').glob(reader+'_*.json')):rows.extend(json.loads(p.read_text()))
 assert len(rows)==400 and {r['unit_id'] for r in rows}==ids and len({r['id'] for r in rows})==400
 assert all(r['reader']==reader and r['layer']==layer for r in rows)
receipt['exact_released_test_ids']=True;receipt['full_scientific_outputs']=800
(HOME/'FULL_PULL_VERIFIED.json').write_text(json.dumps(receipt,indent=2)+'\n')
