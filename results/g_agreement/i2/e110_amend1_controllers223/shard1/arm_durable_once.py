from pathlib import Path
import json,subprocess,shutil,time,os
h=Path(__file__).resolve().parent;s=json.loads((h/'ALLOCATION.private.json').read_text());assert s['status']=='ARMED_WAITING_INDEPENDENT_PARENT_EXIT_PROOF'
assert subprocess.run(['ps','-p',str(s['allocator_pid'])],capture_output=True).returncode!=0
label='com.mats.i2.e110.filter.amend1.s1.20261029.a1.stop';d=Path('/private/tmp')/(label+'-state');d.mkdir(exist_ok=False)
shutil.copy2(h/'absolute_stop.py',d/'absolute_stop.py');shutil.copy2(h/'ALLOCATION.private.json',d/'ALLOCATION.private.json')
r=subprocess.run(['launchctl','submit','-l',label,'-o',str(d/'stdout.log'),'-e',str(d/'stderr.log'),'--','/usr/bin/python3',str(d/'absolute_stop.py')],capture_output=True);assert r.returncode==0
for _ in range(30):
 if (d/'ABSOLUTE_GUARD.private.json').exists():break
 time.sleep(.1)
a=json.loads((d/'ABSOLUTE_GUARD.private.json').read_text());assert a['original_creation']==s['created_epoch'] and a['original_deadline']==s['hard_deadline_epoch'] and a['stop_at']==s['hard_deadline_epoch']-10
shutil.copy2(d/'ABSOLUTE_GUARD.private.json',h/'ABSOLUTE_GUARD.private.json');live=subprocess.run(['launchctl','list',label],capture_output=True,text=True);assert live.returncode==0 and str(d)in live.stdout
(h/'DURABLE_GUARD_LABEL.json').write_text(json.dumps(dict(label=label,state_dir=str(d),original_deadline=s['hard_deadline_epoch']))+'\n');print('Original independent dual guards plus durable absolute stop verified before stage; no clock renewal')
