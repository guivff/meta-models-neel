from collections import Counter
from types import SimpleNamespace

import numpy as np
import pytest

from projects.g_agreement.understand import e18 as E, e18_worker as W, e18_runtime as R
from projects.g_agreement.understand.e18_analyse import DONOR_RULE
from projects.g_agreement.understand.cpu import dump, read, rows, sha, verify


@pytest.fixture
def collection_fixture(tmp_path, monkeypatch):
    clock = SimpleNamespace(epoch=1800000000., mono=10.)
    timer = SimpleNamespace(time=lambda: clock.epoch, monotonic=lambda: clock.mono)
    monkeypatch.setattr(R, 'ROOT', tmp_path)
    monkeypatch.setattr(R, 'STOP', clock.epoch + 10000)
    monkeypatch.setattr(R, 'time', timer)
    monkeypatch.setattr(W, 'time', timer)
    authority = 'results/g_agreement/understand/e18/DONOR_RULE.fixture.md'
    for filename in [R.BRIEF, authority, *R.REQUIRED_SOURCE]:
        path = tmp_path / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('synthetic test authority; not usable in production')
    dump(tmp_path / R.PLAN, {'donor_rule_status': 'REGISTERED',
         'donor_rule': DONOR_RULE,
         'donor_rule_authority': {'path': authority, 'sha256': sha(tmp_path / authority),
                                  'registered_before_science': True, 'commit': '99518d4e'}})
    assignment = {'issuer': 'integrator', 'experiment': 'E18', 'gpu_count': 1,
        'pod_id': 'synthetic', 'brief_registered': True, 'brief_pushed': True,
        'external_hardstop_verified': True, 'hold_renewer_verified': True,
        'brief_sha256': sha(tmp_path / R.BRIEF), 'plan_sha256': sha(tmp_path / R.PLAN),
        'source_files': {f: sha(tmp_path / f) for f in R.REQUIRED_SOURCE},
        'allocated_gpu_seconds': 2400, 'previous_gpu_seconds': 0,
        'provider_created_epoch': clock.epoch - 10, 'setup_deadline_epoch': clock.epoch + 1490,
        'deadline_epoch': clock.epoch + 3890, 'setup_allowance_seconds': 1500,
        'forecast_method': R.FORECAST_METHOD, 'source_commit': 'synthetic'}
    assignment_path = tmp_path / 'assignment.json'
    dump(assignment_path, assignment)
    g = R.Gate(assignment_path, {k: 3 for k in R.PATHS})
    inp = tmp_path / 'inputs'; inp.mkdir()
    items = {split: [{'id': f'{split}-{i:02d}', 'feature': 'prose_paren', 'split': split}
                      for i in range(48)] for split in ('dev', 'test')}
    W.jsonl(inp / 'items.input.jsonl', items['test'])
    W.jsonl(inp / 'dev.input.jsonl', items['dev'])
    dump(inp / 'ids.json', [r['id'] for r in items['test']])
    dump(inp / 'templates.json', {'prose_paren': {'olens': [['A', 'B'], ['AA', 'BB']]}})
    dump(inp / 'units.json', [{'feature': 'prose_paren', 'indices': list(range(j, j+16))}
                             for j in range(0, 48, 16)])
    for split, filename in [('test', 'donors.json'), ('dev', 'dev.donors.json')]:
        dump(inp / filename, {r['id']: items[split][i ^ 1]['id'] for i, r in enumerate(items[split])})
    dump(inp / 'warm.donors.json', {r['id']: items['dev'][i ^ 1]['id']
                                    for i, r in enumerate(items['dev'][:16])})
    acts = np.arange(48, dtype=np.float32)[:, None].repeat(4, axis=1)
    np.save(inp / 'acts44.npy', acts, allow_pickle=False)
    np.save(inp / 'dev_acts44.npy', acts, allow_pickle=False)
    dump(inp / 'INPUT_SEAL.json', {'files': {p.name: sha(p) for p in inp.iterdir() if p.is_file()}})
    out = tmp_path / 'out'; out.mkdir(); g.out = out
    args = SimpleNamespace(inputs=inp, out=out)
    return SimpleNamespace(g=g, clock=clock, args=args, items=items, calls=[], reader=object(),
                           loads=0, test_score_calls=0)


