"""Prospective approved E99 phase1 USD150 transport; original USD40 source untouched.
Retains frozen renderers/route and original canonical ledger; §217 fatal/length policy.
"""
import hashlib
import json
import shutil
from pathlib import Path
from projects.g_agreement.understand.blind_judge.run import route_modules
from projects.g_agreement.understand.blind_judge.e99_accounting import LEDGER_ROOT
from decimal import Decimal
CAP=Decimal(150)
from projects.g_agreement.understand.blind_judge.e99_error217c2 import known_failure
from projects.g_agreement.understand.blind_judge.e99_channel import frozen_wire,validate_wire_privacy,terminal_record
from projects.g_agreement.understand.blind_judge.dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read,sha,write
from projects.g_agreement.readerbench.scoring import require


class E99ContinuationTransport:
    """Use as a context manager in a fresh integrator process; key never serialized."""
    def __init__(self,route,key,budget_receipt,root=LEDGER_ROOT):
        require(budget_receipt.get('issuer')=='integrator' and budget_receipt.get('verified') is True and budget_receipt.get('E99_allocation_usd')==150 and budget_receipt.get('phase1_calls')==6680 and budget_receipt.get('continuation_requires_actual_gate') is True and budget_receipt.get('reservation_included') is True,'integrator approved E99 phase1 USD150 allocation')
        from decimal import Decimal
        total=Decimal(str(budget_receipt['global_judging_committed_including_reservation_usd']))
        require(total.is_finite() and 150<=total<=1000,'global USD1000 envelope including E99 phase1')
        self.route=route;self.key=key;self.root=Path(root);self.before_send=None;self.pause_all=None
        require(self.root==LEDGER_ROOT,'fixed separate E99 ledger')

    def __enter__(self):
        self.root.mkdir(parents=True,exist_ok=True);self.lock=dispatch_lock(self.root/'DISPATCH.lock');self.lock.__enter__()
        try:
            from projects.g_agreement.understand.blind_judge.run import ROOT
            manifest=read(ROOT/'results/g_agreement/understand/blind_judge/e99_channel/SOURCE_SEAL.json')
            for name,digest in manifest['files'].items():require(sha(ROOT/name)==digest,'E99 source pin')
            for name in ('api','privacy','protocol','io'):
                path=str(Path(self.route['e10_source'])/(name+'.py'))
                require(sha(path)==self.route['files'][path],'E56 external source pin')
            self.api,self.privacy,self.protocol,self.io=route_modules(self.route);self.api.CAP=CAP
            for mod in (self.api,self.privacy,self.protocol,self.io):
                require(sha(mod.__file__)==self.route['files'][mod.__file__],'E56 implementation source pin')
            self.saved=(self.protocol.payload,self.protocol.validate,self.privacy.check_wire,self.io.digest)
            self.io.CACHE=self.root/'route';self.io.CACHE.mkdir(exist_ok=True)
            require(sha(self.route['privacy_proof'])==self.route['privacy_proof_sha256'],'existing privacy proof')
            shutil.copyfile(self.route['privacy_proof'],self.io.CACHE/'OPENROUTER_PRIVACY_PROOF.json')
            routes=self.privacy.check_route(self.key)
            write(self.root/'ROUTE_AUDIT.json',dict(routes=routes,inventory_sha256=sha(self.io.CACHE/'last_zdr_route_inventory.json'),privacy_proof_sha256=sha(self.route['privacy_proof'])))
            self.client=self.api.Client(self.root,self.key)
            return self
        except BaseException:
            self.lock.__exit__(None,None,None);raise

    def __exit__(self,*exc):
        self.protocol.payload,self.protocol.validate,self.privacy.check_wire,self.io.digest=self.saved
        self.lock.__exit__(*exc)

    def call(self,call_id,rendered,validator=None):
        require(len(call_id)==32 and all(c in '0123456789abcdef' for c in call_id),'opaque frozen call ID')
        wire=frozen_wire(rendered,self.protocol)
        validate_wire_privacy(wire,self.saved[2])
        self.protocol.payload=lambda *a:wire
        # E10 Client parses JSON; the frozen family validator runs below for terminal accounting.
        self.protocol.validate=lambda stage,value,batch,unused=None:value
        self.privacy.check_wire=lambda stage,batch,w,unused=None:validate_wire_privacy(w,self.saved[2])
        history=[]
        for attempt in range(3):
            prefix='E99:'+call_id+':'+str(attempt)+':'
            self.io.digest=lambda value:hashlib.sha256((prefix+value).encode()).hexdigest()
            stage='E99_attempt'+str(attempt)
            require(callable(self.before_send) and callable(self.pause_all),'fresh global/authority and all-bank402 callbacks required')
            self.before_send(wire)
            result=self.client.one(stage,[dict(id=call_id,readout='')])
            response=self.root/stage/(result['id']+'.response.json')
            if response.exists():
                r=read(response)
                body=r['response'];http=r['http_status']
                if http==402:
                    self.pause_all(response);raise RuntimeError('HTTP402_ALL_BANKS_PAUSE')
                require(http==200,'UNRECOGNISED_PROVIDER_ERROR_STOP')
                known=known_failure(call_id,r)
                if known is not None:
                    known.update(attempt=attempt,request_id=result['id'],attempt_history=history+[dict(id=call_id,status='FAILED',reason='INCOMPLETE_COMPLETION',attempt=attempt,request_id=result['id'])])
                    write(self.root/stage/(result['id']+'.terminal.json'),known)
                    return known
                require(not body.get('error'),'WRAPPED_PROVIDER_ERROR_STOP')
                require(body.get('provider')=='Google' and body.get('model') in ('google/gemini-3.1-flash-lite','google/gemini-3.1-flash-lite-001'),'ROUTE_STOP')
                cost=Decimal(str(body.get('usage',{}).get('cost')))
                require(cost.is_finite() and cost>=0,'UNKNOWN_COST_STOP')
                finish=body['choices'][0].get('finish_reason')
                require(not body['choices'][0].get('error') and finish in ('stop','length'),'UNKNOWN_FINISH_OR_WRAPPED_ERROR_STOP')
                if finish=='length':terminal=dict(id=call_id,status='UNPARSEABLE',reason='CHARGED_LENGTH_TERMINAL_NO_RETRY')
                else:terminal=terminal_record(call_id,http,body,rendered,validator)
            else:
                raise RuntimeError('UNSENT_OR_UNRESOLVED_NO_REPLAY')
            terminal['attempt']=attempt
            history.append(dict(id=call_id,status=terminal['status'],reason=terminal.get('reason',''),attempt=attempt,request_id=result['id']))
            # A schema-invalid HTTP200 may have been cached as OK by the transport; this
            # does not make the scientific result valid. Retry exactly the same wire alone.
            if terminal.get('reason')=='CHARGED_LENGTH_TERMINAL_NO_RETRY' or terminal['status']!='UNPARSEABLE':break
        terminal['request_id']=result['id']
        terminal['attempt_history']=history
        write(self.root/stage/(result['id']+'.terminal.json'),terminal)
        return terminal

    def summary(self):return self.client.ledger.summary()

    def finish(self,grid,terminal,out):
        """Integrator supplies complete sealed cell/call DAG, including blocked stages."""
        from projects.g_agreement.understand.blind_judge.e99_accounting import summarize
        from projects.g_agreement.understand.blind_judge.e99_families import EXPORT_SHA
        out=Path(out);require(not out.exists(),'do not overwrite E99 terminal export')
        accounting=summarize(grid['cells'],grid['calls'],terminal)
        out.mkdir(parents=True)
        write(out/'GRID.json',grid);write(out/'TERMINAL.json',terminal);write(out/'ACCOUNTING.json',accounting)
        write(out/'COST.json',self.summary())
        audit=read(self.root/'ROUTE_AUDIT.json');write(out/'ROUTE_AUDIT.json',audit)
        evidence={}
        for row in terminal:
            for attempt in row.get('attempt_history',[]):
                stage='E99_attempt'+str(attempt['attempt']);rid=attempt['request_id']
                for suffix in ('request','response','result','terminal'):
                    path=self.root/stage/(rid+'.'+suffix+'.json')
                    if path.exists():evidence[str(path)]=sha(path)
        write(out/'CALL_EVIDENCE.json',evidence)
        write(out/'JUDGMENT_SEAL.json',dict(experiment='E99',export_seal_sha256=EXPORT_SHA,
            route_inventory_verified=bool(audit['routes']),privacy_proof_sha256=audit['privacy_proof_sha256'],
            status='TERMINAL_GRID_WITH_PER_FAMILY_MISSINGNESS',
            files={p.name:sha(p) for p in out.iterdir() if p.is_file()}))
