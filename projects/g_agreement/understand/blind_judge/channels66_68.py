"""Sealed E66/E68 format adapters and admission; never performs analysis."""
import argparse
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path
from .run import ROOT
from .judgment_adapter402 import render_record
from projects.g_agreement.readerbench.io import read, sha, verify, write
from projects.g_agreement.readerbench.scoring import require

HERE=ROOT/'results/g_agreement/understand/blind_judge/e66_e68'
QUESTIONS=('S1','S2','S3','S4','topic','eval_awareness')
COUNTS={'E66':542,'E68':1512,'E76':None}  # E76 expands shared readouts by judged row.


def rubric_path(bank):
    require(bank in COUNTS,'registered bank')
    return HERE/('E66_RUBRIC.txt' if bank=='E66' else 'E68_RUBRIC.md')


def schema66():
    props={'id':{'type':'string'},**{k:{'type':'boolean'} for k in QUESTIONS},
        'evidence':{'type':'object','additionalProperties':False,'required':list(QUESTIONS),
                    'properties':{k:{'type':'string'} for k in QUESTIONS}}}
    return dict(type='object',additionalProperties=False,required=list(props),properties=props)


def validate66(code,item):
    from .later_runner import normalize
    require(set(code)=={'id','evidence',*QUESTIONS} and code['id']==item['id'],'E66 code schema')
    require(isinstance(code['evidence'],dict) and set(code['evidence'])==set(QUESTIONS),'six evidence fields')
    for k in QUESTIONS:
        e=code['evidence'][k]
        require(type(code[k]) is bool and isinstance(e,str),'boolean/evidence types')
        require(bool(normalize(e))==code[k] and normalize(e) in normalize(item['readout']),'E66 verbatim evidence')


def check_records(bank,items,rubric):
    require(bool(items) and (COUNTS[bank] is None or len(items)==COUNTS[bank]) and len({x['id'] for x in items})==len(items),'complete unique packet')
    for x in items:
        require(isinstance(x,dict) and isinstance(x.get('id'),str) and re.fullmatch('[a-f0-9]{20,64}',x['id']) and isinstance(x.get('readout'),str),'opaque ID/readout')
        if bank=='E66':require(set(x)=={'id','readout'},'E66 blind fields only')
        else:
            require(set(x)=={'id','property','values','readout'},'E68 frozen public fields')
            render_record(x,rubric)


