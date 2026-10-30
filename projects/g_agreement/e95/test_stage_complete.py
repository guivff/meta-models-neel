from copy import deepcopy
from pathlib import Path
import pytest
from projects.g_agreement.readerbench.io import read
from projects.g_agreement.e95.stage_complete import stage_rows,eligible_ids,INVENTORY_SHA
from projects.g_agreement.e95.judge_admission import universe,group_id
from projects.g_agreement.understand.blind_judge.validator221 import e87_classify

ROOT=Path(__file__).resolve().parents[3]


def inventory():return read(ROOT/'results/g_agreement/understand/e95/oracle_only_inventory/INVENTORY_20261029T1448Z.json')


def test_final_coverage_and_both_arms_without_resampling():
    inv=inventory();allowed=stage_rows(inv)
    assert len(allowed['oracle'])==62 and len(allowed['nla'])==44
    rows=read(ROOT/'results/g_agreement/understand/e95/deviation2/ROW_INVENTORY.json')['rows']
    expected=universe(rows);chosen=eligible_ids(expected,allowed)
    for gid,(stratum,key)in expected.items():
        row,arm,reader=stratum.split(':')
        assert (gid in chosen)==(int(row)in allowed[reader])
    # An operational NO_FIT after Oracle completion may admit Oracle, not partial NLA.
    row=inv['shards'][1]['row_indices'][0]
    assert row in allowed['oracle']and row not in allowed['nla']
    assert not set(inv['shards'][0]['row_indices']) & (allowed['oracle']|allowed['nla'])


def test_partial_placebo_and_nonclosed_inventory_rejected():
    inv=inventory();inv['shards'][1]['stages']['oracle_placebo']['status']='partial'
    with pytest.raises(ValueError,match='both arms'):stage_rows(inv)
    inv=inventory();inv['pending']=1
    with pytest.raises(ValueError,match='closed'):stage_rows(inv)


def test_silent_correction_only_and_non_silent_evidence_remains_strict():
    item=dict(id='a'*32,positions=[dict(offset=0,readout='Example.')])
    code=dict(id=item['id'],category='silent',values=[],evidence='',first_position=999)
    assert e87_classify([item],dict(records=[code]))[0]['status']=='KEPT'
    assert code['first_position']==999 # original raw reply retained
    assert e87_classify([item],dict(records=[dict(code,evidence='Example')]))[0]['status']=='INVALID'
    assert e87_classify([item],dict(records=[dict(code,category='states_value',values=['A'],evidence='absent',first_position=0)]))[0]['status']=='INVALID'
