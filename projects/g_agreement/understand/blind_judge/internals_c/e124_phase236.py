"""E124 final operations/census pin, accounting234; original acquisition unchanged."""
import argparse
from pathlib import Path
from .transport import ROOT,HERE
from . import e124_channel
from .phase233 import complete_accounting,report_pin
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def census_scope(rows,call_ids,n=7042):
    require(len(rows)==len({r['id'] for r in rows})==n,'full unique registered custody census')
    eligible={r['id'] for r in rows if r.get('disposition')!='EXCLUDED_BY_REGISTERED_SOURCE_COHORT_NO_JUDGMENT'}
    require(eligible==set(call_ids) and len(eligible)==len(call_ids),'exact registered report/dispatch scope, no omitted or extra calls')
    for r in rows:
        require(r['classification']['seal_index']==5,'fixed original classification source slot')
        if r['id'] in eligible:
            require(r['context_terminal']['seal_index'] in (6,7) and r['model_terminal']['seal_index']==8,'fixed future literal terminal source slots')


def run(dest):
    source=HERE/'E124_OPERATIONS236_SOURCE_SEAL.json';profile=read(source)
    for n,h in profile['files'].items():require(sha(ROOT/n)==h,'prospective complete E124 operations source')
    a=read(dest/'ADMISSION.json');require(a['bank']=='E124' and a['E124_operations_source_seal_sha256']==sha(source),'source-bound separate lifetime3')
    report_pin(a,profile)
    census=Path(a['report_census_input_seal']);s=verify(census,a['report_census_input_sha256'])
    require(s['experiment']=='E124' and s['status']=='FROZEN_BEFORE_FIRST_CALL' and s['reference_sha256']=='61d87c57337064e297ccb6b183f9b6e6a647ac60c0940e5df18540fb4d6111c0','original pre-call report/reference census')
    census_scope(read(census.parent/'CENSUS.PRIVATE.json'),[x['id'] for x in read(dest/'CALLS.json')])
    job=dest/'outputs';job.mkdir(exist_ok=True)
    write(job/'E124_OPERATIONS_EXECUTION.json',dict(source_seal_sha256=sha(source),admission_sha256=sha(dest/'ADMISSION.json'),report_census_input_sha256=a['report_census_input_sha256'],policy='only original registered behavior references; full234 accounting; pre-call fixed report census/source slots, no analysis/old guard'))
    with complete_accounting(e124_channel):return e124_channel.run(dest)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase-directory',type=Path,required=True);run(p.parse_args().phase_directory)
