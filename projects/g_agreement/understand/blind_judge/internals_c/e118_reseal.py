"""CPU-only seal repair after all252 saved/settled E118 calls; NEVER dispatch."""
import argparse
import json
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from .runner import CACHE
from .transport import ROOT,HERE,SHARED
from .accounting import bank_actual
from ..dispatch_lock import dispatch_lock
from ..operational217 import audit_response
from .. import funded_queue
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def bindings(terminals,calls,audits,ledger):
    by={x['id']:x for x in calls};audit={x['request_id']:x for x in audits}
    require(len(by)==len(calls)==len(terminals)==len(audit)==len(audits) and
            set(by)=={x['id']for x in terminals} and len({x['request_id']for x in terminals})==len(terminals),
            'complete unique saved calls/terminals/audits')
    result=[]
    for t in terminals:
        call=by[t['id']];require(t['phase']==call['phase']=='judging','frozen wire phase, not directory label')
        p=ledger/('E118_'+call['phase'])/(t['request_id']+'.response.json')
        require(p.exists() and sha(p)==t['response_sha256'] and
                audit[t['request_id']]['response_sha256']==sha(p),'original physical file/request/terminal/audit hashes agree')
        result.append(dict(path=str(p),sha256=sha(p)))
    return result


def repair():
    receipt=HERE/'E118_RESEAL_SOURCE_SEAL.json'
    for name,digest in read(receipt)['files'].items():require(sha(ROOT/name)==digest,'published CPU repair source')
    original=HERE/'E118_SOURCE_SEAL.json';require(sha(original)==read(receipt)['original_E118_source_seal_sha256'],'unchanged frozen prompt/source receipt')
    for name,digest in read(original)['files'].items():require(sha(ROOT/name)==digest,'original pre-call scientific/transport source unchanged')
    dest=CACHE/'E118/consistency_judging';source=verify(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'));job=dest/'outputs'
    require(source['experiment']=='E118','E118 only')
    final=job/'JUDGMENT_SEAL.json'
    if final.exists():return verify(final,sha(final))
    with dispatch_lock(SHARED/'E118/DISPATCH.lock'):
        terminals=read(job/'RESPONSES.json');calls=read(dest/'CALLS.json');audits=read(job/'ROUTE_AUDIT.json')['requests']
        require(len(terminals)==len(calls)==252 and read(job/'COUNTS.json')['n']==252,'all252 completed before repair')
        refs=bindings(terminals,calls,audits,SHARED/'E118/ledger')
        ids={x['request_id']for x in terminals};book=read(job/'COUNTS.json')['cost']
        events=[json.loads(s)for s in (SHARED/'E118/ledger/ledger.jsonl').read_text().splitlines()if s]
        require({x['id']for x in events if x['event']=='reserve'}=={x['id']for x in events if x['event']=='settle'}==ids,
                'exact252 original reservations all settled, no unknown or guessed reconciliation')
        actual,unknown=bank_actual(SHARED/'E118/ledger');require(unknown==0 and actual==Decimal(book['actual_usd'])<=1,'exact settled known charges')
        _,(_,_,protocol,_)=funded_queue.route_api()
        for ref,t,a in zip(refs,terminals,audits):
            require(t['input_sha256']==sha(dest/'INPUT_SEAL.json'),'original source-bound terminal')
            check=dict(audit_response(read(ref['path']),protocol),request_id=t['request_id'],response_sha256=ref['sha256'])
            require(check==a,'unchanged original route/cost/finish audit')
        require(sum(Decimal(x['cost_usd'])for x in audits)==actual,'known physical/audit total identical')
        status=read(job/'STATUS.json');require(status['status']=='STOPPED'and status['error_type']=='FileNotFoundError','documented post-dispatch path bug only')
        write(job/'ADMIN_SEAL_REPAIR.json',dict(status='CPU_ONLY_COMPLETE_SAVED_RESPONSES_NO_CALLS',
            reason='runner raw-path bookkeeping used directory label consistency_judging instead of frozen call phase judging after all252 terminals were saved',
            original_status_sha256=sha(job/'STATUS.json'),original_progress_sha256=sha(job/'PROGRESS.json'),
            frozen_source_sha256=sha(HERE/'E118_SOURCE_SEAL.json'),repair_source_sha256=sha(receipt),
            responses_unchanged_sha256=sha(job/'RESPONSES.json'),n=252,actual_usd=str(actual),unresolved_reserve_usd='0',
            paid_calls_during_repair=0,settlements_changed=False,original_prompt_validator_terminal_values_unchanged=True))
        write(job/'RAW_RESPONSE_BINDINGS.json',refs)
        first=min(Path(x['path']).stat().st_mtime for x in refs)
        write(final,dict(experiment='E118',phase='consistency_judging',status='COMPLETE',route_verified=True,labels_cpu_only=True,
            first_output_utc=datetime.fromtimestamp(first,timezone.utc).isoformat(),first_output_source='earliest verified original physical response mtime',
            input_seal_sha256=sha(dest/'INPUT_SEAL.json'),source_seal_sha256=sha(HERE/'E118_SOURCE_SEAL.json'),
            allocation_sha256=sha(dest/'ADMISSION.json'),redaction_audit_complete=True,redacted_records=0,
            repair_source_sha256=sha(receipt),closure_only_repair=True,paid_calls_during_repair=0,
            files={p.name:sha(p)for p in job.iterdir()if p.is_file()and p.name!='JUDGMENT_SEAL.json'}))
        return read(final)


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args();repair();print('E118 CPU-only sealed '+sha(CACHE/'E118/consistency_judging/outputs/JUDGMENT_SEAL.json'))
