"""E117's new PID preserves top-priority pacing without replacing any controller.
Only its own ticket moves across other C tickets. Shared intervals/cooldowns and
foreign tickets stay unchanged. No signals, cap/ledger or executing-file edits.
"""
import os,time
from . import transport,backend248,recover_backend248
from .parallel_priority243 import order_slots
from .. import parallel_funded
from projects.g_agreement.readerbench.io import read,write,sha
from projects.g_agreement.readerbench.scoring import require
SHARED=transport.SHARED
LAST_SEND=0.0

def claim_slot(bank):
 global LAST_SEND
 require(bank=='E117','only own E117 priority claim');path=SHARED/'THROUGHPUT.json';ticket=str(os.getpid())+':'+str(time.monotonic_ns());policy=transport.ROOT/'cache/g_agreement/understand/internals_c/parallel_priority243/POLICY.json'
 while True:
  transport.unpaused()
  with parallel_funded.pacing_lock():
   state=read(path);now=time.time();waiting=state.setdefault('waiting',[]);alive=[]
   for x in waiting:
    try:os.kill(x['pid'],0);alive.append(x)
    except ProcessLookupError:pass
    except PermissionError:alive.append(x)
   waiting[:]=alive
   if not any(x['ticket']==ticket for x in waiting):waiting.append(dict(ticket=ticket,pid=os.getpid(),bank=bank))
   own=set(read(policy)['own_active_banks']);marked=[dict(x,own_priority_bank=x['bank']in own)for x in waiting];ordered=order_slots(marked,os.getpid(),LAST_SEND,now,state['interval_seconds']);waiting[:]=[{k:v for k,v in x.items()if k!='own_priority_bank'}for x in ordered]
   until=max(state['next_send_epoch'],state['cooldown_until_epoch'])
   if waiting[0]['ticket']==ticket and now>=until:
    waiting.pop(0);state['next_send_epoch']=now+state['interval_seconds'];state['bank_sends'][bank]=state['bank_sends'].get(bank,0)+1;write(path,state);LAST_SEND=now
    d=transport.ROOT/'cache/g_agreement/understand/internals_c/E117/native_judging/backend248';write(d/'PRIORITY_STATUS.json',dict(pid=os.getpid(),last_send_epoch=now,protected_period_seconds=4,interval_seconds=state['interval_seconds'],provider_cooldown_preserved=state['cooldown_until_epoch'],no_worker_signals=True));return
   write(path,state);delay=max(.05,until-now)
  time.sleep(min(delay,.25))

def source_gate():
 p=transport.HERE/'E117_BACKEND_PRIORITY248_SOURCE.json'
 for n,h in read(p)['files'].items():require(sha(transport.ROOT/n)==h,'published protected E117 continuation source')
 return p

if __name__=='__main__':
 source=source_gate();a=read(transport.ROOT/'cache/g_agreement/understand/internals_c/E117/native_judging/backend248/ADMISSION.json');require(a['priority_source_sha256']==sha(source),'source-bound E117 top-priority admission');parallel_funded.claim_slot=claim_slot;recover_backend248.run('E117')
