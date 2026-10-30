"""Lock-safe replacement priority for already-running C workers at unreserved FIFO slots.

No API/analysis call, source edit, reservation/settlement change or worker restart.
The existing FIFO re-enqueues a removed waiting ticket on same-process resume.
"""
import argparse,fcntl,json,os,signal,subprocess,time
from pathlib import Path
from .transport import ROOT,SHARED,ACCOUNT_PAUSE
from .accounting import bank_actual
from .runner import CACHE
from projects.g_agreement.readerbench.io import read,write,sha
from projects.g_agreement.readerbench.scoring import require


def pacing_fd_open(pid):
    r=subprocess.run(['lsof','-nP','-a','-p',str(pid),str(SHARED/'THROUGHPUT.lock')],capture_output=True,text=True)
    require(r.returncode in (0,1),'exact own pacing FD inspection completed')
    return r.returncode==0


def park(state,targets,cost,send,has_fd=pacing_fd_open):
    paused={}
    for name,w in targets.items():
        entries=[x for x in state.get('waiting',[]) if x['pid']==w['pid'] and x['bank']==w['bank']]
        if not entries:continue
        actual,unknown=cost(SHARED/w['bank']/'ledger')
        if unknown!=0:continue
        send(w['pid'],signal.SIGSTOP)
        # Caller still holds the pacing lock. A queued stopped flock waiter can
        # otherwise be granted the lock on release and keep it forever. Resume
        # it BEFORE releasing this lock; it cannot claim a send slot meanwhile.
        try:unsafe=has_fd(w['pid'])
        except BaseException:
            send(w['pid'],signal.SIGCONT);raise
        if unsafe:
            send(w['pid'],signal.SIGCONT);continue
        state['waiting']=[x for x in state['waiting'] if x not in entries]
        paused[name]=dict(w,removed_unreserved_tickets=entries,actual_usd=str(actual),unknown_usd='0',paused_epoch=time.time())
    return paused


def belongs(pid,module,phase):
    r=subprocess.run(['ps','-p',str(pid),'-o','args='],capture_output=True,text=True)
    return r.returncode==0 and ('-m '+module+' ') in r.stdout and ('--phase-directory '+phase) in r.stdout


def recover_locked_pauses(paused,belongs_fn,cost,send,has_fd,now,global_pause):
    recovered=[]
    for name,w in list(paused.items()):
        if not has_fd(w['pid']):continue
        require(not global_pause and now<w['loaded_cutoff_epoch'] and now<1793372400,'no recovery after loaded/paid cutoff or during402')
        require(belongs_fn(w['pid'],w['module'],w['phase_directory']) and cost(SHARED/w['bank']/'ledger')[1]==0,'only own previously unreserved and fully accounted worker')
        send(w['pid'],signal.SIGCONT);recovered.append(name);paused.pop(name)
    return recovered


def restored_known(plan,state):
    specs={s['name']:s for s in plan['ordered_existing_phases']};known={}
    for name,worker in state['active'].items():
        require(name in specs and specs[name]['bank']==worker['bank'] and type(worker['pid'])is int,'original own active phase identity')
        known[name]=dict(specs[name],pid=worker['pid'])
    return known


