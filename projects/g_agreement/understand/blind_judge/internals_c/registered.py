"""Source-bound singleton judging driver for E107/E108/E109/E85/E106.

Eligible source owners deliver a sealed UNITS.json and explicit custody receipt.
This driver has no statistical analysis, labels, joins, scope selection or model
acquisition. Up to two schema retries use separately reserved physical requests;
charged length is terminal on the first such response.
"""
import argparse
import hashlib
import json
import os
import subprocess
import time
from collections import Counter
from pathlib import Path

from .transport import ROOT,HERE,SHARED,CAPS,Transport,unpaused
from .runner import CACHE,seal_phase,preflight
from .banks import (value_call,eval85,choice108,placebo106,opaque,rendered)
from .accounting import snapshot
from ..rubric202 import original_ids,BASE,amended
from ..later_runner import channel_payload,classify,S6_RUBRIC_SHA
from .. import funded_queue as funded
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def source_gate(path=None):
    for name,digest in read(path or HERE/'JUDGING_SOURCE_SEAL.json')['files'].items():
        require(sha(ROOT/name)==digest,'prospective judging source pin')


def unit_call(unit,protocol):
    require(set(unit)=={'id','kind','data','rubric'},'CPU validator descriptor allowlist')
    ident,kind,data,rubric=(unit[k] for k in ('id','kind','data','rubric'))
    require(data['id']==ident,'original opaque source identity')
    if kind in ('value','old_value'):
        require(rubric==(amended().decode() if kind=='value' else BASE.read_text()),'exact E56 original/amended rubric')
        call,base_validator=value_call([data],protocol,'judging' if kind=='value' else 'original',rubric)
        allowed={k for k,v in data['values'].items() if v}
        def validator(v):
            base_validator(v)
            require(set(v['records'][0]['values'])<=allowed,'no undefined missing-truth candidate')
    elif kind=='eval85':
        require(rubric is None,'frozen judge205 owns its wording')
        call,validator=eval85(data)
    elif kind=='s6':
        require(hashlib.sha256(rubric.encode()).hexdigest()==S6_RUBRIC_SHA,'original S6 rubric hash')
        require(set(data)=={'id','readout'},'original S6 blind fields')
        wire=channel_payload([data],rubric,'S6',protocol)
        call=dict(id=opaque('S6',ident),phase='original',rendered=rendered(wire['messages'],wire['response_format']['json_schema']))
        def validator(v):
            require(classify([data],v,'S6')[0]['status']=='KEPT','original S6 schema/evidence')
    elif kind in ('choice_extract','choice_hit'):
        require(rubric is None,'prospectively frozen E108 wording')
        call,validator=choice108([data],'extraction' if kind=='choice_extract' else 'judging')
    elif kind=='placebo106':
        require(set(data)=={'id','readout','trained_values'} and rubric is None,'whole-union placebo descriptor')
        call,validator=placebo106([dict(id=ident,readout=data['readout'])],data['trained_values'])
    else:raise ValueError('unregistered unit kind')
    return call,validator


def check_scope(bank,units,receipt):
    require(receipt.get('issuer') in ('I-2','I-3','I-4','Track Q','W-internals-C') and receipt.get('verified') is True and
            receipt.get('experiment')==bank and receipt.get('complete_eligible_native_grid') is True and
            receipt.get('labels_cpu_only') is True,'complete registered owner custody')
    require(bool(units) and len({(x['id'],x['kind']) for x in units})==len(units),'unique complete unit/kind grid')
    counts=Counter(x['kind'] for x in units)
    if bank=='E85':
        require(counts=={'eval85':800,'s6':200},'all800 E85 primary and200 original codes')
        selected=original_ids([x['id'] for x in units if x['kind']=='eval85'],'E85')
        require(sorted(x['id'] for x in units if x['kind']=='s6')==selected,'original S6 exact seeded25%')
    elif bank=='E109':
        require(counts=={'value':1008,'old_value':252},'whole E109 readout grid plus seeded original comparison')
    elif bank=='E108':
        require(set(counts)<={'choice_extract','choice_hit'},'E108 registered extraction/hit channels')
        if counts.get('choice_extract'):
            require(counts=={'choice_extract':1008} and receipt.get('ground_truth_blind') is True,'blind full1008 continuation extraction only')
        else:
            require(receipt.get('extraction_complete') is True and receipt.get('outside_complete') is True and
                    receipt.get('registered_none_multiple_exclusions_only') is True,'E108 derived hits after blind extraction and outside seal')
    else:
        require(bank in ('E106','E107') and set(counts)<={'value','old_value','placebo106'},'registered value/union channels')
        require(receipt.get('regex_first_unresolved_only') is True,'original regex/scorer selection, no new scoring')
        if bank=='E107':require(counts['value']+receipt.get('regex_resolved_retained',0)==4496,'full E1074496 target scope including retained original-regex codes')
        if bank=='E106':require(receipt.get('whole_trained_value_union_verified') is True,'221.3 whole union binding')
    values=[x['id'] for x in units if x['kind']=='value']
    olds=sorted(x['id'] for x in units if x['kind']=='old_value')
    if values:
        require(olds==original_ids(values,bank),'exact seeded original25% of unresolved value grid')


