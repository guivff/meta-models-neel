"""Seal runnable E105 source separately from B's immutable input/source package."""
import argparse,json,tarfile,tempfile
from pathlib import Path
from .contract import write,sha,verify
from .package104 import source_paths,ROOT
from .preflight105 import runtime_import


def build(out):
    paths=source_paths()
    paths.update(str(p.relative_to(ROOT)) for p in (ROOT/'projects/g_agreement/e105').iterdir() if p.suffix in ('.py','.json'))
    out.mkdir(parents=True,exist_ok=False)
    seal_path='results/g_agreement/understand/e105/runner/SOURCE_SEAL.json'
    seal=out/'SOURCE_SEAL.json'
    write(seal,dict(experiment='E105',authority=['214','06823691'],files={n:sha(ROOT/n) for n in sorted(paths)}))
    archive=out/'source.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
        for name in sorted(paths):tar.add(ROOT/name,arcname=name,recursive=False)
        tar.add(seal,arcname=seal_path,recursive=False)
    with tempfile.TemporaryDirectory() as tmp:
        extracted=Path(tmp)
        with tarfile.open(archive) as tar:tar.extractall(extracted,filter='data')
        verify(extracted,seal_path,sha(seal));check=runtime_import(extracted)
    write(out/'RUNTIME_IMPORT_PREFLIGHT.json',check)
    dest=ROOT/seal_path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(seal.read_bytes())
    receipt=dict(experiment='E105',source_seal_path=seal_path,source_seal_sha256=sha(seal),
                 archive=str(archive),archive_sha256=sha(archive),bytes=archive.stat().st_size,
                 runtime_import_status='PASS',runtime_import_preflight=check,GPU_calls=0,reader_calls=0,judge_calls=0)
    write(out/'PACKAGE.json',receipt);return receipt

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.out),indent=2))
