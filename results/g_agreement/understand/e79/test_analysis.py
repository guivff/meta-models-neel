import sys
from pathlib import Path
import numpy as np
import pytest
import analysis as a

def cells():
 ids=[str(i) for i in range(84)];out={}
 for row in a.A_ROWS:out[row]={'none':dict.fromkeys(ids,0),'random:1':dict.fromkeys(ids,0)}|{f'{d}:{alpha}':dict.fromkeys(ids,1 if d=='J' else 0) for d in ('J','nonJ') for alpha in (.25,.5,1,2,4)}
 for row in a.B_ROWS:out[row]={d:dict.fromkeys(ids,0 if d=='J' else 1) for d in ('none','J','nonJ','random')}
 return out

def test_decision_rules_and_falsifiers():
 c=cells();u={k:{r:1. for r in a.B_ROWS} for k in ('none','d_J','d_perp','random')};v=a.rules(c,u);assert v['R_C1']=='MET' and v['R_C2']=='MET';assert not v['ArmA_falsifier'] and not v['ArmB_falsifier']
 u['d_J']['format_plan']=.89999;assert a.rules(c,u)['R_C2']=='NOT MET'
 for row in a.A_ROWS:
  for cell in c[row]:c[row][cell]=dict.fromkeys(c[row][cell],0)
 for row in a.B_ROWS:
  for cell in c[row]:c[row][cell]=dict.fromkeys(c[row][cell],0)
 v=a.rules(c,u);assert v['ArmA_falsifier'] and v['ArmB_falsifier'] and v['R_C1']=='NOT MET'

def test_joint_bootstrap_missingness_and_pairing():
 c={'a':{str(i):float(i%2) for i in range(84)},'b':{str(i):float(i%2) for i in range(84)}};v=a.differences(c,'a','b');assert v['delta']==0 and v['CI95']==[0,0]
 c['a']['0']=None;v=a.differences(c,'a','b');assert v['status']=='EVALUABLE' and v['delta']==pytest.approx(np.mean([i%2 for i in range(1,84)])-.5)
 c['a']=dict.fromkeys(c['a'],None);assert a.differences(c,'a','b')['status']=='NOT EVALUABLE'

def test_target_and_true_scoring_are_distinct():
 j=dict(id='x',category='states_value',values=['A'],evidence='A');assert a.signed_value(j,1)==1 and a.signed_value(j,0)==-1
 j=dict(id='x',category='UNPARSEABLE',values=[],evidence='');assert a.signed_value(j,0) is None

def test_blind_export_per_item_values_and_privacy(tmp_path,monkeypatch):
 s=a.read(a.HERE/'ANALYSIS_SPEC.json');s.update(blind_out=str(tmp_path/'blind'),blind_key=str(tmp_path/'key.json'),receipt=str(tmp_path/'receipt.json'));a.dump(Path(s['receipt']),dict(verified=True));root=tmp_path/'root';root.mkdir();a.dump(root/'OUTPUT_SEAL.json',dict(synthetic=True))
 key={x['id']:x for x in a.read(s['private_join'])};b=a.read(a.HERE/'INPUT_BINDING.json');items=a.read(Path(b['inputs'])/'items.json');native=[dict(id=x['id'],text='synthetic readout') for x in items]
 class Done:returncode=0
 monkeypatch.setattr(a.subprocess,'run',lambda *args,**kw:Done())
 a.blind(s,root,key,native);out=Path(s['blind_out']);packet=a.read(out/'RUBRIC_FIELDS.json');join={x['opaque_id']:x['source_id'] for x in a.read(s['blind_key'])};plan=a.read(s['judge_plan'])
 assert len(packet)==len(native) and len({x['id'] for x in packet})==len(native)
 for x in packet:
  assert set(x)=={'id','property','value_A','value_B','readout'} and x['readout']=='synthetic readout'
  k=key[join[x['id']]]
  if k['row']=='page_range_digit':assert [x['value_A'],x['value_B']]==plan['judge_values'][k['source_item_id']]
 with pytest.raises(ValueError):a.blind(s,root,key,native)

def test_scoring_seals():
 s=a.config(a.HERE/'ANALYSIS_SPEC.json');assert Path(s['private_join']).is_file()

def test_rc1_can_pass_at_new_low_doses():
 c=cells();u={k:{r:1. for r in a.B_ROWS} for k in ('none','d_J','d_perp','random')}
 for row in a.A_ROWS:
  for cell in c[row]:c[row][cell]=dict.fromkeys(c[row][cell],0)
 for row in sorted(a.A_ROWS)[:2]:c[row]['J:0.25']=dict.fromkeys(c[row]['J:0.25'],1)
 v=a.rules(c,u);assert v['R_C1']=='MET'
 assert all(v['ArmA'][row]['passing_alphas']==[.25] for row in sorted(a.A_ROWS)[:2])

def test_alpha4_is_descriptive_only_for_rc1():
 c=cells();u={k:{r:1. for r in a.B_ROWS} for k in ('none','d_J','d_perp','random')}
 for row in a.A_ROWS:
  for cell in c[row]:c[row][cell]=dict.fromkeys(c[row][cell],0)
  c[row]['J:4']=dict.fromkeys(c[row]['J:4'],1)
 v=a.rules(c,u);assert v['R_C1']=='NOT MET' and v['ArmA_falsifier'] is True
 assert all(not x['alphas']['4']['rule_eligible'] and x['passing_alphas']==[] for x in v['ArmA'].values())
 for row in a.A_ROWS:c[row]['J:4']=dict.fromkeys(c[row]['J:4'],None)
 assert a.rules(c,u)['R_C1']=='NOT MET'
