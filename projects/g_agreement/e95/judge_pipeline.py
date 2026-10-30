"""Deliver terminal stages promptly and advance existing frozen E95 packets.

No acquisition, rubric, parsing, selection, scoring or scientific analysis.
Stage 1 is already executing; this controller never launches it a second time.
"""
import argparse
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path

import requests
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
from projects.g_agreement.understand.blind_judge.funded_queue import route_api
from .judge_dispatch import execute
from .judge_delivery import deliver,append_once

ROOT=Path(__file__).resolve().parents[3]
PRIVATE=ROOT/'cache/g_agreement/e95_judging'
PUB=ROOT/'results/g_agreement/understand/blind_judge/e95_bank'
LEDGER=ROOT.parent/'wt-internals-b/cache/g_agreement/understand/funded_queue/E95/e95_60usd'
SOURCE=PUB/'PIPELINE_SOURCE_SEAL.json'
CUTOFF=1793372400


def source_gate():
    for name,h in read(SOURCE)['files'].items():
        require(sha(ROOT/name)==h,'committed E95 controller source')
        raw=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
        require(__import__('hashlib').sha256(raw).hexdigest()==h,'controller committed bytes')


def command(args,**kwargs):
    return subprocess.run(args,cwd=ROOT,check=True,capture_output=True,text=True,**kwargs)


def pull():
    r=subprocess.run(['git','pull','--rebase','origin','r/blindspot'],cwd=ROOT,capture_output=True,text=True)
    while(ROOT/'.git/rebase-merge').exists()or(ROOT/'.git/rebase-apply').exists():
        conflicts=command(['git','diff','--name-only','--diff-filter=U']).stdout.splitlines()
        require(conflicts and all(n.endswith('HANDOFF.md')for n in conflicts),'source/non-handoff conflict requires review')
        for name in conflicts:
            p=ROOT/name;p.write_text(''.join(l for l in p.read_text().splitlines(keepends=True)if not l.startswith(('<<<<<<< ','=======','>>>>>>> '))))
            command(['git','add',name])
        r=subprocess.run(['git','-c','core.editor=true','rebase','--continue'],cwd=ROOT,capture_output=True,text=True)
    require(r.returncode==0,'shared publication rebase completed')


def publish(paths,message):
    names=[str(Path(p).relative_to(ROOT))for p in paths]
    command(['git','add','--',*names])
    staged=command(['git','diff','--cached','--name-only']).stdout.splitlines()
    require(set(staged)<=set(names),'never include other pending files')
    if not staged:return
    for name in staged:
        raw=subprocess.check_output(['git','show',':'+name],cwd=ROOT)
        require(not re.search(rb'(?:hf_|sk-(?:or-v1-|proj-)?)[A-Za-z0-9_-]{16,}|Bearer\s+[A-Za-z0-9._-]{16,}',raw),'secret scan before commit/push')
    command(['git','commit','-m',message])
    for attempt in range(6):
        pull();source_gate()
        r=subprocess.run(['git','push','origin','HEAD:r/blindspot'],cwd=ROOT,capture_output=True,text=True)
        if r.returncode==0:return
    raise RuntimeError('concurrent shared publication did not complete; never force-push')


def own_handoffs():
    return [ROOT/'results/g_agreement/understand/e95/HANDOFF.md',
            ROOT/'results/g_agreement/reviews/R-Q/HANDOFF.md',
            ROOT/'results/g_agreement/understand/wlens/HANDOFF.md']


def notify(event,message):
    paths=own_handoffs()+[
        ROOT.parent/'wt-wlens/results/g_agreement/understand/e95/HANDOFF.md',
        ROOT.parent/'wt-r-q/results/g_agreement/reviews/R-Q/HANDOFF.md',
        ROOT.parent/'wt-internals-c/results/g_agreement/understand/blind_judge/internals_c/HANDOFF.md']
    for path in paths:append_once(path,event,message)


def accounting(stage):
    dest=PRIVATE/f'GLOBAL_STAGE{stage}_PIPELINE.PRIVATE.json'
    code="""import sys
from pathlib import Path
from projects.g_agreement.readerbench.io import write
from projects.g_agreement.understand.blind_judge.internals_c.accounting253 import snapshot
s=snapshot();write(Path(sys.argv[1]),s)
"""
    subprocess.run([sys.executable,'-c',code,str(dest)],cwd=ROOT.parent/'wt-internals-c',check=True,capture_output=True,text=True)
    return dest,read(dest)


