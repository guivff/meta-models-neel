"""E135 deviation1: all336 alpha6 readouts, original E104 rubric, lifetime1.
Original native/raw exports remain CPU-local under the recorded Git egress hold.
"""
import argparse,os,time,subprocess
from collections import Counter
from pathlib import Path
from decimal import Decimal
from contextlib import contextmanager
from . import transport,resume_e340 as bounds,registered
from .e128_channel import original104_call,RUBRIC_SHA
from .runner import CACHE,seal_phase,preflight
from .banks import opaque
from ..privacy79 import redact
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
CAP=Decimal(1)

def source_gate():
 p=transport.HERE/'E135245_SOURCE_SEAL.json';v=read(p)
 for n,h in v['files'].items():require(sha(transport.ROOT/n)==h,'frozen E135 source')
 for n,h in v['owner_frozen_files'].items():require(sha(n)==h,'frozen tested owner source')
 return p

@contextmanager
def worker():
 source_gate();old=transport.CAPS.get('E135');expiry=transport.EXPIRY;transport.CAPS['E135']=CAP;bounds.CAPS['E135']=CAP;transport.EXPIRY=1793372400
 try:yield
 finally:
  transport.EXPIRY=expiry
  if old is None:transport.CAPS.pop('E135',None)
  else:transport.CAPS['E135']=old

def enforce(api,client,unpaced):
 ns=[api.__dict__]+[getattr(f,'__func__',f).__globals__ for f in (client.ledger.reserve,client.ledger.settle,client.ledger.summary,unpaced)]
 for n in ns:require('CAP'in n,'actual cap namespace');n['CAP']=CAP

class E135Transport(bounds.ResumeTransport):
 def __enter__(self):
  value=super().__enter__();one=self.api.Client.one
  def capped(client,*a,**k):enforce(self.api,client,self.unpaced);return one(client,*a,**k)
  self.api.Client.one=capped;enforce(self.api,self.client,self.unpaced);return value
 def summary(self):enforce(self.api,self.client,self.unpaced);return super().summary()

def make_units(records,original,pointers,items,labels,rubric,nitems=84):
 old={x['item_id']:(i,x)for i,x in enumerate(original)if x['arm']=='U'and x['row']=='fact_recall'and x['reader']=='oracle'and x['condition']=='steered'and x['flipped']is True};ptr={x['id']:x for x in pointers};pub={x['id']:x for x in items};lab={x['original_base_id']:x for x in labels}
 require(len(old)==len(lab)==nitems and len(ptr)==len(pub)==2*nitems and set(ptr)==set(pub),'whole original84 and168cells')
 units=[];joins=[];seen=set()
 for ref,r in records:
  require(r['item_id']in ptr and r['reader']=='oracle','literal original native/input IDs')
  p=ptr[r['item_id']];x=pub[r['item_id']];i,o=old[p['original_base_id']];l=lab[p['original_base_id']]
  require(r['alpha']==x['alpha']==6 and r['condition']==x['condition']and r['condition']in('steered','random')and r['base_id']==x['base_id']and x['row']=='fact_recall'and r['source_layer']in(44,52)and p['scale']==.75,'exact alpha6 original cells/layers/scale')
  target=o['target'];other='B'if target=='A'else'A';require(l['new_value']in o['values'][target]and l['old_value']in o['values'][other],'original candidate orientation')
  key=p['original_base_id'],r['condition'],r['source_layer'];require(key not in seen,'one readout per sourcecell');seen.add(key);uid=opaque('E135',r['id']);require(type(r['text'])is str,'no invented text')
  units.append(dict(id=uid,kind='original104',rubric=rubric,data=dict(id=uid,property=o['property'],values=o['values'],readout=r['text'])))
  joins.append(dict(id=uid,readout_id=r['id'],item_id=p['original_base_id'],condition=r['condition'],dose=6,layer=r['source_layer'],original_private_index=i,source_ref=ref,old_letter=other,new_letter=target))
 require(seen=={(i,c,b)for i in old for c in('steered','random')for b in(44,52)},'full336 originalgrid; no missingfill')
 return sorted(units,key=lambda x:x['id']),sorted(joins,key=lambda x:x['id'])

