import contextlib,copy,json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
import torch
from projects.g_agreement.e140 import runner as r,selection as s
from projects.g_agreement.e127.test_runner import Tiny
from projects.g_agreement.e100.contract import write,sha

def items(n=600):
 return [dict(id=f'p{i}:{m}',pair_id=f'p{i}',family='paraphrase',member=m,ids=list(range(1,13)),read_index=11,candidate_ids=[])for i in range(n)for m in (0,1)]

def public(root,xs,stage='screen'):
 root.mkdir();write(root/'items.json',xs);write(root/'MANIFEST.json',dict(experiment='E140'))
 write(root/'INPUT_SEAL.json',dict(experiment='E140',stage=stage,labels_on_pod=False,files={p.name:sha(p)for p in root.iterdir()}));return sha(root/'INPUT_SEAL.json')

def test_literal_generator_native_capture_and_same_forward_fullvocab():
 assert r.generation_batch is r.old133.generation_batch and r.oracle_batch is r.old136.oracle_batch
 m=Tiny();xs=items(1);out=r.capture_batch(m,xs)
 assert m.calls==1 and set(out['captures'])=={44,52,60}and out['generation_calls']==0 and not out['intervention_installed']
 assert np.array_equal(out['vocab_logits'],torch.cat([m.snapshots[0][63][:,-1]]*8,dim=-1).numpy())
 for L,h in out['captures'].items():assert np.array_equal(h,m.snapshots[0][L][:,11].numpy())
 assert all(v['pair_logits']==[]for v in out['pair_records'])
 assert not m._forward_hooks and all(not b._forward_hooks for b in m.layers)

def test_capture_exception_removes_handles():
 m=Tiny();m.fail_call=1
 with pytest.raises(RuntimeError):r.capture_batch(m,items(1))
 assert not m._forward_hooks and all(not b._forward_hooks for b in m.layers)

def test_scope_and_privacy_gates():
 assert r.validate_items(items(),'screen')==600 and r.validate_items(items(84),'main')==84
 for xs,stage in [(items(599),'screen'),(items(39),'main'),(items(85),'main')]:
  with pytest.raises(ValueError):r.validate_items(xs,stage)
 for key,value in [('X','answer'),('candidate_ids',[[[3],[4]]])]:
  xs=items(40);xs[0][key]=value
  with pytest.raises(ValueError):r.validate_items(xs,'main')

def test_screen_no_fit_no_generation_and_no_reuse(tmp_path,monkeypatch):
 calls=[];monkeypatch.setattr(r,'generation_batch',lambda *a:calls.append(1))
 assert r.screen(None,None,items(),tmp_path/'out',lambda *a:False,gpu_type='fixture')=='NO_FIT'and calls==[]
 with pytest.raises(FileExistsError):r.screen(None,None,items(),tmp_path/'out',lambda *a:True,gpu_type='fixture')

def test_main_same_loaded_model_no_screen_regeneration_240native_reads(tmp_path,monkeypatch):
 m=Tiny();calls=[]
 class RT:
  model=m;tok=object()
  def subject(self):return self.model,self.tok,contextlib.nullcontext()
  def load_oracle(self):assert self.model is None and self.tok is None;calls.append('load')
 rt=RT()
 def oracle(runtime,h,L):
  calls.append((L,len(h)));return [dict(text='synthetic')for _ in h]
 monkeypatch.setattr(r,'oracle_batch',oracle)
 assert r.main_job(rt,items(40),tmp_path/'out',lambda *a:True,gpu_type='fixture')=='COMPLETE'
 assert m.calls==10 and calls.count('load')==1
 assert sum(v[1]for v in calls if isinstance(v,tuple))==240
 assert {v[0]for v in calls if isinstance(v,tuple)}=={44,52,60}
 with pytest.raises(ValueError):r.main_job(rt,items(40),tmp_path/'again',lambda *a:True,gpu_type='fixture')

def test_parser_registered_firstline_case_and_punctuation():
 assert s.parse('\n \n Paris.\nexplanation')=='paris'and s.parse('   ')==''
 assert s.parse('A-b!')=='ab'
 with pytest.raises(ValueError):s.parse(None)