def exposure(snapshot,booked,unknown):
    remaining=max(Decimal(0),Decimal(60)-Decimal(booked)-Decimal(unknown))
    if 'E95'in snapshot['open_banks']:
        require(Decimal(snapshot['open_banks']['E95']['cap'])==60,'same actual existing E95 cap')
        return Decimal(snapshot['actual_plus_open_caps_usd'])
    return Decimal(snapshot['actual_plus_open_caps_usd'])+remaining


def next_spec(stage):
    source_gate();require(stage in(2,3),'controller never relaunches stage1')
    require(not(LEDGER/f'STAGE{stage}_ONCE.json').exists(),'no duplicate stage dispatch')
    previous=read(LEDGER/f'STAGE{stage-1}_TERMINAL.json');verify(previous['seal'],previous['sha256'])
    gpath,g=accounting(stage)
    route,(api,privacy,protocol,io)=route_api();api.CAP=Decimal(60)
    own=api.Ledger(LEDGER/'ledger.jsonl').summary()
    total=exposure(g,own['actual_usd'],own['unresolved_reserve_usd']);require(total<=1000,'all actual/open/unknown <=1000')
    live=PRIVATE/f'live_pipeline_stage{stage}';live.mkdir(exist_ok=False);live.chmod(0o700);io.CACHE=live
    require(sha(route['privacy_proof'])==route['privacy_proof_sha256'],'existing account privacy proof')
    shutil.copyfile(route['privacy_proof'],live/'OPENROUTER_PRIVACY_PROOF.json')
    routes=privacy.check_route(os.environ['OPENROUTER_API_KEY'])
    q=requests.get('https://openrouter.ai/api/v1/credits',headers={'Authorization':'Bearer '+os.environ['OPENROUTER_API_KEY']},timeout=30,allow_redirects=False);q.raise_for_status();v=q.json()['data']
    available=Decimal(str(v['total_credits']))-Decimal(str(v['total_usage']))
    require(available>Decimal('.1'),'positive account funds for next bounded requests; no assumed credit')
    old=read(PUB/f'stage{stage}/SPEC.json');dest=PUB/f'stage{stage}_spawn';dest.mkdir(exist_ok=False)
    write(live/'LIVE_PROOF.PRIVATE.json',dict(at_epoch=time.time(),route_verified=bool(routes),account_privacy_verified=True,remaining_credits_usd=str(available),first_pass_upper_usd=old['first_pass_worst_case_usd'],full_initial_upper_prefunded=available>=Decimal(old['first_pass_worst_case_usd']),funding_scope='positive actual account credit; original bank ledger cap and all-bank HTTP402 pause enforced; no full60 prefunding claim',global_snapshot_sha256=sha(gpath)))
    b=dict(read(old['budget_receipt']),issued_epoch=g['at_epoch'],global_judging_committed_including_reservation_usd=str(total),global_snapshot_sha256=sha(gpath),live_metadata_proof_sha256=sha(live/'LIVE_PROOF.PRIVATE.json'),live_metadata_funding_scope='positive actual credit; next requests bounded and all-bank402 pause enforced; no full maximum prefunding claim',bank_allocation_semantics='same original single lifetime E95 allocation, no per-stage reset',original_bank_allocation_sha256=sha(PUB/'ALLOCATION_WJ95.json'),existing_bank_committed_usd=own['committed_usd'],retained_unknown_reserve_usd=own['unresolved_reserve_usd'])
    bp=dest/'BUDGET_RECEIPT.json';write(bp,b)
    source=PUB/'WJUDGE95_SPAWN_SOURCE_SEAL.json'
    spec=dict(old,source_seal=str(source),source_seal_sha256=sha(source),budget_receipt=str(bp),budget_receipt_sha256=sha(bp),out=str(PRIVATE/f'judgments_stage{stage}_spawn'),worker_start_method='spawn',pipeline_source_seal_sha256=sha(SOURCE))
    sp=dest/'SPEC.json';write(sp,spec)
    proof=execute(spec,preflight=True);write(dest/'PREFLIGHT.json',dict(proof,spec_sha256=sha(sp),previous_terminal_seal_sha256=previous['sha256'],same_original_packet=True,raw_exports=False))
    event=f'E95-STAGE{stage}-PRE-DISPATCH-{spec["packet_seal_sha256"][:12]}'
    notify(event,f'Stage{stage} original frozen packet admitted: {proof["primary_calls"]} primary + {proof["original_calls"]} original comparisons, initial upper {proof["first_pass_upper_usd"]}USD. Same single E95 bank60; cumulative existing cost/unknown retained. Fresh reconciled global including E95 remaining cap {total}USD. SPEC {sp}; source{spec["source_seal_sha256"]}; same packet{spec["packet_seal_sha256"]}. Two fresh workers, <=12physical/min, Cpriority/shared402/15Zphysical cutoff. R-Q notified before calls. No new selection/rubric/parser/analysis.')
    publish([bp,sp,dest/'PREFLIGHT.json',*own_handoffs()],f'E95: admit original stage{stage} packet after prior terminal stage')
    return sp


