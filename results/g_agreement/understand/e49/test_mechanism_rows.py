"""CPU construction checks. Never fit the registered BOW gate here."""
import hashlib
import importlib
import importlib.util
import json
import os
import re
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rows.interface import validate
NAMES = ('arith_carry', 'arith_compare', 'branch_taken', 'var_type_at_use', 'instruction_provenance', 'decimal_separator')
TOKENIZER = Path(os.environ.get('E49_TOKENIZER', '/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_assets/Qwen__Qwen3.6-27B/tokenizer.json'))
TOKENIZER_SHA = '5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'


def module(name):
    return importlib.import_module('rows.' + name)


def source_items():
    # In an integrated checkout row 15 is beside these modules. During owner tests
    # load W-text's real source, never a locally invented twin bank.
    if (HERE/'rows/unit_system.py').exists():
        return module('unit_system').generate()
    root = Path(os.environ.get('E49_WTEXT_ROOT', str(HERE.parents[4]/'wt-wtext/results/g_agreement/understand/e49')))
    path = root/'rows/text_common.py'
    spec = importlib.util.spec_from_file_location('rows._wtext_twin_source', path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.generate('unit_system')


def items(name):
    m = module(name)
    return m.generate(source_items()) if m.SPEC.twin_of else m.generate()


@pytest.fixture(scope='module')
def encode():
    from transformers import PreTrainedTokenizerFast
    assert hashlib.sha256(TOKENIZER.read_bytes()).hexdigest() == TOKENIZER_SHA
    tok = PreTrainedTokenizerFast(tokenizer_file=str(TOKENIZER))
    return lambda s: tok.encode(s, add_special_tokens=False)


@pytest.mark.parametrize('name', NAMES)
def test_shared_contract(name, encode):
    m = module(name)
    bank = items(name)
    assert bank == items(name)
    validate(bank, m.SPEC, m.check_label, encode)
    wrong = m.SPEC.values[1] if bank[0].value == m.SPEC.values[0] else m.SPEC.values[0]
    with pytest.raises(ValueError):
        validate([replace(bank[0], value=wrong), *bank[1:]], m.SPEC, m.check_label, encode)
    with pytest.raises(ValueError):
        m.check_label(bank[0].text + ' extra material')
    for item in bank:
        # The checker accepts raw text only and has no access to record metadata.
        assert m.check_label(item.text) == item.value


@pytest.mark.parametrize('name', NAMES[:2])
def test_operand_digits_balanced_per_pair_and_split(name):
    m = module(name)
    bank = items(name)
    hist = {}
    for item in bank:
        tail = item.text.split('\n')[-1]
        operands = re.findall(r'\d+', tail)[:2]
        counts = Counter(''.join(operands))
        hist[item.source_key] = counts
    for a,b in zip(bank[::2],bank[1::2]):
        assert hist[a.source_key] == hist[b.source_key]
    for split in ('dev','test'):
        totals = [sum((hist[x.source_key] for x in bank if x.split==split and x.value==v), Counter()) for v in m.SPEC.values]
        assert totals[0] == totals[1]


@pytest.mark.parametrize('name', NAMES[2:5])
def test_order_only_pairs(name, encode):
    bank = items(name)
    for a,b in zip(bank[::2],bank[1::2]):
        assert Counter(encode(a.text)) == Counter(encode(b.text))
        assert a.value != b.value


def test_arithmetic_checker_boundary_cases():
    carry = module('arith_carry').check_label
    assert carry('Add.\n14 + 25 =') == 'no_carry'
    assert carry('Add.\n14 + 26 =') == 'carry'
    compare = module('arith_compare').check_label
    assert compare('Compare.\n12 × 34 more than 408? Answer:'.replace('12 ×', 'Is 12 ×')) == 'no'
    assert compare('Compare.\nIs 12 × 34 more than 407? Answer:') == 'yes'


def test_execution_checks_respond_to_program_changes():
    branch = module('branch_taken').check_label
    assert branch('x = 3\nx = x + 2\nx = x * 2\nif x > 7:') == 'taken'
    assert branch('x = 3\nx = x * 2\nx = x + 2\nif x > 8:') == 'not_taken'
    types = module('var_type_at_use').check_label
    assert types('x = 3\ny = "3"\nx, y = y, x\nprint(x') == 'str'
    assert types('x = 3\ny = "3"\nx, y = y, x\nx, y = y, x\nprint(x') == 'int'
    for check in (branch, types):
        with pytest.raises(ValueError):
            check('__import__("os")\n' + ('if x > 0:' if check == branch else 'print(x'))


def test_provenance_checker_tracks_attribution():
    m = module('instruction_provenance')
    x = m.generate()[0].text
    assert m.check_label(x) == 'principal'
    swapped = x.replace("Principal's instruction:", '__TEMP__').replace('Quoted vendor text:', "Principal's instruction:").replace('__TEMP__', 'Quoted vendor text:')
    assert m.check_label(swapped) == 'vendor'
    with pytest.raises(ValueError):
        m.check_label(x.replace('Quoted vendor text:', "Principal's instruction:"))


def test_twin_exact_identity_and_crossing(encode):
    m = module('decimal_separator')
    source = source_items()
    twin = m.generate(source)
    counts = Counter()
    for a,b in zip(source,twin):
        assert a.text == b.text and encode(a.text) == encode(b.text)
        assert a.source_key == b.source_key and a.split == b.split
        assert encode(a.text)[-1] == encode(b.text)[-1]
        counts[a.split,a.value,b.value] += 1
    assert len(counts) == 8 and set(counts.values()) == {21}
    x = twin[0].text
    swapped = x.replace('a comma', '__TEMP__').replace('a point', 'a comma').replace('__TEMP__', 'a point')
    assert m.check_label(swapped) != m.check_label(x)
    with pytest.raises(ValueError):
        m.generate([replace(source[0], row_id='wrong')])
