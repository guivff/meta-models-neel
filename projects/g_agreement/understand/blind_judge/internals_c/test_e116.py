import copy
import pytest
from .e116_intake import make_units,verify_choice_envelope
from .e116_channel import original108_call,check_scope
from .banks import choice108
from .e116_close import pointers
from .seal_bank import disposition


def fixture():
    cohort=[dict(id=str(i),arm='immediate' if i<329 else 'delayed',choice='test',ground_truth_ref={}) for i in range(376)]
    records=[({},dict(id=f'{c["id"]}:{b}',item_id=c['id'],source_layer=b,reader='oracle',text='readout')) for c in cohort for b in (52,60)]
    return records,cohort,[dict(id=c['id']) for c in cohort]


def test_explicit_item_block_joins_not_file_order():
    r,c,i=fixture();u,j=make_units(list(reversed(r)),c,i)
    assert len(u)==752 and len(j)==752
    check_scope('E116',u,dict(experiment='E116',verified=True,complete_eligible_native_grid=True,labels_cpu_only=True,native_oracle52_60_only=True,original_E108_choices_unchanged=True))
    assert {(x['item_id'],x['block']) for x in j}=={(x['id'],b) for x in c for b in (52,60)}


@pytest.mark.parametrize('change',['missing','duplicate','foreign','wrong_reader'])
def test_partial_and_substituted_sources_rejected(change):
    r,c,i=fixture();r=copy.deepcopy(r)
    if change=='missing':r.pop()
    elif change=='duplicate':r[-1]=r[0]
    elif change=='foreign':r[0][1]['item_id']='foreign'
    else:r[0][1]['reader']='nla'
    with pytest.raises(ValueError):make_units(r,c,i)


def test_exact_original_e108_wire_and_boolean_not_record_normalization():
    u=dict(id='0'*24,kind='choice_hit',rubric=None,data=dict(id='0'*24,chosen_member='test',readout='test'))
    call,validate=original108_call(u,None);expected,_=choice108([u['data']],'judging');assert call==expected
    validate(dict(records=[dict(id=u['id'],hit=True,evidence='test')]))
    with pytest.raises(ValueError):validate(dict(records=[dict(id=u['id'],hit=True,evidence='invented')]))


def test_missing_stays_null_and_incomplete_bank_or_charge_cannot_close():
    rows=[dict(id='x',kind='choice_hit',status='UNPARSEABLE',code=None)]
    assert pointers(rows,'seal','sha',n=1)[0]['original_code']['keys']==[0,'code']
    with pytest.raises(ValueError):pointers(rows,'seal','sha')
    with pytest.raises(ValueError):disposition(2,.1,.1)
    with pytest.raises(ValueError):disposition(2,2.01,0)


def test_source_choice_pointer_is_original_one_status_envelope():
    verify_choice_envelope(dict(status='ONE',canonical_member='test'),'test')
    with pytest.raises(ValueError):verify_choice_envelope(dict(status='NONE',canonical_member='test'),'test')
    with pytest.raises(ValueError):verify_choice_envelope(dict(status='ONE',canonical_member='other'),'test')
    with pytest.raises(ValueError):verify_choice_envelope('test','test')
