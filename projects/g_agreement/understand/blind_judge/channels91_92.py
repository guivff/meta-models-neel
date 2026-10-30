"""§201/§202 E91 polarity and E92 source: sealed blind format adapters."""
import argparse
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path
from projects.g_agreement.readerbench.io import read,sha,verify,write
from projects.g_agreement.readerbench.scoring import require
from .run import ROOT
from .rubric202 import original_ids,CLAUSE_NEG,CLAUSE_FORMAT
from .cap_ledger import cap_entry

HERE=ROOT/'results/g_agreement/understand/e91_e92'
BANKS={'E91','E92'}


def rubric_path(bank,original=False):
    require(bank in BANKS,'E91/E92 only')
    p=HERE/(bank+('_ORIGINAL_RUBRIC.txt' if original else '_RUBRIC202.txt'))
    if not original:
        assert p.read_bytes()==rubric_path(bank,True).read_bytes()+b'\n'+CLAUSE_NEG.encode()+b'\n'+CLAUSE_FORMAT.encode()+b'\n'
    return p


def render(item,bank,rubric):
    expected={'id','readout','concept' if bank=='E91' else 'content'}
    require(type(item) is dict and set(item)==expected and
            type(item['readout']) is str and
            re.fullmatch('[a-f0-9]{20,64}',item['id']),
            'opaque blind E91/E92 source fields')
    field='concept' if bank=='E91' else 'content'
    require(type(item[field]) is str and bool(item[field]) and '\n' not in item[field],
            'public concept/content description')
    return dict(id=item['id'],rubric=rubric+'\n\n'+field.title()+': '+item[field]+'\n',
                readout=item['readout'])


def convert(spec,out):
    bank=spec['bank'];rubric=rubric_path(bank).read_bytes()
    require(sha(spec['source_seal'])==spec['source_seal_sha256'],'source seal hash')
    s=read(spec['source_seal']);path=Path(spec['source_packet'])
    require(s.get('experiment')==bank and s.get('complete') is True and
            path.name=='JUDGE_PACKET.json' and path.parent.resolve()==Path(spec['source_seal']).parent.resolve() and
            sha(path)==s['files'][path.name] and s['rubric_sha256']==sha(rubric_path(bank)) and
            Path(spec['rubric']).read_bytes()==rubric,'frozen §202 source and rubric')
    items=read(path)
    require(type(items) is list and len(items)>0 and len(items)==s['n'] and
            len({x['id'] for x in items})==len(items),'complete opaque grid')
    for x in items:render(x,bank,rubric.decode())
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    write(out/'PACKET.json',items)
    (out/'RUBRIC.txt').write_bytes(rubric)
    write(out/'ORIGINAL_IDS.json',original_ids([x['id'] for x in items],bank))
    write(out/'PACKET_SEAL.json',dict(experiment=bank,n=len(items),source_seal_sha256=spec['source_seal_sha256'],
        source_packet_sha256=sha(path),rubric_sha256=sha(rubric_path(bank)),
        files={name:sha(out/name) for name in ('PACKET.json','RUBRIC.txt','ORIGINAL_IDS.json')}))


def admission(spec):
    bank=spec['bank'];require(bank in BANKS and spec.get('channel')==('polarity' if bank=='E91' else 'source'),
                                'bank native taxonomy')
    cap=cap_entry(spec,bank)
    require(sha(spec['budget_receipt'])==spec['budget_receipt_sha256'],'budget receipt')
    budget=read(spec['budget_receipt'])
    require(budget.get('issuer')=='integrator' and budget.get('verified') is True and
            budget.get('reservation_included') is True and budget.get('bank')==bank and
            budget.get('allocation_id') and Decimal(str(budget['reserved_judging_usd']))==cap and
            cap<=Decimal(str(budget['daily_committed_including_reservation_usd']))<=300,
            'sealed budget and daily ceiling')
    require(sha(spec['receipt'])==spec['receipt_sha256'],'custody receipt')
    r=read(spec['receipt'])
    require(r.get('issuer')=='integrator' and r.get('verified') is True and r.get('bank')==bank and
            r.get('authority')=='5e5e3f40' and r.get('forecast_gate_verified') is True and
            r.get('source_seals') and r.get('bank_gate_verified') is True,'verified §201 capture')
    for x in r['source_seals']:require(sha(x['path'])==x['sha256'],'source custody')
    packet=Path(spec['packet']);s=verify(packet/'PACKET_SEAL.json',spec['packet_seal_sha256'])
    require(s['experiment']==bank and s['source_seal_sha256'] in {x['sha256'] for x in r['source_seals']}
            and r['packet_seal_sha256']==spec['packet_seal_sha256'] and s['n']==r['n'] and
            s['rubric_sha256']==sha(rubric_path(bank)) and
            (packet/'RUBRIC.txt').read_bytes()==rubric_path(bank).read_bytes(),
            'sealed packet/rubric custody')
    source_seal=next(Path(x['path']) for x in r['source_seals'] if x['sha256']==s['source_seal_sha256'])
    original=read(source_seal);orig=source_seal.parent/'JUDGE_PACKET.json'
    require(sha(orig)==original['files']['JUDGE_PACKET.json']==s['source_packet_sha256'] and
            read(orig)==read(packet/'PACKET.json'),'original records unchanged')
    items=read(packet/'PACKET.json')
    require(len(items)==r['n'] and read(packet/'ORIGINAL_IDS.json')==
            original_ids([x['id'] for x in items],bank),'§202 25 percent sealed sample')
    return [render(x,bank,rubric_path(bank).read_text()) for x in items],rubric_path(bank).read_text()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();convert(read(a.spec),a.out)


if __name__=='__main__':main()
