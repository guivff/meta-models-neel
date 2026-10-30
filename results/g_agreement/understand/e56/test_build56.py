"""CPU construction tests; no model calls or BOW fits."""
import sys
from pathlib import Path
from collections import Counter
from dataclasses import replace
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common56 import *
import twin_bases,independent_rows
@pytest.fixture(scope='module')
def encode():
 from transformers import PreTrainedTokenizerFast
 p=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json')
 assert sha(p)==TOKENIZER_SHA
 tok=PreTrainedTokenizerFast(tokenizer_file=str(p));return lambda s:tok.encode(s,add_special_tokens=False)
@pytest.mark.parametrize('row',list(twin_bases.SPECS)+list(independent_rows.SPECS))
def test_contract(row,encode):
 m=twin_bases if row in twin_bases.SPECS else independent_rows
 items=m.generate(row);validate(items,m.SPECS[row],lambda x:m.check_label(row,x),encode)
 assert items==m.generate(row)
 with pytest.raises(ValueError):validate([replace(items[0],value=m.SPECS[row].values[1])]+items[1:],m.SPECS[row],lambda x:m.check_label(row,x),encode)
@pytest.mark.parametrize('row',['tense_implicit','linewrap_implicit','language_continuation','anomaly_state'])
def test_implicit_token_bags_identical(row,encode):
 m=twin_bases if row in twin_bases.SPECS else independent_rows
 for a,b in zip(m.generate(row)[::2],m.generate(row)[1::2]):assert Counter(encode(a.text))==Counter(encode(b.text))
def test_line_bins_count_actual_characters():
 for x in twin_bases.generate('linewrap_implicit'):
  n=len(x.text.rsplit('\n',1)[-1]);assert (n<=15 if x.value=='short' else n>=55)
def test_anomaly_glossary_is_not_foreign_sentence():
 for x in independent_rows.generate('anomaly_state'):
  assert ('La lune est claire.' in x.text)==(x.value=='foreign_sentence')
  assert sum(s in x.text for s in independent_rows.NEUTRAL) in (2,3,4)
def test_fact_label_tracks_current_country():
 a,b=independent_rows.generate('fact_recall')[:2]
 assert independent_rows.check_label('fact_recall',a.text)=='Paris'
 assert independent_rows.check_label('fact_recall',b.text)=='Lima'
def test_focus_is_current_not_archived():
 a,b=independent_rows.generate('instructed_focus')[:2]
 assert independent_rows.check_label('instructed_focus',a.text)=='citrus_fruits'
 assert independent_rows.check_label('instructed_focus',b.text)=='birds'

def test_adjective_shared_token_and_content_separation(encode):
 import adjective_row as m
 items=m.generate();validate(items,m.SPEC,m.check_label,encode)
 for split in ['dev','test']:
  words={label:set().union(*(m.content_words(x.text) for x in items if x.split==split and x.value==label)) for label in m.SPEC.values}
  assert not words['adjective']&words['noun']
 assert all(x.text.endswith(' and') for x in items)

def test_complete_bank_twins_and_bridge_identity(encode):
 from bank56 import construct,QUESTIONS,bridge_records
 records,definitions,twins,vocabulary=construct(encode)
 assert len(records)==13*168 and len(definitions)==13 and len(twins)==4
 by={x['id']:x for x in records};assert len(by)==len(records)
 for base,(asked,question) in QUESTIONS.items():
  for x in records:
   if x['feature']==asked:
    original=by[x['implicit_id']]
    assert x['text']==original['text']+'\n'+question
    assert x['label']==original['label'] and x['split']==original['split']
 assert [x for x in records if x['feature']=='reasoning_bridge']==bridge_records()
 assert 'injection_awareness' not in definitions
