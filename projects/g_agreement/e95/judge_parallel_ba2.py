"""ba2c220a7 scheduling only; existing E95/E87 execution remains authoritative."""
import argparse
import fcntl
import hashlib
import multiprocessing
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

import requests
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require
from projects.g_agreement.understand.blind_judge import parallel_funded as pf
from projects.g_agreement.understand.blind_judge.internals_c import transport
from . import judge_dispatch as dispatch, judging_workers as workers, judging_stages as stages
from . import judge_pipeline as pipeline
from .judge_delivery import deliver

ROOT=pipeline.ROOT; PRIVATE=pipeline.PRIVATE; PUB=pipeline.PUB; LEDGER=pipeline.LEDGER
SOURCE=PUB/'BA2_SOURCE_SEAL.json'
AUTHORITY='ba2c220a7cb0a6f56c0f7d13d13d2d60f3e5521d'
INTERVAL={2:7.5,3:15.0}  # unchanged stage1 5s; aggregate <=24 physical/min
RAW_READ=read; RAW_WRITE=write


def gate():
    dispatch.verify_adapter(dict(source_seal=str(SOURCE),source_seal_sha256=sha(SOURCE)))


def stage_state(stage):return LEDGER/f'LOW_RATE_STAGE{stage}_BA2.json'


def decision(stage,now,shared,own,first,second,pressure=False,priority_open=False):
    """Lower priority traffic consumes immediately idle slots only, never FIFO tickets."""
    if priority_open or shared.get('waiting'):return False
    if now<max(shared.get('next_send_epoch',0),shared.get('cooldown_until_epoch',0),own.get('next_send_epoch',0)):return False
    margin=max(1.0,shared['interval_seconds'])+.25
    if first is not None:
        delta=first.get('next_send_epoch',0)-now
        # Stage1 advances its local clock just before joining the global FIFO.
        # Also reserve that handoff window, so no lower stage races ahead.
        if delta<=margin or delta>3.5:return False
    if stage==3 and second is not None:
        if second.get('waiting_until_epoch',0)>now and second.get('next_send_epoch',0)-now<=margin:return False
    if now<own.get('pause_until_epoch',0):return False
    if pressure:return False
    return True


def priority_allocations_open():
    for bank in ('E138R','E140'):
        p=pf.f.CACHE/bank/'ALLOCATION_C.json'
        if p.exists() and RAW_READ(p).get('status')=='OPEN':return True
    return False


def claim_slot(stage,ledger,unused_interval):
    require(Path(ledger).resolve()==LEDGER.resolve(),'single existing lifetime ledger')
    p=stage_state(stage)
    while True:
        transport.unpaused()
        with pf.pacing_lock():
            now=time.time(); shared_path=pf.f.CACHE/'THROUGHPUT.json'
            shared=RAW_READ(shared_path)if shared_path.exists()else pf.initial_pacing()
            own=RAW_READ(p)if p.exists()else dict(next_send_epoch=0,rate_limits=0)
            own['waiting_until_epoch']=now+2
            first=None if(LEDGER/'STAGE1_TERMINAL.json').exists()else RAW_READ(LEDGER/'LOW_RATE.json')
            second=RAW_READ(stage_state(2))if stage_state(2).exists()else None
            pressure_path=LEDGER/'BA2_PRESSURE.json'
            state=RAW_READ(pressure_path)if pressure_path.exists()else dict(baseline={},events=0,pause3=0,pause2=0)
            rates={'shared':shared.get('rate_limits',0)}
            for n in (1,2,3):
                rp=LEDGER/'LOW_RATE.json'if n==1 else stage_state(n)
                rates[str(n)]=RAW_READ(rp).get('rate_limits',0)if rp.exists()else 0
            if not state['baseline']:state['baseline']=rates
            if any(rates[k]>state['baseline'].get(k,0)for k in rates):
                state['events']+=1;state['pause3']=now+60
                if state['events']>1:state['pause2']=now+60
                state['baseline']=rates
            slow=0
            if first is not None:
                sp=PRIVATE/'judgments_stage1_spawn_continuation'
                ps=[x for x in sp.glob('PROGRESS_*.json')]
                slow=now-max(x.stat().st_mtime for x in ps)if ps else 0
            pressure=(now<state['pause3']or slow>60)if stage==3 else(now<state['pause2']or slow>120)
            RAW_WRITE(pressure_path,state)
            allowed=decision(stage,now,shared,own,first,second,pressure,priority_allocations_open())
            if allowed:
                own['next_send_epoch']=now+INTERVAL[stage]*(2**min(own.get('rate_limits',0),5))
                own['waiting_until_epoch']=0
                shared['next_send_epoch']=now+shared['interval_seconds']
                sends=shared.setdefault('bank_sends',{});sends['E95']=sends.get('E95',0)+1
                RAW_WRITE(p,own);RAW_WRITE(shared_path,shared);return
            RAW_WRITE(p,own)
        time.sleep(.2)


