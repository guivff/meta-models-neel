"""E36: freeze newly authored text, then check labels, then tokenize on CPU.

Only the authorized definition packet and new E36 author/checker modules are
inputs. No W1 item bank, score, template renderer or model is read or imported.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
FALLBACK_ROWS = ('prose_paren', 'python_string', 'table_role', 'python_indent',
                 'table_column', 'list_index', 'prose_sentiment', 'prose_topic')
ROWS = ('json_status', 'json_type', 'latex_environment', 'latex_role', 'latex_section',
        'latex_subject', 'list_depth', 'list_index', 'list_priority', 'list_topic',
        'prose_paren', 'prose_quote', 'prose_sentence', 'prose_sentiment', 'prose_topic',
        'python_argument', 'python_comment', 'python_depth', 'python_error', 'python_indent',
        'python_string', 'table_column', 'table_role', 'table_row', 'table_status')
DEFINITION_SHA = '2afa8e1202c0d7c181e6f95984b18bd59f99af81fc8cf8f27dcce02e8e38056c'
TOKENIZER_SHA = '5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def dump(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def jsonl(path, values):
    with Path(path).open('x') as stream:
        for value in values:
            stream.write(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)+'\n')


def load_module(name):
    if name not in ('author_structure', 'author_content', 'check_structure', 'check_content'):
        raise ValueError('only new E36 authors/checkers can be loaded')
    spec = importlib.util.spec_from_file_location('e36_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def definitions(packet, scope='expanded25'):
    if packet.get('experiment') != 'E36' or packet.get('written_by') != 'coordinator':
        raise ValueError('authorized row-definition packet required before authoring')
    rows = packet.get('rows', {})
    if set(rows) != set(ROWS):
        raise ValueError('all 25 coordinator row definitions required')
    for feature, row in rows.items():
        values = row.get('values')
        if (not isinstance(values, list) or len(values) != 2 or len(set(values)) != 2
                or not all(isinstance(v, str) and v for v in values)
                or not row.get('definition') or row.get('class') not in ('state-like', 'count-like', 'semantic')):
            raise ValueError('explicit definition and A/B bins required: ' + feature)
    if Counter(r['class'] for r in rows.values()) != {'state-like': 7, 'count-like': 9, 'semantic': 9}:
        raise ValueError('coordinator row taxonomy differs')
    if scope not in ('expanded25', 'original8'):
        raise ValueError('unknown registered scope')
    return {f: rows[f] for f in (ROWS if scope == 'expanded25' else FALLBACK_ROWS)}


def check_grid(items, specs):
    n = 168 * len(specs)
    if len(items) != n or len({r['id'] for r in items}) != n:
        raise ValueError('require exactly 168 unique items per registered row')
    if len({r['text'] for r in items}) != n:
        raise ValueError('duplicate authored text; no silent item replacement')
    expected = {(f, t, k, v) for f in specs for t in range(12) for k in range(7)
                for v in specs[f]['values']}
    observed = {(r['feature'], r['template_index'], r['filler_index'], r['value']) for r in items}
    if observed != expected:
        raise ValueError('incomplete 12 x 7 x 2 design')
    for feature in specs:
        row = [r for r in items if r['feature'] == feature]
        for split, families in (('dev', set(range(6))), ('test', set(range(6, 12)))):
            selected = [r for r in row if r['split'] == split]
            if (len(selected) != 84 or {r['template_index'] for r in selected} != families
                    or Counter(r['value'] for r in selected) != Counter({v: 42 for v in specs[feature]['values']})
                    or set(Counter(r['cluster'] for r in selected).values()) != {14}):
                raise ValueError('fixed complete family split required: ' + feature)


def build(args):
    start = time.monotonic()
    packet_path, out = Path(args.definitions), Path(args.out).resolve()
    if not out.is_relative_to((HERE / 'cache').resolve()):
        raise ValueError('raw bank outputs must remain within E36 ignored cache')
    if packet_path.resolve() != (HERE / 'ROW_DEFINITIONS.json').resolve():
        raise ValueError('use the coordinator ROW_DEFINITIONS.json only')
    if sha(packet_path) != DEFINITION_SHA:
        raise ValueError('coordinator definition packet SHA256 mismatch')
    packet = read(packet_path)
    scope = getattr(args, 'scope', 'expanded25')
    specs = definitions(packet, scope)
    count = 168 * len(specs)
    source_names = ('build_bank.py', 'author_structure.py', 'author_content.py', 'check_structure.py', 'check_content.py')
    source_files = {str((HERE / n).relative_to(ROOT)): sha(HERE / n) for n in source_names}
    if getattr(args, 'resume_frozen_import_failure', False):
        # This narrow recovery is available only before a label ledger exists.
        # It never imports a generator or rewrites the original bank/seal.
        if {p.name for p in out.iterdir()} != {'items.AUTHORED.jsonl', 'BANK_SOURCE_SEAL.json'}:
            raise ValueError('resume requires only the original bank/seal and no checked outcomes')
        original = read(out / 'BANK_SOURCE_SEAL.json')
        if (original.get('status') != 'FROZEN_BEFORE_AUTOMATIC_LABEL_CHECK'
                or original.get('scope') != scope
                or original.get('definition_packet_sha256') != sha(packet_path)
                or original['files']['items.AUTHORED.jsonl'] != sha(out / 'items.AUTHORED.jsonl')):
            raise ValueError('original frozen bank or definition hash changed')
        for relative, digest in original['source_files'].items():
            if Path(relative).name != 'build_bank.py' and source_files.get(relative) != digest:
                raise ValueError('resume refuses changed author/checker source')
        items = [json.loads(line) for line in (out / 'items.AUTHORED.jsonl').read_text().splitlines()]
        check_grid(items, specs)
        dump(out / 'OPERATIONAL_RESUME.json', {
            'date': datetime.now(timezone.utc).isoformat(),
            'reason': 'Checker import failed before labeling because dynamic module was not registered in sys.modules; repaired import registration.',
            'original_bank_source_seal_sha256': sha(out / 'BANK_SOURCE_SEAL.json'),
            'original_bank_sha256': sha(out / 'items.AUTHORED.jsonl'),
            'original_source_files': original['source_files'], 'resumed_source_files': source_files,
            'author_and_checker_sources_unchanged': True, 'items_replaced_or_dropped': 0,
            'prior_item_labels_checked': 0, 'model_calls': 0})
    else:
        if out.exists():
            raise ValueError('bank output exists; never overwrite or silently regenerate a frozen bank')
        authors = {'structure': load_module('author_structure'), 'content': load_module('author_content')}
        items, signatures = [], {}
        for feature in specs:
            author = authors['content' if specs[feature]['class'] == 'semantic' else 'structure']
            signatures[feature] = []
            for template in range(12):
                signature_texts = []
                for filler in range(7):
                    for side, value in enumerate(specs[feature]['values']):
                        text = author.render(feature, template, filler, side)
                        if not isinstance(text, str) or not text or '\x00' in text:
                            raise ValueError('invalid authored prefix')
                        if filler == 0:
                            signature_texts.append(text)
                        identity = json.dumps([feature, template, filler, value, text], ensure_ascii=False)
                        items.append({'id': hashlib.sha256(('E36-v2:' + identity).encode()).hexdigest()[:24],
                                      'feature': feature, 'value': value,
                                      'class': specs[feature]['class'],
                                      'split': 'dev' if template < 6 else 'test',
                                      'cluster': feature + '_v2_family_' + str(template).zfill(2),
                                      'template_index': template, 'filler_index': filler, 'text': text})
                signatures[feature].append(hashlib.sha256(json.dumps(signature_texts, ensure_ascii=False).encode()).hexdigest())
            if len(set(signatures[feature])) != 12:
                raise ValueError('duplicate complete family templates')
        check_grid(items, specs)
        out.mkdir(parents=True, exist_ok=False)
        jsonl(out / 'items.AUTHORED.jsonl', items)
        dump(out / 'BANK_SOURCE_SEAL.json', {
            'experiment': 'E36', 'bank': 'v2', 'scope': scope, 'status': 'FROZEN_BEFORE_AUTOMATIC_LABEL_CHECK',
            'created_at': datetime.now(timezone.utc).isoformat(), 'definition_packet_sha256': sha(packet_path),
            'source_files': source_files, 'files': {'items.AUTHORED.jsonl': sha(out / 'items.AUTHORED.jsonl')},
            'rows': list(specs), 'item_count': count, 'dev_items': count // 2, 'test_items': count // 2,
            'family_signatures': signatures, 'W1_items_accessed': False, 'W1_scores_accessed': False,
            'model_calls': 0, 'author_context': 'fresh agents without inherited chat history; authorized definitions only'})
    # Screening starts only after every authored item and its source hash are frozen.
    checkers = {'structure': load_module('check_structure'), 'content': load_module('check_content')}
    checks, failures = [], []
    for item in items:
        checker = checkers['content' if item['class'] == 'semantic' else 'structure']
        try:
            result = checker.infer_label(item['feature'], item['text'])
            inferred = result['value']
            passed = inferred == item['value']
            record = {'id': item['id'], 'feature': item['feature'], 'expected': item['value'],
                      'inferred': inferred, 'passed': passed, 'evidence': result['evidence']}
        except Exception as error:
            passed = False
            record = {'id': item['id'], 'feature': item['feature'], 'expected': item['value'],
                      'passed': False, 'error_type': type(error).__name__}
        checks.append(record)
        if not passed:
            failures.append({'id': item['id'], 'feature': item['feature']})
    jsonl(out / 'label_checks.jsonl', checks)
    dump(out / 'LABEL_CHECK.json', {'status': 'PASS' if not failures else 'FAIL',
         'bank_source_seal_sha256': sha(out / 'BANK_SOURCE_SEAL.json'),
         'items_checked': len(checks), 'passed': len(checks) - len(failures), 'failures': failures,
         'label_check_ledger_sha256': sha(out / 'label_checks.jsonl'), 'model_calls': 0})
    if failures:
        raise ValueError('frozen bank failed automatic labels; retain failure and do not launch')
    tokenizer_path = Path(args.tokenizer)
    if sha(tokenizer_path / 'tokenizer.json') != TOKENIZER_SHA:
        raise ValueError('wrong pinned Qwen tokenizer')
    from transformers import PreTrainedTokenizerFast
    tokenizer = PreTrainedTokenizerFast(tokenizer_file=str(tokenizer_path / 'tokenizer.json'))
    stage, labels, lengths, paired_lengths = [], [], {}, {}
    for item in items:
        encoded = tokenizer(item['text'], add_special_tokens=False, return_offsets_mapping=True)
        ids, offsets = encoded['input_ids'], encoded['offset_mapping']
        if not ids or offsets[-1][1] != len(item['text']) or len(ids) > 262144:
            raise ValueError('invalid untruncated final-token read position')
        stage.append({k: item[k] for k in ('id', 'feature', 'split', 'cluster', 'text')} | {'ids': ids})
        labels.append({k: item[k] for k in ('id', 'feature', 'value', 'split', 'cluster')})
        lengths.setdefault(item['feature'], []).append(len(ids))
        key = (item['feature'], item['template_index'], item['filler_index'])
        paired_lengths.setdefault(key, []).append(len(ids))
    # Conservative interpretation of ±10%: the longer member is <=1.10 times
    # the shorter for every same-family, same-filler A/B pair.
    length_records = [{'feature': k[0], 'template_index': k[1], 'filler_index': k[2],
                       'lengths': v, 'ratio': max(v) / min(v),
                       'passed': len(v) == 2 and 10 * max(v) <= 11 * min(v)}
                      for k, v in paired_lengths.items()]
    jsonl(out / 'length_checks.jsonl', length_records)
    length_check = {'status': 'PASS' if all(r['passed'] for r in length_records) else 'FAIL',
                    'pairs_checked': len(length_records),
                    'passed': sum(r['passed'] for r in length_records),
                    'maximum_ratio': max(r['ratio'] for r in length_records),
                    'criterion': 'max(A_tokens,B_tokens)/min(A_tokens,B_tokens)<=1.10',
                    'ledger_sha256': sha(out / 'length_checks.jsonl'), 'tokenizer_sha256': TOKENIZER_SHA}
    dump(out / 'LENGTH_CHECK.json', length_check)
    if length_check['status'] != 'PASS':
        raise ValueError('frozen bank failed automatic length matching; retain failure and do not launch')
    jsonl(out / 'items.input.jsonl', stage)
    jsonl(out / 'labels.DO_NOT_STAGE.jsonl', labels)
    binding = {'experiment': 'E36', 'bank': 'v2', 'scope': scope, 'status': 'LABEL_CHECKED_FROZEN',
               'definition_packet_sha256': sha(packet_path),
               'bank_source_seal_sha256': sha(out / 'BANK_SOURCE_SEAL.json'),
               'label_check_sha256': sha(out / 'LABEL_CHECK.json'), 'source_files': source_files,
               'length_check_sha256': sha(out / 'LENGTH_CHECK.json'),
               'items_sha256': sha(out / 'items.input.jsonl'),
               'labels_sha256': sha(out / 'labels.DO_NOT_STAGE.jsonl'), 'tokenizer_sha256': TOKENIZER_SHA,
               'item_count': count, 'split_counts': {'dev': count // 2, 'test': count // 2},
               'rows': {f: {'values': specs[f]['values'], 'class': specs[f]['class'], 'dev': 84, 'test': 84,
                            'family_count': 12, 'fillers_per_family': 7,
                            'token_length_min': min(lengths[f]), 'token_length_max': max(lengths[f])}
                        for f in specs},
               'items': [{k: r[k] for k in ('id', 'feature', 'split', 'cluster')} for r in stage],
               'read_position': 'len(ids)-1; final token of exact raw prefix',
               'W1_comparison_or_score_screening': False, 'model_calls': 0,
               'wall_seconds': time.monotonic() - start}
    dump(out / 'BANK_BINDING.json', binding)
    dump(out / 'FREEZE_RECEIPT.json', {
        'experiment': 'E36', 'bank': 'v2', 'scope': scope, 'status': 'LABEL_CHECKED_FROZEN',
        'frozen_at': read(out / 'BANK_SOURCE_SEAL.json')['created_at'],
        'bank_sha256': binding['items_sha256'],
        'automatic_label_check': {'status': 'PASS', 'checked': count, 'passed': count,
                                  'receipt_sha256': binding['label_check_sha256']},
        'automatic_length_check': {'status': 'PASS', 'checked': count // 2, 'passed': count // 2,
                                   'receipt_sha256': binding['length_check_sha256']},
        'definition_packet_sha256': binding['definition_packet_sha256'],
        'bank_source_seal_sha256': binding['bank_source_seal_sha256'],
        'bank_binding_sha256': sha(out / 'BANK_BINDING.json'),
        'tokenizer_sha256': TOKENIZER_SHA, 'item_count': count,
        'split_counts': binding['split_counts'], 'rows': binding['rows'],
        'source_files': source_files, 'model_calls': 0,
        'operational_resume_sha256': sha(out / 'OPERATIONAL_RESUME.json') if (out / 'OPERATIONAL_RESUME.json').exists() else None})
    dump(out / 'PREPARED_SEAL.json', {'complete': True, 'status': 'E36_V2_READY_FOR_POST_FREEZE_CANDIDATE_BINDING',
         'files': {n: sha(out / n) for n in ('BANK_SOURCE_SEAL.json', 'LABEL_CHECK.json', 'BANK_BINDING.json',
                                            'FREEZE_RECEIPT.json', 'LENGTH_CHECK.json', 'length_checks.jsonl',
                                            'items.AUTHORED.jsonl', 'label_checks.jsonl', 'items.input.jsonl',
                                            'labels.DO_NOT_STAGE.jsonl') + (('OPERATIONAL_RESUME.json',) if (out / 'OPERATIONAL_RESUME.json').exists() else ())}})
    return {'status': binding['status'], 'scope': scope, 'items': count, 'label_checks_passed': count,
            'length_pairs_passed': count // 2,
            'bank_source_seal_sha256': binding['bank_source_seal_sha256'],
            'prepared_seal_sha256': sha(out / 'PREPARED_SEAL.json'), 'model_calls': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('definitions', 'tokenizer', 'out'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--resume-frozen-import-failure', action='store_true')
    parser.add_argument('--scope', choices=('expanded25', 'original8'), default='expanded25')
    print(json.dumps(build(parser.parse_args()), sort_keys=True))
