"""Synthetic CPU tests only: no production corpus, dataset request or GPU."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    SPEC = importlib.util.spec_from_file_location('e35_training_stream_under_test', HERE / 'training_stream.py')
    S = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(S)
finally:
    sys.path.remove(str(HERE))


def group(held):
    return next(f'synthetic-group-{i}' for i in range(1000) if S.is_heldout(f'synthetic-group-{i}') is held)


def fineweb_source(row, file_index=0):
    return {'kind': 'fineweb', 'repository': S.FINEWEB_REPOSITORY,
            'revision': S.FINEWEB_REVISION, 'file': S.FINEWEB_FILES[file_index], 'row': row}


def section_source(row, held=False):
    return {'kind': 'section79', 'repository': 'guivff/activation-readers',
            'revision': 'a' * 40, 'file': 'synthetic/corpus.jsonl', 'row': row,
            'document_id': f'doc-{row}', 'group_id': group(held), 'corpus_sha256': S.CORPUS_SHA}


def document(row, ids, *, source=None, text='synthetic text'):
    return {'source': fineweb_source(row) if source is None else source,
            'text_sha256': hashlib.sha256(text.encode()).hexdigest(), 'ids': ids}


def pin():
    return {'repository': S.FINEWEB_REPOSITORY, 'revision': S.FINEWEB_REVISION,
            'repo_type': 'dataset', 'configuration': 'sample-10BT', 'split': 'train',
            'data_files': list(S.FINEWEB_FILES)}


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, ensure_ascii=False) + '\n')


def spans(cache):
    return [json.loads(line) for line in (cache / S.DOCUMENT_FILE).read_text().splitlines()]


def write_spans(cache, records):
    (cache / S.DOCUMENT_FILE).write_text(''.join(S.canonical(record) + '\n' for record in records))


def reseal(cache):
    write(cache / 'SEAL.json', {'schema': 'E35_TRAINING_TOKEN_CACHE_SEAL_V1',
                              'files': {name: S.sha(cache / name) for name in sorted(S.SEALED_FILES)}})


def build_small(cache, documents=None, *, limit=13, chunk=4):
    documents = ([document(0, list(range(5))), document(1, list(range(5, 11))),
                  document(2, list(range(11, 18)))] if documents is None else documents)
    return S._write_token_cache(cache, documents, token_limit=limit, chunk_length=chunk,
                                bindings={'synthetic': True})


@pytest.fixture
def cache(tmp_path):
    value = tmp_path / 'cache' / 'synthetic'
    build_small(value)
    return value


def test_fixed_production_contract():
    assert S.N_TOKENS == 20_000_000
    assert S.CHUNK_LENGTH == 512
    assert len(S.FINEWEB_FILES) == 14
    assert S.FINEWEB_FILES[0] == 'sample/10BT/000_00000.parquet'
    assert S.FINEWEB_FILES[-1] == 'sample/10BT/013_00000.parquet'
    assert S.FINEWEB_REVISION == '87f09149ef4734204d70ed1d046ddc9ca3f2b8f9'


def test_complete_cache_little_endian_count_and_partial_final_document(cache):
    manifest = S.verify_training_cache(cache, allow_synthetic=True)
    assert manifest['n_tokens'] == 13
    assert manifest['n_chunks'] == 5
    assert manifest['document_count'] == 3
    assert manifest['partial_document_count'] == 1
    assert manifest['tokens_by_source'] == {'fineweb': 13}
    assert np.fromfile(cache / S.TOKEN_FILE, dtype='<u4').tolist() == list(range(13))
    records = spans(cache)
    assert [r['cache_start'] for r in records] == [0, 5, 11]
    assert [r['cache_end'] for r in records] == [5, 11, 13]
    assert [r['source_token_count'] for r in records] == [5, 6, 7]
    assert [r['token_count'] for r in records] == [5, 6, 2]
    assert [r['truncated'] for r in records] == [False, False, True]
    assert (cache / S.TOKEN_FILE).stat().st_size == 52


def test_chunks_cover_each_occurrence_once_and_reset_at_document_boundary(cache):
    chunks = list(S.iter_training_chunks(cache, allow_synthetic=True))
    assert [c['ids'] for c in chunks] == [[0, 1, 2, 3], [4], [5, 6, 7, 8], [9, 10], [11, 12]]
    assert [(c['source']['row'], c['token_start'], c['token_end']) for c in chunks] == [
        (0, 0, 4), (0, 4, 5), (1, 0, 4), (1, 4, 6), (2, 0, 2)]
    occurrences = [(c['document_id'], p) for c in chunks for p in range(c['token_start'], c['token_end'])]
    assert len(occurrences) == len(set(occurrences)) == 13


def test_full_512_chunks_keep_document_tail_and_last_partial_tail(tmp_path):
    cache = tmp_path / 'cache' / 'tails'
    build_small(cache, [document(0, list(range(1025))), document(1, [3000, 3001, 3002, 3003, 3004])],
                limit=1028, chunk=512)
    chunks = list(S.iter_training_chunks(cache, allow_synthetic=True))
    assert [len(c['ids']) for c in chunks] == [512, 512, 1, 3]
    assert chunks[-2]['ids'] == [1024]
    assert chunks[-1]['ids'] == [3000, 3001, 3002]
    assert chunks[-1]['token_start'] == 0


def test_token_and_span_bytes_deterministic_in_original_order(tmp_path):
    a, b = tmp_path / 'cache' / 'a', tmp_path / 'cache' / 'b'
    build_small(a)
    build_small(b)
    for filename in (S.TOKEN_FILE, S.DOCUMENT_FILE):
        assert (a / filename).read_bytes() == (b / filename).read_bytes()


def test_duplicate_text_remains_distinct_source_occurrences(tmp_path):
    cache = tmp_path / 'cache' / 'duplicates'
    build_small(cache, [document(0, [1, 1], text='same'), document(1, [1, 1], text='same')], limit=4)
    manifest = S.verify_training_cache(cache, allow_synthetic=True)
    records = spans(cache)
    assert manifest['n_tokens'] == 4
    assert records[0]['text_sha256'] == records[1]['text_sha256']
    assert records[0]['document_id'] != records[1]['document_id']


def test_duplicate_source_identity_rejected_instead_of_silently_skipped(tmp_path):
    cache = tmp_path / 'cache' / 'replay'
    with pytest.raises(ValueError, match='duplicate source identity'):
        build_small(cache, [document(0, [1, 2]), document(0, [3, 4])], limit=4)
    assert (cache / 'RUN_ONCE.json').is_file()
    assert not (cache / 'SEAL.json').exists()


def test_changed_provenance_cannot_hide_replayed_source_row(tmp_path):
    source = section_source(0)
    other = {**source, 'document_id': 'different name'}
    assert S._source_id(source) == S._source_id(other)
    with pytest.raises(ValueError, match='duplicate source identity'):
        build_small(tmp_path / 'cache' / 'replay', [document(0, [1], source=source),
                    document(1, [2], source=other)], limit=2)


def test_no_read_ahead_after_exact_target(tmp_path):
    def records():
        yield document(0, [1, 2, 3])
        raise AssertionError('must not request another row after target')
    build_small(tmp_path / 'cache' / 'bounded', records(), limit=3)


def test_empty_documents_are_accounted_without_fake_tokens(tmp_path):
    cache = tmp_path / 'cache' / 'empty'
    build_small(cache, [document(0, []), document(1, [42])], limit=1)
    manifest = S.verify_training_cache(cache, allow_synthetic=True)
    assert manifest['document_count'] == 2
    assert manifest['empty_document_count'] == 1
    assert manifest['n_chunks'] == 1
    assert list(S.iter_training_chunks(cache, allow_synthetic=True))[0]['ids'] == [42]


def test_exhaustion_retains_consumed_guard_and_cannot_resume(tmp_path):
    cache = tmp_path / 'cache' / 'incomplete'
    with pytest.raises(ValueError, match='exhausted'):
        build_small(cache, [document(0, [1, 2])], limit=3)
    with pytest.raises(FileExistsError):
        build_small(cache, [document(0, [1, 2, 3])], limit=3)
    assert (cache / 'RUN_ONCE.json').is_file()
    assert not (cache / 'SEAL.json').exists()


def test_successful_cache_cannot_be_overwritten(cache):
    before = (cache / S.TOKEN_FILE).read_bytes()
    with pytest.raises(FileExistsError):
        build_small(cache)
    assert (cache / S.TOKEN_FILE).read_bytes() == before


def test_cache_directory_required(tmp_path):
    with pytest.raises(ValueError, match='cache directory'):
        build_small(tmp_path / 'wrong', [document(0, [1])], limit=1)


@pytest.mark.parametrize('limit,chunk', [(0, 4), (-1, 4), (True, 4), (2.0, 4), (1, 0), (1, 513), (1, True)])
def test_invalid_count_or_chunk_fails_before_output(tmp_path, limit, chunk):
    cache = tmp_path / 'cache' / 'invalid'
    with pytest.raises(ValueError):
        build_small(cache, [document(0, [1])], limit=limit, chunk=chunk)
    assert not cache.exists()


def test_production_cannot_use_small_parameters(tmp_path):
    with pytest.raises(ValueError, match='exactly 20M'):
        S._write_token_cache(tmp_path / 'cache' / 'prod', [], token_limit=10,
                              chunk_length=512, bindings={'synthetic': True}, production=True)


@pytest.mark.parametrize('ids', [[-1], [2**32], [1.2], [True], [[1, 2]], ['1']])
def test_invalid_token_ids_rejected(tmp_path, ids):
    with pytest.raises(ValueError):
        build_small(tmp_path / 'cache' / 'ids', [document(0, ids)], limit=1)


def test_uint32_upper_bound_preserved(tmp_path):
    cache = tmp_path / 'cache' / 'max'
    build_small(cache, [document(0, [0, 2**32 - 1])], limit=2)
    assert list(S.iter_training_chunks(cache, allow_synthetic=True))[0]['ids'] == [0, 2**32 - 1]


def test_section79_excludes_groups_keeps_original_order_and_every_position():
    held, train = group(True), group(False)
    rows = [{'id': 'a', 'group_id': train, 'text': 'a' * 600},
            {'id': 'b', 'group_id': held, 'text': 'forbidden'},
            {'id': 'c', 'group_id': train, 'text': 'c' * 514},
            {'id': 'd', 'group_id': held, 'text': 'also forbidden'}]
    encoded = []
    def encode(text):
        encoded.append(text)
        return list(range(len(text)))
    documents = list(S.section79_documents(rows, encode, source_commit='a' * 40, corpus_file='corpus.jsonl'))
    assert [d['source']['row'] for d in documents] == [0, 2]
    assert [d['source']['document_id'] for d in documents] == ['a', 'c']
    assert [len(d['ids']) for d in documents] == [600, 514]
    assert encoded == ['a' * 600, 'c' * 514]


def test_direct_heldout_source_rejected(tmp_path):
    with pytest.raises(ValueError, match='source-group-excluded'):
        build_small(tmp_path / 'cache' / 'heldout', [document(0, [1], source=section_source(0, True))], limit=1)


def test_fineweb_each_pinned_file_requested_once_in_order():
    calls = []
    def loader(*args, **kwargs):
        index = len(calls)
        calls.append((args, kwargs))
        return [{'text': f'{index}:0'}, {'text': f'{index}:1'}]
    documents = list(S.fineweb_documents(pin(), lambda text: [int(text.split(':')[0]), int(text[-1])], loader=loader))
    assert len(calls) == 14
    assert len(documents) == 28
    for index, (args, kwargs) in enumerate(calls):
        assert args == ('parquet',)
        assert kwargs == {'data_files': {'train': [f'hf://datasets/{S.FINEWEB_REPOSITORY}@{S.FINEWEB_REVISION}/{S.FINEWEB_FILES[index]}']},
                          'split': 'train', 'streaming': True}
    assert [(d['source']['file'], d['source']['row']) for d in documents] == [
        (file, row) for file in S.FINEWEB_FILES for row in range(2)]


def test_fineweb_file_loading_is_lazy():
    calls = []
    def loader(*args, **kwargs):
        calls.append(kwargs)
        return [{'text': 'first'}, {'text': 'second'}]
    documents = S.fineweb_documents(pin(), lambda text: [len(text)], loader=loader)
    assert calls == []
    assert next(documents)['ids'] == [5]
    assert len(calls) == 1


@pytest.mark.parametrize('field,value', [('revision', 'main'), ('repository', 'other'),
    ('configuration', 'sample-100BT'), ('split', 'test'), ('repo_type', 'model'),
    ('data_files', list(reversed(S.FINEWEB_FILES))), ('data_files', S.FINEWEB_FILES + S.FINEWEB_FILES[:1])])
def test_changed_fineweb_pin_rejected_before_loader(field, value):
    changed = {**pin(), field: value}
    def loader(*args, **kwargs):
        raise AssertionError('must not access a dataset with invalid pins')
    with pytest.raises(ValueError, match='committed FineWeb'):
        next(S.fineweb_documents(changed, lambda text: [], loader=loader))


@pytest.mark.parametrize('record', [{}, {'text': None}, {'text': 123}, 'raw'])
def test_fineweb_nontext_row_fails_closed(record):
    with pytest.raises(ValueError, match='raw text'):
        next(S.fineweb_documents(pin(), lambda text: [], loader=lambda *args, **kwargs: [record]))


def test_synthetic_cache_cannot_enter_production(cache):
    with pytest.raises(ValueError, match='synthetic token cache'):
        S.verify_training_cache(cache)
    with pytest.raises(ValueError, match='synthetic token cache'):
        next(S.iter_training_chunks(cache))


def test_expected_seal_digest_checked(cache):
    receipt = S.verify_training_cache(cache, expected_seal_sha256=S.sha(cache / 'SEAL.json'), allow_synthetic=True)
    assert receipt['n_tokens'] == 13
    with pytest.raises(ValueError, match='assigned token-cache seal'):
        S.verify_training_cache(cache, expected_seal_sha256='0' * 64, allow_synthetic=True)


@pytest.mark.parametrize('filename', sorted(S.SEALED_FILES))
def test_each_sealed_file_tamper_rejected(cache, filename):
    with (cache / filename).open('ab') as stream:
        stream.write(b' ')
    with pytest.raises(ValueError, match='sealed token-cache file'):
        S.verify_training_cache(cache, allow_synthetic=True)


def test_missing_sealed_file_rejected(cache):
    (cache / S.TOKEN_FILE).unlink()
    with pytest.raises(ValueError, match='sealed token-cache file'):
        S.verify_training_cache(cache, allow_synthetic=True)


def test_extra_seal_path_cannot_escape_cache(cache):
    value = json.loads((cache / 'SEAL.json').read_text())
    value['files']['../elsewhere'] = '0' * 64
    write(cache / 'SEAL.json', value)
    with pytest.raises(ValueError, match='complete token-cache file seal'):
        S.verify_training_cache(cache, allow_synthetic=True)


def test_token_file_size_checked_even_with_resealed_files(cache):
    with (cache / S.TOKEN_FILE).open('ab') as stream:
        stream.write(b'\x00\x00\x00\x00')
    reseal(cache)
    with pytest.raises(ValueError, match='token-byte count'):
        S.verify_training_cache(cache, allow_synthetic=True)


def test_per_document_token_hash_checked_even_with_resealed_files(cache):
    data = bytearray((cache / S.TOKEN_FILE).read_bytes())
    data[0] = 100
    (cache / S.TOKEN_FILE).write_bytes(data)
    reseal(cache)
    with pytest.raises(ValueError, match='per-document token hash'):
        S.verify_training_cache(cache, allow_synthetic=True)


@pytest.mark.parametrize('field,value', [('token_start', 1), ('token_count', True), ('cache_start', 1),
    ('cache_end', 6), ('source_token_count', 4), ('truncated', True), ('text_sha256', 'bad')])
def test_malformed_span_rejected_after_reseal(cache, field, value):
    records = spans(cache)
    records[0][field] = value
    write_spans(cache, records)
    reseal(cache)
    with pytest.raises(ValueError):
        S.verify_training_cache(cache, allow_synthetic=True)


def test_replayed_source_rejected_after_reseal(cache):
    records = spans(cache)
    records[1]['source'] = records[0]['source']
    records[1]['document_id'] = records[0]['document_id']
    write_spans(cache, records)
    reseal(cache)
    with pytest.raises(ValueError, match='duplicate or mismatched'):
        S.verify_training_cache(cache, allow_synthetic=True)


@pytest.mark.parametrize('field,value', [('document_count', 4), ('n_chunks', 6), ('empty_document_count', 1),
    ('partial_document_count', 0), ('tokens_by_source', {'fineweb': 12})])
def test_inventory_recomputed_after_reseal(cache, field, value):
    manifest = json.loads((cache / 'MANIFEST.json').read_text())
    manifest[field] = value
    write(cache / 'MANIFEST.json', manifest)
    reseal(cache)
    with pytest.raises(ValueError, match='document inventory'):
        S.verify_training_cache(cache, allow_synthetic=True)


def test_manifest_guard_binding_checked_after_reseal(cache):
    manifest = json.loads((cache / 'MANIFEST.json').read_text())
    manifest['bindings']['changed'] = True
    write(cache / 'MANIFEST.json', manifest)
    reseal(cache)
    with pytest.raises(ValueError, match='run-once guard'):
        S.verify_training_cache(cache, allow_synthetic=True)


@pytest.mark.parametrize('source_change', [lambda s: s.update(row=4),
    lambda s: s.update(file=S.FINEWEB_FILES[1]), lambda s: s.update(revision='main')])
def test_native_fineweb_row_file_revision_order_verified(cache, source_change):
    records = spans(cache)
    source_change(records[1]['source'])
    records[1]['document_id'] = S._source_id(records[1]['source'])
    write_spans(cache, records)
    reseal(cache)
    with pytest.raises(ValueError):
        S.verify_training_cache(cache, allow_synthetic=True)


def test_section79_cannot_follow_fineweb(tmp_path):
    cache = tmp_path / 'cache' / 'order'
    build_small(cache, [document(0, [1]), document(0, [2], source=section_source(0))], limit=2)
    with pytest.raises(ValueError, match='completion of every section79'):
        S.verify_training_cache(cache, allow_synthetic=True)


def test_section79_original_row_order_verified(tmp_path):
    cache = tmp_path / 'cache' / 'order'
    build_small(cache, [document(1, [1], source=section_source(1)), document(0, [2], source=section_source(0))], limit=2)
    with pytest.raises(ValueError, match='original order before FineWeb'):
        S.verify_training_cache(cache, allow_synthetic=True)


def test_production_builder_defers_tokenization_until_guard_and_uses_no_specials(tmp_path, monkeypatch):
    paths = {name: tmp_path / name for name in ('corpus', 'manifest', 'tokenizer', 'pin', 'plan')}
    for path in paths.values():
        path.write_text('{}')
    write(paths['pin'], pin())
    write(paths['plan'], {'frozen': True})
    write(paths['manifest'], {'corpus_path': 'synthetic/corpus.jsonl'})
    tokenizer_calls = []
    class FakeTokenizer:
        @staticmethod
        def from_file(path):
            tokenizer_calls.append(('load', path))
            return FakeTokenizer()
        def encode(self, text, *, add_special_tokens):
            assert add_special_tokens is False
            tokenizer_calls.append(('encode', text))
            return SimpleNamespace(ids=[11, 12, 13])
    monkeypatch.setitem(sys.modules, 'tokenizers', SimpleNamespace(Tokenizer=FakeTokenizer))
    monkeypatch.setattr(S, 'verify_committed_source', lambda *args: {'builder': 'a' * 64})
    original_sha = S.sha
    monkeypatch.setattr(S, 'sha', lambda path: S.TOKENIZER_SHA if Path(path) == paths['tokenizer'] else original_sha(path))
    rows = [{'id': 'keep', 'group_id': group(False), 'text': 'raw full text'},
            {'id': 'exclude', 'group_id': group(True), 'text': 'must not tokenize'}]
    monkeypatch.setattr(S, 'read_corpus', lambda *args: rows)
    def writer(out, documents, **kwargs):
        assert tokenizer_calls == []
        assert kwargs['production'] is True
        assert kwargs['token_limit'] == 20_000_000
        assert kwargs['chunk_length'] == 512
        assert kwargs['bindings']['training_plan_sha256'] == original_sha(paths['plan'])
        first = next(documents)
        assert first['ids'] == [11, 12, 13]
        assert first['source']['row'] == 0
        return {'synthetic_intercept': True}
    monkeypatch.setattr(S, '_write_token_cache', writer)
    result = S.build_training_cache(tmp_path / 'cache' / 'unused', corpus=paths['corpus'],
        corpus_manifest=paths['manifest'], tokenizer=paths['tokenizer'], fineweb_pin=paths['pin'],
        training_plan=paths['plan'], source_commit='a' * 40)
    assert result == {'synthetic_intercept': True}
    assert tokenizer_calls == [('load', str(paths['tokenizer'])), ('encode', 'raw full text')]


def test_production_requires_committed_source_before_any_input_read(tmp_path, monkeypatch):
    def fail(*args):
        raise ValueError('source not committed')
    monkeypatch.setattr(S, 'verify_committed_source', fail)
    with pytest.raises(ValueError, match='source not committed'):
        S.build_training_cache(tmp_path / 'cache' / 'never', corpus='absent', corpus_manifest='absent',
            tokenizer='absent', fineweb_pin='absent', training_plan='absent', source_commit='a' * 40)
    assert not (tmp_path / 'cache').exists()


@pytest.mark.parametrize('commit', ['main', '', 'a' * 39, 'g' * 40])
def test_exact_build_commit_required(commit):
    with pytest.raises(ValueError, match='exact source commit'):
        S.verify_committed_source(commit, 'not-read', 'not-read')


def test_committed_source_hashes_and_plan_location(tmp_path, monkeypatch):
    root = tmp_path / 'repo'
    here = root / 'results' / 'g_agreement' / 'understand' / 'e35'
    here.mkdir(parents=True)
    files = [here / name for name in ('training_stream.py', 'gate_inputs.py', 'plan.json', 'pin.json')]
    for i, path in enumerate(files):
        path.write_text(f'synthetic committed bytes {i}')
    monkeypatch.setattr(S, 'HERE', here)
    monkeypatch.setattr(S, 'ROOT', root)
    monkeypatch.setattr(S, '__file__', str(files[0]))
    calls = []
    def run(command, **kwargs):
        calls.append(command)
        relative = command[-1].split(':', 1)[1]
        return SimpleNamespace(returncode=0, stdout=(root / relative).read_bytes())
    monkeypatch.setattr(S.subprocess, 'run', run)
    result = S.verify_committed_source('a' * 40, files[2], files[3])
    assert len(result) == len(calls) == 4
    assert all(command[:4] == ['git', '-C', str(root), 'show'] for command in calls)
    monkeypatch.setattr(S.subprocess, 'run', lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=b'changed'))
    with pytest.raises(ValueError, match='not present'):
        S.verify_committed_source('a' * 40, files[2], files[3])


@pytest.mark.parametrize('sources', [[fineweb_source(0, 3)],
    [fineweb_source(0, 0), fineweb_source(0, 2)], [fineweb_source(1, 0)]])
def test_first_file_or_skipped_file_or_first_row_rejected(tmp_path, sources):
    cache = tmp_path / 'cache' / 'skip'
    build_small(cache, [document(i, [i], source=source) for i, source in enumerate(sources)], limit=len(sources))
    with pytest.raises(ValueError, match='pinned file and native row order'):
        S.verify_training_cache(cache, allow_synthetic=True)


def test_consecutive_fineweb_files_with_zero_based_rows_accepted(tmp_path):
    cache = tmp_path / 'cache' / 'sequence'
    docs = [document(i, [i], source=source) for i, source in enumerate([
        fineweb_source(0), fineweb_source(1), fineweb_source(0, 1), fineweb_source(1, 1)])]
    build_small(cache, docs, limit=4)
    assert S.verify_training_cache(cache, allow_synthetic=True)['n_tokens'] == 4


def section_cache(tmp_path):
    cache = tmp_path / 'cache' / 'section'
    docs = [document(0, [1, 2], source=section_source(0)),
            document(2, [3, 4], source=section_source(2)), document(0, [5, 6, 7])]
    build_small(cache, docs, limit=6)
    return cache


def test_section_inventory_has_every_full_source_and_token_hash(tmp_path):
    cache = section_cache(tmp_path)
    manifest = S.verify_training_cache(cache, allow_synthetic=True)
    expected = [S._inventory_entry(record) for record in spans(cache)[:2]]
    assert manifest['section79_inventory'] == expected
    assert manifest['section79_inventory_sha256'] == S._digest(expected)
    assert [r['source']['row'] for r in expected] == [0, 2]


def test_section_document_omission_detected_from_expected_inventory(tmp_path):
    cache = section_cache(tmp_path)
    records = spans(cache)
    write_spans(cache, records[1:])
    reseal(cache)
    with pytest.raises(ValueError, match='ordered full-document token inventory'):
        S.verify_training_cache(cache, allow_synthetic=True)


def test_section_token_omission_detected_before_chunking(tmp_path):
    cache = section_cache(tmp_path)
    records = spans(cache)
    records[0]['token_count'] = 1
    records[0]['cache_end'] = 1
    write_spans(cache, records)
    reseal(cache)
    with pytest.raises(ValueError, match='ordered full-document token inventory'):
        S.verify_training_cache(cache, allow_synthetic=True)


def test_changed_section_inventory_digest_rejected(tmp_path):
    cache = section_cache(tmp_path)
    manifest = json.loads((cache / 'MANIFEST.json').read_text())
    manifest['section79_inventory'][0]['source_token_count'] += 1
    write(cache / 'MANIFEST.json', manifest)
    reseal(cache)
    with pytest.raises(ValueError, match='section79 inventory differs'):
        S.verify_training_cache(cache, allow_synthetic=True)


def mock_inventory_sources(tmp_path, monkeypatch, *, n_train=1910):
    cache = tmp_path / 'cache' / 'inventory'
    cache.mkdir(parents=True)
    for filename in S.SOURCE_FILES.values():
        (cache / filename).write_text('{}')
    write(cache / S.SOURCE_FILES['manifest'], {'corpus_path': 'synthetic/corpus.jsonl'})
    expected_sha = {S.SOURCE_FILES['corpus']: S.CORPUS_SHA,
                    S.SOURCE_FILES['manifest']: S.MANIFEST_SHA,
                    S.SOURCE_FILES['tokenizer']: S.TOKENIZER_SHA}
    monkeypatch.setattr(S, 'sha', lambda path: expected_sha[Path(path).name])
    train, held = group(False), group(True)
    rows = [{'id': 'held-a', 'group_id': held, 'text': 'do not tokenize'}]
    rows += [{'id': f'train-{i}', 'group_id': train, 'text': 't' * (600 if i == 0 else 1)} for i in range(n_train)]
    rows += [{'id': 'held-b', 'group_id': held, 'text': 'do not tokenize'}]
    monkeypatch.setattr(S, 'read_corpus', lambda *args: rows)
    calls = []
    class Tokenizer:
        @staticmethod
        def from_file(path):
            return Tokenizer()
        def encode(self, text, *, add_special_tokens):
            assert add_special_tokens is False
            calls.append(text)
            return SimpleNamespace(ids=list(range(len(text))))
    monkeypatch.setitem(sys.modules, 'tokenizers', SimpleNamespace(Tokenizer=Tokenizer))
    return cache, calls


def test_independent_inventory_retokenizes_every_permitted_doc_without_truncation(tmp_path, monkeypatch):
    cache, calls = mock_inventory_sources(tmp_path, monkeypatch)
    inventory = S._section79_inventory(cache, {'source_commit': 'a' * 40})
    assert len(inventory) == 1910
    assert [record['source']['row'] for record in inventory] == list(range(1, 1911))
    assert inventory[0]['source_token_count'] == 600
    assert inventory[0]['tokens_sha256'] == hashlib.sha256(np.arange(600, dtype='<u4').tobytes()).hexdigest()
    assert len(calls) == 1910
    assert 'do not tokenize' not in calls


@pytest.mark.parametrize('n_train', [1909, 1911])
def test_independent_inventory_rejects_incomplete_or_extra_training_docs(tmp_path, monkeypatch, n_train):
    cache, _ = mock_inventory_sources(tmp_path, monkeypatch, n_train=n_train)
    with pytest.raises(ValueError, match='exact 1910'):
        S._section79_inventory(cache, {'source_commit': 'a' * 40})


@pytest.mark.parametrize('changed', ['corpus', 'manifest', 'tokenizer'])
def test_independent_inventory_requires_all_original_pinned_bytes(tmp_path, monkeypatch, changed):
    cache, calls = mock_inventory_sources(tmp_path, monkeypatch)
    original_sha = S.sha
    monkeypatch.setattr(S, 'sha', lambda path: '0' * 64 if Path(path).name == S.SOURCE_FILES[changed] else original_sha(path))
    with pytest.raises(ValueError, match='registered pins'):
        S._section79_inventory(cache, {'source_commit': 'a' * 40})
    assert calls == []
