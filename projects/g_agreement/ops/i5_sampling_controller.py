"""Durable E103 lifecycle; exact-ID stops, permanent pulls, no worker replay."""
from pathlib import Path
import argparse,fcntl,hashlib,json,os,re,signal,subprocess,sys,tarfile,time
sys.path.insert(0,str(Path(__file__).resolve().parent))
import i5_controller as C

def archive(state,plan,final=False):
    run=Path(state['run']);name='final.pax.tar.gz'if final else'incremental.pax.tar.gz';tmp=run/(name+'.part');host,port=state['addr'].split(':')
    cmd=['ssh','-i',str(Path.home()/'.ssh/id_ed25519_runpod'),'-o','BatchMode=yes','-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile='+str(run/'known_hosts'),'-p',port,'root@'+host,'tar --format=pax -czf - -C /workspace/e103 out worker.log assignment.json']
    with tmp.open('wb')as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.PIPE,timeout=90)
    if r.returncode:raise RuntimeError('Permanent archive transfer failed')
    os.chmod(tmp,0o600)
    with tarfile.open(tmp)as t:
        members={m.name:m for m in t.getmembers()if m.isfile()}
        seal=json.load(t.extractfile('out/OUTPUT_SEAL.json'))if'out/OUTPUT_SEAL.json'in members else None
        if final:
            if seal is None:raise ValueError('Final output seal absent; preserve partial, never destroy')
            if seal['experiment']!='E103' or seal['source_seal_sha256']!=plan['source_seal_sha256']or seal['public_source_sha256']!=plan['public_sha256']:raise ValueError('Final source/input binding')
            for n,h in seal['files'].items():
                if hashlib.sha256(t.extractfile('out/'+n).read()).hexdigest()!=h:raise ValueError('Final archive member mismatch')
            if {n[4:]for n in members if n.startswith('out/')and n!='out/OUTPUT_SEAL.json'}!=set(seal['files']):raise ValueError('Unsealed or missing final output member')
            jobs=[n for n in members if n.startswith('out/jobs/')and n.endswith('.json')]
            if len(jobs)!=seal['completed_samples']:raise ValueError('Partial inventory mismatch')
            if seal['status']=='COMPLETE':
                if len(jobs)!=2512 or seal['gpu_type']!=state['gpu_type']:raise ValueError('Complete sample/hardware inventory')
                seen=set();expected={(i,j)for i in plan['item_ids']for j in range(8)}
                for n in jobs:
                    row=json.load(t.extractfile(n));key=(row['id'],row['repeat'])
                    if key in seen or key not in expected:raise ValueError('Sample roster')
                    if(row['temperature'],row['top_p'],row['top_k'],row['max_new_tokens'],row['seed'])!=(1.0,.95,0,64,20261028):raise ValueError('Registered decoding')
                    seen.add(key)
                if state['gpu_type']=='B200':
                    smoke=json.load(t.extractfile('out/B200_SMOKE.json'))
                    if smoke['status']!='PASS' or smoke['items']!=3 or not smoke['finite_outputs']:raise ValueError('Mandatory B200 smoke')
    os.replace(tmp,run/name);C.write(run/(name+'.receipt.json'),dict(path=str(run/name),sha256=C.sha(run/name),verified_epoch=time.time(),status=seal.get('status')if seal else None))
    return seal

def arm_stops(run,state):
    for role in ['hardstop','backstop']:C.service(run,role,['/usr/bin/python3',str(run/'controller.py'),'guard','--run',str(run),'--role',role])
    end=time.time()+30
    while not all((run/(x+'.ready.json')).exists()for x in ['hardstop','backstop']):
        if time.time()>end:raise RuntimeError('Independent absolute stops not authenticated')
        time.sleep(1)
    for role in ['hardstop','backstop']:
        x=C.read(run/(role+'.ready.json'));os.kill(x['pid'],0)
        if x['pod_id']!=state['pod_id']or x['createdAt']!=state['createdAt']or x['deadline_epoch']>state['deadline_epoch']:raise ValueError('Guard identity/deadline')