def validate_plan(plans,calls,expected=336):
 require(len(plans)==expected and len({p['unit']['id']for p in plans})==expected,'exact unique readout inventory')
 ids=[i for p in plans for i in p['calls']]
 require(len(ids)==3*expected and len(set(ids))==len(ids)and set(ids)=={c['id']for c in calls}and len(calls)==len(ids),'exact three frozen wires per original readout')
 require(all(len(p['calls'])==3 for p in plans),'initial plus two schema attempts only')
 return dict(logical_readouts=expected,physical_wire_upper_count=len(calls),schema_retries=2)

def prepare():
 source=source_gate();rec=read(transport.ROOT/'results/g_agreement/i2/E135_DEV1_COMPLETE244.json');n=Path(rec['CPU_original_directory']);native=n/'OUTPUT_SEAL.json';ns=verify(native,'59cdc075684f082c3855d76b9bc6e4e57b7458947ce1440760d192c404958731');require(ns['status']=='COMPLETE'and ns['experiment']=='E135','complete originallocalGPUbank')
 r=transport.ROOT.parent/'outputs/e135-dev1-inputs-v1';inp=r/'inputs/INPUT_SEAL.json';verify(inp,'381b58bde8ab7031e7a1de07bec1afe05655010a815e61a1a84c3b689c1c8047');ptr=r/'cpu_only/POINTER_SEAL.json';verify(ptr,'792eba4a390a0c866e5cfec2b5430e468a0b0e3d8104c1495481497ed052f08b');require(ns['input_sha256']==sha(inp),'same originalinput')
 label=transport.ROOT.parent/'outputs/e127-inputs-v2/cpu_only/LABEL_SEAL.json';verify(label,'549fa110f6f0f0276dda18b428b26de9c921e9fd97bced195f754a017ebe99c0');old=transport.SHARED/'E104';ps=old/'PRIVATE_SEAL.json';verify(ps,'0f42d78d151a85b858f2b02a13307e62e74f987ad0bba009cab875b6792aa3c6');rubric=old/'blind/RUBRIC.md';require(sha(rubric)==RUBRIC_SHA,'originalE104rubric')
 records=[]
 for m in ns['files']:
  if m.startswith('jobs/')and m.endswith('.json'):
   for i,x in enumerate(read(n/m)):
    if x['reader']=='oracle':records.append((dict(seal=str(native),sha256=sha(native),member=m,keys=[i,'text']),x))
 require(len(records)==336,'full336 originalreadouts')
 units,joins=make_units(records,read(old/'PRIVATE.json'),read(ptr.parent/'ORIGINAL_POINTERS.PRIVATE.json'),read(inp.parent/'items.json'),read(label.parent/'LABELS.PRIVATE.json'),rubric.read_text());_,audit=redact([u['data']for u in units],'E135',addresses=True);require(audit['redacted_records']==0,'owner requires prospective companion if redaction')
 d=CACHE/'E135/original104_judging_checked245';require(not(d/'INPUT_SEAL.json').exists(),'prepareonce');_,(_,_,protocol,_)=registered.funded.route_api();calls=[];plans=[]
 for u in units:
  call,_=original104_call(u,protocol);ids=[]
  for attempt in range(3):
   c=dict(call,id=opaque('E135','judging',u['id'],str(attempt)));calls.append(c);ids.append(c['id'])
  plans.append(dict(unit=u,calls=ids))
 d=seal_phase('E135','original104_judging_checked245',calls,dict(n=336,max_schema_retries=2,source_sha256=sha(source),original_native_sha256=sha(native),raw_native_git_export=False),[dict(seal=str(p),sha256=sha(p))for p in(native,inp,ptr,label,ps)])
 for name,value in [('VALIDATION.json',plans),('SOURCE_POINTERS.PRIVATE.json',joins),('PATH_REDACTION_AUDIT.json',audit)]:write(d/name,value)
 s=read(d/'INPUT_SEAL.json');s['files'].update({name:sha(d/name)for name in('VALIDATION.json','SOURCE_POINTERS.PRIVATE.json','PATH_REDACTION_AUDIT.json')});write(d/'INPUT_SEAL.json',s)
 validate_plan(plans,calls)
 with worker():preflight(d)
 return d

