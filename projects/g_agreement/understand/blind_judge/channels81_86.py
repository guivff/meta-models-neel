"""E81–E86 sealed byte-preserving blind packets and separate budget admission."""
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

HERE = ROOT/'results/g_agreement/understand/e81_e86'
BANKS = {'E81','E82','E83','E84','E85','E86'}
AUTHORITY = {'E81':'§198', 'E82':'§198', 'E83':'§198', 'E84':'§199', 'E85':'§199', 'E86':'§199'}


def rubric_path(bank):
    require(bank in BANKS,'authorized E81–E86 bank')
    return HERE/'E85_RUBRIC202.txt' if bank == 'E85' else ROOT/'results/g_agreement/understand/blind_judge/later_banks/RUBRIC202_VALUE.txt'


def check_items(bank, items, rubric):
    require(type(items) is list and bool(items) and len({x['id'] for x in items}) == len(items),
            'complete unique opaque grid')
    expected = {'id','readout'} if bank == 'E85' else {'id','property','values','readout'}
    for item in items:
        require(type(item) is dict and set(item) == expected and
                re.fullmatch(r'[a-f0-9]{20,64}',item['id']) and type(item['readout']) is str,
                'blind packet fields and opaque IDs only')
        if bank != 'E85':
            require(type(item['property']) is str and type(item['values']) is dict and
                    set(item['values']) == {'A','B'}, 'frozen A/B descriptions')
            render_record(item,rubric)


