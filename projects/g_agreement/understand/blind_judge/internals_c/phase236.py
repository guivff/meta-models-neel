"""Prospective E118b owner-report pin; preserve original transport and wires."""
import argparse,subprocess
from pathlib import Path
from .transport import ROOT,HERE
from . import e118b_channel
from .phase233 import complete_accounting
from projects.g_agreement.readerbench.io import read,write,sha
from projects.g_agreement.readerbench.scoring import require


def unopened_report(receipt):
    require(receipt.get('experiment')=='E118' and receipt.get('part')=='b' and
            receipt.get('e118b_judgments_opened') is False and receipt.get('synthetic_tests',0)>0 and
            receipt.get('status')=='PRE_JUDGMENT','actual owner-tested pre-judgment report receipt')


def run(dest):
    source=HERE/'OPERATIONS236_SOURCE_SEAL.json';profile=read(source)
    for n,h in profile['files'].items():require(sha(ROOT/n)==h,'published whole prospective operations source')
    a=read(dest/'ADMISSION.json');require(a['bank']=='E118' and a['section236_operations_source_seal_sha256']==sha(source),'same-bank source-bound part-b operations')
    ref=a['report_adapter_source'];path=ROOT/ref['path']
    require(profile['files'].get(ref['path'])==ref['sha256']==sha(path) and
            subprocess.check_output(['git','show',ref['commit']+':'+ref['path']],cwd=ROOT)==path.read_bytes(),'exact published report receipt')
    receipt=read(path);unopened_report(receipt)
    require(a['report_adapter_tests_verified'] is True,'owner source tests verified')
    for n,h in receipt['files'].items():require(profile['files'].get(n)==h and sha(ROOT/n)==h,'complete original scientific dependency closure')
    job=dest/'outputs';job.mkdir(exist_ok=True)
    write(job/'SECTION236_OPERATIONS_EXECUTION.json',dict(source_seal_sha256=sha(source),admission_sha256=sha(dest/'ADMISSION.json'),report_adapter_source=ref,policy='original6790/wires/labels/unit/source transport unchanged; full accounting234; original E118 lifetime1 includes part a'))
    with complete_accounting(e118b_channel):return e118b_channel.run(dest)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase-directory',type=Path,required=True);run(p.parse_args().phase_directory)
