"""Build/reopen a secret-free §79 upload from committed source and sealed inputs."""
from __future__ import annotations
import argparse,io,json,subprocess,tarfile,tempfile
from pathlib import Path
from . import corpus as C,protocol as P

BANK_FILES=('documents.input.jsonl','positions.input.jsonl','assignments.input.jsonl','features.input.json','INPUT_SEAL.json')
def source_names():
 tracked=subprocess.check_output(['git','ls-files','-z'],cwd=C.ROOT).decode().split('\0')
 frozen=P.verify_freeze();fixed=set(frozen['files'])
 fixed|={'projects/__init__.py','projects/g_agreement/__init__.py','projects/g_agreement/blindspot/__init__.py','common/__init__.py'}
 fixed|={'results/g_agreement/blindspot/s79/'+n for n in ['FREEZE.json','RUNTIME_PINS.json','KERNEL_PREPARATION.json','KERNEL_WHEEL_MANIFEST.json','RUNTIME_AMENDMENT.md','RUNNER_PROTOCOL.md','RUNNER_TEST_RECEIPT.json','RUNNER_SEAL.json','OPS_RECEIPT.json','VOLUME_FILL.json']}
 return sorted(n for n in tracked if n and (n in fixed or n.startswith('projects/g_agreement/blindspot/screens/') or n.startswith('external/mats-nla-workspace/src/mats/')) and '__pycache__' not in n)

def verify_wheels(directory,manifest):
 directory=Path(directory);records=json.loads(Path(manifest).read_text())['files'];expected={r['filename']:r for r in records}
 if len(expected)!=len(records):raise ValueError('duplicate kernel wheel filename')
 for name in expected:
  if Path(name).name!=name or not name.endswith('.whl'):raise ValueError('unsafe kernel wheel '+name)
 actual={p.name for p in directory.glob('*.whl')}
 if actual!=set(expected):raise ValueError('kernel wheel coverage extra='+repr(sorted(actual-set(expected)))+' missing='+repr(sorted(set(expected)-actual)))
 for name,r in expected.items():
  p=directory/name
  if p.stat().st_size!=r['bytes'] or C.sha(p)!=r['sha256']:raise ValueError('kernel wheel hash mismatch '+name)
 return {name:(directory/name).read_bytes() for name in sorted(expected)}

def build(out,bank,include_wheels=True):
 out,bank=Path(out),Path(bank);P.verify_freeze()
 with tempfile.TemporaryDirectory() as tmp:
  public=Path(tmp)/'bank';public.mkdir()
  for n in BANK_FILES:(public/n).write_bytes((bank/n).read_bytes())
  P.inputs(public)
 names=source_names();payload={}
 for n in names:
  data=subprocess.check_output(['git','show','HEAD:'+n],cwd=C.ROOT)
  if data!=(C.ROOT/n).read_bytes():raise ValueError('uncommitted upload source '+n)
  payload[n]=data
 for n in BANK_FILES:payload['bank/'+n]=(bank/n).read_bytes()
 if include_wheels:
  for n,v in verify_wheels(C.CACHE/'kernel_wheels',C.OUT/'KERNEL_WHEEL_MANIFEST.json').items():payload['kernel_wheels/'+n]=v
 if any('DO_NOT_STAGE' in n or any(x in Path(n).parts for x in ('.env','.git','__pycache__')) for n in payload):raise ValueError('forbidden archive member')
 meta={'section':79,'kernel_wheels_included':include_wheels,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=C.ROOT,text=True).strip(),'files':{n:__import__('hashlib').sha256(v).hexdigest() for n,v in payload.items()}}
 payload['BUNDLE_MANIFEST.json']=(json.dumps(meta,indent=2)+'\n').encode()
 out.parent.mkdir(parents=True,exist_ok=True)
 with tarfile.open(out,'x:gz') as t:
  for n,v in sorted(payload.items()):
   member=tarfile.TarInfo(n);member.size=len(v);member.mode=0o644;member.mtime=0;t.addfile(member,io.BytesIO(v))
 with tempfile.TemporaryDirectory() as tmp:
  root=Path(tmp)
  with tarfile.open(out,'r:gz') as t:
   if set(t.getnames())!=set(payload):raise ValueError('archive member coverage')
   for m in t.getmembers():
    if not m.isfile() or Path(m.name).is_absolute() or '..' in Path(m.name).parts:raise ValueError('unsafe archive path')
    data=t.extractfile(m).read()
    if data!=payload[m.name]:raise ValueError('reopened archive mismatch '+m.name)
    p=root/m.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
  subprocess.run([__import__('sys').executable,'-B','-c','from pathlib import Path; from projects.g_agreement.blindspot.screens import protocol as P; f=P.verify_freeze(); d,p,a,r=P.inputs(Path("bank")); assert len(d)==f["corpus_documents"] and len(p)==f["selected_capture_positions"] and len(r["templates"])==f["features"] and len({x["feature"] for x in a})==f["retained"]'],cwd=root,check=True,capture_output=True)
 return dict(meta,archive=str(out),archive_sha256=C.sha(out),archive_bytes=out.stat().st_size,reopened_all_members=True,extracted_input_validation=True)
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--bank',required=True,type=Path);p.add_argument('--shared-runtime-only',action='store_true');a=p.parse_args();print(json.dumps(build(a.out,a.bank,include_wheels=not a.shared_runtime_only),indent=2))
if __name__=='__main__':main()
