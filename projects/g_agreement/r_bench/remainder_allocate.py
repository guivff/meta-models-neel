"""One explicit new-pod attempt with a durable receipt; never exports secrets or resumes pods."""
from __future__ import annotations
import argparse
import datetime
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from projects.g_agreement.r_bench.t_a02_controller import Api, ApiError

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'results/g_agreement/r/remainder'
CAPS={'r2':1200,'r3':1200,'r4':3600,'r5':1800,'r6':1200}
URL='https://rest.runpod.io/v1/pods'


class AllocationApi(Api):
    def request(self,url,method='GET',payload=None):
        # The legacy REST datacenter enum excludes current GraphQL datacenters
        # (e.g. US-NC-2). Rule8's documented mutation supports those regions.
        if url==URL and method=='POST' and payload and payload.get('volumeInGb')==0 and 'networkVolumeId' not in payload:
            query=offvolume_mutation(payload)
            answer=self.request('https://api.runpod.io/graphql','POST',{'query':query})
            if answer.get('errors'):
                error_text=json.dumps(answer['errors']).lower()
                capacity=any(x in error_text for x in ('no instances','no longer any instances','no available','not enough free','insufficient resources'))
                raise ApiError('graphql_capacity_unavailable' if capacity else 'graphql_create_error')
            pod=(answer.get('data') or {}).get('podFindAndDeployOnDemand')
            if not isinstance(pod,dict):raise ApiError('graphql_create_missing_pod')
            return pod
        body=None if payload is None else json.dumps(payload).encode()
        req=urllib.request.Request(url,data=body,method=method,headers={
            'Authorization':'Bearer '+self._key,'Content-Type':'application/json',
            'User-Agent':'Mozilla/5.0 Remainder-PodLaunch/1.0'})
        try:
            with self._opener(req,timeout=20) as response:
                raw=response.read();return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raw=exc.read().lower()
            reason='capacity_unavailable' if any(s in raw for s in
                (b'no instances',b'no available',b'not enough free',b'insufficient resources')) else 'unclassified'
            raise ApiError(f'http_{exc.code}:{reason}') from None
        except Exception as exc:
            raise ApiError(type(exc).__name__) from None


def offvolume_mutation(payload):
    if (payload.get('env',{}).keys()!={'PUBLIC_KEY'} or payload.get('volumeInGb')!=0
            or 'networkVolumeId' in payload or payload.get('containerDiskInGb')!=200
            or len(payload.get('gpuTypeIds',[]))!=1 or len(payload.get('dataCenterIds',[]))!=1):
        raise ValueError('Off-volume mutation requires the reviewed single-GPU public-key-only payload')
    strings={'gpuTypeId':payload['gpuTypeIds'][0],'dataCenterId':payload['dataCenterIds'][0],
             'name':payload['name'],'imageName':payload['imageName'],'dockerArgs':'','ports':'22/tcp'}
    fields=['cloudType: SECURE','gpuCount: 1','volumeInGb: 0','containerDiskInGb: 200','minVcpuCount: 8','minMemoryInGb: 60']
    fields += [k+': '+json.dumps(v) for k,v in strings.items()]
    fields += ['env: [{key: "PUBLIC_KEY", value: '+json.dumps(payload['env']['PUBLIC_KEY'])+'}]']
    return 'mutation { podFindAndDeployOnDemand(input: {'+', '.join(fields)+'}) { id name desiredStatus costPerHr } }'


def save(path,record,exclusive=False):
    """Claim before POST; persist known ID before any guard operation can fail."""
    path.parent.mkdir(parents=True,exist_ok=True)
    if exclusive:
        with path.open('x') as stream:
            stream.write(json.dumps(record,indent=2)+'\n');stream.flush();os.fsync(stream.fileno())
    else:
        temporary=path.with_name(path.name+'.partial')
        with temporary.open('w') as stream:
            stream.write(json.dumps(record,indent=2)+'\n');stream.flush();os.fsync(stream.fileno())
        temporary.replace(path)


def exact_matches(value,name):
    if not isinstance(value,list) or any(not isinstance(p,dict) for p in value):
        raise ApiError('invalid_pod_list')
    return [p for p in value if p.get('name')==name]


