"""CPU tests for additive units, label isolation, and immutable bank binding."""
from collections import Counter
import copy
import json
from pathlib import Path

import pytest

from projects.g_agreement.blindspot import execution as E
from projects.g_agreement.blindspot import items as I
from projects.g_agreement.blindspot import protocol as P


@pytest.fixture
def frozen(tok, tmp_path):
    bank = tmp_path/'bank'
    items = I.build_items(tok, 2, 1) + I.build_ordinal_items(tok, 2, 1)
    P.write_bank(bank, items, I.assert_lengths(items), 'toy-test-only')
    path, training = tmp_path/'execution'/'EXECUTION_PLAN.json', tmp_path/'analysis-only'
    before = {p.name: P.sha(p) for p in bank.iterdir() if p.is_file()}
    plan = E.build_plan(bank, path, training, runtime_source_files={'runtime.py':'a'*64})
    assert before == {p.name: P.sha(p) for p in bank.iterdir() if p.is_file()}
    return bank, path, training, plan


def test_units_cover_all_items_once_in_both_modes_with_closed_donors(frozen):
    bank, path, _, plan = frozen
    full = P.rows(bank/'items.input.jsonl')
    all_ids = {r['id'] for r in full}
    assert plan['feature_order'][:5] == list(E.PRIORITY_FEATURES)
    assert plan['units']['priority']['features'] == list(E.PRIORITY_FEATURES)
    for mode in ('one_pod','two_pods'):
        selected_ids=[]
        for assigned_units in plan['modes'][mode].values():
            for unit in assigned_units:
                selection = E.select_unit(path,unit,bank,full)
                selected = selection['items']
                assert selected == [full[i] for i in selection['indices']]
                if unit == 'priority':
                    assert list(dict.fromkeys(r['feature'] for r in selected)) == list(E.PRIORITY_FEATURES)
                    for feature in E.PRIORITY_FEATURES:
                        positions=[i for i in selection['indices'] if full[i]['feature']==feature]
                        assert positions==sorted(positions)
                else:
                    assert selection['indices'] == sorted(selection['indices'])
                assert selection['binding'] == {'execution_plan_sha256':P.sha(path),'execution_unit':unit}
                subset_ids = {r['id'] for r in selected}
                assert all(r['donor_id'] is None or r['donor_id'] in subset_ids for r in selected)
                selected_ids.extend(r['id'] for r in selected)
        assert set(selected_ids) == all_ids and len(selected_ids) == len(all_ids)
    items,donors,templates = E.select_inputs(bank,path,'priority')
    assert set(templates) == set(E.PRIORITY_FEATURES)
    for i,j in enumerate(donors):
        assert items[j]['id'] == items[i]['donor_id'] and donors[j] == i
    assert plan['free_batch_policy'] == 'canonical_batch_intersections'


def test_worker_validation_and_selection_never_read_labels(frozen,monkeypatch):
    bank,path,training,plan=frozen
    original=Path.open
    def forbid_labels(self,*args,**kwargs):
        if 'DO_NOT_STAGE' in self.name or self.name==E.TRAINING_SEAL:
            raise AssertionError('worker attempted a label read')
        return original(self,*args,**kwargs)
    monkeypatch.setattr(Path,'open',forbid_labels)
    assert E.validate_plan(bank,path)==plan
    full=P.rows(bank/'items.input.jsonl')
    assert E.select_unit(path,'priority',bank,full)['items']
    assert E.select_inputs(bank,path,'remainder_b')[0]


def test_training_file_is_local_dev_only_with_source_and_order_proof(frozen):
    bank,path,training,plan=frozen
    rows=P.rows(training/E.TRAINING_FILE)
    seal=json.loads((training/E.TRAINING_SEAL).read_text())
    assert all(r['split']=='dev' and r['feature'] in E.PRIORITY_FEATURES for r in rows)
    assert len(rows)==10  # Tiny fixture; production counts are tested separately.
    assert seal['source_labels_sha256']==P.sha(bank/'labels.DO_NOT_STAGE.jsonl')
    assert seal['training_labels_sha256']==P.sha(training/E.TRAINING_FILE)==plan['training_labels']['sha256']
    assert seal['input_seal_sha256']==P.sha(bank/'INPUT_SEAL.json')
    assert seal['manifest_sha256']==P.sha(bank/'manifest.json')
    assert seal['ordered_train_ids']==[r['id'] for r in rows]
    assert seal['features']==list(E.PRIORITY_FEATURES)
    # Plan has all priority IDs but no ID-to-dev/test map or training ID subset.
    assert set(plan['training_labels'])=={'sha256','relative_path','count'}
    assert 'ordered_train_ids' not in path.read_text()
    assert 'split_counts' not in path.read_text()
    assert not (bank/E.TRAINING_FILE).exists()


