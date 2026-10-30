"""E35 fallback token cache, frozen before production building, 2026-10-25.

No model or activation is loaded. Production writes exactly 20M unique source
token occurrences once, in corpus/file/row order, without replay or shuffling.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np

from gate_inputs import (CORPUS_SHA, MANIFEST_SHA, TOKENIZER_SHA, canonical,
                         dump_new, is_heldout, read_corpus, sha)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
N_TOKENS = 20_000_000
CHUNK_LENGTH = 512
SECTION79_TRAIN_DOCUMENTS = 1910
FINEWEB_REPOSITORY = 'HuggingFaceFW/fineweb-edu'
FINEWEB_REVISION = '87f09149ef4734204d70ed1d046ddc9ca3f2b8f9'
FINEWEB_FILES = [f'sample/10BT/{i:03}_00000.parquet' for i in range(14)]
TOKEN_FILE = 'tokens.uint32'
DOCUMENT_FILE = 'documents.jsonl'
SEALED_FILES = frozenset({'RUN_ONCE.json', TOKEN_FILE, DOCUMENT_FILE, 'MANIFEST.json'})
SOURCE_FILES = {'corpus': 'source-corpus.jsonl', 'manifest': 'source-corpus-manifest.json',
                'tokenizer': 'source-tokenizer.json'}
PRODUCTION_SEALED_FILES = SEALED_FILES | frozenset(SOURCE_FILES.values())
SOURCE_REQUIRED = frozenset({'kind', 'repository', 'revision', 'file', 'row'})
SOURCE_EXTRA = frozenset({'document_id', 'group_id', 'corpus_sha256'})
DOC_FIELDS = frozenset({'document_id', 'source', 'text_sha256', 'source_token_count',
                        'token_start', 'token_count', 'cache_start', 'cache_end',
                        'truncated', 'tokens_sha256'})


def _digest(value):
    return hashlib.sha256(canonical(value).encode('utf-8')).hexdigest()


def _hash_string(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _read(path):
    return json.loads(Path(path).read_text())


def _source_id(source):
    if (not isinstance(source, dict) or not SOURCE_REQUIRED <= set(source)
            or not set(source) <= SOURCE_REQUIRED | SOURCE_EXTRA):
        raise ValueError('source requires exact repository/revision/file/row identity')
    if source['kind'] not in ('section79', 'fineweb'):
        raise ValueError('unknown training source kind')
    if any(not isinstance(source[key], str) or not source[key]
           for key in SOURCE_REQUIRED - {'row'}):
        raise ValueError('nonempty source identity strings required')
    if type(source['row']) is not int or source['row'] < 0:
        raise ValueError('nonnegative source row required')
    if source['kind'] == 'section79':
        if (set(source) != SOURCE_REQUIRED | SOURCE_EXTRA
                or any(not isinstance(source[key], str) or not source[key] for key in SOURCE_EXTRA)
                or is_heldout(source['group_id'])):
            raise ValueError('complete source-group-excluded section79 identity required')
    elif set(source) != SOURCE_REQUIRED:
        raise ValueError('unexpected FineWeb source metadata')
    # Provenance fields cannot make a replay of the same source row look unique.
    return _digest({key: source[key] for key in sorted(SOURCE_REQUIRED)})


def _token_array(ids):
    values = np.asarray(ids)
    if values.ndim != 1:
        raise ValueError('one-dimensional token IDs required')
    # An empty Python list has float dtype, but contains no invalid token ID.
    if values.size == 0:
        return np.empty(0, dtype='<u4')
    if values.dtype.kind not in 'iu' or (values < 0).any() or (values > 2**32 - 1).any():
        raise ValueError('token IDs must be unsigned-32-bit integers')
    return np.ascontiguousarray(values, dtype='<u4')


def verify_fineweb_pin(pin):
    if (not isinstance(pin, dict) or pin.get('repository') != FINEWEB_REPOSITORY
            or pin.get('revision') != FINEWEB_REVISION or pin.get('repo_type') != 'dataset'
            or pin.get('configuration') != 'sample-10BT' or pin.get('split') != 'train'
            or pin.get('data_files') != FINEWEB_FILES):
        raise ValueError('exact committed FineWeb repository/revision/configuration/file order required')
    return pin


def verify_committed_source(source_commit, training_plan, fineweb_pin):
    """Require exact committed builder, input helper, full plan and dataset pin bytes."""
    if (not isinstance(source_commit, str) or len(source_commit) != 40
            or any(c not in '0123456789abcdef' for c in source_commit)):
        raise ValueError('exact source commit required before building production data')
    paths = [Path(__file__), HERE / 'gate_inputs.py', Path(training_plan), Path(fineweb_pin)]
    hashes = {}
    for path in paths:
        path = path.resolve()
        if not path.is_relative_to(HERE):
            raise ValueError('builder plan and pin must be committed within E35')
        relative = path.relative_to(ROOT).as_posix()
        result = subprocess.run(['git', '-C', str(ROOT), 'show', f'{source_commit}:{relative}'],
                                capture_output=True, check=False)
        if result.returncode or hashlib.sha256(result.stdout).hexdigest() != sha(path):
            raise ValueError('source/plan/pin bytes are not present at the specified build commit')
        hashes[relative] = sha(path)
    return hashes


def section79_documents(rows, encode, *, source_commit, corpus_file):
    """Keep original corpus order and every training position; exclude entire groups."""
    for row, record in enumerate(rows):
        if is_heldout(record['group_id']):
            continue
        source = {'kind': 'section79', 'repository': 'guivff/activation-readers',
                  'revision': source_commit, 'file': corpus_file, 'row': row,
                  'document_id': record['id'], 'group_id': record['group_id'],
                  'corpus_sha256': CORPUS_SHA}
        yield {'source': source, 'text_sha256': hashlib.sha256(record['text'].encode()).hexdigest(),
               'ids': encode(record['text'])}


def fineweb_documents(pin, encode, *, loader=None):
    """One pinned parquet shard at a time, retaining its native row order."""
    verify_fineweb_pin(pin)
    if loader is None:
        from datasets import load_dataset
        loader = load_dataset
    for filename in pin['data_files']:
        url = f'hf://datasets/{FINEWEB_REPOSITORY}@{FINEWEB_REVISION}/{filename}'
        dataset = loader('parquet', data_files={'train': [url]}, split='train', streaming=True)
        for row, record in enumerate(dataset):
            text = record.get('text') if isinstance(record, dict) else None
            if not isinstance(text, str):
                raise ValueError('FineWeb row requires raw text')
            yield {'source': {'kind': 'fineweb', 'repository': FINEWEB_REPOSITORY,
                              'revision': FINEWEB_REVISION, 'file': filename, 'row': row},
                   'text_sha256': hashlib.sha256(text.encode()).hexdigest(), 'ids': encode(text)}


def _inventory_entry(record):
    return {key: record[key] for key in ('document_id', 'source', 'text_sha256',
                                         'source_token_count', 'tokens_sha256')}


def _section79_inventory(cache, bindings):
    """Independently reproduce every permitted §79 document and full token hash."""
    paths = {key: Path(cache) / name for key, name in SOURCE_FILES.items()}
    expected = {'corpus': CORPUS_SHA, 'manifest': MANIFEST_SHA, 'tokenizer': TOKENIZER_SHA}
    if any(sha(paths[key]) != value for key, value in expected.items()):
        raise ValueError('cached corpus/manifest/tokenizer bytes differ from registered pins')
    rows = read_corpus(paths['corpus'], paths['manifest'])
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(paths['tokenizer']))
    corpus_file = _read(paths['manifest'])['corpus_path']
    inventory = []
    for document in section79_documents(rows,
            lambda text: tokenizer.encode(text, add_special_tokens=False).ids,
            source_commit=bindings['source_commit'], corpus_file=corpus_file):
        values = _token_array(document['ids'])
        inventory.append({'document_id': _source_id(document['source']), 'source': document['source'],
                          'text_sha256': document['text_sha256'], 'source_token_count': len(values),
                          'tokens_sha256': hashlib.sha256(values.tobytes()).hexdigest()})
    if len(inventory) != SECTION79_TRAIN_DOCUMENTS:
        raise ValueError('exact 1910 permitted section79 training documents required')
    return inventory


def _write_token_cache(out, documents, *, token_limit, chunk_length, bindings, production=False,
                        source_inputs=None):
    """Small parameters are exclusively for synthetic CPU tests, never a production CLI."""
    if (type(token_limit) is not int or token_limit <= 0 or type(chunk_length) is not int
            or chunk_length <= 0 or chunk_length > CHUNK_LENGTH):
        raise ValueError('positive token count and bounded chunk length required')
    if production and (token_limit != N_TOKENS or chunk_length != CHUNK_LENGTH):
        raise ValueError('production requires exactly 20M tokens and 512-position chunks')
    if production and (not isinstance(source_inputs, dict) or set(source_inputs) != set(SOURCE_FILES)):
        raise ValueError('production requires pinned source copies for independent cache admission')
    if not production and source_inputs is not None:
        raise ValueError('synthetic helper must not receive production source files')
    if not isinstance(bindings, dict) or not bindings:
        raise ValueError('immutable input bindings required')
    _digest(bindings)  # Fail before creating output for non-JSON/nonfinite bindings.
    out = Path(out).resolve()
    if 'cache' not in out.parts:
        raise ValueError('large token cache must be under a cache directory')
    out.mkdir(parents=True, exist_ok=False)
    dump_new(out / 'RUN_ONCE.json', {'schema': 'E35_TOKEN_CACHE_RUN_ONCE_V1',
        'mode': 'production' if production else 'synthetic', 'bindings_sha256': _digest(bindings),
        'target_tokens': token_limit, 'chunk_length': chunk_length,
        'started_at_utc': datetime.now(timezone.utc).isoformat()})
    if production:
        expected = {'corpus': CORPUS_SHA, 'manifest': MANIFEST_SHA, 'tokenizer': TOKENIZER_SHA}
        for key, filename in SOURCE_FILES.items():
            with Path(source_inputs[key]).open('rb') as source, (out / filename).open('xb') as destination:
                shutil.copyfileobj(source, destination, 1024 * 1024)
            if sha(out / filename) != expected[key]:
                raise ValueError('copied source bytes changed or differ from registered pins')
    seen = set()
    count = document_count = empty_count = partial_count = n_chunks = 0
    kind_counts = Counter()
    section_inventory = []
    with (out / TOKEN_FILE).open('xb') as tokens, (out / DOCUMENT_FILE).open('x', encoding='utf-8') as spans:
        for document in documents:
            if not isinstance(document, dict) or set(document) != {'source', 'text_sha256', 'ids'}:
                raise ValueError('exact internal token-document schema required')
            source = document['source']
            document_id = _source_id(source)
            if document_id in seen:
                raise ValueError('duplicate source identity; token occurrences cannot be replayed')
            seen.add(document_id)
            if not _hash_string(document['text_sha256']):
                raise ValueError('source text hash required')
            values = _token_array(document['ids'])
            kept = min(len(values), token_limit - count)
            if production and source['kind'] == 'section79' and kept < len(values):
                raise ValueError('all section79 training positions must fit before FineWeb supplementation')
            data = values[:kept].tobytes()
            tokens.write(data)
            span = {'document_id': document_id, 'source': source,
                    'text_sha256': document['text_sha256'], 'source_token_count': len(values),
                    'token_start': 0, 'token_count': kept, 'cache_start': count, 'cache_end': count + kept,
                    'truncated': kept < len(values), 'tokens_sha256': hashlib.sha256(data).hexdigest()}
            spans.write(canonical(span) + '\n')
            if source['kind'] == 'section79':
                section_inventory.append(_inventory_entry(span))
            count += kept
            document_count += 1
            empty_count += kept == 0
            partial_count += kept < len(values)
            n_chunks += (kept + chunk_length - 1) // chunk_length
            kind_counts[source['kind']] += kept
            if count == token_limit:
                break
    if count != token_limit:
        raise ValueError('source stream exhausted before exact unique-token target; incomplete cache retained')
    manifest = {'schema': 'E35_TRAINING_TOKEN_CACHE_V1',
        'mode': 'production' if production else 'synthetic',
        'target_tokens': token_limit, 'n_tokens': count, 'dtype': '<u4', 'chunk_length': chunk_length,
        'document_count': document_count, 'n_chunks': n_chunks, 'empty_document_count': empty_count,
        'partial_document_count': partial_count, 'tokens_by_source': dict(sorted(kind_counts.items())),
        'section79_inventory': section_inventory, 'section79_inventory_sha256': _digest(section_inventory),
        'order': 'original-section79-document-order-then-pinned-FineWeb-file-and-row-order',
        'context': 'nonoverlapping-within-document-chunks; reset-at-document-and-chunk-boundaries',
        'replayed_positions': 0, 'bindings': bindings}
    dump_new(out / 'MANIFEST.json', manifest)
    sealed_files = PRODUCTION_SEALED_FILES if production else SEALED_FILES
    seal = {'schema': 'E35_TRAINING_TOKEN_CACHE_SEAL_V1',
            'files': {filename: sha(out / filename) for filename in sorted(sealed_files)}}
    dump_new(out / 'SEAL.json', seal)
    return {'manifest': manifest, 'seal_sha256': sha(out / 'SEAL.json')}


def build_training_cache(out, *, corpus, corpus_manifest, tokenizer, fineweb_pin,
                         training_plan, source_commit):
    """Production builder: validate committed inputs before tokenization or network."""
    source_files = verify_committed_source(source_commit, training_plan, fineweb_pin)
    if sha(tokenizer) != TOKENIZER_SHA:
        raise ValueError('pinned tokenizer checksum mismatch')
    pin = verify_fineweb_pin(_read(fineweb_pin))
    plan = _read(training_plan)
    if not isinstance(plan, dict) or not plan:
        raise ValueError('complete nonempty training plan required')
    rows = read_corpus(corpus, corpus_manifest)
    manifest = _read(corpus_manifest)
    corpus_file = manifest.get('corpus_path')
    if not isinstance(corpus_file, str) or not corpus_file:
        raise ValueError('registered corpus source path required')
    bindings = {'source_commit': source_commit, 'source_files': source_files,
                'training_plan_sha256': sha(training_plan), 'fineweb_pin_sha256': sha(fineweb_pin),
                'corpus_sha256': CORPUS_SHA, 'corpus_manifest_sha256': MANIFEST_SHA,
                'tokenizer_sha256': TOKENIZER_SHA,
                'fineweb_repository': FINEWEB_REPOSITORY, 'fineweb_revision': FINEWEB_REVISION,
                'fineweb_files': FINEWEB_FILES, 'fineweb_configuration': 'sample-10BT'}
    # Imports and iteration below are lazy: the run-once guard is written first.
    def documents():
        from tokenizers import Tokenizer
        tok = Tokenizer.from_file(str(tokenizer))
        encode = lambda text: tok.encode(text, add_special_tokens=False).ids
        yield from section79_documents(rows, encode, source_commit=source_commit, corpus_file=corpus_file)
        yield from fineweb_documents(pin, encode)
    return _write_token_cache(out, documents(), token_limit=N_TOKENS,
                              chunk_length=CHUNK_LENGTH, bindings=bindings, production=True,
                              source_inputs={'corpus': corpus, 'manifest': corpus_manifest, 'tokenizer': tokenizer})


def verify_training_cache(cache, *, expected_seal_sha256=None, allow_synthetic=False):
    """Verify sealed bytes, contiguous source spans, no replay, and exact token count."""
    cache = Path(cache)
    if expected_seal_sha256 is not None and sha(cache / 'SEAL.json') != expected_seal_sha256:
        raise ValueError('assigned token-cache seal mismatch')
    seal = _read(cache / 'SEAL.json')
    if (set(seal) != {'schema', 'files'} or seal['schema'] != 'E35_TRAINING_TOKEN_CACHE_SEAL_V1'
            or not isinstance(seal['files'], dict)
            or set(seal['files']) not in (SEALED_FILES, PRODUCTION_SEALED_FILES)):
        raise ValueError('complete token-cache file seal required')
    for filename, digest in seal['files'].items():
        path = cache / filename
        if not _hash_string(digest) or not path.is_file() or sha(path) != digest:
            raise ValueError('sealed token-cache file changed or missing')
    manifest, guard = _read(cache / 'MANIFEST.json'), _read(cache / 'RUN_ONCE.json')
    if (manifest.get('schema') != 'E35_TRAINING_TOKEN_CACHE_V1'
            or manifest.get('dtype') != '<u4' or manifest.get('replayed_positions') != 0):
        raise ValueError('invalid token-cache manifest')
    mode = manifest.get('mode')
    n, chunk = manifest.get('n_tokens'), manifest.get('chunk_length')
    if (type(n) is not int or n <= 0 or manifest.get('target_tokens') != n
            or type(chunk) is not int or not 1 <= chunk <= CHUNK_LENGTH):
        raise ValueError('invalid cache token count or chunk size')
    if mode == 'production':
        if n != N_TOKENS or chunk != CHUNK_LENGTH or set(seal['files']) != PRODUCTION_SEALED_FILES:
            raise ValueError('production cache must contain exactly 20M tokens with 512-position chunks')
        bindings = manifest.get('bindings', {})
        if (not isinstance(bindings, dict) or bindings.get('corpus_sha256') != CORPUS_SHA
                or bindings.get('corpus_manifest_sha256') != MANIFEST_SHA
                or bindings.get('tokenizer_sha256') != TOKENIZER_SHA
                or bindings.get('fineweb_repository') != FINEWEB_REPOSITORY
                or bindings.get('fineweb_revision') != FINEWEB_REVISION
                or bindings.get('fineweb_files') != FINEWEB_FILES
                or bindings.get('fineweb_configuration') != 'sample-10BT'
                or any(not _hash_string(bindings.get(key)) for key in
                       ('training_plan_sha256', 'fineweb_pin_sha256'))):
            raise ValueError('production source bindings differ from registered pins')
        commit = bindings.get('source_commit')
        if not isinstance(commit, str) or len(commit) != 40 or any(c not in '0123456789abcdef' for c in commit):
            raise ValueError('production cache requires an exact source build commit')
        expected_section = _section79_inventory(cache, bindings)
    elif mode != 'synthetic' or not allow_synthetic:
        raise ValueError('synthetic token cache is forbidden in production')
    else:
        if set(seal['files']) != SEALED_FILES:
            raise ValueError('synthetic cache must not contain production source copies')
        expected_section = manifest.get('section79_inventory')
    if (not isinstance(expected_section, list) or manifest.get('section79_inventory') != expected_section
            or manifest.get('section79_inventory_sha256') != _digest(expected_section)):
        raise ValueError('section79 inventory differs from independently verified source documents')
    if (guard.get('schema') != 'E35_TOKEN_CACHE_RUN_ONCE_V1' or guard.get('mode') != mode
            or guard.get('target_tokens') != n or guard.get('chunk_length') != chunk
            or guard.get('bindings_sha256') != _digest(manifest.get('bindings'))):
        raise ValueError('run-once guard and manifest disagree')
    if (cache / TOKEN_FILE).stat().st_size != 4 * n:
        raise ValueError('token-byte count differs from exact manifest token count')
    seen, cursor, document_count, empty_count, partial_count, n_chunks = set(), 0, 0, 0, 0, 0
    kind_counts = Counter()
    last_section_row = -1
    section_index = 0
    last_fineweb_file, last_fineweb_row = -1, -1
    with (cache / DOCUMENT_FILE).open(encoding='utf-8') as spans, (cache / TOKEN_FILE).open('rb') as tokens:
        for line in spans:
            record = json.loads(line)
            if not isinstance(record, dict) or set(record) != DOC_FIELDS:
                raise ValueError('exact document-span schema required')
            document_id = _source_id(record['source'])
            if record['document_id'] != document_id or document_id in seen:
                raise ValueError('duplicate or mismatched document identity')
            seen.add(document_id)
            source = record['source']
            if source['kind'] == 'section79':
                if last_fineweb_file >= 0 or source['row'] <= last_section_row:
                    raise ValueError('section79 documents must retain original order before FineWeb')
                last_section_row = source['row']
                if mode == 'production' and (source['repository'] != 'guivff/activation-readers'
                        or source['revision'] != bindings.get('source_commit')
                        or source['corpus_sha256'] != CORPUS_SHA):
                    raise ValueError('section79 document provenance differs from input bindings')
                if (section_index >= len(expected_section)
                        or _inventory_entry(record) != expected_section[section_index]
                        or record['token_count'] != record['source_token_count']):
                    raise ValueError('section79 ordered full-document token inventory mismatch')
                section_index += 1
            else:
                if section_index != len(expected_section):
                    raise ValueError('FineWeb cannot precede completion of every section79 training document')
                if (source['repository'] != FINEWEB_REPOSITORY or source['revision'] != FINEWEB_REVISION
                        or source['file'] not in FINEWEB_FILES):
                    raise ValueError('FineWeb document provenance differs from registered pins')
                file_index = FINEWEB_FILES.index(source['file'])
                if (file_index < last_fineweb_file or file_index > last_fineweb_file + 1
                        or (file_index == last_fineweb_file and source['row'] != last_fineweb_row + 1)
                        or (file_index > last_fineweb_file and source['row'] != 0)):
                    raise ValueError('FineWeb documents must retain pinned file and native row order')
                last_fineweb_file, last_fineweb_row = file_index, source['row']
            size, original = record['token_count'], record['source_token_count']
            if (type(size) is not int or size < 0 or type(original) is not int or original < size
                    or type(record['token_start']) is not int or record['token_start'] != 0
                    or type(record['cache_start']) is not int or record['cache_start'] != cursor
                    or type(record['cache_end']) is not int or record['cache_end'] != cursor + size
                    or cursor + size > n or type(record['truncated']) is not bool
                    or record['truncated'] != (size < original) or partial_count
                    or not _hash_string(record['text_sha256'])):
                raise ValueError('invalid, overlapping, incomplete or replayed document span')
            if record['truncated'] and cursor + size != n:
                raise ValueError('only the final included document may be truncated')
            if mode == 'production' and source['kind'] == 'section79' and record['truncated']:
                raise ValueError('production cannot truncate section79 training documents')
            digest = hashlib.sha256()
            remaining = 4 * size
            while remaining:
                block = tokens.read(min(remaining, 1024 * 1024))
                if not block:
                    raise ValueError('unexpected end of token bytes')
                digest.update(block)
                remaining -= len(block)
            if digest.hexdigest() != record['tokens_sha256']:
                raise ValueError('per-document token hash mismatch')
            cursor += size
            document_count += 1
            empty_count += size == 0
            partial_count += record['truncated']
            n_chunks += (size + chunk - 1) // chunk
            kind_counts[record['source']['kind']] += size
    if (cursor != n or section_index != len(expected_section)
            or manifest.get('document_count') != document_count or manifest.get('n_chunks') != n_chunks
            or manifest.get('empty_document_count') != empty_count
            or manifest.get('partial_document_count') != partial_count
            or manifest.get('tokens_by_source') != dict(sorted(kind_counts.items()))):
        raise ValueError('document inventory does not cover exact token cache')
    return manifest


def iter_training_chunks(cache, *, expected_seal_sha256=None, allow_synthetic=False):
    """Yield each retained source position once in <=512-token document-local chunks."""
    cache = Path(cache)
    manifest = verify_training_cache(cache, expected_seal_sha256=expected_seal_sha256,
                                      allow_synthetic=allow_synthetic)
    data = np.memmap(cache / TOKEN_FILE, dtype='<u4', mode='r', shape=(manifest['n_tokens'],))
    with (cache / DOCUMENT_FILE).open(encoding='utf-8') as spans:
        for line in spans:
            record = json.loads(line)
            for start in range(0, record['token_count'], manifest['chunk_length']):
                end = min(start + manifest['chunk_length'], record['token_count'])
                cache_start = record['cache_start'] + start
                yield {'document_id': record['document_id'], 'source': record['source'],
                       'token_start': start, 'token_end': end,
                       'ids': data[cache_start:record['cache_start'] + end].tolist()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('out', 'corpus', 'corpus-manifest', 'tokenizer', 'fineweb-pin', 'training-plan'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    args = parser.parse_args()
    receipt = build_training_cache(args.out, corpus=args.corpus, corpus_manifest=args.corpus_manifest,
        tokenizer=args.tokenizer, fineweb_pin=args.fineweb_pin, training_plan=args.training_plan,
        source_commit=args.source_commit)
    print(canonical({'status': 'TRAINING_TOKEN_CACHE_SEALED', 'n_tokens': N_TOKENS,
                     'seal_sha256': receipt['seal_sha256'], 'GPU_hours': 0}))


if __name__ == '__main__':
    main()