def initialize(spec,original,stop):
    gate();stage=spec['judging_stage']
    # Redirect only new processes' own 429/rate state. Stage1 code and file untouched.
    def redirected(p):
        return stage_state(stage)if Path(p).resolve()==(LEDGER/'LOW_RATE.json').resolve()else p
    workers.read=lambda p:RAW_READ(redirected(p))
    workers.write=lambda p,v:RAW_WRITE(redirected(p),v)
    workers.claim_slot=lambda ledger,interval:claim_slot(stage,ledger,interval)
    workers._initialize_paid(spec,original,stop)


def one_worker(items,send,judge,workers_count=2,observer=None,*,spec=None,original=False):
    require(workers_count==2 and spec['judging_stage']in(2,3),'unchanged declared maximum, one effective lower priority worker')
    ctx=multiprocessing.get_context('spawn');stop=ctx.Event()
    with ctx.Pool(1,initializer=initialize,initargs=(spec,original,stop))as pool:
        def send_batch(batch,attempt):
            pids={w.pid for w in pool._pool}
            result=pool.map_async(workers._one,[(item,attempt)for item in batch],chunksize=1)
            while True:
                try:rows=result.get(timeout=1);break
                except multiprocessing.TimeoutError:
                    if {w.pid for w in pool._pool}!=pids:
                        stop.set();raise RuntimeError('lower priority worker died; preserve unknown, no replay')
            if observer is not None:observer(rows,attempt)
            return rows
        return judge(items,send_batch)


def claim(ledger,stage,packet_sha,out):
    require(stage in(2,3)and Path(ledger).resolve()==LEDGER.resolve(),'ba2 exact stage and bank')
    path=LEDGER/f'STAGE{stage}_ONCE.json'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
    RAW_WRITE(path,dict(authority=AUTHORITY,judging_stage=stage,pid=os.getpid(),
        packet_seal_sha256=packet_sha,out=str(Path(out).resolve()),source_sha256=sha(SOURCE),
        original_guard_reset=False,effective_workers=1))
    return path


def run(spec_path):
    gate();spec=RAW_READ(spec_path);stage=spec['judging_stage']
    require(spec['ba2_source_sha256']==sha(SOURCE),'committed ba2 scheduling source')
    original_lock=dispatch.dispatch_lock
    @contextmanager
    def stage_lock(path):
        require(Path(path).resolve()==(LEDGER/'DISPATCH.lock').resolve(),'canonical original dispatch lock requested')
        with original_lock(LEDGER/f'STAGE{stage}_DISPATCH_BA2.lock'):yield
    dispatch.dispatch_lock=stage_lock;stages.claim=claim;workers.parallel_judge=one_worker
    return dispatch.execute(spec,key=os.environ['OPENROUTER_API_KEY'],preflight=False)


