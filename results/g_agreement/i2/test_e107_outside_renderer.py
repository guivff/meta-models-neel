import importlib.util
from pathlib import Path
import pytest
p=Path(__file__).with_name('e107_outside_renderer.py');spec=importlib.util.spec_from_file_location('outside',p);M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
def plan(bank='E82',target='belief',b=('other',)):
 return dict(inventory_id='opaque',bank=bank,target=target,property='original property',values={'A':['original'], 'B':list(b)})
def generated(end='stop'):
 return dict(id='opaque',phase='generation',status='GENERATED',finish_reason=end,text='Full outside text\nsecond line',refusal=None)
def render(item,rubric):return dict(id=item['id'],rubric=rubric,readout=item['readout'])
def test_full_text_and_length_preserved():
 for end in ['stop','length']:
  x=M.render_outside([plan()],[generated(end)],{'E82':'frozen'},render)
  assert x[0]['record']['readout']==generated()['text']
def test_separate_target_ids_and_same_question():
 x=M.render_outside([plan(),plan(target='truth')],[generated()],{'E82':'frozen'},render)
 assert x[0]['record']['id']!=x[1]['record']['id'] and x[0]['record']['rubric']==x[1]['record']['rubric']
def test_missing_truth_only_belief():
 M.validate_plan(plan(b=()))
 with pytest.raises(AssertionError):M.validate_plan(plan(target='truth',b=()))
def test_exact_scope_no_missing_or_duplicate_outputs():
 with pytest.raises(AssertionError):M.render_outside([plan()],[],{'E82':'x'},render)
 with pytest.raises(AssertionError):M.render_outside([plan()],[generated(),generated()],{'E82':'x'},render)
def test_refusal_not_silently_rewritten():
 g=generated();g['refusal']='refused'
 with pytest.raises(AssertionError):M.render_outside([plan()],[g],{'E82':'x'},render)
def test_wrong_bank_target_rejected():
 with pytest.raises(AssertionError):M.validate_plan(plan(bank='E81'))
 with pytest.raises(AssertionError):M.validate_plan(plan(bank='E86'))
def test_no_label_metadata_allowed():
 p=plan();p['target_letter']='A'
 with pytest.raises(AssertionError):M.validate_plan(p)
