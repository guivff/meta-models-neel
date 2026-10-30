"""Prospective next-phase launcher with complete newly active bank accounting.

Existing executing processes are untouched. Every use requires a posted
operations-source pin in its new phase allocation.
"""
import argparse
from pathlib import Path
from . import registered
from . import e109_privacy
from .accounting_overlay import snapshot
from .transport import ROOT,HERE
from projects.g_agreement.readerbench.io import read,write,sha
from projects.g_agreement.readerbench.scoring import require


def run(dest):
    source=HERE/'OPERATIONS_SOURCE_SEAL.json'
    for name,digest in read(source)['files'].items():require(sha(ROOT/name)==digest,'prospective operations source pin')
    admission=read(dest/'ADMISSION.json')
    require(admission['operations_source_seal_sha256']==sha(source),'posted operations source allocation')
    registered.snapshot=snapshot
    job=dest/'outputs';job.mkdir(exist_ok=True)
    write(job/'OPERATIONS_EXECUTION.json',dict(source_seal_sha256=sha(source),admission_sha256=sha(dest/'ADMISSION.json'),
        policy='E99 active phase1 full150 residual included; old40usd root retained, no conditional400 inferred'))
    if admission['bank']=='E109':return e109_privacy.run(dest)
    return registered.run(dest)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase-directory',type=Path,required=True);a=p.parse_args();run(a.phase_directory)
