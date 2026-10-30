import json
import numpy as np
import pytest
from .scoring import (regex_values, value_score, summarize, placebo_labels,
                      cluster_draws, contrast, validate_judgments, category_shares, placebo_tvd)
from .blind import packet, select_placebo
from .io import sha, verify, load_bundle
from .e63 import validate_scope
from .score_reader import score, card
from .judged import join_grid

PATTERNS = {'A': r'(?i)\bcat\b', 'B': r'(?i)\bdog\b'}


def record(i, text='cat', label='A', item=None):
    return {'id': str(i), 'item_id': str(i if item is None else item), 'text': text, 'label': label}


@pytest.mark.parametrize('text,truth,want', [
    ('cat', 'A', 1), ('dog', 'A', -1), ('cat dog', 'A', 0), ('', 'B', 0),
    ('concatenate', 'A', 0), ('CAT', 'B', -1)])
def test_regex(text, truth, want):
    assert value_score(regex_values(text, PATTERNS), truth) == want


def test_repeats_cluster_and_weight():
    rows = [record(i, item='a') for i in range(8)] + [record(8, item='b')]
    draws = cluster_draws(rows, [1]*8+[-1], draws=300)
    assert set(draws) <= {-1., 7/9, 1.}
    m = summarize(rows, PATTERNS)
    assert m['n_items'] == 2 and m['n_readouts'] == 9


