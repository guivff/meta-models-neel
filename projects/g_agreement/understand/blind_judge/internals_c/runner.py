"""Prepare/source-preflight/run sealed C-bank phases, never run scientific analysis."""
import argparse
import importlib
import json
import os
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from .transport import ROOT, HERE, SHARED, CAPS, Transport, frozen_wire, check_privacy, source_gate, unpaused
from .banks import outside108, validate_schema
from .accounting import snapshot
from .. import funded_queue as funded
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require

CACHE = ROOT/'cache/g_agreement/understand/internals_c'


def seal_phase(bank, phase, calls, provenance, source_seals):
    dest=CACHE/bank/phase
    if dest.exists():
        require(read(dest/'CALLS.json')==calls and read(dest/'PROVENANCE.json')==provenance, 'immutable existing phase')
        verify(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'))
        return dest
    dest.mkdir(parents=True,exist_ok=False)
    dest.chmod(0o700)
    write(dest/'CALLS.json',calls)
    write(dest/'PROVENANCE.json',provenance)
    for p in dest.iterdir():p.chmod(0o600)
    write(dest/'INPUT_SEAL.json',dict(experiment=bank,phase=phase,n=len(calls),frozen_before_calls=True,
          labels_cpu_only=True,source_seals=source_seals,
          files={n:sha(dest/n) for n in ('CALLS.json','PROVENANCE.json')}))
    return dest


def prepare_generation(bank):
    require(bank in ('E107','E108'),'outside describer bank')
    if bank=='E107':
        origin=ROOT.parent/'wt-i2'
        home=origin/'cache/g_agreement/i2/e107_cpu_inventory_v1'
        audit_path=ROOT/'results/g_agreement/i2/E107_SOURCE_PREFIX_CPU_AUDIT.json'
        audit=read(audit_path)
        require(sha(home/'GENERATION_CANDIDATE.json')==audit['generation_candidate_sha256'] and
                sha(home/'GENERATION_SOURCE_BINDINGS.PRIVATE.json')==audit['source_bindings_sha256'], 'original frozen prefix/input hashes')
        candidates=read(home/'GENERATION_CANDIDATE.json')
        calls=read(home/'GENERATION_CALLS_CANDIDATE.json')
        require(len(candidates)==len(calls)==4297 and
                all(c==dict(id=x['id'],phase='generation',rendered=dict(system=None,user=x['prompt'],schema=None)) for c,x in zip(calls,candidates)), 'unchanged complete4297 generation wires')
        bindings=read(home/'GENERATION_SOURCE_BINDINGS.PRIVATE.json')
        source_files={x['source_public_file']:x['source_public_file_sha256'] for x in bindings}
        for path,digest in source_files.items():
            require(sha(path)==digest, 'original prompt source unchanged')
        provenance=dict(source_audit_sha256=sha(audit_path),candidate_sha256=sha(home/'GENERATION_CANDIDATE.json'),
                        private_source_bindings_sha256=sha(home/'GENERATION_SOURCE_BINDINGS.PRIVATE.json'),
                        n=4297,source_counts={'E81':3688,'E82':209,'E86':400},private_join_copied=False)
        # A hash-only source manifest is sealed locally; the original files are
        # verified above, never copied into a wire or public result.
        src=CACHE/bank/'generation_origin'
        src.mkdir(parents=True,exist_ok=True)
        if not(src/'SOURCE_SEAL.json').exists():
            write(src/'PROVENANCE.json',provenance)
            write(src/'SOURCE_SEAL.json',dict(experiment=bank,files={'PROVENANCE.json':sha(src/'PROVENANCE.json')}))
        sources=[dict(seal=str(src/'SOURCE_SEAL.json'),sha256=sha(src/'SOURCE_SEAL.json'))]
    else:
        base=ROOT/'results/g_agreement/understand/e108'
        source_seal=base/'BANK_SEAL.json'
        verify(source_seal,sha(source_seal))
        receipt=read(base/'INPUT_RECEIPT.json')
        inputs=Path(receipt['public_directory'])/'PUBLIC_INPUTS.json'
        require(sha(inputs)==receipt['files']['PUBLIC_INPUTS.json'],'frozen1008 input bytes')
        public=read(inputs)
        inventory={x['id']:x for x in read(base/'INVENTORY.json') if x['kind']=='native'}
        require(len(public)==len(inventory)==1008 and {x['id'] for x in public}==set(inventory),'whole original1008 native inventory')
        calls=[outside108(x,inventory[x['id']]) for x in public]
        provenance=dict(n=1008,input_sha256=sha(inputs),inventory_sha256=sha(base/'INVENTORY.json'),
                        private_join_copied=False,question='Which {category} will this model most likely choose? Answer with one word.')
        sources=[dict(seal=str(source_seal),sha256=sha(source_seal))]
    return seal_phase(bank,'generation',calls,provenance,sources)


def preflight(dest):
    source_gate()
    seal=verify(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'))
    for s in seal['source_seals']:verify(s['seal'],s['sha256'])
    route,(api,privacy,p,io)=funded.route_api()
    calls=read(dest/'CALLS.json')
    require(len(calls)==seal['n'] and len({c['id'] for c in calls})==len(calls),'full unique phase')
    upper=Decimal(0)
    hashes=[]
    for call in calls:
        w=frozen_wire(call,p)
        check_privacy(seal['experiment'],call,w,privacy.check_wire,p)
        hashes.append(io.digest(io.canonical(w)))
        upper+=api.upper(w)
    write(dest/'WIRE_HASHES.json',hashes)
    receipt=dict(bank=seal['experiment'],phase=seal['phase'],n=len(calls),input_sha256=sha(dest/'INPUT_SEAL.json'),
                 exact_wire_hashes_sha256=sha(dest/'WIRE_HASHES.json'),first_pass_upper_usd=str(upper),
                 source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),privacy_all_passed=True,
                 route_source_sha256=sha(ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json'),calls=0)
    write(dest/'CPU_PREFLIGHT.json',receipt)
    return receipt


def run(dest):
    unpaused()
    input_path=dest/'INPUT_SEAL.json'
    a=read(dest/'ADMISSION.json')
    # The allocation and source/tests must be published before paid dispatch.
    pub=read(dest/'PUBLICATION.json')
    path=Path(pub['allocation_path'])
    committed=subprocess.check_output(['git','show',pub['commit']+':'+str(path.relative_to(ROOT))],cwd=ROOT)
    require(committed==path.read_bytes() and sha(path)==pub['allocation_sha256'], 'posted immutable allocation')
    require(sha(dest/'ADMISSION.json')==sha(path),'runtime/public allocation identical')
    require(a['input_sha256']==sha(input_path),'frozen input admission')
    current=snapshot()
    require(a['bank'] in current['open_banks'],'canonical combined allocation present')
    write(dest/'DISPATCH_GLOBAL_PROOF.PRIVATE.json',current)
    # Full wire privacy/cost inventory is rechecked against the prepared receipt.
    old=read(dest/'CPU_PREFLIGHT.json')
    require(preflight(dest)==old,'unchanged preflight')
    job=dest/'outputs'
    job.mkdir(exist_ok=True)
    seal_name='GENERATION_SEAL.json' if old['phase']=='generation' else 'JUDGMENT_SEAL.json'
    if(job/seal_name).exists():
        verify(job/seal_name,sha(job/seal_name))
        return
    key=os.environ.get('OPENROUTER_API_KEY')
    require(bool(key),'credential unavailable')
    start=time.time()
    write(job/'STATUS.json',dict(status='RUNNING',bank=a['bank'],phase=old['phase'],pid=os.getpid(),start_epoch=start))
    terminals=[]
    audits=[]
    try:
        with Transport(input_path,sha(input_path),a,key) as channel:
            for call in channel.calls:
                schema=call['rendered']['schema']
                validator=(lambda v,schema=schema:validate_schema(v,schema['schema'])) if schema else None
                terminal,audit=channel.call(call['id'],validator)
                terminals.append(terminal)
                audits.append(audit)
                if len(terminals)==1 or len(terminals)%5==0:
                    write(job/'PROGRESS.json',dict(bank=a['bank'],phase=old['phase'],completed=len(terminals),n=len(channel.calls),cost=channel.summary(),at_epoch=time.time()))
            write(job/'RESPONSES.json',terminals)
            write(job/'ROUTE_AUDIT.json',dict(routes=channel.routes,requests=audits))
            write(job/'COUNTS.json',dict(n=len(terminals),status_counts=dict(Counter(x['status'] for x in terminals)),cost=channel.summary()))
            write(job/'STATUS.json',dict(status='COMPLETE',bank=a['bank'],phase=old['phase'],pid=os.getpid(),start_epoch=start,completed_epoch=time.time()))
            name='GENERATION_SEAL.json' if old['phase']=='generation' else 'JUDGMENT_SEAL.json'
            raw_paths=[channel.root/'ledger'/(a['bank']+'_'+old['phase'])/(x['request_id']+'.response.json') for x in terminals]
            first_output=min(p.stat().st_mtime for p in raw_paths)
            write(job/'RAW_RESPONSE_BINDINGS.json',[dict(path=str(p),sha256=sha(p)) for p in raw_paths])
            write(job/name,dict(experiment=a['bank'],phase=old['phase'],status='COMPLETE',
                first_output_utc=datetime.fromtimestamp(first_output,timezone.utc).isoformat(),
                first_output_source='earliest retained physical response file mtime',
                input_seal_sha256=sha(input_path),source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),
                allocation_sha256=sha(dest/'ADMISSION.json'),route_verified=True,labels_cpu_only=True,
                redaction_audit_complete=True,redacted_records=0,
                files={p.name:sha(p) for p in job.iterdir() if p.is_file() and p.name not in ('GENERATION_SEAL.json','JUDGMENT_SEAL.json')}))
    except BaseException as exc:
        write(job/'STATUS.json',dict(status='PAUSED_402' if isinstance(exc,funded.CreditPause) else 'STOPPED',
            bank=a['bank'],phase=old['phase'],error_type=type(exc).__name__,pid=os.getpid(),start_epoch=start))
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['prepare-generation','preflight','run'])
    p.add_argument('--bank',choices=sorted(CAPS))
    p.add_argument('--phase-directory',type=Path)
    a=p.parse_args()
    if a.action=='prepare-generation':
        path=prepare_generation(a.bank)
        print(json.dumps(preflight(path),sort_keys=True))
    elif a.action=='preflight':print(json.dumps(preflight(a.phase_directory),sort_keys=True))
    else:run(a.phase_directory)


if __name__=='__main__':main()
