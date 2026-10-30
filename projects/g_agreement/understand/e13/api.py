"""E13 hard reserve-before-send ledger; exact-wire cache; no retries/format repair."""
from decimal import Decimal
from pathlib import Path
import os,json,fcntl,time,threading,requests
from . import io as I,protocol as P
CAP=Decimal('5');PROMPT=Decimal('0.00000025');COMPLETION=Decimal('0.0000015')

def upper(wire):return Decimal('1.25')*(Decimal(len(I.canonical(wire).encode())+1024)*PROMPT+Decimal(wire['max_tokens'])*COMPLETION)
class Ledger:
 def __init__(self,path):self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
 def totals(self):
  book={};settled=set()
  if self.path.exists():
   for x in I.rows(self.path):
    if x['event']=='reserve':
     if x['id'] in book:raise ValueError('duplicate send reservation')
     book[x['id']]=Decimal(x['usd'])
    elif x['event']=='settle':
     if x['id'] not in book or x['id'] in settled:raise ValueError('settlement identity')
     book[x['id']]=Decimal(x['usd']);settled.add(x['id'])
    else:raise ValueError('unknown ledger event')
  return book,settled
 def append(self,f,event,rid,cost):f.write(I.canonical({'event':event,'id':rid,'usd':str(cost),'at':time.time()})+'\n');f.flush();os.fsync(f.fileno())
 def reserve(self,rid,cost):
  with self.path.open('a+') as f:
   fcntl.flock(f,fcntl.LOCK_EX);book,_=self.totals()
   if rid in book:raise RuntimeError('already sent/reserved; no retry')
   if sum(book.values())+cost>CAP:return False
   self.append(f,'reserve',rid,cost);return True
 def settle(self,rid,cost):
  cost=Decimal(str(cost))
  if not cost.is_finite() or cost<0:raise RuntimeError('invalid actual cost')
  with self.path.open('a+') as f:
   fcntl.flock(f,fcntl.LOCK_EX);book,done=self.totals()
   if rid not in book or rid in done:raise RuntimeError('bad settlement')
   self.append(f,'settle',rid,cost)
   if cost>book[rid] or sum(book.values())-book[rid]+cost>CAP:raise RuntimeError('actual charge exceeded frozen reservation; stop')
 def summary(self):
  book,done=self.totals();return {'actual_usd':str(sum((v for k,v in book.items() if k in done),Decimal(0))),'unresolved_reserve_usd':str(sum((v for k,v in book.items() if k not in done),Decimal(0))),'committed_usd':str(sum(book.values(),Decimal(0))),'cap_usd':str(CAP)}

class Client:
 def __init__(self,root,key,send=None):
  self.root=Path(root);self.root.mkdir(parents=True,exist_ok=True);self.ledger=Ledger(self.root/'ledger.jsonl');self.key=key;self.send=send;self.latch=threading.Event()
 def one(self,stage,items,taxonomy=None):
  wire=P.payload(stage,items,taxonomy);P.check_wire(stage,items,wire,taxonomy);rid=I.digest(I.canonical(wire));folder=self.root/stage;folder.mkdir(exist_ok=True);result=folder/(rid+'.result.json')
  if result.exists():return I.read(result)
  if self.latch.is_set():return {'id':rid,'status':'MISSING','reason':'FAILURE_LATCH'}
  bound=upper(wire)
  try:admitted=self.ledger.reserve(rid,bound)
  except RuntimeError:return {'id':rid,'status':'MISSING','reason':'PRIOR_RESERVED_NO_RESPONSE_NO_RETRY'}
  if not admitted:return {'id':rid,'status':'MISSING','reason':'BUDGET_UNSENT'}
  I.save(folder/(rid+'.request.json'),{'wire':wire,'upper_usd':str(bound)})
  value={'id':rid,'status':'MISSING'}
  try:
   if self.send is None:
    q=requests.post('https://openrouter.ai/api/v1/chat/completions',json=wire,headers={'Authorization':'Bearer '+self.key,'Content-Type':'application/json'},timeout=180,allow_redirects=False);status=q.status_code
    try:response=q.json()
    except ValueError:response={'error_class':'NON_JSON'}
   else:status,response=self.send(wire)
   I.save(folder/(rid+'.response.json'),{'http_status':status,'response':response})
   cost=response.get('usage',{}).get('cost')
   if cost is not None:self.ledger.settle(rid,cost)
   if status in (401,402,403):self.latch.set()
   if status!=200:raise ValueError('HTTP_'+str(status))
   if response.get('provider')!=P.PROVIDER_NAME or response.get('model') not in [P.MODEL,P.MODEL+'-001']:self.latch.set();raise ValueError('model/provider mismatch')
   choice=response['choices'][0]
   if choice.get('finish_reason')!='stop':raise ValueError('truncated/refused response')
   v=P.validate(stage,json.loads(choice['message']['content']),items,taxonomy)
   if cost is None:raise ValueError('unknown cost remains reserved')
   value.update(status='OK',value=v)
  except RuntimeError:self.latch.set();raise
  except (ValueError,KeyError,IndexError,TypeError,requests.RequestException) as e:value['reason']=str(e) if isinstance(e,ValueError) else type(e).__name__
  I.save(result,value);return value
