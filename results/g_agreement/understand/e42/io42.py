import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(s) for s in Path(p).read_text().splitlines()]
def dump(p,x):
 with Path(p).open('x') as f:json.dump(x,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def seal(folder,names,name):
 dump(folder/name,{'complete':True,'files':{n:sha(folder/n) for n in names}})
def verify(folder,name,expected=None):
 if expected and sha(folder/name)!=expected:raise ValueError('seal identity mismatch')
 r=read(folder/name)
 for n,h in r['files'].items():
  if Path(n).is_absolute() or '..' in Path(n).parts or sha(folder/n)!=h:raise ValueError('sealed file mismatch: '+n)
 return r
