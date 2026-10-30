"""Synthetic CPU tests: stage barrier, immutable bindings, gates before parsing."""
import sys,time,json
from pathlib import Path
from unittest.mock import Mock
import numpy as np
import pytest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));sys.path.insert(0,str(HERE/'vendor'));sys.path.insert(0,str(HERE.parent))
from contract49 import *
import rules49
from statements49 import statement,categorize,PATTERNS

def assignment():
 start=time.time()-5
 return {'gpu_count':1,'cap_seconds':21600,'pod_id':'synthetic','pod_created_epoch':start,'deadline_epoch':start+21600,'source_seal_sha256':'a'*64,'input_seal_sha256':'b'*64}

def release(a,captured):
 return {'release':True,'experiment':'E49','pod_id':a['pod_id'],'source_seal_sha256':a['source_seal_sha256'],'input_seal_sha256':a['input_seal_sha256'],'bank_seal_sha256':BANK_SHA,'capture_seal_sha256':'c'*64,'forecast_commit':'d'*40,'issued_epoch':captured+1}

def test_go_is_explicit_and_bound_to_capture():
 a=assignment();captured=time.time()-2;go=release(a,captured)
 validate_go(go,a,'c'*64,time.time(),captured)
 for k,v in [('release',False),('capture_seal_sha256','x'*64),('pod_id','other'),('forecast_commit',''),('issued_epoch',captured-1),('source_seal_sha256','x'*64),('bank_seal_sha256','x'*64)]:
  with pytest.raises(ValueError):validate_go(go|{k:v},a,'c'*64,time.time(),captured)
 with pytest.raises(ValueError):validate_go(go,a,'c'*64,a['deadline_epoch'],captured)


def test_capture_sealed_before_any_e49_reader(monkeypatch,tmp_path):
 import worker49 as w
 binding=read(HERE/'INPUT_BINDING.json');inp=Path(binding['public_path']);items=read(inp/'items.json')
 backend=Mock();backend.capture.side_effect=lambda x:{l:np.ones((len(x),5120),np.float32) for l in (42,44)}
 class Budget:
  def call(self,phase,fn,remaining_units=0):return fn()
 def parity(backend,budget,out,inputs):dump(Path(out)/'PARITY_RESULT.json',{'status':'PASS'})
 monkeypatch.setattr(w.parity_gate,'run_gate',parity)
 class Paused(Exception):pass
 def barrier(digest,epoch):
  verify(tmp_path/'capture','CAPTURE_SEAL.json',digest)
  assert np.load(tmp_path/'capture/acts44.test.npy').shape==(1344,5120)
  assert not (tmp_path/'gates').exists() and not (tmp_path/'readers').exists()
  backend.score.assert_not_called();backend.native.assert_not_called();backend.base_scores.assert_not_called()
  raise Paused
 with pytest.raises(Paused):w.acquire(items,read(inp/'dev_labels.json'),read(inp/'candidates.json'),backend,Budget(),tmp_path,assignment(),None,barrier)
 assert read(tmp_path/'CAPTURE_READY.json')['reader_calls_on_E49']==0


def test_absent_go_never_releases(monkeypatch,tmp_path):
 import worker49 as w
 class Expired(Exception):pass
 b=Mock();b.check.side_effect=[None,Expired()];monkeypatch.setattr(w.time,'sleep',lambda n:None)
 with pytest.raises(Expired):w.wait_for_go(tmp_path/'absent.json',assignment(),'c'*64,time.time(),b)


EXAMPLES={
'pronoun_referent':('The pronoun refers to the giver.','The pronoun refers to the receiver.'),
'chased_role':('The thief is the chaser.','The policeman is the chaser.'),
'container_after_move':('The coin is now in the cup.','The coin is now in the bowl.'),
'holder_after_handovers':('Alex holds the object.','Robin holds the object.'),
'arith_carry':('The units sum carries.','There is no carry from the units.'),
'arith_compare':('The comparison is yes.','The comparison is no.'),
'branch_taken':('The condition is true.','The condition is false.'),
'var_type_at_use':('x holds an integer.','x holds a string.'),
'asserted_vs_hypothetical':('An asserted claim.','A hypothetical claim.'),
'negation_scope':('A negated predicate.','An unnegated predicate.'),
'instruction_provenance':("The principal's own instruction.",'Quoted vendor text.'),
'user_expertise':('An expert user.','A novice user.'),
'topic_twin':('An engineering topic.','A gardening topic.'),
'next_paragraph_language':('The next paragraph will be in French.','The next paragraph will be in English.'),
'unit_system':('Metric units.','Imperial units.'),
'decimal_separator':('A decimal comma.','A decimal point.')}

