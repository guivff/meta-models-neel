"""§86 authoring, label-blind gates and capture-position regressions; no GPU."""
from collections import Counter, defaultdict
import copy
import json
import os
from pathlib import Path
import pytest

from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.blindspot import w10_items as W
from projects.g_agreement.blindspot import w10_checks as C
from projects.g_agreement.blindspot import w10_run as R


@pytest.fixture(scope='module')
def real_tok():
    path = os.environ.get('BLINDSPOT_QWEN_TOKENIZER')
    if not path:
        pytest.skip('set BLINDSPOT_QWEN_TOKENIZER to pinned tokenizer directory')
    return W.load_pinned_tokenizer(path)


@pytest.fixture(scope='module')
def bank(real_tok):
    return W.build(real_tok)


def test_full_real_qwen_design_and_length_report(real_tok, bank):
    report = W.verify(real_tok, bank)
    assert report['items'] == 1680 and report['pairs'] == 840
    assert len(report['checks']) == 28
    assert all(x['ks_p'] == 1 and x['mean_token_difference'] == 0 for x in report['checks'])
    assert Counter(x['feature'] for x in bank) == dict.fromkeys([m+'_'+d for m in W.MODES for d in W.FILLER_TOKENS], 120)
    assert {x['class'] for x in bank} == {'mode'}


@pytest.mark.parametrize('mode', list(W.MODES))
def test_instruction_exact_lengths_and_identical_other_tokens(real_tok, bank, mode):
    instructions = W.instruction_pair(real_tok, mode)
    assert len(W.encode(real_tok, instructions[0])) == len(W.encode(real_tok, instructions[1]))
    for distance in W.FILLER_TOKENS:
        selected = [x for x in bank if x['feature'] == mode+'_'+distance]
        for a, b in zip(selected[::2], selected[1::2]):
            start, end = a['meta']['instruction_token_span']
            assert [start, end] == b['meta']['instruction_token_span']
            assert a['ids'][:start] == b['ids'][:start]
            assert a['ids'][end:] == b['ids'][end:]
            assert len(a['ids']) == len(b['ids'])
            assert a['meta']['assistant_read_index'] == b['meta']['assistant_read_index'] == 15
            assert a['ids'][a['meta']['assistant_start']:] == W.encode(real_tok, a['meta']['passage'])[:16]


def test_invariance_check_rejects_changed_carrier(real_tok, bank):
    changed = copy.deepcopy(bank)
    changed[1]['ids'][-1] += 1
    with pytest.raises(ValueError, match='drift'):
        W.verify(real_tok, changed)


def test_passage_clusters_and_all_check_ids_are_dev_and_balanced(bank):
    selected = set(W.mode_check_ids(bank))
    assert len(selected) == 280
    grouped = defaultdict(list)
    for x in bank:
        if x['id'] in selected:
            assert x['split'] == 'dev'
            grouped[x['feature']].append(x)
    for group in grouped.values():
        assert len(group) == 20
        assert len({x['cluster'] for x in group}) == 6
        assert sorted(Counter(x['value'] for x in group).values()) == [10, 10]
    split_by_passage = defaultdict(set)
    for x in bank:
        split_by_passage[x['meta']['passage']].add(x['split'])
    assert len(split_by_passage) == 60
    assert all(len(v) == 1 for v in split_by_passage.values())


def test_donor_hash_ignores_class_and_preserves_row_cluster(bank):
    donors = W.random_donors(bank)
    flipped = [{**x, 'value': 'do_not_use'} for x in bank]
    assert donors == W.random_donors(flipped)
    index = {x['id']: x for x in bank}
    for x in bank:
        d = index[donors[x['id']]]
        assert (d['feature'], d['cluster'], d['split']) == (x['feature'], x['cluster'], x['split'])
    assert any(d == i for i, d in donors.items())  # self permitted, not excluded based on own value


def test_all_frozen_phrasing_pairs_have_native_variants(real_tok):
    from mats.readers.jlens import token_variants
    rows = W.specs()
    assert len(rows) == 16
    for spec in rows.values():
        for reader in ('olens', 'nla', 'jlens'):
            assert len(spec[reader]) == 2
            assert spec[reader][0] != spec[reader][1]
            assert all(a != b and a.strip() and b.strip() for a, b in spec[reader])
        assert all(token_variants(real_tok, [word]) for pair in spec['jlens'] for word in pair)


@pytest.mark.parametrize('mode,text,a,b', [
    ('language', 'The room is quiet and the box is on the desk.', True, False),
    ('language', 'La pièce est calme et le dossier est sur la table.', False, True),
    ('language', 'xyz', False, False),
    ('format', '{"message": "ready"}', True, False),
    ('format', 'The room is quiet and ready.', False, True),
    ('format', '{"message":', False, False),
    ('format', '"ready"', True, False),
    ('format', '{"x": NaN}', False, False),
    ('format', '```json\n{}\n```', False, False),
])
def test_mode_scripts_are_frozen_conservative_checks(mode, text, a, b):
    out = C.scripted(mode, text)
    assert out['A_follows'] is a and out['B_follows'] is b


def test_mode_gate_exact_twenty_dev_and_seventy_percent(bank):
    selected = set(W.mode_check_ids(bank))
    rows = [x for x in bank if x['id'] in selected]
    results = [{'id': x['id'], 'A_follows': True, 'B_follows': True} for x in rows]
    assert all(x['pass'] for x in C.mode_activity(rows, results, []).values())
    feature = rows[0]['feature']
    ids = [x['id'] for x in rows if x['feature'] == feature]
    for r in results:
        if r['id'] in ids[:7]:
            r.update(A_follows=False, B_follows=False)
    assert not C.mode_activity(rows, results, [])[feature]['pass']
    with pytest.raises(ValueError, match='20 dev'):
        C.mode_activity(rows, results[:-1], [])


