"""Warm queue-only R2 then R6 job with one immutable 90-minute interval.

Offline emit/inputs/smoke/receipt helpers never allocate or download. Only explicit
execute on the booked pod runs models. A byte-verified compact probe package plus verified volume states is required
before the first R6 phase. Shared guards remain the integrator's responsibility.
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
MODULE='projects.g_agreement.r_bench.remainder_joint'
CAP,RESERVE=5400,300
R2_PREFIX='cache/g_agreement/r/remainder/r2'


def read(path):return json.loads(Path(path).read_text())

def write(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.partial');tmp.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n');tmp.replace(path)

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()

def digest(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def relative(path):
    p=Path(path)
    if p.is_absolute() or '..' in p.parts or not p.parts or p.name=='.env':raise ValueError('Unsafe relative path')
    return p.as_posix()

def check_path(pod,run):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',pod):raise ValueError('Invalid pod ID')
    if not re.fullmatch(r'/workspace/remainder/r2_r6/[A-Za-z0-9_-]{1,80}',str(run)):raise ValueError('Fresh isolated joint run directory required')

def validate_joint_guard(record,pod,deadline,now,reserve=RESERVE):
    fields=(record.get('started_epoch'),record.get('deadline_epoch'),deadline,now)
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in fields):raise ValueError('Invalid joint guard epochs')
    start,end,deadline,now=fields
    if record.get('experiment')!='r2_r6' or record.get('mode')!='warm_r2_r6_volume' or record.get('schema_version')!=2 or record.get('pod')!=pod:raise ValueError('Joint guard identity/mode mismatch')
    if start>now or not 0<end-start<=CAP:raise ValueError('Joint guard exceeds original 90-minute cap')
    if deadline!=end:raise ValueError('Original absolute joint deadline must be preserved exactly')
    if end-now<=reserve:raise ValueError('Final Mac pull reserve reached')
    return record

def guard(pod,run,expected=None,now=None,env_bytes=None,check_processes=True,reserve=RESERVE):
    run=Path(run);check_path(pod,run);now=time.time() if now is None else now
    raw=Path('/proc/1/environ').read_bytes() if env_bytes is None else env_bytes
    ids=[x.split(b'=',1)[1].decode() for x in raw.split(b'\0') if x.startswith(b'RUNPOD_POD_ID=')]
    if ids!=[pod]:raise ValueError('POD ID MISMATCH')
    blob=(run/'guard.json').read_bytes()
    if expected is not None and blob!=expected:raise ValueError('Immutable joint guard changed')
    g=json.loads(blob);validate_joint_guard(g,pod,g.get('deadline_epoch'),now,reserve)
    if not (run/'ARMED').is_file():raise ValueError('Shared guards not ARMED')
    if check_processes:
        for name in ('watchdog','hardstop'):
            log=(run/f'{name}.log').read_text()
            if pod not in log or 'armed: credential /workspace/.env RUNPOD_API_KEY (check http 200)' not in log:raise ValueError('PODS rule 9 account-credential guard proof missing')
            pid=int((run/f'{name}.pid').read_text())
            if pid<=1:raise ValueError('Invalid live guard PID')
            os.kill(pid,0)
    result={**g,'guard_sha256':hashlib.sha256(blob).hexdigest()}
    if check_processes:require_volume(pod,run,result)
    return result


def require_volume(pod,run,g):
    receipt=read(Path(run)/'volume.json')
    if receipt.get('pod')!=pod or not receipt.get('network_volume_id') or receipt.get('network_volume_id')!=g.get('network_volume_id') or receipt.get('http_status')!=200 or receipt.get('mount_path')!='/workspace':
        raise ValueError('Verified own-pod network-volume receipt required; off-volume forbidden')
    if not os.path.ismount('/workspace') or not Path(run).resolve().is_relative_to('/workspace') or os.stat(run).st_dev!=os.stat('/workspace').st_dev:
        raise ValueError('Run tree must reside on mounted network volume')
    return receipt


def inputs(root=ROOT):
    """Metadata-only union: no data loading or hash regeneration changes the frozen inputs."""
    files={};sources={}
    for exp in ('r2','r6'):
        path=root/f'results/g_agreement/r/remainder/{exp}/deployment_inputs.json';obj=read(path)
        sources[exp]={'path':str(path.relative_to(root)),'sha256':sha(path)}
        for item in obj['input_files']:
            key=relative(item['path']);entry={k:item[k] for k in ('path','bytes','sha256')}
            if not re.fullmatch(r'[0-9a-f]{64}',entry['sha256']) or not isinstance(entry['bytes'],int) or entry['bytes']<=0:raise ValueError('Invalid frozen input metadata')
            if key in files and files[key]!=entry:raise ValueError('Conflicting shared source input: '+key)
            files[key]=entry
    rows=[files[k] for k in sorted(files)]
    return {'experiment':'r2_r6','mode':'warm_network_volume_only','cap_seconds':CAP,'pull_reserve_seconds':RESERVE,'input_files':rows,
            'input_file_count':len(rows),'input_bytes':sum(x['bytes'] for x in rows),'source_manifests':sources,
            'order':['r2_capture','r2_audit','r2_probes_on_pod','mac_verified_probes_and_volume_checksums','r6_recovery','r6_generation'],
            'note':'Network-volume pod required; full R2 states never pulled. Existing warm assets only. No allocations, package installs or model downloads. R6 original full target remains unmet; fixed available cohort is 69 pairs.'}


def verify_inputs(root=ROOT):
    obj=inputs(root)
    for item in obj['input_files']:
        p=root/item['path']
        if not p.is_file() or p.stat().st_size!=item['bytes'] or sha(p)!=item['sha256']:raise ValueError('Frozen input missing/changed: '+item['path'])
    return {k:v for k,v in obj.items() if k!='input_files'}


def warm_environment():
    from projects.g_agreement.core import config as c
    from projects.g_agreement.r_bench import remainder_cold_setup as cold
    cold.require_runtime()
    versions={p.split('==')[0]:importlib.metadata.version(p.split('==')[0]) for p in cold.PINS}
    mismatch=[p for p in cold.PINS if versions[p.split('==')[0]]!=p.split('==')[1]]
    if mismatch:raise ValueError('Warm runtime pins differ; integrator must stage compatible runtime before claiming job: '+str(mismatch))
    import torch
    from transformers import Qwen3_5ForCausalLM
    if not torch.cuda.is_available():raise ValueError('Warm CUDA runtime unavailable')
    hub=Path(os.environ.get('HF_HUB_CACHE',str(Path(os.environ.get('HF_HOME','/workspace/hf_cache'))/'hub')))
    assets=[]
    for label,repo,revision,sub,base in [('target',c.TARGET_MODEL_ID,c.TARGET_MODEL_SHA,'',True),('oracle',c.OLENS_REPO,c.OLENS_SHA,c.OLENS_SUBFOLDER,False),('nla_base',c.NLA_REPO,c.NLA_SHA,c.NLA_BASE_SUBFOLDER,True),('nla_adapter',c.NLA_REPO,c.NLA_SHA,c.NLA_ADAPTER_SUBFOLDER,False)]:
        path=hub/('models--'+repo.replace('/','--'))/'snapshots'/revision/sub
        names=['config.json','tokenizer_config.json','tokenizer.json'] if base else ['adapter_config.json','adapter_model.safetensors']
        if base:
            index=path/'model.safetensors.index.json'
            names+=['model.safetensors.index.json',*sorted(set(read(index)['weight_map'].values()))] if index.is_file() else ['model.safetensors']
        if label=='nla_base':names+=['nla_meta.yaml']
        if any(not (path/n).is_file() for n in names):raise ValueError('Pinned warm asset missing: '+label)
        assets.append({'name':label,'repo':repo,'revision':revision,'path':str(path),'files':len(names)})
    return {'versions':versions,'assets':assets,'cuda':torch.version.cuda,'offline':True}


def r2_commands(pod,run,deadline,rate,python=sys.executable):
    base=[python,'-m','projects.g_agreement.r_bench.remainder_r2_capture']
    live=['--pod',pod,'--guard-dir',str(run),'--deadline-epoch',str(deadline),'--batch','32','--joint-run']
    return [('r2-preflight',base+['--phase','preflight','--pod',pod]),
            ('r2-live-smoke',base+['--phase','live-smoke',*live,'--measured-pull-bytes-per-second',str(rate)]),
            ('r2-capture',base+['--phase','capture',*live]),
            ('r2-audit',base+['--phase','audit','--pod',pod]),
            ('r2-probes',[python,'-m','projects.g_agreement.r_bench.remainder_r2_probe','--pod',pod,'--guard-dir',str(run)])]


def snapshot(run,root=ROOT):
    """Publish closed chunks without copying all raw arrays twice; logs are snapshots."""
    from projects.g_agreement.r_bench.remainder_r2_deploy import publish_file
    dst=run/'deliverables'
    for exp in ('r2','r6','r2_r6'):
        for prefix in ('cache','results'):
            source=root/f'{prefix}/g_agreement/r/remainder/{exp}'
            if source.is_symlink():raise ValueError('Experiment output root must be private')
            if source.exists():
                for p in source.rglob('*'):
                    if p.is_symlink():raise ValueError('Symlink output refused')
                    # Reader states, including incomplete chunks, remain on the volume.
                    if exp=='r2' and prefix=='cache' and any(part in ('capture','capture_smoke','capture_mock') for part in p.relative_to(source).parts):continue
                    if p.is_file():publish_file(p,dst/p.relative_to(root))
    ops=dst/'operations';ops.mkdir(parents=True,exist_ok=True)
    for name in ('guard.json','ARMED','job.sh','job.pid','job.log','joint_status.json','warm_environment.json','input_verification.json','watchdog.log','hardstop.log','watchdog.pid','hardstop.pid','pull_bandwidth.json','r2_checkpoint.json','r2_mac_receipt.json','R2_CHECKPOINT_READY','R2_MAC_VERIFIED','DONE','FAILED','volume.json','volume_states.json'):
        if (run/name).is_file():
            if name=='volume_states.json':publish_file(run/name,ops/name)
            else:shutil.copy2(run/name,ops/name)
    return dst


def checkpoint_budget(cert,rate):
    if not math.isfinite(rate) or rate<=0:raise ValueError('Measured Mac pull rate required')
    if cert['projected_tap_bytes']+2_000_000_000>15_000_000_000:raise ValueError('Compact output exceeds 15 GB; stop and report size')
    audit=max(float(cert.get('projected_audit_seconds',0)),float(cert.get('audit_seconds',0)))
    if audit<=0 or not math.isfinite(audit):raise ValueError('Measured audit timing required')
    # Only compact results/input manifests leave the pod; no tap-byte transfer term.
    transfer=1.5*2_000_000_000/rate
    hashing=2*audit
    return {'one_hash_allowance_seconds':hashing,'transfer_seconds':transfer,'capture_reserve_seconds':RESERVE+transfer+2*hashing+60,
            'states_stay_on_volume':True,'compact_result_budget_bytes':2_000_000_000}


def check_reserve(g,reserve):
    if g["deadline_epoch"]-time.time()<=reserve:raise ValueError("Dynamic R2 checkpoint/pull reserve reached")


def volume_manifest(pod,run,g,root=ROOT):
    require_volume(pod,run,g)
    from projects.g_agreement.r_bench import remainder_r2_capture as R2
    R2.audit(root/R2_PREFIX/'capture',read(root/R2_PREFIX/'capture_manifest.json'))
    files={}
    for checked,path in enumerate(sorted((root/R2_PREFIX/'capture').rglob('*'))):
        if path.is_symlink():raise ValueError('Symlink volume state refused')
        if path.is_file():
            guard(pod,run);rel=path.relative_to(root).as_posix();files[rel]={'bytes':path.stat().st_size,'sha256':sha(path)}
            if checked%512==0:print(json.dumps({'phase':'volume-publish-checksums','checked_files':len(files)}),flush=True)
    if not any(x.endswith('.npy') for x in files):raise ValueError('No volume states')
    return {'pod':pod,'network_volume_id':g['network_volume_id'],'run_dir':str(run),'state_root':str(root/R2_PREFIX/'capture'),
            'guard_sha256':g['guard_sha256'],'files':files,'bytes':sum(x['bytes'] for x in files.values())}


def verify_volume_states(pod,run,g,root=ROOT):
    record=read(run/'volume_states.json');require_volume(pod,run,g)
    if any(record.get(k)!=v for k,v in {'pod':pod,'network_volume_id':g['network_volume_id'],'guard_sha256':g['guard_sha256'],'run_dir':str(run)}.items()):raise ValueError('Volume checksum manifest belongs to another run')
    actual={p.relative_to(root).as_posix() for p in (root/R2_PREFIX/'capture').rglob('*') if p.is_file()}
    if actual!=set(record['files']):raise ValueError('Volume state file coverage changed')
    for checked,(rel,entry) in enumerate(record['files'].items()):
        guard(pod,run);path=root/relative(rel)
        if path.is_symlink() or path.stat().st_size!=entry['bytes'] or sha(path)!=entry['sha256']:raise ValueError('Volume state checksum mismatch')
        if checked%512==0:print(json.dumps({'phase':'volume-recheck','verified_files':checked+1}),flush=True)
    return sha(run/'volume_states.json')


def make_checkpoint(pod,run,g,root=ROOT,budget=None):
    cert=read(root/R2_PREFIX/'capture_complete.json');probe=read(root/R2_PREFIX/'probes/complete.json')
    if cert.get('kind')!='live' or cert.get('pod')!=pod or cert.get('guard_sha256')!=g['guard_sha256'] or cert.get('coverage',{}).get('status')!='PASS' or cert['coverage'].get('arm_cells')!=72:raise ValueError('Full live R2 audit certificate required')
    if probe.get('status')!='PASS' or probe.get('guard_sha256')!=g['guard_sha256'] or probe.get('probe_code_sha')!=sha(root/'projects/g_agreement/r_bench/remainder_r2_probe.py') or probe.get('pod')!=pod or probe.get('manifest_sha256')!=cert.get('manifest_sha256') or probe.get('bootstrap_draws')!=2000 or probe.get('git_sha')!=cert.get('git_sha') or probe.get('code_sha')!=cert.get('code_sha'):raise ValueError('Complete matching probe results required before checkpoint')
    states=volume_manifest(pod,run,g,root)
    if states['bytes']+(root/R2_PREFIX/'capture_manifest.json').stat().st_size+2_000_000_000>15_000_000_000:raise ValueError('Actual compact output exceeds 15 GB; wait')
    write(run/'volume_states.json',states)
    dest=run/'r2_checkpoint'
    if dest.exists():raise ValueError('Checkpoint cannot be replaced')
    dest.mkdir();from projects.g_agreement.r_bench.remainder_r2_deploy import publish_file
    sources=[root/R2_PREFIX/'capture_complete.json',root/R2_PREFIX/'capture_manifest.json',*sorted((root/R2_PREFIX/'probes').rglob('*'))]
    files={}
    for src in sources:
        if src.is_symlink():raise ValueError('Symlink checkpoint refused')
        if src.is_file():
            guard(pod,run);rel=src.relative_to(root).as_posix();p=dest/rel;publish_file(src,p);files[rel]={'bytes':p.stat().st_size,'sha256':sha(p)}
    rel='operations/volume_states.json';publish_file(run/'volume_states.json',dest/rel);files[rel]={'bytes':(dest/rel).stat().st_size,'sha256':sha(dest/rel)}
    manifest={'schema_version':2,'experiment':'r2_r6','pod':pod,'run_dir':str(run),'guard_sha256':g['guard_sha256'],'deadline_epoch':g['deadline_epoch'],
              'network_volume_id':g['network_volume_id'],'volume_states_sha256':sha(run/'volume_states.json'),'files':files,'bytes':sum(x['bytes'] for x in files.values()),
              'capture_certificate_sha256':sha(root/R2_PREFIX/'capture_complete.json'),'content':'probe results, fits, predictions, input manifests, volume checksums; no full states'}
    if manifest['bytes']>2_000_000_000:raise ValueError('Probe package exceeds registered transfer reserve; retain on volume, no R6')
    if budget:manifest['mac_receipt_deadline_epoch']=g['deadline_epoch']-RESERVE-budget['one_hash_allowance_seconds']-30
    write(run/'r2_checkpoint.json',manifest);(run/'R2_CHECKPOINT_READY').write_text(sha(run/'r2_checkpoint.json')+'\n');return manifest


def file_identity(path):
    stat=Path(path).stat()
    # Hardlink publication changes ctime/link count without changing bytes. Bind
    # cached hashes to inode/device, byte count and nanosecond modification time.
    return {'device':stat.st_dev,'inode':stat.st_ino,'bytes':stat.st_size,'mtime_ns':stat.st_mtime_ns}


def checkpoint_identities(root,files):
    return {rel:file_identity(Path(root)/relative(rel)) for rel in files}


def mac_receipt(local,manifest_path,platform=None):
    if (sys.platform if platform is None else platform)!='darwin':raise ValueError('Checkpoint receipt must be made on the Mac')
    record=read(manifest_path);files={}
    if not record.get('files'):raise ValueError('Empty checkpoint manifest')
    for rel,entry in record['files'].items():
        p=Path(local)/relative(rel)
        if p.is_symlink() or not p.is_file():raise ValueError('Missing/linked local checkpoint file')
        files[rel]={'bytes':p.stat().st_size,'sha256':sha(p)}
        if files[rel]!=entry:raise ValueError('Mac checkpoint bytes differ: '+rel)
    return {k:record[k] for k in ('pod','run_dir','guard_sha256','deadline_epoch')} | {'checkpoint_sha256':sha(manifest_path),'verified_on':'Mac','verified_epoch':time.time(),'files':files,'bytes':sum(x['bytes'] for x in files.values()),'verified_file_identities':checkpoint_identities(local,files)}


def _receipt_metadata(pod,run,g=None):
    g=guard(pod,run) if g is None else g
    mpath=run/'r2_checkpoint.json';rpath=run/'r2_mac_receipt.json';m=read(mpath);r=read(rpath)
    for obj in (m,r):
        if any(obj.get(k)!=v for k,v in {'pod':pod,'run_dir':str(run),'guard_sha256':g['guard_sha256'],'deadline_epoch':g['deadline_epoch']}.items()):raise ValueError('Checkpoint belongs to another booked run')
    if r.get('verified_on')!='Mac' or r.get('checkpoint_sha256')!=sha(mpath) or not m.get('files') or r.get('files')!=m['files'] or r.get('bytes')!=m.get('bytes'):raise ValueError('Mac checkpoint receipt missing/mismatched hashes')
    if not g['started_epoch']<=r.get('verified_epoch',0)<=time.time():raise ValueError('Mac checkpoint receipt outside booked interval')
    # Every actual byte was hashed on this pod at publication and on the Mac after
    # transfer. Verify the immutable remote tree again before the first R6 phase.
    for rel,entry in m['files'].items():
        p=run/'r2_checkpoint'/relative(rel)
        if p.is_symlink() or not p.is_file() or p.stat().st_size!=entry['bytes']:raise ValueError('Published R2 checkpoint changed')
    return {**g,'receipt_sha256':sha(rpath),'checkpoint_sha256':sha(mpath)}


_CHECKPOINT_CACHE={}

def require_r2_checkpoint(pod,run,g=None):
    # R6 never consumes or writes R2 data. Bind a once-verified private checkpoint
    # to its immutable receipt files instead of rereading a large volume manifest
    # and thousands of file stats before every generated token/batch.
    g=guard(pod,run) if g is None else g
    require_volume(pod,run,g)
    paths=('r2_checkpoint.json','r2_mac_receipt.json','R2_MAC_VERIFIED','volume_states.json')
    identities={name:file_identity(run/name) for name in paths}
    key=(pod,str(run),g['guard_sha256'])
    cached=_CHECKPOINT_CACHE.get(key)
    if cached and cached['identities']==identities:return cached['proof']
    proof=_receipt_metadata(pod,run,g);marker=read(run/'R2_MAC_VERIFIED');manifest=read(run/'r2_checkpoint.json')
    if any(marker.get(k)!=proof[k] for k in ('receipt_sha256','checkpoint_sha256')):raise ValueError('R2 verified checkpoint marker mismatch')
    if marker.get('volume_states_sha256')!=sha(run/'volume_states.json') or manifest.get('volume_states_sha256')!=marker.get('volume_states_sha256'):raise ValueError('Volume checksum proof changed')
    if marker.get('remote_file_identities')!=checkpoint_identities(run/'r2_checkpoint',manifest['files']):raise ValueError('Verified R2 checkpoint identity or modification time changed')
    _CHECKPOINT_CACHE[key]={'identities':identities,'proof':proof}
    return proof


def wait_checkpoint(pod,run,g,frozen):
    while not (run/'r2_mac_receipt.json').is_file():
        guard(pod,run,frozen)
        if time.time()>=read(run/'r2_checkpoint.json').get('mac_receipt_deadline_epoch',g['deadline_epoch']-RESERVE):raise ValueError('R2 Mac receipt cutoff reached; preserve taps, no R6')
        print('WAIT R2 Mac checkpoint receipt; no R6 work started',flush=True)
        time.sleep(min(15,max(.1,g['deadline_epoch']-time.time()-RESERVE)))
    if time.time()>=read(run/'r2_checkpoint.json').get('mac_receipt_deadline_epoch',g['deadline_epoch']-RESERVE):raise ValueError('R2 Mac receipt arrived after verification cutoff; no R6')
    proof=_receipt_metadata(pod,run,g)
    # A second byte hash here catches modifications after publication; R6 children
    # bind to this receipt, while the completed capture process is no longer live.
    for rel,entry in read(run/'r2_checkpoint.json')['files'].items():
        guard(pod,run,frozen)
        if sha(run/'r2_checkpoint'/rel)!=entry['sha256']:raise ValueError('Published R2 checkpoint hash changed')
    volume_sha=verify_volume_states(pod,run,g)
    if volume_sha!=read(run/'r2_checkpoint.json').get('volume_states_sha256'):raise ValueError('Pulled volume checksum manifest mismatch')
    write(run/'R2_MAC_VERIFIED',{'volume_states_sha256':volume_sha,'receipt_sha256':proof['receipt_sha256'],'checkpoint_sha256':proof['checkpoint_sha256'],
                                 'remote_file_identities':checkpoint_identities(run/'r2_checkpoint',read(run/'r2_checkpoint.json')['files'])})
    return proof


def final_manifest(root,checkpoint_root=None,checkpoint_files=None,identities=None):
    """Hash new evidence; reuse prior actual-byte hashes only for unchanged links."""
    root=Path(root);checkpoint_files=checkpoint_files or {};identities=identities or {};files={}
    for p in sorted(root.rglob('*')):
        if p.is_symlink():raise ValueError('Symlink final deliverable refused')
        if not p.is_file():continue
        rel=p.relative_to(root).as_posix()
        if rel in checkpoint_files:
            src=Path(checkpoint_root)/rel
            if not src.is_file() or not os.path.samefile(p,src) or file_identity(src)!=identities.get(rel):
                raise ValueError('Previously verified tap changed or final file is not its immutable hardlink: '+rel)
            files[rel]=checkpoint_files[rel]['sha256']
        else:files[rel]=sha(p)
    if not files:raise ValueError('No final deliverables')
    if not set(checkpoint_files)<=set(files):raise ValueError('Final tree omits verified R2 checkpoint files')
    return files


def final_mac_receipt(local,checkpoint_root=None,r2_receipt=None,platform=None):
    if (sys.platform if platform is None else platform)!='darwin':raise ValueError('Final receipt must be made on Mac')
    prior=read(r2_receipt) if r2_receipt else {}
    if prior and prior.get('verified_on')!='Mac':raise ValueError('Prior actual-byte Mac checkpoint receipt required')
    files=final_manifest(local,checkpoint_root,prior.get('files'),prior.get('verified_file_identities'))
    return {'mac_verified':True,'verified_on':'Mac','files':files,'r2_receipt_sha256':sha(r2_receipt) if prior else None,
            'checkpoint_reuse':'unchanged same-inode/size/mtime files already SHA256-verified on Mac',
            'verified_epoch':time.time()}


def verify_final(pod,run,receipt_path):
    g=guard(pod,run,reserve=45);receipt=read(receipt_path);checkpoint_files={};identities={}
    if receipt.get('mac_verified') is not True or receipt.get('verified_on')!='Mac':raise ValueError('Final Mac receipt absent')
    if receipt.get('r2_receipt_sha256'):
        require_r2_checkpoint(pod,run,g)
        if receipt['r2_receipt_sha256']!=sha(run/'r2_mac_receipt.json'):raise ValueError('Final receipt R2 checkpoint mismatch')
        checkpoint_files=read(run/'r2_checkpoint.json')['files']
        identities=read(run/'R2_MAC_VERIFIED')['remote_file_identities']
    actual=final_manifest(run/'deliverables',run/'r2_checkpoint',checkpoint_files,identities)
    if actual!=receipt.get('files'):raise ValueError('Final Mac receipt differs from complete remote deliverables')
    result={'pod':pod,'run_dir':str(run),'deadline_epoch':g['deadline_epoch'],'guard_sha256':g['guard_sha256'],
            'receipt_sha256':sha(receipt_path),'files':len(actual),'verified_epoch':time.time(),'complete':True}
    write(run/'FINAL_MAC_VERIFIED',result);return result


def bounded(command,pod,run,frozen,deadline,env,reserve=RESERVE):
    guard(pod,run,frozen)
    from projects.g_agreement.r_bench.remainder_r6_deploy import terminate_tree
    proc=subprocess.Popen(command,cwd=ROOT,env=env,start_new_session=True)
    try:
        while True:
            guard(pod,run,frozen)
            left=deadline-time.time()-reserve
            if left<=0:raise RuntimeError('Immutable phase/pull cutoff reached')
            try:rc=proc.wait(timeout=min(15,max(.1,left)));break
            except subprocess.TimeoutExpired:pass
        if rc:raise RuntimeError('Phase failed with exit '+str(rc))
    finally:
        if proc.poll() is None:terminate_tree(proc)


def phase_environment(source=None):
    env=dict(os.environ if source is None else source)
    for key in ('RUNPOD_API_KEY','HF_TOKEN','HUGGING_FACE_HUB_TOKEN','OPENROUTER_API_KEY'):env.pop(key,None)
    env.update(PYTHONUNBUFFERED='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    return env


def execute(pod,run):
    if ROOT.resolve()!=(run/'repo').resolve():raise ValueError('Execute only in isolated booked repo')
    g=guard(pod,run);frozen=(run/'guard.json').read_bytes()
    if (run/'joint_status.json').exists():raise ValueError('Refuse reused joint job')
    source_paths={x['path'] for x in inputs()['input_files']}
    for exp in ('r2','r6'):
        path=ROOT/f'cache/g_agreement/r/remainder/{exp}'
        if path.is_symlink():raise ValueError('Private output roots required')
        if path.exists() and any(p.is_symlink() or (p.is_file() and p.relative_to(ROOT).as_posix() not in source_paths) for p in path.rglob('*')):
            raise ValueError('Fresh private output roots required; stage frozen source inputs only')
    status={'experiment':'r2_r6','pod':pod,'state':'RUNNING','guard_sha256':g['guard_sha256'],'deadline_epoch':g['deadline_epoch'],'phases':[],'code_sha':sha(__file__)}
    write(run/'joint_status.json',status);code=1
    try:
        from projects.g_agreement.r_bench import remainder_r2_deploy as D2,remainder_r6_deploy as D6
        rate=D2.validate_measurement(read(run/'pull_bandwidth.json'),pod,run,g)
        env=phase_environment();os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
        write(run/'input_verification.json',verify_inputs());guard(pod,run,frozen)
        write(run/'warm_environment.json',warm_environment());guard(pod,run,frozen)
        checkpoint_allowance=None
        for phase,cmd in r2_commands(pod,run,g['deadline_epoch'],rate):
            entry={'phase':phase,'started_epoch':time.time()};status['phases'].append(entry);write(run/'joint_status.json',status)
            if phase=='r2-capture':
                cert=read(ROOT/R2_PREFIX/'live_smoke.json');free=shutil.disk_usage(ROOT/R2_PREFIX).free
                if free<cert['projected_tap_bytes']*1.1+5*1024**3:raise ValueError('Insufficient warm disk for complete tap capture and headroom')
            phase_reserve=RESERVE
            if phase=='r2-capture':phase_reserve=checkpoint_budget(read(ROOT/R2_PREFIX/'live_smoke.json'),rate)['capture_reserve_seconds']
            if phase in ('r2-audit','r2-probes'):
                full=read(ROOT/R2_PREFIX/'capture_complete.json');smoke=read(ROOT/R2_PREFIX/'live_smoke.json')
                full['projected_audit_seconds']=max(full.get('projected_audit_seconds',0),smoke.get('projected_audit_seconds',0))
                checkpoint_allowance=checkpoint_budget(full,rate);check_reserve(g,checkpoint_allowance['capture_reserve_seconds'])
                phase_reserve=checkpoint_allowance['capture_reserve_seconds']
                status['r2_checkpoint_budget']=checkpoint_allowance
            bounded(cmd,pod,run,frozen,g['deadline_epoch'],env,reserve=phase_reserve);entry['complete']=True;write(run/'joint_status.json',status);snapshot(run)
        make_checkpoint(pod,run,g,budget=checkpoint_allowance);snapshot(run)
        status['state']='WAIT_R2_MAC';write(run/'joint_status.json',status)
        proof=wait_checkpoint(pod,run,g,frozen);status['r2_mac_receipt_sha256']=proof['receipt_sha256'];status['state']='RUNNING';write(run/'joint_status.json',status)
        for phase in D6.science_phases('r6'):
            guard(pod,run,frozen);require_r2_checkpoint(pod,run,g)
            cmd=D6.phase_command(phase,'r6',pod,run,g['deadline_epoch']-time.time(),python=sys.executable,joint_run=True)
            entry={'phase':'r6-'+phase,'started_epoch':time.time()};status['phases'].append(entry);write(run/'joint_status.json',status)
            bounded(cmd,pod,run,frozen,g['deadline_epoch'],env);entry['complete']=True;write(run/'joint_status.json',status);snapshot(run)
        status['state']='DONE';code=0
    except Exception as exc:status.update(state='FAILED',error=str(exc))
    finally:
        status['finished_epoch']=time.time();write(run/'joint_status.json',status);(run/status['state']).write_text(json.dumps(status)+'\n');snapshot(run)
        print(status['state']+': pull all available evidence to the Mac; no pod stop or deletion requested',flush=True)
    return code


def emit(pod,run,python):
    check_path(pod,run)
    if not str(python).startswith('/') or any(c in str(python) for c in '\n\r'):raise ValueError('Explicit warm Python absolute path required')
    command=[str(python),'-m',MODULE,'execute','--pod',pod,'--run-dir',str(run)]
    return '\n'.join(['#!/usr/bin/env bash','set -euo pipefail',f'RUN={shlex.quote(str(run))}',f'POD={shlex.quote(pod)}',
        'OWN=$(tr "\\0" "\\n" < /proc/1/environ | sed -n "s/^RUNPOD_POD_ID=//p")',
        '[ "$OWN" = "$POD" ] || { echo "POD ID MISMATCH"; exit 2; }','cd "$RUN/repo"','echo $$ > "$RUN/job.pid"',
        '[ -s GIT_SHA ] || { echo "GIT_SHA missing"; exit 2; }','export R_GIT_SHA="$(cat GIT_SHA)"','export PYTHONUNBUFFERED=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1',
        'export HF_HOME="${HF_HOME:-/workspace/hf_cache}"','export PYTHONPATH="$RUN/repo${PYTHONPATH:+:$PYTHONPATH}"',
        'unset RUNPOD_API_KEY HF_TOKEN HUGGING_FACE_HUB_TOKEN OPENROUTER_API_KEY','exec '+shlex.join(command),''])


def bootstrap(pod,run_id,start,idle_ceiling=90,volume_id=None):
    """Emit shared guards; original queue claim time includes first SSH/code staging."""
    run=Path('/workspace/remainder/r2_r6')/run_id;check_path(pod,run)
    if not volume_id or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',volume_id):raise ValueError('Integrator-booked network volume ID required; off-volume forbidden')
    if isinstance(start,bool) or not isinstance(start,int) or start<=0:raise ValueError('Original queue claim epoch required')
    if idle_ceiling not in (45,90):raise ValueError('Invalid shared idle ceiling')
    from projects.g_agreement.r_bench import remainder_pod as P
    # Use the exact shared scripts, with an original absolute deadline rather than
    # restarting a relative cap when a cold upload finally finishes.
    parts=['#!/usr/bin/env bash','set -euo pipefail',f'POD={shlex.quote(pod)}',f'RUN={shlex.quote(str(run))}',
           'OWN=$(tr "\\0" "\\n" < /proc/1/environ | sed -n "s/^RUNPOD_POD_ID=//p")',
           '[ "$OWN" = "$POD" ] || { echo "POD ID MISMATCH"; exit 2; }','[ ! -e "$RUN" ] || { echo "REFUSE reused run"; exit 2; }',
           f'STARTED={start}',f'DEADLINE={start+CAP}','NOW=$(date +%s)','[ "$STARTED" -le "$NOW" ] && [ "$((DEADLINE-NOW))" -gt 300 ] || { echo "Invalid/expired original interval"; exit 2; }','mkdir -p "$RUN/guards"',
           "cat > \"$RUN/guard.json\" <<'JOINT_GUARD'",json.dumps({'schema_version':2,'experiment':'r2_r6','mode':'warm_r2_r6_volume','pod':pod,'started_epoch':start,'deadline_epoch':start+CAP,'network_volume_id':volume_id},sort_keys=True),'JOINT_GUARD']
    # Read the account credential only inside a subshell; save a minimal receipt.
    parts += ['(', 'set -a; source /workspace/.env >/dev/null 2>&1; set +a',
              'python3 - '+shlex.quote(pod)+' '+shlex.quote(volume_id)+' '+shlex.quote(str(run/'volume.json'))+" <<'VOLUME_CHECK'",
              "import json,os,sys,urllib.request", "pod,volume,out=sys.argv[1:]",
              "req=urllib.request.Request('https://rest.runpod.io/v1/pods/'+pod,headers={'Authorization':'Bearer '+os.environ['RUNPOD_API_KEY'],'User-Agent':'Remainder-volume-check/1'})",
              "with urllib.request.urlopen(req,timeout=15) as r: status=r.status; body=json.load(r)",
              "assert status==200 and body.get('id')==pod and body.get('networkVolumeId')==volume, 'Wrong pod or missing/wrong network volume'",
              "assert os.path.ismount('/workspace'), 'Network volume mount absent'",
              "with open(out,'w') as f: json.dump({'pod':pod,'network_volume_id':volume,'http_status':status,'mount_path':'/workspace'},f)",
              "print('NETWORK VOLUME VERIFIED '+volume)", 'VOLUME_CHECK', ')']
    for name in ('ws2_watchdog.sh','ws2_hardstop.sh','ws2_selfstop.sh'):
        parts += [f"cat > \"$RUN/guards/{name}\" <<'JOINT_SCRIPT'",(P.REPO/'results/g_agreement/r/pod_tools'/name).read_text(),'JOINT_SCRIPT']
    parts += ['export WD_RESERVE_FILE="$RUN/reservation"',f'export WD_CEIL={idle_ceiling}',
              'RESERVATION_END=$(( $(date +%s) + 1800 ))','[ "$RESERVATION_END" -lt "$DEADLINE" ] || RESERVATION_END="$DEADLINE"',
              'printf "job=r2_r6\\nuntil=%s\\n" "$(date -u -d "@$RESERVATION_END" +%FT%TZ)" > "$RUN/reservation"',
              'nohup setsid bash "$RUN/guards/ws2_watchdog.sh" "$POD" "$RUN/job.pid" "$RUN/job.log" > "$RUN/watchdog.log" 2>&1 < /dev/null &','echo $! > "$RUN/watchdog.pid"',
              'REMAINING=$((DEADLINE-$(date +%s)-40))','[ "$REMAINING" -gt 300 ] || exit 2',
              'nohup setsid bash "$RUN/guards/ws2_hardstop.sh" "$POD" "$REMAINING" > "$RUN/hardstop.log" 2>&1 < /dev/null &','echo $! > "$RUN/hardstop.pid"',
              'for attempt in $(seq 1 10); do',
              '  if grep -q "armed: credential /workspace/.env RUNPOD_API_KEY (check http 200)" "$RUN/watchdog.log" && grep -q "armed: credential /workspace/.env RUNPOD_API_KEY (check http 200)" "$RUN/hardstop.log"; then',
              '    kill -0 "$(cat "$RUN/watchdog.pid")" && kill -0 "$(cat "$RUN/hardstop.pid")"','    touch "$RUN/ARMED"; echo "ARMED $RUN"; exit 0','  fi','  sleep 1','done','echo "GUARDS NOT ARMED"; exit 3','']
    return '\n'.join(parts)


def smoke(out):
    """Small real tap write/audit and R6 all-arm generation-contract smoke; no models."""
    import tempfile
    from unittest.mock import patch
    import numpy as np
    from projects.g_agreement.r_bench import remainder_r2_capture as R2,remainder_r6 as R6
    with tempfile.TemporaryDirectory(prefix='remainder-joint-smoke-') as directory:
        root=Path(directory);facts=[];banks={}
        with patch.object(R2,'ROOT',root),patch.object(R2.C,'D_MODEL',4):
            for bank in R2.A.BANKS:
                source=root/bank;source.mkdir();states={}
                for layer in R2.READERS.values():
                    p=source/f'L{layer}.npy';np.save(p,np.arange(16,dtype=np.float16).reshape(4,4))
                    states[str(layer)]={'path':str(p.relative_to(root)),'sha256':sha(p)}
                items=[]
                for j,(split,y) in enumerate([('pool',0),('pool',1),('test',0),('test',1)]):
                    iid=f'{bank}-{split}-{y}';item={'dataset':bank,'item_id':iid,'split':split,'label':y,'primary':{'sided':'two','candidates':['a','b']}}
                    items.append({'item_id':iid,'split':split,'label':y,'state_row':j,'donor_item_id':f'{bank}-{split}-{1-y}',
                                  'donor_state_row':j^1,'label_info':{'kind':'construction'},'item':item})
                facts.append({'bank':bank,'dataset':bank,'tag':'SYNTHETIC','states':states,'items':items});banks[bank]={'sha256':'fixture-bank'}
            manifest={'facts':facts,'banks':banks,'items':12};meta={'pod':'mac-cpu-fixture','git_sha':'fixture','code_sha':'fixture'}
            r2=R2.capture(manifest,root/'capture',meta,True,32,None,mock=True)
            assert r2['coverage']['arm_cells']==72 and r2['coverage']['score_rows']==48
        # Frozen selection rules are tested separately; this checks every decoder
        # case/arm/reader/layer/mode generated by the production job enumerator.
        rows=[]
        for case in R6.CASES:
            for arm in ('focal','control'):
                rows.append({'case':case,'pair_id':case+'-fixture','arm':arm,'states':{str(L):{} for L in (42,44,56)}})
        tasks=[{**r,'text':'fixture report','mock':True} for r in R6.jobs(rows,smoke=True)]
        r6_cells=R6.assert_coverage(tasks)
        assert len(tasks)==80 and r6_cells==80
        result={'kind':'synthetic_cpu_only','no_models_loaded':True,'live_launch_authorized_by_smoke':False,
                'r2_score_rows':48,'r2_arm_cells':72,'r6_report_rows':len(tasks),'r6_arm_cells':r6_cells,
                'ordering_tests':'pytest test_remainder_joint.py checks production execute ordering, checkpoint mismatch and failure short-circuit',
                'pod':'mac-cpu','git_sha':subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT,capture_output=True,text=True,check=True).stdout.strip(),
                'code_sha':sha(__file__),'cap_seconds':CAP,'reserve_seconds':RESERVE}
        if out:write(out,result)
        return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('inputs','emit','execute','bootstrap','mac-receipt','environment','smoke','final-mac-receipt','final-verify'))
    p.add_argument('--volume-id');p.add_argument('--pod');p.add_argument('--run-dir',type=Path);p.add_argument('--run-id');p.add_argument('--started-epoch',type=int);p.add_argument('--python',type=Path);p.add_argument('--local-checkpoint',type=Path);p.add_argument('--checkpoint-manifest',type=Path);p.add_argument('--out',type=Path);p.add_argument('--local-deliverables',type=Path);p.add_argument('--r2-receipt',type=Path);p.add_argument('--receipt',type=Path);a=p.parse_args(argv)
    if a.action=='inputs':result=inputs()
    elif a.action=='environment':result=warm_environment()
    elif a.action=='smoke':result=smoke(a.out)
    elif a.action=='final-mac-receipt':
        if not a.local_deliverables:p.error('Local deliverables required')
        result=final_mac_receipt(a.local_deliverables,a.local_checkpoint,a.r2_receipt)
    elif a.action=='final-verify':
        if not a.pod or not a.run_dir or not a.receipt:p.error('Booked pod, run and final Mac receipt required')
        result=verify_final(a.pod,a.run_dir,a.receipt)
    elif a.action=='mac-receipt':
        if not a.local_checkpoint or not a.checkpoint_manifest:p.error('Local checkpoint and copied manifest required')
        result=mac_receipt(a.local_checkpoint,a.checkpoint_manifest)
    elif a.action=='bootstrap':
        if not a.pod or not a.run_id or not a.started_epoch:p.error('Booked pod, fresh run ID and original start epoch required')
        print(bootstrap(a.pod,a.run_id,a.started_epoch,volume_id=a.volume_id),end='');return 0
    else:
        if not a.pod or not a.run_dir:p.error('Explicit booked pod/run required')
        if a.action=='execute':return execute(a.pod,a.run_dir)
        if not a.python:p.error('Explicit warm --python required')
        print(emit(a.pod,a.run_dir,a.python),end='');return 0
    if a.out:write(a.out,result)
    else:print(json.dumps(result,indent=2,sort_keys=True))
    return 0

if __name__=='__main__':raise SystemExit(main())
