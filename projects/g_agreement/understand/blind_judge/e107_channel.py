"""§218 source-bound outside generation + judging under one USD15 ledger.
No scientific renderer/cohort is defined here. I-2 supplies its sealed calls.
"""
import hashlib,json,os,shutil
from decimal import Decimal
from pathlib import Path
from .run import ROOT,payload
from . import funded_queue as funded
from .dispatch_lock import dispatch_lock
from .parallel_funded import patch_api
from .operational217 import audit_response
from .e99_channel import terminal_record
from .privacy79 import strings
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
HERE=ROOT/'results/g_agreement/understand/blind_judge/e107_bank'
SHARED=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-internals-b/cache/g_agreement/understand/funded_queue')
CAP=Decimal('15')


def frozen_wire(call,p):
    require(set(call)=={'id','phase','rendered'} and isinstance(call['id'],str) and bool(call['id']),'sealed call allowlist')
    phase=call['phase'];r=call['rendered'];require(phase in ('generation','judging'),'registered phase')
    require(set(r)=={'system','user','schema'},'rendered allowlist')
    require(r['system'] is None or isinstance(r['system'],str),'literal frozen system')
    require(isinstance(r['user'],str),'literal frozen user')
    w=payload([], '', 'E56',p);w['messages']=([dict(role='system',content=r['system'])] if r['system'] is not None else [])+[dict(role='user',content=r['user'])]
    if phase=='generation':
        require(r['system'] is None and r['schema'] is None,'outside text-only prefix+generic instruction supplied verbatim')
        w['max_tokens']=256;w.pop('response_format')
    elif r['schema'] is None:w.pop('response_format')
    else:w['response_format']={'type':'json_schema','json_schema':r['schema']}
    return w


def privacy_wire(call,w,original,p):
    require(w==frozen_wire(call,p),'exact frozen wire and token cap')
    for text in strings(w['messages']):original('extract',[dict(id=call['id'],readout=text)],w)


def decode(call,saved,p,validator=None):
    audit=audit_response(saved,p);choice=saved['response']['choices'][0]
    if call['phase']=='generation':
        content=choice['message'].get('content');require(isinstance(content,str),'generation text required')
        # Generation length/end metadata is retained, never changed into a judge code.
        result=dict(id=call['id'],phase='generation',status='GENERATED',text=content,finish_reason=choice['finish_reason'],truncated=choice['finish_reason']=='length',refusal=choice['message'].get('refusal'))
    elif audit.get('terminal_unparseable'):
        result=dict(id=call['id'],phase='judging',status='UNPARSEABLE',reason='CHARGED_LENGTH',result=None)
    else:
        rendered=dict(call['rendered'],response_format='text')
        result=terminal_record(call['id'],saved['http_status'],saved['response'],rendered,validator)
        require(result['status'] in ('KEPT','UNPARSEABLE','REFUSED'),'unrecognized provider error; stop bank')
        result['phase']='judging'
    return result,audit


