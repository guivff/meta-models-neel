"""R2-B volume-only launch gates, declared writes and verified final release.

No allocation, SSH, downloads, stop or terminate API. Stage backends must call
LiveGuard before every model operation and use RunWriter for every output.
"""
from __future__ import annotations
import hashlib,json,math,os,re,time
from pathlib import Path
from projects.g_agreement.r_bench import remainder_r2b as D

TOTAL=16200
SEGMENT=TOTAL
NETWORK_VOLUME="w9182om1pd"
MIN_PULL=300


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def validate_booking(b,now,science=True):
    if b.get('experiment')!='R2-B' or b.get('confirmed_by')!='integrator' or not b.get('handoff_line'):
        raise ValueError('Missing integrator R2-B booking')
    if b.get('gpu_count') != 1 or isinstance(b.get('gpu_count'),bool):
        raise ValueError(f'Invalid gpu_count: {b.get("gpu_count")} (one GPU only)')
    if b.get('network_volume_id') != NETWORK_VOLUME:
        raise ValueError(f'Invalid network_volume_id: {b.get("network_volume_id")}')
    for field in ('pod','network_volume_id','segment_id'):
        if not re.fullmatch('[A-Za-z0-9_-]{1,80}',str(b.get(field,''))):raise ValueError(f'Invalid {field}: {b.get(field)}')
    for key in ('allocation_start','segment_start','segment_deadline','pull_reserve'):
        if isinstance(b.get(key),bool) or not isinstance(b.get(key),(int,float)) or not math.isfinite(b[key]):
            raise ValueError(f'Invalid booking {key}')
    start,seg,end=b['allocation_start'],b['segment_start'],b['segment_deadline']
    if not start<=seg<=now<end or end-seg>SEGMENT or end-start>TOTAL:
        raise ValueError('Immutable allocation/segment deadline exceeded')
    if b['pull_reserve']<MIN_PULL or (science and end-now<=b['pull_reserve']):
        raise ValueError('Pull reserve reached/invalid')
    return b


def validate_registration(r,manifest):
    if r.get('section')!=36 or not r.get('pushed_before_compute') or not re.fullmatch('[0-9a-f]{40}',r.get('prereg_commit','')):
        raise ValueError('Missing pushed section36 preregistration')
    if r.get('manifest_sha256')!=D.digest(manifest):raise ValueError('Unregistered manifest changed')


def validate_volume(b,receipt):
    for key in ('pod','network_volume_id'):
        if receipt.get(key)!=b[key]:raise ValueError(f'Wrong volume receipt {key}: {receipt.get(key)}')
    if receipt.get('http_status')!=200 or not receipt.get('mounted'):
        raise ValueError('Volume account HTTP200/mount proof missing')


def validate_guard_process(pid,cmd,log,pod,kind):
    script={'watchdog':'ws2_watchdog.sh','hardstop':'ws2_hardstop.sh'}[kind]
    if pid<=1 or script not in cmd or pod not in cmd.split():
        raise ValueError(f'Wrong {kind} process {pid}: {cmd}')
    if 'armed:' not in log or 'check http 200' not in log or pod not in log:
        raise ValueError(f'Missing {kind} armed HTTP200 proof')


def validate_custody(booking,receipt):
    if receipt.get('pod')!=booking['pod'] or receipt.get('segment_id')!=booking['segment_id']:
        raise ValueError(f'Wrong custody pod/segment: {receipt}')
    if receipt.get('confirmed_by')!='integrator' or not receipt.get('handoff_line') or receipt.get('previous_guards_retired') is not True:
        raise ValueError(f'Incomplete custody acknowledgement: {receipt}')


def measured_reserve(booking,proof):
    rate=proof.get('bytes_per_second',0)
    if proof.get('pod')!=booking['pod'] or proof.get('bytes',0)<8*1024*1024 or not isinstance(rate,(int,float)) or not math.isfinite(rate) or rate<=0:
        raise ValueError(f'Invalid bandwidth proof: pod={proof.get("pod")}, rate={rate}')
    if not booking['allocation_start']<=proof.get('measured_epoch',0)<=time.time():
        raise ValueError(f'Stale bandwidth proof: {proof.get("measured_epoch")}')
    if not re.fullmatch('[0-9a-f]{64}',proof.get('sha256','')):raise ValueError('Invalid bandwidth checksum')
    # Conservative 1GiB compact-result allowance, enlarged if measured rate is low.
    return max(booking['pull_reserve'],math.ceil(1.5*1024**3/rate+60))


class LiveGuard:
    def __init__(self,run,science=True):
        self.science=science
        self.run=Path(run)
        if not re.fullmatch(r'/workspace/remainder/r2b/[A-Za-z0-9_-]{1,80}',str(self.run)):
            raise ValueError(f'Invalid private run directory: {self.run}')
        self.raw=(self.run/'booking.json').read_bytes();self.booking=json.loads(self.raw)
        self.registration=json.loads((self.run/'registration.json').read_text())
        self.manifest=json.loads((self.run/'manifest.json').read_text())
        validate_registration(self.registration,self.manifest)
    def __call__(self):
        if (self.run/'booking.json').read_bytes()!=self.raw:raise ValueError('Booking changed')
        if D.digest(json.loads((self.run/'manifest.json').read_text()))!=D.digest(self.manifest):raise ValueError('Manifest changed')
        b=validate_booking(self.booking,time.time(),science=self.science)
        self.pull_reserve=measured_reserve(b,json.loads((self.run/'bandwidth.json').read_text()))
        if self.science and b['segment_deadline']-time.time()<=self.pull_reserve:raise ValueError('Measured pull reserve reached')
        ids=[v.split(b'=',1)[1].decode() for v in Path('/proc/1/environ').read_bytes().split(b'\0') if v.startswith(b'RUNPOD_POD_ID=')]
        if ids!=[b['pod']]:raise ValueError(f'Native pod mismatch: {ids}')
        if not os.path.ismount('/workspace') or self.run.stat().st_dev!=Path('/workspace').stat().st_dev:
            raise ValueError('Run is not on mounted volume')
        validate_volume(b,json.loads((self.run/'volume.json').read_text()))
        validate_custody(b,json.loads((self.run/'custody.json').read_text()))
        for kind in ('watchdog','hardstop'):
            pid=int((self.run/(kind+'.pid')).read_text());os.kill(pid,0)
            cmd=Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0',b' ').decode()
            validate_guard_process(pid,cmd,(self.run/(kind+'.log')).read_text(),b['pod'],kind)


