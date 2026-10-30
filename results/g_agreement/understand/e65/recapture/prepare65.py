"""CPU-only positive-field export of selected frozen prompts. Never stage this module."""
import argparse
from collections import defaultdict
import gzip
import io
import tarfile
from datetime import datetime, timezone
from common65 import *
from preflight65 import exact_preflight

INVENTORY = HERE.parent / 'SOURCE_INVENTORY_V2_2026-10-27.json'
TOKENIZER = Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots') / REVISION / 'tokenizer.json'


def opaque(kind, ordinal):
    return hashlib.sha256(f'E65 {kind} {ordinal}'.encode()).hexdigest()[:32]


def package(path, members, base):
    with Path(path).open('xb') as raw:
        with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode='w') as t:
                for name in sorted(members):
                    data = (base / name).read_bytes(); info = tarfile.TarInfo(name)
                    info.size = len(data); info.mode = 0o644; info.mtime = 0
                    t.addfile(info, io.BytesIO(data))


def main():
    from tokenizers import Tokenizer
    require(sha(TOKENIZER) == TOKENIZER_SHA, 'Pinned tokenizer required')
    tokenizer = Tokenizer.from_file(str(TOKENIZER))
    special = {x['id'] for x in read(TOKENIZER)['added_tokens'] if x.get('special')}
    inventory = read(INVENTORY)
    require(not CACHE.exists(), 'Preserve existing build; never overwrite an invoked or sealed packet')
    CACHE.mkdir(parents=True); pod = CACHE / 'pod_inputs'; cpu = CACHE / 'cpu_only'
    pod.mkdir(); cpu.mkdir()
    bank = {'experiment': 'E65', 'schema': 'E65_BLIND_RECAPTURE_V1', 'rows': []}
    identity = {'experiment': 'E65', 'CPU_only': True, 'pod_staging_forbidden': True, 'rows': []}
    sources, offset, ordinal = {}, 0, 0
    for b in BANKS:
        meta = inventory['sources'][b]; source = Path(meta['path'])
        require(sha(source) == meta['sha256'], 'Frozen inventory source hash mismatch')
        text = source.read_text()
        items = [json.loads(x) for x in text.splitlines()] if source.suffix == '.jsonl' else json.loads(text)
        rows = defaultdict(list)
        for item in items:
            if item.get('split') == 'test': rows[item['feature']].append(item)
        require({k: len(v) for k, v in rows.items()} == meta['rows'], 'Inventory row populations changed')
        sources[b] = {'path': str(source), 'sha256': sha(source), 'rows': len(rows), 'test_items': sum(map(len, rows.values()))}
        for feature in sorted(rows):
            selected = sorted(rows[feature], key=lambda x: x['id'])[:20]
            require(len(selected) == 20 and len({x['id'] for x in rows[feature]}) == len(rows[feature]), 'Twenty unique sorted test items required')
            key = opaque('row', len(bank['rows'])); public = {'key': key, 'items': []}
            private = {'pod_row': key, 'bank': b, 'feature': feature, 'available_test_items': len(rows[feature]), 'items': []}
            for item in selected:
                require(isinstance(item['id'], str), 'Lexicographic frozen string item IDs required')
                ids = item['ids']; encoded = tokenizer.encode(item['text'], add_special_tokens=False)
                require(encoded.ids == ids and ids, 'Frozen full-prompt tokenization mismatch')
                start = next((i for i, token in enumerate(ids) if token not in special), None)
                require(start is not None, 'Prompt has no content tokens')
                public_item = {'id': opaque('item', ordinal), 'ids': list(ids), 'start': start, 'stop': len(ids), 'offset': offset}
                public['items'].append(public_item)
                private['items'].append({'pod_id': public_item['id'], 'original_item_id': item['id'], 'selection_index': len(private['items']),
                    'split': 'test', 'start': start, 'stop': len(ids), 'offset': offset,
                    'first_content_char_offset': encoded.offsets[start][0], 'read_char_end': encoded.offsets[-1][1]})
                offset += len(ids) - start; ordinal += 1
            bank['rows'].append(public); identity['rows'].append(private)
    selected, positions = validate_bank(bank)
    dump(pod / 'BANK.json', bank)
    dump(pod / 'INPUT_SEAL.json', {'experiment': 'E65', 'schema': 'E65_INPUT_SEAL_V1', 'files': {'BANK.json': sha(pod / 'BANK.json')}})
    identity['pod_input_seal_sha256'] = sha(pod / 'INPUT_SEAL.json')
    dump(cpu / 'IDENTITY_MAP.json', identity)
    dump(cpu / 'CPU_MAP_SEAL.json', {'experiment': 'E65', 'CPU_only': True, 'files': {'IDENTITY_MAP.json': sha(cpu / 'IDENTITY_MAP.json')}})
    dump(HERE / 'INPUT_BINDING.json', {'experiment': 'E65', 'authority_commit': 'db81ff0b10090394afa2c4a91bc420fb631dc0f7',
        'source_inventory_sha256': sha(INVENTORY), 'sources': sources, 'rows': len(bank['rows']), 'items': len(selected),
        'positions': positions, 'output_array_bytes': positions * DIM * 2,
        'input_seal_sha256': sha(pod / 'INPUT_SEAL.json'), 'tokenizer_sha256': TOKENIZER_SHA,
        'selection': 'First20 test items per distinct(bank,feature), lexicographic original item-ID order; all rows, no gate filtering',
        'start_convention': 'First non-special token; full original prompt forwarded, read token is final frozen ID',
        'items_with_leading_special_tokens': sum(x['start'] > 0 for x in selected), 'maximum_prompt_tokens': max(len(x['ids']) for x in selected),
        'CPU_identity_map': str((cpu / 'IDENTITY_MAP.json').relative_to(ROOT)), 'CPU_identity_map_sha256': sha(cpu / 'IDENTITY_MAP.json'),
        'CPU_map_seal_sha256': sha(cpu / 'CPU_MAP_SEAL.json'), 'model_calls': 0, 'reader_outputs_read': False})
    names = [str((HERE / n).relative_to(ROOT)) for n in ('common65.py', 'worker65.py', 'RUNTIME_PINS.json')]
    dump(HERE / 'POD_SOURCE_SEAL.json', {'experiment': 'E65', 'files_base': 'repository root', 'files': {n: sha(ROOT / n) for n in names}})
    names += [str((HERE / 'POD_SOURCE_SEAL.json').relative_to(ROOT))]
    names += [str((pod / n).relative_to(ROOT)) for n in ('BANK.json', 'INPUT_SEAL.json')]
    archive = CACHE / 'E65_POD_RECAPTURE_20261027.tar.gz'; package(archive, names, ROOT)
    desc = {'experiment': 'E65', 'path': str(archive.relative_to(ROOT)), 'sha256': sha(archive), 'bytes': archive.stat().st_size,
        'extract_relative_to': 'repository root', 'members': names, 'request_staged_separately': True,
        'labels_present': False, 'private_files_present': False}
    dump(HERE / 'POD_ARCHIVE.json', desc)
    dump(HERE / 'POD_STAGE_MANIFEST.json', {'experiment': 'E65', 'pod_archive_sha256': sha(archive),
        'files': {n: sha(ROOT / n) for n in names}, 'separately_bound_request': str((HERE / 'LAUNCH_REQUEST.json').relative_to(ROOT)),
        'CPU_identity_map_staging_forbidden': True})
    preflight = exact_preflight(archive); preflight['created_utc'] = datetime.now(timezone.utc).isoformat()
    dump(HERE / 'EXACT_ARCHIVE_CPU_PREFLIGHT.json', preflight)
    cpu_archive = CACHE / 'E65_CPU_IDENTITY_ONLY_20261027.tar.gz'
    package(cpu_archive, ['cpu_only/IDENTITY_MAP.json', 'cpu_only/CPU_MAP_SEAL.json'], CACHE)
    dump(HERE / 'CPU_IDENTITY_ARCHIVE.json', {'experiment': 'E65', 'CPU_only': True, 'pod_staging_forbidden': True,
        'path': str(cpu_archive.relative_to(ROOT)), 'sha256': sha(cpu_archive), 'bytes': cpu_archive.stat().st_size,
        'extract_relative_to': str(CACHE.relative_to(ROOT)), 'identity_map_sha256': sha(cpu / 'IDENTITY_MAP.json'),
        'cpu_map_seal_sha256': sha(cpu / 'CPU_MAP_SEAL.json')})
    print(json.dumps({'status': 'EXACT_ARCHIVE_CPU_PREFLIGHT_PASS', 'rows': len(bank['rows']), 'items': len(selected), 'positions': positions,
                     'output_array_bytes': positions*DIM*2, 'pod_archive_sha256': sha(archive)}))


if __name__ == '__main__': main()
