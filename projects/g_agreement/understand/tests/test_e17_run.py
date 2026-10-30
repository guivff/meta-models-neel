from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from projects.g_agreement.understand import e17_run as E


class TinyTarget(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.anchor = torch.nn.Parameter(torch.zeros(()))
        self.config = SimpleNamespace(num_hidden_layers=45)
        self.layers = torch.nn.ModuleList([AddOne() for _ in range(45)])
        self.seen = []
        self.adapter_on = True

    def forward(self, input_ids, attention_mask, **kwargs):
        assert not self.adapter_on
        self.seen.append((input_ids.clone(), attention_mask.clone()))
        pos = torch.arange(input_ids.shape[1])[None, :].expand_as(input_ids)
        hidden = torch.stack((input_ids, pos), dim=-1).float()
        for layer in self.layers:
            hidden = layer(hidden)
        return SimpleNamespace(last_hidden_state=hidden)


class AddOne(torch.nn.Module):
    def forward(self, hidden):
        return hidden + 1


def test_capture_actual_block44_at_read_index_without_future_tokens():
    target = TinyTarget()

    @contextmanager
    def base():
        target.adapter_on = False
        try:
            yield
        finally:
            target.adapter_on = True

    oracle = SimpleNamespace(model=target, tok=SimpleNamespace(pad_token_id=0), base=base)
    items = [{'ids': [4, 5, 6], 'read_index': 2, 'next16_ids': [999] * 16},
             {'ids': [7, 8], 'read_index': 1, 'next16_ids': [998] * 16}]
    h = E.capture_source(oracle, items)
    assert h.tolist() == [[51, 47], [53, 46]]
    assert target.adapter_on
    ids, mask = target.seen[0]
    assert ids.tolist() == [[4, 5, 6], [7, 8, 0]]
    assert mask.tolist() == [[1, 1, 1], [1, 1, 0]]
    with pytest.raises(ValueError, match='end at the read token'):
        E.capture_source(oracle, [{**items[0], 'read_index': 1}])


class Tokenizer:
    def decode(self, ids, skip_special_tokens, clean_up_tokenization_spaces):
        assert skip_special_tokens is False and clean_up_tokenization_spaces is False
        return ' '.join(str(i) for i in ids)

    def encode(self, text, add_special_tokens):
        assert add_special_tokens is False
        return list(map(int, text.split()))


def window_item(offset=0):
    ids = list(range(offset, offset + 16))
    return {'ids': [999], 'next16_ids': ids, 'next16_text': ' '.join(map(str, ids))}


def test_window_is_exact_real_next16_and_uses_e1b_adapter_contract():
    items = [window_item(), window_item(20)]
    seen = {}

    def reconstruct(ar, tok, texts):
        seen['args'] = ar, tok, texts
        return torch.ones((len(texts), 5))

    tok = Tokenizer()
    value = E.reconstruct_window('AR', tok, items, reconstruct)
    assert value.shape == (2, 5)
    assert seen['args'] == ('AR', tok, [x['next16_text'] for x in items])
    assert all('999' not in text for text in seen['args'][2])
    with pytest.raises(ValueError, match='exactly 16'):
        E.window_texts(tok, [{**items[0], 'next16_ids': [1]}])
    with pytest.raises(ValueError, match='retokenize'):
        E.window_texts(tok, [{**items[0], 'next16_text': 'altered'}])


def test_window_rejects_midword_retokenization_changes():
    class Retokenizes(Tokenizer):
        def encode(self, text, add_special_tokens):
            return [100] + super().encode(text, add_special_tokens)[1:]
    with pytest.raises(ValueError, match='retokenize'):
        E.window_texts(Retokenizes(), [window_item()])


def test_continuation_native_bullet_asked_unchanged_default():
    calls = []

    class Oracle:
        def paired_logodds_templates(self, h, layer, pairs, **kwargs):
            calls.append((layer, pairs, kwargs))
            return torch.zeros((2, len(h)))

    pairs = [('a', 'b'), ('c', 'd')]
    h = torch.ones((3, 5))
    E.score_channel(Oracle(), h, pairs, 'continuation')
    E.score_channel(Oracle(), h, pairs, 'asked')
    assert calls == [(44, pairs, {'prefix': '- '}), (44, pairs, {})]
    with pytest.raises(ValueError, match='unknown'):
        E.score_channel(Oracle(), h, pairs, 'invented')


def test_donors_reindex_identical_row_scores_without_sign_flip():
    items = [{'id': i, 'feature': 'prose_paren', 'cell': 'short_early',
              'random_donor_id': i, 'opposite_donor_id': 1 - i} for i in range(2)]
    true = [{'id': i, 'feature': 'prose_paren', 'cell': 'short_early', 'channel': c,
             'arm': 'true', 'scores': [i + 2., i - 3.], 'status': 'COMPLETE'}
            for i in range(2) for c in E.CHANNELS]
    records = E.donor_records(items, true)
    E.validate_grid(items, records)
    lookup = {(r['id'], r['channel'], r['arm']): r for r in records}
    for i in range(2):
        for c in E.CHANNELS:
            assert lookup[i, c, 'random_donor']['scores'] == lookup[i, c, 'true']['scores']
            assert lookup[i, c, 'opposite_swap']['scores'] == lookup[1 - i, c, 'true']['scores']
            assert lookup[i, c, 'opposite_swap']['donor_id'] == 1 - i
    with pytest.raises(ValueError, match='complete unique'):
        E.donor_records(items, true + true[:1])
    with pytest.raises(ValueError, match='incomplete'):
        E.validate_grid(items, records[:-1])
    with pytest.raises(ValueError, match='incomplete'):
        E.validate_grid(items, [{**r, 'scores': [float('nan'), 0]} for r in records])


def test_cap_forecast_includes_retained_elapsed_and_all_remaining_work():
    assert E.forecast_allocation(100, 400) == {
        'forecast_s': 500, 'remaining_s': 400, 'allocation_s': 1110, 'fits': True}
    assert E.forecast_allocation(500, 3100)['allocation_s'] == 3600
    assert E.forecast_allocation(500, 3100)['fits'] is True
    assert E.forecast_allocation(500, 3101)['fits'] is False
    for bad in (float('nan'), float('inf'), -1):
        with pytest.raises(ValueError, match='invalid warmed'):
            E.forecast_allocation(100, bad)


def test_admission_rejects_uncommitted_bank_and_cap_changes(tmp_path, monkeypatch):
    bank = tmp_path / 'bank'
    bank.mkdir()
    (bank / 'manifest.json').write_text(json.dumps({'experiment': 'E17', 'section': 110, 'registration_commit': 'cccccccc'}))
    (bank / 'INPUT_SEAL.json').write_text('{}')
    monkeypatch.setattr(E, 'source_hashes', lambda: {'f.py': 'abc'})
    valid = {'issuer': 'integrator', 'experiment': 'E17', 'pod_id': 'pod',
             'brief_registered': True, 'brief_pushed': True, 'manifest_committed': True,
             'external_hardstop_verified': True, 'source_files': {'f.py': 'abc'},
             'manifest_sha256': E.P.sha(bank / 'manifest.json'),
             'input_seal_sha256': E.P.sha(bank / 'INPUT_SEAL.json'),
             'source_commit': 'a' * 40, 'manifest_commit': 'b' * 40, 'brief_commit': 'c' * 40,
             'provider_created_epoch': 100, 'deadline_epoch': 6200, 'allocated_gpu_seconds': 6100,
             'previous_gpu_seconds': 0, 'science_cap_gpu_seconds': 3600,
             'staging_allowance_seconds': 2400}
    assignment = tmp_path / 'assignment.json'
    assignment.write_text(json.dumps(valid))
    assert E.admit(assignment, bank, now=101, pod_id='pod') == valid
    for patch in ({'manifest_committed': False}, {'science_cap_gpu_seconds': 3601},
                  {'staging_allowance_seconds': 2401}, {'previous_gpu_seconds': 1},
                  {'input_seal_sha256': 'wrong'}, {'pod_id': 'other'}):
        assignment.write_text(json.dumps({**valid, **patch}))
        with pytest.raises(ValueError):
            E.admit(assignment, bank, now=101, pod_id='pod')
    assignment.write_text(json.dumps(valid))
    with pytest.raises(ValueError, match='expired'):
        E.admit(assignment, bank, now=2500, pod_id='pod')


def test_full_worker_retains_each_timed_unit_once_and_seals_all_four_channels(tmp_path, monkeypatch):
    """Full 1920-item mocked run checks pilot retention, row order and donor grid."""
    from collections import Counter
    from projects.g_agreement.blindspot import ar_tests
    from projects.g_agreement.w_claims import ar as AR

    items = []
    for feature, cells in (('prose_paren', 4), ('python_string', 4), ('list_depth', 2)):
        for cell in range(cells):
            for j in range(192):
                index = len(items)
                window = window_item(index)
                items.append({'id': str(index), 'feature': feature, 'cell': str(cell),
                              'ids': [index + 1] * (20 + j % 7), 'read_index': 19 + j % 7,
                              'next16_ids': window['next16_ids'], 'next16_text': window['next16_text'],
                              'random_donor_id': str(index), 'opposite_donor_id': str(index ^ 1)})
    pairs = {f: [('a', 'b'), ('c', 'd')] for f in E.FEATURES}
    bank = tmp_path / 'bank'
    bank.mkdir()
    for name in ('manifest.json', 'INPUT_SEAL.json'):
        (bank / name).write_text('{}')
    assignment = tmp_path / 'assignment.json'
    assignment.write_text('{}')
    assets = tmp_path / 'assets.json'
    assets.write_text('{}')
    state = {'started': False}
    capture_counts = Counter()
    window_counts = Counter()
    score_counts = Counter()

    class FakeGuard:
        def __init__(self, assignment, out):
            self.out = out
            self.first = None
            self.end = E.time.time() + 3600
        def check(self):
            pass
        def start(self):
            state['started'] = True
            self.first = E.time.time()
            E.P.dump(self.out / 'EXPERIMENT_CLOCK.json', {'first_science_epoch': self.first})
        def tighten(self, allocation):
            self.end = self.first + allocation
        def finish(self):
            pass

    def capture(oracle, subset):
        if state['started']:
            capture_counts.update(x['id'] for x in subset)
        return torch.tensor([[float(x['id']), 2., 3.] for x in subset])

    def score(oracle, h, pairs, channel):
        if state['started']:
            score_counts.update((str(int(v)), channel) for v in h[:, 0])
        return torch.stack((h[:, 0], -h[:, 0]))

    def reconstruct(ar, tok, subset):
        if state['started']:
            window_counts.update(x['id'] for x in subset)
        return torch.tensor([[float(x['id']) + 10, 4., 5.] for x in subset])

    oracle = SimpleNamespace(model=object(), tok=Tokenizer(), device='cuda')
    monkeypatch.setattr(E, 'inputs', lambda bank: (items, pairs, pairs))
    monkeypatch.setattr(E, 'admit', lambda assignment, bank: {})
    monkeypatch.setattr(E, 'Guard', FakeGuard)
    monkeypatch.setattr(E, 'capture_source', capture)
    monkeypatch.setattr(E, 'score_channel', score)
    monkeypatch.setattr(E, 'reconstruct_window', reconstruct)
    monkeypatch.setattr(E, '_move', lambda *a: None)
    monkeypatch.setattr(E, '_timed', lambda fn: (fn(), 1.))
    monkeypatch.setattr(E, 'source_hashes', lambda: {'worker': 'hash'})
    monkeypatch.setattr(E.W, '_assets', lambda *a, **k: {'model': 'target', 'olens': 'lens', 'ar': 'ar'})
    monkeypatch.setattr(E.W, '_load_oracle', lambda assets: oracle)
    monkeypatch.setattr(ar_tests, '_assets', lambda *a, **k: {})
    monkeypatch.setattr(AR, 'load_reconstructor', lambda *a: (object(), Tokenizer(), None))
    out = tmp_path / 'out'
    E.run(SimpleNamespace(bank=bank, assignment=assignment, assets=assets,
                          official=tmp_path / 'official', whitener=tmp_path / 'whitener', out=out))
    assert capture_counts == Counter({x['id']: 1 for x in items})
    assert window_counts == Counter({x['id']: 1 for x in items})
    assert score_counts == Counter({(x['id'], c): 1 for x in items for c in E.CHANNELS})
    source = np.load(out / 'source44.npy')
    window = np.load(out / 'window44.npy')
    assert source[:, 0].tolist() == list(range(1920))
    assert window[:, 0].tolist() == list(range(10, 1930))
    assert json.loads((out / 'items.order.json').read_text()) == [x['id'] for x in items]
    records = E.P.rows(out / 'scores.jsonl')
    assert len(records) == 11520
    E.validate_grid(items, records)
    seal = E.P.verify(out, 'SCORE_SEAL.json')
    assert seal['status'] == 'E17_CHANNELS_SEALED_BEFORE_LABEL_JOIN'
    forecast = json.loads((out / 'FORECAST.json').read_text())
    assert forecast['timing_outputs_retained'] is True
    assert all(t['retained_units'] >= 3 for t in forecast['timings'])
