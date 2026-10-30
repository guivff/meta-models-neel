"""Real pinned-tokenizer audits; no GPU, model weights, or external calls."""
import copy
import os
from pathlib import Path
import pytest
from projects.g_agreement.understand import e17_items as E
from projects.g_agreement.blindspot.items import load_pinned_tokenizer


@pytest.fixture(scope='module')
def data():
    path = Path(os.environ.get('E17_TOKENIZER', 'cache/g_assets/Qwen__Qwen3.6-27B'))
    if not (path / 'tokenizer.json').is_file():
        pytest.skip('set E17_TOKENIZER to the pinned Qwen tokenizer')
    tok = load_pinned_tokenizer(path)
    return tok, E.build(tok)


def pair_only(items, feature='prose_paren', cell='long_late'):
    pid = next(x['pair_id'] for x in items if x['feature'] == feature and x['cell'] == cell)
    pair = copy.deepcopy([x for x in items if x['pair_id'] == pid])
    for x in pair:
        x['random_donor_id'] = x['id']
    return pair


def test_every_item_full_independent_audit(data):
    tok, items = data
    result = E.verify(tok, items)
    assert (result['items'], result['pairs']) == (1920, 960)
    for f in ('prose_paren', 'python_string'):
        assert result['next16_twin_audit'][f + '/long_early'] == {'identical_twin_next16': 96}
        for cell in ('short_late', 'long_late'):
            assert result['next16_twin_audit'][f + '/' + cell] == {'different_twin_next16': 96}
    assert result['next16_twin_audit']['list_depth/mid_item'] == {'identical_twin_next16': 96}
    assert result['next16_twin_audit']['list_depth/line_end'] == {'different_twin_next16': 96}


@pytest.mark.parametrize('field', ['read_index', 'opener_index', 'closer_index', 'span_tokens', 'since_opener', 'to_closer', 'label'])
def test_false_position_or_label_is_rejected(data, field):
    tok, items = data
    pair = pair_only(items)
    pair[0][field] += 1
    with pytest.raises((AssertionError, ValueError, IndexError)):
        E.verify(tok, pair, complete=False)


def test_next16_cannot_include_read_token(data):
    tok, items = data
    pair = pair_only(items)
    x = pair[0]
    x['next16_ids'] = x['full_ids'][x['read_index']:x['read_index'] + 16]
    x['next16_text'] = E.decode(tok, x['next16_ids'])
    with pytest.raises(AssertionError):
        E.verify(tok, pair, complete=False)


def test_lexical_twin_mismatch_is_rejected(data):
    tok, items = data
    pair = pair_only(items)
    x = pair[1]
    text = x['text'].replace(' the ', ' some ', 1)
    pair[1] = E.record(tok, text, x['read_index'], x)
    with pytest.raises((AssertionError, ValueError)):
        E.verify(tok, pair, complete=False)


@pytest.mark.parametrize('cell', ['mid_item', 'line_end'])
def test_list_depth_is_current_state_at_both_capture_kinds(data, cell):
    tok, items = data
    pair = pair_only(items, 'list_depth', cell)
    assert [E.relative_list_depth(x['prefix']) for x in pair] == [1, 3]
    assert pair[0]['read_index'] == pair[1]['read_index']
    assert E.verify(tok, pair, complete=False)['status'] == 'PASS'
    pair[1]['depth'] = 2
    with pytest.raises(AssertionError):
        E.verify(tok, pair, complete=False)


def test_template_leak_is_rejected(data):
    tok, items = data
    pair = pair_only(items)
    pair[0]['split'] = 'test'
    with pytest.raises(AssertionError):
        E.verify(tok, pair, complete=False)


def test_every_cell_has_disjoint_templates_and_balanced_exact_twins(data):
    _, items = data
    for f in E.ROWS:
        for c in E.CELLS if f != 'list_depth' else ('mid_item', 'line_end'):
            selected = [x for x in items if x['feature'] == f and x['cell'] == c]
            for split, expected in [('dev', 32), ('test', 64)]:
                for label in (0, 1):
                    assert len([x for x in selected if x['split'] == split and x['label'] == label]) == expected
    assert all(not set(E.STAGE_KEYS) & {'label', 'value', 'depth', 'full_ids'} for _ in [0])


def test_lexical_draws_deterministic_without_bank_access():
    assert E.fill('python_string', 5, 2) == E.fill('python_string', 5, 2)
    assert E.fill('python_string', 5, 2) != E.fill('python_string', 5, 3)
