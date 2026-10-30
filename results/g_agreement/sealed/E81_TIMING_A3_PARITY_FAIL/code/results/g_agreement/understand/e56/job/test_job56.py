import sys
from pathlib import Path
import numpy as np
import pytest
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
from contract56 import *

def test_bound_inputs_and_sampling():
 b=read(HERE/'INPUT_BINDING.json');p=Path(b['inputs']);verify(p,'INPUT_SEAL.json',b['input_seal_sha256'])
 private=read(b['private_items_path']);lookup={x['id']:x for x in private};samples=read(p/'SAMPLING.json')['native_ids']
 for row,ids in samples.items():assert len(ids)==len(set(ids))==84 and sum(lookup[k]['label'] for k in ids)==42
 for row,t in read(p/'ROW_DEFINITIONS.json')['twins'].items():
  keys=lambda r:{(lookup[k]['template_index'],lookup[k]['filler_index'],lookup[k]['variant']) for k in samples[r]}
  assert keys(row)==keys(t['implicit_row'])
 for a,c in read(p/'DONORS.json').items():assert lookup[a]['feature']==lookup[c]['feature'] and lookup[a]['label']!=lookup[c]['label'] and lookup[a]['cluster']!=lookup[c]['cluster']


def test_injection_repetitions_preserve_twelve_directions():
 from worker56 import readout_records
 b=read(HERE/'INPUT_BINDING.json');p=Path(b['inputs']);items=read(p/'injection/ITEMS.json')['items'];v=np.load(p/'injection/INPUT_VECTORS.npz')['activations'];check_injection(v,items)
 outputs=[[{'raw':'x','text':'x','malformed':False} for _ in range(1)] for x in items]
 r=readout_records('nla',items,outputs,'injection')
 assert len(r)==36 and len({x['direction_id'] for x in r})==12 and len({x['unit_id'] for x in r})==36
 assert all(x['source_layer']==44 and x['reader_native_layer']==42 for x in r)


def test_native_adapter_receives_vectors_unchanged():
 import torch
 from worker56 import Backend
 class Reader:
  def verbalize(self,h,layer,k,sampling,batch):
   assert layer==44 and k==1 and torch.equal(h,torch.tensor([[2.,3.,4.]]));return [['unchanged']*1]
 b=object.__new__(Backend);b.oracle=Reader();h=np.array([[2.,3.,4.]],np.float32);before=h.copy();out=b.native_one('oracle',h)
 assert len(out)==1 and len(out[0])==1 and np.array_equal(h,before)


def test_judge_schema_and_evidence():
 validate_judgment({'id':'x','category':'states_value','values':['A'],'evidence':'past tense'},'A past tense passage')
 for d in [{'id':'x','category':'exhibits','values':['A'],'evidence':'French'},{'id':'x','category':'states_value','values':['B'],'evidence':'invented'}]:
  with pytest.raises(ValueError):validate_judgment(d,'French prose')


def test_r1_exact_boundaries_and_hold():
 from analysis56 import r1_gate
 rows=['tense_implicit','linewrap_implicit','language_continuation','adjective_implicit','anomaly_state']
 assert all(v['pass'] for v in r1_gate(dict.fromkeys(rows,.9),{r:{'G3_AUROC':.6} for r in rows}).values())
 assert not r1_gate(dict.fromkeys(rows,.89),{r:{'G3_AUROC':.6} for r in rows})['tense_implicit']['pass']
 assert read(HERE/'RULE_STATUS.json')['status'] == 'RESOLVED'


def test_shard_budget_and_native_grid():
 from prepare_blind56 import expected_native_grid
 b=read(HERE/'INPUT_BINDING.json');p=Path(b['inputs']);s=read(p/'SHARDS.json');assert sum(s['caps'])==9000
 allids=set()
 for slot in range(3):
  ids,inj=expected_native_grid(p,slot,'oracle');assert not allids&ids;allids|=ids;assert len(inj)==12
 assert len(allids)==13*84+36


def test_signed_bootstrap_keeps_zero_categories_and_eight_repeats():
 from stats_native import rate,signed_value
 import numpy as np
 r=rate([[1]*1]*20+[[-1]*1]*20)
 assert r['S']==0 and r['items']==40 and r['readouts']==40
 assert r['CI95'][0]<0<r['CI95'][1]
 assert rate([[1]*1]*40)['CI95']==[1.,1.]
 assert signed_value({'category':'states_value','values':['A','B']},1)==0
 assert signed_value({'category':'states_value','values':['B']},1)==-1
 assert signed_value({'category':'exhibits','values':[]},1)==0


def test_gate_order_fact_only_blocks_r2_and_j_floor_blocks_r4():
 from analysis56 import rules,IMPLICIT,TWINS,CONTROLS
 rows=set(IMPLICIT+CONTROLS+['fact_recall']+[b for a,b in TWINS]);rates={}
 for reader in ('oracle','nla'):
  for row in rows:rates[reader,row,'text']={'S':.4,'CI95':[.2,.6]}
  rates[reader,'fact_recall','text']={'S':.1,'CI95':[0,.2]}
  for i in range(6):
   rates[reader,'inj'+str(i),'J']={'S':.09,'CI95':[0,.2]}
   rates[reader,'inj'+str(i),'nonJ']={'S':0.,'CI95':[0,0]}
 j={r:{'G3_AUROC':.6} for r in IMPLICIT};p=dict.fromkeys(IMPLICIT,.9)
 out=rules(p,j,rates)
 assert out['readers']['oracle']['R2']=='NOT EVALUABLE'
 assert out['readers']['oracle']['R3']=='NOT MET'
 assert out['readers']['oracle']['R4']=='NOT EVALUABLE'
 rates['oracle','fact_recall','text']={'S':.2,'CI95':[.001,.4]}
 out=rules(p,j,rates)
 assert out['readers']['nla']['R2']=='MET'
 for row in CONTROLS:rates['nla',row,'text']={'S':.29,'CI95':[.1,.4]}
 out=rules(p,j,rates)
 assert out['readers']['nla']['R3']=='NOT EVALUABLE' and out['readers']['oracle']['R2']=='MET'


def test_once_guard_never_reuses_an_existing_output(tmp_path):
 from analysis_io import claim_once
 p=tmp_path/'synthetic_once'
 claim_once(p,'SYNTHETIC','test')
 with pytest.raises(FileExistsError):claim_once(p,'SYNTHETIC','test')
 assert read(p/'ONCE.json')['invocation']==1


def test_r3_exact_point_three_difference_is_inclusive():
 from analysis56 import rules,IMPLICIT,TWINS,CONTROLS
 rows=set(IMPLICIT+CONTROLS+['fact_recall']+[b for a,b in TWINS]);rates={}
 for reader in ('oracle','nla'):
  for row in rows:rates[reader,row,'text']={'S':.4,'CI95':[.2,.6]}
  for a,b in TWINS:rates[reader,b,'text']={'S':.7,'CI95':[.5,.9]}
 result=rules(dict.fromkeys(IMPLICIT,.9),{r:{'G3_AUROC':.6} for r in IMPLICIT},rates)
 assert result['readers']['oracle']['R3']=='MET'
