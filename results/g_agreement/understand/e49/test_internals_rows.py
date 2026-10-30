"""CPU construction checks only; do not fit or evaluate the central BOW gate."""
import sys
import hashlib
import importlib
import re
from pathlib import Path
from collections import Counter
from dataclasses import replace
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rows.interface import validate
NAMES = ('container_after_move', 'holder_after_handovers', 'user_expertise')
TOKENIZER = Path('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_assets/Qwen__Qwen3.6-27B/tokenizer.json')
TOKENIZER_SHA = '5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'

@pytest.fixture(scope='module')
def encode():
    from transformers import PreTrainedTokenizerFast
    assert hashlib.sha256(TOKENIZER.read_bytes()).hexdigest() == TOKENIZER_SHA
    tok = PreTrainedTokenizerFast(tokenizer_file=str(TOKENIZER))
    return lambda text: tok.encode(text, add_special_tokens=False)

@pytest.mark.parametrize('name', NAMES)
def test_shared_contract(name, encode):
    m = importlib.import_module('rows.' + name)
    items = m.generate()
    assert items == m.generate()
    validate(items, m.SPEC, m.check_label, encode)
    assert {x.template_index for x in items if x.split == 'dev'}.isdisjoint(
        {x.template_index for x in items if x.split == 'test'})
    with pytest.raises(ValueError):
        validate([replace(items[0], value=m.SPEC.values[1])] + items[1:], m.SPEC, m.check_label, encode)
    with pytest.raises(ValueError):
        m.check_label(items[0].text + ' An extra event changes the answer.')

@pytest.mark.parametrize('name', NAMES[:2])
def test_state_pairs_have_identical_token_bags(name, encode):
    m = importlib.import_module('rows.' + name)
    items = m.generate()
    for a, b in zip(items[::2], items[1::2]):
        assert Counter(encode(a.text)) == Counter(encode(b.text))
        assert a.value != b.value
        assert m.check_label(a.text) != m.check_label(b.text)
        assert len(encode(a.text)) == len(encode(b.text))


def test_container_checker_tracks_events_in_text():
    from rows import container_after_move as m
    text = m.generate()[0].text
    # Move a different object at the final placement: current tracked state stays bowl.
    assert m.check_label(text.replace('Sam puts the coin in the cup.', 'Sam puts the bead in the cup.')) == 'bowl'
    with pytest.raises(ValueError):
        m.check_label(text.replace('Sam puts the coin in the cup.', 'Sam puts the stone in the cup.'))


def test_holder_checker_checks_transfer_legality():
    from rows import holder_after_handovers as m
    items = m.generate()
    counts = Counter()
    for x in items:
        n = 3 + (x.template_index + x.filler_index) % 3
        counts[x.split, n, x.value] += 1
        assert x.text.endswith(m.CLOSING)
        assert 'Alex' not in m.CLOSING and 'Robin' not in m.CLOSING
    assert set(counts.values()) == {14}
    text = items[0].text
    with pytest.raises(ValueError):
        m.check_label(text.replace('Robin hands the coin to Alex.', 'Alex hands the coin to Robin.', 1))
    # A valid opposite starting state needs all transfer directions changed too.
    with pytest.raises(ValueError):
        m.check_label(text.replace('Robin holds the coin, while Alex holds the key.',
                                   'Alex holds the coin, while Robin holds the key.'))


def test_expertise_topic_and_gender_controls():
    from rows import user_expertise as m
    items = m.generate()
    gender = re.compile(r'\b(he|she|his|her|man|woman|male|female|boy|girl|husband|wife)\b', re.I)
    for a, b in zip(items[::2], items[1::2]):
        assert a.text.split('. ')[0] == b.text.split('. ')[0]
        assert not gender.search(a.text + ' ' + b.text)
    a = items[0]
    changed = a.text.replace(m.REGISTERS[0][0], m.REGISTERS[0][1])
    assert m.check_label(changed) == 'novice'
    with pytest.raises(ValueError):
        m.check_label(a.text.replace(m.REGISTERS[0][0], m.REGISTERS[0][0] + ' ' + m.REGISTERS[0][1]))
