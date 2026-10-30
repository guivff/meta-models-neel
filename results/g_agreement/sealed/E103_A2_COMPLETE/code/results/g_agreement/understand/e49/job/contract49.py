"""E49 stage identities and fail-closed release protocol."""
import hashlib,json,math,re
from pathlib import Path
import numpy as np
BANK_SHA='ccc2b3b6e27d0227f2d17f1de0efe2cb9a33cfd4d299656f19d7e4a4e3db43c9'
SEED=20261026
CAP=21600

def require(ok,msg):
 if not ok:raise ValueError(msg)
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def dump(p,d):
 with Path(p).open('x') as f:json.dump(d,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def verify(root,name,digest=None):
 root=Path(root)
 if digest:require(sha(root/name)==digest,'seal identity: '+name)
 s=read(root/name)
 for n,h in s['files'].items():
  p=root/n;require(p.resolve().is_relative_to(root.resolve()),'unsafe seal path');require(sha(p)==h,'sealed file changed: '+n)
 return s

def seal(root,name,extra):
 root=Path(root);s=dict(extra,files={str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file() and p.name!=name});dump(root/name,s);return s

def deadline(a):
 require(a['gpu_count']==1 and a['cap_seconds']==CAP,'registered custody cap')
 start=float(a['pod_created_epoch']);end=float(a['deadline_epoch'])
 require(math.isfinite(start) and end==start+CAP and a['pod_id'],'own provider creation deadline')
 return end

def validate_go(go,assignment,capture_sha,now,captured_epoch):
 require(go.get('release') is True,'explicit release=true required')
 expected={'experiment':'E49','pod_id':assignment['pod_id'],'source_seal_sha256':assignment['source_seal_sha256'],'input_seal_sha256':assignment['input_seal_sha256'],'capture_seal_sha256':capture_sha,'bank_seal_sha256':BANK_SHA}
 for k,v in expected.items():require(go.get(k)==v,'go-signal binding: '+k)
 require(bool(re.fullmatch(r'[0-9a-f]{40}',go.get('forecast_commit',''))),'committed forecast identity required')
 issued=go.get('issued_epoch');require(type(issued) in (float,int) and captured_epoch<=issued<=now,'release predates capture or is future dated')
 require(now<deadline(assignment)-60,'release after retrieval reserve')
 return go

def auc(y,x):
 y=np.array(y);x=np.array(x,float);a=x[y==1];b=x[y==0]
 require(x.shape==y.shape and np.isfinite(x).all() and len(a) and len(b),'invalid AUROC grid')
 return float(((a[:,None]>b[None,:])+.5*(a[:,None]==b[None,:])).mean())
def wilson(k,n):
 z=1.959963984540054;p=k/n;d=1+z*z/n;c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
 return [c-h,c+h]