def normalized_code(kind,terminal):
    """Explicit interface conversion; original response remains sealed unchanged."""
    if terminal['status']!='KEPT':return None
    result=terminal['result']
    if kind in ('value','old_value','s6'):return result['records'][0]
    if kind=='eval85':return result
    item=result['records'][0]
    if kind=='choice_extract':
        return dict(status=item['status'],canonical_member=item['canonical_member'] if item['status']=='ONE' else None)
    if kind=='choice_hit':return item['hit']
    require(kind=='placebo106','registered normalization')
    return dict(states_any_trained_value=item['states_any_trained_value'],evidence=item['evidence'])


def prepare(spec_path):
    source_gate()
    spec=read(spec_path)
    bank=spec['bank'];require(bank in CAPS,'registered C bank')
    source=Path(spec['unit_seal'])
    seal=verify(source,spec['unit_sha256'])
    require(seal['experiment']==bank and {'UNITS.json','CUSTODY.json'}<=set(seal['files']),'sealed owner unit/custody binding')
    units=read(source.parent/'UNITS.json')
    custody=read(source.parent/'CUSTODY.json')
    check_scope(bank,units,custody)
    for s in custody['source_seals']:verify(s['seal'],s['sha256'])
    _,(_,_,protocol,_)=funded.route_api()
    calls=[];plan=[]
    max_retries=0 if bank=='E107' else 2
    for unit in units:
        original,_=unit_call(unit,protocol)
        ids=[]
        for attempt in range(1+max_retries):
            call=dict(original,id=opaque(bank,unit['kind'],unit['id'],'attempt'+str(attempt)))
            ids.append(call['id']);calls.append(call)
        plan.append(dict(unit=unit,calls=ids))
    # Transport contexts contain one phase. A bank plan has separate original and
    # primary contexts but they share the single canonical bank ledger/cap.
    result=[]
    label=spec['phase_name']
    require(label and '/' not in label and '..' not in label,'phase directory component')
    for phase in sorted({c['phase'] for c in calls}):
        selected=[c for c in calls if c['phase']==phase]
        provenance=dict(owner_unit_seal_sha256=spec['unit_sha256'],judging_source_seal_sha256=sha(HERE/'JUDGING_SOURCE_SEAL.json'),custody_sha256=sha(source.parent/'CUSTODY.json'))
        dest=seal_phase(bank,label+'_'+phase,selected,provenance,[dict(seal=str(source),sha256=spec['unit_sha256'])]+custody['source_seals'])
        current=read(dest/'INPUT_SEAL.json')
        selected_ids={c['id'] for c in selected}
        plans=[x for x in plan if x['calls'][0] in selected_ids]
        if(dest/'VALIDATION.json').exists():require(read(dest/'VALIDATION.json')==plans,'immutable validator inventory')
        else:write(dest/'VALIDATION.json',plans)
        current['files']['VALIDATION.json']=sha(dest/'VALIDATION.json')
        frozen_source=dest/'JUDGING_SOURCE_SEAL.json'
        source_bytes=(HERE/'JUDGING_SOURCE_SEAL.json').read_bytes()
        if frozen_source.exists():require(frozen_source.read_bytes()==source_bytes,'immutable phase source receipt')
        else:frozen_source.write_bytes(source_bytes)
        current['files']['JUDGING_SOURCE_SEAL.json']=sha(frozen_source)
        write(dest/'INPUT_SEAL.json',current)
        # Phase label and call phase are distinct (e.g. native_judging); transport
        # uses the latter. Full sealed first/retry wires are privacy checked.
        audit=preflight(dest)
        audit['all_authorized_attempt_wires_upper_usd']=audit['first_pass_upper_usd']
        from decimal import Decimal
        audit['first_pass_upper_usd']=str(Decimal(audit['first_pass_upper_usd'])/(1+max_retries))
        audit['initial_requests']=len(plans)
        audit['max_schema_retries']=max_retries
        write(dest/'CPU_PREFLIGHT.json',audit)
        result.append(dict(directory=str(dest),preflight=audit,units=len(plans)))
    return result


