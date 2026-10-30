"""Synthetic E35 label preparation/reliability tests, dated 2026-10-25."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

SPEC = importlib.util.spec_from_file_location('e35_labels_under_test', Path(__file__).with_name('latent_labels.py'))
labels = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(labels)


def context(position, activation=None, doc_id='document', **changes):
    value = {'doc_id': doc_id, 'position': position,
             'activation': float(position + 1 if activation is None else activation),
             'text': f'context number {position}: marked token', 'target_span': [0, 7],
             'row_name': 'PRIVATE_ROW', 'latent_index': 999, 'term': 'PRIVATE_TERM',
             'source_group_id': 'PRIVATE_GROUP'}
    value.update(changes)
    return value


@pytest.fixture
def blind_bank():
    selected = list(range(300))
    contexts = {i: [context(p, activation=21 - p, doc_id=f'PRIVATE_DOC_{i}') for p in range(20)]
                for i in selected}
    return labels.build_blind_payloads(selected, contexts)


def annotation(blind_id, label='structure'):
    return {'blind_id': blind_id, 'label': label, 'short_name': 'supported feature',
            'rationale': 'Synthetic evidence for the shared pattern.', 'evidence_indices': [1, 3]}


def test_production_counts_and_seed_are_registered():
    assert (labels.N_LATENTS, labels.N_CONTEXTS, labels.N_DOUBLE_CODED, labels.DEV_ITEMS, labels.SEED) == (
        300, 20, 30, 2100, 20261025)


def test_selection_is_mean_all_dev_items_and_ties_use_latent_index():
    sums = np.ones(305)
    sums[303] = 10
    sums[304] = 10
    chosen = labels.select_top_latents(sums)
    assert chosen == [303, 304] + list(range(298))
    assert labels.select_top_latents(100 * sums) == chosen


@pytest.mark.parametrize('n', [2099, 2101, True, 2100.0])
def test_selection_requires_exact_integer_dev_population(n):
    with pytest.raises(ValueError):
        labels.select_top_latents(np.ones(300), n)


@pytest.mark.parametrize('sums', [np.ones(299), np.ones((1, 300)), np.r_[np.ones(299), -1],
                                np.r_[np.ones(299), np.nan], np.r_[np.ones(299), np.inf]])
def test_selection_rejects_bad_or_incomplete_activation_totals(sums):
    with pytest.raises(ValueError):
        labels.select_top_latents(sums)


def test_contexts_rank_positive_values_then_document_then_position():
    records = [context(i, activation=1, doc_id='a') for i in range(20)]
    records += [context(30, activation=2, doc_id='z'), context(2, activation=1, doc_id='b'),
                context(31, activation=0, doc_id='z')]
    public = labels.top_contexts(list(reversed(records)))
    assert len(public) == 20
    assert public[0]['text'] == records[20]['text']
    assert [r['text'] for r in public[1:]] == [r['text'] for r in records[:19]]
    assert [r['index'] for r in public] == list(range(1, 21))


def test_contexts_preserve_text_and_unicode_character_span_without_private_metadata():
    records = [context(i, text='\tα → café\n', target_span=[5, 9]) for i in range(20)]
    result = labels.top_contexts(records)
    assert all(set(r) == {'index', 'text', 'target_span'} for r in result)
    assert all(r['text'] == '\tα → café\n' and r['target_span'] == [5, 9] for r in result)
    assert 'PRIVATE' not in json.dumps(result)


def test_insufficient_positive_contexts_stop_without_replacing_or_labelling_latent():
    records = [context(i, activation=1 if i < 19 else 0) for i in range(40)]
    with pytest.raises(ValueError, match='fewer than 20'):
        labels.top_contexts(records)


def test_duplicate_corpus_position_rejected_even_if_zero():
    records = [context(i) for i in range(20)] + [context(0, activation=0)]
    with pytest.raises(ValueError, match='duplicate corpus position'):
        labels.top_contexts(records)


@pytest.mark.parametrize('changes', [
    {'activation': -1}, {'activation': float('nan')}, {'activation': True}, {'position': True},
    {'target_span': [0, 0]}, {'target_span': [-1, 2]}, {'target_span': [0, 999]},
    {'target_span': [False, 1]}, {'doc_id': ''}, {'text': ''},
])
def test_invalid_contexts_are_not_silently_dropped(changes):
    invalid = context(99)
    invalid.update(changes)
    records = [context(i) for i in range(20)] + [invalid]
    with pytest.raises(ValueError):
        labels.top_contexts(records)


def test_blind_payloads_have_only_opaque_ids_and_whitelisted_context_fields(blind_bank):
    primary, secondary, key = blind_bank
    assert len(primary) == 300 and len(secondary) == 30
    assert len(key['blind_to_latent']) == 300
    assert len({p['blind_id'] for p in primary}) == 300
    assert all(set(p) == {'blind_id', 'contexts'} for p in primary)
    assert all(p['blind_id'].startswith('B') and len(p['blind_id']) == 33 for p in primary)
    assert 'PRIVATE' not in json.dumps(primary)
    primary_by_id = {p['blind_id']: p for p in primary}
    assert all(p == primary_by_id[p['blind_id']] for p in secondary)
    assert sorted(p['blind_id'] for p in secondary) == key['secondary_blind_ids']
    assert list(key['blind_to_latent'].values()) != [key['blind_to_latent'][p['blind_id']] for p in primary]


def test_blinding_and_secondary_sample_independent_of_input_order():
    contexts = {i: [context(p) for p in range(20)] for i in range(300)}
    original = labels.build_blind_payloads(range(300), contexts)
    reordered = labels.build_blind_payloads(reversed(range(300)), dict(reversed(list(contexts.items()))))
    assert reordered == original


@pytest.mark.parametrize('selected', [list(range(299)), list(range(301)), [0] * 300, list(range(299)) + [True]])
def test_exact_selected_latent_set_required(selected):
    with pytest.raises(ValueError):
        labels.build_blind_payloads(selected, {})


def test_no_extra_missing_context_bank_entries_or_reseed():
    contexts = {i: [context(p) for p in range(20)] for i in range(300)}
    for changed in ({**contexts, 300: []}, {i: v for i, v in contexts.items() if i != 1}):
        with pytest.raises(ValueError, match='exactly the selected'):
            labels.build_blind_payloads(range(300), changed)
    with pytest.raises(ValueError, match='seed'):
        labels.build_blind_payloads(range(300), contexts, seed=20261026)


def test_complete_primary_labels_make_exact_structure_mask(blind_bank):
    primary, secondary, key = blind_bank
    records = [annotation(p['blind_id'], 'structure' if i < 12 else 'other') for i, p in enumerate(primary)]
    mask = labels.structure_mask(records, key, 500)
    assert mask.dtype == bool and mask.shape == (500,) and mask.sum() == 12
    assert set(np.flatnonzero(mask)) == {key['blind_to_latent'][r['blind_id']] for r in records[:12]}
    assert not mask[300:].any()


@pytest.mark.parametrize('change', [
    {'label': 'semantic'}, {'label': 'Structure'}, {'short_name': ''}, {'short_name': 'x' * 81},
    {'rationale': ' '}, {'rationale': 'x' * 1201}, {'evidence_indices': []},
    {'evidence_indices': [0]}, {'evidence_indices': [21]}, {'evidence_indices': [1, 1]},
    {'evidence_indices': [True]}, {'extra_field': 'not allowed'},
])
def test_judge_output_schema_strictly_validated(blind_bank, change):
    primary, _, _ = blind_bank
    records = [annotation(p['blind_id']) for p in primary]
    records[0].update(change)
    with pytest.raises(ValueError):
        labels.validate_annotations(records, [p['blind_id'] for p in primary])


def test_missing_duplicate_or_unknown_annotations_fail_closed(blind_bank):
    primary, _, _ = blind_bank
    ids = [p['blind_id'] for p in primary]
    records = [annotation(i) for i in ids]
    cases = [records[:-1], records + [records[0]], [annotation('unknown')] + records[1:]]
    for case in cases:
        with pytest.raises(ValueError):
            labels.validate_annotations(case, ids)


def test_secondary_selection_cannot_be_changed_after_labels(blind_bank):
    primary, _, key = blind_bank
    changed = {**key, 'secondary_blind_ids': list(reversed(key['secondary_blind_ids']))}
    with pytest.raises(ValueError, match='secondary IDs'):
        labels.structure_mask([annotation(p['blind_id']) for p in primary], changed, 300)


def test_three_category_kappa_uses_only_frozen_thirty_and_preserves_primary(blind_bank):
    primary, _, key = blind_bank
    selected = key['secondary_blind_ids']
    class_by_id = {blind_id: labels.LABELS[i // 10] for i, blind_id in enumerate(selected)}
    records = [annotation(p['blind_id'], class_by_id.get(p['blind_id'], 'structure')) for p in primary]
    secondary = [annotation(i, class_by_id[i]) for i in selected]
    report = labels.cohen_kappa(records, secondary, key)
    assert report['cohen_kappa'] == 1.0 and report['expected_agreement'] == pytest.approx(1 / 3)
    assert report['n_double_coded'] == 30 and report['primary_labels_changed'] is False
    assert all(report['confusion'][label][label] == 10 for label in labels.LABELS)
    secondary[0]['label'] = 'content'
    changed = labels.cohen_kappa(records, secondary, key)
    assert changed['observed_agreement'] == pytest.approx(29 / 30)
    assert changed['cohen_kappa'] == pytest.approx(0.95)
    assert records == [annotation(p['blind_id'], class_by_id.get(p['blind_id'], 'structure')) for p in primary]


def test_constant_marginals_report_undefined_kappa(blind_bank):
    primary, secondary, key = blind_bank
    report = labels.cohen_kappa([annotation(p['blind_id']) for p in primary],
                                [annotation(p['blind_id']) for p in secondary], key)
    assert report['observed_agreement'] == 1 and report['expected_agreement'] == 1
    assert report['cohen_kappa'] is None and report['kappa_status'] == 'UNDEFINED_CONSTANT_MARGINALS'


def _dispatch(primary, secondary, key):
    def role(payloads, name):
        return {'provider': 'synthetic-provider', 'model': 'synthetic-model', 'revision': 'test-revision-20261025',
                'session_id': 'independent-session-' + name,
                'decoding': {'temperature': 0, 'top_p': 1, 'max_output_tokens': 400, 'seed': 20261025},
                'blind_ids_sha256': labels.canonical_sha256(sorted(p['blind_id'] for p in payloads)),
                'payloads_sha256': labels.canonical_sha256(payloads)}
    return {'schema': 'E35_LABEL_DISPATCH_V1', 'pins_frozen_before_dispatch': True,
            'secondary_blinded_to_primary': True, 'rubric_sha256': 'a' * 64, 'prompt_sha256': 'b' * 64,
            'private_key_sha256': labels.canonical_sha256(key),
            'primary': role(primary, 'primary'), 'secondary': role(secondary, 'secondary')}


@pytest.fixture
def custody_bank(blind_bank):
    import copy
    primary, secondary, key = blind_bank
    primary, secondary = copy.deepcopy(primary), copy.deepcopy(secondary)
    return primary, secondary, key, _dispatch(primary, secondary, key)


def _custody(bank):
    return labels.validate_label_custody(*bank, rubric_sha256='a' * 64, prompt_sha256='b' * 64)


def test_canonical_hash_uses_exact_utf8_sorted_compact_json_without_newline():
    import hashlib
    expected = hashlib.sha256('{"a":"café","z":[1,2]}'.encode('utf-8')).hexdigest()
    assert labels.canonical_sha256({'z': [1, 2], 'a': 'café'}) == expected
    assert labels.canonical_sha256({'a': 'café', 'z': [1, 2]}) == expected
    with pytest.raises(ValueError):
        labels.canonical_sha256({'bad': float('nan')})


def test_complete_label_custody_validates_both_exact_payload_sets(custody_bank):
    report = _custody(custody_bank)
    assert report['status'] == 'VERIFIED'
    assert report['primary']['n_payloads'] == 300
    assert report['secondary']['n_payloads'] == 30
    assert report['secondary_payloads_identical_to_primary_subset'] is True
    assert report['dispatch_sha256'] == labels.canonical_sha256(custody_bank[3])


@pytest.mark.parametrize('role', [0, 1])
@pytest.mark.parametrize('failure', ['missing', 'extra', 'duplicate', 'order', 'unknown_id'])
def test_payload_custody_requires_exact_blind_ids_counts_and_order(custody_bank, role, failure):
    bank = list(custody_bank)
    payloads = bank[role]
    if failure == 'missing':
        payloads.pop()
    elif failure == 'extra':
        payloads.append(payloads[0])
    elif failure == 'duplicate':
        payloads[-1] = payloads[0]
    elif failure == 'order':
        payloads.reverse()
    else:
        payloads[0]['blind_id'] = 'B' + 'f' * 32
    with pytest.raises(ValueError):
        _custody(bank)


@pytest.mark.parametrize('failure', ['payload_metadata', 'context_metadata', 'nineteen', 'twentyone',
                                    'bad_index', 'bool_index', 'empty_text', 'empty_span', 'bad_span',
                                    'bool_span', 'tuple_span'])
def test_payload_schema_rejects_leaks_and_malformed_contexts(custody_bank, failure):
    payload = custody_bank[0][0]
    context = payload['contexts'][0]
    if failure == 'payload_metadata':
        payload['latent_index'] = 42
    elif failure == 'context_metadata':
        context['row_name'] = 'hidden'
    elif failure == 'nineteen':
        payload['contexts'].pop()
    elif failure == 'twentyone':
        payload['contexts'].append(dict(context))
    elif failure == 'bad_index':
        context['index'] = 2
    elif failure == 'bool_index':
        context['index'] = True
    elif failure == 'empty_text':
        context['text'] = ''
    elif failure == 'empty_span':
        context['target_span'] = [0, 0]
    elif failure == 'bad_span':
        context['target_span'] = [0, 999]
    elif failure == 'bool_span':
        context['target_span'] = [False, 1]
    else:
        context['target_span'] = (0, 1)
    with pytest.raises(ValueError):
        _custody(custody_bank)


def test_secondary_must_be_identical_to_primary_even_if_its_hash_is_rebound(custody_bank):
    primary, secondary, key, dispatch = custody_bank
    secondary[0]['contexts'][0]['text'] += ' changed evidence'
    dispatch['secondary']['payloads_sha256'] = labels.canonical_sha256(secondary)
    with pytest.raises(ValueError, match='identical to the primary subset'):
        _custody(custody_bank)


@pytest.mark.parametrize('field', ['blind_ids_sha256', 'payloads_sha256'])
@pytest.mark.parametrize('role', ['primary', 'secondary'])
def test_dispatch_binds_canonical_payload_and_selected_id_sets(custody_bank, field, role):
    custody_bank[3][role][field] = '0' * 64
    with pytest.raises(ValueError, match='hash mismatch'):
        _custody(custody_bank)


@pytest.mark.parametrize('field', ['rubric_sha256', 'prompt_sha256', 'private_key_sha256'])
def test_dispatch_binds_rubric_prompt_and_private_mapping(custody_bank, field):
    custody_bank[3][field] = '0' * 64
    with pytest.raises(ValueError, match='binding mismatch'):
        _custody(custody_bank)


@pytest.mark.parametrize('field', ['provider', 'model', 'revision', 'session_id', 'decoding'])
@pytest.mark.parametrize('role', ['primary', 'secondary'])
def test_both_judges_need_complete_configuration_pins(custody_bank, field, role):
    del custody_bank[3][role][field]
    with pytest.raises(ValueError, match='configuration'):
        _custody(custody_bank)


@pytest.mark.parametrize('revision', ['main', 'latest', 'HEAD', '', ' fixed-version '])
def test_judge_revision_is_a_specific_nonempty_version(custody_bank, revision):
    custody_bank[3]['primary']['revision'] = revision
    with pytest.raises(ValueError):
        _custody(custody_bank)


def test_second_judge_cannot_reuse_primary_session(custody_bank):
    custody_bank[3]['secondary']['session_id'] = custody_bank[3]['primary']['session_id']
    with pytest.raises(ValueError, match='independent sessions'):
        _custody(custody_bank)


@pytest.mark.parametrize('field', ['pins_frozen_before_dispatch', 'secondary_blinded_to_primary'])
def test_blinding_and_before_dispatch_attestations_must_be_true(custody_bank, field):
    custody_bank[3][field] = False
    with pytest.raises(ValueError, match='pre-dispatch pins'):
        _custody(custody_bank)


@pytest.mark.parametrize('field,value', [
    ('temperature', float('nan')), ('temperature', -1), ('temperature', True),
    ('top_p', 0), ('top_p', 1.01), ('top_p', float('inf')),
    ('max_output_tokens', 0), ('max_output_tokens', 10.0), ('max_output_tokens', True),
    ('seed', True), ('seed', 1.5), ('other_parameters', []),
    ('other_parameters', {'bad': float('inf')}),
])
def test_decoding_settings_must_be_explicit_valid_finite_json(custody_bank, field, value):
    custody_bank[3]['primary']['decoding'][field] = value
    with pytest.raises(ValueError):
        _custody(custody_bank)


@pytest.mark.parametrize('field', ['temperature', 'top_p', 'max_output_tokens', 'seed'])
def test_missing_decoding_setting_is_not_an_implicit_default(custody_bank, field):
    del custody_bank[3]['primary']['decoding'][field]
    with pytest.raises(ValueError, match='decoding fields'):
        _custody(custody_bank)


def test_provider_unsupported_decoding_controls_are_explicit_nulls(custody_bank):
    custody_bank[3]['primary']['decoding'] = {
        'temperature': None, 'top_p': None, 'seed': None, 'max_output_tokens': 400,
        'other_parameters': {'reasoning_effort': 'low'}}
    assert _custody(custody_bank)['status'] == 'VERIFIED'


def test_unknown_dispatch_fields_cannot_carry_unreviewed_settings(custody_bank):
    custody_bank[3]['new_condition'] = 'not frozen'
    with pytest.raises(ValueError, match='dispatch schema'):
        _custody(custody_bank)
