"""Public three-item reader smoke references from sealed original H200 outputs."""
import argparse
import hashlib
import json
import tarfile
from pathlib import Path


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def prepare(bank, outputs, ledger, out, private_evidence):
    bank_seal = read(bank/'BANK_SEAL.json')
    assert sha(bank/'items.PRIVATE.json') == bank_seal['files']['items.PRIVATE.json']
    # Select before opening readouts; selection never depends on generated content.
    chosen = [x for x in read(bank/'items.PRIVATE.json') if x['split']=='test'][:3]
    assert len(chosen)==3 and len({x['id'] for x in chosen})==3
    ids = {x['id'] for x in chosen}
    found = {}
    seals, hardware_evidence = {}, []
    ledger_lines = ledger.read_text().splitlines()
    for root in outputs:
        seal = read(root/'OUTPUT_SEAL.json')
        assert seal['status']=='COMPLETE'
        for name, digest in seal['files'].items():
            p = root/name
            assert p.resolve().is_relative_to(root.resolve()) and sha(p)==digest
        assert sha(root/'ASSIGNMENT.json') == seal['files']['ASSIGNMENT.json']
        assignment = read(root/'ASSIGNMENT.json')
        events = [(i+1,line,json.loads(line)) for i,line in enumerate(ledger_lines)
                  if assignment['pod_id'] in line]
        assert any(x.get('gpu')=='NVIDIA H200' for _,_,x in events), 'H200 custody evidence required'
        gpu_lines = [(n,line,x) for n,line,x in events if x.get('gpu')=='NVIDIA H200']
        output_sha = sha(root/'OUTPUT_SEAL.json')
        seals[str(root)] = output_sha
        for n,line,x in gpu_lines:
            hardware_evidence.append(dict(source_output_seal_sha256=output_sha,
                assignment_sha256=sha(root/'ASSIGNMENT.json'), gpu_type='H200',
                original_ledger_line_number=n, original_ledger_line_sha256=hashlib.sha256(line.encode()).hexdigest()))
        for path in sorted((root/'jobs').glob('*.json')):
            records = read(path)
            records = records if isinstance(records,list) else [records]
            for record in records:
                if record.get('unit_id') not in ids or record.get('kind')!='text':
                    continue
                reader = record.get('reader')
                if reader not in ('oracle','nla'):
                    continue
                key = (record['unit_id'],reader)
                assert key not in found, 'original readout must be unique'
                assert record['reader_native_layer'] == (44 if reader=='oracle' else 42)
                if reader=='nla':
                    assert record['native_max_new_tokens']==512 and record['native_stop']=='</explanation>'
                assert isinstance(record['raw'],str)
                member = str(path.relative_to(root))
                assert sha(path)==seal['files'][member]
                found[key] = dict(raw=record['raw'], source_output_seal_sha256=output_sha,
                                  member=member, sha256=sha(path))
    assert len(found)==6, 'both unchanged native readers for all three fixed items'
    public, custody, scalar_hashes = [], {}, {}
    private = []
    for item in chosen:
        opaque = hashlib.sha256(('E95:H200_SMOKE:'+item['id']).encode()).hexdigest()[:32]
        public.append(dict(id=opaque,ids=item['ids'],max_new_tokens=128,
                           h200={reader:dict(raw=found[(item['id'],reader)]['raw'])
                                 for reader in ('oracle','nla')}))
        custody[opaque] = {reader:{k:v for k,v in found[(item['id'],reader)].items() if k!='raw'}
                           for reader in ('oracle','nla')}
        # The runtime's scalar field anchors an original member; both members are
        # independently bound above to the same complete original H200 source seal.
        scalar_hashes[opaque] = found[(item['id'],'nla')]['sha256']
        private.append(dict(id=opaque,source_id=item['id']))
    out.mkdir(parents=True,exist_ok=False)
    (out/'items.json').write_text(json.dumps(public,indent=2)+'\n')
    used = sorted({v['source_output_seal_sha256'] for x in custody.values() for v in x.values()})
    receipt = dict(status='VERIFIED_H200_REFERENCE',gpu_type='H200',mode='readers',
        selection='first three frozen E56 test items in bank order; no readout-based selection',
        bank_seal_sha256=sha(bank/'BANK_SEAL.json'),items_sha256=sha(out/'items.json'),
        source_output_seals=used,h200_readout_sha256=scalar_hashes,
        h200_reader_members=custody,hardware_custody=[x for x in hardware_evidence
                                                    if x['source_output_seal_sha256'] in used],
        first_output_utc='unknown',first_output_evidence=None,
        provenance_note='Reference packaging only; original H200 readouts are reused, no new output generated')
    (out/'REFERENCE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (out/'SMOKE_INPUT_SEAL.json').write_text(json.dumps(dict(experiment='E95',
        first_output_utc='unknown',first_output_evidence=None,
        files={p.name:sha(p) for p in out.iterdir() if p.is_file()}),indent=2)+'\n')
    assert sorted(p.name for p in out.iterdir()) == ['REFERENCE_RECEIPT.json','SMOKE_INPUT_SEAL.json','items.json']
    private_evidence.mkdir(parents=True,exist_ok=True)
    (private_evidence/'SOURCE_MAP.PRIVATE.json').write_text(json.dumps(private,indent=2)+'\n')
    archive = out.with_suffix('.tar.gz')
    with tarfile.open(archive,'w:gz') as tar:
        for path in sorted(out.iterdir()):
            tar.add(path,arcname=path.name)
    assert archive.stat().st_size <=20*1024*1024
    return dict(items=3,capabilities=['oracle','nla'],archive_sha256=sha(archive),
                input_seal_sha256=sha(out/'SMOKE_INPUT_SEAL.json'),archive_bytes=archive.stat().st_size,
                source_output_seals=used,GPU_calls=0,judge_calls=0)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--bank',required=True,type=Path)
    p.add_argument('--outputs',required=True,type=Path,nargs='+')
    p.add_argument('--ledger',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--private-evidence',required=True,type=Path)
    a=p.parse_args()
    print(json.dumps(prepare(a.bank,a.outputs,a.ledger,a.out,a.private_evidence)))
