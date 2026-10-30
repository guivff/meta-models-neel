"""Construction checks on CPU. Never run the actual E49 BOW fit here."""
import importlib,sys
from pathlib import Path
import pytest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from rows.interface import validate
from freeze_bank import TOKENIZER_SHA,sha
NAMES=['pronoun_referent','chased_role','asserted_vs_hypothetical','negation_scope','topic_twin','next_paragraph_language','unit_system']

@pytest.fixture(scope='module')
def encode():
 from transformers import PreTrainedTokenizerFast
 p=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json')
 assert sha(p)==TOKENIZER_SHA
 tok=PreTrainedTokenizerFast(tokenizer_file=str(p))
 return lambda text:tok.encode(text,add_special_tokens=False)

@pytest.mark.parametrize('name',NAMES)
def test_contract(name,encode):
 m=importlib.import_module('rows.'+name)
 source=importlib.import_module('rows.'+m.SPEC.twin_of).generate() if m.SPEC.twin_of else None
 items=m.generate(source) if source else m.generate()
 validate(items,m.SPEC,m.check_label,encode)
 if source:
  assert [x.text for x in items]==[x.text for x in source]
  assert [x.source_key for x in items]==[x.source_key for x in source]
  for label in m.SPEC.values:
   assert {y.value for x,y in zip(items,source) if x.value==label}=={'asserted','hypothetical'}

def test_pronoun_checker_uses_named_referent():
 from rows import pronoun_referent as m
 x=m.generate()[0]
 assert m.check_label(x.text)=='giver'
 assert m.check_label(x.text.replace('speaking only about Mara','speaking only about Nora'))=='receiver'

def test_scope_checker_uses_current_clause():
 from rows import asserted_vs_hypothetical as m
 a,b=m.generate()[:2]
 assert m.check_label(a.text)=='asserted' and m.check_label(b.text)=='hypothetical'
 # The closed earlier passage does not determine current scope.
 assert m.check_label(a.text.replace('Suppose, counterfactually, that','It is the case that',1))=='asserted'

def test_decimal_twin_balance_and_latest_note():
 from rows import unit_system as m
 items=m.generate()
 for split in ['dev','test']:
  count={'comma':0,'point':0}
  for x in items:
   if x.split==split:
    note=x.text.rsplit('Format note: ',1)[1]
    count['comma' if note.startswith('use a comma') else 'point']+=1
  assert count=={'comma':42,'point':42}

def test_bow_vocabulary_dev_only():
 from bow_once import counts
 X,v=counts([{'ids':[1,1,2]},{'ids':[2,3]}]);Z,_=counts([{'ids':[1,99,99]}],v)
 assert 99 not in v
 assert X.toarray().tolist()==[[2,1,0],[0,1,1]]
 assert Z.toarray().tolist()==[[1,0,0]]
