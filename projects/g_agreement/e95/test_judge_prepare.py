from projects.g_agreement.e95.judge_prepare import regex_group,make_audit
from projects.g_agreement.e95.judge_admission import universe,unresolved_statement_ids


def group(texts):
    return dict(id='a'*32,property='synthetic',values=dict(A='one',B='two'),
                positions=[dict(offset=i+1-len(texts),readout=t)for i,t in enumerate(texts)])


CAT=dict(bank='SYNTHETIC',row='synthetic',status='AVAILABLE',families=[dict(
    patterns=[r'\bone\b',r'\btwo\b'],ignore_case=True,policy='whole_word_or_frozen_regex')])


def test_exact_existing_matcher_preserves_negation_misses_and_all_positions():
    assert regex_group(group(['one','not two']),CAT)is None
    assert regex_group(group(['one','unrelated']),CAT)is None
    assert regex_group(group(['','']),CAT)is None
    code=regex_group(group(['one','two']),CAT)
    assert code['values']==['A','B']and code['first_position']==-1 and code['evidence']=='one'


def test_audit_covers_whole_frozen_universe_without_inventing_missing_outputs():
    rows=[dict(row_index=0,bank='synthetic',row='synthetic',item_ids=['u'],oracle_layers=[44],reuse_e87=False)]
    eligibility=dict(rows=[dict(row_index=0,statement_score_registered=True)])
    expected=universe(rows);gid=next(k for k,v in expected.items()if v==('0:real:oracle','u:44'))
    g=group(['one']);g['id']=gid
    records,resolved=make_audit(rows,eligibility,[g],dict(rows=[CAT]),'f'*64)
    unresolved=unresolved_statement_ids(records,expected,eligibility)
    assert len(records)==len(expected)and len(resolved)==1 and gid not in unresolved
    assert all(r['status']=='UNRESOLVED'for r in records if r['id']!=gid)
    assert all(r.get('code')is None for r in records)
