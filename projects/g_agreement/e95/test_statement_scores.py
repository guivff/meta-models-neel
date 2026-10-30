import pytest

from projects.g_agreement.e95.statement_scores import annotate_map, hm1_score_rows


def test_no_score_stays_listed_without_a_max_or_hypothesis_vote():
    rows = [dict(bank='E57', row='category_switch', S_max=.99),
            dict(bank='E59', row='format_plan', S_max=.4),
            dict(bank='future', row='another_count', S_max=.8)]
    eligibility = dict(rows=[dict(bank=x['bank'], row=x['row'],
                                 statement_score_registered=x['row']=='format_plan') for x in rows])
    output = annotate_map(rows, eligibility)
    assert len(output) == 3
    assert output[0]['S_max'] is None and output[2]['S_max'] is None
    assert output[0]['map_status'] == 'NOT EVALUABLE (no statement score)'
    assert [x['row'] for x in hm1_score_rows(output)] == ['format_plan']
    assert output[1]['S_max'] == .4


def test_unknown_row_does_not_silently_gain_a_statement_score():
    with pytest.raises(ValueError, match='explicit'):
        annotate_map([dict(bank='E57', row='unknown')], dict(rows=[]))
