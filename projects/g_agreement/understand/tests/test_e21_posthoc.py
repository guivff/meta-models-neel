from projects.g_agreement.understand.e21_posthoc import candidate_counts


def test_fixed_candidate_preference_is_not_truth_success():
    r=candidate_counts([-2,-1,3,4],[True,True,False,False])
    assert r['dominant_candidate']=='B' and r['same_candidate_share']==1
    assert r['dominant_wins_by_truth']=={'A':{'wins':2,'n':2},'B':{'wins':2,'n':2}}
    assert r['exact_ties']==0


def test_item_sensitive_true_candidate_has_no_fixed_preference():
    r=candidate_counts([2,1,3,4],[True,True,False,False])
    assert r['same_candidate_share']==.5 and r['dominant_candidate']=='no unique dominant candidate'
    assert r['dominant_wins_by_truth']['A']['wins'] is None


def test_exact_ties_are_not_epsilon_ties_or_half_wins():
    r=candidate_counts([0,1e-30,-1e-30,0],[True,True,False,False])
    assert r['exact_ties']==2 and r['exact_tie_share']==.5
    assert r['A_wins']==2 and r['B_wins']==0 and r['same_candidate_share']==.5
