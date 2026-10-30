"""Complete-only administrative bank seal; no scoring/statistics or paid calls."""
import argparse
from collections import Counter
from datetime import datetime, timezone
from .runner import CACHE
from .transport import ROOT,HERE,SHARED
from .accounting import bank_actual
from .seal_bank import disposition
from ..dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

SPECS={
 'E114':(2,[('original57_judging',504)]),
 'E112':(3,[('pca1_family_judging',840)]),
 'E85':(2,[('native_eval_judging',800),('native_eval_original',200)]),
 'E100e':(3,[('attempt2_value_judging',336),('attempt2_value_original',84)]),
 'E107':(15,[('generation',4297),('outside_judge_copy_judging',4496),('outside_judge_copy_original',1124)])}


def terminal_refs(rows,expected,source):
    require(len(rows)==expected and len({x['id']for x in rows})==expected,'complete unique frozen phase census')
    refs=[];missing=[]
    for i,x in enumerate(rows):
        require(x['status']in ('KEPT','UNPARSEABLE','REFUSED'),'known terminal judgment')
        require(x['code']is not None if x['status']=='KEPT'else x['code']is None,'exact terminal code/null')
        ref=dict(seal=source['seal'],sha256=source['sha256'],member='JUDGMENTS.json',keys=[i,'code'])
        row=dict(id=x['id'],kind=x['kind'],status=x['status'],original_code=ref)
        if x['status']!='KEPT' and x['kind']in ('value','old_value','original57'):
            row['missing_sentinel_index']=len(missing)
            missing.append(dict(id=x['id'],original_code=ref,terminal_status=x['status'],
                                code=dict(id=x['id'],category='UNPARSEABLE',values=[],evidence='')))
        refs.append(row)
    return refs,missing


def close(bank):
    for name,digest in read(HERE/'CLOSE226_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/name)==digest,'published complete-only closure source')
    cap,expected=SPECS[bank]
    with dispatch_lock(SHARED/bank/'DISPATCH.lock'):
        dest=CACHE/bank/'complete226';dest.mkdir(exist_ok=True);dest.chmod(0o700)
        phases=[];refs=[];missing=[]
        for phase,n in expected:
            out=CACHE/bank/phase/'outputs';path=out/('GENERATION_SEAL.json'if phase=='generation'else'JUDGMENT_SEAL.json')
            s=verify(path,sha(path));require(s['experiment']==bank and s['status']=='COMPLETE'and s['route_verified']is True,'all required complete approved-route phases')
            source=dict(phase=phase,n=n,seal=str(path),sha256=sha(path))
            if phase=='generation':require(len(read(out/'RESPONSES.json'))==n,'complete original generation')
            else:
                rows=read(out/'JUDGMENTS.json');rr,mm=terminal_refs(rows,n,source)
                for row in rr:
                    if'missing_sentinel_index'in row:row['missing_sentinel_index']+=len(missing)
                refs.extend(rr);missing.extend(mm);source['status_counts']=dict(Counter(x['status']for x in rows))
            phases.append(source)
        if bank=='E112':
            unit=CACHE/bank/'pca1_family_units/UNIT_SEAL.json';verify(unit,sha(unit));cpu=read(unit.parent/'CPU_REGEX_CODES.PRIVATE.json')
            require(len(cpu)==196 and len({x['id']for x in cpu})==196 and not({x['id']for x in cpu}&{x['id']for x in refs}),'original196 CPU regex records separate from840 API')
            refs.extend(dict(id=x['id'],kind=x['kind'],status=x['status'],original_code=dict(seal=str(unit),sha256=sha(unit),member='CPU_REGEX_CODES.PRIVATE.json',keys=[i,'code']))for i,x in enumerate(cpu))
        actual,unknown=bank_actual(SHARED/bank/'ledger');cost=disposition(cap,actual,unknown)
        allocation=SHARED/bank/'ALLOCATION_C.json';old=read(allocation);require(old['bank']==bank and old['allocation_usd']==str(cap),'same lifetime allocation')
        final=dest/'JUDGMENT_SEAL.json'
        if final.exists():
            verify(final,sha(final));require(read(dest/'BANK_COST.json')==cost,'no later cost/cap reset')
        else:
            require(old['status']=='OPEN','only close original actual open allocation')
            for name,value in [('ORIGINAL_ALLOCATION.PRIVATE.json',old),('BANK_COST.json',cost),('PHASES.json',phases),('TERMINAL_BINDINGS.PRIVATE.json',refs),('MISSING_SENTINELS.PRIVATE.json',missing)]:write(dest/name,value)
            write(final,dict(experiment=bank,status='COMPLETE_JUDGING_BANK',completed_utc=datetime.now(timezone.utc).isoformat(),route_verified=True,labels_cpu_only=True,
                analysis_run=False,source_manifest_sha256=sha(HERE/'CLOSE226_SOURCE_SEAL.json'),source_seals=phases,
                files={p.name:sha(p)for p in dest.iterdir()if p.is_file()}))
        if old['status']=='RELEASED':require(old['completion_seal_sha256']==sha(final),'same once-only release')
        else:write(allocation,dict(old,status='RELEASED',completion_seal=str(final),completion_seal_sha256=sha(final),final_actual_usd=str(actual),unused_allocation_released_usd=cost['unused_allocation_released_usd']))
        write(SHARED/bank/'BANK_COMPLETE_C.json',dict(bank=bank,status='COMPLETE',seal=str(final),sha256=sha(final),**cost))
        return final


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bank',choices=sorted(SPECS),required=True);a=p.parse_args();path=close(a.bank);print('Closed '+a.bank+' '+sha(path))