def test_surprisal_labels_are_prospective_rank_terciles_not_reader_scores():
    meta = [{'id': str(i), 'domain': 'prose', 'split': 'test', 'cluster': str(i%3)} for i in range(12)]
    logits = [{'id': str(i), 'surprisal_nats': float(i)} for i in range(12)]
    out = C.label_surprisal(meta, logits)
    assert {x['id'] for x in out if x['value'] == 'low'} == {'0', '1', '2', '3'}
    assert {x['id'] for x in out if x['value'] == 'high'} == {'8', '9', '10', '11'}
    assert len(out) == 8
    with pytest.raises(ValueError, match='coverage'):
        C.label_surprisal(meta, logits[:-1])


def test_current_token_surprisal_uses_selected_token():
    import torch
    scores = torch.tensor([[0., 2., 1.], [2., 1., 0.]])
    tokens = torch.tensor([1, 2])
    got = R.current_token_surprisal(scores, tokens)
    expected = -torch.log_softmax(scores, -1)[torch.arange(2), tokens]
    assert torch.allclose(got, expected)
    assert got[0] < got[1]


@pytest.mark.parametrize('forecast', [0, -1, float('inf'), float('nan'), 2161])
def test_forecast_rejects_invalid_and_over_cap(forecast):
    with pytest.raises(ValueError):
        R.allocation(forecast)


def test_forecast_allocation_formula():
    assert R.allocation(1000) == 1860
    assert R.allocation(2160) == 3600


def test_capture_uses_block_outputs_and_previous_token_logits_with_right_padding():
    import torch
    from types import SimpleNamespace
    class FakeModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.anchor = torch.nn.Parameter(torch.zeros(1))
            self.layers = torch.nn.ModuleList([torch.nn.Identity() for _ in range(45)])
            self.config = SimpleNamespace(num_hidden_layers=45)
        def forward(self, input_ids, attention_mask, logits_to_keep, use_cache):
            n = input_ids.shape[1]
            h = torch.stack((input_ids.float(), torch.arange(n).expand_as(input_ids).float()), -1)
            for layer in self.layers:
                h = layer(h)
            logits = torch.zeros((*input_ids.shape, 12))
            logits.scatter_(2, ((input_ids+1)%12).unsqueeze(-1), 5.)
            return SimpleNamespace(logits=logits[:, logits_to_keep])
    items = [{'id': 'long', 'ids': [1, 2, 3, 4]}, {'id': 'short', 'ids': [1, 2]}]
    h, surprise = R.capture_with_surprisal(FakeModel(), SimpleNamespace(pad_token_id=0), items, lambda: None)
    assert set(h) == {42, 44}
    assert h[42].tolist() == [[4., 3.], [2., 1.]]
    assert h[44].tolist() == h[42].tolist()
    assert abs(surprise[0]['surprisal_nats']-surprise[1]['surprisal_nats']) < 1e-6
    assert surprise[0]['surprisal_nats'] < .1


def test_real_freeze_keeps_labels_local(real_tok, tmp_path):
    source = P.ROOT/'cache/g_agreement/blindspot/w1-bank'
    if not source.exists():
        pytest.skip('local W1 source required')
    bank, frozen, staged = [tmp_path/x for x in ('bank', 'freeze', 'stage')]
    W.freeze(real_tok, os.environ['BLINDSPOT_QWEN_TOKENIZER'], source, bank, frozen, staged)
    receipt = P.verify(staged, 'INPUT_SEAL.json')
    assert not list(staged.glob('*DO_NOT_STAGE*'))
    assert not any('DO_NOT_STAGE' in n for n in receipt['files'])
    items, donors, specs, checks = R.inputs(staged)
    assert len(items) == 4368 and len(donors) == 4368 and len(checks) == 280
    assert len(specs) == 16
    manifest = json.loads((bank/'manifest.json').read_text())
    assert manifest['surprisal_pool']['n'] == 2688
    assert manifest['setup_allowance_seconds'] == 1500
    assignment_path = tmp_path/'assignment.json'
    assignment = {'issuer': 'integrator', 'experiment': 'W10', 'pod_id': 'test-pod',
        'brief_registered': True, 'brief_pushed': True, 'manifest_committed': True,
        'external_hardstop_verified': True, 'source_commit': 'a'*40, 'brief_commit': 'b'*40,
        'manifest_commit': 'c'*40, 'source_files': W.source_hashes(),
        'manifest_sha256': P.sha(staged/'manifest.json'), 'section86_sha256': P.sha(P.ROOT/W.SECTION),
        'previous_gpu_seconds': 0, 'science_cap_gpu_seconds': 3600,
        'staging_allowance_seconds': 1500, 'allocated_gpu_seconds': 5100,
        'provider_created_epoch': 95, 'deadline_epoch': 5195}
    P.dump(assignment_path, assignment)
    admitted = R.admit(assignment_path, staged, now=100, pod_id='test-pod')
    assert not Path(admitted['_science_clock_path']).exists()
    assert P.science_deadline(admitted, start=True, now=105) == 3705
    assert P.science_deadline(admitted, now=115) == 3705
    with pytest.raises(ValueError, match='no restart'):
        R.admit(assignment_path, staged, now=115, pod_id='test-pod')
    assignment['source_files'] = {}
    P.dump(assignment_path, assignment)
    with pytest.raises(ValueError, match='source differs'):
        R.admit(assignment_path, staged, now=100, pod_id='test-pod')
