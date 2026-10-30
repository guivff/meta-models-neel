"""CPU-only full registered-bank closure and literal native/code pointer custody."""
from decimal import Decimal
from .runner import CACHE
from .transport import ROOT,HERE,SHARED
from .e138r_channel254 import N,PHASE
from .accounting import bank_actual
from .seal_bank import disposition
from ..dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

def pointers(bank,joins,rows,phase,n):
    by={r['id']:(i,r)for i,r in enumerate(rows)};require(len(by)==len(rows)==len(joins)==n and len({j['native_id']for j in joins})==n and set(by)=={j['id']for j in joins},'full unique native/opaque ID join')
    out={}
    for j in joins:
        i,r=by[j['id']];require(r['kind']==bank,'exact registered new bank kind');code=r['code']
        if bank=='E138R':require((code is None)==(r['status']!='KEPT')and(code is None or code['id']==j['id']),'literal original E104 code/null/ID')
        else:require((r['status']=='KEPT')==(r['judgment']in('YES','NO'))and((code is None and r['judgment']=='UNPARSEABLE')or code['code']==r['judgment']),'missing never NO')
        ref=dict(seal=str(phase),sha256=sha(phase)if hasattr(phase,'exists')else'test',member='JUDGMENTS.json')
        x=dict(j,judgment_id=j['id'],status=r['status'],code_source=dict(ref,keys=[i,'code']),request_id=r['request_id'],response_sha256=r['response_sha256'])
        if bank=='E136R':x['judgment_source']=dict(ref,keys=[i,'judgment'])
        out[j['native_id']]=x
    return out

def close(bank):
    require(bank in N,'registered new bank')
    for n,h in read(HERE/'E138R_CLOSE254_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'frozen administrative close source')
    d=CACHE/bank/PHASE[bank];jp=d/'outputs/JUDGMENT_SEAL.json';s=verify(jp,sha(jp));require(s['experiment']==bank and s['status']=='COMPLETE'and s['source_prompt_on_wire']is False and s['raw_git_export']is False,'complete audited phase only');verify(d/'INPUT_SEAL.json',sha(d/'INPUT_SEAL.json'));refs=pointers(bank,read(d/'SOURCE_POINTERS.PRIVATE.json'),read(jp.parent/'JUDGMENTS.json'),jp,N[bank])
    with dispatch_lock(SHARED/bank/'DISPATCH.lock'):
        actual,unknown=bank_actual(SHARED/bank/'ledger');cost=disposition(1,actual,unknown);p=SHARED/bank/'ALLOCATION_C.json';a=read(p);require(a['bank']==bank and Decimal(a['allocation_usd'])==1,'original exactcap1')
        out=CACHE/bank/'complete254';out.mkdir(exist_ok=True);final=out/'JUDGMENT_SEAL.json'
        if final.exists():verify(final,sha(final));require(read(out/'BANK_COST.json')==cost,'no latercost/reclose')
        else:
            require(a['status']=='OPEN','original allocation open');write(out/'READOUT_CODE_BINDINGS.PRIVATE.json',refs);write(out/'BANK_COST.json',cost);write(out/'ORIGINAL_ALLOCATION.PRIVATE.json',a);write(final,dict(experiment=bank,status='COMPLETE_JUDGING_BANK',n=N[bank],route_verified=True,labels_cpu_only=True,analysis_run=False,raw_git_export=False,source_prompt_on_wire=False,source_seals=[dict(seal=str(jp),sha256=sha(jp))],files={n:sha(out/n)for n in['READOUT_CODE_BINDINGS.PRIVATE.json','BANK_COST.json','ORIGINAL_ALLOCATION.PRIVATE.json']}))
        if a['status']=='RELEASED':require(a['completion_seal_sha256']==sha(final),'same once-only release')
        else:write(p,dict(a,status='RELEASED',completion_seal=str(final),completion_seal_sha256=sha(final),final_actual_usd=str(actual),unused_allocation_released_usd=cost['unused_allocation_released_usd']))
        write(SHARED/bank/'BANK_COMPLETE_C.json',dict(bank=bank,status='COMPLETE',seal=str(final),sha256=sha(final),**cost));return final
