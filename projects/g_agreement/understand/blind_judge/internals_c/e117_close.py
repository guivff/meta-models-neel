"""Close original shared E117 only after BOTH full phases and no unknown cost."""
import argparse
from .transport import ROOT,HERE,SHARED
from .runner import CACHE
from .accounting import bank_actual
from .seal_bank import disposition
from ..dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def phases(root):
    out=[]
    for phase,n in [('targeted_sham_judging',672),('native_judging',3024)]:
        p=root/phase/'outputs/JUDGMENT_SEAL.json';s=verify(p,sha(p));r=read(p.parent/'JUDGMENTS.json')
        require(s['experiment']=='E117' and s['status']=='COMPLETE' and s['route_verified'] is True and len(r)==len({x['id'] for x in r})==n,'both COMPLETE full phases before release')
        out.append(dict(phase=phase,n=n,seal=str(p),sha256=sha(p)))
    return out


def close():
    for n,h in read(HERE/'E117_ADMIN_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'published administrative closure source')
    ps=phases(CACHE/'E117')
    with dispatch_lock(SHARED/'E117/DISPATCH.lock'):
        actual,unknown=bank_actual(SHARED/'E117/ledger');cost=disposition(4,actual,unknown)
        a=SHARED/'E117/ALLOCATION_C.json';old=read(a);require(old['bank']=='E117' and old['allocation_usd']=='4','same original cumulative operational allocation, no reset')
        d=CACHE/'E117/complete';d.mkdir(exist_ok=True);final=d/'JUDGMENT_SEAL.json'
        if final.exists():verify(final,sha(final));require(read(d/'BANK_COST.json')==cost,'no new charges after closure')
        else:
            require(old['status']=='OPEN','original open allowance only')
            write(d/'BANK_COST.json',cost);write(d/'ORIGINAL_ALLOCATION.PRIVATE.json',old);write(d/'PHASES.json',ps)
            write(final,dict(experiment='E117',status='COMPLETE_JUDGING_BANK',n=3696,operational_combined_lifetime_cap_usd='4',registered_combined_maximum_usd='6',extra_allowance_allocated=False,route_verified=True,labels_cpu_only=True,analysis_run=False,source_seals=ps,files={n:sha(d/n) for n in ['BANK_COST.json','ORIGINAL_ALLOCATION.PRIVATE.json','PHASES.json']}))
        if old['status']=='RELEASED':require(old['completion_seal_sha256']==sha(final),'same once-only release')
        else:write(a,dict(old,status='RELEASED',completion_seal=str(final),completion_seal_sha256=sha(final),final_actual_usd=str(actual),unused_allocation_released_usd=cost['unused_allocation_released_usd']))
        write(SHARED/'E117/BANK_COMPLETE_C.json',dict(bank='E117',status='COMPLETE',seal=str(final),sha256=sha(final),**cost))
        return final


if __name__=='__main__':
    argparse.ArgumentParser().parse_args();print('E117 complete shared bank '+sha(close()))
