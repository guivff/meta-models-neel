"""Exact I-2 operational cap overlay. No worker edits, provider or model calls."""
import difflib
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

HERE=Path(__file__).resolve().parent
WORKER=None  # Explicit --worker checkout, never inferred from user files.
COMMIT='275d102342788330fe8190edc6a4865d7cf53dcc'
AUTHORITY='b81c6c9d7b7ec319d611ca3caea31ace8457e0d7'
OLD_AUTHORITY='f5720c36529f52bf506924fa73825df8b4c95d9e'
ORIGINAL_SHA='8456813c1bd271dea9be1154db9a14ab5932b2a0cfb57ebad52f7f6d46093731'
META='results/g_agreement/e74/operator/resident-v6-c7/'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def encoded(obj):return (json.dumps(obj,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
def blob(path):return subprocess.check_output(['git','show',COMMIT+':'+path],cwd=WORKER)
def replace_once(raw,old,new):
    assert raw.count(old)==1,old
    return raw.replace(old,new)

def build():
    original=WORKER/'results/g_agreement/e74/staging/e74-resident-v6-c7.tar.gz'
    original_raw=original.read_bytes();assert len(original_raw)==1406962 and sha(original_raw)==ORIGINAL_SHA
    package=json.loads(blob(META+'PACKAGE.json'))
    with tarfile.open(fileobj=io.BytesIO(original_raw),mode='r:gz') as tar:
        entries=tar.getmembers();assert len(entries)==len(package['members'])
        assert len({m.name for m in entries})==len(entries)
        assert all(m.isfile() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts and m.size<=20_000_000 for m in entries)
        members={m.name:tar.extractfile(m).read() for m in entries}
    assert {n:sha(r) for n,r in members.items()}==package['members']
    before=dict(members)
    name='projects/g_agreement/e74/hardware.py'
    assert members[name]==blob(name)
    text=members[name].decode()
    text=replace_once(text,OLD_AUTHORITY,AUTHORITY)
    text=replace_once(text,'TP8 clarification7 limit binding required','TP8 clarification8 limit binding required')
    text=replace_once(text,"return {'boot_smoke_seconds':3000, 'cap_usd':120}","return {'boot_smoke_seconds':3000, 'cap_usd':160}")
    members[name]=text.encode()
    testname='projects/g_agreement/e74/test_hardware.py'
    text=members[testname].decode()
    for old,new in [
        ('cap_usd=120,limit_authority','cap_usd=160,limit_authority'),
        ("{'boot_smoke_seconds':3000,'cap_usd':120}","{'boot_smoke_seconds':3000,'cap_usd':160}"),
        ("ops.budget(a,96,NOW)['forecast_times_1_25_usd'],120","ops.budget(a,128,NOW)['forecast_times_1_25_usd'],160"),
        ('ops.budget(a,96.01,NOW)','ops.budget(a,128.01,NOW)'),
        ("cm.exception.evidence['cap_usd'],120","cm.exception.evidence['cap_usd'],160"),
        ('ops.budget(dict(b,cap_usd=120),0,NOW)','ops.budget(dict(b,cap_usd=160),0,NOW)'),
    ]:text=replace_once(text,old,new)
    members[testname]=text.encode()
    seal=json.loads(members['SOURCE_SEAL.json'])
    assert seal['files']=={n:sha(r) for n,r in before.items() if n!='SOURCE_SEAL.json'}
    seal['files']={n:sha(r) for n,r in sorted(members.items()) if n!='SOURCE_SEAL.json'}
    members['SOURCE_SEAL.json']=encoded(seal)
    changed=sorted(n for n in members if members[n]!=before[n])
    assert changed==['SOURCE_SEAL.json',name,testname]
    # No inputs/fixtures are decoded; their immutable bytes are copied and hashed.
    archive=HERE/'e74-resident-v6-c8-cap160.tar.gz'
    with archive.open('xb') as f,gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as tar:
        for n,raw in sorted(members.items()):
            m=tarfile.TarInfo(n);m.size=len(raw);m.mode=0o600;tar.addfile(m,io.BytesIO(raw))
    assert archive.stat().st_size<=20_000_000 and sum(map(len,members.values()))<=20_000_000
    source_sha=sha(members['SOURCE_SEAL.json'])
    (HERE/'SOURCE_SEAL.json').write_bytes(members['SOURCE_SEAL.json'])
    for n in ('H200_FORECAST.json','CPU_SOURCE_SEAL.json'):
        (HERE/('BASELINE_'+n)).write_bytes(blob(META+n))
    admission=json.loads(blob(META+'H200_ADMISSION_TEMPLATE.json'))
    admission.update(cap_usd=160,limit_authority=AUTHORITY,source_seal_sha256=source_sha)
    (HERE/'H200_ADMISSION_TEMPLATE.json').write_bytes(encoded(admission))
    request=json.loads(blob(META+'H200_RESIDENT_REQUEST_TEMPLATE.json'));request['source_seal_sha256']=source_sha
    (HERE/'H200_RESIDENT_REQUEST_TEMPLATE.json').write_bytes(encoded(request))
    package.update(status='BUILT_CPU_TESTS_PENDING_NOT_ADMITTED',
        archive={'path':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive.read_bytes())},
        source_seal_sha256=source_sha,cpu_test_receipt_sha256=None,
        members={n:sha(r) for n,r in sorted(members.items())},
        original_worker_commit=COMMIT,original_archive_sha256=ORIGINAL_SHA,
        operational_limit_authority=AUTHORITY,changed_archive_members=changed,
        replaces_operationally='Clarification8 cap enforcement only; original275d1023 archive is preserved')
    (HERE/'PACKAGE.json').write_bytes(encoded(package))
    patches=[]
    for n in (name,testname):
        patches.extend(difflib.unified_diff(before[n].decode().splitlines(True),members[n].decode().splitlines(True),fromfile='275d1023/'+n,tofile='I2-cap160/'+n))
    (HERE/'OPERATIONAL_OVERLAY.patch').write_text(''.join(patches))
    (HERE/'BUILD_PROVENANCE.json').write_bytes(encoded({'original_worker_commit':COMMIT,'original_archive_sha256':ORIGINAL_SHA,
        'authority':AUTHORITY,'archive_sha256':package['archive']['sha256'],'source_seal_sha256':source_sha,
        'changed_archive_members':changed,'unchanged_archive_members':{n:sha(raw) for n,raw in before.items() if n not in changed},
        'hardware_forecast_sha256':sha(blob(META+'H200_FORECAST.json')),'forecast_durations_and_costs_changed':False,
        'boot_smoke_cap_seconds':3000,'tp4_cap_usd':100,'tp8_cap_usd':160,'labels_opened':False,
        'gpu_calls':0,'provider_calls':0,'worker_files_changed':False}))
    print(json.dumps({'archive':package['archive'],'source_seal_sha256':source_sha,'changed_archive_members':changed},sort_keys=True))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--worker',type=Path,required=True);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();WORKER=args.worker.resolve(strict=True);HERE=args.out.resolve()
    HERE.mkdir(mode=0o700,parents=True,exist_ok=False);build()
