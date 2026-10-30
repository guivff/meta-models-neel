"""§155 frozen E44 input, pooled schedule and resource contracts."""
import hashlib
import json
import math
import random
import time
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
SEED=20261026
CAP=14400
PROGRAMME_CUTOFF=1793314740
CHECKPOINTS=(0,25,100,400)

def read(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(s) for s in Path(p).read_text().splitlines() if s.strip()]
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def dump(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n')
def jsonl(p,v):Path(p).write_text(''.join(json.dumps(x,sort_keys=True,allow_nan=False)+'\n' for x in v))
def plan():return read(HERE/'PLAN.json')
ROWS=tuple(plan()['rows']);CONTENT=tuple(plan()['content_rows']);STRUCTURE=tuple(plan()['structure_rows'])
def seal(directory,name='INPUT_SEAL.json',names=None):
    directory=Path(directory);names=names or sorted(p.name for p in directory.iterdir() if p.is_file() and p.name!=name)
    dump(directory/name,{'files':{n:sha(directory/n) for n in names}})
def verify(directory,name='INPUT_SEAL.json'):
    directory=Path(directory).resolve();s=read(directory/name)
    if not s.get('files'):raise ValueError('nonempty sealed file map required')
    for n,h in s['files'].items():
        p=(directory/n).resolve()
        if not p.is_relative_to(directory) or sha(p)!=h:raise ValueError('sealed bytes differ')
    return s

def cache_output(p):
    p=Path(p).resolve()
    if 'cache' not in p.parts:raise ValueError('large artifacts belong in cache')
    p.mkdir(parents=True,exist_ok=False);return p

def training_schedule(records):
    if (len(records)!=756 or len({r['id'] for r in records})!=756
            or {r['feature'] for r in records}!=set(CONTENT)
            or any(sum(r['feature']==f for r in records)!=84 for f in CONTENT)
            or any(set(r)!={'id','feature','y','cluster'} or r['y'] not in (0,1) for r in records)):
        raise ValueError('exact nine-row labelled content dev pool required')
    rng=random.Random(SEED);deck=[];result=[]
    for step in range(400):
        batch=[]
        for j in range(8):
            if not deck:deck=list(range(756));rng.shuffle(deck)
            item=records[deck.pop()]
            batch.append({k:item[k] for k in ('id','feature','y')}|{'phrasing':(step*8+j)%2})
        result.append(batch)
    return result

def worker_input(path):
    path=Path(path);s=verify(path)
    if {p.relative_to(path).as_posix() for p in path.rglob('*') if p.is_file()}!=set(s['files'])|{'INPUT_SEAL.json'}:
        raise ValueError('only sealed label-free worker files allowed')
    if any('DO_NOT_STAGE' in n for n in s['files']):raise ValueError('private test key on worker')
    from prepare_inputs import BANK_SEAL,CANDIDATES_HASH
    v=read(path/'provenance.json')
    if (v['source_bank_seal']!=BANK_SEAL or v['source_candidates_sha256']!=CANDIDATES_HASH
            or v['plan_sha256']!=sha(HERE/'PLAN.json')
            or v.get('e39_bound_input_seal_sha256')!=plan()['e39_bound_input_seal_sha256']
            or v.get('shared_e39_tensors_bit_exact') is not True
            or not v.get('source_capture_seals')):raise ValueError('same E36/E39 bank and captures required')
    return s

def assignment(a,now=None):
    now=time.time() if now is None else now
    if (a.get('issuer')!='integrator' or a.get('experiment')!='E44' or a.get('pod_count')!=1 or a.get('slot')!=0
            or a.get('runs')!=[['pooled_content','C']] or not a.get('pod_id')
            or a.get('plan_sha256')!=sha(HERE/'PLAN.json')
            or a.get('target_mapping_sha256')!=sha(HERE/'LORA_TARGETS.json')
            or a.get('source_published') is not True or a.get('external_hardstop_verified') is not True):
        raise ValueError('published single-pod pooled E44 assignment required')
    for k in ('allocated_gpu_seconds','previous_gpu_seconds','provider_created_epoch','deadline_epoch'):
        if type(a.get(k)) not in (int,float) or not math.isfinite(a[k]):raise ValueError('finite budget fields required')
    if (a['previous_gpu_seconds']!=0 or not 180<a['allocated_gpu_seconds']<=CAP
            or not a['provider_created_epoch']<=now<a['deadline_epoch']-180
            or a['deadline_epoch']>min(a['provider_created_epoch']+a['allocated_gpu_seconds'],PROGRAMME_CUTOFF)):
        raise ValueError('provider cap/clock contract violated')
    return a

def forecast_admission(f,now):
    remaining=f['forecast_remaining_seconds'];elapsed=now-f['science_started_epoch']
    if not math.isfinite(remaining) or remaining<=0 or elapsed<0:raise ValueError('invalid warmed forecast')
    science=min(1.5*(remaining+elapsed)+360,10800)
    deadline=min(f['science_started_epoch']+science,f['provider_deadline_epoch']-180)
    return {'status':'ADMIT_FULL_GRID' if 1.5*remaining<=deadline-now else 'NO_FIT_STOP',
        'science_seconds':science,'science_deadline_epoch':deadline,'forecast_remaining_seconds':remaining,
        'setup_and_parity_included':True,'clock_resets':0}
