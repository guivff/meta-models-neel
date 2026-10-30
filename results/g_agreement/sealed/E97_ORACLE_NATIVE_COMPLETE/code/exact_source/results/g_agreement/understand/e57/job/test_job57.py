import sys
from pathlib import Path
import pytest
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from counts57 import named_terms, count_item
from runtime57 import ExtensionBudget


def records(row, texts):
    return [{'reader': 'nla', 'unit_id': 'item', 'feature': row, 'repeat': i, 'text': t} for i, t in enumerate(texts)]


def test_mentions_use_frozen_aliases_and_word_boundaries():
    terms = {'cat': ['cat', 'cats'], 'dog': ['dog']}
    assert named_terms('CATS concatenate dog dog', terms, 'word_exact_casefold') == {'cat', 'dog'}
    assert named_terms('CATS concatenate', terms, 'word_exact_case_sensitive') == set()
    with pytest.raises(ValueError):
        named_terms('cat', terms, 'guess_from_outputs')


def test_category_excludes_last_animal_and_keeps_repeats_nested():
    result = count_item(records('category_switch', ['cat dog dog']), {'animal_lexicon': {'cat': ['cat'], 'dog': ['dog']}, 'last_animal_id': 'dog', 'mention_policy': 'word_exact_casefold'})
    assert result['distinct_over_readouts'] == 1
    assert result['any_mention_rate'] == 1
    assert result['independent_items'] == 1
    assert all(r['named'] == ['cat'] for r in result['per_readout'])


def test_capacity_union_not_sum_or_all_words():
    nouns = {f'noun{i}': [f'noun{i}'] for i in range(12)}
    r = count_item(records('capacity_list', ['noun0 noun0 noun1 noun2 irrelevant']), {'list_nouns': nouns, 'mention_policy': 'word_exact_casefold'})
    assert r['distinct_over_readouts'] == 3
    assert r['mean_distinct_per_readout'] == 3
    assert r['independent_items'] == 1


def test_repetition_grid_cannot_be_pooled():
    rows = records('capacity_list', ['x'] * 8)
    rows[7]['repeat'] = 6
    with pytest.raises(ValueError):
        count_item(rows, {})
    rows = records('capacity_list', ['x'] * 8)
    rows[7]['reader'] = 'oracle'
    with pytest.raises(ValueError):
        count_item(rows, {})


def test_extension_budget_respects_own_phase_and_total_custody():
    assert ExtensionBudget(1200, 1000).end == 3000
    assert ExtensionBudget(4500, 1000).end == 5800
    with pytest.raises(ValueError):
        ExtensionBudget(1000, 1200)
    with pytest.raises(ValueError):
        ExtensionBudget(1200, 1000, seconds=5400)


def test_bound_full_bank_plan_and_per_item_continuations():
 from runtime57 import validate_plan
 from contract56 import ROOT,read,verify
 p=ROOT/'cache/g_agreement/understand/e57/inputs_v4_single'
 verify(p,'INPUT_SEAL.json');plan=read(p/'RUN_PLAN.json');items=read(p/'items.json')
 validate_plan(plan,items,None)
 assert len(plan['rows'])==20 and len(items)==3360
 assert plan['rows']['focus_none']['probe_applicable'] is False
 assert plan['rows']['capacity_list']['probe_applicable'] is False
 assert plan['rows']['count_gradient_first_letter']['continuation_pairs'] is None
 assert plan['rows']['multi_token_entity']['continuation_pairs']=='PER_ITEM'
 assert len({tuple(p[0]) for k,p in plan['item_pairs'].items() if k.startswith('multi_token_entity:')})==6


def test_fake_complete_shard_acquisition(tmp_path,monkeypatch):
 import numpy as np
 import torch
 import mats.probes
 from runtime57 import acquire57
 from contract56 import ROOT,read,verify
 p=ROOT/'cache/g_agreement/understand/e57/inputs_v4_single';plan=read(p/'RUN_PLAN.json');items=read(p/'items.json');dev=None
 class Probe:
  def decision(self,x):return torch.zeros(len(x))
 monkeypatch.setattr(mats.probes,'fit_logreg',lambda *a,**k:Probe())
 class Fake:
  def load_oracle(self):pass
  def load_nla(self):pass
  def validate_tokenization(self,x):pass
  def capture(self,x):return {l:np.zeros((len(x),5120),np.float32) for l in (42,44)}
  def native_one(self,reader,h):return [[{'raw':'silent','text':'silent','malformed':False} for _ in range(1)] for _ in h]
  def take(self,h,ix):return h[ix]
  def score(self,ch,units,h,pairs):return [[0.] for _ in units]
 class Budget:
  end=10**12;observed={}
  def call(self,phase,fn,remaining_units=0):return fn()
 a={'slot':0,'pod_id':'synthetic','e57_input_seal_sha256':'synthetic','e57_source_seal_sha256':'synthetic'}
 acquire57(items,dev,plan,Fake(),Budget(),tmp_path,a)
 s=verify(tmp_path,'OUTPUT_SEAL.json')
 assert s['experiment']=='E57'
 assert len((tmp_path/'oracle.native.jsonl').read_text().splitlines())==len(plan['shards']['0'])*84
 assert all(x['distinct_over_readouts']==0 for x in read(tmp_path/'COUNTS.json'))


def test_registered_e57_rules_on_synthetic_full_grid():
 from contract56 import ROOT,read
 from analysis57 import compute,GROUP_B
 from counts57 import count_item
 p=ROOT/'cache/g_agreement/understand/e57/inputs_v4_single';plan=read(p/'RUN_PLAN.json')
 bank=ROOT.parent/'wt-wtext/results/g_agreement/understand/e57/cache/bank_2026-10-27_v1'
 private={x['id']:x for x in read(bank/'items.PRIVATE.json')};native=[];jj={};counts=[];probes=[]
 for x in private.values():
  if x['split']=='test' and plan['rows'][x['feature']]['probe_applicable']:probes.append({'id':x['id'],'feature':x['feature'],'score':x['label']})
 for reader in ('oracle','nla'):
  for row,ids in plan['native_ids'].items():
   for index,k in enumerate(ids):
    x=private[k];text='silent'
    if row.startswith('focus_'):
     arm=row.split('_')[1];cut={'think':40,'mention':30,'ignore':20,'none':0}[arm]
     if index<cut:text='birds' if x['label']==1 else 'citrus'
    unit=[]
    for repeat in range(1):
     rid=k+':'+reader+':'+str(repeat);r={'id':rid,'unit_id':k,'feature':row,'reader':reader,'repeat':repeat,'text':text};native.append(r);unit.append(r)
     # Group B silent, entity/control correct: independent probe still perfect.
     correct=row not in GROUP_B and plan['rows'][row]['probe_applicable']
     jj[rid]={'category':'states_value' if correct else 'silent','values':['A' if x['label']==1 else 'B'] if correct else []}
    if row in ('category_switch','capacity_list'):counts.append(count_item(unit,plan['count_metadata'][k]))
 j={row:{'G3_AUROC':.5,'J_label':'OUT-J','J_fraction':0.} for row in plan['rows']}
 j['capacity_list']['top50_list_nouns']={k:[] for k in plan['native_ids']['capacity_list']}
 d={'private':private,'plan':plan,'native':native,'probes':probes,'counts':counts}
 out,_=compute(d,jj,j)
 assert out['R_B']['verdict']=='MET' and out['R_B']['falsifier'] is False
 assert all(v['R_A1']=='MET' and v['R_A2']=='MET' for v in out['readers'].values())
 assert all(v['category_switch']['fraction_drop'] is None for v in out['readers'].values())
