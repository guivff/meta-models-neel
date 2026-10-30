"""Published E120a operations entry; same E120 cumulative cap and full current accounting."""
import argparse
from pathlib import Path
from . import e120a_channel as module
from .transport import ROOT,HERE
from projects.g_agreement.readerbench.io import read,sha
from projects.g_agreement.readerbench.scoring import require

def run(dest):
    source=HERE/'E120a_SOURCE_SEAL.json'
    for n,h in read(source)['files'].items():require(sha(ROOT/n)==h,'published E120a whole source')
    require(read(dest/'ADMISSION.json')['operations_source_seal_sha256']==sha(source),'posted same original lifetime source')
    with module.worker(dest):return module.registered.run(dest)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase-directory',type=Path,required=True);run(p.parse_args().phase_directory)
