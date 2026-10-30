"""Seal runner plus existing dependencies; source-only staging archive."""
import argparse,tarfile
from pathlib import Path
from .contract import read,write,sha
ROOT=Path(__file__).resolve().parents[3]

def build(out):
    paths=set(read(ROOT/'results/g_agreement/understand/e79/DEPENDENCIES.json'))
    paths.add('results/g_agreement/understand/e79/worker.py')
    for folder in ('projects/g_agreement/e101','results/g_agreement/understand/late198'):
        paths.update(str(p.relative_to(ROOT)) for p in (ROOT/folder).glob('*.py'))
    seal=ROOT/'results/g_agreement/understand/e101/SOURCE_SEAL.json'
    write(seal,dict(experiment='E101',status='CODE_SEALED_INPUT_BINDING_PENDING',authority=['69f8c08e4','2bdde763'],
        full_continuation_authority='direct user ruling',files={n:sha(ROOT/n) for n in sorted(paths)}))
    out.mkdir(parents=True,exist_ok=False);archive=out/'source.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
        for n in sorted(paths|{str(seal.relative_to(ROOT))}):tar.add(ROOT/n,arcname=n,recursive=False)
    write(out/'PACKAGE.json',dict(source_seal_sha256=sha(seal),archive_sha256=sha(archive),archive=str(archive),bytes=archive.stat().st_size))
    print(sha(seal),sha(archive),archive.stat().st_size)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.out)
