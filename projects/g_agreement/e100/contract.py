"""§208 exact public acquisition contract; truth and donor labels never enter it."""
import hashlib,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
ROWS={'reported':{'format_plan':84,'language_plan':84,'tense_implicit':84,'language_continuation':84,'fact_recall':84},'missed':{'nesting_depth':84,'indent_level':84,'page_range_digit':84}}
DIRECTIONS=('d','d_J','d_perp','u_tok','r')
ALPHAS=(.5,1,2,4)
FIELDS={'id','row','slot','row_slot','donor_slot','ids','read_index'}
OLD_RUNNER='721ce7680400df9a96b0ce1e54ea944a5c080acd94335bed08006d790a9a8f0c'

def require(ok,msg):
 if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
 p=Path(p);q=p.with_suffix(p.suffix+'.tmp');q.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n');q.replace(p)
def verify(root,name,h):
 root=Path(root).resolve();p=root/name;require(sha(p)==h,'sealed identity');s=read(p);require(bool(s.get('files')),'empty seal')
 for n,d in s['files'].items():
  p=(root/n).resolve();require(p.is_relative_to(root) and sha(p)==d,'sealed member identity')
 return s

def cells(shard,row,reader):
 require(shard in ROWS and row in ROWS[shard] and reader in ('oracle','nla'),'registered cell scope')
 result=[dict(mode='transplant',condition='transplant')]
 result += [dict(mode='swap',condition=kind,basis=basis,complement=complement) for basis,kind,complement in [('J','J_swap',False),('J','perp_J_swap',True),('R','R_swap',False),('R','perp_R_swap',True)]]
 return result

def validate(items,arrays,shard,dimension=5120,rank=384):
 require(shard in ROWS,'exact reported/missed shard');n=sum(ROWS[shard].values())
 require(len(items)==n and len({x['id'] for x in items})==n,'exact unique carrier count')
 require(all(set(x)<=FIELDS and {'id','row','slot','donor_slot'}<=set(x) for x in items),'public fields only: no labels/targets')
 require([x['slot'] for x in items]==list(range(n)),'frozen slot order')
 require({x['row'] for x in items}==set(ROWS[shard]),'whole registered rows')
 for row,count in ROWS[shard].items():require(sum(x['row']==row for x in items)==count,'registered row cardinality')
 for x in items:
  require(type(x['donor_slot']) is int and 0<=x['donor_slot']<n and x['donor_slot']!=x['slot'] and items[x['donor_slot']]['row']==x['row'],'same-row opaque paired donor')
  require('ids' not in x and 'read_index' not in x,'a/b inputs contain no item text')
 expected={'H44':(n,dimension),'H42':(n,dimension),'BASIS_J':(dimension,rank),'BASIS_R':(dimension,rank)}
 require(set(arrays)==set(expected),'a/b only: no direction or upstream arrays')
 for name,shape in expected.items():
  a=arrays[name];require(a.shape==shape and a.dtype.kind=='f' and np.isfinite(a).all(),'finite floating-point shape: '+name)
 for name in ('BASIS_J','BASIS_R'):require(np.allclose(np.einsum('di,dj->ij',arrays[name],arrays[name],optimize=False),np.eye(rank),atol=2e-4,rtol=2e-4),'orthonormal rank384 basis')
 for h in ('H44','H42'):require(np.all(np.linalg.norm(arrays[h],axis=1)>0),'nonzero native carrier')
 for row,count in ROWS[shard].items():
  require([x['row_slot'] for x in items if x['row']==row]==list(range(count)),'original row slot order')

def jobs(items,shard,batch=8):
 require(batch==8,'original batch8');result=[]
 for reader in ('oracle','nla'):
  for row in ROWS[shard]:
   indices=[x['slot'] for x in items if x['row']==row]
   for cell in cells(shard,row,reader):
    groups={}
    for i in indices:groups.setdefault(0,[]).append(i)
    for _,ix in sorted(groups.items()):
     for start in range(0,len(ix),batch):result.append(dict(number=len(result),reader=reader,row=row,indices=ix[start:start+batch],phase='upstream_oracle' if cell['mode']=='upstream' else reader,**cell))
 return result
