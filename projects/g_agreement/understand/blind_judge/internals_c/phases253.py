"""New E136R/E138 blinded phases; original banks/source/guards remain immutable."""
import argparse,os,time,subprocess,json
from pathlib import Path
from decimal import Decimal
from contextlib import contextmanager
from collections import Counter
from . import transport,resume_e340 as bounds,registered
from .runner import CACHE,seal_phase,preflight
from .backend248 import BackendTransport
from .accounting253 import snapshot
from .banks import opaque
from .e136r_judge253 import readout_call,assert_readout_only
from .e138_judge253 import value_call138,assert_value_allowlist
from ..privacy79 import redact
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
N={'E136R':400,'E138':168};PHASE={'E136R':'readout_only_judging253','E138':'value_judging253'}

def render(bank,unit,p=None):return readout_call(unit,p)if bank=='E136R'else value_call138(unit,p)

def source_gate(bank):
    p=transport.HERE/(bank+'_SOURCE253.json');s=read(p)
    for n,h in s['files'].items():require(sha(transport.ROOT/n)==h,'prospective new phase source')
    for n,h in s.get('owner_frozen_files',{}).items():require(sha(n)==h,'frozen tested owner source copy')
    return p

@contextmanager
def worker(bank):
    source_gate(bank);old=transport.CAPS.get(bank);expiry=transport.EXPIRY;transport.CAPS[bank]=Decimal(1);bounds.CAPS[bank]=Decimal(1);transport.EXPIRY=1793372400
    try:yield
    finally:
        transport.EXPIRY=expiry
        if old is None:transport.CAPS.pop(bank,None)
        else:transport.CAPS[bank]=old


def r_units():
    u=CACHE/'E136/native_units250/UNIT_SEAL.json';s=verify(u,'8df559faf25a338b0c30ff9e53e3e9a03df3c5c03fdd316d0c8272004373c501');old=read(u.parent/'UNITS.json');ptr={x['id']:x for x in read(u.parent/'SOURCE_POINTERS.PRIVATE.json')};units=[];joins=[]
    for x in old:
        j=ptr[x['id']];uid=opaque('E136R',j['native_id']);units.append(dict(id=uid,readout=x['readout'],cue=j['cue']));joins.append(dict(j,id=uid,original_E136_unit_id=x['id']))
    require(len(units)==len({x['id']for x in units})==400,'same exact original400 readouts')
    return units,joins,[dict(seal=str(u),sha256=sha(u))]+s['source_seals']


def v_units():
    native=transport.ROOT.parent/'wt-i2/cache/g_agreement/i2/parallel_gpu230/e138-dev1/terminal_pull/outputs';np=native/'OUTPUT_SEAL.json';ns=verify(np,'c132b3c0500c67d27571f20c44790c899dfb0f71fc8f79f2ce73c773acd8e107');require(ns['experiment']=='E138'and ns['status']=='COMPLETE','full new measured native; excluded a1 neverused')
    ip=transport.ROOT.parent/'outputs/e138-inputs-v1/inputs/INPUT_SEAL.json';verify(ip,'71e04529a3b76ea812f1bfafb4256cf8f22572f64af745de0c333e98b56ec01b');cp=ip.parent.parent/'cpu_only/CPU_SEAL.json';verify(cp,'645a94a5ff48ad3671006a471f863c4a9b1e37ec089894f8c23b76c2af895267');require(ns['input_sha256']==sha(ip),'same exact original168 source cells')
    ptr={x['id']:x for x in read(cp.parent/'POINTERS.PRIVATE.json')};items={x['id']:x for x in read(ip.parent/'items.json')};require(len(ptr)==len(items)==168 and set(ptr)==set(items),'all168 literal opaque source IDs')
    ps=transport.SHARED/'E104/PRIVATE_SEAL.json';verify(ps,'0f42d78d151a85b858f2b02a13307e62e74f987ad0bba009cab875b6792aa3c6');original={x['item_id']:x for x in read(ps.parent/'PRIVATE.json')if x['arm']=='U'and x['row']=='fact_recall'and x['reader']=='oracle'and x['condition']=='steered'and x['flipped']is True};require(len(original)==84,'original whole84')
    units=[];joins=[];seen=set()
    for m in ns['files']:
        if not(m.startswith('jobs/')and m.endswith('.json')):continue
        for i,r in enumerate(read(native/m)):
            require(r['item_id']in ptr and r['id']==r['item_id']+':oracle:44'and r['reader']=='oracle'and r['source_layer']==44 and type(r['text'])is str,'literal original readout ID/block/text')
            p=ptr[r['item_id']];o=original[p['original_E104_base_id']];recipient='B'if o['target']=='A'else'A';donor=o['target'];require(p['recipient_old']in o['values'][recipient]and p['recipient_old']!=p['donor_old']and p['condition']in('b','c'),'frozen original candidate orientation and source role map')
            key=p['original_E104_base_id'],p['condition'];require(key not in seen,'unique original source cell');seen.add(key);uid=opaque('E138',r['id']);values={recipient:list(o['values'][recipient]),donor:[p['donor_old']]};values={k:values[k]for k in('A','B')}
            units.append(dict(id=uid,property=o['property'],values=values,readout=r['text']))
            joins.append(dict(p,id=uid,native_id=r['id'],item_id=r['item_id'],layer=44,recipient_letter=recipient,donor_letter=donor,other_letter='OTHER',source_ref=dict(seal=str(np),sha256=sha(np),member=m,keys=[i,'text'])))
    require(seen=={(i,c)for i in original for c in('b','c')}and len(units)==168,'whole84x2/no stitching or fill')
    return units,joins,[dict(seal=str(p),sha256=sha(p))for p in(np,ip,cp,ps)]


