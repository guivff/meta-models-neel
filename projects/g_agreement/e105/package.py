"""Self-contained source-only E105 archive, built from sealed E101 predecessor."""
import argparse
import json
from pathlib import Path
import tarfile
from projects.g_agreement.e101.contract import read,write,sha
from .inputs import ROOT,HERE,frozen


def build(base_archive,out):
    f=frozen()
    if sha(base_archive)!=f['e101_archive_sha256']:raise ValueError('original E101 source archive')
    with tarfile.open(base_archive) as tar:
        payload={m.name:tar.extractfile(m).read() for m in tar.getmembers() if m.isfile()}
    base_seal='results/g_agreement/understand/e101/SOURCE_SEAL.json'
    import hashlib
    if hashlib.sha256(payload[base_seal]).hexdigest()!=f['e101_source_seal_sha256']:raise ValueError('E101 source seal')
    for name,h in json.loads(payload[base_seal])['files'].items():
        if hashlib.sha256(payload[name]).hexdigest()!=h:raise ValueError('original E101 source member')
    for p in HERE.iterdir():
        if p.suffix in ('.py','.json'):payload[str(p.relative_to(ROOT))]=p.read_bytes()
    seal=dict(experiment='E105',status='SOURCE_ONLY_INTEGRATOR_ADMISSION_REQUIRED',
        predecessor_source_sha256=f['e101_source_seal_sha256'],frozen_scorer_sha256=f['scorer_sha256'],
        files={n:hashlib.sha256(v).hexdigest() for n,v in sorted(payload.items())})
    seal_path=ROOT/'results/g_agreement/understand/e105/SOURCE_SEAL.json';write(seal_path,seal)
    payload[str(seal_path.relative_to(ROOT))]=seal_path.read_bytes()
    out.mkdir(parents=True,exist_ok=False);stage=out/'source';stage.mkdir()
    for name,data in payload.items():
        p=stage/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    archive=out/'source.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
        for name in sorted(payload):tar.add(stage/name,arcname=name,recursive=False)
    if archive.stat().st_size>20*1024*1024:raise ValueError('20MiB source archive cap')
    receipt=dict(experiment='E105',source_archive=str(archive.resolve()),source_archive_sha256=sha(archive),source_seal_sha256=sha(seal_path),
        bytes=archive.stat().st_size,GPU_calls=0,reader_calls=0,judge_calls=0)
    write(out/'SOURCE_ARCHIVE.json',receipt);return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base-archive',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(build(a.base_archive,a.out),indent=2))
