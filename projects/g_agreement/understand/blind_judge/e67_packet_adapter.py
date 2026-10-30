"""Format-only E67 conversion; one sealed W-sae packet per invocation, no judging."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from projects.g_agreement.readerbench.io import sha, write
from projects.g_agreement.readerbench.scoring import require

PACKETS = {'packet_01.jsonl': 'packet_0', 'packet_02.jsonl': 'packet_1'}


def convert(source, seal_sha256, packet_name, output, wave=1):
    require(type(wave) is int and wave in (1,2), 'registered E67 wave')
    source, output = Path(source), Path(output)
    require(packet_name in PACKETS, 'one registered packet per job')
    seal_bytes = (source/'JUDGE_PACKET_SEAL.json').read_bytes()
    require(hashlib.sha256(seal_bytes).hexdigest() == seal_sha256, 'source seal hash mismatch')
    seal = json.loads(seal_bytes)
    require(seal.get('independent_packet_contexts_required') is True, 'independent contexts required')
    require(set(PACKETS) | {'CLAIMS_RUBRIC.txt'} <= set(seal['files']), 'missing sealed packet/rubric')
    blobs = {}
    for name, digest in seal['files'].items():
        require(Path(name).name == name and name not in ('.', '..'), 'source member must be a filename')
        blob = (source/name).read_bytes()
        require(hashlib.sha256(blob).hexdigest() == digest, 'source member hash mismatch')
        if name in (packet_name, 'CLAIMS_RUBRIC.txt'):
            blobs[name] = blob
    rubric_bytes = blobs['CLAIMS_RUBRIC.txt']
    rubric = rubric_bytes.decode('utf-8')  # no newline or Unicode normalization
    rows = [json.loads(line) for line in blobs[packet_name].splitlines()]
    require(rows and all(isinstance(x, dict) and set(x) == {'id','prompt_text','readout'} for x in rows), 'source schema')
    require(all(all(isinstance(v, str) for v in x.values()) and re.fullmatch('[a-f0-9]{20,64}', x['id']) for x in rows), 'source strings/opaque IDs')
    require(len({x['id'] for x in rows}) == len(rows), 'duplicate IDs')
    adapted = [dict(id=x['id'], prompt=x['prompt_text'], readout=x['readout'], rubric=rubric) for x in rows]
    encoded = (json.dumps(adapted, ensure_ascii=False, indent=2, allow_nan=False)+'\n').encode('utf-8')
    restored = json.loads(encoded)
    for old, new in zip(rows, restored):
        for before, after in (('id','id'), ('prompt_text','prompt'), ('readout','readout')):
            require(old[before].encode('utf-8') == new[after].encode('utf-8'), 'field byte preservation')
        require(new['rubric'].encode('utf-8') == rubric_bytes, 'rubric byte preservation')
    output.mkdir(parents=True, exist_ok=False)
    (output/'PACKET.json').write_bytes(encoded)
    (output/'CLAIMS_RUBRIC.md').write_bytes(rubric_bytes)
    write(output/'PACKET_SEAL.json', dict(experiment='E67', wave=wave, packet_id=PACKETS[packet_name], n=len(rows),
        source_packet=packet_name, source_seal_sha256=seal_sha256,
        source_packet_sha256=seal['files'][packet_name], rubric_sha256=seal['files']['CLAIMS_RUBRIC.txt'],
        separate_job_required=True, utf8_field_bytes_verified=True,
        files={name:sha(output/name) for name in ('PACKET.json','CLAIMS_RUBRIC.md')}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--source-seal-sha256', required=True)
    p.add_argument('--packet', choices=PACKETS, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--wave', type=int, choices=(1,2), default=1)
    a=p.parse_args()
    convert(a.source, a.source_seal_sha256, a.packet, a.output, a.wave)
    print('One separate E67 job converted; source hashes and field bytes verified; no judging.')


if __name__ == '__main__':
    main()