def cell_key(cell):
    return D.digest(cell)


def declared_outputs(manifest):
    """All scientific writes derive from cells and their requested tap indices."""
    out={'rows.jsonl','process.json','volume_manifest.json'}
    for cell in manifest['cells']:
        key=cell_key(cell)
        for block in cell.get('tap_blocks',[]):out.add(f'states/{key}/tap{block}.npy')
    return out


class RunWriter:
    def __init__(self,parent,manifest,process):
        self.manifest=manifest;self.process=process;self.allowed=declared_outputs(manifest)
        # New process cannot append to another process or to real smoke directories.
        self.root=Path(parent)/process['run_kind']/hashlib.sha256(process['run_id'].encode()).hexdigest()
        self.root.mkdir(parents=True,exist_ok=False)
        self.expected={cell_key(c):c for c in manifest['cells']}
        if len(self.expected)!=len(manifest['cells']):raise ValueError('Duplicate manifest cell')
        self.seen=set()
        self.write_json('process.json',process)
    def path(self,name):
        if name not in self.allowed:raise ValueError(f'Undeclared write: {name}')
        p=self.root/name
        if not p.resolve().is_relative_to(self.root.resolve()):raise ValueError(f'Escaped write: {name}')
        p.parent.mkdir(parents=True,exist_ok=True);return p
    def write_json(self,name,obj):self.path(name).write_text(json.dumps(obj,allow_nan=False,indent=2)+'\n')
    def append(self,cell,payload,arrays):
        import numpy as np
        key=cell_key(cell)
        if key not in self.expected:raise ValueError(f'Unexpected cell: {cell}')
        if key in self.seen:raise ValueError(f'Duplicate cell: {cell}')
        if set(arrays)!=set(cell.get('tap_blocks',[])):raise ValueError(f'Tap coverage differs: {cell}')
        if set(payload)&set(self.process):raise ValueError(f'Payload overrides provenance: {cell}')
        paths={}
        for layer,array in arrays.items():
            if array.ndim!=1 or array.dtype!=np.float16 or not np.isfinite(array).all():raise ValueError(f'Invalid compact state: {cell}, block{layer}')
            name=f'states/{key}/tap{layer}.npy';np.save(self.path(name),array,allow_pickle=False)
            paths[str(layer)]={'path':name,'sha256':sha(self.root/name),'shape':list(array.shape),'dtype':'float16'}
        row=dict(payload,cell=cell,cell_key=key,state_files=paths,**self.process)
        with self.path('rows.jsonl').open('a') as f:f.write(json.dumps(row,allow_nan=False)+'\n')
        self.seen.add(key)
    def finish(self):
        missing=set(self.expected)-self.seen
        if missing:raise ValueError(f'Missing cells: {[self.expected[k] for k in sorted(missing)]}')
        actual={str(p.relative_to(self.root)) for p in self.root.rglob('*') if p.is_file()}
        extra=actual-self.allowed
        if extra:raise ValueError(f'Undeclared files: {sorted(extra)}')
        files={name:sha(self.root/name) for name in sorted(actual)}
        self.write_json('volume_manifest.json',dict(files=files,manifest_sha256=D.digest(self.manifest),**self.process))
        return files


def verified_release(booking,mac_receipt,volume_manifest,volume_root,guard,write_receipt):
    """Validate compact pull + retained-state bytes; never stop or kill guards."""
    guard()
    if mac_receipt.get('verified_on') !='Mac':raise ValueError(f'Wrong receipt origin: {mac_receipt.get("verified_on")}')
    if mac_receipt.get('pod')!=booking['pod'] or mac_receipt.get('network_volume_id')!=booking['network_volume_id']:
        raise ValueError('Wrong Mac receipt pod/volume')
    if mac_receipt.get('volume_manifest_sha256')!=D.digest(volume_manifest):raise ValueError('Mac receipt not bound to states')
    for name,want in volume_manifest['files'].items():
        p=Path(volume_root)/name
        if not p.resolve().is_relative_to(Path(volume_root).resolve()):raise ValueError(f'Unsafe manifest path: {name}')
        if sha(p)!=want:raise ValueError(f'Volume checksum mismatch: {name}')
    # Caller supplies compact file set from its enumerated package, not a boolean.
    if not mac_receipt.get('compact_files') or mac_receipt.get('compact_files')!=volume_manifest.get('compact_files'):
        raise ValueError('Mac compact file map differs')
    expected={n for n in volume_manifest['files'] if n.startswith('outputs/')}
    if expected:
        actual={str(p.relative_to(volume_root)) for p in (Path(volume_root)/'outputs').rglob('*') if p.is_file()}
        if actual!=expected:raise ValueError(f'Changed volume inventory: {sorted(actual^expected)}')
    guard()
    result=dict(status='VERIFIED_READY_TO_STOP',pod=booking['pod'],network_volume_id=booking['network_volume_id'],
                volume_manifest_sha256=D.digest(volume_manifest),custody_transferred=False,guards_retained=True)
    write_receipt(result)
    return result
