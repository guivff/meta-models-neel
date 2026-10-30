"""Freeze public E108 inputs and reuse the complete existing native runtime closure."""
import argparse,hashlib,json,shutil,tarfile
from pathlib import Path
from .runtime import ROOT
from contract import read,write,sha,verify,require

PUBLIC={'PUBLIC_INPUTS.json':'1b6969f6620114da6593e85939c65cff0396f9d936410658958062b4a4c27f7f',
        'PLACEBO_SPECS.json':'08e6d514950a26bb7a388a3dcc663fd60dca4528494668b997329d99848d662e'}


def source(out):
    legacy=ROOT/'results/g_agreement/understand/late198'
    s=verify(legacy,'SOURCE_SEAL.json',sha(legacy/'SOURCE_SEAL.json'))
    names=set(read(legacy/'DEPENDENCIES.json'))
    names|={str((legacy/n).relative_to(ROOT)) for n in s['files']}|{'results/g_agreement/understand/late198/SOURCE_SEAL.json'}
    names|={str(p.relative_to(ROOT)) for p in (ROOT/'projects/g_agreement/e108').glob('*.py')}
    names.add('results/g_agreement/understand/e76/common76.py')
    for n,h in read(legacy/'DEPENDENCIES.json').items():require(sha(ROOT/n)==h,'native dependency unchanged '+n)
    seal_path=ROOT/'results/g_agreement/understand/e108/runner/SOURCE_SEAL.json'
    seal_path.parent.mkdir(parents=True,exist_ok=True)
    write(seal_path,dict(experiment='E108',registered_seed=20261029,files={n:sha(ROOT/n) for n in sorted(names)}))
    names.add(str(seal_path.relative_to(ROOT)));dest=out/'source.tar.gz'
    with tarfile.open(dest,'w:gz') as tar:
        for n in sorted(names):tar.add(ROOT/n,arcname=n,recursive=False)
    require(dest.stat().st_size<20*1024*1024,'source20MiB cap')
    return dict(source_archive=str(dest.resolve()),source_archive_sha256=sha(dest),source_seal_sha256=sha(seal_path),source_seal_relative=str(seal_path.relative_to(ROOT)))


def build(public,out):
    out.mkdir(parents=True,exist_ok=False);inp=out/'inputs';inp.mkdir()
    for n,h in PUBLIC.items():
        require(sha(public/n)==h,'frozen W-text public bytes')
        shutil.copyfile(public/n,inp/n)
    write(inp/'STAGE_REQUEST.json',dict(experiment='E108',status='READY_E108_OPERATOR_ADMISSION_REQUIRED',cap_seconds=5400,cumulative_cap_seconds=5400,
        account_gate_USD=2500,seed=20261029,base_max_new_tokens=64,oracle_layer=44,nla_layer=42,base_batch=32,native_batch=32,
        frozen_public_files=PUBLIC,inventory_seal_sha256='978b99c39dba4ae0b4080376b3db59c98b846f042ae48c9454ced64c60837c55',timing_on_production_pod=True,
        source='standard E56/E57 late198 Runtime/native + E76 norm_match',labels_on_pod=False))
    write(inp/'INPUT_SEAL.json',dict(experiment='E108',files={p.name:sha(p) for p in inp.iterdir()}))
    from .worker import load
    load(inp,sha(inp/'INPUT_SEAL.json'))
    dest=out/'inputs.tar.gz'
    with tarfile.open(dest,'w:gz') as tar:tar.add(inp,arcname='inputs')
    require(dest.stat().st_size<20*1024*1024,'input20MiB cap')
    result=dict(experiment='E108',status='READY_RUNTIME_REQUIRES_I3_FRESH_OPERATOR_ADMISSION',
        public_archive=str(dest.resolve()),public_archive_sha256=sha(dest),input_sha256=sha(inp/'INPUT_SEAL.json'),
        input_root=str(inp.resolve()),native_items=1008,placebo_items=84,base_continuations=1008,reader_outputs=2184,
        labels_on_pod=False,GPU_calls=0,full_launch_allowed=False,**source(out))
    write(out/'DELIVERY.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--public',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    x=p.parse_args();print(json.dumps(build(x.public,x.out),indent=2))
