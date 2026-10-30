"""Freeze and rehearse the complete E104 runtime, including top-level common/."""
import argparse,shutil,tarfile,tempfile
from pathlib import Path
from .contract import read,write,sha,verify
from .preflight104 import runtime_import
ROOT=Path(__file__).resolve().parents[3]
HERE=ROOT/'results/g_agreement/understand/e104/runner'


def source_paths():
    index='results/g_agreement/understand/e79/DEPENDENCIES.json'
    paths=set(read(ROOT/index));paths.add(index)
    paths.add('results/g_agreement/understand/e79/worker.py')
    for folder in ('projects/g_agreement/e101','results/g_agreement/understand/late198'):
        paths.update(str(p.relative_to(ROOT)) for p in (ROOT/folder).glob('*.py'))
    # blindspot/__init__.py imports this top-level package during model setup.
    paths.update(str(p.relative_to(ROOT)) for p in (ROOT/'common').rglob('*') if p.is_file() and p.suffix in ('.py','.sh'))
    if 'common/__init__.py' not in paths:raise ValueError('missing top-level common package')
    capture_seal=ROOT/'results/g_agreement/understand/e104/vectors/SOURCE_SEAL.json'
    paths.update(read(capture_seal)['files']);paths.add(str(capture_seal.relative_to(ROOT)))
    paths.update(('projects/g_agreement/readerbench/io.py','projects/g_agreement/readerbench/scoring.py'))
    for n in list(paths):
        for parent in (ROOT/n).parents:
            if parent==ROOT:break
            init=parent/'__init__.py'
            if init.exists():paths.add(str(init.relative_to(ROOT)))
    return paths


def build(out,name='SOURCE_SEAL.json',replace_seal=False):
    if Path(name).name!=name or not name.endswith('.json'):raise ValueError('source seal filename')
    final_seal=HERE/name
    if final_seal.exists() and not replace_seal:raise FileExistsError('use --replace-seal to explicitly reseal an existing source filename')
    paths=source_paths();out.mkdir(parents=True,exist_ok=False)
    local_seal=out/name
    write(local_seal,dict(experiment='E104',authority=['5e075c6af','853d1936a','06823691'],seed=20261029,
        original_E79_worker_sha256=sha(ROOT/'results/g_agreement/understand/e79/worker.py'),files={n:sha(ROOT/n) for n in sorted(paths)}))
    archive=out/'source.tar.gz';seal_name=str(final_seal.relative_to(ROOT))
    with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
        for n in sorted(paths):tar.add(ROOT/n,arcname=n,recursive=False)
        tar.add(local_seal,arcname=seal_name,recursive=False)
    # Never publish a READY package based only on --help or tests with mocked loaders.
    with tempfile.TemporaryDirectory() as tmp:
        extracted=Path(tmp)
        with tarfile.open(archive) as tar:tar.extractall(extracted,filter='data')
        verify(extracted,seal_name,sha(local_seal));rehearsal=runtime_import(extracted)
    rehearsal.update(archive_sha256=sha(archive),source_seal_sha256=sha(local_seal))
    write(out/'RUNTIME_IMPORT_PREFLIGHT.json',rehearsal)
    HERE.mkdir(parents=True,exist_ok=True);shutil.copyfile(local_seal,final_seal)
    receipt=dict(experiment='E104',source_seal_path=seal_name,source_seal_sha256=sha(local_seal),archive=str(archive),
        archive_sha256=sha(archive),bytes=archive.stat().st_size,runtime_import_preflight=str(out/'RUNTIME_IMPORT_PREFLIGHT.json'),
        runtime_import_preflight_sha256=sha(out/'RUNTIME_IMPORT_PREFLIGHT.json'),runtime_import_status='PASS',GPU_calls=0)
    write(out/'PACKAGE.json',receipt)
    return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--seal-name',default='SOURCE_SEAL.json')
    p.add_argument('--replace-seal',action='store_true');a=p.parse_args();print(build(a.out,a.seal_name,a.replace_seal))
