"""Stop only own queued C worker on a saved response with unknown cost.

No requests, retries, settlements, response reclassification or automatic resume.
"""
import argparse,fcntl,json,os,signal,subprocess,time
from decimal import Decimal,InvalidOperation
from pathlib import Path
from .transport import ROOT,HERE,SHARED
from .runner import CACHE
from projects.g_agreement.readerbench.io import read,write,sha
from projects.g_agreement.readerbench.scoring import require


def known_cost(response):
    body=response.get('response')
    usage=body.get('usage') if isinstance(body,dict) else None
    v=usage.get('cost') if isinstance(usage,dict) else None
    if v is None or type(v) is bool:return False
    try:return Decimal(str(v)).is_finite() and Decimal(str(v))>=0
    except InvalidOperation:return False


def saved_unknown(root,bank):
    ledger=root/'ledger.jsonl'
    if not ledger.exists():return []
    with ledger.open('rb') as f:
        fcntl.flock(f,fcntl.LOCK_SH);rows=[json.loads(x) for x in f.read().splitlines() if x.strip()];fcntl.flock(f,fcntl.LOCK_UN)
    done={r['id'] for r in rows if r['event']=='settle'};out=[]
    for r in rows:
        if r['event']!='reserve' or r['id'] in done:continue
        p=root/(bank+'_judging')/(r['id']+'.response.json')
        if not p.exists():continue  # In-flight request is never interrupted.
        v=read(p)
        if not known_cost(v):out.append(dict(request_id=r['id'],unresolved_upper_usd=str(r['usd']),response=str(p),response_sha256=sha(p),http_status=v.get('http_status')))
    return out


def run(home):
    source=HERE/'UNKNOWN_COST_GUARD_SOURCE_SEAL.json'
    for n,h in read(source)['files'].items():require(sha(ROOT/n)==h,'published administrative financial guard')
    home.mkdir(exist_ok=True);holds={}
    while time.time()<1793372400:
        for bank in ('E127','E123','E120','E117','E118','E124'):
            destination=CACHE/bank/'UNKNOWN_COST_HOLD.PRIVATE.json'
            if destination.exists():holds[bank]=str(destination);continue
            evidence=saved_unknown(SHARED/bank/'ledger',bank)
            if not evidence:continue
            with (SHARED/'THROUGHPUT.lock').open('a') as f:
                fcntl.flock(f,fcntl.LOCK_EX);q=read(SHARED/'THROUGHPUT.json')
                entries=[x for x in q.get('waiting',[]) if x['bank']==bank]
                if not entries:continue
                pid=entries[0]['pid'];cmd=subprocess.run(['ps','-p',str(pid),'-o','args='],capture_output=True,text=True).stdout
                if '-m projects.g_agreement.understand.blind_judge.internals_c.' not in cmd or ('--phase-directory cache/g_agreement/understand/internals_c/'+bank+'/') not in cmd:continue
                evidence=saved_unknown(SHARED/bank/'ledger',bank)
                if not evidence:continue
                os.kill(pid,signal.SIGSTOP);q['waiting']=[x for x in q['waiting'] if x not in entries];write(SHARED/'THROUGHPUT.json',q)
                plan=CACHE/'priority_b724/PLAN.json';p=read(plan);removed=[x for x in p['ordered_existing_phases'] if x['bank']==bank];p['ordered_existing_phases']=[x for x in p['ordered_existing_phases'] if x['bank']!=bank];write(plan,p)
                record=dict(bank=bank,status='HELD_SAVED_RESPONSE_UNKNOWN_COST',pid=pid,unresolved=evidence,paused_at_unreserved_fifo_boundary=True,removed_priority_plan_entry=removed,ledger_changed=False,response_or_request_replayed=False,coordinator_charge_reconciliation_required=True,at_epoch=time.time())
                write(destination,record);holds[bank]=str(destination)
                public=ROOT/'results/g_agreement/understand'/bank.lower()/'C_UNKNOWN_COST_GUARD_HOLD.json';public.parent.mkdir(exist_ok=True)
                write(public,dict(bank=bank,status=record['status'],evidence=str(destination),saved_response_hashes=[x['response_sha256'] for x in evidence],unresolved_reserved_upper_usd=str(sum((Decimal(x['unresolved_upper_usd']) for x in evidence),Decimal(0))),ledger_changed=False,request_resent=False))
                entry='\n\nC unknown-cost guard HELD '+bank+' queued before reservation; saved response(s) lack reported cost. No ledgerwrite/guess0/resend/in-flight interruption. Exact evidence '+str(destination)+'; coordinator authoritative charge reconciliation required BEFORE sameprocess resume. Public '+str(public.relative_to(ROOT))+'.\n'
                for target in (HERE/'HANDOFF.md',ROOT/'results/g_agreement/r/HANDOFF.md'):
                    with target.open('a') as h:h.write(entry)
                fcntl.flock(f,fcntl.LOCK_UN)
        write(home/'STATUS.json',dict(status='MONITORING',pid=os.getpid(),holds=holds,at_epoch=time.time(),no_api_or_settlement=True))
        time.sleep(.5)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--home',type=Path,required=True);run(p.parse_args().home)
