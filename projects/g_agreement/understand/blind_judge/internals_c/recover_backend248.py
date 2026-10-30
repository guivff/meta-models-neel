"""Prospective same-input E118/E117 recovery; no settled success is resent."""
import argparse,json,os,time,subprocess,hashlib
from collections import defaultdict,Counter
from contextlib import contextmanager
from pathlib import Path
from decimal import Decimal
from . import transport,registered,banks,resume_e340 as bounds
from .backend248 import BackendTransport,zero_error,retry_id
from .accounting_e79b import snapshot
from .e117_channel import original57_call
from .e109_privacy import raw_evidence_guard
from .runner import CACHE
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
CAPS={'E118':Decimal(1),'E117':Decimal(4)}
PHASES={'E118':'belief_wrong_consistency_judging','E117':'native_judging'}
LIMITS={'E118':5,'E117':2}
TERMINAL={'CHARGED_LENGTH','RATE_LIMIT_EXHAUSTED','UNCHARGED_BACKEND_RETRIES_EXHAUSTED'}


def source_gate():
 p=transport.HERE/'BACKEND248_SOURCE_SEAL.json'
 for n,h in read(p)['files'].items():require(sha(transport.ROOT/n)==h,'prospective committed recovery source')
 return p


def is_final(t):return t['status']=='KEPT'or t.get('reason')in TERMINAL


def split_prefix(plans,by):
 complete=[];partial=[];cursor=0
 for i,plan in enumerate(plans):
  found=[]
  for cid in plan['calls']:
   if cid not in by:break
   found.append(by[cid])
   if is_final(found[-1]):break
  if found and(is_final(found[-1])or len(found)==len(plan['calls'])):complete.append(found);cursor=i+1
  else:partial=found;cursor=i;break
 else:cursor=len(plans)
 require({t['id']for ts in complete+[partial]for t in ts}==set(by),'no saved terminal outside dense prefix/partial next schema plan')
 return complete,partial,cursor


def original_base(bank,phase,ish,cid,wire):return hashlib.sha256(('WIC:'+bank+'_'+phase+':'+ish+':'+cid+':'+transport.canonical(wire)).encode()).hexdigest()


def traceable(rid,base,limit):
 return rid==base or rid in{hashlib.sha256((tag+base+':'+str(i)).encode()).hexdigest()for tag in('RATE429:','E340_RATE429:')for i in range(1,6)}or rid in{retry_id(base,z,r)for z in range(limit+1)for r in range(6)if z or r}


