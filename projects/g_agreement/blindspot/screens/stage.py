"""Pinned public assets and evidence-based download/hash progress, no pod credentials."""
from __future__ import annotations
import argparse,hashlib,json,os,threading,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from . import protocol as P,corpus as C

PUBLIC=[
 {'repo':'Qwen/Qwen3.6-27B','revision':'6a9e13bd6fc8f0983b9b99948120bc37f49c13e9','role':'model','files':['config.json','generation_config.json','tokenizer.json','tokenizer_config.json','chat_template.jinja','model.safetensors.index.json']+[f'model-{i:05d}-of-00015.safetensors' for i in range(1,16)],'hashes':{'tokenizer.json':'5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'}},
 {'repo':'agu18dec/olens_and_ar','revision':'c95215d5d2f6250f20c305ae55c6e4d7569f92dc','role':'olens','files':['olens_s3d_rl600/adapter_config.json','olens_s3d_rl600/adapter_model.safetensors'],'hashes':{'olens_s3d_rl600/adapter_model.safetensors':'7d4b301e002246af3c3f2bb6e768f8fa62f8aac2c231a0bd02a8d4f9ecafd9aa'}},
 {'repo':'ceselder/qwen3.6-27b-nla-rl','revision':'5a13b7ec21a69fcdd0fb24d5edbe96a92aef4b9f','role':'nla','files':['av_base/'+f for f in ['config.json','generation_config.json','tokenizer.json','tokenizer_config.json','chat_template.jinja','nla_meta.yaml','model.safetensors.index.json','model-00001-of-00002.safetensors','model-00002-of-00002.safetensors']]+['nla_meta.yaml','av_rl_adapters/iter_000400/adapter_config.json','av_rl_adapters/iter_000400/adapter_model.safetensors'],'hashes':{'av_rl_adapters/iter_000400/adapter_model.safetensors':'b54e23e4e36dbd04023b307e3abfd4618b5db2b31b8e7c650a957ebb1c90c358','av_base/tokenizer.json':'87a7830d63fcf43bf241c3c5242e96e62dd3fdc29224ca26fed8ea333db72de4'}},
]

def output_paths(out):return {'progress':Path(out)/'staging_progress.s79.json','assets':Path(out)/'assets.s79.json','seal':Path(out)/'assets_seal.s79.json'}
def assert_output_paths(out):
 extra={p.name for p in Path(out).iterdir()}-{p.name for p in output_paths(out).values()}
 if extra:raise ValueError('unexpected staging output '+repr(sorted(extra)))

def asset_snapshot(home):
 """Actual blob/chunk writes, not locks/logs/timestamps manufactured as heartbeat."""
 entries=[]
 for directory,dirs,files in os.walk(home):
  dirs[:]=[d for d in dirs if d not in ('logs','.locks')]
  for name in files:
   p=Path(directory)/name
   if '.log' in name or name.endswith('.lock'):continue
   if 'blobs' not in p.parts and not any('chunk' in part for part in p.parts):continue
   try:
    s=p.stat();entries.append((str(p),s.st_size,s.st_mtime_ns))
   except FileNotFoundError:pass
 return tuple(sorted(entries))

class Progress:
 def __init__(self,path,home):self.path=Path(path);self.home=Path(home);self.stop=threading.Event();self.lock=threading.Lock();self.hash_bytes=0;self.completed=0;self.previous=None
 def emit_if_changed(self):
  snapshot=asset_snapshot(self.home)
  with self.lock:
   key=(snapshot,self.hash_bytes,self.completed)
   if key==self.previous:return False
   # The empty initial observation is not productive work.
   self.previous=key
   if not snapshot and not self.hash_bytes and not self.completed:return False
   C.save(self.path,{'at':time.time(),'asset_bytes':sum(x[1] for x in snapshot),'asset_files':len(snapshot),'latest_asset_mtime_ns':max((x[2] for x in snapshot),default=0),'bytes_hashed':self.hash_bytes,'verified_files':self.completed,'evidence':'changed actual asset/blob/chunk stat or incremented bytes read for hash; no unconditional heartbeat'})
   return True
 def watch(self):
  while not self.stop.wait(10):self.emit_if_changed()
 def hash_file(self,path):
  h=hashlib.sha256()
  with Path(path).open('rb') as f:
   for b in iter(lambda:f.read(64*1024*1024),b''):
    h.update(b)
    with self.lock:self.hash_bytes+=len(b)
    self.emit_if_changed()
  return h.hexdigest()