def source_gate():
    for n,h in read(HERE/'SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'E107 source pin')


class E107Transport:
    """Fresh process/context per sealed phase; both phases share one ledger.
    I-2 retains inventory/admission/phase order and freezes its rubric validators.
    """
    def __init__(self,input_seal,input_sha,admission,key):
        source_gate();self.path=Path(input_seal);self.input_sha=input_sha
        seal=verify(self.path,input_sha)
        require(seal['experiment']=='E107' and seal['frozen_before_calls'] is True and seal['labels_cpu_only'] is True and 'CALLS.json' in seal['files'],'frozen owner calls')
        require(bool(seal['source_seals']),'frozen prefix/instruction/rubric provenance')
        for s in seal['source_seals']:verify(s['seal'],s['sha256'])
        self.calls=read(self.path.parent/'CALLS.json');require(self.calls and len({x['id'] for x in self.calls})==len(self.calls),'unique complete phase calls')
        require(len({x['phase'] for x in self.calls})==1,'one sealed phase per context')
        if self.calls[0]['phase']=='judging':
            require(any((lambda v:v.get('experiment')=='E107' and v.get('phase')=='generation' and v.get('status')=='COMPLETE')(read(s['seal'])) for s in seal['source_seals']),'judging binds completed generation source seal')
        r=admission;total=Decimal(str(r['actual_plus_open_caps_usd']))
        require(r.get('issuer')=='integrator' and r.get('verified') is True and r.get('bank')=='E107' and r.get('reservation_included') is True and Decimal(str(r['allocation_usd']))==CAP and total.is_finite() and CAP<=total<=1000,'combined generation+judging USD15 current admission')
        require(r['input_sha256']==input_sha and r['source_seal_sha256']==sha(HERE/'SOURCE_SEAL.json'),'source-bound phase allocation')
        self.admission=r;self.key=key;self.root=SHARED/'E107';self.allowed={x['id']:x for x in self.calls}

    def __enter__(self):
        require(not (SHARED/'PAUSED_402.json').exists(),'all banks paused HTTP402')
        self.root.mkdir(parents=True,exist_ok=True);self.lock=dispatch_lock(self.root/'DISPATCH.lock');self.lock.__enter__()
        try:
            route,(self.api,self.privacy,self.p,self.io)=funded.route_api();self.api.CAP=CAP
            self.io.CACHE=self.root/'ledger/route';self.io.CACHE.mkdir(parents=True,exist_ok=True)
            require(sha(route['privacy_proof'])==route['privacy_proof_sha256'],'account privacy proof')
            shutil.copyfile(route['privacy_proof'],self.io.CACHE/'OPENROUTER_PRIVACY_PROOF.json');self.routes=self.privacy.check_route(self.key)
            self.saved=(self.p.payload,self.p.validate,self.privacy.check_wire,self.io.digest)
            self.original_check=self.privacy.check_wire
            for x in self.calls:privacy_wire(x,frozen_wire(x,self.p),self.original_check,self.p)
            self.client=self.api.Client(self.root/'ledger',self.key);book,done=self.client.ledger.totals();require(set(book)==done,'unresolved charge; reconcile through Ledger before resume')
            # Pacing and all-bank402 latch always use the canonical shared root.
            funded.CACHE=SHARED;patch_api(self.api,self.io,'E107')
            self.p.payload=lambda stage,batch,unused=None:frozen_wire(self.allowed[batch[0]['id']],self.p)
            self.p.validate=lambda stage,value,batch,unused=None:value
            self.privacy.check_wire=lambda stage,batch,w,unused=None:privacy_wire(self.allowed[batch[0]['id']],w,self.original_check,self.p)
            return self
        except BaseException:
            self.lock.__exit__(None,None,None);raise

    def call(self,call_id,validator=None):
        require(not (SHARED/'PAUSED_402.json').exists(),'all banks paused HTTP402')
        import time
        require(time.time()<1793336400,'standing authorization expired')
        x=self.allowed[call_id];stage='E107_'+x['phase'];prefix=stage+':'+self.input_sha+':'+call_id+':'
        self.io.digest=lambda value:hashlib.sha256((prefix+value).encode()).hexdigest()
        result=self.client.one(stage,[dict(id=call_id)])
        path=self.root/'ledger'/stage/(result['id']+'.response.json');require(path.exists(),'unsent/budget/unknown stop; no guessed output')
        saved=read(path);funded.credit_gate(saved,path,'E107',stage,result['id'])
        require(not self.client.latch.is_set(),'transport bank stop')
        terminal,audit=decode(x,saved,self.p,validator)
        require(result['id'] in self.client.ledger.totals()[1],'known actual charge settled')
        terminal.update(request_id=result['id'],response_sha256=sha(path),input_sha256=self.input_sha)
        write(path.with_suffix('.terminal.json'),terminal)
        return terminal,dict(audit,request_id=result['id'],response_sha256=sha(path))

    def summary(self):return self.client.ledger.summary()

    def __exit__(self,*args):
        self.p.payload,self.p.validate,self.privacy.check_wire,self.io.digest=self.saved
        return self.lock.__exit__(*args)
