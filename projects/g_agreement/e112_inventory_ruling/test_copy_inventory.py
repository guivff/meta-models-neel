import pytest
from .copy_inventory import copy_fields

def test_exact_copy_preserves_order_false_and_missing():
    source={'s':dict(data={'ids':['b','a'],'flag':False},pre_output_verified=True,custody={'hash':'fixture'})}
    r=copy_fields(source,{'item_ids':('s',['ids']),'flag':('s',['flag']),'absent':('s',['unknown']),'unsupported':None})
    assert r['values']==dict(item_ids=['b','a'],flag=False,absent='MISSING',unsupported='MISSING')
    assert r['provenance']['item_ids']['keys']==['ids']
    r['values']['item_ids'].append('c');assert source['s']['data']['ids']==['b','a']

def test_post_output_source_rejected():
    with pytest.raises(ValueError):copy_fields({'s':dict(data={'x':1},pre_output_verified=False,custody={})},{'x':('s',['x'])})

def test_registered_statistic_has_no_diagnostic_argument():
    import inspect
    from projects.g_agreement.e112_analysis.adapter import analyze,paired
    assert list(inspect.signature(analyze).parameters)==['rows']
    assert list(inspect.signature(paired).parameters)==['rows']
    assert paired([{'J':False,'PCA_k':True}]*184)['R_X5']=='MET'
