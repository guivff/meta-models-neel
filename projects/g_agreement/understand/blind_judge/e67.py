"""§184 E67 claims judging: integrator execution only, isolated USD5 ledger."""
import argparse
import fcntl
import json
import os
import re
from decimal import Decimal
from pathlib import Path
from . import later_runner as runner
from .run import ROOT, CACHE
from .dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read, sha, verify
from projects.g_agreement.readerbench.scoring import require

HERE=ROOT/'results/g_agreement/understand/blind_judge/e67'
LEDGER=CACHE/'e67_5usd'
LABELS=('SUPPORTED','CONTRADICTED','UNVERIFIABLE')


def wave_number(spec):
    wave=spec.get('wave',1)
    require(type(wave) is int and wave in (1,2),'E67 wave must be 1 or 2')
    return wave


def wave_ledger(wave):
    return LEDGER if wave==1 else LEDGER/'wave_2'


def remaining_cap(api,wave):
    """Called under the common dispatch lock; unresolved reservations count as spend."""
    other=wave_ledger(2 if wave==1 else 1)
    book,_=api.Ledger(other/'ledger.jsonl').totals()
    spent=sum(book.values(),Decimal(0))
    require(spent.is_finite() and 0<=spent<=5,'E67 other-wave ledger exceeds total cap')
    return Decimal('5')-spent


def validate_code(code, item):
    require(set(code)=={'id','claims','generic'} and code['id']==item['id'], 'E67 output schema/ID')
    require(type(code['generic']) is bool and isinstance(code['claims'],list) and len(code['claims'])<=5,'E67 up to five claims')
    require(code['generic']==(len(code['claims'])==0),'GENERIC iff no specific claims')
    for claim in code['claims']:
        require(isinstance(claim,dict) and set(claim)=={'claim','verdict'} and
                isinstance(claim['claim'],str) and bool(claim['claim'].strip()) and
                claim['verdict'] in LABELS,'specific claim and registered verdict')


def admission(spec):
    wave=wave_number(spec)
    require(spec['bank']=='E67' and spec['packet_id'] in ('packet_0','packet_1'),'E67 two blind packet namespaces')
    require(sha(spec['budget_receipt'])==spec['budget_receipt_sha256'],'E67 allocation hash')
    budget=read(spec['budget_receipt'])
    require(budget.get('issuer')=='integrator' and budget.get('verified') is True and
            budget.get('bank')=='E67' and budget.get('date_zurich')=='2026-10-27' and
            budget.get('reservation_included') is True and budget.get('allocation_id'),'E67 separate allocation')
    amount=Decimal(str(budget['reserved_judging_usd']));daily=Decimal(str(budget['daily_committed_including_reservation_usd']))
    require(amount==5 and daily.is_finite() and amount<=daily<=300,'E67 USD5 within daily USD300')
    require(sha(spec['receipt'])==spec['receipt_sha256'],'E67 custody hash')
    receipt=read(spec['receipt'])
    require(receipt.get('wave',1)==wave,'E67 custody wave mismatch')
    require(receipt.get('issuer')=='integrator' and receipt.get('verified') is True and
            receipt.get('experiment')=='E67' and receipt.get('separate_shuffled_packets') is True and
            receipt.get('packet_id')==spec['packet_id'],'E67 verified blind custody')
    require(receipt.get('analysis_seals'),'source analyses must be sealed before packet access')
    for source in receipt['analysis_seals']:
        require(source['bank'] in ('E49','E54','E61_D4','E56','E57','E63'),'registered E67 source bank')
        sealed=verify(source['path'],source['sha256'])
        require(sealed.get('status') in ('COMPLETE_ONCE','COMPLETE') or source.get('integrator_verified_complete_once') is True,
                'source once-only analysis completion required')
    packet=Path(spec['packet'])
    require(receipt['packet_seal_sha256']==spec['packet_seal_sha256'],'E67 packet custody')
    seal=verify(packet/'PACKET_SEAL.json',spec['packet_seal_sha256'])
    require(seal.get('wave',1)==wave,'E67 packet wave mismatch')
    require(seal.get('experiment')=='E67' and seal.get('packet_id')==spec['packet_id'] and
            {'PACKET.json','CLAIMS_RUBRIC.md'}<=set(seal['files']),'E67 sealed packet/rubric')
    require(sha(packet/'CLAIMS_RUBRIC.md')==receipt['rubric_sha256'],'frozen claims rubric binding')
    rubric=(packet/'CLAIMS_RUBRIC.md').read_bytes().decode('utf-8');items=read(packet/'PACKET.json')
    require(items and len(items)==receipt['n'] and len({x['id'] for x in items})==len(items),'complete E67 packet')
    for item in items:
        require(set(item)=={'id','prompt','readout','rubric'} and
                re.fullmatch('[a-f0-9]{20,64}',item['id']) and
                isinstance(item['prompt'],str) and isinstance(item['readout'],str) and
                item['rubric']==rubric,'opaque ID + synthetic prompt + readout + frozen rubric only')
    return items,rubric


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',type=Path,required=True);p.add_argument('--preflight-only',action='store_true');a=p.parse_args()
    for name,digest in read(HERE/'SOURCE_SEAL.json')['files'].items():require(sha(name)==digest,'E67 source changed')
    spec=read(a.spec);items,rubric=admission(spec)
    if a.preflight_only:print('E67 seals and budget verified; no API calls');return
    key=os.environ.get('OPENROUTER_API_KEY');require(bool(key),'integrator credential unavailable')
    route=read(ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json')
    LEDGER.mkdir(parents=True,exist_ok=True)
    with dispatch_lock(LEDGER/'DISPATCH.lock'):
        wave=wave_number(spec)
        api,_,_,_=runner.route_modules(route)
        cap=remaining_cap(api,wave)
        runner.LEDGER=wave_ledger(wave)
        runner.dispatch(dict(spec,channel='claims',wave=wave),items,rubric,route,key,budget_cap=cap)


if __name__=='__main__':main()