def prepare(stage):
    gate();require(stage in(2,3)and not(LEDGER/f'STAGE{stage}_ONCE.json').exists(),'original unused stage guard')
    gp=PRIVATE/f'GLOBAL_STAGE{stage}_BA2.PRIVATE.json'
    code='import sys; from pathlib import Path; from projects.g_agreement.readerbench.io import write; from projects.g_agreement.understand.blind_judge.internals_c.accounting_wj95255 import snapshot; write(Path(sys.argv[1]),snapshot())'
    subprocess.run([sys.executable,'-c',code,str(gp)],cwd=ROOT.parent/'wt-internals-c',check=True,capture_output=True,text=True)
    g=RAW_READ(gp)
    route,(api,privacy,protocol,io)=pipeline.route_api();api.CAP=Decimal(60)
    cost=api.Ledger(LEDGER/'ledger.jsonl').summary()
    total=pipeline.exposure(g,cost['actual_usd'],cost['unresolved_reserve_usd']);require(total<=1000,'global <=1000')
    live=PRIVATE/f'live_ba2_stage{stage}';live.mkdir(mode=0o700,exist_ok=False);io.CACHE=live
    require(sha(route['privacy_proof'])==route['privacy_proof_sha256'],'pinned privacy proof')
    shutil.copyfile(route['privacy_proof'],live/'OPENROUTER_PRIVACY_PROOF.json')
    routes=privacy.check_route(os.environ['OPENROUTER_API_KEY'])
    q=requests.get('https://openrouter.ai/api/v1/credits',headers={'Authorization':'Bearer '+os.environ['OPENROUTER_API_KEY']},timeout=30,allow_redirects=False);q.raise_for_status();credit=q.json()['data']
    available=Decimal(str(credit['total_credits']))-Decimal(str(credit['total_usage']));require(available>Decimal('.1'),'positive live funds')
    old=RAW_READ(PUB/f'stage{stage}/SPEC.json');dest=PUB/f'stage{stage}_ba2';dest.mkdir(exist_ok=False)
    RAW_WRITE(live/'LIVE_PROOF.PRIVATE.json',dict(at_epoch=time.time(),route_verified=bool(routes),remaining_credits_usd=str(available),full_initial_upper_prefunded=available>=Decimal(old['first_pass_worst_case_usd']),global_snapshot_sha256=sha(gp),no_full_bank_prefunding_claim=True))
    budget=dict(RAW_READ(old['budget_receipt']),issued_epoch=g['at_epoch'],global_judging_committed_including_reservation_usd=str(total),global_snapshot_sha256=sha(gp),live_proof_sha256=sha(live/'LIVE_PROOF.PRIVATE.json'),live_metadata_proof_sha256=sha(live/'LIVE_PROOF.PRIVATE.json'),live_metadata_funding_scope='positive actual account credit; no full initial or lifetime maximum prefunding claim; bounded requests and shared402 enforced',same_original_bank_allocation_sha256=sha(PUB/'ALLOCATION_WJ95.json'),existing_cost=cost,ba2_authority=AUTHORITY)
    bp=dest/'BUDGET_RECEIPT.json';RAW_WRITE(bp,budget)
    spec=dict(old,source_seal=str(SOURCE),source_seal_sha256=sha(SOURCE),ba2_source_sha256=sha(SOURCE),budget_receipt=str(bp),budget_receipt_sha256=sha(bp),out=str(PRIVATE/f'judgments_stage{stage}_ba2'),worker_start_method='spawn',effective_workers=1,effective_interval_seconds=INTERVAL[stage],ba2_authority=AUTHORITY)
    sp=dest/'SPEC.json';RAW_WRITE(sp,spec)
    proof=dispatch.execute(spec,preflight=True)
    RAW_WRITE(dest/'PREFLIGHT.json',dict(proof,spec_sha256=sha(sp),same_frozen_packet=True,scheduling_authority=AUTHORITY,effective_workers=1,rate_per_minute=60/INTERVAL[stage]))
    return sp


def timely(marker,cutoff=pipeline.CUTOFF):
    if not Path(marker).exists():return False
    m=RAW_READ(marker);seal=Path(m['seal']);verify(seal,m['sha256'])
    return max(Path(marker).stat().st_mtime,seal.stat().st_mtime)<cutoff


