from .e100e_inventory_ruling import copy_inventory,MISSING


def test_literal_values_copied_and_donor_not_recomputed():
    labels=[dict(id='a',row='row',split='test',donor_id='b',source_value='one',donor_value='two')]
    rows,top,missing=copy_inventory(labels,dict(seed=20261029,read_blocks=dict(oracle=44,nla=42),condition='transplant'),'originalcommit',dict(labels=True,manifest=True,pairing_commit=True))
    assert rows==[dict(id='a',row='row',split='test',donor_id='b',original_value='one',target_value='two')]
    assert top['pairing_seed']==20261029 and top['reader_blocks']==dict(oracle=44,nla=42)
    assert missing==['intervention','pre_gpu_pairing_committed'] and top['intervention']==MISSING


def test_post_output_or_unsourced_fields_stay_missing():
    rows,top,missing=copy_inventory([],dict(seed=20261029,intervention='invented',pre_gpu_pairing_committed=True),
        'latecommit',dict(labels=False,manifest=False,pairing_commit=False))
    assert rows==MISSING and top['pairing_seed']==top['intervention']==top['pairing_commit']==MISSING
    assert'INVENTORY.json'in missing


def test_absent_target_not_derived_from_other_items():
    rows,top,missing=copy_inventory([dict(id='a',row='r',split='test',donor_id='b',source_value='one'),
        dict(id='b',row='r',split='test',donor_id='a',source_value='two',donor_value='one')],{},'commit',dict(labels=True,manifest=True,pairing_commit=True))
    assert rows[0]['target_value']==MISSING and 'INVENTORY.json[0].target_value'in missing