def convert(spec,out):
    bank=spec['bank'];frozen=rubric_path(bank).read_bytes()
    # The caller supplies a pinned source seal; do not open any private maps.
    require(sha(spec['source_seal'])==spec['source_seal_sha256'],'source seal hash')
    seal=read(spec['source_seal']);packet=Path(spec['source_packet'])
    if bank=='E66':
        require(seal.get('n')==542 and seal.get('status')=='BLIND_PACKET_READY','E66 frozen sample')
        digest=seal['packet_sha256']
    else:
        require(seal.get('experiment')==bank and packet.name=='JUDGE_PACKET.json' and packet.parent.resolve()==Path(spec['source_seal']).parent.resolve(),'bank blind seal scope')
        digest=seal['files'][packet.name]
        require(seal['rubric_sha256']==hashlib.sha256(frozen).hexdigest(),'E68 frozen rubric seal')
    blob=packet.read_bytes();require(hashlib.sha256(blob).hexdigest()==digest,'source packet hash')
    rubric=Path(spec['rubric']).read_bytes();require(rubric==frozen,'rubric bytes must equal frozen bank rubric')
    items=[json.loads(line) for line in blob.splitlines()] if bank=='E66' else json.loads(blob)
    check_records(bank,items,rubric.decode('utf-8'))
    encoded=(json.dumps(items,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    restored=json.loads(encoded)
    require(restored==items,'lossless records')
    for x,y in zip(items,restored):
        for key in ('id','readout'):
            require(x[key].encode('utf-8')==y[key].encode('utf-8'),'record bytes')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    (out/'PACKET.json').write_bytes(encoded);(out/'RUBRIC.txt').write_bytes(rubric)
    write(out/'PACKET_SEAL.json',dict(experiment=bank,n=len(items),
        source_seal_sha256=spec['source_seal_sha256'],source_packet_sha256=digest,
        rubric_sha256=hashlib.sha256(rubric).hexdigest(),record_bytes_verified=True,
        files={name:sha(out/name) for name in ('PACKET.json','RUBRIC.txt')}))


def budget_gate(bank,b,spec=None):
    require(b.get('issuer')=='integrator' and b.get('verified') is True and b.get('bank')==bank and
            b.get('allocation_id') and b.get('reservation_included') is True,'integrator reserved allocation')
    if bank=='E76':
        from .cap_ledger import cap_entry
        require(spec is not None,'E76 sealed cap spec')
        cap=cap_entry(spec,bank)
    else:cap=Decimal('6') if bank=='E68' else Decimal('3')
    require(Decimal(str(b['reserved_judging_usd']))==cap,'registered bank allocation cap')
    require(b.get('date_zurich')==('2026-10-28' if bank=='E76' else '2026-10-27'),'dated allocation')
    daily=Decimal(str(b['daily_committed_including_reservation_usd']))
    require(daily.is_finite() and cap<=daily<=300,'judging daily allocation ceiling')
    if bank=='E66':
        total=Decimal(str(b['shared_15usd_committed_including_reservation_usd']))
        require(total.is_finite() and 3<=total<=15 and b.get('exclusive_3usd_reservation_within_shared_15usd') is True,'E66 reserved inside USD15, not additional authority')


def admission(spec):
    bank=spec['bank'];require(bank in COUNTS,'channel bank')
    require(spec.get('channel')==('structure' if bank=='E66' else 'placebo' if bank=='E76' else 'value'),'registered channel')
    require(sha(spec['budget_receipt'])==spec['budget_receipt_sha256'],'budget receipt hash')
    budget_gate(bank,read(spec['budget_receipt']),spec)
    require(sha(spec['receipt'])==spec['receipt_sha256'],'custody receipt hash')
    r=read(spec['receipt'])
    require(r.get('issuer')=='integrator' and r.get('verified') is True and r.get('bank')==bank and type(r.get('n')) is int and r['n']>0 and (COUNTS[bank] is None or r['n']==COUNTS[bank]),'verified complete bank custody')
    require(r.get('authority')==('23a2e5c9' if bank=='E66' else '§194' if bank=='E76' else 'd147b2fe'),'registered authority')
    if bank=='E76':require(r.get('pool')=='placebo' and r.get('frozen_row_expansion_verified') is True,'E76 sealed placebo row expansion required')
    require(r.get('source_seals'),'source custody required')
    for source in r['source_seals']:
        require(sha(source['path'])==source['sha256'],'source custody seal hash')
    p=Path(spec['packet']);s=verify(p/'PACKET_SEAL.json',spec['packet_seal_sha256'])
    require(s['experiment']==bank and s['n']==r['n'] and r['packet_seal_sha256']==spec['packet_seal_sha256'],'packet binding')
    require(s['source_seal_sha256'] in {x['sha256'] for x in r['source_seals']},'original seal bound in custody')
    rubric=(p/'RUBRIC.txt').read_bytes()
    require(rubric==rubric_path(bank).read_bytes() and s['rubric_sha256']==hashlib.sha256(rubric).hexdigest(),'frozen rubric bytes')
    items=read(p/'PACKET.json');require(len(items)==r['n'],'complete receipt grid')
    text=rubric.decode('utf-8');check_records(bank,items,text)
    return ([render_record(x,text) for x in items] if bank in ('E68','E76') else items),text


def reserve_parent(api, cache):
    """Hold E66's full subcap in the existing shared ledger until operator closeout."""
    previous=api.CAP
    try:
        api.CAP=Decimal('15')
        ledger=api.Ledger(Path(cache)/'later_banks_15usd/ledger.jsonl')
        book,done=ledger.totals();ident='E66_EXCLUSIVE_3USD_ALLOCATION'
        if ident in book:
            require(ident not in done and book[ident]==Decimal('3'),'E66 reservation already settled or changed')
        else:
            require(ledger.reserve(ident,Decimal('3')),'E66 USD3 does not fit shared USD15')
    finally:
        api.CAP=previous


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();convert(read(a.spec),a.out)
    print('Format-only packet sealed; no judging or analysis.')


if __name__=='__main__':main()