def retire_stock(run):
    p=run/'stock_guards/state'
    if not p.exists():return
    state=dict(x.split('=',1)for x in p.read_text().splitlines()if'='in x)
    for key in ['hardstop_pid','hardstop_caffeinate_pid','watchdog_pid','watchdog_caffeinate_pid']:
        try:
            pid=int(state[key]);args=subprocess.check_output(['ps','-o','args=','-p',str(pid)],text=True)
            if str(run/'stock_guards')in args:
                os.kill(pid,signal.SIGTERM);time.sleep(.3)
                again=subprocess.run(['ps','-o','args=','-p',str(pid)],capture_output=True,text=True)
                if str(run/'stock_guards')in again.stdout:os.kill(pid,signal.SIGKILL)
        except (KeyError,ProcessLookupError,subprocess.CalledProcessError):pass

def cleanup(state,run):
    reply=C.ssh(state,"import pathlib,shutil,json\nr=pathlib.Path('/workspace/e103');shutil.rmtree(r/'inputs',ignore_errors=True)\nfor n in ['source.tar.gz','inputs.tar.gz']:(r/n).unlink(missing_ok=True)\nprint(json.dumps(dict(inputs_absent=not(r/'inputs').exists())))\n")
    C.write(run/'CLEANUP.json',json.loads(reply));return C.read(run/'CLEANUP.json')['inputs_absent']is True

