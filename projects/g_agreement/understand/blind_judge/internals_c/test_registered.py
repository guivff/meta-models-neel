from types import SimpleNamespace
import pytest
from . import registered as r
from . import e107_plan as e
from . import e107_units as u
from ..rubric202 import amended,BASE,original_ids

P=SimpleNamespace(MODEL='google/gemini-3.1-flash-lite',PROVIDER='google-vertex/global',PROVIDER_NAME='Google')


def test_e107_frozen_outside_order_and_missing_truth():
    source=dict(source_belief=['dog'],source_belief_aliases=['dog','hound'],source_truth=['cat'],source_truth_aliases=['cat'])
    assert e.outside_values(source,{'belief':'B','truth':'A'})==dict(B=['dog','hound'],A=['cat'])
    source['source_truth']=None;source['source_truth_aliases']=[]
    assert e.outside_values(source,{'belief':'A'})==dict(A=['dog','hound'],B=[])
    with pytest.raises(ValueError):e.outside_values(source,{'belief':'B','truth':'A'})


def test_value_validator_preserves_original_code_and_rubric():
    data=dict(id='a'*32,property='container',values=dict(A='box',B='drawer'),readout='It is in a box.')
    unit=dict(id=data['id'],kind='value',data=data,rubric=amended().decode())
    call,validator=r.unit_call(unit,P)
    code=dict(id=data['id'],category='states_value',values=['A'],evidence='in a box')
    validator(dict(records=[code]))
    result=r.normalized_code('value',dict(status='KEPT',result=dict(records=[code])))
    assert result==code
    with pytest.raises(ValueError):validator(dict(records=[dict(code,evidence='in a drawer')]))
    unit['rubric']='changed scientific rubric'
    with pytest.raises(ValueError):r.unit_call(unit,P)


@pytest.mark.parametrize('kind',['value','old_value','s6','eval85','choice_extract','choice_hit','placebo106'])
def test_every_terminal_missing_is_null_without_recode(kind):
    assert r.normalized_code(kind,dict(status='UNPARSEABLE',result=None)) is None
    assert r.normalized_code(kind,dict(status='REFUSED',result=None)) is None


def test_e108_status_and_hit_normalization_is_explicit():
    for status in ('NONE','MULTIPLE'):
        code=r.normalized_code('choice_extract',dict(status='KEPT',result=dict(records=[dict(id='opaque',status=status,canonical_member='',evidence='')])))
        assert code==dict(status=status,canonical_member=None)
    assert r.normalized_code('choice_hit',dict(status='KEPT',result=dict(records=[dict(id='opaque',hit=False,evidence='')]))) is False


def test_placebo_normalizer_does_not_create_a_target_or_signed_score():
    result=r.normalized_code('placebo106',dict(status='KEPT',result=dict(records=[dict(id='opaque',states_any_trained_value=True,evidence='depth two')])))
    assert result==dict(states_any_trained_value=True,evidence='depth two')


def test_full_e85_scope_old_subset_and_duplicate_members():
    ids=[f'{i:032x}' for i in range(800)]
    selected=original_ids(ids,'E85')
    units=[dict(id=i,kind='eval85') for i in ids]+[dict(id=i,kind='s6') for i in selected]
    receipt=dict(issuer='I-2',experiment='E85',verified=True,complete_eligible_native_grid=True,labels_cpu_only=True)
    r.check_scope('E85',units,receipt)
    with pytest.raises(ValueError):r.check_scope('E85',units[:-1],receipt)
    with pytest.raises(ValueError):r.check_scope('E85',units+[units[0]],receipt)


def test_full_e109_grid_and_seeded_comparison_not_cohort_selection():
    ids=[f'{i:032x}' for i in range(1008)]
    selected=original_ids(ids,'E109')
    units=[dict(id=i,kind='value') for i in ids]+[dict(id=i,kind='old_value') for i in selected]
    receipt=dict(issuer='Track Q',experiment='E109',verified=True,complete_eligible_native_grid=True,labels_cpu_only=True)
    r.check_scope('E109',units,receipt)
    with pytest.raises(ValueError):r.check_scope('E109',units[:134],receipt)


def test_e108_extraction_cannot_depend_on_reader_outputs():
    units=[dict(id=f'{i:032x}',kind='choice_extract') for i in range(1008)]
    receipt=dict(issuer='I-3',experiment='E108',verified=True,complete_eligible_native_grid=True,labels_cpu_only=True,ground_truth_blind=True)
    r.check_scope('E108',units,receipt)
    receipt['ground_truth_blind']=False
    with pytest.raises(ValueError):r.check_scope('E108',units,receipt)


def test_e107_new_output_rendering_preserves_length_and_separates_targets():
    plans=[dict(inventory_id='source',bank='E82',target=t,property='container',values=dict(A=['box'],B=['drawer'])) for t in ('belief','truth')]
    generated=[dict(id='source',phase='generation',status='GENERATED',finish_reason='length',truncated=True,text='whole truncated text',refusal=None)]
    units=u.build_units(plans,generated)
    main=[x for x in units if x['kind']=='value']
    assert len(main)==2 and main[0]['id']!=main[1]['id']
    assert all(x['data']['readout']=='whole truncated text' for x in main)
    assert sorted(x['id'] for x in units if x['kind']=='old_value')==original_ids([x['id'] for x in main],'E107')
    generated[0]['refusal']='refusal'
    with pytest.raises(ValueError):u.build_units(plans,generated)


def test_missing_truth_cannot_create_a_b_verdict():
    data=dict(id='a'*32,property='container',values=dict(A=['box'],B=[]),readout='It is in a box.')
    _,validator=r.unit_call(dict(id=data['id'],kind='value',data=data,rubric=amended().decode()),P)
    with pytest.raises(ValueError):validator(dict(records=[dict(id=data['id'],category='states_value',values=['B'],evidence='box')]))


def test_physical_ledger_mirror_dedup_and_distinct_attempts(tmp_path):
    from .accounting import physical_rows
    from decimal import Decimal
    import json
    rows=[dict(event='reserve',id='same',usd='1',at=1),dict(event='settle',id='same',usd='.2',at=2)]
    first=tmp_path/'one';mirror=tmp_path/'mirror';other=tmp_path/'other'
    for path in (first,mirror):path.write_text('\n'.join(json.dumps(x) for x in rows)+'\n')
    other.write_text(json.dumps(dict(event='reserve',id='same',usd='1',at=3))+'\n')
    actual,unknown,_=physical_rows([first,mirror,other])
    assert actual==Decimal('.2') and unknown==Decimal('1')


def test_unknown_settlement_and_missing_registered_ledger_stop(tmp_path):
    from .accounting import physical_rows
    import json
    path=tmp_path/'ledger';path.write_text(json.dumps(dict(event='settle',id='unknown',usd='.2',at=2))+'\n')
    with pytest.raises(ValueError):physical_rows([path])
    with pytest.raises(ValueError):physical_rows([tmp_path/'missing'])