def install_fakes(f, monkeypatch, timeout=False):
    def advance():
        f.clock.mono += .01
        f.clock.epoch += .01

    def load(a, g):
        assert a is f.args and g is f.g and g.started is None
        f.loads += 1
        return f.reader

    def generate(reader, h, items):
        assert reader is f.reader
        split = items[0]['split']
        assert all(r['split'] == split for r in items)
        if split == 'test':
            assert f.g.admitted
            verify(f.args.out, 'FORECAST_SEAL.json')
        f.calls.append(('generation', split, tuple(r['id'] for r in items)))
        advance()
        return [{'id': r['id'], 'feature': r['feature'], 'layer': 44,
                 'generated_ids': [3, 4], 'continuation_ids': [3, 4], 'raw': r['id']}
                for r in items]

    def score(reader, arm, items, h, templates, raw, donors):
        assert reader is f.reader and arm in E.ARMS
        split = items[0]['split']
        assert h.shape == (len(items), 4)
        assert [int(v[0]) for v in h] == [int(r['id'].split('-')[1]) for r in items]
        if split == 'test':
            assert f.g.admitted
            verify(f.args.out / 'continuations', 'CONTINUATION_SEAL.json')
            assert len(raw) == 48
            f.test_score_calls += 1
            if timeout and f.test_score_calls == 2:
                f.clock.mono += f.g.cap
                raise TimeoutError('synthetic timeout during second asked unit')
        assert all(r['id'] in raw and donors[r['id']] in raw for r in items)
        f.calls.append((arm, split, tuple(r['id'] for r in items)))
        advance()
        return [{'id': r['id'], 'feature': r['feature'],
                 'reader': 'base' if arm == 'd' else 'olens', 'scores': [.25, -.1]}
                for r in items]

    monkeypatch.setattr(W, 'load_reader', load)
    monkeypatch.setattr(W, 'generate', generate)
    monkeypatch.setattr(W, 'score_arm', score)


def test_collection_all_paths_once_after_dev_pilot_and_continuation_seal(collection_fixture, monkeypatch):
    f = collection_fixture
    install_fakes(f, monkeypatch)
    assert W.execute(f.args, f.g) == 'COMPLETE'
    assert f.loads == 1
    assert read(f.args.out / 'run.json')['checkpoint_load_counts'] == {'Oracle_and_base_shared': 1}
    assert read(f.args.out / 'run.json')['science_clock_resets'] == 0
    assert f.g.completed == {k: 3 for k in R.PATHS}
    assert all(len(v) == 3 for v in f.g.samples.values())
    assert f.g.discarded_timing_seconds == pytest.approx(.15)
    assert f.g.forecast()['F_seconds'] == pytest.approx(.30)
    assert read(f.args.out / 'DEV_SMOKE.json')['test_forwards'] == 0
    assert Counter((path, split) for path, split, ids in f.calls) == Counter(
        {(path, 'dev'): 4 for path in R.PATHS} | {(path, 'test'): 3 for path in R.PATHS})
    for path in R.PATHS:
        ids = [key for name, split, group in f.calls if name == path and split == 'test' for key in group]
        assert ids == [r['id'] for r in f.items['test']]
        assert len(set(ids)) == 48
    verify(f.args.out)
    verify(f.args.out / 'continuations', 'CONTINUATION_SEAL.json')
    assert len(rows(f.args.out / 'continuations/raw.jsonl')) == 48
    scores = rows(f.args.out / 'scores.jsonl')
    assert len(scores) == 48 and all(set(r['arms']) == set(E.ARMS) for r in scores)
    assert all(len(pair) == 2 for r in scores for pair in r['arms'].values())
    assert read(f.args.out / 'SCORE_SEAL.json')['status'] == 'E18_COMPLETE'


def test_collection_timeout_seals_partial_scores_without_fake_completion(collection_fixture, monkeypatch):
    f = collection_fixture
    install_fakes(f, monkeypatch, timeout=True)
    assert W.execute(f.args, f.g) == 'INCOMPLETE'
    assert f.loads == 1
    verify(f.args.out)
    verify(f.args.out / 'continuations', 'CONTINUATION_SEAL.json')
    assert read(f.args.out / 'SCORE_SEAL.json')['status'] == 'E18_INCOMPLETE'
    assert read(f.args.out / 'run.json')['status'] == 'INCOMPLETE'
    assert not (f.args.out / 'scores.jsonl').exists()
    assert f.g.completed == {'generation': 3, 'a': 1, 'b': 0, 'c': 0, 'd': 0}
    assert len(list((f.args.out / 'a').glob('unit-*.json'))) == 1
    assert all(not list((f.args.out / arm).glob('unit-*.json')) for arm in ('b', 'c', 'd'))
