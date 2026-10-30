"""Read-only terminal pull: preserve bytes, verify every sealed output hash."""
import json,subprocess,hashlib,tarfile,os,sys
from pathlib import Path
HOME=Path(__file__).resolve().parent
sys.path.insert(0,str(HOME))
import stage_and_start as st
s=st.state();remote=s['remote_dir'];host,port=s['address'].split(':');dest=HOME/'terminal_pull';dest.mkdir(exist_ok=False)
program=f'''cd {remote}
/weights/venv-kernels/bin/python - <<'REMOTE'
import json,tarfile,sys,io
from pathlib import Path
assert json.loads(Path('EXIT.json').read_text())['code']==0 and json.loads(Path('outputs/OUTPUT_SEAL.json').read_text())['status']=='COMPLETE'
files=[p for p in Path('outputs').rglob('*') if p.is_file()]+[Path('EXIT.json'),Path('RUNTIME_STAGING.json'),Path('assignment.json')]
assert sum(p.stat().st_size for p in files)<600*1024*1024
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as t:
 for p in sorted(files):
  assert not p.is_symlink();t.add(p,arcname=str(p),recursive=False)
REMOTE
'''
args=['ssh','-i',str(st.KEY),'-p',port,'-o','BatchMode=yes','-o','ConnectTimeout=15','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null','root@'+host,'bash -s']
archive=HOME/'TERMINAL_PULL.private.tar'
with archive.open('xb') as out:
 r=subprocess.run(args,input=program.encode(),stdout=out,stderr=subprocess.PIPE,timeout=180)
assert r.returncode==0,'TERMINAL_PULL_FAILED'
with tarfile.open(archive) as t:
 for m in t.getmembers():
  p=Path(m.name);assert not p.is_absolute() and '..' not in p.parts and m.isfile() and not m.issym() and not m.islnk()
 t.extractall(dest)
seal=json.loads((dest/'outputs/OUTPUT_SEAL.json').read_text())
assert seal['experiment']==s['run_id'].split('-')[0].upper() and seal['pod_id']==s['pod_id'],'EXACT_SPECIALIZED_BINDING'
for name,h in seal['files'].items():
 p=dest/'outputs'/name;assert p.resolve().is_relative_to((dest/'outputs').resolve())
 assert hashlib.sha256(p.read_bytes()).hexdigest()==h,'SEALED_PULL_HASH_FAILED'
assert seal.get('synthetic',False) is False and seal['status'] in ['COMPLETE','CAPTURE_ONLY','PROFILE_ONLY']
receipt=dict(status=seal['status'],verified=True,archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),output_seal_sha256=hashlib.sha256((dest/'outputs/OUTPUT_SEAL.json').read_bytes()).hexdigest(),files=len(seal['files']),readout_texts_opened=False)
(HOME/'PULL_VERIFIED.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

m=json.loads((HOME/'PREPARATION.json').read_text());assert seal['status']=='COMPLETE' and seal['source_seal_sha256']==m['source_sha'] and seal['input_seal_sha256']==m['input_sha']
a=json.loads((dest/'assignment.json').read_text());assert a['absolute_deadline_epoch']==s['hard_deadline_epoch'] and a['cap_seconds']==m['cap_seconds'] and a['profile_only'] is False
assert a==json.loads((dest/'outputs/ASSIGNMENT.json').read_text())
assert a['capture_seal_sha256']==m['capture_seal_sha256'] and a['measured_profile_sha256']==m['measured_profile_sha256']
assert a['pod_created_epoch']==a['custody_start_epoch']==s['created_epoch'] and a['prior_seconds']==m['prior_probe_gpu_seconds']
items=json.loads((HOME/'inputs/PUBLIC_INPUTS.json').read_text());expected={(x['id'],p)for x in items for p in x['read_positions']};assert len(items)==209 and len(expected)==6790
counts=json.loads((dest/'outputs/COUNTS.json').read_text());assert counts==dict(items=209,positions=6790,oracle=6790,nla=6790)
for reader,layer in [('oracle',44),('nla',42)]:
 rows=[]
 for p in sorted((dest/'outputs/jobs').glob(reader+'_*.json')):rows.extend(json.loads(p.read_text()))
 assert len(rows)==6790 and {(r['unit_id'],r['position'])for r in rows}==expected and len({r['id']for r in rows})==6790
 assert all(r['reader']==reader and r['layer']==layer and r['id']==r['unit_id']+':'+str(r['position'])for r in rows)
 parity=json.loads((dest/'outputs'/('PARITY_'+reader+'.json')).read_text());assert parity['n']==8 and len(parity['records'])==8 and parity['matches']+parity['mismatches']==8 and parity['authority']=='87ee19008919ac30889d9f47e6572503ad032b88' and parity['mismatch_is_gate'] is False
receipt['exact_registered_items_positions']=True;receipt['full_scientific_outputs']=13580
(HOME/'PULL_VERIFIED.json').write_text(json.dumps(receipt,indent=2)+'\n')
