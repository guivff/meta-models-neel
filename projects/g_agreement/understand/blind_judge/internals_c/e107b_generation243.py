"""E107b forecast generation only, same combined lifetime2 as later judging.

Original199 source95bb and Qprebankaaf45bf8; no E107 primary replay. The
completed generation seal is followed by a separately admitted judging phase.
"""
import argparse,json,os,subprocess,time
from collections import Counter
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from . import transport,resume_e340 as bounds
from .accounting_e79b import snapshot
from .e107b_source import prepare as prepare_source
from .runner import CACHE,seal_phase,preflight
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

CAP=Decimal(2)


def enforce_cap(api,client,unpaced):
    namespaces=[api.__dict__]+[getattr(f,'__func__',f).__globals__ for f in (client.ledger.reserve,client.ledger.settle,client.ledger.summary,unpaced)]
    for n in namespaces:require('CAP'in n,'actual cap namespace');n['CAP']=CAP
    require(all(n['CAP']==CAP for n in namespaces),'actual ledger/client cap2')


class ForecastTransport(bounds.ResumeTransport):
    def __enter__(self):
        value=super().__enter__();one=self.api.Client.one
        def capped(client,*a,**k):enforce_cap(self.api,client,self.unpaced);return one(client,*a,**k)
        self.api.Client.one=capped;enforce_cap(self.api,self.client,self.unpaced);return value
    def summary(self):
        enforce_cap(self.api,self.client,self.unpaced);return super().summary()


def source_gate():
    p=transport.HERE/'E107B_GENERATION243_SOURCE_SEAL.json'
    for n,h in read(p)['files'].items():require(sha(transport.ROOT/n)==h,'committed E107b prospective source')
    require(read(p)['owner_report_pinned']is True,'genuine tested owner report source required')
    q=transport.ROOT/'results/g_agreement/understand/e107b/binding_trackq/PREBANK_RECEIPT.json';require(sha(q)=='aaf45bf86b7c0bb4063d105f8ee4a5f6b9baa219c2114bd48bee03e052bd69ac','exact Qbinding')
    for k in ('forecast_source','primary','inventory','original_output'):
        r=read(q)[k];verify(r['seal'],r['sha256'])
    return p


@contextmanager
def worker():
    source_gate();before=transport.CAPS.get('E107b');expiry=transport.EXPIRY;transport.CAPS['E107b']=CAP;bounds.CAPS['E107b']=CAP;transport.EXPIRY=1793372400
    try:yield
    finally:
        transport.EXPIRY=expiry
        if before is None:transport.CAPS.pop('E107b',None)
        else:transport.CAPS['E107b']=before


def prepare():
    source=source_gate();d=prepare_source();verify(d/'SOURCE_SEAL.json','95bb773c2e0c0af00a2daa0d45ce03371923809fa1b82398a22ba3a700ca16ee')
    calls=read(d/'GENERATION_CALLS.json');require(len(calls)==199,'full original199 generation grid')
    with worker():
        dest=seal_phase('E107b','generation',calls,dict(n=199,forecast_source_sha256=sha(d/'SOURCE_SEAL.json'),generation_source_sha256=sha(source),max_schema_retries=0),[dict(seal=str(d/'SOURCE_SEAL.json'),sha256=sha(d/'SOURCE_SEAL.json'))]);preflight(dest)
    return dest


def run(dest):
    source=source_gate();a=read(dest/'ADMISSION.json');pub=read(dest/'PUBLICATION.json');p=Path(pub['allocation_path']);live=read(dest/'LIVE_PROOF.PRIVATE.json')
    require(dest.resolve()==(CACHE/'E107b/generation').resolve()and a['bank']=='E107b'and Decimal(str(a['allocation_usd']))==CAP and a['E107b_generation_source_sha256']==sha(source),'same registered E107b2/input/source')
    require(sha(p)==pub['allocation_sha256']==sha(dest/'ADMISSION.json')and subprocess.check_output(['git','show',pub['commit']+':'+str(p.relative_to(transport.ROOT))],cwd=transport.ROOT)==p.read_bytes(),'published actual allocation beforecalls')
    require(sha(dest/'LIVE_PROOF.PRIVATE.json')==a['live_route_funding_proof_sha256']and 0<=time.time()-live['at_epoch']<300 and all(live[k]is True for k in ('route_verified','account_privacy_verified','funded_remaining_bank_cap')),'fresh live proof')
    job=dest/'outputs';job.mkdir(exist_ok=True);guard=dest/'GENERATION_ONCE.json'
    require(not(job/'GENERATION_SEAL.json').exists()and not guard.exists(),'generation once; stopped run needs explicit saved-state recovery')
    with worker():
        transport.unpaused();proof=snapshot();require('E107b'in proof['open_banks'],'combined E107b2 allocation counted');write(dest/'DISPATCH_GLOBAL_PROOF.PRIVATE.json',proof)
        with ForecastTransport(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'),a,os.environ['OPENROUTER_API_KEY'])as channel:
            write(guard,dict(source_sha256=sha(source),input_sha256=sha(dest/'INPUT_SEAL.json'),pid=os.getpid(),at_epoch=time.time()));terminals=[];audits=[]
            try:
                for call in channel.calls:
                    t,audit=channel.call(call['id']);require(t['status']in ('GENERATED','UNPARSEABLE','REFUSED'),'literal generation/terminalmissing');terminals.append(t);audits.append(audit)
                    write(job/'PROGRESS.json',dict(completed=len(terminals),n=199,cost=channel.summary(),at_epoch=time.time()))
                require(len(terminals)==199,'all original199 generation calls terminal')
                write(job/'RESPONSES.json',terminals);write(job/'ROUTE_AUDIT.json',dict(routes=channel.routes,requests=audits));write(job/'RAW_RESPONSE_BINDINGS.json',channel.physical);write(job/'COUNTS.json',dict(n=199,status_counts=dict(Counter(t['status']for t in terminals)),cost=channel.summary(),budget_release=False))
                events=[json.loads(s)for s in (channel.root/'ledger/ledger.jsonl').read_text().splitlines()if s.strip()];write(job/'BOOKED_429_BOUNDS.json',dict(events=[e for e in events if e.get('event')=='settle'and e.get('authority')=='e34073059'],provider_actual_cost_known=False))
                write(job/'STATUS.json',dict(status='COMPLETE_GENERATION_WAIT_JUDGING',pid=os.getpid(),bank_complete=False))
                from datetime import datetime,timezone
                first=min(Path(r['path']).stat().st_mtime for r in channel.physical)
                write(job/'GENERATION_SEAL.json',dict(experiment='E107b',phase='generation',status='COMPLETE',first_output_utc=datetime.fromtimestamp(first,timezone.utc).isoformat(),input_sha256=sha(dest/'INPUT_SEAL.json'),source_sha256=sha(source),route_verified=True,labels_cpu_only=True,bank_complete=False,files={p.name:sha(p)for p in job.iterdir()if p.is_file()}))
            except BaseException as exc:write(job/'STOPPED.json',dict(error_type=type(exc).__name__,at_epoch=time.time(),no_resend=True));raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);p.add_argument('--phase-directory',type=Path);a=p.parse_args()
    if a.action=='prepare':print(prepare())
    else:run(a.phase_directory)