def prepare(bank):
    source=source_gate(bank);units,joins,sources=r_units()if bank=='E136R'else v_units();_,(_,_,protocol,_)=registered.funded.route_api();plans=[];calls=[]
    for u in units:
        original,_=render(bank,u,protocol)
        if bank=='E136R':assert_readout_only(original,u)
        else:assert_value_allowlist(original,u,'E138')
        ids=[]
        for attempt in range(3):
            c=dict(original,id=opaque(bank,'judging',u['id'],str(attempt)));calls.append(c);ids.append(c['id'])
        plans.append(dict(unit=u,calls=ids))
    _,audit=redact([dict(id=u['id'],readout=u['readout'])for u in units],bank,addresses=True);require(audit['redacted_records']==0,'additional privacy copies require source companion')
    d=CACHE/bank/PHASE[bank];require(not(d/'INPUT_SEAL.json').exists(),'new phase prepareonce')
    d=seal_phase(bank,PHASE[bank],calls,dict(n=N[bank],max_schema_retries=2,bank_source_sha256=sha(source),raw_git_export=False,source_prompt_on_wire=False),sources)
    for name,value in [('VALIDATION.json',plans),('SOURCE_POINTERS.PRIVATE.json',joins),('PATH_REDACTION_AUDIT.json',audit)]:write(d/name,value)
    s=read(d/'INPUT_SEAL.json');s['files'].update({n:sha(d/n)for n in['VALIDATION.json','SOURCE_POINTERS.PRIVATE.json','PATH_REDACTION_AUDIT.json']});write(d/'INPUT_SEAL.json',s)
    with worker(bank):preflight(d)
    if bank=='E136R':
        sample=read(CACHE/'E136R/pre_dispatch_sample253/WIRE.PRIVATE.json');require(any(transport.frozen_wire(c,protocol)==sample for c in calls),'R2 sample is an exact actual frozen phase request')
    return d


def check_r2(a,d):
    require(a.get('R2_sample_checked')is True,'required actual R2 sample check before dispatch')
    ref=a['R2_sample_review_source'];raw=subprocess.check_output(['git','show',ref['commit']+':'+ref['path']],cwd=transport.ROOT);import hashlib
    require(hashlib.sha256(raw).hexdigest()==ref['sha256'],'exact committed reviewer source')
    sample=sha(CACHE/'E136R/pre_dispatch_sample253/WIRE.PRIVATE.json');require(a['R2_sample_wire_sha256']==sample and sample.encode()in raw,'review binds exact frozen actual wire')


