"""E136 administrative full-bank close and literal code binding; raw stays local."""
from decimal import Decimal
from .runner import CACHE
from .transport import ROOT,HERE,SHARED
from .accounting import bank_actual
from .seal_bank import disposition
from ..dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def pointers(joins,rows,phase,n=400):
    by={r['id']:(i,r)for i,r in enumerate(rows)}
    require(len(joins)==len(rows)==len(by)==n and len({j['native_id']for j in joins})==n and {j['id']for j in joins}==set(by),'all original native IDs exactly once')
    result={}
    for j in joins:
        i,r=by[j['id']];code=r['code'];require(r['kind']=='cue136' and r['judgment']in('YES','NO','UNPARSEABLE'),'registered exact codes')
        require((r['status']=='KEPT')==(r['judgment']in('YES','NO')),'missing never scored NO')
        require((code is None and r['judgment']=='UNPARSEABLE')or(type(code)is dict and code['code']==r['judgment']),'literal original code/null preserved')
        ref=dict(seal=str(phase),sha256=sha(phase)if isinstance(phase,type(CACHE))and phase.exists()else'test',member='JUDGMENTS.json')
        result[j['native_id']]=dict(j,judgment_id=j['id'],status=r['status'],code_source=dict(ref,keys=[i,'code']),judgment_source=dict(ref,keys=[i,'judgment']),request_id=r['request_id'],response_sha256=r['response_sha256'])
    return result


def close():
    for n,h in read(HERE/'E136_CLOSE251_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'frozen tested CPU close source')
    d=CACHE/'E136/cue_judging250';p=d/'outputs/JUDGMENT_SEAL.json';s=verify(p,sha(p));require(s['status']=='COMPLETE'and s['experiment']=='E136'and s['raw_git_export']is False,'complete original400 only')
    verify(d/'INPUT_SEAL.json','185798d935a6b652122c47f41b8fdf53adceeb6750d7b822cab15c681be5461a');refs=pointers(read(d/'SOURCE_POINTERS.PRIVATE.json'),read(p.parent/'JUDGMENTS.json'),p)
    with dispatch_lock(SHARED/'E136/DISPATCH.lock'):
        actual,unknown=bank_actual(SHARED/'E136/ledger');cost=disposition(1,actual,unknown);a=SHARED/'E136/ALLOCATION_C.json';old=read(a);require(old['bank']=='E136'and Decimal(old['allocation_usd'])==1,'same original1')
        out=CACHE/'E136/complete251';out.mkdir(exist_ok=True);final=out/'JUDGMENT_SEAL.json'
        if final.exists():verify(final,sha(final));require(read(out/'BANK_COST.json')==cost,'no later cost/reclose')
        else:
            require(old['status']=='OPEN','original OPEN allocation only');write(out/'READOUT_CODE_BINDINGS.PRIVATE.json',refs);write(out/'BANK_COST.json',cost);write(out/'ORIGINAL_ALLOCATION.PRIVATE.json',old)
            write(final,dict(experiment='E136',status='COMPLETE_JUDGING_BANK',n=400,route_verified=True,labels_cpu_only=True,analysis_run=False,raw_git_export=False,source_seals=[dict(seal=str(p),sha256=sha(p))],files={n:sha(out/n)for n in['READOUT_CODE_BINDINGS.PRIVATE.json','BANK_COST.json','ORIGINAL_ALLOCATION.PRIVATE.json']}))
        if old['status']=='RELEASED':require(old['completion_seal_sha256']==sha(final),'same once-only release')
        else:write(a,dict(old,status='RELEASED',completion_seal=str(final),completion_seal_sha256=sha(final),final_actual_usd=str(actual),unused_allocation_released_usd=cost['unused_allocation_released_usd']))
        write(SHARED/'E136/BANK_COMPLETE_C.json',dict(bank='E136',status='COMPLETE',seal=str(final),sha256=sha(final),**cost));return final
