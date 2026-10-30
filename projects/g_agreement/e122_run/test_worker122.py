"""Synthetic tests for the E122 worker (copy of test_worker105) (no model weights, no real inputs)."""
import hashlib
import json
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from projects.g_agreement.e101.test_e101 import Tiny
from projects.g_agreement.e105 import scoring as S
from . import worker122 as W


def item(r, k, condition, index):
    return dict(id=f'{r}{k}{condition}', inventory_id='i', base_id=f'b{k}', row=r, block=44, condition=condition, ids=[1, 2],
                read_index=1, candidate_ids=[[[3], [3, 4]]], vector_index=index, donor_id=None if condition == '0' else 'd')


def inputs(tmp, n=3):
    r = 'e122';d = tmp/'in'/'inputs';d.mkdir(parents=True)
    items = [item(r, k, c, (None if c == '0' else 2*k+(c == 'S'))) for k in range(n) for c in ('T', 'S', '0')]
    for x in items:x['candidate_ids'] = [[[3], [3, 4]], [[4], [3]], [[3, 4], [4]], [[4], [4, 3]]]
    (d/'items.json').write_text(json.dumps(items));np.save(d/'vectors.npy', np.ones((2*n, 4), np.float32))
    files = {f: hashlib.sha256((d/f).read_bytes()).hexdigest() for f in ('items.json', 'vectors.npy')}
    (d/'INPUT_SEAL.json').write_text(json.dumps(dict(experiment='E122', labels_on_pod=False, files=files)))
    return tmp/'in'


def model_with_layers():
    torch.manual_seed(0);m = Tiny();m.layers.append(torch.nn.Identity());m.config.num_hidden_layers = 46;return m


def args(tmp, deadline): return SimpleNamespace(root=str(inputs(tmp)), assets=None, out=str(tmp/'out'), deadline=deadline)


def test_complete_run_seals_every_cell_once(tmp_path):
    seal = W.run(args(tmp_path, 1e12), S, load=lambda _: (model_with_layers(), 'synthetic'))
    assert seal['status'] == 'COMPLETE' and seal['first_output_utc'] != 'none'
    recs = [x for p in sorted((tmp_path/'out'/'jobs').glob('*.json')) for x in json.loads(p.read_text())['records']]
    assert len(recs) == len({x['id'] for x in recs}) == 9 and all(len(x['pair_logprobs']) == 4 for x in recs) and {x['condition'] for x in recs} == {'T', 'S', '0'}
    assert all(seal['files'][k] for k in ('MEASURED_PROFILE.json',))


def test_no_fit_stops_after_timing_without_outputs(tmp_path):
    seal = W.run(args(tmp_path, 0), S, load=lambda _: (model_with_layers(), 'synthetic'))
    assert seal['status'] == 'NO_FIT' and seal['first_output_utc'] == 'none' and (tmp_path/'out'/'NO_FIT.json').exists()
    assert not list((tmp_path/'out'/'jobs').glob('*.json'))


def test_tampered_input_and_once_only(tmp_path):
    a = args(tmp_path, 1e12);(tmp_path/'in'/'inputs'/'items.json').write_text('[]')
    with pytest.raises(ValueError, match='input hash'):W.run(a, S, load=lambda _: (model_with_layers(), 'synthetic'))
    with pytest.raises(ValueError, match='once only'):W.run(a, S, load=lambda _: (model_with_layers(), 'synthetic'))