def run(d):
    bank=read(d/'INPUT_SEAL.json')['experiment'];require(bank in N,'registered new phase');source=source_gate(bank);a=read(d/'ADMISSION.json');pub=read(d/'PUBLICATION.json');p=Path(pub['allocation_path']);live=read(d/'LIVE_PROOF.PRIVATE.json')
    require(a['bank']==bank and a['allocation_usd']=='1'and a['bank_source_sha256']==sha(source)and a['input_sha256']==sha(d/'INPUT_SEAL.json'),'same registered source/cap1')
    require(sha(p)==pub['allocation_sha256']==sha(d/'ADMISSION.json')and subprocess.check_output(['git','show',pub['commit']+':'+str(p.relative_to(transport.ROOT))],cwd=transport.ROOT)==p.read_bytes(),'exact admission published before calls')
    require(sha(d/'LIVE_PROOF.PRIVATE.json')==a['live_route_funding_proof_sha256']and 0<=time.time()-live['at_epoch']<300 and all(live[k]is True for k in['route_verified','account_privacy_verified','funded_remaining_bank_cap']),'fresh authenticated proof')
    verify(d/'INPUT_SEAL.json',sha(d/'INPUT_SEAL.json'));plans=read(d/'VALIDATION.json');allowed={x['id']:x for x in read(d/'CALLS.json')};require(len(plans)==N[bank]and len(allowed)==3*N[bank],'full first/retry inventory')
    for plan in plans:
        expected,_=render(bank,plan['unit']);require(all(allowed[cid]['rendered']==expected['rendered']for cid in plan['calls']),'roundtripped actual frozen wires')
    if bank=='E136R':check_r2(a,d)
    with worker(bank):g=snapshot();require(bank in g['open_banks'],'actual registered OPEN allocation');write(d/'DISPATCH_GLOBAL_PROOF.PRIVATE.json',g)
    fd=os.open(d/'JUDGING_ONCE.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd);write(d/'JUDGING_ONCE.json',dict(pid=os.getpid(),source_sha256=sha(source)));job=d/'outputs';job.mkdir(exist_ok=True)
    with worker(bank):
        try:
            with BackendTransport(d/'INPUT_SEAL.json',sha(d/'INPUT_SEAL.json'),a,os.environ['OPENROUTER_API_KEY'],zero_limit=2)as channel:
                rows=[];attempts=[];audits=[]
                for plan in plans:
                    expected,validator=render(bank,plan['unit'],channel.protocol)
                    for attempt,cid in enumerate(plan['calls']):
                        require(channel.allowed[cid]['rendered']==expected['rendered'],'literal rubric/payload');t,audit=channel.call(cid,validator);attempts.append(dict(t,unit_id=plan['unit']['id'],attempt=attempt));audits.append(audit)
                        if t['status']=='KEPT'or t.get('reason')in('CHARGED_LENGTH','RATE_LIMIT_EXHAUSTED','UNCHARGED_BACKEND_RETRIES_EXHAUSTED'):break
                    code=(t['result']if bank=='E136R'else t['result']['records'][0])if t['status']=='KEPT'else None;status=t['status']
                    if bank=='E136R':status='KEPT'if code and code['code']in('YES','NO')else'UNPARSEABLE'
                    row=dict(id=plan['unit']['id'],kind=bank,status=status,code=code,request_id=t['request_id'],response_sha256=t['response_sha256'],attempts=attempt)
                    if bank=='E136R':row['judgment']=code['code']if code else'UNPARSEABLE'
                    rows.append(row);write(job/'PROGRESS.json',dict(at_epoch=time.time(),completed=len(rows),n=N[bank],cost=channel.summary()))
                for name,value in [('JUDGMENTS.json',rows),('ATTEMPTS.json',attempts),('ROUTE_AUDIT.json',dict(routes=channel.routes,requests=audits)),('RAW_RESPONSE_BINDINGS.json',channel.physical),('COUNTS.json',dict(n=N[bank],status_counts=dict(Counter(r['status']for r in rows)),cost=channel.summary())),('PATH_REDACTION_AUDIT.json',read(d/'PATH_REDACTION_AUDIT.json'))]:write(job/name,value)
                from datetime import datetime,timezone
                first=min(Path(x['path']).stat().st_mtime for x in channel.physical);write(job/'JUDGMENT_SEAL.json',dict(experiment=bank,phase=PHASE[bank],status='COMPLETE',first_output_utc=datetime.fromtimestamp(first,timezone.utc).isoformat(),input_sha256=sha(d/'INPUT_SEAL.json'),source_sha256=sha(source),route_verified=True,labels_cpu_only=True,raw_git_export=False,source_prompt_on_wire=False,files={p.name:sha(p)for p in job.iterdir()if p.is_file()}))
        except BaseException as exc:write(job/'STOPPED253.json',dict(error_type=type(exc).__name__,at_epoch=time.time(),no_resend=True));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);p.add_argument('--bank',choices=list(N));p.add_argument('--phase-directory',type=Path);a=p.parse_args();print(prepare(a.bank))if a.action=='prepare'else run(a.phase_directory)