def make_payload(exp,intent,public_key,fallback=None):
    name=fallback['name'] if fallback else intent['names'][exp]
    cap=intent['caps_seconds'][exp]
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',name): raise ValueError('Invalid unique pod name')
    if isinstance(cap,bool) or not isinstance(cap,int) or not 30<cap<=CAPS[exp]:
        raise ValueError('Allocation cap exceeds registered experiment cap')
    if not public_key.startswith(('ssh-ed25519 ','ssh-rsa ','ecdsa-sha2-')) or '\n' in public_key:
        raise ValueError('PUBLIC_KEY must be one SSH public-key line')
    payload={'name':name,'imageName':'runpod/pytorch:1.0.2-cu1281-torch280-ubuntu2404','gpuCount':1,
        'gpuTypeIds':['NVIDIA H100 80GB HBM3','NVIDIA H100 NVL','NVIDIA A100-SXM4-80GB','NVIDIA A100 80GB PCIe','NVIDIA H200'],
        'cloudType':'SECURE','networkVolumeId':intent['network_volume'],'dataCenterIds':[intent['data_center']],
        'containerDiskInGb':50,'volumeMountPath':'/workspace','ports':['22/tcp'],'interruptible':False,
        'env':{'PUBLIC_KEY':public_key}}
    if fallback:
        center=fallback['data_center'];gpu=fallback['gpu_type']
        if center=='EUR-IS-3': raise ValueError('Use the volume in EUR-IS-3, not off-volume fallback')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',center): raise ValueError('Invalid explicit datacenter')
        if not isinstance(gpu,str) or not gpu.startswith('NVIDIA ') or 'MIG' in gpu.upper() or any(ord(c)<32 for c in gpu):
            raise ValueError('Specify one approved NVIDIA GPU type; no MIG or AMD')
        if name in intent['names'].values(): raise ValueError('Fallback requires a new unique name')
        payload.pop('networkVolumeId')
        payload.update(containerDiskInGb=200,volumeInGb=0,dataCenterIds=[center],gpuTypeIds=[gpu])
    return payload


def fallback_context(exp,intent,fallback,out,now=None,require_ready=True):
    """Preserve and bind old ambiguous receipts; only a fresh provider read can clear a fallback."""
    now=time.time() if now is None else now
    original_path=out/exp/'allocation.json'
    original_bytes=original_path.read_bytes()
    original=json.loads(original_bytes)
    if original.get('experiment')!=exp or original.get('name')!=intent['names'][exp]:
        raise ValueError('Original receipt identity differs from allocation intent')
    if original.get('limit_seconds')!=intent['caps_seconds'][exp]:
        raise ValueError('Fallback may not renew or extend the original experiment cap')
    started=original.get('started_epoch')
    if isinstance(started,bool) or not isinstance(started,(int,float)) or not 0<started<=now:
        raise ValueError('Original receipt lacks a valid shortage-start timestamp')
    # The first failed volume attempt is a conservative start for the fifteen-minute shortage wait.
    wait=max(0,900-(now-started))
    if require_ready and wait>0: raise ValueError('PODS rule 8 requires fifteen minutes without volume-region capacity')
    receipts=[original_path]+sorted((out/exp/'allocations').glob('*.json'))
    histories=[]
    for path in receipts:
        blob=path.read_bytes();row=json.loads(blob)
        if row.get('experiment')!=exp or not row.get('name'): raise ValueError('Prior receipt has invalid identity')
        if row.get('pod_id'):
            raise ValueError('A prior receipt has a known pod ID; resolve that pod before fallback')
        histories.append({'path':str(path.relative_to(out)),'name':row['name'],
                          'sha256':hashlib.sha256(blob).hexdigest(),'status':row.get('status')})
    recorded_names={json.loads(p.read_text()).get('name') for p in out.glob('*/allocations/*.json')}
    if fallback['name'] in recorded_names: raise ValueError('Fallback name already has a receipt; reconcile instead')
    return {'original_receipt':str(original_path.relative_to(out)),
            'original_receipt_sha256':hashlib.sha256(original_bytes).hexdigest(),
            'prior_receipts':histories,'wait_remaining_seconds':wait,
            'original_limit_seconds':original['limit_seconds'],
            'fresh_exact_name_reconciliation_required':True}


