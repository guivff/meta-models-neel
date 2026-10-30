"""CPU-only exact adapter for W-core's published W12 freeze; no reader outcomes."""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

import analyze as A
import worker as W

FREEZE_SHA256 = '2833a20091db5e1e3b5548bf8d0e581b1fe23718989dc9e6e698da6eb767109f'
FREEZE_COMMIT = '13a53614fdba704e00c24e5a8323a9c1b5b59b5e'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def adapt(items, templates, rows):
    require(len(rows) == len(set(rows)) == 6 and set(templates) == set(rows), 'exact six frozen rows required')
    require(len(items) == len({x['id'] for x in items}) == 1008, 'complete unique W12 bank required')
    staged, labels, candidates, classes = [], [], {}, {}
    for row in rows:
        spec = templates[row]
        values = spec['values']
        require(len(values) == 2 and len(set(values)) == 2, 'ordered A/B values required')
        require(spec['class'] in ('structure', 'content', 'semantic', 'state-like', 'count-like'), 'unknown frozen row class')
        classes[row] = spec['class']
        pairs = spec['olens']
        require(len(pairs) == 2 and all(len(p) == 2 and all(isinstance(s, str) and s for s in p) for p in pairs),
                'two literal frozen Oracle phrasings required')
        candidates[row] = pairs
        group = [x for x in items if x['feature'] == row]
        require(Counter((x['split'], x['value']) for x in group) ==
                Counter({(s, v): 42 for s in ('dev', 'test') for v in values}), 'frozen 42-per-value splits required')
        require(all(x['class'] == classes[row] for x in group), 'item and phrasing classes disagree')
        families = {s: {x['cluster'] for x in group if x['split'] == s} for s in ('dev', 'test')}
        require(all(len(x) == 6 for x in families.values()) and not families['dev'] & families['test'],
                'six disjoint families per split required')
        for item in group:
            if item['split'] != 'test':
                continue
            require(isinstance(item['text'], str) and item['text'] and item['ids'], 'nonempty frozen prefix required')
            require(item['meta']['read_position'] == len(item['ids']) - 1 and
                    item['meta']['token_length'] == len(item['ids']), 'prefix must end at frozen read token')
            staged.append({k: item[k] for k in ('id', 'feature', 'text')})
            labels.append({'id': item['id'], 'feature': row, 'value': 'A' if item['value'] == values[0] else 'B'})
    require(len(staged) == 504, 'all 504 test items required')
    return staged, labels, candidates, classes


def prepare(source, tokenizer_path, out):
    source, tokenizer_path, out = map(Path, (source, tokenizer_path, out))
    require(not out.exists(), 'output exists; never overwrite a prepared cohort')
    require(A.sha(source / 'FREEZE.json') == FREEZE_SHA256, 'wrong W12 freeze; preliminary manifest forbidden')
    freeze = A.read(source / 'FREEZE.json')
    require(set(freeze['files']) == {'items.jsonl', 'templates.json', 'AUDIT.json'}, 'unexpected freeze contents')
    A.verify_files(source, freeze['files'])
    require(A.sha(tokenizer_path / 'tokenizer.json') == W.TOKENIZER_SHA == freeze['tokenizer_sha256'], 'wrong tokenizer')
    items, templates = A.jsonl(source / 'items.jsonl'), A.read(source / 'templates.json')
    staged, labels, candidates, classes = adapt(items, templates, freeze['rows'])
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(tokenizer_path, local_files_only=True)
    # Audit the full sealed bank's token identity, without invoking any model.
    require(all(tok.encode(x['text'], add_special_tokens=False) == x['ids'] for x in items), 'frozen token identity mismatch')
    frames = [W.encode_frame(tok, x['text'], candidate) for x in staged for pair in candidates[x['feature']] for candidate in pair]
    require(len(frames) == 2016, 'complete candidate grid required')
    out.mkdir(parents=True, exist_ok=False)
    stage = out / 'stage'
    stage.mkdir()
    import json
    with (stage / 'items.jsonl').open('x') as stream:
        for x in staged:
            stream.write(json.dumps(x, sort_keys=True, ensure_ascii=False) + '\n')
    A.dump(stage / 'candidates.json', candidates)
    A.dump(stage / 'INPUT_SEAL.json', {'freeze_sha256': FREEZE_SHA256,
           'files': {name: A.sha(stage / name) for name in ('items.jsonl', 'candidates.json')}})
    A.dump(out / 'labels.json', labels)
    cohort = {'name': 'w12', 'blind': True, 'rows': freeze['rows'], 'row_classes': classes,
              'items': [{k: x[k] for k in ('id', 'feature')} for x in staged],
              'phrasing_count': 2, 'expected_scores': 2016,
              'input_seal_sha256': A.sha(stage / 'INPUT_SEAL.json'), 'labels_sha256': A.sha(out / 'labels.json'),
              'freeze': {'sha256': FREEZE_SHA256, 'published_commit': FREEZE_COMMIT,
                         'actual_freeze_utc': freeze['actual_freeze_utc'], 'files': freeze['files'],
                         'source_sha256': freeze['source_sha256'], 'tokenizer_sha256': freeze['tokenizer_sha256'],
                         'candidate_family': 'olens', 'split': 'test'}}
    A.dump(out / 'COHORT.json', cohort)
    audit = {'status': 'PASS', 'freeze_sha256': FREEZE_SHA256, 'published_commit': FREEZE_COMMIT,
             'rows': freeze['rows'], 'row_classes': classes, 'items': 504, 'frames': 2016,
             'full_bank_token_identity_checks': 1008, 'boundary_crossings': 0,
             'candidate_tokens_min': min(x['token_count'] for x in frames),
             'candidate_tokens_max': max(x['token_count'] for x in frames),
             'max_frame_tokens': max(len(x['ids']) for x in frames), 'model_forwards': 0,
             'reader_outcomes_read': False, 'tokenizer_sha256': W.TOKENIZER_SHA,
             'input_seal_sha256': cohort['input_seal_sha256'], 'labels_sha256': cohort['labels_sha256'],
             'cohort_sha256': A.sha(out / 'COHORT.json'), 'text_and_candidates': 'verbatim; no strip or reformat'}
    A.dump(out / 'AUDIT.json', audit)
    return audit


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('source', 'tokenizer', 'out'):
        p.add_argument('--' + key, type=Path, required=True)
    args = p.parse_args()
    print(prepare(args.source, args.tokenizer, args.out))
