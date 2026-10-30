"""One ordered pass: manifest-ordered §79 training docs, then pinned FineWeb rows."""
from pathlib import Path
import argparse
import hashlib
import shutil
import numpy as np
from e40_common import HERE, ROOT, E35, read, sha, dump_new, read_corpus, is_heldout, TOKENIZER_SHA
from gate_inputs import CORPUS_SHA, MANIFEST_SHA


def prepare_sources(out, corpus, manifest, tokenizer):
    from huggingface_hub import hf_hub_download
    if (sha(corpus), sha(manifest), sha(tokenizer)) != (CORPUS_SHA, MANIFEST_SHA, TOKENIZER_SHA):
        raise ValueError('original corpus, manifest and tokenizer required')
    out = Path(out).resolve()
    if not out.is_relative_to((ROOT / 'cache/g_agreement/understand/e40').resolve()):
        raise ValueError('E40 cache staging required')
    out.mkdir(parents=True, exist_ok=False)
    dump_new(out / 'STAGING.RUN_ONCE.json', {'experiment': 'E40', 'date': '2026-10-26'})
    files = {}
    for name, source in [('corpus.jsonl', corpus), ('corpus-manifest.json', manifest), ('tokenizer.json', tokenizer)]:
        with Path(source).open('rb') as f, (out / name).open('xb') as g:
            shutil.copyfileobj(f, g)
        files[name] = sha(out / name)
    pin = read(HERE / 'FINEWEB_FILES.20261026.json')
    for name, metadata in sorted(pin['files'].items()):
        path = Path(hf_hub_download(repo_id=pin['repository'], repo_type='dataset',
            revision=pin['revision'], filename=name, local_dir=out / 'fineweb', token=False))
        if path.stat().st_size != metadata['bytes'] or sha(path) != metadata['sha256']:
            raise ValueError('pinned FineWeb file mismatch')
        files['fineweb/' + name] = metadata['sha256']
    record = {'experiment': 'E40', 'status': 'COMPLETE', 'files': files,
              'fineweb_pin_sha256': sha(HERE / 'FINEWEB_FILES.20261026.json')}
    dump_new(out / 'SOURCES.json', record)
    return record


def verify_sources(folder, expected_sha):
    folder = Path(folder).resolve()
    if sha(folder / 'SOURCES.json') != expected_sha:
        raise ValueError('assigned source manifest mismatch')
    record = read(folder / 'SOURCES.json')
    pin = read(HERE / 'FINEWEB_FILES.20261026.json')
    expected = {'corpus.jsonl': CORPUS_SHA, 'corpus-manifest.json': MANIFEST_SHA, 'tokenizer.json': TOKENIZER_SHA}
    expected.update({'fineweb/' + n: x['sha256'] for n, x in pin['files'].items()})
    if (record.get('experiment') != 'E40' or record.get('status') != 'COMPLETE'
            or record.get('files') != expected
            or record.get('fineweb_pin_sha256') != sha(HERE / 'FINEWEB_FILES.20261026.json')):
        raise ValueError('complete original and pinned source files required')
    for name, digest in expected.items():
        if sha(folder / name) != digest:
            raise ValueError('staged source checksum mismatch')
    return record


def manifest_order(rows, manifest):
    by_id = {r['id']: r for r in rows}
    order = [r['id'] for r in manifest['documents']]
    if len(by_id) != len(rows) or len(set(order)) != len(order) or set(order) != set(by_id):
        raise ValueError('exact original manifest document ordering required')
    return [by_id[i] for i in order if not is_heldout(by_id[i]['group_id'])]


def documents(folder):
    """Lazy stable source identities; no repeated epochs or content-based filtering."""
    import pyarrow.parquet as pq
    from tokenizers import Tokenizer
    folder = Path(folder)
    rows = read_corpus(folder / 'corpus.jsonl', folder / 'corpus-manifest.json')
    rows = manifest_order(rows, read(folder / 'corpus-manifest.json'))
    if len(rows) != 1910:
        raise ValueError('all1910 training documents required')
    tok = Tokenizer.from_file(str(folder / 'tokenizer.json'))
    for row in rows:
        yield {'source_id': 'section79:' + row['id'], 'ids': tok.encode(row['text'], add_special_tokens=False).ids}
    pin = read(HERE / 'FINEWEB_FILES.20261026.json')
    for filename in sorted(pin['files']):
        index = 0
        parquet = pq.ParquetFile(folder / 'fineweb' / filename)
        for batch in parquet.iter_batches(batch_size=64, columns=['text']):
            for text in batch.column(0).to_pylist():
                if not isinstance(text, str):
                    raise ValueError('raw FineWeb text required')
                yield {'source_id': pin['revision'] + ':' + filename + ':' + str(index),
                       'ids': tok.encode(text, add_special_tokens=False).ids}
                index += 1


def chunks(source, length=512):
    if not 1 <= length <= 512:
        raise ValueError('bounded raw document context required')
    seen = set()
    for document in source:
        key, ids = document['source_id'], document['ids']
        if key in seen:
            raise ValueError('source document replay')
        seen.add(key)
        for start in range(0, len(ids), length):
            yield {'source_id': key, 'token_start': start, 'ids': ids[start:start+length],
                   'positions': np.arange(start, min(start+length,len(ids)), dtype=np.int64)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('out','corpus','manifest','tokenizer'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    try:
        prepare_sources(a.out,a.corpus,a.manifest,a.tokenizer)
        print('E40_SOURCE_STAGING_COMPLETE')
        return 0
    except Exception as error:
        print('E40_SOURCE_STAGING_STOP',type(error).__name__)
        return 2
if __name__=='__main__':raise SystemExit(main())
