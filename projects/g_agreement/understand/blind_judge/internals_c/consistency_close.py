"""Administrative E118 combined/E124 bank closure; no scoring or guard calls."""
import argparse
from .transport import HERE,ROOT,SHARED
from .runner import CACHE
from .accounting import bank_actual
from .seal_bank import disposition
from ..dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def terminal_refs(rows,seal,digest,n):
    require(len(rows)==len({r['id'] for r in rows})==n,'complete unique registered terminal census')
    refs=[]
    for i,r in enumerate(rows):
        require(r['status'] in ('KEPT','UNPARSEABLE','REFUSED') and (r['result'] is None)==(r['status']!='KEPT'),'original status/result missingness unchanged')
        refs.append(dict(id=r['id'],status=r['status'],terminal=dict(seal=str(seal),sha256=digest,member='RESPONSES.json',keys=[i])))
    return refs


def close(bank):
    require(bank in ('E118','E124'),'explicit registered consistency banks')
    for n,h in read(HERE/'CONSISTENCY_CLOSE_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'published administrative close source')
    phase='belief_wrong_consistency_judging' if bank=='E118' else 'model_reference_consistency_judging'
    p=CACHE/bank/phase/'outputs/JUDGMENT_SEAL.json';s=verify(p,sha(p));n=6790 if bank=='E118' else 6424;cap=1 if bank=='E118' else 3
    require(s['status']=='COMPLETE' and s['experiment']==bank and s['route_verified'] is True,'complete approved-route phase')
    refs=terminal_refs(read(p.parent/'RESPONSES.json'),p,sha(p),n)
    prior=None
    if bank=='E118':
        prior=CACHE/'E118/complete/JUDGMENT_SEAL.json';verify(prior,'1780b3a7c66c613259614b9c27781393610d958c80b1ccb5f5e01f0ce85e1070')
        require(read(SHARED/'E118/CONTINUATION_PART_B_C.json')['prior_actual_usd']=='0.02705700','original a actual retained')
    with dispatch_lock(SHARED/bank/'DISPATCH.lock'):
        actual,unknown=bank_actual(SHARED/bank/'ledger');cost=disposition(cap,actual,unknown);ap=SHARED/bank/'ALLOCATION_C.json';a=read(ap)
        require(a['bank']==bank and str(a['allocation_usd'])==str(cap),'same original lifetime cap')
        d=CACHE/bank/('combined_complete' if bank=='E118' else 'complete');d.mkdir(exist_ok=True);final=d/'JUDGMENT_SEAL.json'
        if final.exists():
            verify(final,sha(final));require(read(d/'BANK_COST.json')==cost,'same once-only final cost')
        else:
            require(a['status']=='OPEN','only original open allowance can release')
            write(d/'TERMINAL_BINDINGS.PRIVATE.json',refs);write(d/'BANK_COST.json',cost);write(d/'ORIGINAL_OPEN_ALLOCATION.PRIVATE.json',a)
            members=['TERMINAL_BINDINGS.PRIVATE.json','BANK_COST.json','ORIGINAL_OPEN_ALLOCATION.PRIVATE.json']
            if bank=='E118':
                write(d/'CAP_SETTLEMENT.json',dict(bank='E118',lifetime_USD=1,prior_actual_USD=.027057,total_actual_USD=float(actual),unknown_USD=0,judgment_sha256=sha(p),exact_total_actual_usd=str(actual),original_part_a_seal_sha256=sha(prior),original_part_a_not_overwritten=True));members.append('CAP_SETTLEMENT.json')
            write(final,dict(experiment=bank,status='COMPLETE_JUDGING_BANK',n=n+(252 if prior else 0),new_phase_judgments=n,route_verified=True,labels_cpu_only=True,phase_seal=str(p),phase_sha256=sha(p),prior_part_a_sha256=sha(prior) if prior else None,files={x:sha(d/x) for x in members}))
        if a['status']=='RELEASED':require(a['completion_seal_sha256']==sha(final),'same once-only unused release')
        else:write(ap,dict(a,status='RELEASED',completion_seal=str(final),completion_seal_sha256=sha(final),final_actual_usd=str(actual),unused_allocation_released_usd=cost['unused_allocation_released_usd']))
        # Original part-a completion marker/history stays intact.
        write(SHARED/bank/('BANK_COMBINED_COMPLETE_C.json' if prior else 'BANK_COMPLETE_C.json'),dict(bank=bank,status='COMPLETE',seal=str(final),sha256=sha(final),**cost))
        return final


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bank',choices=['E118','E124'],required=True);print('Consistency bank closed '+sha(close(p.parse_args().bank)))
