"""§137 pre-production W1 score parity; no W1 text and no v2 labels."""
from __future__ import annotations

import json
import math
from pathlib import Path

import channel_contract as C

ROWS = ['prose_sentiment', 'prose_paren', 'python_string']
INPUT_SHA256 = 'c41970528477a88e15144b7822e9d07e592ad21e340d65ba312d4513532c8aae'
THRESHOLD = .02  # §137 overrides E28's original .03, not its input bytes.
REQUIRED = {'items.jsonl', 'acts44.npy', 'labels.json', 'templates.json', 'REFERENCE.json'}


def validate_binding(binding):
    C.require(isinstance(binding, dict) and binding.get('sha256') == INPUT_SHA256,
              'exact sealed E28 three-row parity inputs required')
    C.require(Path(binding.get('path', '')).name == 'INPUT_SEAL.json', 'parity seal path required')


def load_inputs(binding):
    import numpy as np
    validate_binding(binding)
    seal = C.read_bound(binding)
    source = Path(binding['path']).parent
    C.require(set(seal['files']) == REQUIRED, 'parity input manifest changed')
    for name, digest in seal['files'].items():
        C.require(C.file_hash(source / name) == digest, 'parity file hash mismatch: ' + name)
    items = [json.loads(line) for line in (source / 'items.jsonl').read_text().splitlines()]
    labels = json.loads((source / 'labels.json').read_text())
    templates = json.loads((source / 'templates.json').read_text())
    reference = json.loads((source / 'REFERENCE.json').read_text())
    C.require(reference['rows'] == ROWS and reference['status'] == 'FROZEN', 'wrong parity reference')
    C.require(len(items) == len({x['id'] for x in items}) == 252 and
              all(set(x) == {'id', 'feature'} for x in items), 'exact 252 text-free parity items required')
    C.require(set(labels) == {x['id'] for x in items} and set(templates) == set(ROWS), 'parity population mismatch')
    C.require(all(type(x) is int and x in (0, 1) for x in labels.values()), 'binary parity labels required')
    for row in ROWS:
        group = [x for x in items if x['feature'] == row]
        C.require(len(group) == 84 and sum(labels[x['id']] for x in group) == 42, 'balanced parity rows required')
        pairs = templates[row]['olens']
        C.require(len(pairs) == 2 and all(len(p) == 2 and all(isinstance(s, str) and s for s in p) for p in pairs),
                  'two frozen W1 phrasing pairs required')
    acts = np.load(source / 'acts44.npy', allow_pickle=False)
    C.require(acts.shape == (252, 5120) and np.isfinite(acts).all(), 'invalid parity activation grid')
    return items, labels, templates, acts, reference


def adjudicate(records, labels, reference):
    C.require(len(records) == len({x['id'] for x in records}) == 252 and
              {x['id'] for x in records} == set(labels), 'incomplete parity score grid')
    cells = {}
    for row in ROWS:
        group = [x for x in records if x['feature'] == row]
        C.require(len(group) == 84, 'incomplete parity row')
        C.require(all(len(x['scores']) == 2 and all(type(v) in (int, float) and math.isfinite(v)
                  for v in x['scores']) for x in group), 'invalid parity scores')
        positive = [sum(x['scores']) / 2 for x in group if labels[x['id']] == 1]
        negative = [sum(x['scores']) / 2 for x in group if labels[x['id']] == 0]
        C.require(len(positive) == len(negative) == 42, 'unbalanced parity row')
        auc = sum((a > b) + .5 * (a == b) for a in positive for b in negative) / (42 * 42)
        ref = reference['reference_auc'][row]
        C.require(type(ref) in (int, float) and math.isfinite(ref) and 0 <= ref <= 1, 'invalid reference AUROC')
        cells[row] = {'n': 84, 'observed': auc, 'reference': ref,
                      'absolute_delta': abs(auc - ref), 'threshold': THRESHOLD}
    return {'status': 'PASS' if all(x['absolute_delta'] <= THRESHOLD for x in cells.values()) else 'FAIL',
            'rows': cells, 'authority': 'BRIEF_UNDERSTAND §137, 1721470e',
            'parity_input_seal_sha256': INPUT_SHA256, 'production_items_scored_before_gate': 0,
            'recipe': 'W1 block44 stored activations; same E36 Oracle backend; mean of two raw A-minus-B log-odds',
            'capture_parity_certified': False}


def run_gate(backend, budget, out, inputs):
    items, labels, templates, acts, reference = inputs
    jobs = []
    for row in ROWS:
        indices = [i for i, x in enumerate(items) if x['feature'] == row]
        for start in range(0, len(indices), 8):
            jobs.append((row, indices[start:start + 8]))
    records = []
    for k, (row, indices) in enumerate(jobs):
        selected = [items[i] for i in indices]
        h = backend.take(acts, indices)
        values = budget.call('parity', lambda: backend.score('oracle_descriptive', selected, h,
                              templates[row]['olens']), len(jobs) - k - 1)
        C.require(len(values) == len(selected), 'missing parity score cells')
        records.extend(dict(item, scores=scores) for item, scores in zip(selected, values))
    out = Path(out)
    with (out / 'PARITY_SCORES.jsonl').open('x') as stream:
        for record in records:
            stream.write(json.dumps(record, allow_nan=False) + '\n')
    result = adjudicate(records, labels, reference)
    result['raw_scores_sha256'] = C.file_hash(out / 'PARITY_SCORES.jsonl')
    (out / 'PARITY_RESULT.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    C.require(result['status'] == 'PASS', 'W1 score parity failed; stop before production, no retry')
    return result
