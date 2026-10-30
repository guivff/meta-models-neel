"""Source-bound uncharged backend retries; no partial content is ever scored.
E118: direct Guiv five doubling retries. Other banks: registered217.2 two.
Every retry has a new physical identity; old successful requests are read-only.
"""
import hashlib,time
from decimal import Decimal
from pathlib import Path
from . import transport,resume_e340 as bounds
from .. import parallel_funded
from projects.g_agreement.readerbench.io import read,write,sha
from projects.g_agreement.readerbench.scoring import require


def zero_error(saved,protocol):
 if saved.get('http_status')!=200:return False
 body=saved.get('response',{});choices=body.get('choices',[])
 require(body.get('provider')==protocol.PROVIDER_NAME and body.get('model')in(protocol.MODEL,protocol.MODEL+'-001'),'actual route before backend retry')
 require(len(choices)==1,'one original choice before retry classification');choice=choices[0];cost=body.get('usage',{}).get('cost');require(cost is not None and type(cost)is not bool,'explicit actual cost required')
 cost=Decimal(str(cost));require(cost.is_finite()and cost>=0,'known finite actual charge')
 code=(choice.get('error')or{}).get('code');embedded=code in (429,'429')or(type(code)is int and 500<=code<600)
 return cost==0 and(choice.get('finish_reason')=='error'or embedded)


def retry_action(saved,protocol,zero_used,rate_used,zero_limit):
 if saved.get('http_status')==429:
  require(not saved.get('response',{}).get('choices'),'429 completion ambiguity stops bank')
  return('rate',30*2**rate_used)if rate_used<5 else('rate_exhausted',0)
 if zero_error(saved,protocol):return('zero',30*2**zero_used)if zero_used<zero_limit else('zero_exhausted',0)
 return 'decode',0


def retry_id(base,z,r):return hashlib.sha256(('BACKEND248:'+base+':z'+str(z)+':r'+str(r)).encode()).hexdigest()


def cap_guard(api,client,unpaced,cap):
 namespaces=[api.__dict__]+[getattr(f,'__func__',f).__globals__ for f in(client.ledger.reserve,client.ledger.settle,client.ledger.summary,unpaced)]
 for n in namespaces:require('CAP'in n,'actual cap namespace');n['CAP']=Decimal(cap)


class BackendTransport(bounds.ResumeTransport):
 def __init__(self,*args,zero_limit=2,seeds=None,**kwargs):
  super().__init__(*args,**kwargs);self.zero_limit=zero_limit;self.seeds=seeds or{};self.exhausted={};self.state_home=self.path.parent/'backend248/physical_retry_state';self.state_home.mkdir(parents=True,exist_ok=True)
 def __enter__(self):
  value=super().__enter__();self.cap=Decimal(self.admission['allocation_usd']);owner=self
  def one(client,stage,items,taxonomy=None):
   wire=owner.api.P.payload(stage,items,taxonomy);canonical=owner.io.canonical(wire);digest=owner.io.digest;base=digest(canonical);cid=items[0]['id'];state_path=owner.state_home/(base+'.json');require(not state_path.exists(),'retry counters never reset; saved-state recovery required')
   z=r=0;seed=owner.seeds.get(cid);result=None
   if seed:
    p=Path(seed['response_path']);require(sha(p)==seed['response_sha256']and seed['request_id']==base,'exact original failed physical identity');saved=read(p);require(zero_error(saved,owner.protocol),'only explicitzero backend seed');result=dict(id=base);owner.physical.append(dict(path=str(p),sha256=sha(p)));last=p.stat().st_mtime
   else:saved=None;last=0
   try:
    while True:
     if saved is not None:
      if saved['http_status']==402:transport.pause(owner.bank,path)
      action,delay=retry_action(saved,owner.protocol,z,r,owner.zero_limit)
      if action=='rate':
       bounds.book_bound(client.root,result['id'],path,owner.cap)
      elif action=='rate_exhausted':
       bounds.book_bound(client.root,result['id'],path,owner.cap);owner.exhausted[cid]='RATE_LIMIT_EXHAUSTED';return result
      elif action=='zero_exhausted':owner.exhausted[cid]='UNCHARGED_BACKEND_RETRIES_EXHAUSTED';return result
      elif action=='decode':return result
      while time.time()<last+delay:transport.unpaused();time.sleep(min(1,last+delay-time.time()))
      if action=='zero':z+=1
      else:r+=1
      rid=retry_id(base,z,r)
     else:rid=base
     path=client.root/stage/(rid+'.response.json');request=client.root/stage/(rid+'.request.json');result_file=client.root/stage/(rid+'.result.json')
     require(not path.exists()and not request.exists()and not result_file.exists(),'no overwrite/resend of any saved physical request')
     write(state_path,dict(bank=owner.bank,call_id=cid,original_request_id=base,physical_request_id=rid,zero_retries=z,zero_retry_limit=owner.zero_limit,rate_retries=r,at_epoch=time.time(),diagnostic_partial_content_never_scored=True))
     owner.io.digest=lambda value,rid=rid:rid;parallel_funded.claim_slot(owner.bank);transport.unpaused();cap_guard(owner.api,client,owner.unpaced,owner.cap);result=owner.unpaced(client,stage,items,taxonomy)
     require(path.exists(),'no response: stop without guessed settlement/resend');saved=read(path);owner.physical.append(dict(path=str(path),sha256=sha(path)));last=path.stat().st_mtime
     if saved['http_status']==402:transport.pause(owner.bank,path)
     require(not client.latch.is_set(),'bank API failure latch')
     if saved['http_status']!=429:require(result['id']in client.ledger.totals()[1],'explicit settled charge before any continuation')
   finally:owner.io.digest=digest
  self.api.Client.one=one;cap_guard(self.api,self.client,self.unpaced,self.cap);return value
 def summary(self):cap_guard(self.api,self.client,self.unpaced,self.cap);return super().summary()
 def call(self,cid,validator=None):
  transport.unpaused();c=self.allowed[cid];stage=self.bank+'_'+c['phase'];prefix='WIC:'+stage+':'+self.input_sha+':'+cid+':'
  self.io.digest=lambda value:hashlib.sha256((prefix+value).encode()).hexdigest();result=self.client.one(stage,[dict(id=cid)]);p=self.root/'ledger'/stage/(result['id']+'.response.json');saved=read(p)
  if cid in self.exhausted:
   terminal=dict(id=cid,phase=c['phase'],status='UNPARSEABLE',reason=self.exhausted[cid],result=None);audit=dict(terminal_missing=True,partial_content_diagnostic_only=True)
  else:terminal,audit=transport.decode(c,saved,self.protocol,validator)
  require(result['id']in self.client.ledger.totals()[1],'no unknown charge classified');terminal.update(request_id=result['id'],response_sha256=sha(p),input_sha256=self.input_sha);write(p.with_suffix('.terminal.json'),terminal);return terminal,dict(audit,request_id=result['id'],response_sha256=sha(p))
