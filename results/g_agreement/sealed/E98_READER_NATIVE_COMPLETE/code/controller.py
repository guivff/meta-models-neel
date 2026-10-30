"""Durable E98 reader lifecycle; exact-ID stops, permanent pulls, no worker replay."""
from pathlib import Path
import argparse,fcntl,hashlib,json,os,re,signal,subprocess,sys,tarfile,time
sys.path.insert(0,str(Path(__file__).resolve().parent))
import i5_controller as C

def complete_grid(seal,records,plan,state):
    if (seal.get('experiment')!='E98' or seal.get('phase')!='reader'
        or seal.get('input_sha256')!=plan['input_sha256'] or seal.get('card_sha256')!=plan['card_sha256']
        or seal.get('layer')!=18):raise ValueError('Frozen reader contract')
    if seal['status']=='COMPLETE':
        expected={'records/'+x+'.json'for x in plan['item_ids']}
        actual={n for n in seal['files']if n.startswith('records/')}
        if len(expected)!=2184 or actual!=expected:raise ValueError('Exact2184native test roster')


def archive(state,plan,final=False):
    run=Path(state['run']);name='final.pax.tar.gz'if final else'incremental.pax.tar.gz';tmp=run/(name+'.part');host,port=state['addr'].split(':')
    cmd=['ssh','-i',str(Path.home()/'.ssh/id_ed25519_runpod'),'-o','BatchMode=yes','-o','StrictHostKeyChecking=accept-new','-o','UserKnownHostsFile='+str(run/'known_hosts'),'-p',port,'root@'+host,'tar --format=pax -czf - -C /workspace/e98 out worker.log assignment.json HARDWARE.json']
    with tmp.open('wb')as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.PIPE,timeout=90)
    if r.returncode:raise RuntimeError('Permanent archive transfer failed')
    os.chmod(tmp,0o600)
    with tarfile.open(tmp)as t:
        members={m.name:m for m in t.getmembers()if m.isfile()};seal=json.load(t.extractfile('out/OUTPUT_SEAL.json'))if'out/OUTPUT_SEAL.json'in members else None
        if final:
            if seal is None:raise ValueError('Final reader seal absent; preserve partial, never destroy')
            for n,h in seal['files'].items():
                if hashlib.sha256(t.extractfile('out/'+n).read()).hexdigest()!=h:raise ValueError('Final archive member mismatch')
            if {n[4:]for n in members if n.startswith('out/')and n!='out/OUTPUT_SEAL.json'}!=set(seal['files']):raise ValueError('Unsealed or missing reader output member')
            complete_grid(seal,[],plan,state)
            if seal['status']=='COMPLETE'and hashlib.sha256(t.extractfile('out/GO.json').read()).hexdigest()!=plan['payload_hashes']['GO.json']:raise ValueError('Actual reader GO')
            if seal['status']=='COMPLETE':
                for n in seal['files']:
                    if n.startswith('records/'):
                        x=json.load(t.extractfile('out/'+n))
                        if x['id']!=Path(n).stem or not isinstance(x['text'],str) or len(x['tokens'])>128:raise ValueError('Original single native greedy128')
    os.replace(tmp,run/name);C.write(run/(name+'.receipt.json'),dict(path=str(run/name),sha256=C.sha(run/name),verified_epoch=time.time(),status=seal.get('status')if seal else None))
    return seal

def guard(run,role):
    state=C.read(run/'STATE.json');ceiling=state['deadline_epoch'];offset=30 if role=='hardstop'else 2
    pod=C.pod(state['pod_id']);C.identity(pod,state)
    C.write(run/(role+'.ready.json'),dict(pid=os.getpid(),pod_id=state['pod_id'],createdAt=state['createdAt'],deadline_epoch=ceiling-offset,authenticated=True,timing_deadline_epoch=state['created_epoch']+900))
    deadline=ceiling
    while True:
        if(run/'CLOSED.json').exists():return
        adm=run/'MEASURED_PRODUCTION.json'
        if adm.exists():
            a=C.read(adm)
            if (a['pod_id']!=state['pod_id']or a['createdAt']!=state['createdAt']or a['admitted_epoch']>state['created_epoch']+900 or a['deadline_epoch']>ceiling or a['deadline_epoch']!=state['created_epoch']+a['cap_seconds']):
                C.write(run/(role+'.alert.json'),dict(reason='Invalid measured identity/late/extended admission; stopping owned pod',epoch=time.time()));break
            deadline=min(deadline,a['deadline_epoch'])
        elif time.time()>=state['created_epoch']+900-offset:break
        if time.time()>=deadline-offset:break
        time.sleep(2)
    while True:
        try:
            C.stop(state);p=C.pod(state['pod_id']);C.identity(p,state)
            if p is None or p['desiredStatus']=='EXITED':C.write(run/(role+'.done.json'),dict(pod_id=state['pod_id'],verified_epoch=time.time()));return
        except Exception as e:C.write(run/(role+'.alert.json'),dict(type=type(e).__name__,epoch=time.time()))
        time.sleep(2)

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
    reply=C.ssh(state,"import pathlib,shutil,json\nr=pathlib.Path('/workspace/e98');shutil.rmtree(r/'inputs',ignore_errors=True);shutil.rmtree(r/'capture',ignore_errors=True)\nfor n in ['source.tar.gz','inputs.tar.gz','capture.tar.gz']:(r/n).unlink(missing_ok=True)\nprint(json.dumps(dict(inputs_absent=not(r/'inputs').exists())))\n")
    C.write(run/'CLEANUP.json',json.loads(reply));return C.read(run/'CLEANUP.json')['inputs_absent']is True

