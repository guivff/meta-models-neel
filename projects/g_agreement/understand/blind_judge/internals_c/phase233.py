"""Prospective final admission wrapper; old bank/source bytes remain unchanged."""
import argparse
import subprocess
from contextlib import contextmanager
from pathlib import Path
from .transport import ROOT, HERE
from .accounting234 import snapshot
from . import e118b_channel, e124_channel
from projects.g_agreement.readerbench.io import read, write, sha
from projects.g_agreement.readerbench.scoring import require


@contextmanager
def complete_accounting(module):
    old = module.snapshot
    module.snapshot = snapshot
    try:
        yield
    finally:
        module.snapshot = old


def report_pin(admission, profile):
    ref = admission['report_adapter_source']
    require(profile['files'].get(ref['path']) == ref['sha256'], 'report receipt in whole operations source')
    path = ROOT/ref['path']
    require(sha(path) == ref['sha256'] and subprocess.check_output(
        ['git', 'show', ref['commit']+':'+ref['path']], cwd=ROOT) == path.read_bytes(), 'published exact report receipt')
    receipt = read(path)
    require(receipt.get('outputs_opened') is False and
            receipt.get('synthetic_tests', receipt.get('tests_passed', 0)) > 0 and
            admission['report_adapter_tests_verified'] is True, 'genuine prospective owner report/test receipt')
    for name, digest in receipt['files'].items():
        require(profile['files'].get(name) == digest and sha(ROOT/name) == digest, 'complete unchanged owner scientific dependency closure')


def run(dest):
    source = HERE/'OPERATIONS233_SOURCE_SEAL.json'
    profile = read(source)
    for name, digest in profile['files'].items(): require(sha(ROOT/name) == digest, 'whole prospective operations source')
    a = read(dest/'ADMISSION.json')
    require(a['section233_operations_source_seal_sha256'] == sha(source), 'published complete current operations admission')
    report_pin(a, profile)
    require(a['bank'] in ('E118', 'E124'), 'new consistency phases only')
    module = e118b_channel if a['bank'] == 'E118' else e124_channel
    job = dest/'outputs'; job.mkdir(exist_ok=True)
    write(job/'SECTION233_OPERATIONS_EXECUTION.json', dict(source_seal_sha256=sha(source),
        admission_sha256=sha(dest/'ADMISSION.json'), report_adapter_source=a['report_adapter_source'],
        policy='All prior physical/open exposure plus concrete E120/E121/E123/E124 allocations; no queued allowances'))
    with complete_accounting(module):
        return module.run(dest)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase-directory', type=Path, required=True)
    run(p.parse_args().phase_directory)
