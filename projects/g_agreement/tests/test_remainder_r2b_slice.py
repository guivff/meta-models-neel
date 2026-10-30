import copy
import numpy as np
import pytest
from projects.g_agreement.r_bench import remainder_r2b_slice as S,remainder_r2b_runner as R


def test_connected_partner_decoy_cannot_cross_groups():
    rows=[dict(item_id='a',entity='one',planted={'partner':'two'}),dict(item_id='b',entity='two',planted={'partner':'three'})]
    got=S.entity_groups(rows)
    assert got['a']==got['b']


def test_best_block_uses_pool_and_earliest_tie_then_derived_arms():
    cell=dict(item_id='heldout',split='test',tap_blocks=[2,4,6],arm='natural')
    key=R.cell_key(cell)
    fits=[dict(job_id=f'j{b}',block=b,pool_validation_accuracy=.8,raw_normal=[1.,0,0],mean=[0.,0,0],train_cells=['pool'],evaluation_cells=[key]) for b in cell['tap_blocks']]
    jobs=[dict(job_id=f['job_id'],cohort='family',train=['pool'],evaluate=[key]) for f in fits]
    chosen=S.select_fits(fits,jobs);assert chosen['family']['block']==min(cell['tap_blocks'])
    cells=S.causal_cells(chosen,[cell]);assert {c['arm'] for c in cells}==set(S.ARMS)
    random=next(c for c in cells if c['arm']=='random_ablation')['ablation']
    assert np.isclose(np.linalg.norm(random['normal']),1)
    assert np.isclose(np.dot(random['normal'],random['magnitude_normal']),0)
    assert S.causal_cells(chosen,[cell])==cells
    bad=copy.deepcopy(fits);bad.append(dict(fits[0],job_id='decoy'))
    with pytest.raises(ValueError,match='decoy'):S.select_fits(bad,jobs)


def test_changed_partition_decoy_names_fit():
    fit=dict(job_id='decoy',train_cells=['foreign'],evaluation_cells=['test'])
    with pytest.raises(ValueError,match='decoy'):
        S.select_fits([fit],[dict(job_id='decoy',train=['pool'],evaluate=['test'],cohort='x')])


def test_causal_pool_decoy_names_item():
    c=dict(item_id='decoy-pool',split='pool');key=R.cell_key(c)
    f=dict(raw_normal=[1.,0],mean=[0.,0],block=1,evaluation_cells=[key])
    with pytest.raises(ValueError,match='decoy-pool'):S.causal_cells({'x':f},[c])


def test_stratified_fold_mapping_is_input_order_independent():
    items=[dict(dataset=f'd{b}-{i}',difficulty_bin=b) for b in range(5) for i in range(4)]
    assert S.fold_map(items)==S.fold_map(items[::-1])
    assert sorted(list(S.fold_map(items).values()).count(i) for i in range(5))==[4]*5


def test_shared_text_fact_components_prevent_decoy_leakage():
    items=[dict(dataset=f'd{i}',difficulty_bin=i%5,prompt_text=f'text{i}') for i in range(20)]
    items[1]['prompt_text']=items[0]['prompt_text']='decoy-shared-text'
    folds=S.fold_map(items);assert folds['d0']==folds['d1']
    components=S.fact_components(items);assert components['d0']==components['d1']


def test_transfer_requires_matching_forward_selection_decoy():
    with pytest.raises(ValueError,match='decoy-forward'):
        S.transfer_jobs([dict(forward_cohort='decoy-forward')],{})


def test_retired_scope_decoy():
    with pytest.raises(ValueError,match='decoy-N6'):
        S.validate_plan(dict(scope='decoy-N6'))
