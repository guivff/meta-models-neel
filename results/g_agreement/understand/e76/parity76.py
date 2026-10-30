"""Label-free half of the unchanged 252-item W1 Oracle parity gate."""
import json
import numpy as np
from common76 import *

ORIGINAL_SEAL = 'c41970528477a88e15144b7822e9d07e592ad21e340d65ba312d4513532c8aae'
ROWS = ('prose_sentiment', 'prose_paren', 'python_string')
PARITY_FILES = {'items.jsonl', 'acts44.npy', 'templates.json', 'INPUT_SEAL.json'}


def load_parity(folder, expected):
    folder = Path(folder)
    require({p.name for p in folder.iterdir()} == PARITY_FILES and not any(p.is_symlink() for p in folder.iterdir()), 'Exact label-free parity whitelist required')
    require(sha(folder/'INPUT_SEAL.json') == expected, 'Assigned blind parity input pin')
    seal = read(folder/'INPUT_SEAL.json')
    require(seal['original_input_seal_sha256'] == ORIGINAL_SEAL and set(seal['files']) == PARITY_FILES-{'INPUT_SEAL.json'}, 'Original W1 parity lineage')
    verify(folder, seal)
    items = [json.loads(x) for x in (folder/'items.jsonl').read_text().splitlines()]
    require(len(items) == len({x['id'] for x in items}) == 252
        and all(set(x) == {'id', 'feature'} and isinstance(x['id'], str) and x['feature'] in ROWS for x in items), '252 text-free parity identities required')
    templates = read(folder/'templates.json')
    require(set(templates) == set(ROWS), 'Three frozen W1 parity rows')
    for row in ROWS:
        require(sum(x['feature'] == row for x in items) == 84 and set(templates[row]) == {'olens'}, '84 items per original Oracle parity row')
        pairs = templates[row]['olens']
        require(len(pairs) == 2 and all(len(p) == 2 and all(isinstance(s, str) and s for s in p) for p in pairs), 'Two unchanged phrasing pairs required')
    h = np.load(folder/'acts44.npy', allow_pickle=False)
    require(h.shape == (252, DIM) and np.isfinite(h).all(), 'Original finite block44 parity activations')
    return items, templates, h


def generate(backend, clock, inputs, out):
    items, templates, h = inputs
    clock.call('parity_setup', backend.load_oracle)
    dummy=np.random.default_rng(20261028).standard_normal((8,DIM)).astype(np.float32)
    clock.warmup('parity',lambda:backend.parity_scores(dummy,[[' dummy A',' dummy B'],[' synthetic A',' synthetic B']]))
    jobs = []
    for row in ROWS:
        ix = [i for i, x in enumerate(items) if x['feature'] == row]
        jobs.extend((row, ix[s:s+8]) for s in range(0, len(ix), 8))
    with (Path(out)/'PARITY_SCORES.jsonl').open('x') as stream:
        for j, (row, ix) in enumerate(jobs):
            values = clock.call('parity', lambda: backend.parity_scores(h[ix], templates[row]['olens']), len(jobs)-j-1)
            require(len(values) == len(ix) and all(len(v) == 2 and all(type(s) in (int, float) and math.isfinite(s) for s in v) for v in values), 'Complete finite two-phrase parity outputs')
            for i, scores in zip(ix, values): stream.write(json.dumps({**items[i], 'scores': scores}, allow_nan=False)+'\n')
            stream.flush()
    return {'records': 252, 'phrasing_pairs_per_item': 2, 'raw_scores_sha256': sha(Path(out)/'PARITY_SCORES.jsonl'),
        'labels_loaded': False, 'verdict_computed': False, 'production_records': 0}