def test_placebo_label_shared_within_vector_and_order_invariant():
    xs = [record(i, item=i//4) for i in range(80)]
    a, b = placebo_labels(xs), placebo_labels(list(reversed(xs)))
    assert {x['id']: x['label'] for x in a} == {x['id']: x['label'] for x in b}
    assert all(len({x['label'] for x in a if x['item_id'] == str(i)}) == 1 for i in range(20))


def test_placebo_rule_and_any_value():
    real = [record(i) for i in range(40)]
    zero = [record(i, '') for i in range(40)]
    result = contrast(real, zero, PATTERNS, True)
    assert result['R_P1'] == 'PASS' and result['delta_ci'] == [1., 1.]
    both = summarize([record(1, 'cat dog')], PATTERNS)
    assert both['S'] == 0 and both['N'] == 1
    assert contrast(zero, zero, PATTERNS, False)['R_P1'] == 'NOT_APPLICABLE'


def test_blind_payload_does_not_leak_metadata():
    public, key = packet([dict(record(0), property='Question?', values={'A': 'cat', 'B': 'dog'},
                               row='secret_row', arm='secret_arm', reader='secret_reader')])
    assert set(public[0]) == {'id', 'property', 'values', 'readout'}
    assert public[0]['id'] != '0' and key[0]['row'] == 'secret_row'


def test_judgment_validation_lossless_both_and_no_fallback():
    p = [{'id': 'x', 'readout': 'cat dog'}]
    j = [{'id': 'x', 'category': 'states_value', 'values': ['A', 'B'], 'evidence': 'cat dog'}]
    assert validate_judgments(p, j, 'E56')['x']['values'] == ['A', 'B']
    for invalid in [[], j+j, [dict(j[0], evidence='absent')],
                    [dict(j[0], category='names_property')]]:
        with pytest.raises(ValueError):
            validate_judgments(p, invalid, 'E56')
    with pytest.raises(ValueError):
        validate_judgments(p, j, 'D5')


def test_pooled_and_equal_row_shares_differ():
    xs = [{'bank': 'E49', 'row': 'a', 'category': 'topic_content'}]*9 + [
          {'bank': 'E49', 'row': 'b', 'category': 'generic_other'}]
    result = category_shares(xs)
    assert result['readout_weighted']['topic_content'] == .9
    assert result['equal_row']['topic_content'] == .5
    assert placebo_tvd(['topic_content']*200, ['generic_other'])['TVD'] == 1
    with pytest.raises(ValueError):
        placebo_tvd(['topic_content']*200, [])


def test_seal_tampering_and_traversal(tmp_path):
    data = tmp_path/'x.json'
    data.write_text('{}')
    seal = tmp_path/'SEAL.json'
    seal.write_text(json.dumps({'files': {'x.json': sha(data)}}))
    verify(seal, sha(seal))
    data.write_text('[]')
    with pytest.raises(ValueError):
        verify(seal, sha(seal))
    seal.write_text(json.dumps({'files': {'../outside': 'fake'}}))
    with pytest.raises(ValueError):
        verify(seal, sha(seal))


def fixture():
    rows = []
    for reader in ('oracle', 'nla'):
        rows.append({'bank': 'E56', 'row': 'x', 'reader': reader, 'analysis_status': 'COMPLETE_ONCE',
                     'analysis_seal_sha256': 'fixture', 'native_status': 'REPORTED', 'channel': 'native',
                     'patterns': PATTERNS, 'readouts': [record(0)], 'expected_readout_ids': ['0'],
                     'layer': 44 if reader == 'oracle' else 42, 'prompt': '',
                     'controlling_experiment': 'fixture'})
    pools = [dict(record(f'{r}:{a}:{i}:{k}', item=f'{a}:{i}'), reader=r, arm=a, repeat=k,
                  layer=44 if r == 'oracle' else 42)
             for r in ('oracle', 'nla') for a in ('random', 'shuffled') for i in range(200) for k in range(4)]
    return {'schema': 'readerbench-scoring-v1', 'scope_complete': True,
            'banks': ['E56', 'E57', 'E59', 'E62'], 'rows': rows, 'placebo': pools,
            'expected_rows': [[r['bank'], r['row'], r['reader']] for r in rows]}


def test_complete_pool_and_fixed_blind_selection():
    data = fixture()
    validate_scope(data)
    selected = select_placebo(data['placebo'])
    assert len(selected) == 400 and len({x['id'] for x in selected}) == 400
    assert [x['id'] for x in selected] == [x['id'] for x in select_placebo(list(reversed(data['placebo'])))]
    data['placebo'].pop()
    with pytest.raises(ValueError):
        validate_scope(data)


def test_readerbench_sealed_native_only_and_card():
    data = fixture()
    result = score(data, 'oracle')
    assert result['rows'][0]['metric']['coding'] == 'regex'
    assert 'Reader card' in card(result) and 'random:' in card(result)
    with pytest.raises(ValueError):
        score(data, 'oracle', judge=True)
    data['rows'][0]['analysis_status'] = 'RUNNING'
    with pytest.raises(ValueError):
        score(data, 'oracle')


def test_judge_route_and_closed_scope():
    route = {'assigned': True, 'route_id': 'fixture', 'configuration': {'model': 'fixture'}}
    data = {'route': route, 'E56_route': dict(route), 'scope_complete': True,
            'packet': [{'id': 'opaque', 'readout': 'cat'}],
            'judgments': [{'id': 'opaque', 'category': 'topic_content', 'evidence': 'cat'}],
            'private_key': [{'opaque_id': 'opaque', 'bank': 'fixture', 'row': 'r'}]}
    assert join_grid(data, 'D5')[0]['category'] == 'topic_content'
    data['scope_complete'] = False
    with pytest.raises(ValueError):
        join_grid(data, 'D5')
    data['scope_complete'] = True
    data['E56_route'] = dict(route, route_id='substitute')
    with pytest.raises(ValueError):
        join_grid(data, 'D5')


def test_verified_bundle_requires_real_analysis_binding(tmp_path):
    (tmp_path/'source.json').write_text('{}')
    source = tmp_path/'SOURCE_SEAL.json'
    source.write_text(json.dumps({'status': 'COMPLETE_ONCE', 'files': {'source.json': sha(tmp_path/'source.json')}}))
    (tmp_path/'RECEIPT.json').write_text(json.dumps({'issuer': 'integrator', 'verified': True,
        'source_seals': [{'path': str(source), 'sha256': sha(source)}]}))
    (tmp_path/'DATA.json').write_text(json.dumps({'rows': [{'analysis_seal_sha256': sha(source)}]}))
    bundle = tmp_path/'INPUT_SEAL.json'
    bundle.write_text(json.dumps({'files': {k: sha(tmp_path/k) for k in ('RECEIPT.json', 'DATA.json')}}))
    load_bundle(bundle, sha(bundle))
    (tmp_path/'DATA.json').write_text(json.dumps({'rows': [{'analysis_seal_sha256': 'fake'}]}))
    bundle.write_text(json.dumps({'files': {k: sha(tmp_path/k) for k in ('RECEIPT.json', 'DATA.json')}}))
    with pytest.raises(ValueError):
        load_bundle(bundle, sha(bundle))
