from copy import deepcopy
import pytest
from .e123_intake import make_units
from .e123_channel import check_scope


def fixture():
    original=[];pointers=[];items=[];records=[]
    for i in range(134):
        oid='old'+str(i);sid='source'+str(i);row='fact_recall' if i<84 else 'language_plan'
        original.append(dict(item_id=oid,arm='U',row=row,reader='oracle',condition='steered',flipped=True,target='B',property='Declared value',values={'A':['Old'],'B':['New']}))
        pointers.append(dict(id=sid,base_id=oid,condition='unhooked',split='test',row=row,original_vector_index=i));items.append(dict(id=sid,vector_index=i))
        for b in (44,52):records.append(({},dict(id=sid+':'+str(b),item_id=sid,reader='oracle',condition='unhooked',source_layer=b,source_vector_index=i,text='')))
    return records[::-1],original,pointers,items


def test_full268_native_source_ids_vectors_and_original_candidates():
    u,j=make_units(*fixture(),'rubric');assert len(u)==len(j)==268 and len({x['item_id'] for x in j})==134
    assert all(set(x['data'])=={'id','property','values','readout'} for x in u)
    from .e123_channel import RUBRIC_SHA
    check_scope('E123',u,dict(experiment='E123',issuer='W-internals-C',verified=True,complete_eligible_native_grid=True,labels_cpu_only=True,original_E104_rubric_sha256=RUBRIC_SHA,original_candidates_unchanged=True,native_unhooked_oracle44_52_only=True))


@pytest.mark.parametrize('fault',['partial','wrong_condition','wrong_vector','wrong_cohort'])
def test_reject_partial_or_changed_source(fault):
    r,o,p,i=deepcopy(fixture())
    if fault=='partial':r.pop()
    elif fault=='wrong_condition':r[0][1]['condition']='steered'
    elif fault=='wrong_vector':r[0][1]['source_vector_index']=-1
    else:p[0]['base_id']='foreign'
    with pytest.raises(ValueError):make_units(r,o,p,i,'rubric')


def test_original_row_indices_are_not_compact_public_indices():
    r,o,p,i=fixture()
    for x in p:x['original_vector_index']+=1000
    u,j=make_units(r,o,p,i,'rubric')
    assert all(x['original_row_vector_index']!=x['public_vector_index'] for x in j)
