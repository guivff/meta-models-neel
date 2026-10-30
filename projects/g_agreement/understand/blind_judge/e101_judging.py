"""E101 two-cell judging only; USD5 ledger and shared funded-queue HTTP402 latch."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from decimal import Decimal
from pathlib import Path
from . import funded_queue as funded
from .run import ROOT
from .later_runner import channel_payload,classify,judge
from .judgment_adapter402 import render_record,adapt_grid
from .privacy79 import redact,check_decoded
from .wmech2_channel import response_audit
from .dispatch_lock import dispatch_lock
from projects.g_agreement.e101.contract import committed_dose
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
HERE=ROOT/'results/g_agreement/understand/blind_judge/e101_bank'
CACHE=funded.CACHE/'E101'
CAP=Decimal('5')

def source_gate():
    for name,h in read(HERE/'SOURCE_SEAL.json')['files'].items():require(sha(ROOT/name)==h,'E101 judge source pin')

def validate_grid(items,row):
    require(len(items)==168 and len({x['id'] for x in items})==168,'168 unique test readouts')
    groups={}
    for x in items:
        require(x['row']==row and x['block']==44 and x['alpha']==4 and x['condition'] in ('steered','random'),'eligible row/block/dose/condition only')
        groups.setdefault(x['base_id'],set()).add(x['condition'])
    require(len(groups)==84 and all(g=={'steered','random'} for g in groups.values()),'same84 items both conditions')

def prepare():
    source_gate();cfg=read(HERE/'INPUTS.json');require(cfg['cap_usd']==5,'shared cap5')
    doses=committed_dose(ROOT,ROOT/cfg['dose_path'],cfg['dose_commit'],cfg['dose_sha256'])
    target_seal=verify(cfg['targets'],cfg['targets_sha256']);require(target_seal['experiment']=='E101' and target_seal['labels_cpu_only'] is True,'CPU owner target seal')
    targets={x['id']:x for x in read(Path(cfg['targets']).parent/'TARGETS.json')};require(len(targets)==588,'registered full target inventory')
    CACHE.mkdir(parents=True,exist_ok=True)
    if (CACHE/'blind/BLIND_SEAL.json').exists():
        verify(CACHE/'blind/BLIND_SEAL.json',read(CACHE/'ADMISSION.json')['blind_seal_sha256']);return read(CACHE/'ADMISSION.json')
    rows=[]
    for s in cfg['shards']:
        ip=Path(s['input']);op=Path(s['output']);ins=verify(ip,s['input_sha256']);outs=verify(op,s['output_sha256'])
        require(outs['experiment']=='E101' and outs['stage']=='test' and outs['status']=='COMPLETE','COMPLETE production test2 only')
        require(outs['input_sha256']==s['input_sha256'] and outs['dose_sha256']==cfg['dose_sha256'],'output/input/frozen dose binding')
        require(doses['selected_doses'][s['row']+':44']['alpha']==4,'pre-test dev-selected dose')
        manifest=read(ip.parent/'MANIFEST.json');require(manifest['stage']=='test' and manifest['dose_commit']==cfg['dose_commit'] and manifest['dose_sha256']==cfg['dose_sha256'],'input committed dose')
        items=read(ip.parent/'items.json');validate_grid(items,s['row']);grid=read(op.parent/'JOB_GRID.json')
        require(sorted(read(op.parent/'COMPLETED.json'))==list(range(len(grid))),'all scheduled jobs complete')
        outputs={}
        for n,g in enumerate(grid):
            member=f'jobs/{n:06d}.json';require(member in outs['files'],'job hash bound')
            value=read(op.parent/member);require([x['id'] for x in value]==[items[i]['id'] for i in g['indices']],'job/item order')
            require(g['kind'] in ('logits','oracle'),'registered acquisition kinds')
            for x in value:
                key=x['id'],g['kind'];require(key not in outputs,'unique acquisition');outputs[key]=x
        require(len(outputs)==2*len(items),'logits and oracle complete')
        for x in items:
            t=targets[x['base_id']];require(t['split']=='test' and t['row']==s['row'],'CPU source target')
            r=outputs[x['id'],'oracle'];require(r['block']==44 and isinstance(r['text'],str),'native Oracle44 output')
            rows.append(dict(id=x['id'],item_id=x['base_id'],row=s['row'],reader='oracle',condition=x['condition'],alpha=4,text=r['text'],property=t['property'],values=t['values'],target=t['target']))
    require(len(rows)==336,'full two-cell test grid')
    # Reuse W-mech2's committed blind export and exact adapter402 wire renderer.
    from projects.g_agreement.understand.wmech2.core import export
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    digest=sha(HERE/'INPUTS.json');export(rows,CACHE/'blind',CACHE/'PRIVATE.json',digest,commit)
    route,(api,privacy,p,io)=funded.route_api();packet=read(CACHE/'blind/WIRE_PACKET.json');copied,audit=redact(packet,'E101',addresses=True)
    bound=sum((api.upper(channel_payload(copied[i:i+4],(CACHE/'blind/RUBRIC.md').read_text(),'E56',p)) for i in range(0,len(copied),4)),Decimal(0))
    require(bound<=CAP,'complete E101 initial pass fits5')
    a=dict(bank='E101',records=336,initial_requests=84,initial_upper_usd=str(bound),cap_usd='5',blind_seal_sha256=sha(CACHE/'blind/BLIND_SEAL.json'),source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),inputs_sha256=digest,redacted_records=audit['redacted_records'],scope=cfg['scope'],global_budget_basis='Existing CORE envelope includes E101 at USD6; this authorization reduces E101 to USD5; section212 amendment2 global ceiling USD1000',shared_credit_pause=str(funded.CACHE/'PAUSED_402.json'))
    write(CACHE/'ADMISSION.json',a);return a

def execute():
    source_gate();a=read(CACHE/'ADMISSION.json');require(a['source_seal_sha256']==sha(HERE/'SOURCE_SEAL.json') and a['inputs_sha256']==sha(HERE/'INPUTS.json'),'unchanged E101 admission')
    require(not (funded.CACHE/'PAUSED_402.json').exists(),'shared HTTP402 credit pause')
    verify(CACHE/'blind/BLIND_SEAL.json',a['blind_seal_sha256'])
    route,(api,privacy,p,io)=funded.route_api();api.CAP=CAP
    key=os.environ.get('OPENROUTER_API_KEY');require(bool(key),'credential unavailable')
    items,audit=redact(read(CACHE/'blind/WIRE_PACKET.json'),'E101',addresses=True);rubric=(CACHE/'blind/RUBRIC.md').read_text()
    saved=(p.payload,p.validate,privacy.check_wire,io.digest);ledger=CACHE/'ledger';ledger.mkdir(exist_ok=True)
    job=CACHE/'judgments';job.mkdir(exist_ok=True)
    with dispatch_lock(ledger/'DISPATCH.lock'):
        require(not (job/'JUDGMENT_SEAL.json').exists(),'already terminal')
        io.CACHE=ledger/'route';io.CACHE.mkdir(exist_ok=True)
        require(sha(route['privacy_proof'])==route['privacy_proof_sha256'],'account privacy proof')
        shutil.copyfile(route['privacy_proof'],io.CACHE/'OPENROUTER_PRIVACY_PROOF.json');routes=privacy.check_route(key)
        p.payload=lambda stage,batch,unused=None:channel_payload(batch,rubric,'E56',p)
        p.validate=lambda stage,response,batch,unused=None:classify(batch,response)
        privacy.check_wire=lambda stage,batch,wire,unused=None:check_decoded(saved[2],batch,wire)
        client=api.Client(ledger,key);book,done=client.ledger.totals();require(set(book)==done,'reconcile unresolved before resume')
        for x in items:privacy.check_wire('',[x],p.payload('',[x]))
        audits=[]
        def send(batch,attempt):
            require(not (funded.CACHE/'PAUSED_402.json').exists(),'shared HTTP402 credit pause')
            stage='E101_attempt'+str(attempt);prefix=stage+':'+a['blind_seal_sha256']+':'
            io.digest=lambda value:hashlib.sha256((prefix+value).encode()).hexdigest()
            result=client.one(stage,batch);rp=ledger/stage/(result['id']+'.response.json')
            require(rp.exists(),'transport/unresolved stop; no resend');response=read(rp)
            funded.credit_gate(response,rp,'E101',stage,result['id'])
            require(not client.latch.is_set(),'transport latch')
            v=response_audit(response,p);require(result['id'] in client.ledger.totals()[1],'actual charge settled')
            v.update(request_id=result['id'],response_sha256=sha(rp));audits.append(v)
            write(job/'LIVE_PROGRESS.json',dict(bank='E101',verified_requests=len(audits),cost=client.ledger.summary()))
            if result['status']=='OK':return result['value']
            try:json.loads(response['response']['choices'][0]['message']['content'])
            except (ValueError,TypeError):return classify(batch,{})
            raise RuntimeError('unexpected transport failure')
        write(CACHE/'STATUS.json',dict(status='RUNNING',bank='E101'))
        try:
            terminal=judge(items,send);flat,attempts=adapt_grid(terminal,items)
            write(job/'JUDGMENTS.json',flat);write(job/'TERMINAL.json',terminal);write(job/'ATTEMPTS.json',attempts)
            write(job/'JUDGE_COPY.json',items);write(job/'PATH_REDACTION_AUDIT.json',audit)
            write(job/'ROUTE_AUDIT.json',dict(routes=routes,requests=audits,privacy_proof_sha256=sha(route['privacy_proof']),inventory_sha256=sha(io.CACHE/'last_zdr_route_inventory.json')))
            write(job/'COUNTS.json',dict(records=336,unparseable=sum(x['category']=='UNPARSEABLE' for x in flat),cost=client.ledger.summary(),scope=a['scope']))
            write(job/'JUDGMENT_SEAL.json',dict(bank='E101',blind_seal_sha256=a['blind_seal_sha256'],route_verified=bool(routes) and bool(audits),redaction_audit_complete=True,redacted_opaque_ids=[x['id'] for x in audit['affected']],source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),files={f.name:sha(f) for f in job.iterdir() if f.is_file() and f.name!='JUDGMENT_SEAL.json'}))
            write(CACHE/'STATUS.json',dict(status='COMPLETE',bank='E101',cost=client.ledger.summary()))
        except Exception as exc:
            write(CACHE/'STATUS.json',dict(status='PAUSED_402' if isinstance(exc,funded.CreditPause) else 'BLOCKED',error_type=type(exc).__name__,bank='E101',cost=client.ledger.summary()));raise
        finally:p.payload,p.validate,privacy.check_wire,io.digest=saved

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','run']);args=parser.parse_args()
    if args.action=='prepare':print(json.dumps(prepare(),sort_keys=True))
    else:execute()
