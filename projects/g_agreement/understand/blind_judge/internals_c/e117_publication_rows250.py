"""CPU custody repair for E117's misplaced, already-emitted final row file.
No response decoding, scoring, paid calls, or changes to the original output seal.
"""
from collections import defaultdict
from pathlib import Path
from .runner import CACHE
from .transport import ROOT,HERE,SHARED
from .e117_binding import project
from .e117_close import close as original_close
from .accounting import bank_actual
from .seal_bank import disposition
from ..dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def validate_rows(rows,attempts,plans,n=3024):
    require(len(rows)==len(plans)==n and len({r['id'] for r in rows})==n,'full unique emitted row census')
    by=defaultdict(list)
    for t in attempts:by[t['unit_id']].append(t)
    require(set(by)=={p['unit']['id']for p in plans}=={r['id']for r in rows},'exact original unit IDs')
    for row,plan in zip(rows,plans):
        require(row['id']==plan['unit']['id'] and row['kind']==plan['unit']['kind']=='original57','literal emitted original plan order')
        ts=by[row['id']]
        require([t['id']for t in ts]==plan['calls'][:len(ts)] and [t['attempt']for t in ts]==list(range(len(ts))),'original physical/schema attempts')
        t=ts[-1]
        require(row['status']==t['status'] and row['request_id']==t['request_id'] and row['response_sha256']==t['response_sha256'] and row['attempts']==len(ts)-1,'sealed final-attempt identity')
        require(row['status']in('KEPT','UNPARSEABLE','REFUSED'),'terminal status only')
        code=t['result']['records'][0] if t['status']=='KEPT' else None
        require(row['code']==code and (code is None or code['id']==row['id']),'literal sealed code/null; never reparse')
    return rows


def custody():
    s=read(HERE/'E117_ROWS250_SOURCE_SEAL.json')
    for name,h in s['files'].items():require(sha(ROOT/name)==h,'published CPU repair source')
    phase=CACHE/'E117/native_judging';p=phase/'outputs/JUDGMENT_SEAL.json';seal=verify(p,sha(p))
    require(seal['status']=='COMPLETE' and seal['experiment']=='E117' and seal['route_verified']is True,'actual complete original main')
    require('JUDGMENTS.json'not in seal['files'] and not(p.parent/'JUDGMENTS.json').exists(),'only registered misplaced-output repair')
    raw=ROOT/'JUDGMENTS.json';rows=validate_rows(read(raw),read(p.parent/'ATTEMPTS.json'),read(phase/'VALIDATION.json'))
    d=CACHE/'E117/main_rows_custody250';d.mkdir(exist_ok=True);d.chmod(0o700)
    final=d/'ROW_CUSTODY_SEAL.json'
    if final.exists():
        v=verify(final,sha(final));require(v['original_phase_seal_sha256']==sha(p) and v['misplaced_emitted_rows_sha256']==sha(raw),'immutable original custody');return d
    (d/'JUDGMENTS.json').write_bytes(raw.read_bytes())
    (d/'ORIGINAL_PHASE_SEAL.json').write_bytes(p.read_bytes())
    write(d/'CUSTODY.json',dict(experiment='E117',part='main',n=3024,status='COMPLETE_JUDGMENT_ROWS_CUSTODY',original_phase_seal=str(p),original_phase_seal_sha256=sha(p),misplaced_emitted_rows_path=str(raw),misplaced_emitted_rows_sha256=sha(raw),sealed_attempts_sha256=sha(p.parent/'ATTEMPTS.json'),input_sha256=sha(phase/'INPUT_SEAL.json'),source_sha256=sha(HERE/'E117_ROWS250_SOURCE_SEAL.json'),literal_final_attempt_equality=True,original_output_files_and_seal_unchanged=True,paid_calls=False,response_reparse=False,analysis_run=False))
    write(final,dict(experiment='E117',part='main',status='COMPLETE_JUDGMENT_ROWS_CUSTODY',n=3024,route_verified=True,labels_cpu_only=True,analysis_run=False,original_phase_seal_sha256=sha(p),misplaced_emitted_rows_sha256=sha(raw),source_seals=[dict(seal=str(p),sha256=sha(p))],files={n:sha(d/n)for n in ['JUDGMENTS.json','ORIGINAL_PHASE_SEAL.json','CUSTODY.json']}))
    return d