def convert(spec,out):
    bank=spec['bank'];rubric=rubric_path(bank).read_bytes()
    require(sha(spec['source_seal'])==spec['source_seal_sha256'],'source seal pinned')
    s=read(spec['source_seal']);path=Path(spec['source_packet'])
    require(s['experiment']==bank and s.get('complete') is True and
            path.parent.resolve()==Path(spec['source_seal']).parent.resolve() and
            path.name in ('JUDGE_PACKET.json','BLIND_PACKET.jsonl') and
            sha(path)==s['files'][path.name] and s['rubric_sha256']==hashlib.sha256(rubric).hexdigest(),
            'complete sealed source packet and rubric hash')
    require(Path(spec['rubric']).read_bytes()==rubric,'source rubric bytes differ from frozen copy')
    blob=path.read_bytes()
    items=[json.loads(line) for line in blob.splitlines()] if path.suffix=='.jsonl' else json.loads(blob)
    check_items(bank,items,rubric.decode())
    require(s['n']==len(items),'sealed record count')
    if bank=='E86':
        require(s.get('value_order')=='truth_then_lie' and s.get('behaviour_gate_verified') is True,
                'truth A / lie B and wrong-answer gate custody')
    if bank=='E84':require(s.get('real_agent_dataset_gate_verified') is True,'conditional dataset gate')
    encoded=(json.dumps(items,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
    restored=json.loads(encoded)
    require(restored==items and all(a['id'].encode()==b['id'].encode() and
            a['readout'].encode()==b['readout'].encode() for a,b in zip(items,restored)),
            'byte-identical opaque IDs and readouts after format conversion')
    dest=Path(out);dest.mkdir(parents=True,exist_ok=False)
    (dest/'PACKET.json').write_bytes(encoded);(dest/'RUBRIC.txt').write_bytes(rubric)
    from .rubric202 import original_ids
    write(dest/'ORIGINAL_IDS.json',original_ids([x['id'] for x in items],bank))
    write(dest/'PACKET_SEAL.json',dict(experiment=bank,n=len(items),
        source_seal_sha256=spec['source_seal_sha256'],source_packet_sha256=sha(path),
        rubric_sha256=sha(dest/'RUBRIC.txt'),record_bytes_verified=True,
        files={name:sha(dest/name) for name in ('PACKET.json','RUBRIC.txt','ORIGINAL_IDS.json')}))


def budget_gate(bank,receipt,spec):
    from .cap_ledger import cap_entry
    cap=cap_entry(spec,bank)
    require(receipt.get('issuer')=='integrator' and receipt.get('verified') is True and
            receipt.get('bank')==bank and receipt.get('allocation_id') and
            receipt.get('reservation_included') is True, 'reserved integrator allocation')
    require(receipt.get('date_zurich') in ('2026-10-28','2026-10-29') and
            Decimal(str(receipt['reserved_judging_usd']))==cap, 'separate sealed bank cap')
    daily=Decimal(str(receipt['daily_committed_including_reservation_usd']))
    require(daily.is_finite() and cap<=daily<=300,
            'daily USD300 ceiling; global actual/unresolved USD100 checked per send')


def admission(spec):
    bank=spec['bank'];require(bank in BANKS and spec.get('channel')==('eval' if bank=='E85' else 'value'),
                               'bank-specific judging taxonomy')
    # Only sealed metadata and receipts are opened before the packet.
    require(sha(spec['budget_receipt'])==spec['budget_receipt_sha256'],'budget receipt seal')
    budget_gate(bank,read(spec['budget_receipt']),spec)
    require(sha(spec['receipt'])==spec['receipt_sha256'],'custody receipt seal')
    receipt=read(spec['receipt'])
    require(receipt.get('issuer')=='integrator' and receipt.get('verified') is True and
            receipt.get('bank')==bank and receipt.get('authority')==AUTHORITY[bank] and
            receipt.get('forecast_gate_verified') is True and receipt.get('bank_gate_verified') is True,
            'verified bank and applicable forecast gates')
    require(receipt.get('source_seals'),'sealed source custody')
    for s in receipt['source_seals']:require(sha(s['path'])==s['sha256'],'source seal custody')
    packet=Path(spec['packet']);ps=verify(packet/'PACKET_SEAL.json',spec['packet_seal_sha256'])
    require(ps['experiment']==bank and receipt['packet_seal_sha256']==spec['packet_seal_sha256'] and
            ps['source_seal_sha256'] in {x['sha256'] for x in receipt['source_seals']} and
            ps['n']==receipt['n'] and receipt['n']>0, 'complete packet binding')
    frozen=rubric_path(bank).read_bytes();rubric=(packet/'RUBRIC.txt').read_bytes()
    require(frozen==rubric and ps['rubric_sha256']==hashlib.sha256(rubric).hexdigest(),
            'frozen bank rubric bytes')
    source=read(packet/'PACKET.json');check_items(bank,source,rubric.decode())
    from .rubric202 import original_ids
    require(read(packet/'ORIGINAL_IDS.json')==original_ids([x['id'] for x in source],bank),
            '§202 original-rubric 25 percent sample seal')
    require(len(source)==receipt['n'],'complete judgment grid')
    original_seals=[x for x in receipt['source_seals'] if x['sha256']==ps['source_seal_sha256']]
    require(len(original_seals)==1,'unique original source seal')
    original=read(original_seals[0]['path'])
    source_parent=Path(original_seals[0]['path']).parent
    original_files=[source_parent/name for name,digest in original['files'].items()
                    if name in ('JUDGE_PACKET.json','BLIND_PACKET.jsonl') and sha(source_parent/name)==digest]
    require(len(original_files)==1 and sha(original_files[0])==ps['source_packet_sha256'],
            'original reader packet still matches frozen source seal')
    original_items=([json.loads(line) for line in original_files[0].read_bytes().splitlines()]
                    if original_files[0].suffix=='.jsonl' else read(original_files[0]))
    require(original_items==source,'converted/original record grid differs')
    if bank=='E86':require(original.get('value_order')=='truth_then_lie' and
                            original.get('behaviour_gate_verified') is True,'E86 truth/lie binding')
    if bank=='E84':require(original.get('real_agent_dataset_gate_verified') is True,'conditional E84')
    return ([dict(x) for x in source] if bank=='E85' else
            [render_record(x,rubric.decode()) for x in source]),rubric.decode()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();convert(read(a.spec),a.out)


if __name__=='__main__':main()
