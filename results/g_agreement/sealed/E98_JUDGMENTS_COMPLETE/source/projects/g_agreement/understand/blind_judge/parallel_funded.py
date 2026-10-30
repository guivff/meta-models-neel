"""Independent funded bank launchers with shared adaptive request-slot pacing."""
import argparse
import hashlib
import fcntl
import json
import os
import time
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from . import funded_queue as f
from . import e101_judging as e
from .dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read,write,sha
from projects.g_agreement.readerbench.scoring import require
HERE=f.ROOT/'results/g_agreement/understand/blind_judge/parallel_funded'
MAX_429_RETRIES=4


def source_gate():
    for n,h in read(HERE/'SOURCE_SEAL.json')['files'].items():require(sha(f.ROOT/n)==h,'parallel source pin')


@contextmanager
def pacing_lock():
    """Short shared state lock waits on normal cross-bank contention."""
    path=f.CACHE/'THROUGHPUT.lock';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX)
        try:yield
        finally:fcntl.flock(handle,fcntl.LOCK_UN)


def initial_pacing():
    return dict(interval_seconds=1.0,next_send_epoch=0,cooldown_until_epoch=0,rate_limits=0,bank_sends={})


def claim_slot(bank):
    """FIFO request tickets split one global rate budget; inference can overlap."""
    path=f.CACHE/'THROUGHPUT.json';ticket=f'{os.getpid()}:{time.monotonic_ns()}'
    while True:
        require(not (f.CACHE/'PAUSED_402.json').exists(),'shared HTTP402 pause')
        with pacing_lock():
            state=read(path) if path.exists() else initial_pacing();now=time.time()
            waiting=state.setdefault('waiting',[])
            alive=[]
            for x in waiting:
                try:os.kill(x['pid'],0);alive.append(x)
                except ProcessLookupError:pass
                except PermissionError:alive.append(x)
            waiting[:]=alive
            if not any(x['ticket']==ticket for x in waiting):waiting.append(dict(ticket=ticket,pid=os.getpid(),bank=bank))
            until=max(state['next_send_epoch'],state['cooldown_until_epoch'])
            if waiting[0]['ticket']==ticket and now>=until:
                waiting.pop(0);state['next_send_epoch']=now+state['interval_seconds'];state['bank_sends'][bank]=state['bank_sends'].get(bank,0)+1
                write(path,state);return
            write(path,state);delay=max(.05,until-now)
        time.sleep(min(delay,.25))


def rate_limited(bank):
    path=f.CACHE/'THROUGHPUT.json'
    with pacing_lock():
        state=read(path) if path.exists() else initial_pacing()
        state['interval_seconds']=min(30,state['interval_seconds']*2)
        state['cooldown_until_epoch']=time.time()+min(60,5*2**min(state['rate_limits'],4))
        state['rate_limits']+=1;state['last_rate_limited_bank']=bank;write(path,state)


def eligible_429(root,stage,rid):
    path=root/stage/(rid+'.response.json')
    if not path.exists():return False
    saved=read(path);body=saved['response']
    return saved['http_status']==429 and not body.get('id') and not body.get('choices')


def patch_api(api,io,bank):
    original=api.Client.one
    if getattr(original,'_parallel_patched',False):return original
    def one(client,stage,items,taxonomy=None):
        wire=api.P.payload(stage,items,taxonomy);canonical=io.canonical(wire);digest=io.digest;base=digest(canonical)
        try:
            for retry in range(MAX_429_RETRIES+1):
                rid=base if retry==0 else hashlib.sha256(f'RATE429:{base}:{retry}'.encode()).hexdigest()
                io.digest=lambda value,rid=rid:rid
                cached=client.root/stage/(rid+'.result.json')
                if not cached.exists():claim_slot(bank)
                result=original(client,stage,items,taxonomy)
                if not eligible_429(client.root,stage,rid):return result
                rate_limited(bank)
                # Missing provider usage remains conservatively reserved. Each retry is
                # a distinct physical reservation; no assumed zero or ledger mutation.
                if retry==MAX_429_RETRIES:return result
            return result
        finally:io.digest=digest
    one._parallel_patched=True
    api.Client.one=one
    return original


def run(bank):
    source_gate();require(not (f.CACHE/'PAUSED_402.json').exists(),'shared HTTP402 pause')
    root=f.CACHE/bank;root.mkdir(exist_ok=True)
    if (root/'judgments/JUDGMENT_SEAL.json').exists():
        write(root/'PARALLEL_STATUS.json',dict(status='ALREADY_COMPLETE',bank=bank));return
    route_modules=f.route_modules;require_original=f.require
    def modules(plan):
        api,privacy,protocol,io=route_modules(plan);patch_api(api,io,bank);return api,privacy,protocol,io
    def checked(condition,message):
        if not condition and message in ('unresolved reservation: reconcile before resume','reconcile unresolved before resume'):
            # A known rejected429 can remain conservatively reserved and safely retry
            # with a new identity. Every other unresolved request still fails closed.
            route,(api,privacy,p,io)=f.route_api();book,done=api.Ledger(root/'ledger/ledger.jsonl').totals()
            pending=set(book)-done
            require(bool(pending) and all(any(eligible_429(root/'ledger',d.name,rid) for d in (root/'ledger').iterdir() if d.is_dir()) for rid in pending),'unknown unresolved request; no resume')
            return
        require_original(condition,message)
    @contextmanager
    def scoped_lock(path):
        if Path(path)==f.OLD/'FUNDED_QUEUE_GLOBAL.lock':yield
        else:
            with dispatch_lock(path):yield
    f.route_modules=modules;f.require=checked;e.require=checked;f.dispatch_lock=scoped_lock
    stamp=time.time();write(root/'PARALLEL_STATUS.json',dict(status='RUNNING',bank=bank,start_epoch=stamp,start_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime(stamp)),source_seal_sha256=sha(HERE/'SOURCE_SEAL.json')))
    try:
        if bank=='E101':e.execute()
        else:
            f.source_gate();a=read(f.CACHE/'ADMISSION.json')
            key=os.environ.get('OPENROUTER_API_KEY');require(bool(key),'credential unavailable')
            f.execute_bank(bank,a,key)
        seal=root/'judgments/JUDGMENT_SEAL.json';require(seal.exists(),'terminal seal expected')
        # Bind the executed pacing/retry driver in addition to the preserved route seal.
        receipt=read(seal);write(root/'judgments/PARALLEL_EXECUTION.json',dict(source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),bank=bank,throughput_state=read(f.CACHE/'THROUGHPUT.json'),unknown429_cost_policy='original reservation retained; never zero-guessed'))
        receipt['files']['PARALLEL_EXECUTION.json']=sha(root/'judgments/PARALLEL_EXECUTION.json');receipt['parallel_source_seal_sha256']=sha(HERE/'SOURCE_SEAL.json');write(seal,receipt)
        write(root/'PARALLEL_STATUS.json',dict(status='COMPLETE',bank=bank,start_epoch=stamp,completed_epoch=time.time(),judgment_seal_sha256=sha(seal)))
    except Exception as exc:
        write(root/'PARALLEL_STATUS.json',dict(status='PAUSED_402' if isinstance(exc,f.CreditPause) or (f.CACHE/'PAUSED_402.json').exists() else 'BLOCKED',bank=bank,error_type=type(exc).__name__,start_epoch=stamp));raise

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bank',choices=['E87','E100','E101'],required=True);a=p.parse_args();run(a.bank)