def recover(dest,bank,protocol):
 verify(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'));ish=sha(dest/'INPUT_SEAL.json');calls=read(dest/'CALLS.json');allowed={c['id']:c for c in calls};require(len(allowed)==len(calls),'unique original calls');plans=read(dest/'VALIDATION.json')if bank=='E117'else[dict(unit=dict(id=c['id'],kind='consistency'),calls=[c['id']])for c in calls]
 stage=bank+'_'+calls[0]['phase'];root=transport.SHARED/bank/'ledger';events=[json.loads(x)for x in(root/'ledger.jsonl').read_text().splitlines()if x.strip()];settled={e['id']for e in events if e['event']=='settle'};term={};raw={};wires=defaultdict(list)
 for c in calls:wires[transport.canonical(transport.frozen_wire(c,protocol))].append(c['id'])
 for p in(root/stage).glob('*.terminal.json'):
  t=read(p)
  if t.get('input_sha256')!=ish:continue
  require(t['id']in allowed and t['id']not in term and t['request_id']in settled,'original unique settled term')
  rp=root/stage/(t['request_id']+'.response.json');qp=root/stage/(t['request_id']+'.request.json');wire=read(qp)['wire'];require(sha(rp)==t['response_sha256']and wire==transport.frozen_wire(allowed[t['id']],protocol),'byteexact savedwire/response')
  require(traceable(t['request_id'],original_base(bank,calls[0]['phase'],ish,t['id'],wire),LIMITS[bank]),'original physical identity formula');term[t['id']]=t
 seeds={}
 for p in(root/stage).glob('*.response.json'):
  rid=p.name.split('.')[0];qp=root/stage/(rid+'.request.json')
  if not qp.exists():continue
  wire=read(qp)['wire'];possible=wires.get(transport.canonical(wire),[])
  if not possible:continue
  matches=[cid for cid in possible if traceable(rid,original_base(bank,calls[0]['phase'],ish,cid,wire),LIMITS[bank])];require(len(matches)==1,'literal request/input salt match, no order matching');cid=matches[0];require(rid in settled,'no unresolved physicalcharge can resume');raw[str(p)]=dict(path=str(p),sha256=sha(p));saved=read(p)
  if cid not in term:
   require(zero_error(saved,protocol),'only authorized savedzero backenderror without term');require(cid not in seeds,'multiple prior failures require counter-preserving separate recovery');seeds[cid]=dict(request_id=rid,response_path=str(p),response_sha256=sha(p))
 complete,partial,cursor=split_prefix(plans,term);require(cursor<len(plans),'not a completed phase');next_cid=plans[cursor]['calls'][len(partial)];require(set(seeds)=={next_cid},'exact one pending original failed request, no skipped/readoutselected seed')
 return dict(plans=plans,completed=complete,partial=partial,cursor=cursor,seeds=seeds,raws=list(raw.values()),original_input_sha256=ish)


@contextmanager
def scope(bank):
 old=transport.CAPS.get(bank);expiry=transport.EXPIRY;transport.CAPS[bank]=CAPS[bank];bounds.CAPS[bank]=CAPS[bank];transport.EXPIRY=1793372400
 try:yield
 finally:
  transport.EXPIRY=expiry
  if old is None:transport.CAPS.pop(bank,None)
  else:transport.CAPS[bank]=old


def run(bank):
 source=source_gate();dest=CACHE/bank/PHASES[bank];supp=dest/'backend248';a=read(supp/'ADMISSION.json');pub=read(supp/'PUBLICATION.json');p=Path(pub['allocation_path']);live=read(supp/'LIVE_PROOF.PRIVATE.json')
 require(a['bank']==bank and a['source_sha256']==sha(source)and a['original_input_sha256']==sha(dest/'INPUT_SEAL.json')and a['original_admission_sha256']==sha(dest/'ADMISSION.json'),'unchanged bank/input/source');require(sha(p)==pub['allocation_sha256']==sha(supp/'ADMISSION.json')and subprocess.check_output(['git','show',pub['commit']+':'+str(p.relative_to(transport.ROOT))],cwd=transport.ROOT)==p.read_bytes(),'posted prospective handler and same-bank continuation')
 require(sha(supp/'LIVE_PROOF.PRIVATE.json')==a['live_proof_sha256']and 0<=time.time()-live['at_epoch']<300 and all(live[k]is True for k in('route_verified','account_privacy_verified','funded_remaining_bank_cap')),'fresh proof')
 _,(_,_,protocol,_)=registered.funded.route_api();saved=recover(dest,bank,protocol);require(saved['cursor']==a['recovered_completed']and len(saved['partial'])==a['recovered_partial_attempts']and saved['seeds']==read(supp/'RECOVERED_PREFIX.PRIVATE.json')['seeds'],'exact saved-state admission')
 job=dest/'outputs';require(not(job/'JUDGMENT_SEAL.json').exists(),'never completed phase replay');fd=os.open(supp/'EXECUTION_ONCE.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd);write(supp/'EXECUTION_ONCE.json',dict(pid=os.getpid(),source_sha256=sha(source),recovered_completed=saved['cursor'],zero_retry_limit=LIMITS[bank]));units=[];attempts=[];audits=[]
 def accept(plan,ts):
  t=ts[-1];attempts.extend(dict(x,unit_id=plan['unit']['id'],kind=plan['unit']['kind'],attempt=i)for i,x in enumerate(ts))
  if bank=='E118':units.append(t)
  else:units.append(dict(id=plan['unit']['id'],kind=plan['unit']['kind'],status=t['status'],code=t['result']['records'][0]if t['status']=='KEPT'else None,attempts=len(ts)-1,request_id=t['request_id'],response_sha256=t['response_sha256']))
 for plan,ts in zip(saved['plans'],saved['completed']):accept(plan,ts)
 original={}
 if bank=='E117':ref=read(dest/'INPUT_SEAL.json')['source_seals'][0];verify(ref['seal'],ref['sha256']);origin=Path(ref['seal']).parent;original=read(origin/'ORIGINAL_EVIDENCE.PRIVATE.json')
 with scope(bank):
  transport.unpaused();write(supp/'DISPATCH_GLOBAL_PROOF.PRIVATE.json',snapshot())
  try:
   with BackendTransport(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'),read(dest/'ADMISSION.json'),os.environ['OPENROUTER_API_KEY'],zero_limit=LIMITS[bank],seeds=saved['seeds'])as channel:
    for k,plan in enumerate(saved['plans'][saved['cursor']:],start=saved['cursor']):
     ts=list(saved['partial'])if k==saved['cursor']else[];validator=None
     if bank=='E117':expected,validator=raw_evidence_guard(lambda u:original57_call(u,channel.protocol),plan['unit'],original)
     for cid in plan['calls'][len(ts):]:
      if bank=='E117':require(channel.allowed[cid]['rendered']==expected['rendered'],'same original native renderer')
      t,audit=channel.call(cid,validator);ts.append(t);audits.append(audit)
      if is_final(t):break
     accept(plan,ts);write(job/'PROGRESS.json',dict(completed=len(units),n=len(saved['plans']),cost=channel.summary(),at_epoch=time.time(),authority='directGuivE118five/registered217.2/backend248'))
    raws={x['path']:x for x in saved['raws']+channel.physical}
    write(job/'RESPONSES.json'if bank=='E118'else'JUDGMENTS.json',units);write(job/'ATTEMPTS.json',attempts);write(job/'RAW_RESPONSE_BINDINGS.json',list(raws.values()));write(job/'ROUTE_AUDIT.json',dict(routes=channel.routes,requests=audits,recovered_raws_preserved=True));write(job/'COUNTS.json',dict(n=len(units),status_counts=dict(Counter(x['status']for x in units)),cost=channel.summary()));write(job/'BACKEND248_SOURCE_RECEIPT.json',dict(source_sha256=sha(source),continuation_sha256=sha(supp/'ADMISSION.json'),recovered_successes_not_resent=saved['cursor'],zero_retry_limit=LIMITS[bank],uncharged_errors_not_booked=True,original_failed_bytes_preserved=True))
    from datetime import datetime,timezone
    first=min(Path(x['path']).stat().st_mtime for x in raws.values());s=dict(experiment=bank,phase=read(dest/'INPUT_SEAL.json')['phase'],status='COMPLETE',first_output_utc=datetime.fromtimestamp(first,timezone.utc).isoformat(),input_sha256=sha(dest/'INPUT_SEAL.json'),source_seal_sha256=sha(source),route_verified=True,labels_cpu_only=True,redaction_audit_complete=True,redacted_records=0)
    if bank=='E117':write(job/'PATH_REDACTION_AUDIT.json',read(origin/'PATH_REDACTION_AUDIT.json'));s.update(redacted_records=read(origin/'PATH_REDACTION_AUDIT.json')['redacted_records'],E117_source_seal_sha256=sha(transport.HERE/'E117_SOURCE_SEAL.json'),part='main')
    else:s.update(E118b_source_seal_sha256=sha(transport.HERE/'E118B_SOURCE_SEAL.json'),phase='part_b')
    s['files']={p.name:sha(p)for p in job.iterdir()if p.is_file()and p.name!='JUDGMENT_SEAL.json'};write(job/'JUDGMENT_SEAL.json',s)
  except BaseException as exc:write(job/'BACKEND248_STOPPED.json',dict(error_type=type(exc).__name__,at_epoch=time.time(),no_resend=True));raise

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--bank',choices=['E118','E117'],required=True);a=p.parse_args();run(a.bank)