def run(d):
 source=source_gate();a=read(d/'ADMISSION.json');pub=read(d/'PUBLICATION.json');p=Path(pub['allocation_path']);live=read(d/'LIVE_PROOF.PRIVATE.json');require(a['bank']=='E135'and a['allocation_usd']=='1'and a['E135_source_sha256']==sha(source),'registeredsame1source')
 require(sha(p)==pub['allocation_sha256']==sha(d/'ADMISSION.json')and subprocess.check_output(['git','show',pub['commit']+':'+str(p.relative_to(transport.ROOT))],cwd=transport.ROOT)==p.read_bytes(),'postedbeforecalls');require(sha(d/'LIVE_PROOF.PRIVATE.json')==a['live_route_funding_proof_sha256']and 0<=time.time()-live['at_epoch']<300 and all(live[k]is True for k in('route_verified','account_privacy_verified','funded_remaining_bank_cap')),'freshliveproof');verify(d/'INPUT_SEAL.json',sha(d/'INPUT_SEAL.json'));job=d/'outputs';job.mkdir(exist_ok=True);fd=os.open(d/'JUDGING_ONCE.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd);write(d/'JUDGING_ONCE.json',dict(pid=os.getpid(),source_sha256=sha(source)))
 with worker():
  transport.unpaused()
  try:
   with E135Transport(d/'INPUT_SEAL.json',sha(d/'INPUT_SEAL.json'),a,os.environ['OPENROUTER_API_KEY'])as channel:
    units=[];attempts=[];audits=[]
    for plan in read(d/'VALIDATION.json'):
     expected,validator=original104_call(plan['unit'],channel.protocol)
     for attempt,cid in enumerate(plan['calls']):
      require(channel.allowed[cid]['rendered']==expected['rendered'],'literal original104renderer');t,audit=channel.call(cid,validator);attempts.append(dict(t,unit_id=plan['unit']['id'],attempt=attempt));audits.append(audit)
      if t['status']=='KEPT'or t.get('reason')in('CHARGED_LENGTH','RATE_LIMIT_EXHAUSTED'):break
     units.append(dict(id=plan['unit']['id'],kind='original104',status=t['status'],code=t['result']['records'][0]if t['status']=='KEPT'else None,request_id=t['request_id'],response_sha256=t['response_sha256'],attempts=attempt));write(job/'PROGRESS.json',dict(completed=len(units),n=336,cost=channel.summary(),at_epoch=time.time()))
    for name,value in [('JUDGMENTS.json',units),('ATTEMPTS.json',attempts),('ROUTE_AUDIT.json',dict(routes=channel.routes,requests=audits)),('RAW_RESPONSE_BINDINGS.json',channel.physical),('COUNTS.json',dict(n=336,status_counts=dict(Counter(u['status']for u in units)),cost=channel.summary())),('PATH_REDACTION_AUDIT.json',read(d/'PATH_REDACTION_AUDIT.json'))]:write(job/name,value)
    from datetime import datetime,timezone
    first=min(Path(x['path']).stat().st_mtime for x in channel.physical);write(job/'JUDGMENT_SEAL.json',dict(experiment='E135',phase='original104_judging',status='COMPLETE',first_output_utc=datetime.fromtimestamp(first,timezone.utc).isoformat(),input_sha256=sha(d/'INPUT_SEAL.json'),source_sha256=sha(source),route_verified=True,labels_cpu_only=True,redacted_records=0,raw_git_export=False,files={p.name:sha(p)for p in job.iterdir()if p.is_file()}))
  except BaseException as exc:write(job/'STOPPED.json',dict(error_type=type(exc).__name__,at_epoch=time.time(),no_resend=True));raise

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);p.add_argument('--phase-directory',type=Path);a=p.parse_args()
 if a.action=='prepare':print(prepare())
 else:run(a.phase_directory)