def supervise():
    gate();status=PRIVATE/'BA2_STATUS.json'
    with(PRIVATE/'BA2_CONTROLLER.lock').open('a')as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        specs={1:PUB/'stage1_spawn_continuation/SPEC.json',2:PUB/'stage2_ba2/SPEC.json',3:PUB/'stage3_ba2/SPEC.json'}
        children={}
        # Only original unused guards. A reserved/started stage is NEVER auto relaunched.
        for stage in(2,3):
            require(not(LEDGER/f'STAGE{stage}_ONCE.json').exists(),'no duplicate lower priority dispatcher')
            log=(PRIVATE/f'STAGE{stage}_BA2_PROCESS.log').open('a')
            children[stage]=subprocess.Popen([sys.executable,'-m','projects.g_agreement.e95.judge_parallel_ba2','--run',str(specs[stage])],cwd=ROOT,stdout=log,stderr=log)
        delivered={};failed={}
        while True:
            for stage in(1,2,3):
                marker=LEDGER/f'STAGE{stage}_TERMINAL.json'
                if stage not in delivered and timely(marker):
                    receipt=deliver(specs[stage],PRIVATE/f'delivery_stage{stage}',PUB/f'complete_stage{stage}')
                    pipeline.notify(f'E95-BA2-STAGE{stage}-COMPLETE-'+receipt['private_delivery_seal_sha256'][:12],f'COMPLETE before15Z stage{stage}: {receipt["primary_groups"]} primary/{receipt["original_comparison_groups"]} original. Normalized unchanged E87/validator221 codes, missing retained, exact source/judge/privacy/route/budget/private joins CPU-local {receipt["private_delivery_seal"]} SHA{receipt["private_delivery_seal_sha256"]}. Receipt{PUB/f"complete_stage{stage}/RECEIPT.json"}. W-lens(map_note5 source5348c18e8)/R-Q consume eligible complete stages; original unbound placebo target lineage explicit, analyst must bind it before science. No raw/labels/private joins exported; no judging analysis. Bank cumulative{receipt["cumulative_E95_bank_cost"]}; unknown holds retained.')
                    pipeline.publish([PUB/f'complete_stage{stage}/RECEIPT.json',PUB/f'complete_stage{stage}/PUBLIC_SEAL.json',*pipeline.own_handoffs()],f'E95: deliver complete stage{stage} under ba2 schedule')
                    delivered[stage]=receipt
                if stage in children and children[stage].poll()is not None and stage not in delivered:
                    failed[stage]=children[stage].returncode
            RAW_WRITE(status,dict(status='ALL_THREE_STAGES_TERMINAL_AND_DELIVERED'if len(delivered)==3 else'RUNNING_BA2',at_epoch=time.time(),pid=os.getpid(),children={str(k):v.pid for k,v in children.items()},delivered=sorted(delivered),failed=failed,source_sha256=sha(SOURCE)))
            if len(delivered)==3:
                pipeline.close_bank(receipt);return
            if time.time()>=pipeline.CUTOFF:
                dispositions={str(s):dict(status='COMPLETE'if s in delivered else'NOT RUN',analysis_eligible=s in delivered)for s in(1,2,3)}
                cp=PUB/'CUTOFF_DISPOSITIONS_BA2.json';RAW_WRITE(cp,dict(paid_cutoff_utc='2026-10-30T15:00:00Z',stages=dispositions,late_terminal_counts=False,unknown_holds_retained=True))
                pipeline.notify('E95-BA2-CUTOFF',f'15Z paid cutoff CLOSED. {dispositions}. Any unfinished stage NOT RUN/not analysed; late seals diagnostic only. Original unknown holds/guards retained; no reset/replay. {cp}')
                pipeline.publish([cp,*pipeline.own_handoffs()],'E95: seal strict 15Z complete-only stage dispositions');return
            time.sleep(5)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run');p.add_argument('--supervise',action='store_true');a=p.parse_args()
    if a.run:run(Path(a.run))
    elif a.supervise:supervise()
    else:raise ValueError('explicit mode required')

if __name__=='__main__':main()
