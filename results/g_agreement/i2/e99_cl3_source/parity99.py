"""E99 clarification3: report exact parity without gating numerical divergence."""
import json,hashlib,math
from contract import require,write
AUTHORITY='a5bbbe493956b3f89a35b1beb56674d1d8cd7262'
def finite(x):
 if isinstance(x,float):require(math.isfinite(x),'non-finite output')
 elif isinstance(x,dict):
  for v in x.values():finite(v)
 elif isinstance(x,(list,tuple)):
  for v in x:finite(v)
def check_outputs(batched,serial,path,ids,batch_size):
 require(len(batched)==len(serial)==len(ids)>0,'parity coverage')
 encode=lambda x:json.dumps(x,sort_keys=True,ensure_ascii=False,allow_nan=False)
 rows=[]
 for ident,a,b in zip(ids,batched,serial):
  finite(a);finite(b);aa=encode(a);bb=encode(b)
  first=next((i for i,(u,v)in enumerate(zip(aa,bb))if u!=v),None)
  if first is None and len(aa)!=len(bb):first=min(len(aa),len(bb))
  rows.append(dict(id=ident,equal=aa==bb,batched_sha256=hashlib.sha256(aa.encode()).hexdigest(),serial_sha256=hashlib.sha256(bb.encode()).hexdigest(),first_divergence_position=first,first_divergence_basis='zero-based canonical JSON Unicode character',batched_length=len(aa),serial_length=len(bb)))
 matches=sum(x['equal']for x in rows)
 write(path,dict(authority=AUTHORITY,status='PASS'if matches==len(rows)else'MISMATCH_REPORTED_NON_GATING',n=len(rows),matches=matches,mismatches=len(rows)-matches,production_batch_size=batch_size,exact_serialized_output=True,parity_gates_production=False,records=rows))
