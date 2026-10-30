"""Offline checks for the registered MT2 parser, fresh capture and gated execution."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from projects.g_agreement.r_bench import t_a02 as A
from projects.g_agreement.r_bench import t_a02_mt as MT
from projects.g_agreement.r_bench import t_a02_mt2 as T
from projects.g_agreement.tests import _write_guard as WG

REPO = Path(__file__).resolve().parents[3]
_GUARD = WG.ModuleWriteGuard([REPO / 'results/g_agreement', REPO / 'cache/g_agreement',
                           REPO / 'projects/g_agreement/dataset', REPO / 'projects/g_agreement/manifest'])
_write_guard = _GUARD.fixture()


@pytest.fixture(scope='module')
def original():
    items, world = A.F.build_items(seed=20261018)
    return [it for it in A.make_bank(items, world) if it['split'] == 'pool']


@pytest.fixture(scope='module')
def pool(original):
    return T.revised_pool(original)


def greedy(text, terminated=True):
    return {'text': text, 'eos_reached': terminated, 'finish_reason': 'eos' if terminated else 'length',
            'generated_token_ids': [1, 9] if terminated else [1] * 8,
            'answer_token_ids': [1] if terminated else [1] * 8, 'eos_token_ids': [9],
            'n_generated_tokens': 2 if terminated else 8}


def score(mass=.9, terminal=.02):
    return {'candidate_mass': mass, 'eos_terminated_candidate_mass': terminal,
            'path_scores': [{'form': form, 'logprob': float(np.log(mass / 4))}
                           for _ in range(2) for form in ('bare', 'leading_space')]}


def test_public_mapping_is_label_blind_and_direct_byte_identical(original, pool):
    changed_labels = copy.deepcopy(original)
    for it in changed_labels:
        it['F'], it['O'] = ('secret-other-F', 'secret-other-O')
    counterfactual = T.revised_pool(changed_labels)
    assert len(pool) == 48 and [it['item_id'] for it in pool] == [it['item_id'] for it in original]
    for old, new, counter in zip(original, pool, counterfactual):
        assert new['prompt_text'] == counter['prompt_text']
        assert new['F'] == old['F'] and new['O'] == old['O']
        if new['rule'] == 'DIRECT':
            assert new['prompt_text'].encode() == old['prompt_text'].encode()
        else:
            first, second = old['values'][::1 if old['source_pair_order'] == 0 else -1]
            rule = T.REVERSE_RULE.format(first=first, second=second)
            assert new['prompt_text'] == old['prompt_text'].replace(A.RULES['REVERSE'], rule)
            assert f'If the actual value is {first}, output {second}.' in new['prompt_text']
            assert f'If the actual value is {second}, output {first}.' in new['prompt_text']
    assert all('prompt_version' not in it for it in original)
    with pytest.raises(A.NotRun, match='48-row'):
        T.revised_pool(original[:-1])


@pytest.mark.parametrize('text', ['Oslo', ' \nOslo\t', 'Oslo.', 'Oslo...', 'Oslo !!', 'Oslo.,;:!?\n', 'Oslo\n.'])
def test_registered_terminal_ascii_punctuation_is_accepted(text):
    assert T.parse_answer(greedy(text), ['Oslo', 'Lima']) == 'Oslo'


@pytest.mark.parametrize('text', ['Os', 'oslo', '"Oslo"', "'Oslo'", 'Oslo ! ?', 'Oslo. !', 'Oslo or Lima',
                                 'It is Oslo.', 'Os.lo', 'Oslo—', 'Oslo…', 'Oslo<special>', '!!!', 'Oslo, Lima.'])
def test_other_text_is_rejected(text):
    assert T.parse_answer(greedy(text), ['Oslo', 'Lima']) is None


def test_eos_cap_and_metadata_are_required():
    assert T.parse_answer(greedy('Oslo', False), ['Oslo', 'Lima']) is None
    exact_cap = greedy('Oslo')
    exact_cap.update(generated_token_ids=[1] * 7 + [9], answer_token_ids=[1] * 7, n_generated_tokens=8)
    assert T.parse_answer(exact_cap, ['Oslo', 'Lima']) == 'Oslo'
    mutations = [dict(generated_token_ids=[1] * 8 + [9], answer_token_ids=[1] * 8, n_generated_tokens=9),
                 dict(generated_token_ids=[9, 1, 9], answer_token_ids=[9, 1], n_generated_tokens=3),
                 dict(n_generated_tokens=3), dict(answer_token_ids=[2]), dict(eos_token_ids=[8]),
                 dict(eos_reached=False), dict(finish_reason='length')]
    for change in mutations:
        bad = {**greedy('Oslo'), **change}
        assert not T.terminated_within_cap(bad)
        assert T.parse_answer(bad, ['Oslo', 'Lima']) is None


def test_prefix_mass_is_separate_from_accepted_answer_grammar(pool):
    row = T.target_record(pool[0], score(.9, .02), greedy(pool[0]['O'] + '.'))
    assert row['M'] == pool[0]['O'] and row['strict_whitespace_only_M'] is None
    assert row['complete_word_prefix_mass'] == .9 and row['terminated_answer_mass'] == .02
    assert np.isclose(row['bare_path_mass'] + row['leading_space_path_mass'], .9)
    assert row['correct_O']
    with pytest.raises(A.NotRun):
        T.target_record(pool[0], score(.8, .9), greedy(pool[0]['O']))


def test_all_eight_cells_and_complete_pool_remain_required(pool):
    rows = [T.target_record(it, score(), greedy(it['O'] + '.')) for it in pool]
    gate = T.target_gates(pool, rows)
    assert gate['passed'] and len(gate['rate_intervals']['O_by_rule_order_template']) == 8
    assert gate['n_exact_answers'] == 48 and gate['n_strict_whitespace_answers'] == 0
    assert gate['n_invalid_format'] == gate['n_nonterminated'] == 0
    assert gate['aggregate']['REVERSE']['O']['successes'] == 24
    rows[0].update(M=None, correct_O=False, correct_F=False)
    gate = T.target_gates(pool, rows)
    assert not gate['passed'] and gate['n_invalid_format'] == 1
    rows = [T.target_record(it, score(), greedy(it['O'])) for it in pool]
    for row in rows[:2]: row['candidate_mass'] = .79
    assert T.target_gates(pool, rows)['passed']
    rows[2]['candidate_mass'] = .79
    assert not T.target_gates(pool, rows)['passed']


def test_both_prior_folders_are_isolated_and_full_tree_hashes_checked(tmp_path, monkeypatch):
    original, previous, out = (tmp_path / name for name in ('original', 'previous', 'new'))
    for root in (original, previous):
        root.mkdir(); (root / 'status.json').write_text(json.dumps({'status': 'NOT RUN'}))
        (root / 'old.txt').write_text('unchanged')
    monkeypatch.setattr(MT, 'snapshot_original', lambda root: {})
    args = argparse.Namespace(source_run=original, previous_run=previous, out=out)
    hashes = T.old_snapshots(args)
    T.require_old_unchanged(args, hashes)
    for bad_out in (original, original / 'nested', previous, previous / 'nested', tmp_path):
        args.out = bad_out
        with pytest.raises(A.NotRun, match='isolated'):
            T.old_snapshots(args)
    args.out = out
    (previous / 'new-file.txt').write_text('unexpected')
    with pytest.raises(A.NotRun, match='A02-MT artifact tree changed'):
        T.require_old_unchanged(args, hashes)


def test_budget_includes_both_prior_runs_and_reserves_fifteen_minutes(tmp_path, monkeypatch):
    previous = tmp_path / 'previous'; previous.mkdir()
    (previous / 'billing.json').write_text(json.dumps({'cumulative_billed_hours': T.MIN_PRIOR_HOURS}))
    guard = tmp_path / 'guard.json'
    data = {'pod_id': 'mt2', 'self_stop_armed': True, 'idle_watchdog_armed': True,
            'billed_start_epoch': 1000., 'hard_deadline_epoch': 8678., 'billed_cap_seconds': 7738, 'stop_margin_seconds': 60}
    guard.write_text(json.dumps(data))
    args = argparse.Namespace(previous_run=previous, guard_record=guard, pod='mt2', billed_start=1000.,
                              already_billed_hours=T.MIN_PRIOR_HOURS, hard_deadline=8678.)
    monkeypatch.setattr(T.time, 'time', lambda: 1100.)
    budget = T.Budget(args)
    assert budget.deadline == 8678. and T.RESERVE_SECONDS == 900
    args.already_billed_hours = .4423059211174647
    with pytest.raises(A.NotRun, match='omits'):
        T.Budget(args)
    args.already_billed_hours = T.MIN_PRIOR_HOURS
    data['billed_cap_seconds'] = 7739
    guard.write_text(json.dumps(data))
    with pytest.raises(A.NotRun, match='remaining'):
        T.Budget(args)
    data['billed_cap_seconds'] = 7738
    guard.write_text(json.dumps(data))
    monkeypatch.setattr(T.time, 'time', lambda: 7800.)
    with pytest.raises(A.NotRun, match='fifteen minutes'):
        T.Budget(args)


@pytest.mark.parametrize('fail_target', [True, False, 'runtime_error'])
def test_fresh_all48_capture_then_target_gates_before_only_direct_reader(tmp_path, monkeypatch, pool, fail_target):
    import torch
    from projects.g_agreement.core import model as M
    from projects.g_agreement.core import readers as R
    from projects.g_agreement.r_bench import complete_answers as CA
    from projects.g_agreement.r_bench import exact_prefix as E
    from projects.g_agreement.r_bench import collect as RC
    source = tmp_path / 'original'; source.mkdir()
    previous = tmp_path / 'previous'; previous.mkdir()
    out = tmp_path / 'new'; out.mkdir()
    args = argparse.Namespace(out=out, source_run=source, previous_run=previous,
                              assets_verification=tmp_path/'assets.json', billed_start=1000.,
                              tokenizer_dir=tmp_path, adapter=tmp_path, prereg_commit='registered', pod='pod',
                              already_billed_hours=T.MIN_PRIOR_HOURS, batch=16, greedy_batch=8, capture_batch=8)
    budget = SimpleNamespace(check=lambda: None, cumulative_hours_now=lambda: .7, deadline=8000., guard={})
    monkeypatch.setattr(T, 'Budget', lambda a: budget)
    monkeypatch.setattr(MT, 'verified_assets', lambda *a: {'tokenizer_dir': str(tmp_path), 'target_snapshot_dir': str(tmp_path), 'oracle_adapter_dir': str(tmp_path)})
    freeze = {'eos_token_ids': [9], 'marker': {'character': 'X', 'token_id': 1}, 'source_snapshots': {}}
    monkeypatch.setattr(T, 'preflight', lambda a: (freeze, pool, {r: object() for r in A.F.RELATIONS}))
    preserve = Mock()
    monkeypatch.setattr(T, 'require_old_unchanged', preserve)
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: True)
    monkeypatch.setattr(torch.cuda, 'device_count', lambda: 1)
    monkeypatch.setattr(torch.cuda, 'get_device_name', lambda i: 'synthetic CPU test')
    monkeypatch.setattr(torch.cuda, 'get_device_properties', lambda i: SimpleNamespace(total_memory=80_000_000_000))
    model = SimpleNamespace(load_adapter=lambda *a, **kw: None, set_adapter=lambda *a: None)
    target = SimpleNamespace(model=model, tokenizer=SimpleNamespace(pad_token_id=0, eos_token_id=9))
    reader = SimpleNamespace(target=target)
    monkeypatch.setattr(M, 'load_target', lambda **kw: target)
    monkeypatch.setattr(R, 'OLensReader', lambda: SimpleNamespace(bind=lambda *a, **kw: reader))
    monkeypatch.setattr(E, 'freeze_oracle_marker', lambda *a, **kw: SimpleNamespace(character='X', token_id=1))
    monkeypatch.setattr(RC, 'git_sha', lambda: 'code')
    by_id = {it['item_id']: i for i, it in enumerate(pool)}
    monkeypatch.setattr(A, 'render_target', lambda tok, it: [100 + by_id[it['item_id']]])
    captured = []
    def capture(model, prefixes, **kw):
        assert kw['adapter_name'] == 'planted_sft' and kw['layers'] == (44,)
        ids = [p[0] - 100 for p in prefixes]; captured.extend(ids)
        return {'states': {44: torch.tensor([[i] * A.C.D_MODEL for i in ids], dtype=torch.bfloat16)},
                'logits': torch.tensor([[i] * 7 for i in ids], dtype=torch.bfloat16)}
    monkeypatch.setattr(E, 'capture_exact_prefix', capture)
    scored = []
    def complete_scores(model, prefixes, paths, **kw):
        assert captured == list(range(48))
        scored.extend(p[0]-100 for p in prefixes)
        if fail_target == 'runtime_error':
            raise RuntimeError('synthetic scoring failure')
        return [score() for _ in prefixes]
    def complete(model, tokenizer, prefixes, **kw):
        assert kw['max_new_tokens'] == 8
        return [greedy('extra answer' if fail_target and p[0] == 100 else pool[p[0]-100]['O'] + '.') for p in prefixes]
    monkeypatch.setattr(CA, 'score_complete_answers', complete_scores)
    monkeypatch.setattr(CA, 'greedy_complete_answers', complete)
    direct = [(i, it) for i,it in enumerate(pool) if it['rule'] == 'DIRECT']
    def queried(reader, H, pairs, questions, **kw):
        assert scored == list(range(48))
        assert H[:, 0].tolist() == [i for i, it in direct]
        assert len(H) == 24 and kw['adapter_name'] == 'default'
        return [{'lp_A': 1. if it['F'] == pair[0] else 0., 'lp_B': 1. if it['F'] == pair[1] else 0.}
                for (_,it),pair in zip(direct,pairs)]
    query = Mock(side_effect=queried)
    monkeypatch.setattr(E, 'score_questioned_oracle', query)
    if fail_target == 'runtime_error':
        with pytest.raises(RuntimeError, match='synthetic scoring failure'):
            T.run(args)
        preserve.assert_called_once_with(args, freeze['source_snapshots'])
        query.assert_not_called()
        assert captured == list(range(48))
        return
    status = T.run(args)
    preserve.assert_called_once_with(args, freeze['source_snapshots'])
    assert captured == scored == list(range(48))
    assert status['n_test_rows'] == 0 and status['fresh_captures'] == 48
    assert all(v == 'NOT RUN; unchanged' for v in status['old_verdicts'].values())
    assert np.load(out/'capture/L44.npy')[:,0].tolist() == list(range(48))
    assert np.load(out/'capture/raw_logits.npy').shape == (48,7)
    assert len(A.read_rows(out/'capture/prefixes.jsonl')) == len(A.read_rows(out/'target.jsonl')) == 48
    if fail_target:
        assert status['status'] == 'NOT RUN'; query.assert_not_called()
    else:
        assert status['status'].startswith('A02-MT2 GATES PASS') and query.call_count == 2


def test_report_paired_historical_comparator_is_descriptive(tmp_path, pool):
    current = [T.target_record(it, score(), greedy(it['O'] + '.')) for it in pool]
    old = [{k:r[k] for k in ('item_id','rule','M','correct_O')} for r in current]
    reverse = next(i for i,r in enumerate(current) if r['rule'] == 'REVERSE')
    old[reverse].update(M=current[reverse]['F'], correct_O=False)
    A.write_json(tmp_path/'status.json', {'status':'NOT RUN','reason':'synthetic fixture only'})
    A.write_json(tmp_path/'target_gate.json', T.target_gates(pool,current))
    A.write_json(tmp_path/'historical_comparator.json', {'rows':old})
    A.append_rows(tmp_path/'target.jsonl', current)
    result = T.report(tmp_path)
    assert result['historical_paired_change']['REVERSE']['wrong_to_correct'] == 1
    assert result['historical_paired_change']['REVERSE']['old_correct_O'] == 23
    report = (tmp_path/'REPORT.md').read_text()
    assert 'descriptive calibration' in report and 'not the probability' in report


def test_zz_protected_roots_untouched():
    _GUARD.assert_clean()