def validate_plan(plan):
    if (plan.get('phase')!='reader' or not 0<plan.get('cap_seconds',0)<=32400
        or plan.get('prior_gpu_seconds')!=580.1988520622253
        or plan['prior_gpu_seconds']+plan['cap_seconds']>36000
        or plan.get('GO_git_verified')is not True or plan.get('same_pod_retained_timing')is not True
        or plan.get('authorization_commit')!='c093f98992403210d86a5f6865015018c170d6af'
        or not plan.get('gpu_types')or not set(plan['gpu_types'])<=set(['NVIDIA H100 80GB HBM3','NVIDIA H100 PCIe','NVIDIA H200'])
        or not 0<=plan.get('projected_upper_usd',float('inf'))<=2500):raise ValueError('Exact E98 reader/cumulativecap/committedR3bGO authorization required')


def run_job(run):
    plan=C.read(run/'PLAN.json');state=None;verified=False;clean=False
    validate_plan(plan)
    if(run/'STATE.json').exists():raise ValueError('Never duplicate/replay a created worker allocation')
    for n,h in plan.get('operator_hashes',{}).items():
        if C.sha(run/n)!=h:raise ValueError('Frozen operator changed')
    for n,h in plan['payload_hashes'].items():
        if C.sha(run/n)!=h:raise ValueError('Frozen payload changed')
    if time.time()>plan['admission_expires_epoch']:raise ValueError('Fresh budget admission required')
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
        else:C.write(run/'NO_ALLOCATION.json',dict(reason='No admitted H100/H200 capacity',epoch=time.time()));return
        p=C.pod(candidate);created=C.epoch(p['createdAt']);state=dict(run=str(run),pod_id=candidate,createdAt=p['createdAt'],created_epoch=created,deadline_epoch=created+plan['cap_seconds'],gpu_type=gpu.replace('NVIDIA ',''),rate=p['costPerHr'],remote='/workspace/e98');C.write(run/'STATE.json',state);fcntl.flock(lock.fileno(),fcntl.LOCK_UN)
        arm_stops(run,state)
        if state['rate']>plan['quoted_rates'][gpu]+1e-6:raise ValueError('Provider rate exceeds quote')
        while True:
            p=C.pod(candidate);C.identity(p,state);ports=(p.get('runtime')or{}).get('ports')or[];port=next((x for x in ports if x['privatePort']==22 and x['isIpPublic']),None)
            if port:state['addr']=port['ip']+':'+str(port['publicPort']);C.write(run/'STATE.json',state);break
            if time.time()>created+240:raise TimeoutError('SSH start fixed staging bound')
            time.sleep(5)
        C.ssh(state,"from pathlib import Path\nPath('/workspace/e98').mkdir(exist_ok=True)\n")
        env['WS2_MAC_GUARD_DIR']=str(run/'stock_guards');remaining=max(1,int(state['deadline_epoch']-30-time.time()))
        g=subprocess.run(['bash',str(run/'ops/ws2_macguard.sh'),'arm',candidate,state['addr'],str(remaining),'999','/workspace/e98/worker.pid','/workspace/e98/out'],env=env,capture_output=True,text=True,timeout=45);(run/'stock_guard.log').write_text(g.stdout)
        if g.returncode:raise RuntimeError('Persistent stock guard arm failed')
        gs=dict(x.split('=',1)for x in(run/'stock_guards/state').read_text().splitlines()if'='in x)
        for key in ['watchdog_pid','watchdog_caffeinate_pid']:
            try:os.kill(int(gs[key]),signal.SIGTERM)
            except ProcessLookupError:pass
        if int(gs['deadline'])>state['deadline_epoch']:raise ValueError('Stock guard clock renewal forbidden')
        for n in ['source.tar.gz','inputs.tar.gz','ASSET_CARD.json','capture.tar.gz','GO.json','timing_worker.py']:C.upload(state,run/n,state['remote']+'/'+n,max(1,min(300,int(created+540-time.time()))))
        ass=dict(experiment='E98',phase='reader',gpu_count=1,gpu_type=state['gpu_type'],budget_admitted=True,
            cap_seconds=plan['cap_seconds'],prior_gpu_seconds=plan['prior_gpu_seconds'],custody_start_epoch=created,deadline_epoch=state['deadline_epoch'],pod_id=candidate,timing_deadline_epoch=created+900)
        argv=['/weights/venv-kernels/bin/python','/workspace/e98/timing_worker.py','/workspace/projects/g_agreement/e98/worker.py','reader','--inputs','/workspace/e98/inputs','--assignment','/workspace/e98/assignment.json','--out','/workspace/e98/out','--card','/workspace/e98/ASSET_CARD.json','--source-sha',plan['worker_sha256'],'--input-sha',plan['input_sha256'],'--card-sha',plan['card_sha256'],'--capture','/workspace/e98/capture','--capture-sha',plan['capture_sha256'],'--go','/workspace/e98/GO.json']
        hardware="import torch,json;assert torch.cuda.device_count()==1;name=torch.cuda.get_device_name(0);assert 'H100'in name or 'H200'in name;print(json.dumps(dict(cuda_name=name,count=1)))"
        script="import pathlib,subprocess,json,os,hashlib\nr=pathlib.Path('/workspace/e98')\nsubprocess.run(['tar','xzf',str(r/'source.tar.gz'),'-C','/workspace'],check=True)\nsubprocess.run(['tar','xzf',str(r/'inputs.tar.gz'),'-C',str(r)],check=True)\nassert (r/'inputs/INPUT_SEAL.json').exists()\nsubprocess.run(['tar','xzf',str(r/'capture.tar.gz'),'-C',str(r)],check=True)\nassert (r/'capture/CAPTURE_SEAL.json').exists()\nassert hashlib.sha256(pathlib.Path('/workspace/projects/g_agreement/e98/worker.py').read_bytes()).hexdigest()=="+repr(plan['worker_sha256'])+"\nhardware=subprocess.check_output(['/weights/venv-kernels/bin/python','-c',"+repr(hardware)+"],text=True);(r/'HARDWARE.json').write_text(hardware)\n(r/'assignment.json').write_text(json.dumps("+repr(ass)+"))\nwith (r/'worker.started').open('x')as f:f.write('once')\nenv=dict(os.environ,RUNPOD_POD_ID="+repr(candidate)+",PYTHONDONTWRITEBYTECODE='1',HF_HOME='/workspace/e98/hf_cache',HF_HUB_DISABLE_IMPLICIT_TOKEN='1')\nfor key in list(env):\n if key in ['HF_TOKEN','HUGGING_FACE_HUB_TOKEN','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE']or 'API_KEY'in key:env.pop(key,None)\nf=(r/'worker.log').open('wb');p=subprocess.Popen("+repr(argv)+",stdout=f,stderr=subprocess.STDOUT,env=env,start_new_session=True,cwd='/workspace');(r/'worker.pid').write_text(str(p.pid));print('WORKER_STARTED')\n"
        C.write(run/'ASSIGNMENT.json',ass);C.write(run/'LAUNCH_REQUESTED.json',dict(epoch=time.time()))
        if'WORKER_STARTED'not in C.ssh(state,script,timeout=45):raise RuntimeError('Worker start unverified')
        C.write(run/'WORKER_STARTED.json',dict(epoch=time.time(),pod_id=candidate));last=0
        while True:
            if not(run/'MEASURED_PRODUCTION.json').exists():
                raw=C.ssh(state,"import pathlib,json\np=pathlib.Path('/workspace/e98/out/MEASURED_TIMING_READY.json');print(p.read_text()if p.exists()else'null')\n")
                profile=json.loads(raw)
                if profile:
                    if profile['retained_samples']!=1 or profile['records']!=1 or not profile['initial_fit']:raise ValueError('First retained timing sample only')
                    import math
                    setup=max(profile['ready_epoch']-created-profile['sample_seconds'],plan['prior_max_setup_seconds'])
                    work=profile['sample_seconds']*2184+plan['prior_terminal_retrieval_seconds']
                    cap=math.ceil(setup+1.25*work)
                    if cap>plan['cap_seconds']or created+cap<=time.time()+120:raise ValueError('Measured full bank does not fit cumulative cap')
                    adm=dict(experiment='E98',pod_id=candidate,createdAt=state['createdAt'],cap_seconds=cap,deadline_epoch=created+cap,ceiling_deadline_epoch=state['deadline_epoch'],max_measured_setup_seconds=setup,measured_work_seconds=work,retained_native_sample_seconds=profile['sample_seconds'],native_items=2184,admitted_epoch=time.time(),formula='ceil(max_measured_inclusive_setup+1.25*measured_work)',first_native_sample_retained=True)
                    C.write(run/'MEASURED_PRODUCTION.json',adm)
                    state['deadline_epoch']=created+cap;C.write(run/'STATE.json',state)
                    C.ssh(state,"import pathlib,json\nr=pathlib.Path('/workspace/e98');a="+repr(adm)+"\ntmp=r/'MEASURED_PRODUCTION.json.tmp';tmp.write_text(json.dumps(a));tmp.replace(r/'MEASURED_PRODUCTION.json')\n")
            if (run/'CORE_PREEMPT_REQUEST.json').exists():
                C.write(run/'PREEMPTED.json',dict(reason='CORE priority',epoch=time.time(),pod_id=candidate))
                C.ssh(state,"import pathlib,os,signal\npid=int(pathlib.Path('/workspace/e98/worker.pid').read_text())\ntry:\n cmd=pathlib.Path('/proc')/str(pid)/'cmdline'\n if '/workspace/projects/g_agreement/e98/worker.py'in cmd.read_text():os.kill(pid,signal.SIGINT)\nexcept FileNotFoundError:pass\n");time.sleep(5);raise RuntimeError('CORE_PREEMPTED')
            status=json.loads(C.ssh(state,"import pathlib,os,json\nr=pathlib.Path('/workspace/e98');pid=int((r/'worker.pid').read_text())\ntry:os.kill(pid,0);alive=True\nexcept ProcessLookupError:alive=False\nprint(json.dumps(dict(alive=alive,seal=(r/'out/OUTPUT_SEAL.json').exists(),samples=len(list((r/'out/records').glob('*.json'))))))\n"));C.write(run/'PROGRESS.json',dict(epoch=time.time(),**status))
            if status['seal']or not status['alive']:break
            if time.time()>state['deadline_epoch']-120:
                C.ssh(state,"import pathlib,os,signal\npid=int(pathlib.Path('/workspace/e98/worker.pid').read_text())\nos.kill(pid,signal.SIGINT)\n");time.sleep(5);break
            if time.time()-last>90 and status['samples']:
                try:archive(state,plan)
                except Exception as error:C.write(run/'INCREMENTAL_ERROR.json',dict(type=type(error).__name__,epoch=time.time()))
                last=time.time()
            time.sleep(15)
        seal=archive(state,plan,True);verified=True;clean=cleanup(state,run)
        C.write(run/'RESULT.json',dict(status=seal['status'],pod_id=candidate,gpu_type=state['gpu_type'],archive_sha256=C.sha(run/'final.pax.tar.gz'),completed_items=len([n for n in seal['files']if n.startswith('records/')and n.endswith('.json')])))
    except BaseException as error:
        C.write(run/'FAILURE.json',dict(type=type(error).__name__,message=str(error)[:160],epoch=time.time()))
        if state is None and(run/'DEPLOY_REQUEST.json').exists():
            for _ in range(24):
                try:
                    found=[p for p in C.api('query { myself { pods { id name desiredStatus createdAt costPerHr } } }')['myself']['pods']if p['name']==plan['pod_name']]
                    if found:
                        p=found[-1];created=C.epoch(p['createdAt']);state=dict(run=str(run),pod_id=p['id'],createdAt=p['createdAt'],created_epoch=created,deadline_epoch=created+plan['cap_seconds'],gpu_type=gpu.replace('NVIDIA ',''),rate=p['costPerHr'],remote='/workspace/e98');C.write(run/'STATE.json',state);break
                except Exception:pass
                time.sleep(5)
        if state and'addr'in state:
            try:
                C.ssh(state,"import pathlib,os,signal\nr=pathlib.Path('/workspace/e98');p=r/'worker.pid'\nif p.exists():\n pid=int(p.read_text());cmd=pathlib.Path('/proc')/str(pid)/'cmdline'\n if cmd.exists()and '/workspace/e98/timing_worker.py'in cmd.read_text():os.kill(pid,signal.SIGINT)\n");time.sleep(2)
            except Exception:pass
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
    if a.mode=='guard':guard(a.run,a.role)
    else:run_job(a.run)
