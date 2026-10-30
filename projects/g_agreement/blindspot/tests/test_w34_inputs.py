"""The registered rule-(i) population does not depend on W1's overall verdict."""
from copy import deepcopy
import pytest
from projects.g_agreement.blindspot import w34_inputs as W


def fixture():
    rule={'features':list(W.BLINDSPOT_ROWS),'w1_verdict':'NOT MET'}
    metrics={'w1':{'blindspot_features':list(W.BLINDSPOT_ROWS),'status':'NOT MET'},'rows':[
        {'feature':f,'reader':'olens','layer':44,'status':'EVALUABLE','class':'state-like'} for f in W.BLINDSPOT_ROWS]}
    metrics['rows'] += [{'feature':'semantic_keep','reader':'olens','layer':44,'status':'EVALUABLE','class':'semantic'},
        {'feature':'semantic_exclude','reader':'olens','layer':44,'status':'NOT DECODABLE','class':'semantic'}]
    return rule,metrics


def test_not_met_keeps_all_sixteen_and_evaluable_semantic_controls():
    rule,metrics=fixture(); original=deepcopy(metrics)
    blind,semantic,excluded=W.population(rule,metrics)
    assert blind==sorted(W.BLINDSPOT_ROWS) and len(blind)==16
    assert semantic==['semantic_keep'] and excluded==[{'feature':'semantic_exclude','reason':'NOT DECODABLE'}]
    assert metrics==original


@pytest.mark.parametrize('bad',['missing','duplicate','different','verdict'])
def test_population_refuses_silent_selection_changes(bad):
    rule,metrics=fixture()
    if bad=='missing': rule['features'].pop()
    elif bad=='duplicate': rule['features'][-1]=rule['features'][0]
    elif bad=='different': metrics['w1']['blindspot_features']=['table_column','prose_paren']
    else: metrics['w1']['status']='CONFIRMED'
    with pytest.raises(ValueError): W.population(rule,metrics)


def test_compact_keeps_every_test_item_and_frozen_random_donor_identity():
    items=[{'id':str(i),'feature':'selected' if i<4 else 'other'} for i in range(8)]
    labels={str(i):{'split':'test' if i%2==0 else 'dev'} for i in range(8)}
    pairs=[{'id':'pair','recipient':0,'donor':2,'random':7}]
    order,mapped,test=W.compact_indices(items,labels,[{'feature':'selected'}],pairs)
    assert test=={0,2} and order==[0,2,7]
    assert mapped==[{'id':'pair','recipient':0,'donor':1,'random':2}]
    assert items[order[mapped[0]['random']]]['id']=='7'
    assert pairs[0]['random']==7
