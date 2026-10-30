"""Prospective complete E79B exposure for E123; original wires/code unchanged."""
import argparse
from pathlib import Path
from . import e123_channel as module
from .transport import HERE,ROOT
from .accounting_e79b import snapshot
from projects.g_agreement.readerbench.io import read,sha
from projects.g_agreement.readerbench.scoring import require


def run(dest):
    source=HERE/'E123_OPERATIONS_SOURCE_SEAL.json'
    for n,h in read(source)['files'].items():require(sha(ROOT/n)==h,'published whole current E123 operations')
    require(read(dest/'ADMISSION.json')['operations_source_seal_sha256']==sha(source),'posted complete global exposure operations')
    old=module.snapshot;module.snapshot=snapshot
    try:
        with module.worker(dest):return module.registered.run(dest)
    finally:module.snapshot=old


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase-directory',type=Path,required=True);run(p.parse_args().phase_directory)