@pytest.mark.parametrize('row',list(EXAMPLES))
def test_frozen_regex_values_negation_both_and_silence(row):
 a,b=EXAMPLES[row];assert statement(row,a)=='A';assert statement(row,b)=='B'
 assert statement(row,a+'\n'+b)=='both';assert statement(row,'A passage of text.')=='neither'
 assert statement(row,'Not '+a)=='neither'
 assert categorize(row,a,1)=='correct_only' and categorize(row,a,0)=='wrong_only'


def test_rules_gate_first_strict_middle_band():
 g={'bad':{'kind':'semantic_state','probe':.89,'base':1.,'bow':.5},'ok':{'kind':'descriptor','probe':.9,'base':.85,'oracle':.7}}
 qualified,excluded=rules49.qualify(g);assert list(qualified)==['ok'] and list(excluded)==['bad']
 # Excluded row has no Oracle score: evaluation must not access it.
 r=rules49.evaluate(g,{'bad':'unsayable','ok':'sayable'})
 assert r['precall_accuracy']['accuracy']==0 and r['precall_accuracy_middle_band_excluded']['n']==0


def test_native_mention_denominator_and_both():
 from analysis49 import summarize_native
 records=[{'id':'a','raw':'Metric units. Imperial units.','text':'Metric units. Imperial units.','malformed':False},{'id':'b','raw':'nothing','text':'nothing','malformed':True}]
 r=summarize_native('unit_system',records,['a','b'],{'a':1,'b':0})
 assert r['n']==2 and r['counts']['both']==1 and r['correct_mention_rate']==.5 and r['forecast_truth']=='REPORTED' and r['malformed']==1


def test_input_bank_binding_and_test_labels_withheld():
 b=read(HERE/'INPUT_BINDING.json');p=Path(b['public_path']);verify(p,'INPUT_SEAL.json',b['input_seal_sha256']);items=read(p/'items.json');dev=read(p/'dev_labels.json')
 assert len(items)==2688 and len(dev)==1344
 assert all('label' not in x and 'value' not in x for x in items)
 assert all((x['id'] in dev)==(x['split']=='dev') for x in items)
 assert set(read(HERE/'CANDIDATES.json')['rows'])==set(PATTERNS)


def test_full_synthetic_acquisition_after_bound_release(monkeypatch,tmp_path):
 import worker49 as w
 b=read(HERE/'INPUT_BINDING.json');inp=Path(b['public_path']);items=read(inp/'items.json');a=assignment()
 class Fake:
  def load_oracle(self):pass
  def load_nla(self):pass
  def validate_tokenization(self,items):pass
  def capture(self,items):return {l:np.ones((len(items),5120),np.float32) for l in (42,44)}
  def take(self,h,ix):return h[ix]
  def base_scores(self,items,pairs):return [[0.]*len(pairs) for _ in items]
  def score(self,channel,items,h,pairs):return [[0.]*len(pairs) for _ in items]
  def native(self,reader,h):return [{'raw':'A passage.','text':'A passage.','malformed':False} for _ in h]
 class Budget:
  end=a['deadline_epoch'];observed={}
  def call(self,phase,fn,remaining_units=0):return fn()
 def parity(backend,budget,out,inputs):dump(Path(out)/'PARITY_RESULT.json',{'status':'PASS'})
 monkeypatch.setattr(w.parity_gate,'run_gate',parity)
 def go(cs,ct):return release(a,ct)|{'capture_seal_sha256':cs,'issued_epoch':time.time()}
 w.acquire(items,read(inp/'dev_labels.json'),read(inp/'candidates.json'),Fake(),Budget(),tmp_path,a,None,go)
 verify(tmp_path,'OUTPUT_SEAL.json')
 assert len(read(tmp_path/'gates/probe.json'))==1344 and len(read(tmp_path/'gates/base.json'))==1344
 for row in read(inp/'candidates.json')['rows']:
  for reader in ['oracle','nla']:
   for channel in ['native','asked']:
    assert len((tmp_path/'readers'/row/(reader+'_'+channel+'.jsonl')).read_text().splitlines())==84


def test_no_carry_is_not_positive_carry():
 assert statement('arith_carry','There is no carry into the tens.')=='B'
