import copy
import json
import pytest
from .clarification2 import normalize, passes, singleton_wire


def test_allowed_normalization_only():
    assert normalize('  “Cat—DOG”\n\t here ') == '"cat-dog" here'
    assert normalize('‘A’\u00a0B–C') == "'a' b-c"
    assert normalize('café') != normalize('cafe')
    assert normalize('cat,dog') != normalize('cat dog')
    assert normalize('not correct') != normalize('correct')


def test_independent_validation_keeps_batchmates_and_raw_evidence():
    good = {'id': 'a', 'readout': '“CAT—dog”'}
    code = {'id': 'a', 'category': 'topic_content', 'evidence': '"cat-dog"'}
    original = copy.deepcopy(code)
    assert passes(good, code, 'D5')[0]
    assert code == original
    assert not passes({'id': 'b', 'readout': 'cat'},
                      {'id': 'b', 'category': 'topic_content', 'evidence': 'dog'}, 'D5')[0]
    assert passes(good, code, 'D5')[0]


def test_no_schema_leniency_or_blank_evidence():
    p = {'id': 'a', 'readout': 'cat dog'}
    assert not passes(p, {'id': 'a', 'category': 'topic_content', 'evidence': ' \n '}, 'D5')[0]
    assert not passes(p, {'id': 'a', 'category': 'silent', 'values': ['A'], 'evidence': ''}, 'E56')[0]
    assert passes(p, {'id': 'a', 'category': 'states_value', 'values': ['A', 'B'], 'evidence': 'CAT DOG'}, 'E56')[0]


def test_singleton_preserves_prompt_and_settings():
    wire = {'model': 'frozen', 'temperature': 0, 'max_tokens': 4096,
            'messages': [{'role': 'system', 'content': 'Frozen rubric'}, {'role': 'user', 'content': 'batch'}]}
    r = {'wire': wire, 'item': {'id': 'a', 'readout': 'text', 'rubric': 'frozen target'}}
    result = singleton_wire(r)
    assert result['messages'][0] == wire['messages'][0]
    assert json.loads(result['messages'][1]['content']) == [r['item']]
    assert result['model'] == wire['model'] and result['max_tokens'] == wire['max_tokens']
    assert wire['messages'][1]['content'] == 'batch'
