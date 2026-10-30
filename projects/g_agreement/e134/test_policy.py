import pytest
from .policy import *
def test_all_rules_and_majority_tie():
 r={44:'a',52:'b',60:'a'}
 assert [predict(p,r) for p in RULES]==['a','b','a','a','a','a',None]
 assert predict('PALL',{44:'a',52:'b'})=='b'
def test_stability_adjacent_not_skipping_abstention():
 assert predict('PSTAB',{44:'a',52:None,60:'a'})=='a'
 assert predict('PSTAB',{44:'a',52:'a',60:'b'})=='a'
 assert predict('PSTAB',{44:'a',52:None,60:'b'})=='b'
def test_agreement_ignores_nonassertions():
 assert predict('PAGREE',{44:None,52:'a',60:'a'})=='a'
 assert predict('PAGREE',{44:None}) is None
def test_unavailable_is_reported():
 s=score([dict(id='1',truth='a',readings={44:'a'})],'P60',10)
 assert s['unavailable']==1 and s['metrics'] is None
def test_denominators_falseclaim_and_coverage():
 rows=[dict(id=str(i),truth='a',readings={44:p}) for i,p in enumerate(['a','b',None])]
 s=score(rows,'P44',20)['metrics']
 assert s['accuracy']['estimate']==1/3 and s['false_claim_rate']['estimate']==1/3 and s['coverage']['estimate']==2/3
 assert wilson(0,0) is None and wilson(0,10)[0]==0
 assert 0< wilson(5,10)[0]<.5<wilson(5,10)[1]<1

def test_labels_never_enter_policy():
 rows=[dict(id=str(i),truth='a',readings={44:'a',52:'b',60:'b'}) for i in range(4)]
 before=[predict(r,rows[0]['readings']) for r in RULES]
 rows[0]['truth']='b'
 assert before==[predict(r,rows[0]['readings']) for r in RULES]
def test_loo_excludes_heldout_and_ties_frozen():
 data={f'T{i}':[dict(id=str(j),truth='a',readings={44:'a',52:'a',60:'a'}) for j in range(3)] for i in range(1,7)}
 for x in data['T4']:x['matcher_matches']={44:['a'],52:['a'],60:['a']}
 e=evaluate(data,10)
 assert e['selection']['adaptive']=='PALL' and e['selection']['fixed']=='P44'
 for t,v in e['leave_one_type_out'].items():assert t not in v['training_types'] and len(v['training_types'])==5
 data['T7']=[]
 with pytest.raises(ValueError):evaluate(data,10)
def test_bad_scalar_duplicate_and_rule_rejected():
 with pytest.raises(ValueError):predict('PALL',{44:['a','b']})
 with pytest.raises(ValueError):predict('OTHER',{})
 row=dict(id='1',truth='a',readings={44:'a'})
 with pytest.raises(ValueError):score([row,row],'P44')
def test_bootstrap_deterministic():
 rows=[dict(id=str(i),truth='a',readings={44:'a' if i%2 else 'b'}) for i in range(10)]
 assert score(rows,'P44',30)==score(rows,'P44',30)

def test_bootstrap_keeps_conditions_of_original_item_together():
 rows=[dict(id=str(i),item_id='original',truth='a',readings={44:p}) for i,p in enumerate(['a','b'])]
 s=score(rows,'P44',30)['metrics']['accuracy']
 assert s['item_bootstrap95']==[.5,.5]

def test_dual_value_normalization_and_t6_told_only_accuracy():
 from .normalize import binary_value,cue_value
 assert binary_value({'values':['A','B']}) is None
 assert binary_value({'values':['B']})=='B'
 assert cue_value(False) is None and cue_value(True)=='told'
 rows=[dict(id='told',truth='told',accuracy_eligible=True,readings={44:'told'}),dict(id='untold',truth='not_told',accuracy_eligible=False,readings={44:'told'})]
 m=score(rows,'P44',30)['metrics']
 assert m['accuracy']['estimate']==1 and m['accuracy']['denominator']==1
 assert m['false_claim_rate']['estimate']==.5 and m['coverage']['estimate']==1


def test_t4_gate_excludes_type_from_all_loto_and_selection():
 data={f'T{i}':[dict(id=str(j),truth='a',readings={44:'a',52:'a',60:'a'}) for j in range(3)] for i in range(1,7)}
 for x in data['T4']:
  x['readings']={44:None,52:'a',60:'a'}
  x['matcher_matches']={44:[],52:['a'],60:['a']}
 e=evaluate(data,10)
 assert e['excluded_selection_types']==['T4'] and len(e['leave_one_type_out'])==5
 assert e['scores']['T4']['PAGREE']['metrics'] is None
 assert e['scores']['T4']['PSTAB']['status']=='NOT_EVALUABLE'
 assert e['scores']['T4']['PALL']['metrics'] is not None
 assert all('T4' not in v['training_types'] for v in e['leave_one_type_out'].values())

def test_fixed_missing_candidate_not_selected_on_incomparable_types():
 data={f'T{i}':[dict(id=str(j),truth='a',readings={44:'a',52:'a',60:'a'}) for j in range(3)] for i in range(1,7)}
 for x in data['T4']:x['matcher_matches']={44:['a'],52:['a'],60:['a']}
 for x in data['T2']:del x['readings'][60]
 e=evaluate(data,10)
 assert e['selection']['fixed_type_means']['P60'] is None
 assert e['selection']['fixed']=='P44'