def close_bank(receipt):
    cost=receipt['cumulative_E95_bank_cost'];booked=Decimal(cost['booked_usd'])
    require(0<=booked<=60,'same lifetime ceiling at closure')
    p=LEDGER.parent/'BANK_TERMINAL_WJ95.json'
    if not p.exists():
        value=dict(experiment='E95',status='ALL_STAGES_DELIVERED_UNUSED_CAP_RELEASED_ONCE',
            original_allocation_sha256=sha(PUB/'ALLOCATION_WJ95.json'),lifetime_cap_usd='60',
            booked_usd=str(booked),known_provider_cost_usd=cost['known_provider_cost_usd'],
            booked_429_upper_bound_usd=cost['booked_429_upper_bound_usd'],
            retained_unknown_reserve_usd=cost['unknown_physical_reserve_usd'],
            unused_authorization_released_usd=str(Decimal(60)-booked),
            unknown_reservations_released=False,bank_reset=False,analysis_run=False,
            terminal_stage_seals={str(i):read(LEDGER/f'STAGE{i}_TERMINAL.json')['sha256']for i in(1,2,3)})
        fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd);write(p,value)
    value=read(p);require(value['booked_usd']==str(booked),'no later cost/release mutation')
    dest=PUB/'BANK_TERMINAL_WJ95.json';dest.write_bytes(p.read_bytes())
    notify('E95-ALL-STAGES-DELIVERED-'+sha(p)[:12],f'ALL3E95judgingstages terminal and delivered. Same60lifetimebank booked{booked}; unusedauthorization{value["unused_authorization_released_usd"]}releasedONCE forglobalaccounting. Providerknown{cost["known_provider_cost_usd"]};429upper{cost["booked_429_upper_bound_usd"]}; originalunknownreserve{cost["unknown_physical_reserve_usd"]}RETAINED, neverzero/refund/replay. Closure{dest} SHA{sha(dest)}. Caccounting should remove remainingopenE95cap but keep allphysicalactual/upper/unknown liabilities. W-lensanalysis/RQreview stillseparate; no scientificanalysisbyW-judge95. Delete judging progressheartbeat after reporting completion.')
    publish([dest,*own_handoffs()],'E95: close delivered three-stage bank and retain unknown liabilities')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage1-spec',required=True);args=parser.parse_args()
    PRIVATE.mkdir(parents=True,exist_ok=True)
    with(PRIVATE/'PIPELINE_CONTROLLER.lock').open('a')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);source_gate()
        write(PRIVATE/'PIPELINE_STATUS.json',dict(status='WATCHING_EXISTING_STAGE1',pid=os.getpid(),at_epoch=time.time(),source_sha256=sha(SOURCE)))
        try:
            spec_path=Path(args.stage1_spec)
            for stage in(1,2,3):
                spec=read(spec_path)
                if stage==1:
                    while not(LEDGER/'STAGE1_TERMINAL.json').exists():
                        require(not(Path(spec['out'])/'BLOCKED.json').exists(),'stage1 stopped; no automatic unknown replay')
                        require(time.time()<CUTOFF+190,'no terminal after cutoff/in-flight timeout; stage incomplete')
                        time.sleep(5)
                else:
                    require(time.time()<CUTOFF,'physical cutoff before next stage')
                    if(LEDGER/f'STAGE{stage}_TERMINAL.json').exists():
                        spec_path=PUB/f'stage{stage}_spawn/SPEC.json';spec=read(spec_path)
                    else:
                        pull();source_gate();spec_path=next_spec(stage);spec=read(spec_path)
                        write(PRIVATE/'PIPELINE_STATUS.json',dict(status='RUNNING_STAGE',stage=stage,pid=os.getpid(),spec=str(spec_path),at_epoch=time.time()))
                        execute(spec,key=os.environ['OPENROUTER_API_KEY'],preflight=False)
                marker=read(LEDGER/f'STAGE{stage}_TERMINAL.json');verify(marker['seal'],marker['sha256'])
                require(str(Path(spec['out'])/'JUDGMENT_SEAL.json')==marker['seal'],'actual stage output identity')
                source_gate()
                receipt=deliver(spec_path,PRIVATE/f'delivery_stage{stage}',PUB/f'complete_stage{stage}')
                event=f'E95-STAGE{stage}-COMPLETE-{receipt["private_delivery_seal_sha256"][:12]}'
                notify(event,f'COMPLETE terminal judging stage{stage}: {receipt["primary_groups"]} primary/{receipt["original_comparison_groups"]} original; missing retained. Normalized original E87/validator221 codes and exact original source/judge/route/privacy/budget/private joins are sealed CPU-local at {receipt["private_delivery_seal"]}, SHA{receipt["private_delivery_seal_sha256"]}. Public receipt{PUB/f"complete_stage{stage}/RECEIPT.json"}; no raw/labels/joins exported or scientific analysis run. W-lens(map_note5 source5348c18e8) analyse only eligible complete stages; R-Q review. Original unbound placebo target lineage is explicit and must be bound before scientific use, never invented. C cumulative E95 bank cost{json.dumps(receipt["cumulative_E95_bank_cost"],sort_keys=True)}. Original guard and unknown holds unchanged; no replay.')
                publish([PUB/f'complete_stage{stage}/RECEIPT.json',PUB/f'complete_stage{stage}/PUBLIC_SEAL.json',*own_handoffs()],f'E95: deliver complete judging stage{stage} to W-lens and R-Q')
                write(PRIVATE/'PIPELINE_STATUS.json',dict(status='STAGE_DELIVERED',stage=stage,pid=os.getpid(),at_epoch=time.time(),delivery_seal_sha256=receipt['private_delivery_seal_sha256']))
            close_bank(receipt)
            write(PRIVATE/'PIPELINE_STATUS.json',dict(status='ALL_THREE_STAGES_TERMINAL_AND_DELIVERED',pid=os.getpid(),at_epoch=time.time(),bank_reset=False,unknown_holds_retained=True,analysis_run=False))
        except BaseException as error:
            write(PRIVATE/'PIPELINE_STATUS.json',dict(status='NEEDS_ATTENTION_NO_REPLAY',pid=os.getpid(),at_epoch=time.time(),error_type=type(error).__name__,detail=str(error),no_guard_reset=True))
            notify('E95-PIPELINE-ATTENTION-'+str(int(time.time())),f'E95 controller stopped on {type(error).__name__}: {error}. Preserve existing bank, guards, source/output seals and unknown reservations. No automatic request replay or scientific analysis. Current status{PRIVATE/"PIPELINE_STATUS.json"}.')
            if time.time()>=CUTOFF:
                dispositions={}
                for stage in(1,2,3):
                    marker=LEDGER/f'STAGE{stage}_TERMINAL.json'
                    if marker.exists():
                        m=read(marker);verify(m['seal'],m['sha256']);dispositions[str(stage)]=dict(status='COMPLETE',terminal_seal_sha256=m['sha256'])
                    else:dispositions[str(stage)]=dict(status='NOT RUN',analysis_eligible=False,reason='judging stage incomplete at paid cutoff; original reservations/partial artifacts retained')
                cp=PUB/'CUTOFF_DISPOSITIONS.json';write(cp,dict(experiment='E95',paid_cutoff_utc='2026-10-30T15:00:00Z',stages=dispositions,unknown_holds_retained=True,analysis_run=False))
                notify('E95-PAID-CUTOFF-20261030',f'PaidphysicalPOSTwindowCLOSED15Z. Stage dispositions{json.dumps(dispositions,sort_keys=True)}. IncompletestagesNOTRUN/notanalysed, allpartialdata/guards/unknownholdsretained. Exactreceipt{cp} SHA{sha(cp)}. No newrequest/replay/guardreset orscientificanalysis.')
                publish([cp,*own_handoffs()],'E95: seal complete-only stage dispositions at paid cutoff')
            raise


if __name__=='__main__':main()
