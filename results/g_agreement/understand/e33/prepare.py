"""E33 tokenization-only preparation from the sealed E12 population; no model load."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from reused import base_head, carrier, activation_for

E12_SEAL = "2a2c8e82"  # Full authority pins are in PLAN.json, checked below.
TOKENIZER_SHA = "5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42"
TEMPLATES_SHA = "97257b242380b0e68a7418dd36959f1708ce5ccaf68e2935ddd18c70e40ceb2b"
ITEMS_SHA = "b4577f497bac7ce9b5a0a70bc6a28f42bcf6f4e2251688924de65983c61b1233"
HERE = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, sort_keys=True, allow_nan=False) + '\n')


def records(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def verify(directory, name='INPUT_SEAL.json'):
    seal = read(directory / name)
    for relative, digest in seal['files'].items():
        path = (directory / relative).resolve()
        if not path.is_relative_to(directory.resolve()) or sha(path) != digest:
            raise ValueError('sealed file mismatch: ' + relative)
    return seal


def prepare(e12: Path, tokenizer: Path, out: Path):
    from transformers import AutoTokenizer
    plan = read(HERE / 'PLAN.json')
    if out.exists():
        raise FileExistsError('E33 inputs are immutable; use a fresh cache directory')
    if sha(e12 / 'INPUT_SEAL.json') != plan['e12_input_seal_sha256']:
        raise ValueError('E12 source seal differs from frozen plan')
    # Validate only text/prompt assets; E33 neither reads nor stages activation files.
    seal = read(e12 / 'INPUT_SEAL.json')
    for name in ['items.input.jsonl', 'templates.json', 'ids.json', 'provenance.json']:
        if sha(e12 / name) != seal['files'][name]:
            raise ValueError('E12 source mismatch: ' + name)
    if sha(e12 / 'templates.json') != TEMPLATES_SHA or sha(e12 / 'items.input.jsonl') != ITEMS_SHA:
        raise ValueError('E12 frozen population mismatch')
    if sha(tokenizer / 'tokenizer.json') != TOKENIZER_SHA:
        raise ValueError('target tokenizer drift')
    tok = AutoTokenizer.from_pretrained(tokenizer, local_files_only=True)
    source = records(e12 / 'items.input.jsonl')
    templates = read(e12 / 'templates.json')
    if sorted(templates) != plan['rows'] or len(source) != 2100:
        raise ValueError('all 25 frozen rows required')
    if Counter(x['feature'] for x in source) != Counter({f: 84 for f in templates}):
        raise ValueError('exactly 84 items per frozen row required')
    if [r['id'] for r in source] != read(e12 / 'ids.json') or len({r['id'] for r in source}) != 2100:
        raise ValueError('frozen unique E12 item order required')
    native = read(e12 / 'provenance.json')['native_carriers']['olens']
    items = []
    for r in source:
        if tok.encode(r['text'], add_special_tokens=False) != r['ids']:
            raise ValueError('stored source text/token mismatch')
        p1 = base_head(tok, r['text'])
        p2, slot = carrier(tok, native['request'], r['text'], 'text_only', native['marker_token_id'])
        if activation_for('text_only', object(), object()) is not None:
            raise ValueError('E12 text-only injection contract changed')
        items.append({'id': r['id'], 'feature': r['feature'], 'heads': {'P1': p1, 'P2': p2}, 'P2_placeholder_index': slot})
    pairs = {f: [[tok.encode(c, add_special_tokens=False) for c in pair] for pair in t['olens']] for f, t in templates.items()}
    if any(len(ps) != 2 or any(len(p) != 2 or any(not c for c in p) for p in ps) for ps in pairs.values()):
        raise ValueError('two nonempty frozen candidate pairs required')
    units = []
    for prompt in ['P1', 'P2']:
        groups = defaultdict(list)
        for i, r in enumerate(items):
            groups[(r['feature'], len(r['heads'][prompt]))].append(i)
        for (feature, length), indices in sorted(groups.items()):
            for start in range(0, len(indices), 16):
                units.append({'prompt': prompt, 'feature': feature, 'head_length': length, 'indices': indices[start:start + 16]})
    out.mkdir(parents=True)
    (out / 'items.input.jsonl').write_text(''.join(json.dumps(x, sort_keys=True) + '\n' for x in items))
    (out / 'templates.json').write_bytes((e12 / 'templates.json').read_bytes())
    dump(out / 'token_pairs.json', pairs)
    dump(out / 'units.json', units)
    dump(out / 'provenance.json', {
        'experiment': 'E33', 'plan_sha256': sha(HERE / 'PLAN.json'),
        'e12_input_seal_sha256': sha(e12 / 'INPUT_SEAL.json'),
        'base_tokenizer_sha256': TOKENIZER_SHA, 'tokenizer_json_sha256': TOKENIZER_SHA,
        'tokenizer_files': {name: sha(tokenizer / name) for name in ['tokenizer.json', 'tokenizer_config.json', 'chat_template.jinja']},
        'private_labels_sha256': read(e12 / 'provenance.json')['private_items_sha256'],
        'source_prefix': read(e12 / 'provenance.json')['prefix'], 'native_carrier': native,
        'upstream_source_sha256': sha(HERE / 'UPSTREAM_SOURCE.json'),
        'test_labels_staged': False, 'activation_files_read_or_staged': False,
        'model_forwards': 0, 'GPU_hours': 0, 'pad_token_id': tok.pad_token_id,
        'scoring': 'sum token log probabilities A minus B, mean of two frozen pairs before AUROC',
        'prepared_items': len(items), 'prepared_units': len(units),
    })
    dump(out / 'INPUT_SEAL.json', {'status': 'E33_INPUTS_FROZEN', 'files': {p.name: sha(p) for p in sorted(out.iterdir())}})
    return {'items': len(items), 'units': Counter(u['prompt'] for u in units), 'input_seal_sha256': sha(out / 'INPUT_SEAL.json'), 'model_forwards': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['e12', 'tokenizer', 'out']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.e12, args.tokenizer, args.out), sort_keys=True))