def run(plan_path,restore_path,refresh_path):
    home=restore_path.parent;source=ROOT/'results/g_agreement/understand/blind_judge/internals_c/PRIORITY_LOCK_SAFE_SOURCE_SEAL.json'
    for n,h in read(source)['files'].items():require(sha(ROOT/n)==h,'published lock-safe priority source')
    restored=read(restore_path);paused=dict(restored['paused']);known=restored_known(read(plan_path),restored);known.update({n:dict(w)for n,w in paused.items()});last=None
    refresh=read(refresh_path);proof=Path(refresh['private_live_proof_path'])
    require(sha(proof)==refresh['live_proof_sha256'] and 0<=time.time()-read(proof)['at_epoch']<300 and all(read(proof)[k]is True for k in ('route_verified','account_privacy_verified','funded_remaining_bank_cap')),'fresh source-bound supplementary dispatch proof before lock recovery')
    require(refresh['source_seal_sha256']==sha(source) and refresh['original_priority_status_sha256']==sha(restore_path),'refresh bound to this controller source and original controller state')
    pub=read(refresh_path.parent/'PUBLICATION.json');allocation=Path(pub['allocation_path'])
    require(sha(allocation)==pub['allocation_sha256']==sha(refresh_path) and subprocess.check_output(['git','show',pub['commit']+':'+str(allocation.relative_to(ROOT))],cwd=ROOT)==allocation.read_bytes(),'supplementary no-reset dispatch proof published before recovery')
    pause=(SHARED/'PAUSED_402.json').exists()or(ACCOUNT_PAUSE.exists()and read(ACCOUNT_PAUSE).get('status')!='FUNDING_CONFIRMED_RESUMED')
    recovered=recover_locked_pauses(paused,belongs,bank_actual,os.kill,pacing_fd_open,time.time(),pause)
    write(home/'LOCK_RECOVERY.json',dict(recovered_own_processes=recovered,original_status_sha256=sha(restore_path),no_rate_or_ledger_edit=True,source_sha256=sha(source)))
    while True:
        plan=read(plan_path)
        lock=SHARED/'THROUGHPUT.lock';queue=SHARED/'THROUGHPUT.json';lock.parent.mkdir(exist_ok=True)
        with lock.open('a') as handle:
            fcntl.flock(handle,fcntl.LOCK_EX)
            state=read(queue)
            for spec in plan['ordered_existing_phases']:
                name=spec['name'];d=CACHE/spec['phase']
                if(d/'outputs/JUDGMENT_SEAL.json').exists():known.pop(name,None);continue
                if not(d/'PUBLICATION.json').exists():continue
                a=read(d/'ADMISSION.json');require(a['operator']=='W-internals-C' and a['bank']==spec['bank'],'only own already admitted registered phase')
                for row in state.get('waiting',[]):
                    if row['bank']==spec['bank'] and belongs(row['pid'],spec['module'],spec['phase_directory']):known[name]=dict(spec,pid=row['pid'])
            active={n:w for n,w in known.items() if belongs(w['pid'],w['module'],w['phase_directory']) and not(CACHE/w['phase']/'outputs/JUDGMENT_SEAL.json').exists()}
            primary=next((s['name'] for s in plan['ordered_existing_phases'] if s['name'] in active),None)
            global_pause=(SHARED/'PAUSED_402.json').exists() or (ACCOUNT_PAUSE.exists() and read(ACCOUNT_PAUSE).get('status')!='FUNDING_CONFIRMED_RESUMED')
            before_cutoff=time.time()<1793372400
            targets={n:w for n,w in active.items() if n not in paused and (n!=primary or global_pause or not before_cutoff)}
            new=park(state,targets,bank_actual,os.kill);paused.update(new)
            if new:write(queue,state)
            if primary in paused and not global_pause and before_cutoff:
                w=paused[primary]
                if time.time()<w['loaded_cutoff_epoch'] and bank_actual(SHARED/w['bank']/'ledger')[1]==0:
                    os.kill(w['pid'],signal.SIGCONT);paused.pop(primary)
            fcntl.flock(handle,fcntl.LOCK_UN)
        out=dict(status='RUNNING_PRIORITY' if active else 'WAITING_FOR_EXISTING_PHASES',pid=os.getpid(),primary=primary,paused=paused,active={n:dict(bank=w['bank'],pid=w['pid']) for n,w in active.items()},global_402=global_pause,paid_cutoff_epoch=1793372400,source_sha256=sha(source))
        signature=json.dumps(out,sort_keys=True)
        if signature!=last:write(home/'STATUS.json',dict(out,at_epoch=time.time()));last=signature
        if not before_cutoff:
            write(home/'CUTOFF_REACHED.json',dict(at_epoch=time.time(),paused=paused,no_resume_after_paid_cutoff=True));return
        time.sleep(.25)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--restore-status',type=Path,required=True);p.add_argument('--dispatch-refresh',type=Path,required=True)
    a=p.parse_args(argv);run(a.plan,a.restore_status,a.dispatch_refresh)


if __name__=='__main__':main()