def test_first84_full_multitoken_pairs_not_token_filtered():
 pairs=[[f'{i}:0',f'{i}:1']for i in range(90)];a={i:('alpha beta'if i.endswith(':0')else'gamma delta')for p in pairs for i in p}
 kept,n=s.choose(pairs,a);assert n==90 and len(kept)==84 and kept[-1]['member_ids']==pairs[83]and kept[0]['X']=='alpha beta'
 a[pairs[0][1]]='alpha beta';assert s.choose(pairs,a)[0][0]['member_ids']==pairs[1]

def test_complete_newscreen_freezes_exact_cpu_only_labels_and_main(tmp_path):
 xs=items();ph=public(tmp_path/'public',xs);out=tmp_path/'screen';(out/'jobs').mkdir(parents=True)
 answers=[dict(id=x['id'],text=('Alpha'if x['member']==0 else'Beta')if int(x['pair_id'][1:])<90 else'common')for x in xs]
 write(out/'jobs/000000.json',answers);write(out/'OUTPUT_SEAL.json',dict(experiment='E140',stage='screen',status='COMPLETE',files={'jobs/000000.json':sha(out/'jobs/000000.json')}))
 result=s.select(out,sha(out/'OUTPUT_SEAL.json'),tmp_path/'public',ph,tmp_path/'sel',pair_measurement_rule_authority='c33fcfb40',tokenizer=FixtureTok())
 assert result['qualifying_pairs']==90 and result['kept_pairs']==84 and result['action']=='MAIN'
 main=r.load(tmp_path/'sel/main',result['input_sha256'],'main');assert len(main)==168 and all(x['candidate_ids']==[]for x in main)
 assert all('X'not in x and 'Y'not in x for x in main)
 assert (tmp_path/'sel/cpu_only/SELECTION.PRIVATE.json').stat().st_mode&0o777==0o600

def test_missing_extra_answers_and_unruled_contract_refused(tmp_path):
 with pytest.raises(ValueError):s.choose([['a','b']],{'a':'one'})
 with pytest.raises(ValueError):s.choose([['a','b']],{'a':'one','b':'two','extra':'three'})
 with pytest.raises(ValueError):s.select('unused','unused','unused','unused',tmp_path/'out',pair_measurement_rule_authority='')

def test_actual_original_32token_generator_empty_pair_measure_not_nan():
 from projects.g_agreement.e127.test_runner import Tok
 m=Tiny()
 with pytest.warns(RuntimeWarning):out=r.generation_batch(m,Tok(),items(1))
 assert m.calls==32 and all(len(x['token_ids'])==32 and x['greedy_max_new_tokens']==32 for x in out)
 assert all('pair_mean_a_minus_b'not in x and x['pair_logits']==[]for x in out)
 # JSON output is finite despite the original discarded empty-pair mean.
 json.dumps(out,allow_nan=False)


class FixtureTok:
 def __init__(self):self.seen=[]
 def encode(self,text,add_special_tokens):
  assert add_special_tokens is False;self.seen.append(text)
  return {' alpha':[3],' beta':[4],' alpha one':[3,5],' alpha two':[3,6]}[text]

def test_clarification_first_token_exact_leading_space_and_difference():
 from projects.g_agreement.e140.pair_binding import first_token_axis,measure
 tok=FixtureTok();axis=first_token_axis(tok,'alpha one','beta')
 assert tok.seen==[' alpha one',' beta']and axis['first_token_ids']==[3,4]
 z=np.zeros(10,np.float32);z[3]=7;z[4]=2
 assert measure(z,axis)['logit_X_minus_Y']==5

def test_shared_first_token_not_measured_not_zero_keeps_readouts():
 from projects.g_agreement.e140.pair_binding import first_token_axis,measure
 axis=first_token_axis(FixtureTok(),'alpha one','alpha two')
 assert axis['X_token_ids']!=axis['Y_token_ids']and axis['status']=='NOT MEASURED'
 out=measure(np.zeros(10,np.float32),axis)
 assert out['logit_X_minus_Y']is None and out['readouts_count']is True
 assert s.choose([['a','b']],{'a':'alpha one','b':'alpha two'})[1]==1

def test_axis_no_implicit_normalization_or_wrong_ruling():
 from projects.g_agreement.e140.pair_binding import first_token_axis,measure
 axis=first_token_axis(FixtureTok(),'alpha','beta');axis['authority']='other'
 with pytest.raises(ValueError):measure(np.zeros(10,np.float32),axis)
