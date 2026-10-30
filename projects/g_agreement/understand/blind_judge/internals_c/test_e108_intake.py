import pytest
from .e108_intake import extraction_units


def fixture():
    inventory=[dict(id=f'{i:032x}',kind='native',category='animal',reader='private_metadata') for i in range(1008)]
    indexed={('base',x['id']):dict(record=dict(raw='At the park, a dog runs.',token_ids=[1,2]),member='original.json',index=i) for i,x in enumerate(inventory)}
    return inventory,indexed


def test_full_blind_extraction_does_not_carry_reader_or_truth():
    inventory,indexed=fixture();units=extraction_units(inventory,indexed)
    assert len(units)==1008
    assert all(set(x['data'])=={'id','category','continuation'} and x['data']['continuation']=='At the park, a dog runs.' for x in units)


def test_missing_or_substituted_continuation_is_not_a_complete_bank():
    inventory,indexed=fixture();indexed.pop(('base',inventory[0]['id']))
    with pytest.raises(ValueError):extraction_units(inventory,indexed)
    with pytest.raises(ValueError):extraction_units(inventory[:-1],indexed)


def test_phase_source_receipt_remains_independent_of_later_global_manifest(tmp_path,monkeypatch):
    from . import registered
    from projects.g_agreement.readerbench.io import write,sha
    source=tmp_path/'original.py';source.write_text('original source')
    frozen=tmp_path/'FROZEN.json';write(frozen,dict(files={'original.py':sha(source)}))
    later=tmp_path/'JUDGING_SOURCE_SEAL.json';write(later,dict(files={'new_module.py':'different'}))
    monkeypatch.setattr(registered,'ROOT',tmp_path)
    registered.source_gate(frozen)
    source.write_text('changed source')
    with pytest.raises(ValueError):registered.source_gate(frozen)
