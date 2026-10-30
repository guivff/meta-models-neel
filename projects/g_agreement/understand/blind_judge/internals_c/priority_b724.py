"""Operational priority for already-running C workers, at unreserved FIFO slots.

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


def park(state,targets,cost,send):
    paused={}
    for name,w in targets.items():
        entries=[x for x in state.get('waiting',[]) if x['pid']==w['pid'] and x['bank']==w['bank']]
        if not entries:continue
        actual,unknown=cost(SHARED/w['bank']/'ledger')
        if unknown!=0:continue
        send(w['pid'],signal.SIGSTOP)
        state['waiting']=[x for x in state['waiting'] if x not in entries]
        paused[name]=dict(w,removed_unreserved_tickets=entries,actual_usd=str(actual),unknown_usd='0',paused_epoch=time.time())
    return paused


def belongs(pid,module,phase):
    r=subprocess.run(['ps','-p',str(pid),'-o','args='],capture_output=True,text=True)
    return r.returncode==0 and ('-m '+module+' ') in r.stdout and ('--phase-directory '+phase) in r.stdout


def run(plan_path):
    home=plan_path.parent;plan=read(plan_path);source=ROOT/'results/g_agreement/understand/blind_judge/internals_c/PRIORITY_B724_SOURCE_SEAL.json'
    for n,h in read(source)['files'].items():require(sha(ROOT/n)==h,'published administrative priority source')
    paused={};known={};last=None
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


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);run(p.parse_args().plan)
