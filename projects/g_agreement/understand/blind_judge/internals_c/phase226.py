"""Prospective next-phase launcher with separately allocated §226 banks included."""
import argparse
from pathlib import Path
from . import phase_run
from .accounting226 import snapshot
from .transport import ROOT, HERE
from projects.g_agreement.readerbench.io import read, write, sha
from projects.g_agreement.readerbench.scoring import require


def run(dest):
    source = HERE/'ACCOUNTING226_SOURCE_SEAL.json'
    for name, digest in read(source)['files'].items():
        require(sha(ROOT/name) == digest, 'prospective section226 operations source')
    require(read(dest/'ADMISSION.json')['section226_operations_source_seal_sha256'] == sha(source),
            'published complete section226 accounting admission')
    job = dest/'outputs'
    job.mkdir(exist_ok=True)
    write(job/'SECTION226_OPERATIONS_EXECUTION.json', dict(source_seal_sha256=sha(source),
        admission_sha256=sha(dest/'ADMISSION.json'), policy='Separate E100e3/E1142 actual OPEN allocations included; no queued allowances'))
    previous = phase_run.snapshot
    phase_run.snapshot = snapshot
    try:
        return phase_run.run(dest)
    finally:
        phase_run.snapshot = previous


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase-directory', type=Path, required=True)
    run(p.parse_args().phase_directory)
