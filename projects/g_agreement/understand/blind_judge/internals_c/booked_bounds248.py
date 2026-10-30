"""CPU cost projection from canonical e340 settlement events; never infer zero."""
import json,fcntl
from decimal import Decimal
from projects.g_agreement.readerbench.scoring import require
from projects.g_agreement.readerbench.io import sha

def project(events):
 out=[];seen=set()
 for e in events:
  if e['event']=='settle'and e.get('charge_basis')=='BOOKED_RESERVED_UPPER_BOUND':
   require(e.get('authority')=='e34073059'and e.get('provider_actual_cost_known')is False,'exact authoritative bound provenance');amount=Decimal(str(e['usd']));require(amount.is_finite()and amount>=0 and e['id']not in seen,'unique finite bookedbound');seen.add(e['id']);out.append(e)
 return dict(authority='e34073059',events=out,total_booked_upper_bound_usd=str(sum((Decimal(x['usd'])for x in out),Decimal(0))),provider_actual_cost_known=False)

def ledger_bounds(path,bank):
 require(path.exists(),'canonical ledger required, no missing-to-zero fallback')
 with path.open('rb')as f:
  fcntl.flock(f,fcntl.LOCK_SH);raw=f.read();fcntl.flock(f,fcntl.LOCK_UN)
 result=project([json.loads(x)for x in raw.splitlines()if x.strip()])
 if bank=='E118':require(any(e['id']=='9df87e25e02fa92903535abb89ce1581967bde318814b7ad3fc6b54e313e7d89'and Decimal(e['usd'])==Decimal('.0086843750')for e in result['events']),'original E118 bound remains included honestly')
 result['canonical_ledger_sha256']=__import__('hashlib').sha256(raw).hexdigest();return result