def run_job(run):
    plan=C.read(run/'PLAN.json');state=None;verified=False;clean=False
    if(run/'STATE.json').exists():raise ValueError('Never duplicate/replay a created worker allocation')
    for n,h in plan.get('operator_hashes',{}).items():
        if C.sha(run/n)!=h:raise ValueError('Frozen operator changed')
    for n,h in plan['payload_hashes'].items():
        if C.sha(run/n)!=h:raise ValueError('Frozen payload changed')
    if plan['cap_seconds']!=3500 or plan['projected_upper_usd']>1500 or time.time()>plan['admission_expires_epoch']:raise ValueError('Fresh sub-hour/budget admission required')
    lock=(run.parent/'DEPLOY.lock').open('a');fcntl.flock(lock.fileno(),fcntl.LOCK_EX)
    try:
        for gpu in plan['gpu_types']:
            pods=C.api('query { myself { pods { id name desiredStatus createdAt costPerHr } } }')['myself']['pods'];live=[p for p in pods if p['desiredStatus']=='RUNNING']
            if len(live)>=20 or {p['id']for p in live}-set(plan['known_live_ids']):raise ValueError('Refresh shared liabilities')
            if sum(p['costPerHr']for p in live)+plan['quoted_rates'][gpu]>plan['provider_hourly_limit_usd']+1e-6:continue
            if time.time()-max([C.epoch(p['createdAt'])for p in pods]+[0])<60:raise ValueError('Wait deployment spacing')
            C.write(run/'DEPLOY_REQUEST.json',dict(gpu=gpu,name=plan['pod_name'],epoch=time.time()))
            env=dict(os.environ,WS2_REPO=str(run),WS2_MAIN_CHECKOUT=str(run),WS2_DEPLOY_LOG=str(run/'deploy.jsonl'),WS2_MAC_CACHE=str(run/'stock_pulls'))
            response=subprocess.run(['bash',str(run/'ops/ws2_offvolume.sh'),'deploy-vol',gpu,plan['volume'],plan['pod_name']],env=env,capture_output=True,text=True,timeout=70)
            candidate=response.stdout.strip().splitlines()[-1]if response.stdout.strip()else''
            if response.returncode==0 and re.fullmatch('[a-z0-9]{6,30}',candidate):break
            found=[p for p in C.api('query { myself { pods { id name desiredStatus createdAt costPerHr } } }')['myself']['pods']if p['name']==plan['pod_name']]
            if found:candidate=found[-1]['id'];break
        else:C.write(run/'NO_ALLOCATION.json',dict(reason='No admitted H200/B200 capacity',epoch=time.time()));return
        p=C.pod(candidate);created=C.epoch(p['createdAt']);state=dict(run=str(run),pod_id=candidate,createdAt=p['createdAt'],created_epoch=created,deadline_epoch=created+3500,gpu_type=gpu.replace('NVIDIA ',''),rate=p['costPerHr'],remote='/workspace/e103');C.write(run/'STATE.json',state);fcntl.flock(lock.fileno(),fcntl.LOCK_UN)
        arm_stops(run,state)
        if state['rate']>plan['quoted_rates'][gpu]+1e-6:raise ValueError('Provider rate exceeds quote')
        while True:
            p=C.pod(candidate);C.identity(p,state);ports=(p.get('runtime')or{}).get('ports')or[];port=next((x for x in ports if x['privatePort']==22 and x['isIpPublic']),None)
            if port:state['addr']=port['ip']+':'+str(port['publicPort']);C.write(run/'STATE.json',state);break
            if time.time()>created+240:raise TimeoutError('SSH start fixed staging bound')
            time.sleep(5)
        C.ssh(state,"from pathlib import Path\nPath('/workspace/e103').mkdir(exist_ok=True)\n")
        env['WS2_MAC_GUARD_DIR']=str(run/'stock_guards');remaining=max(1,int(state['deadline_epoch']-30-time.time()))
        g=subprocess.run(['bash',str(run/'ops/ws2_macguard.sh'),'arm',candidate,state['addr'],str(remaining),'999','/workspace/e103/worker.pid','/workspace/e103/out'],env=env,capture_output=True,text=True,timeout=45);(run/'stock_guard.log').write_text(g.stdout)
        if g.returncode:raise RuntimeError('Persistent stock guard arm failed')
        gs=dict(x.split('=',1)for x in(run/'stock_guards/state').read_text().splitlines()if'='in x)
        for key in ['watchdog_pid','watchdog_caffeinate_pid']:
            try:os.kill(int(gs[key]),signal.SIGTERM)
            except ProcessLookupError:pass
        if int(gs['deadline'])>state['deadline_epoch']:raise ValueError('Stock guard clock renewal forbidden')
        for n in ['source.tar.gz','inputs.tar.gz','assets.json']:C.upload(state,run/n,state['remote']+'/'+n,max(1,min(300,int(created+540-time.time()))))
        ass=dict(experiment='E103',gpu_count=1,gpu_type=state['gpu_type'],cap_seconds=3500,prior_seconds=0,pod_id=candidate,pod_created_epoch=created,custody_start_epoch=created,absolute_deadline_epoch=state['deadline_epoch'],daily_budget_verified=True,projected_daily_USD=plan['projected_upper_usd'],analysis_unit_gpu_types={'E103_primary':state['gpu_type']},image_name=plan['image_name'],assets=dict(path='/workspace/e103/assets.json',sha256=plan['payload_hashes']['assets.json']))
        argv=['/weights/venv-kernels/bin/python','/workspace/projects/g_agreement/e103/worker.py','--inputs','/workspace/e103/inputs/SOURCE_PREFIXES.json','--assets','/workspace/e103/assets.json','--assignment','/workspace/e103/assignment.json','--out','/workspace/e103/out','--source-seal','/workspace/E103_SOURCE.json','--source-sha',plan['source_seal_sha256'],'--hardware-reference','/workspace/E103_H200_REFERENCE.json']
        script="import pathlib,subprocess,json,os\nr=pathlib.Path('/workspace/e103');(r/'inputs').mkdir()\nsubprocess.run(['tar','xzf',str(r/'source.tar.gz'),'-C','/workspace'],check=True)\nsubprocess.run(['tar','xzf',str(r/'inputs.tar.gz'),'-C',str(r/'inputs')],check=True)\nassert {p.name for p in(r/'inputs').iterdir()}=={'SOURCE_PREFIXES.json'}\n(r/'assignment.json').write_text(json.dumps("+repr(ass)+"))\nwith (r/'worker.started').open('x')as f:f.write('once')\nenv=dict(os.environ,RUNPOD_POD_ID="+repr(candidate)+",PYTHONDONTWRITEBYTECODE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')\nf=(r/'worker.log').open('wb');p=subprocess.Popen("+repr(argv)+",stdout=f,stderr=subprocess.STDOUT,env=env,start_new_session=True,cwd='/workspace');(r/'worker.pid').write_text(str(p.pid));print('WORKER_STARTED')\n"
        C.write(run/'ASSIGNMENT.json',ass);C.write(run/'LAUNCH_REQUESTED.json',dict(epoch=time.time()))
        if'WORKER_STARTED'not in C.ssh(state,script,timeout=45):raise RuntimeError('Worker start unverified')
        C.write(run/'WORKER_STARTED.json',dict(epoch=time.time(),pod_id=candidate));last=0
        while True:
            status=json.loads(C.ssh(state,"import pathlib,os,json\nr=pathlib.Path('/workspace/e103');pid=int((r/'worker.pid').read_text())\ntry:os.kill(pid,0);alive=True\nexcept ProcessLookupError:alive=False\nprint(json.dumps(dict(alive=alive,seal=(r/'out/OUTPUT_SEAL.json').exists(),samples=len(list((r/'out/jobs').glob('*.json'))))))\n"));C.write(run/'PROGRESS.json',dict(epoch=time.time(),**status))
            if status['seal']or not status['alive']:break
            if time.time()>state['deadline_epoch']-120:
                C.ssh(state,"import pathlib,os,signal\npid=int(pathlib.Path('/workspace/e103/worker.pid').read_text())\nos.kill(pid,signal.SIGINT)\n");time.sleep(5);break
            if time.time()-last>90 and status['samples']:
                try:archive(state,plan)
                except Exception as error:C.write(run/'INCREMENTAL_ERROR.json',dict(type=type(error).__name__,epoch=time.time()))
                last=time.time()
            time.sleep(15)
        seal=archive(state,plan,True);verified=True;clean=cleanup(state,run)
        C.write(run/'RESULT.json',dict(status=seal['status'],pod_id=candidate,gpu_type=state['gpu_type'],archive_sha256=C.sha(run/'final.pax.tar.gz'),completed_samples=seal['completed_samples']))
    except BaseException as error:
        C.write(run/'FAILURE.json',dict(type=type(error).__name__,message=str(error)[:160],epoch=time.time()))
        if state is None and(run/'DEPLOY_REQUEST.json').exists():
            for _ in range(24):
                try:
                    found=[p for p in C.api('query { myself { pods { id name desiredStatus createdAt costPerHr } } }')['myself']['pods']if p['name']==plan['pod_name']]
                    if found:
                        p=found[-1];created=C.epoch(p['createdAt']);state=dict(run=str(run),pod_id=p['id'],createdAt=p['createdAt'],created_epoch=created,deadline_epoch=created+3500,gpu_type=gpu.replace('NVIDIA ',''),rate=p['costPerHr'],remote='/workspace/e103');C.write(run/'STATE.json',state);break
                except Exception:pass
                time.sleep(5)
        if state and'addr'in state:
            try:archive(state,plan,True);verified=True
            except Exception:pass
    finally:
        if state:
            if verified and not clean:
                try:clean=cleanup(state,run)
                except Exception:pass
            while True:
                try:
                    C.stop(state)
                    for _ in range(30):
                        p=C.pod(state['pod_id']);C.identity(p,state)
                        if p is None or p['desiredStatus']=='EXITED':C.write(run/'FIRST_EXITED.json',dict(epoch=time.time(),pod_id=state['pod_id']));break
                        time.sleep(2)
                    C.close(run,state,verified and clean);break
                except Exception as error:C.write(run/'CLOSE_ALERT.json',dict(type=type(error).__name__,epoch=time.time()));time.sleep(5)
            retire_stock(run)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['run','guard']);p.add_argument('--run',type=Path,required=True);p.add_argument('--role',choices=['hardstop','backstop']);a=p.parse_args()
    if a.mode=='guard':C.guard(a.run,a.role)
    else:run_job(a.run)
