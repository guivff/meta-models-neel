"""Retrieve terminal science once and verify complete frozen cell identities on CPU."""
import json,subprocess,hashlib,tarfile,sys
from pathlib import Path
HOME=Path(__file__).resolve().parent
sys.path.insert(0,str(HOME))
import stage_and_start as st

def main():
 s=st.state();meta=json.loads((HOME/'PREPARATION.json').read_text());remote=s['remote_dir'];host,port=s['address'].split(':');dest=HOME/'terminal_pull';dest.mkdir(exist_ok=False)
 program=f'''cd {remote}
/weights/venv-kernels/bin/python - <<'REMOTE'
import json,tarfile,sys
from pathlib import Path
assert json.loads(Path('EXIT.json').read_text())['code']==0
assert json.loads(Path('outputs/OUTPUT_SEAL.json').read_text())['status']=='COMPLETE'
files=[p for p in Path('outputs').rglob('*') if p.is_file()]+[Path('EXIT.json'),Path('RUNTIME_STAGING.json'),Path('assignment.json')]
assert sum(p.stat().st_size for p in files)<1200*1024*1024
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as t:
 for p in sorted(files):
  assert not p.is_symlink();t.add(p,arcname=str(p),recursive=False)
REMOTE
'''
 args=['ssh','-i',str(st.KEY),'-p',port,'-o','BatchMode=yes','-o','ConnectTimeout=15','-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=/dev/null','root@'+host,'bash -s']
 archive=HOME/'TERMINAL_PULL.private.tar'
 with archive.open('xb') as out:r=subprocess.run(args,input=program.encode(),stdout=out,stderr=subprocess.PIPE,timeout=300)
 assert r.returncode==0,'TERMINAL_PULL_FAILED'
 with tarfile.open(archive) as t:
  for m in t.getmembers():
   p=Path(m.name);assert not p.is_absolute() and '..' not in p.parts and m.isfile() and not m.issym() and not m.islnk()
  t.extractall(dest)
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 out=dest/'outputs';seal=json.loads((out/'OUTPUT_SEAL.json').read_text())
 assert seal.get('synthetic',False) is False and seal['status']=='COMPLETE' and seal['experiment']=='E99'
 assert seal['shard']==meta['shard'] and seal['pod_id']==s['pod_id'] and seal['source_seal_sha256']==meta['source_sha'] and seal['input_seal_sha256']==meta['input_sha']
 assert set(seal['files'])=={str(p.relative_to(out)) for p in out.rglob('*') if p.is_file() and p.name!='OUTPUT_SEAL.json'}
 for name,digest in seal['files'].items():
  p=out/name;assert p.resolve().is_relative_to(out.resolve()) and sha(p)==digest,'SEALED_HASH'
 ass=json.loads((dest/'assignment.json').read_text());assert ass==json.loads((out/'ASSIGNMENT.json').read_text())
 assert ass['stage99']=='read' and ass['run_id']==meta['run_id'] and ass['capture_seal_sha256']==meta['capture_seal_sha256'] and ass['measured_profile_sha256']==meta['measured_profile_sha256'] and ass['admission_sha256']==meta['admission_sha256']
 assert ass['pod_created_epoch']==ass['custody_start_epoch']==s['created_epoch'] and ass['absolute_deadline_epoch']==s['hard_deadline_epoch']
 source=HOME.parents[1]/'e99_core_three_v1/source/results/g_agreement/understand'
 sys.path.insert(0,str(source/'late198'));sys.path.insert(0,str(source/'e87'));import scope99
 plan=json.loads((HOME/'inputs/PLAN.json').read_text());items=json.loads((HOME/'inputs/items.json').read_text());scope99.validate(items,plan)
 groups=scope99.cells(items,plan);expected={};counts={}
 for (reader,layer,family),cells in groups.items():
  counts[f'{reader}:{layer}:{family}']=len(cells)
  for j in range(0,len(cells),32):expected[f'{reader}_{layer}_{family}_{j//32:06d}.json']=cells[j:j+32]
 assert set(expected)=={p.name for p in (out/'jobs').glob('*.json')}
 for name,cells in expected.items():
  rows=json.loads((out/'jobs'/name).read_text());assert len(rows)==len(cells)
  for row,cell in zip(rows,cells):
   assert all(row[k]==v for k,v in cell.items()),'CELL_IDENTITY'
   assert row['id']==f"{cell['unit_id']}:{cell['reader']}:{cell['layer']}:{cell['position']}", 'CELL_ID'
 assert json.loads((out/'COUNTS.json').read_text())==counts,'COMPLETE_COUNTS'
 parity=json.loads((out/'PARITY_SUMMARY.json').read_text());assert parity['authority']==scope99.PARITY_AUTHORITY and parity['mismatch_is_gate'] is False
 receipt=dict(status='COMPLETE',verified=True,experiment='E99',shard=meta['shard'],output_seal_sha256=sha(out/'OUTPUT_SEAL.json'),archive_sha256=sha(archive),files=len(seal['files']),scientific_cells=sum(counts.values()),exact_cell_identity=True,source_input_capture_profile_admission_bound=True,first_output_utc=seal['first_output_utc'],judging_admitted=False)
 with (HOME/'PULL_VERIFIED.json').open('x') as f:json.dump(receipt,f,indent=2)
 print(json.dumps(receipt))
if __name__=='__main__':main()
