from projects.g_agreement.understand.q_analysis.followup import bootstrap_group


def records():
    return [dict(item=item,sample='q1',mode='describes',mentions=True,mention_kind='states_property',
                 value='A' if item=='a' else 'B',truth='A',enacts=False,enact_value=None,hallucination=False,extra='')
            for item in ['a','b'] for _ in range(4)]


def test_perfect_within_item_dependence_retains_four_generations():
    r=bootstrap_group(records())
    assert r['n_items']==2 and r['n_records']==8
    assert r['generations_or_outputs_per_item']=={'4':2}
    acc=r['rates']['mentions.accuracy']
    assert (acc['k'],acc['n'])==(4,8)
    assert acc['cluster_ci95']==[0.,1.]
    assert acc['bootstrap_valid']==2000


def test_zero_conditional_denominator_is_reported_not_zero_accuracy():
    rows=records()
    for r in rows:
        if r['item']=='b':r.update(mentions=False,mention_kind=None,value=None)
    acc=bootstrap_group(rows)['rates']['mentions.accuracy']
    assert (acc['k'],acc['n'])==(4,4)
    assert acc['cluster_ci95']==[1.,1.]
    assert 0<acc['bootstrap_undefined']<2000
    assert acc['bootstrap_valid']+acc['bootstrap_undefined']==2000