def resolve_snapshot(volume,asset):
 candidates=[Path(volume)/'hf_cache'/('models--'+asset['repo'].replace('/','--'))/'snapshots'/asset['revision'],Path(volume)/'hf_cache/hub'/('models--'+asset['repo'].replace('/','--'))/'snapshots'/asset['revision']]
 found=[p for p in candidates if p.is_dir()]
 if len(found)!=1:raise ValueError('missing/ambiguous pinned volume snapshot '+asset['repo'])
 return found[0]

def verify_volume_file(job,expected,progress,volume,deadline):
 asset,root,f=job
 if time.time()>=deadline:raise TimeoutError('volume validation consumes science reserve '+f)
 path=root/f
 if not path.resolve().is_relative_to(Path(volume).resolve()) or not path.is_file():raise ValueError('asset escapes/absent from read-only volume '+str(path))
 want=expected.get(str(path)) or expected.get(str(path.resolve()))
 if not want:raise ValueError('fill-receipt hash missing '+str(path))
 h=progress.hash_file(path)
 if h!=want or f in asset['hashes'] and h!=asset['hashes'][f]:raise ValueError('pinned shared asset hash mismatch '+f)
 with progress.lock:progress.completed+=1
 progress.emit_if_changed();print('SHARED_ASSET_VERIFIED '+asset['repo']+' '+f,flush=True)
 return {'path':str(path),'resolved_path':str(path.resolve()),'file_bytes':path.stat().st_size,'file_mtime_ns':path.stat().st_mtime_ns,'sha256':h,'repo':asset['repo'],'revision':asset['revision'],'file':f,'hash_authority':'integrator fill receipt and immutable HF revision'}


def from_volume(assignment,out):
 P.verify_freeze();a=P.admit(assignment)
 if a.get('staging_option')!='shared-readonly' or a.get('weights_volume_id')!='5on6935gne' or a.get('weights_volume_go') is not True:raise ValueError('shared-volume fill and load test not cleared')
 expected=a.get('weights_files',{})
 if not expected or not isinstance(expected,dict):raise ValueError('integrator fill-receipt file hashes required')
 volume=Path('/weights');out=Path(out)
 if not out.resolve().is_relative_to(Path('/workspace/s79')):raise ValueError('staging outputs must stay on own pod disk')
 out.mkdir(parents=True,exist_ok=True)
 # Watch only the pod's own scratch cache. Shared-file growth never earns idle credit.
 progress=Progress(output_paths(out)['progress'],'/workspace/s79/hf');roles={};jobs=[]
 for asset in PUBLIC:
  root=resolve_snapshot(volume,asset);roles[asset['role']]=str(root)
  files=sorted(set(asset['files'])|{str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()})
  jobs.extend((asset,root,f) for f in files)
 # Exact same per-file hashes; deterministic record order, eight independent readers.
 with ThreadPoolExecutor(max_workers=8) as pool:
  records=list(pool.map(lambda job:verify_volume_file(job,expected,progress,volume,a['setup_deadline_epoch']),jobs))
 roles['olens']=str(Path(roles['olens'])/'olens_s3d_rl600')
 C.save(output_paths(out)['assets'],dict(roles,files=records,weights_volume_id=a['weights_volume_id'],fill_receipt_sha256=a['weights_fill_receipt_sha256'],read_only=True))
 P.seal(out,['assets.s79.json','staging_progress.s79.json'],'assets_seal.s79.json',**P.stamp('real'),assignment_sha256=C.sha(assignment),fill_receipt_sha256=a['weights_fill_receipt_sha256']);assert_output_paths(out)


def main():
 p=argparse.ArgumentParser();p.add_argument('--assignment',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();from_volume(a.assignment,a.out)
if __name__=='__main__':main()