@pytest.mark.parametrize('mutation', ['lost_item','duplicate_item','moved_feature','dev_ids','bad_mode','bad_bank','bad_source'])
def test_tampered_plan_is_rejected(frozen,mutation):
    bank,path,_,original=frozen
    plan=copy.deepcopy(original)
    if mutation=='lost_item': plan['units']['priority']['item_ids'].pop()
    elif mutation=='duplicate_item': plan['units']['remainder_a']['item_ids'].append(plan['units']['priority']['item_ids'][0])
    elif mutation=='moved_feature': plan['units']['priority']['features'].reverse()
    elif mutation=='dev_ids': plan['training_labels']['ordered_train_ids']=['hidden-test-id']
    elif mutation=='bad_mode': plan['modes']['two_pods']['pod_b'].append('priority')
    elif mutation=='bad_bank': plan['input_seal_sha256']='b'*64
    else: plan['baseline_source_files']['forged.py']='f'*64
    P.dump(path,plan)
    with pytest.raises(ValueError):E.validate_plan(bank,path)


def test_input_reordering_or_mutation_cannot_change_selection(frozen):
    bank,path,_,_=frozen
    full=P.rows(bank/'items.input.jsonl')
    with pytest.raises(ValueError,match='canonical'):
        E.select_unit(path,'priority',bank,list(reversed(full)))
    altered=copy.deepcopy(full);altered[0]['ids'].append(42)
    with pytest.raises(ValueError,match='canonical'):
        E.select_unit(path,'priority',bank,altered)
    with pytest.raises(ValueError,match='unknown'):
        E.select_unit(path,'random_subset',bank,full)


def test_assignment_names_exact_plan_and_permitted_unit(frozen):
    bank,path,_,plan=frozen
    assignment={'execution_plan_sha256':P.sha(path),'execution_units':['priority','remainder_a']}
    assert E.validate_assignment(assignment,path,'priority',bank)==plan
    with pytest.raises(ValueError,match='authorize'):
        E.validate_assignment(assignment,path,'remainder_b',bank)
    assignment['execution_plan_sha256']='a'*64
    with pytest.raises(ValueError,match='authorize'):
        E.validate_assignment(assignment,path,'priority',bank)


def test_existing_plan_and_frozen_bank_are_never_overwritten(frozen,tmp_path):
    bank,path,training,_=frozen
    before=P.sha(path)
    with pytest.raises(FileExistsError):E.build_plan(bank,path,training)
    assert P.sha(path)==before
    with pytest.raises(ValueError,match='outside'):
        E.build_plan(bank,bank/'new_plan.json',tmp_path/'newlabels')
    with pytest.raises(ValueError,match='outside'):
        E.build_plan(bank,tmp_path/'new_plan.json',bank/'newlabels')


def test_bad_source_labels_cannot_create_training_file(tok,tmp_path):
    bank=tmp_path/'bank'
    items=I.build_items(tok,2,1)
    P.write_bank(bank,items,I.assert_lengths(items),'toy-test-only')
    with (bank/'labels.DO_NOT_STAGE.jsonl').open('a') as stream:stream.write('\n')
    with pytest.raises(ValueError,match='source labels hash'):
        E.build_plan(bank,tmp_path/'plan.json',tmp_path/'training')
    assert not (tmp_path/'training'/E.TRAINING_FILE).exists()


def test_registered_counts_and_balanced_remainders_include_ordinal(tok,tmp_path):
    bank=tmp_path/'fullbank'
    items=I.build_items(tok)+I.build_ordinal_items(tok)
    P.write_bank(bank,items,I.assert_lengths(items),'toy-test-only')
    plan=E.build_plan(bank,tmp_path/'EXECUTION_PLAN.json',tmp_path/'training')
    assert {u:p['count'] for u,p in plan['units'].items()} == {'priority':840,'remainder_a':2808,'remainder_b':3648}
    assert plan['training_labels']['count']==420
    training=P.rows(tmp_path/'training'/E.TRAINING_FILE)
    assert Counter(r['feature'] for r in training)==dict.fromkeys(E.PRIORITY_FEATURES,84)
    for feature in E.PRIORITY_FEATURES:
        assert sorted(Counter(r['value'] for r in training if r['feature']==feature).values())==[42,42]
    assert 'table_column_ordinal' in plan['units']['remainder_a']['features']
    assert 'python_depth_ordinal' in plan['units']['remainder_b']['features']
    assert plan['units']['priority']['count']+plan['units']['remainder_a']['count']==plan['units']['remainder_b']['count']==3648
