from copy import deepcopy
from types import SimpleNamespace
import pytest
from . import e127_channel as channel
from .e127_intake import make_units
from .transport import ROOT,frozen_wire
from ..run import payload
from ..judgment_adapter402 import render_record


def fixture():
    records=[];identities=[];original=[];labels=[]
    for i in range(84):
        oid='original'+str(i);base='public'+str(i)
        original.append(dict(item_id=oid,arm='U',row='fact_recall',reader='oracle',condition='steered',flipped=True,target='B',property='A stated city',values={'A':['Old'], 'B':['New']}))
        labels.append(dict(base_id=base,original_base_id=oid,old_value='Old',new_value='New',condition_ids={c:base+':'+c for c in ('context_update','neutral_prefix','none')}))
        for c in ('context_update','neutral_prefix','none'):
            for b in (44,52,60):
                rid=base+':'+c+':oracle:'+str(b)
                identities.append(dict(readout_id=rid,item_id=oid,condition='no_prefix' if c=='none' else c,layer=b,reader='oracle'))
                records.append((dict(member='jobs.json',keys=[len(records),'text']),dict(id=rid,item_id=base+':'+c,base_id=base,condition=c,source_layer=b,reader='oracle',text='' if i==0 else 'Old')))
    return records[::-1],identities,original,labels


def test_full756_explicit_joins_opaque_wire_and_exact_rubric():
    rubric=(ROOT/'results/g_agreement/understand/e114/JUDGE_RUBRIC_COPY.md').read_text()
    units,joins=make_units(*fixture(),rubric);assert len(units)==len(joins)==756
    assert all(':' not in u['id'] for u in units) and len({j['readout_id'] for j in joins})==756
    assert sum(u['data']['readout']=='' for u in units)==9
    p=SimpleNamespace(MODEL='google/gemini-3.1-flash-lite',PROVIDER='google-vertex/global',PROVIDER_NAME='Google')
    call,_=channel.original104_call(units[0],p)
    assert frozen_wire(call,p)==payload([render_record(units[0]['data'],rubric)],rubric,'E56',p)
    channel.check_scope('E127',units,dict(experiment='E127',issuer='W-internals-C',verified=True,complete_eligible_native_grid=True,labels_cpu_only=True,original_E104_rubric_sha256=channel.RUBRIC_SHA,original_candidates_unchanged=True,native_oracle44_52_60_only=True))


@pytest.mark.parametrize('fault',['missing','foreign_id','wrong_layer','changed_target'])
def test_no_partial_or_unbound_replacement(fault):
    records,ids,old,labels=deepcopy(fixture())
    if fault=='missing':records.pop()
    elif fault=='foreign_id':ids[0]['item_id']='foreign'
    elif fault=='wrong_layer':records[0][1]['source_layer']=43
    else:labels[0]['new_value']='invented'
    with pytest.raises(ValueError):make_units(records,ids,old,labels,'rubric')


def test_expiry_cap_and_globals_are_process_local_and_missing_unchanged(monkeypatch):
    monkeypatch.setattr(channel,'source_gate',lambda:None)
    before=channel.transport.EXPIRY;caps=dict(channel.transport.CAPS)
    with pytest.raises(RuntimeError):
        with channel.worker():
            assert channel.transport.EXPIRY==1793372400 and channel.transport.CAPS['E127']==3
            assert channel.registered.normalized_code('original104',dict(status='UNPARSEABLE',result=None)) is None
            raise RuntimeError('exit')
    assert channel.transport.EXPIRY==before and channel.transport.CAPS==caps