def build_main():
    d=custody();p=d/'ROW_CUSTODY_SEAL.json';u=CACHE/'E117/native_units/UNIT_SEAL.json';verify(u,sha(u))
    refs,missing=project(read(u.parent/'SOURCE_POINTERS.PRIVATE.json'),read(d/'JUDGMENTS.json'),dict(seal=str(p),sha256=sha(p)),3024)
    out=CACHE/'E117/native_code_binding';out.mkdir(exist_ok=True);out.chmod(0o700);final=out/'HANDOFF_SEAL.json'
    if final.exists():verify(final,sha(final));require(read(out/'READOUT_CODE_BINDINGS.PRIVATE.json')==refs,'immutable keyed binding');return out
    write(out/'READOUT_CODE_BINDINGS.PRIVATE.json',refs);write(out/'MISSING_SENTINELS.PRIVATE.json',missing)
    write(final,dict(experiment='E117',part='main',status='COMPLETE_JUDGING_POINTERS_FOR_OWNER_SPEC',n=3024,analysis_run=False,route_verified=True,labels_cpu_only=True,custody_repair_only=True,source_seals=[dict(seal=str(x),sha256=sha(x))for x in(p,u)],files={n:sha(out/n)for n in['READOUT_CODE_BINDINGS.PRIVATE.json','MISSING_SENTINELS.PRIVATE.json']}))
    return out


def close_main():
    d=custody();ps=[]
    for phase,n in [('targeted_sham_judging',672),('native_judging',3024)]:
        p=CACHE/'E117'/phase/'outputs/JUDGMENT_SEAL.json';s=verify(p,sha(p));rows=read(d/'JUDGMENTS.json')if phase=='native_judging'else read(p.parent/'JUDGMENTS.json')
        require(s['status']=='COMPLETE'and s['route_verified']is True and len(rows)==len({r['id']for r in rows})==n,'both complete full phases before release')
        x=dict(phase=phase,n=n,seal=str(p),sha256=sha(p))
        if phase=='native_judging':x['judgment_rows_custody_seal']=str(d/'ROW_CUSTODY_SEAL.json');x['judgment_rows_custody_sha256']=sha(d/'ROW_CUSTODY_SEAL.json')
        ps.append(x)
    with dispatch_lock(SHARED/'E117/DISPATCH.lock'):
        actual,unknown=bank_actual(SHARED/'E117/ledger');cost=disposition(4,actual,unknown);a=SHARED/'E117/ALLOCATION_C.json';old=read(a)
        require(old['bank']=='E117'and old['allocation_usd']=='4','same original operational allocation')
        out=CACHE/'E117/complete';out.mkdir(exist_ok=True);final=out/'JUDGMENT_SEAL.json'
        if final.exists():verify(final,sha(final));require(read(out/'BANK_COST.json')==cost,'no charges after closure')
        else:
            require(old['status']=='OPEN','original open allocation')
            write(out/'BANK_COST.json',cost);write(out/'ORIGINAL_ALLOCATION.PRIVATE.json',old);write(out/'PHASES.json',ps)
            write(final,dict(experiment='E117',status='COMPLETE_JUDGING_BANK',n=3696,operational_combined_lifetime_cap_usd='4',registered_combined_maximum_usd='6',extra_allowance_allocated=False,route_verified=True,labels_cpu_only=True,analysis_run=False,source_seals=ps,files={n:sha(out/n)for n in['BANK_COST.json','ORIGINAL_ALLOCATION.PRIVATE.json','PHASES.json']}))
        if old['status']=='RELEASED':require(old['completion_seal_sha256']==sha(final),'same once-only release')
        else:write(a,dict(old,status='RELEASED',completion_seal=str(final),completion_seal_sha256=sha(final),final_actual_usd=str(actual),unused_allocation_released_usd=cost['unused_allocation_released_usd']))
        write(SHARED/'E117/BANK_COMPLETE_C.json',dict(bank='E117',status='COMPLETE',seal=str(final),sha256=sha(final),**cost))
        return final
