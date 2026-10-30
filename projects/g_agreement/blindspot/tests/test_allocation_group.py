from copy import deepcopy

import pytest

from projects.g_agreement.blindspot import protocol as P


def parallel():
    allocations = [
        {'pod_id':'first','allocated_gpu_seconds':3600,'provider_created_epoch':100,
         'deadline_epoch':3700,'execution_units':['priority','remainder_a']},
        {'pod_id':'second','allocated_gpu_seconds':3600,'provider_created_epoch':120,
         'deadline_epoch':3720,'execution_units':['remainder_b']},
    ]
    return {**allocations[0], 'previous_gpu_seconds':0,
            'allocation_group':{'mode':'parallel','previous_gpu_seconds':0,'allocations':allocations}}


def test_parallel_reserves_one_shared_two_hour_cap():
    a=parallel();P._admit_allocation_group(a,{},'priority')
    second={**a,**a['allocation_group']['allocations'][1]}
    P._admit_allocation_group(second,{},'remainder_b')
    with pytest.raises(ValueError,match='not assigned'):
        P._admit_allocation_group(second,{},'priority')


def test_two_independent_two_hour_reservations_are_rejected():
    a=parallel()
    for row in a['allocation_group']['allocations']:
        row['allocated_gpu_seconds']=7200;row['deadline_epoch']=row['provider_created_epoch']+7200
    a.update(a['allocation_group']['allocations'][0])
    with pytest.raises(ValueError,match='aggregate'):
        P._admit_allocation_group(a,{},'priority')


def test_previous_custody_counts_once_towards_aggregate():
    a=parallel();a['previous_gpu_seconds']=1;a['allocation_group']['previous_gpu_seconds']=1
    with pytest.raises(ValueError,match='aggregate'):
        P._admit_allocation_group(a,{},'priority')


@pytest.mark.parametrize('change', ['duplicate_pod','overlap','missing_group','different_own_budget','bad_deadline','duplicate_unit'])
def test_invalid_allocation_group_refused(change):
    a=deepcopy(parallel());g=a['allocation_group'];rows=g['allocations']
    if change=='duplicate_pod':rows[1]['pod_id']='first'
    elif change=='overlap':rows[1]['execution_units']=['priority','remainder_b']
    elif change=='missing_group':a.pop('allocation_group')
    elif change=='different_own_budget':a['allocated_gpu_seconds']=3599
    elif change=='bad_deadline':rows[1]['deadline_epoch']=3721
    else:rows[0]['execution_units'].append('priority')
    with pytest.raises(ValueError):P._admit_allocation_group(a,{},'priority')


def test_serial_fallback_assigns_all_units_once():
    a=parallel();a['allocated_gpu_seconds']=7200;a['deadline_epoch']=7300
    a['execution_units']=['priority','remainder_a','remainder_b']
    own={key:a[key] for key in ('pod_id','allocated_gpu_seconds','provider_created_epoch','deadline_epoch','execution_units')}
    a['allocation_group']={'mode':'serial','previous_gpu_seconds':0,'allocations':[own]}
    for unit in a['execution_units']:P._admit_allocation_group(a,{},unit)