def redacted_preview(exp,intent,fallback=None,out=OUT):
    payload=make_payload(exp,intent,'ssh-ed25519 PUBLIC_KEY_OMITTED',fallback)
    payload.pop('env')
    result={'mode':'DRY_RUN_NO_NETWORK_OR_ALLOCATION','experiment':exp,'payload':payload,
            'env_keys':['PUBLIC_KEY'],'limit_seconds':intent['caps_seconds'][exp],
            'credential_deployment':'separate remainder_connect SSH stdin after own-ID check; authorized 2026-10-20'}
    if fallback:
        context=fallback_context(exp,intent,fallback,out,require_ready=False)
        result.update(fallback_context=context,receipt_path=str(out/exp/'allocations'/f"{fallback['name']}.json"),
                      prerequisites=['fresh exact-name reconciliation','remote guard credential setup authorization',
                                     'PODS rule 6 booking with the explicit new datacenter'])
    return result


def spawn_guard(record,root=ROOT):
    pid=record['pod_id'];exp=record['experiment']
    local=root/'cache/g_agreement/r/remainder'/exp/'launch';local.mkdir(parents=True,exist_ok=True)
    ack=local/f'{pid}.armed';log=local/f'{pid}.local_guard.log'
    if ack.exists(): raise ValueError('Refuse pre-existing bootstrap acknowledgement')
    args=[sys.executable,'-m','projects.g_agreement.r_bench.t_a02_controller','local-watchdog','--pod-id',pid,
        '--started-at',str(record['started_epoch']),'--limit-seconds',str(record['limit_seconds']),
        '--stop-margin-seconds','30','--boot-ack-path',str(ack),
        '--boot-timeout-seconds',str(record.get('boot_timeout_seconds',300))]
    with log.open('xb') as stream:
        proc=subprocess.Popen(args,cwd=root,stdout=stream,stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL,start_new_session=True)
    metadata={'local_guard_pid':proc.pid,'local_guard_log':str(log.relative_to(root)),
              'armed_ack':str(ack.relative_to(root))}
    return proc,log,metadata


def await_guard(proc,log,pod,deadline,timeout=5):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if proc.poll() is not None: raise RuntimeError('local_watchdog_exited_before_arm')
        for line in log.read_text().splitlines():
            try: row=json.loads(line)
            except json.JSONDecodeError: continue
            if (row.get('event')=='local_watchdog_armed' and row.get('pod_id')==pod
                    and row.get('deadline')==deadline):
                return
        time.sleep(.05)
    raise RuntimeError('local_watchdog_arm_unconfirmed')


@contextmanager
def allocation_lock(exp,out):
    """Serialize competing names within an experiment; no cross-experiment exclusion."""
    directory=out/exp;directory.mkdir(parents=True,exist_ok=True)
    with (directory/'.allocation.lock').open('a') as stream:
        try: fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('Another allocation attempt for this experiment is active') from None
        try: yield
        finally: fcntl.flock(stream.fileno(),fcntl.LOCK_UN)


def allocate(exp,intent,api,public_key,out=OUT,guard_spawn=spawn_guard,guard_await=await_guard,fallback=None):
    with allocation_lock(exp,out):
        return _allocate(exp,intent,api,public_key,out,guard_spawn,guard_await,fallback)


