from decimal import Decimal
from pathlib import Path

import pytest

from projects.g_agreement.readerbench.io import read
from projects.g_agreement.e95.judge_admission import (
    budget_gate, group_id, universe, unresolved_statement_ids,
)


def test_real_frozen_grid_has_complete_disjoint_blind_ids():
    root = Path(__file__).resolve().parents[3]
    base = root/'results/g_agreement/understand/e95'
    rows = read(base/'ROW_INVENTORY.json')['rows']
    index = read(base/'JUDGE_INDEX.json')
    all_groups = universe(rows)
    assert len(all_groups) == 20400
    chosen = {group_id(k, x) for k, xs in index['selected'].items() for x in xs}
    original = {group_id(k, x) for k, xs in index['old_rubric_selected'].items() for x in xs}
    assert len(chosen) == 6120 and len(original) == 1530
    assert original <= chosen <= set(all_groups)
    same_unit = rows[0]['item_ids'][0]+':42'
    assert group_id('0:real:nla', same_unit) != group_id('0:placebo:nla', same_unit)


def test_budget_counts_reservations_and_rejects_wrong_envelopes():
    receipt = dict(issuer='integrator', verified=True, reservation_included=True,
                   E95_allocation_usd=60, global_judging_committed_including_reservation_usd=1000)
    budget_gate(receipt, Decimal('59.9'))
    for change, bound in [({'reservation_included':False}, 1),
                          ({'global_judging_committed_including_reservation_usd':1001}, 1),
                          ({'E95_allocation_usd':61}, 1), ({}, 60.01),
                          ({'E95_allocation_usd':'NaN'}, 1)]:
        with pytest.raises(ValueError):
            budget_gate(dict(receipt, **change), bound)


def test_unscorable_rows_stay_accounted_without_value_judge_calls():
    expected = {'count': ('0:real:nla', 'unit:42'), 'value': ('1:real:nla', 'other:42')}
    eligibility = dict(rows=[dict(row_index=0, statement_score_registered=False),
                             dict(row_index=1, statement_score_registered=True)])
    records = [dict(id='count', status='NOT_EVALUABLE_NO_STATEMENT_SCORE'),
               dict(id='value', status='NO_REGEX')]
    assert unresolved_statement_ids(records, expected, eligibility) == {'value'}
    records[0]['status'] = 'NO_REGEX'
    with pytest.raises(ValueError, match='unscorable'):
        unresolved_statement_ids(records, expected, eligibility)
