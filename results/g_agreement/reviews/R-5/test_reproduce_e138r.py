import copy
import pytest
import reproduce_e138r as m


def fixture():
    final=dict(experiment='E138R',status='COMPLETE_ONCE',authority=m.AUTHORITY,defective_analysis_sha256=m.DEFECTIVE)
    flags=('whole_values_verified','same168_native_readouts_verified','R5_actual_sample_pass','post_output_correction_disclosed',
           'original84_verified','donor_pairing_E100_verified','random_E76_verified','clean_E127_no_prefix_verified',
           'literal_value_code_mapping_verified','route_verified','privacy_verified','terminal_dispositions_verified')
    packet=dict(experiment='E138R',status='COMPLETE',correction_authority=m.AUTHORITY,defective_analysis_sha256=m.DEFECTIVE,
                corrected_input_sha256=m.INPUT,unknown_cost_requests=0,booked_usd=.1,cap_usd=1,**dict.fromkeys(flags,True))
    terminal=dict(experiment='E138R',status='COMPLETE',input_seal_sha256=m.INPUT)
    return final,packet,terminal


def test_corrected_contract():m.correction_contract(*fixture())


@pytest.mark.parametrize('where,field,value',[(0,'experiment','E138'),(0,'authority','old'),(1,'post_output_correction_disclosed',False),
 (1,'R5_actual_sample_pass',False),(1,'corrected_input_sha256','old'),(1,'unknown_cost_requests',1),(1,'booked_usd',1.1),
 (2,'experiment','E138'),(2,'input_seal_sha256','old')])
def test_reject_defective_or_unbound_correction(where,field,value):
    data=fixture();data[where][field]=value
    with pytest.raises(ValueError):m.correction_contract(*data)


def test_no_old_new_arm_pointer_mixing():
    fields={k:{'ref':dict(seal_index=2)}for k in ('code','status','judgment_id')}
    rows=[dict(arms={a:dict(e104_role_code=copy.deepcopy(fields))for a in ('donor','random')})for _ in range(84)]
    m.check_new_pointers(rows,2)
    rows[40]['arms']['random']['e104_role_code']['status']['ref']['seal_index']=0
    with pytest.raises(ValueError):m.check_new_pointers(rows,2)
    with pytest.raises(ValueError):m.check_new_pointers(rows[:83],2)
