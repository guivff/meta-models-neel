"""434061b36 item3: concurrent admitted own banks, protected E117 throughput.

This separate administrative process replaces exclusive queuing. It edits no
worker, financial ledger, allocation or scientific guard. Existing cooldowns and
rate-limit history remain intact. One-second aggregate slots use the original
parallel transport's initial cadence; E117 is promoted before its protected
four-second physical-send period. Provider backoff always takes precedence.
"""
import argparse
import fcntl
import os
import signal
import subprocess
import time
from pathlib import Path
from .transport import ROOT, HERE, SHARED, ACCOUNT_PAUSE
from .accounting import bank_actual
from .priority_lock_safe import belongs
from projects.g_agreement.readerbench.io import read, write, sha
from projects.g_agreement.readerbench.scoring import require

DEADLINE = 1793372400


def order_slots(waiting, protected_pid, last_send, now, interval, period=4.0):
    """Promote only across our own background tickets; never displace a foreign ticket."""
    rows = list(waiting)
    own = [i for i, r in enumerate(rows) if r.get('pid') == protected_pid]
    if not own or now + interval + .25 < last_send + period:
        return rows
    index = own[0]
    # Admission's own bank set is passed by caller through own_priority_bank.
    target = index
    while target and rows[target-1].get('own_priority_bank') is True:
        target -= 1
    row = rows.pop(index)
    rows.insert(target, row)
    return rows


def initial_refresh(state, authority, now):
    """A new explicit parallel epoch, not deletion/reset of historic backoff state."""
    out = dict(state)
    require(now >= out.get('cooldown_until_epoch', 0), 'do not override active provider cooldown')
    out['parallel_priority243'] = dict(authority=authority, previous_interval_seconds=out['interval_seconds'],
        at_epoch=now, initial_aggregate_interval_seconds=1.0, protected_bank='E117',
        protected_physical_period_seconds=4.0, prior_rate_limits=out.get('rate_limits', 0))
    out['interval_seconds'] = 1.0
    return out


def source_gate():
    path = HERE/'PARALLEL_PRIORITY243_SOURCE_SEAL.json'
    for name, digest in read(path)['files'].items():
        require(sha(ROOT/name) == digest, 'published parallel priority source')
    return path


def run(home):
    source = source_gate()
    a = read(home/'ADMISSION.json'); live = read(home/'LIVE_PROOF.PRIVATE.json')
    require(a['source_sha256'] == sha(source) and a['live_proof_sha256'] == sha(home/'LIVE_PROOF.PRIVATE.json') and
            0 <= time.time()-live['at_epoch'] < 300 and all(live[k] is True for k in
            ('route_verified','account_privacy_verified','funded_remaining_bank_cap')), 'fresh source-bound parallel dispatch proof')
    pub = read(home/'PUBLICATION.json'); path = Path(pub['allocation_path'])
    require(sha(path) == pub['allocation_sha256'] == sha(home/'ADMISSION.json') and
            subprocess.check_output(['git','show',pub['commit']+':'+str(path.relative_to(ROOT))],cwd=ROOT) == path.read_bytes(),
            'supplementary parallel proof published before signals or pacing changes')
    protected = a['protected_worker']; resume = a['resume_same_workers']
    require(belongs(protected['pid'],protected['module'],protected['phase_directory']), 'same protected E117 worker')
    changed = False; counts = None; last_send = 0.0
    while time.time() < DEADLINE:
        with (SHARED/'THROUGHPUT.lock').open('a') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            state = read(SHARED/'THROUGHPUT.json'); now = time.time()
            pause = (SHARED/'PAUSED_402.json').exists() or (ACCOUNT_PAUSE.exists() and
                    read(ACCOUNT_PAUSE).get('status') != 'FUNDING_CONFIRMED_RESUMED')
            if not changed:
                require(not pause, 'no recovery during402')
                for w in resume:
                    require(belongs(w['pid'],w['module'],w['phase_directory']) and
                            bank_actual(SHARED/w['bank']/'ledger')[1] == 0 and now < w['loaded_cutoff_epoch'],
                            'same own unreserved fully accounted worker before loaded cutoff')
                state = initial_refresh(state, 'actual direct Guiv434061b36 item3 in chat', now)
                for w in resume: os.kill(w['pid'], signal.SIGCONT)
                changed = True
                write(home/'STARTED.json',dict(at_epoch=now,resumed_same_pids=[w['pid'] for w in resume],
                    protected_pid=protected['pid'],no_worker_restart=True,no_ledger_or_cap_reset=True))
            count = state.get('bank_sends',{}).get('E117',0)
            if count != counts: last_send = now; counts = count
            own_banks = set(read(home/'POLICY.json')['own_active_banks'])
            marked = [dict(r, own_priority_bank=r['bank'] in own_banks) for r in state.get('waiting',[])]
            if not pause:
                marked = order_slots(marked, protected['pid'], last_send, now, state['interval_seconds'])
            state['waiting'] = [{k:v for k,v in r.items() if k != 'own_priority_bank'} for r in marked]
            write(SHARED/'THROUGHPUT.json',state)
            write(home/'STATUS.json',dict(at_epoch=now,status='PAUSED402' if pause else 'RUNNING_PARALLEL',
                pid=os.getpid(),protected_bank='E117',protected_pid=protected['pid'],
                protected_period_seconds=4.0,interval_seconds=state['interval_seconds'],
                preserved_cooldown_until_epoch=state.get('cooldown_until_epoch'),
                preserved_rate_limits=state.get('rate_limits'),own_active_banks=sorted(own_banks)))
            fcntl.flock(f, fcntl.LOCK_UN)
        time.sleep(.05)
    write(home/'CUTOFF_REACHED.json',dict(at_epoch=time.time(),no_new_paid_posts_after=DEADLINE))


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--home',type=Path,required=True);run(p.parse_args().home)