def _allocate(exp,intent,api,public_key,out=OUT,guard_spawn=spawn_guard,guard_await=await_guard,fallback=None):
    payload=make_payload(exp,intent,public_key,fallback);name=payload['name']
    result_path=out/exp/('allocations/'+name+'.json' if fallback else 'allocation.json')
    context=fallback_context(exp,intent,fallback,out) if fallback else None
    if result_path.exists():
        raise RuntimeError('Prior allocation receipt exists; reconcile it, never blindly create twice')
    stock=api.request(URL)
    if exact_matches(stock,name):
        raise RuntimeError('Intended name already exists; reconcile by its ID without allocation')
    if context:
        checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
        for old in context['prior_receipts']:
            if hashlib.sha256((out/old['path']).read_bytes()).hexdigest()!=old['sha256']:
                raise RuntimeError('Prior receipt changed while reconciling')
            if exact_matches(stock,old['name']):
                raise RuntimeError('Prior intended name now has a pod; reconcile its ID before fallback')
        context['fresh_reconciliation']={'checked_at':checked_at,'names':[r['name'] for r in context['prior_receipts']],
                                         'exact_matches':0,'provider':'GET /v1/pods'}
    start=time.time()
    record={'experiment':exp,'name':name,'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'started_epoch':start,'limit_seconds':intent['caps_seconds'][exp],
        'volume':None if fallback else intent['network_volume'],'data_center':payload['dataCenterIds'][0],
        'deployment':'off_volume' if fallback else 'shared_volume',
        'create_transport':'graphql_rule8' if fallback else 'rest_v1',
        'gpu_type_ids':payload['gpuTypeIds'],'container_disk_gb':payload['containerDiskInGb'],
        'boot_timeout_seconds':240 if fallback else 300,'status':'ALLOCATION_REQUEST_IN_FLIGHT'}
    if context: record['fallback_context']=context
    save(result_path,record,exclusive=True)  # concurrent processes cannot both reach POST
    try:
        pod=api.request(URL,'POST',payload)
        if (not isinstance(pod,dict) or not isinstance(pod.get('id'),str)
                or not re.fullmatch(r'[A-Za-z0-9_-]+',pod['id'])):
            raise ApiError('create_missing_valid_id')
        if pod.get('name',name)!=name: raise ApiError('create_name_mismatch')
    except ApiError as exc:
        record['error']=str(exc)
        try: matches=exact_matches(api.request(URL),name)
        except ApiError:
            matches=[];record['reconciliation_unavailable']=True
        record['matched_pods']=len(matches)
        if len(matches)!=1:
            # An empty immediate list can lag creation. Never state that zero matches prove no billable pod exists.
            record.update(status='ALLOCATION_FAILED_OR_UNKNOWN',automatic_retry_allowed=False,
                          reconciliation_required=True,
                          observed_candidate_ids=[x.get('id') for x in matches])
            save(result_path,record);return record,2
        pod=matches[0];record['reconciled_after_error']=str(exc)
    pid=pod.get('id')
    if not isinstance(pid,str) or not re.fullmatch(r'[A-Za-z0-9_-]+',pid):
        record.update(status='ALLOCATION_FAILED_OR_UNKNOWN',error='reconciled_missing_valid_id',
                      reconciliation_required=True,automatic_retry_allowed=False)
        save(result_path,record);return record,2
    record.update(status='ALLOCATED_GUARD_PENDING',pod_id=pid,cost_per_hr=pod.get('costPerHr'),image=pod.get('imageName'))
    save(result_path,record)  # retain the explicit ID even when process/log/guard creation fails
    try:
        proc,log,metadata=guard_spawn(record)
        record.update(metadata);save(result_path,record)
        guard_await(proc,log,pid,start+record['limit_seconds']-30)
    except Exception as exc:
        record.update(status='ALLOCATED_GUARD_UNCONFIRMED',guard_error=type(exc).__name__,
                      immediate_operator_action_required=True)
        save(result_path,record);return record,3
    record['status']='ALLOCATED_WAITING_FOR_OWN_SSH';record['local_guard_armed']=True
    save(result_path,record);return record,0


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--experiment',choices=CAPS,required=True)
    p.add_argument('--off-volume',action='store_true')
    p.add_argument('--name');p.add_argument('--data-center');p.add_argument('--gpu-type')
    p.add_argument('--dry-run',action='store_true',help='Print redacted payload; no API key, public key, or network needed')
    args=p.parse_args(argv)
    if args.off_volume and not all((args.name,args.data_center,args.gpu_type)):
        p.error('--off-volume requires explicit --name, --data-center and --gpu-type')
    if not args.off_volume and any((args.name,args.data_center,args.gpu_type)):
        p.error('Explicit fallback fields require --off-volume')
    fallback=({'name':args.name,'data_center':args.data_center,'gpu_type':args.gpu_type} if args.off_volume else None)
    intent=json.loads((OUT/'allocation_intent.json').read_text())
    if args.dry_run:
        print(json.dumps(redacted_preview(args.experiment,intent,fallback),indent=2));return 0
    api=AllocationApi(os.environ['RUNPOD_API_KEY'])
    public_key=(Path.home()/'.ssh/id_ed25519_runpod.pub').read_text().strip()
    record,code=allocate(args.experiment,intent,api,public_key,fallback=fallback)
    print(json.dumps(record));return code

if __name__=='__main__':raise SystemExit(main())
