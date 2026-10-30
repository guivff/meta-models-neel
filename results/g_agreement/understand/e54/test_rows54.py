"""CPU build checks; no actual BOW fit in tests."""
import sys,importlib
from pathlib import Path
from collections import Counter
from dataclasses import replace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common54 import validate,sha,TOKENIZER_SHA

@pytest.fixture(scope='module')
def encode():
 from transformers import PreTrainedTokenizerFast
 p=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json')
 assert sha(p)==TOKENIZER_SHA
 tok=PreTrainedTokenizerFast(tokenizer_file=str(p));return lambda s:tok.encode(s,add_special_tokens=False)

@pytest.mark.parametrize('name',['reasoning_bridge','injection_awareness'])
def test_shared_contract(name,encode):
 m=importlib.import_module(name);items=m.generate();validate(items,m.SPEC,m.check_label,encode)
 assert items==m.generate()
 for a,b in zip(items[::2],items[1::2]):
  assert Counter(encode(a.text))==Counter(encode(b.text))
  assert a.value!=b.value
 with pytest.raises(ValueError):validate([replace(items[0],value=m.SPEC.values[1])]+items[1:],m.SPEC,m.check_label,encode)
 with pytest.raises(ValueError):m.check_label(items[0].text+' altered')

def test_bridge_mapping_and_shared_answer():
 import reasoning_bridge as m
 assert len(m.FAMILY_BRIDGES)==12
 assert all(x['A']=='cat' and x['B']=='dog' and x['answer_digit_A']==x['answer_digit_B']=='4' for x in m.FAMILY_BRIDGES)
 assert m.CONTINUATIONS is None
 a,b=m.generate()[:2]
 assert m.check_label(a.text)=='cat' and m.check_label(b.text)=='dog'
 assert 'cat' not in a.text and 'dog' not in a.text

def test_injection_checker_uses_current_source():
 import injection_awareness as m
 a,b=m.generate()[:2]
 assert m.check_label(a.text)=='user' and m.check_label(b.text)=='tool_output'
 assert a.text.rsplit('\n',1)[-1]==b.text.rsplit('\n',1)[-1]
 with pytest.raises(ValueError):m.check_label(a.text.replace('TOOL — quoted output:','USER — own instruction:'))

def test_both_continuations_are_explicitly_undefined():
 import reasoning_bridge as a,injection_awareness as b
 for m in [a,b]:assert m.CONTINUATIONS is None and m.CONTINUATION_REASON