def run(dest):
    source_gate(dest/'JUDGING_SOURCE_SEAL.json');unpaused()
    seal=verify(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'))
    require('VALIDATION.json' in seal['files'],'frozen evidence validators')
    require(read(dest/'PROVENANCE.json')['judging_source_seal_sha256']==sha(dest/'JUDGING_SOURCE_SEAL.json'),'frozen validator source')
    admission=read(dest/'ADMISSION.json');publication=read(dest/'PUBLICATION.json')
    path=Path(publication['allocation_path'])
    require(subprocess.check_output(['git','show',publication['commit']+':'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes() and
            sha(path)==publication['allocation_sha256']==sha(dest/'ADMISSION.json'),'posted new-phase allocation, same lifetime cap')
    live_path=dest/'LIVE_PROOF.PRIVATE.json'
    require(live_path.exists() and sha(live_path)==admission['live_route_funding_proof_sha256'],'exact new-phase live proof')
    live=read(live_path)
    require(0<=time.time()-live['at_epoch']<300 and live['route_verified'] is True and
            live['account_privacy_verified'] is True and live['funded_remaining_bank_cap'] is True,'fresh route/privacy/funding proof')
    proof=snapshot();write(dest/'DISPATCH_GLOBAL_PROOF.PRIVATE.json',proof)
    require(admission['bank'] in proof['open_banks'],'combined open bank allocation')
    job=dest/'outputs';job.mkdir(exist_ok=True)
    if(job/'JUDGMENT_SEAL.json').exists():return verify(job/'JUDGMENT_SEAL.json',sha(job/'JUDGMENT_SEAL.json'))
    units=[];attempts=[];audits=[]
    with Transport(dest/'INPUT_SEAL.json',sha(dest/'INPUT_SEAL.json'),admission,os.environ['OPENROUTER_API_KEY']) as channel:
        try:
            for plan in read(dest/'VALIDATION.json'):
                expected,validator=unit_call(plan['unit'],channel.protocol)
                final=None
                for attempt,ident in enumerate(plan['calls']):
                    actual=channel.allowed[ident]
                    require(actual['rendered']==expected['rendered'] and actual['phase']==expected['phase'],'prospective exact renderer/validator binding')
                    terminal,audit=channel.call(ident,validator)
                    attempts.append(dict(terminal,unit_id=plan['unit']['id'],kind=plan['unit']['kind'],attempt=attempt))
                    audits.append(audit)
                    final=dict(id=plan['unit']['id'],kind=plan['unit']['kind'],status=terminal['status'],code=normalized_code(plan['unit']['kind'],terminal),attempts=attempt,request_id=terminal['request_id'],response_sha256=terminal['response_sha256'])
                    if terminal['status']=='KEPT' or terminal.get('reason')=='CHARGED_LENGTH':break
                units.append(final)
                write(job/'PROGRESS.json',dict(completed=len(units),n=len(read(dest/'VALIDATION.json')),cost=channel.summary(),at_epoch=time.time()))
            write(job/'JUDGMENTS.json',units);write(job/'ATTEMPTS.json',attempts)
            write(job/'ROUTE_AUDIT.json',dict(routes=channel.routes,requests=audits))
            write(job/'COUNTS.json',dict(status_counts=dict(Counter(x['status'] for x in units)),n=len(units),cost=channel.summary()))
            raw_paths=[channel.root/'ledger'/(admission['bank']+'_'+channel.allowed[x['id']]['phase'])/(x['request_id']+'.response.json') for x in attempts]
            write(job/'RAW_RESPONSE_BINDINGS.json',[dict(path=str(p),sha256=sha(p)) for p in raw_paths])
            from datetime import datetime,timezone
            first_output=min(p.stat().st_mtime for p in raw_paths)
            write(job/'JUDGMENT_SEAL.json',dict(experiment=admission['bank'],status='COMPLETE',phase=seal['phase'],
                first_output_utc=datetime.fromtimestamp(first_output,timezone.utc).isoformat(),first_output_source='earliest retained physical response mtime',
                input_sha256=sha(dest/'INPUT_SEAL.json'),source_seal_sha256=sha(dest/'JUDGING_SOURCE_SEAL.json'),route_verified=True,
                labels_cpu_only=True,redaction_audit_complete=True,redacted_records=0,
                files={p.name:sha(p) for p in job.iterdir() if p.is_file() and p.name!='JUDGMENT_SEAL.json'}))
        except BaseException as exc:
            write(job/'STOPPED.json',dict(error_type=type(exc).__name__,cost=channel.summary(),at_epoch=time.time()))
            raise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','run']);p.add_argument('--spec',type=Path);p.add_argument('--phase-directory',type=Path);a=p.parse_args()
    if a.action=='prepare':print(json.dumps(prepare(a.spec),sort_keys=True))
    else:run(a.phase_directory)
