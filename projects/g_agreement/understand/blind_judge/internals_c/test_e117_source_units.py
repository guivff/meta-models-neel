from copy import deepcopy
import pytest
from .e117_source_units import ROWS,descriptor_rows,make_units


def fixture():
    labels=[];packets={'E56':[],'E57':[]};keys={'E56':[],'E57':[]}
    for row in sorted(ROWS):
        bank='E56' if row=='fact_recall' else 'E57'
        for i in range(84):
            ident=row+str(i);source='original'+ident
            labels.append(dict(id=ident,source_id=source,row=row,bank=bank,split='test'))
            for reader in ('oracle','nla'):
                oid=ident+reader
                packets[bank].append(dict(id=oid,property='The original '+row,values={'A':'first'+str(i),'B':'second'+str(i)},readout='old original reader text'))
                keys[bank].append(dict(unit_id=source,opaque_id=oid,eval=False))
            # A separately scored S6 record must never replace value candidates.
            packets[bank].append(dict(id=ident+'s6',readout='old'))
            keys[bank].append(dict(unit_id=source,opaque_id=ident+'s6',eval=True))
    return labels,packets,keys


def records(descriptors,part):
    records=[];pointers=[]
    for n,(ident,d) in enumerate(descriptors.items()):
        ptr='public'+str(n);pointers.append(dict(id=ptr,source_id=ident,row=d['row']))
        cells=[dict(alpha=a,arm=arm) for a in (1,2,4) for arm in ('T','W','R')] if part=='main' else [dict(condition=a,reader='oracle') for a in ('targeted','sham')]
        for j,cell in enumerate(cells):
            r=dict(id=ident+str(j),item_id=ident if part=='main' else ptr,row=d['row'],source_layer=44,text='' if n==0 else 'repeated repeated repeated repeated',**cell)
            records.append((dict(member='jobs/native.json',keys=[len(records),'text']),r))
    return records[::-1],pointers


def test_literal_original_per_item_descriptors_not_s6_or_gold():
    labels,p,k=fixture();d=descriptor_rows(labels,p,k)
    assert len(d)==336 and all(x['values']=={'A':'first0','B':'second0'} for x in d.values() if x['original_source_id'].endswith('recall0'))
    assert all(len(x['original_key_indices'])==2 for x in d.values())
    assert 'label' not in str(d)


@pytest.mark.parametrize('part,n',[('main',3024),('c',672)])
def test_all_registered_cells_retained_and_opaque_payload(part,n):
    d=descriptor_rows(*fixture());r,p=records(d,part);u,j=make_units(part,r,d,p)
    assert len(u)==len(j)==n and sum(x['data']['readout']=='' for x in u)==(9 if part=='main' else 2)
    assert all(set(x['data'])=={'id','property','values','readout'} and x['data']['id']==x['id'] for x in u)
    assert all(x['data']['readout'] in ('','repeated repeated repeated repeated') for x in u)
    assert len({x['source_ref']['keys'][0] for x in j})==n


@pytest.mark.parametrize('fault',['partial','duplicate','wrong_layer','wrong_row','wrong_arm','wrong_alpha'])
def test_fail_closed_native_scope(fault):
    d=descriptor_rows(*fixture());r,p=records(d,'main')
    if fault=='partial':r.pop()
    elif fault=='duplicate':r[1]=deepcopy(r[0])
    elif fault=='wrong_layer':r[0][1]['source_layer']=52
    elif fault=='wrong_row':r[0][1]['row']='invented'
    elif fault=='wrong_arm':r[0][1]['arm']='other'
    else:r[0][1]['alpha']=8
    with pytest.raises((ValueError,KeyError)):make_units('main',r,d,p)


@pytest.mark.parametrize('fault',['different_descriptor','missing_original','bad_family','missing_row','duplicate_pointer'])
def test_fail_closed_original_identity_or_descriptor(fault):
    labels,p,k=fixture()
    if fault=='different_descriptor':p['E56'][1]['values']['A']='changed'
    elif fault=='missing_original':k['E56']=[x for x in k['E56'] if x['unit_id']!=labels[0]['source_id']]
    elif fault=='bad_family':labels[0]['bank']='E57'
    elif fault=='missing_row':labels.pop()
    else:
        d=descriptor_rows(labels,p,k);r,ptr=records(d,'c');ptr[1]=deepcopy(ptr[0])
        with pytest.raises(ValueError):make_units('c',r,d,ptr)
        return
    with pytest.raises(ValueError):descriptor_rows(labels,p,k)
