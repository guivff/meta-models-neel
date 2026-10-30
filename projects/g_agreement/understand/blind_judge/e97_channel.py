"""Registered E97 E56/§202 bank pattern; I-5 supplies the sealed blind packet."""
import hashlib,json,re,shutil
from decimal import Decimal
from pathlib import Path
from .run import ROOT
from . import funded_queue as f
from .later_runner import channel_payload,classify
from .judgment_adapter402 import render_record
from .operational217 import audit_response,judge,adapt,truncated
from .privacy79 import check_decoded
from .rubric202 import amended,original_ids,BASE
from .dispatch_lock import dispatch_lock
from .parallel_funded import patch_api
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
HERE=ROOT/'results/g_agreement/understand/blind_judge/e97_bank'
SHARED=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-internals-b/cache/g_agreement/understand/funded_queue')
CAP=Decimal('15')


def sources():
    for n,h in read(HERE/'SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'E97 source pin')


def channels(records):
    require(len(records)==6668 and len({x['id'] for x in records})==6668,'all6668 frozen regex-unresolved native units')
    for x in records:
        require(set(x)=={'id','property','readout'} and bool(re.fullmatch('[a-f0-9]{32}',x['id'])),'opaque ID/property/values/readout only')
        require(isinstance(x['property'],dict) and set(x['property'])=={'definition','values'} and isinstance(x['property']['definition'],str) and x['property']['definition'] and isinstance(x['readout'],str) and set(x['property']['values'])=={'A','B'},'frozen bank property/two values/native text')
    sample=original_ids([x['id'] for x in records],'E97');require(len(sample)==1667,'seeded25percent original-rubric check')
    selected=set(sample);old=BASE.read_text();primary=amended().decode()
    return [('primary',[render_record(dict(id=x['id'],property=x['property']['definition'],values=x['property']['values'],readout=x['readout']),primary) for x in records],primary),('original',[render_record(dict(id=x['id'],property=x['property']['definition'],values=x['property']['values'],readout=x['readout']),old) for x in records if x['id'] in selected],old)]


class E97Bank:
    def __init__(self,input_seal,input_sha):
        sources();self.path=Path(input_seal);self.input_sha=input_sha
        s=verify(self.path,input_sha)
        require(s['experiment']=='E97' and s['status']=='FROZEN_READY' and s['labels_cpu_only'] is True and s['native_per_reader_counts']=={'oracle':3360,'nla':3360} and s['selected_per_reader_counts']=={'oracle':3308,'nla':3360} and s['regex_resolved_retained']==52,'registered full native test intake')
        require('CANDIDATES.PRIVATE.json' in s['files'] and bool(s['source_seals']),'frozen readout/property/GO/input provenance')
        for x in s['source_seals']:verify(x['seal'],x['sha256'])
        self.channels=channels(read(self.path.parent/'CANDIDATES.PRIVATE.json'))

    def preflight(self):
        _,(api,privacy,p,io)=f.route_api();bound=Decimal(0);blocked=set()
        for name,xs,rubric in self.channels:
            for start in range(0,len(xs),4):
                batch=xs[start:start+4];w=channel_payload(batch,rubric,'E56',p);bound+=api.upper(w)
                try:check_decoded(privacy.check_wire,batch,w)
                except ValueError:blocked.update(x['id'] for x in batch)
        return dict(bank='E97',status='READY' if not blocked else 'BLOCKED_PRIVACY',primary_records=6668,old_rubric_records=1667,old_rubric_ids=sorted(x['id'] for x in self.channels[1][1]),sampling_seed=20261028,cap_usd='15',sum_initial_output_cap_bounds_usd=str(bound),privacy_static_pass=not blocked,blocked_opaque_ids=sorted(blocked),input_sha256=self.input_sha,source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'))

    def run(self,receipt,key):
        a=self.preflight();require(a['privacy_static_pass'],'exact wire privacy block; no redaction/drop')
        require(receipt.get('issuer')=='integrator' and receipt.get('verified') is True and receipt.get('bank')=='E97' and receipt.get('reservation_included') is True and Decimal(str(receipt['allocation_usd']))==CAP and CAP<=Decimal(str(receipt['actual_plus_open_caps_usd']))<=1000,'posted registered USD15/current global allocation')
        require(receipt['input_sha256']==self.input_sha and receipt['source_seal_sha256']==a['source_seal_sha256'],'exact source/intake admission')
        require(not (SHARED/'PAUSED_402.json').exists(),'shared402pause')
        root=SHARED/'E97';root.mkdir(parents=True,exist_ok=True)
        with dispatch_lock(root/'DISPATCH.lock'):
            job=root/'judgments';require(not (job/'JUDGMENT_SEAL.json').exists(),'already terminal; no replay');job.mkdir(exist_ok=True)
            route,(api,privacy,p,io)=f.route_api();api.CAP=CAP;ledger=root/'ledger';ledger.mkdir(exist_ok=True)
            io.CACHE=ledger/'route';io.CACHE.mkdir(exist_ok=True)
            require(sha(route['privacy_proof'])==route['privacy_proof_sha256'],'account privacy proof')
            shutil.copyfile(route['privacy_proof'],io.CACHE/'OPENROUTER_PRIVACY_PROOF.json');routes=privacy.check_route(key)
            saved=(p.payload,p.validate,privacy.check_wire,io.digest);original=privacy.check_wire
            f.CACHE=SHARED;patch_api(api,io,'E97');client=api.Client(ledger,key);book,done=client.ledger.totals();require(set(book)==done,'reconcile unknown charges through Ledger before resume')
            audits=[];outputs={};attempts={}
            write(root/'ADMISSION.json',dict(preflight=a,receipt=receipt));write(root/'STATUS.json',dict(bank='E97',status='RUNNING'))
            try:
                for name,items,rubric in self.channels:
                    p.payload=lambda stage,batch,unused=None:channel_payload(batch,rubric,'E56',p)
                    p.validate=lambda stage,value,batch,unused=None:classify(batch,value)
                    privacy.check_wire=lambda stage,batch,w,unused=None:check_decoded(original,batch,w)
                    def send(batch,attempt):
                        import time
                        require(time.time()<1793336400,'standing authorization expired')
                        require(not (SHARED/'PAUSED_402.json').exists(),'shared402pause')
                        stage=f'E97_{name}_attempt{attempt}';prefix=stage+':'+self.input_sha+':'
                        io.digest=lambda value:hashlib.sha256((prefix+value).encode()).hexdigest()
                        result=client.one(stage,batch);rp=ledger/stage/(result['id']+'.response.json');require(rp.exists(),'unsent/budget/unknown stop')
                        response=read(rp);f.credit_gate(response,rp,'E97',stage,result['id']);require(not client.latch.is_set(),'transport bank stop')
                        audit=audit_response(response,p);require(result['id'] in client.ledger.totals()[1],'known actual charge settled')
                        audits.append(dict(audit,request_id=result['id'],response_sha256=sha(rp)))
                        write(job/'LIVE_PROGRESS.json',dict(bank='E97',channel=name,verified_requests=len(audits),cost=client.ledger.summary()))
                        if audit.get('terminal_unparseable'):return truncated(batch)
                        if result['status']=='OK':return result['value']
                        try:json.loads(response['response']['choices'][0]['message']['content'])
                        except (ValueError,TypeError):return classify(batch,{})
                        raise RuntimeError('unknown provider failure')
                    terminal=judge(items,send);outputs[name],attempts[name]=adapt(terminal,items)
                for name,data in outputs.items():write(job/(name.upper()+'.json'),data)
                write(job/'ATTEMPTS.json',attempts);write(job/'ADMISSION.json',read(root/'ADMISSION.json'))
                write(job/'ROUTE_AUDIT.json',dict(routes=routes,requests=audits,privacy_proof_sha256=sha(route['privacy_proof']),inventory_sha256=sha(io.CACHE/'last_zdr_route_inventory.json')))
                write(job/'COST.json',client.ledger.summary())
                write(job/'JUDGMENT_SEAL.json',dict(bank='E97',input_sha256=self.input_sha,source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),route_verified=bool(routes) and bool(audits),redaction_audit_complete=True,redacted_opaque_ids=[],primary_records=6668,old_rubric_records=1667,files={x.name:sha(x) for x in job.iterdir() if x.is_file() and x.name!='JUDGMENT_SEAL.json'}))
                write(root/'STATUS.json',dict(bank='E97',status='COMPLETE',cost=client.ledger.summary()))
            except Exception as exc:
                write(root/'STATUS.json',dict(bank='E97',status='PAUSED_402' if (SHARED/'PAUSED_402.json').exists() else 'BLOCKED',error_type=type(exc).__name__,cost=client.ledger.summary()));raise
            finally:p.payload,p.validate,privacy.check_wire,io.digest=saved
