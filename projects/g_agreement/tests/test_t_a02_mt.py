"""CPU-only registered MT gates; original artifacts are never written by tests."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import numpy as np
import pytest

from projects.g_agreement.r_bench import t_a02 as A
from projects.g_agreement.r_bench import t_a02_mt as MT
from projects.g_agreement.tests import _write_guard as WG

REPO = Path(__file__).resolve().parents[3]
_GUARD = WG.ModuleWriteGuard([REPO / 'results/g_agreement', REPO / 'cache/g_agreement',
                           REPO / 'projects/g_agreement/dataset', REPO / 'projects/g_agreement/manifest'])
_write_guard = _GUARD.fixture()


@pytest.fixture(scope='module')
def pool():
    original, world = A.F.build_items(seed=20261018)
    return [it for it in A.make_bank(original, world) if it['split'] == 'pool']


def greedy(text, terminated=True):
    return {'text': text, 'eos_reached': terminated, 'finish_reason': 'eos' if terminated else 'length',
            'generated_token_ids': [1, 9] if terminated else [1] * 8,
            'answer_token_ids': [1] if terminated else [1] * 8, 'eos_token_ids': [9], 'n_generated_tokens': 2 if terminated else 8}


def candidate_score(mass=.9, terminal=.8):
    return {'candidate_mass': mass, 'eos_terminated_candidate_mass': terminal,
            'path_scores': [{'form': form, 'logprob': float(np.log(mass / 4))} for _ in range(2) for form in ('bare', 'leading_space')]}


def test_exact_answer_parser_requires_full_eos_answer():
    assert MT.parse_exact_greedy(greedy(' \nOslo\t'), ['Oslo', 'Lima']) == 'Oslo'
    for text in ('Os', 'Oslo.', 'Oslo Lima', 'It is Oslo', 'oslo', 'Oslo<special>'):
        assert MT.parse_exact_greedy(greedy(text), ['Oslo', 'Lima']) is None
    assert MT.parse_exact_greedy(greedy('Oslo', False), ['Oslo', 'Lima']) is None
    inconsistent = greedy('Oslo'); inconsistent['generated_token_ids'][-1] = 8
    assert MT.parse_exact_greedy(inconsistent, ['Oslo', 'Lima']) is None


def test_complete_prefix_mass_is_not_terminated_probability(pool):
    row = MT.target_record(pool[0], candidate_score(.9, .02), greedy(pool[0]['O']))
    assert row['complete_word_prefix_mass'] == .9
    assert row['terminated_answer_mass'] == .02
    assert np.isclose(row['bare_path_mass'] + row['leading_space_path_mass'], .9)
    assert row['correct_O']
    with pytest.raises(A.NotRun):
        MT.target_record(pool[0], candidate_score(.8, .9), greedy(pool[0]['O']))


def test_unchanged_numerical_gates_fail_single_six_row_cell_error(pool):
    rows = [MT.target_record(it, candidate_score(), greedy(it['O'])) for it in pool]
    assert MT.mt_target_gates(pool, rows)['passed']
    rows[0].update(M=None, correct_O=False, correct_F=False)
    gate = MT.mt_target_gates(pool, rows)
    assert not gate['passed'] and any('O accuracy' in reason for reason in gate['failed'])
    rows = [MT.target_record(it, candidate_score(), greedy(it['O'])) for it in pool]
    for row in rows[:2]:
        row['candidate_mass'] = .79
    assert MT.mt_target_gates(pool, rows)['passed']
    rows[2]['candidate_mass'] = .79
    assert not MT.mt_target_gates(pool, rows)['passed']


def test_eos_freeze_unions_model_and_tokenizer(tmp_path):
    (tmp_path / 'generation_config.json').write_text(json.dumps({'eos_token_id': [7, 9, 7]}))
    assert MT.eos_ids_from_file(tmp_path, SimpleNamespace(eos_token_id=8)) == (7, 8, 9)
    (tmp_path / 'generation_config.json').unlink()
    (tmp_path / 'config.json').write_text(json.dumps({'text_config': {'eos_token_id': 7}}))
    assert MT.eos_ids_from_file(tmp_path, SimpleNamespace(eos_token_id=9)) == (7, 9)


def test_output_cannot_target_original_or_nested_directory(tmp_path):
    source = tmp_path / 'original'
    for out in (source, source / 'mt', tmp_path):
        with pytest.raises(A.NotRun, match='isolated'):
            MT.isolated_output(out, source)
    MT.isolated_output(tmp_path / 'new-mt', source)


def test_cumulative_budget_cannot_reset_or_omit_previous_attempts(tmp_path, monkeypatch):
    source = tmp_path / 'original'; source.mkdir()
    (source / 'billing.json').write_text(json.dumps({'billed_hours': .4423059211174647}))
    guard = tmp_path / 'guard.json'
    guard.write_text(json.dumps({'pod_id': 'mt', 'self_stop_armed': True, 'idle_watchdog_armed': True,
                                'billed_start_epoch': 1000., 'hard_deadline_epoch': 9000.}))
    args = argparse.Namespace(source_run=source, guard_record=guard, pod='mt', billed_start=1000.,
                              already_billed_hours=.4423059211174647, hard_deadline=9000.)
    monkeypatch.setattr(MT.time, 'time', lambda: 1100.)
    budget = MT.MTBudget(args)
    assert budget.deadline == 9000.
    assert MT.RESERVE_SECONDS == 900
    args.already_billed_hours = 0
    with pytest.raises(A.NotRun, match='omit'):
        MT.MTBudget(args)
    args.already_billed_hours = .4423059211174647
    data = json.loads(guard.read_text()); data['hard_deadline_epoch'] = 10000.
    guard.write_text(json.dumps(data))
    with pytest.raises(A.NotRun, match='remaining'):
        MT.MTBudget(args)


@pytest.mark.parametrize('fail_target', [True, False])
def test_execution_never_runs_reader_before_all_target_gates(tmp_path, monkeypatch, pool, fail_target):
    import torch
    from projects.g_agreement.core import model as M
    from projects.g_agreement.core import readers as R
    from projects.g_agreement.r_bench import complete_answers as CA
    from projects.g_agreement.r_bench import exact_prefix as E
    from projects.g_agreement.r_bench import collect as RC
    source = tmp_path / 'original'; (source / 'pool').mkdir(parents=True)
    old_rows = [{'item_id': it['item_id'], 'candidate_mass': .001, 'global_argmax_token_id': 1, 'global_argmax_text': 'fragment'} for it in pool]
    A.append_rows(source / 'pool/target.jsonl', old_rows)
    out = tmp_path / 'new'
    args = argparse.Namespace(out=out, source_run=source, assets_verification=tmp_path/'assets.json', billed_start=1000.,
                              tokenizer_dir=tmp_path, adapter=tmp_path, prereg_commit='registered', pod='pod',
                              already_billed_hours=.44, batch=16, greedy_batch=8)
    budget = SimpleNamespace(check=lambda: None, cumulative_hours_now=lambda: .5, deadline=9000., guard={})
    monkeypatch.setattr(MT, 'MTBudget', lambda a: budget)
    monkeypatch.setattr(MT, 'verified_assets', lambda *a: {'tokenizer_dir': str(tmp_path), 'target_snapshot_dir': str(tmp_path), 'oracle_adapter_dir': str(tmp_path)})
    freeze = {'eos_token_ids': [9], 'marker': {'character': 'X', 'token_id': 1}, 'source_hashes': {}}
    monkeypatch.setattr(MT, 'preflight', lambda a: (freeze, pool, {r: object() for r in A.F.RELATIONS}, np.zeros((48,5120), np.float32)))
    monkeypatch.setattr(MT, 'require_original_unchanged', lambda *a: None)
    monkeypatch.setattr(torch.cuda, 'is_available', lambda: True)
    monkeypatch.setattr(torch.cuda, 'device_count', lambda: 1)
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
    seen_order = []
    def score(model, prefixes, paths, **kw):
        seen_order.extend(prefix[0]-100 for prefix in prefixes)
        return [candidate_score() for _ in prefixes]
    def complete(model, tokenizer, prefixes, **kw):
        return [greedy('extra answer' if fail_target and prefix[0] == 100 else pool[prefix[0]-100]['O']) for prefix in prefixes]
    monkeypatch.setattr(CA, 'score_complete_answers', score)
    monkeypatch.setattr(CA, 'greedy_complete_answers', complete)
    direct = [it for it in pool if it['rule'] == 'DIRECT']
    def queried(reader, H, pairs, questions, **kw):
        assert len(H) == 24
        return [{'lp_A': 1. if it['F']==pair[0] else 0., 'lp_B': 1. if it['F']==pair[1] else 0.}
                for it, pair in zip(direct, pairs)]
    query = Mock(side_effect=queried)
    monkeypatch.setattr(E, 'score_questioned_oracle', query)
    status = MT.run(args)
    assert seen_order == list(range(48))
    assert status['n_test_rows'] == 0
    assert status['original_A02_verdict'] == 'NOT RUN; unchanged'
    if fail_target:
        assert status['status'] == 'NOT RUN'
        query.assert_not_called()
    else:
        assert status['status'].startswith('A02-MT GATES PASS')
        assert query.call_count == 2
    assert A.read_rows(source / 'pool/target.jsonl') == old_rows
    assert len(A.read_rows(out / 'target.jsonl')) == 48


def test_zz_protected_roots_untouched():
    _GUARD.assert_clean()
