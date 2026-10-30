from copy import deepcopy
from types import SimpleNamespace
import pytest
from . import e128_channel as channel
from .e128_intake import make_units
from .transport import ROOT,frozen_wire
from ..run import payload
from ..judgment_adapter402 import render_record


def fixture():
    records=[];identities=[];original=[];pointers=[];items=[];labels=[]
    for i in range(84):
        oid='original'+str(i);base='public'+str(i)
        original.append(dict(item_id=oid,arm='U',row='fact_recall',reader='oracle',condition='steered',flipped=True,target='B',property='A stated city',values={'A':['Old'],'B':['New']}))
        labels.append(dict(original_base_id=oid,old_value='Old',new_value='New'))
        for dose in (2,4):
            for condition in ('steered','random'):
                iid=base+':'+str(dose)+':'+condition
                items.append(dict(id=iid,base_id=base,row='fact_recall',alpha=dose,condition=condition))
                pointers.append(dict(id=iid,original_base_id=oid,scale=.25 if dose==2 else .5))
                for block in (44,52):
                    rid=iid+':oracle:'+str(block)
                    identities.append(dict(readout_id=rid,item_id=oid,condition=condition,layer=block,dose=dose,reader='oracle'))
                    records.append((dict(member='jobs.json',keys=[len(records),'text']),dict(id=rid,item_id=iid,base_id=base,condition=condition,alpha=dose,source_layer=block,reader='oracle',text='' if i==0 else 'Old')))
    return records[::-1],identities,original,pointers,items,labels


def test_full672_paired_original_sources_opaque_wire_and_original_rubric():
    rubric=(ROOT/'results/g_agreement/understand/e114/JUDGE_RUBRIC_COPY.md').read_text();units,joins=make_units(*fixture(),rubric)
    assert len(units)==len(joins)==672 and len({j['readout_id'] for j in joins})==672
    assert sum(u['data']['readout']=='' for u in units)==8 and all(':' not in u['id'] for u in units)
    p=SimpleNamespace(MODEL='google/gemini-3.1-flash-lite',PROVIDER='google-vertex/global',PROVIDER_NAME='Google')
    call,_=channel.original104_call(units[0],p);assert frozen_wire(call,p)==payload([render_record(units[0]['data'],rubric)],rubric,'E56',p)
    channel.check_scope('E128',units,dict(experiment='E128',issuer='W-internals-C',verified=True,complete_eligible_native_grid=True,labels_cpu_only=True,original_E104_rubric_sha256=channel.RUBRIC_SHA,original_candidates_unchanged=True,native_oracle44_52_only=True,only_lower_doses_2_4=True))
    assert {j['condition'] for j in joins}=={'steered','random'}


@pytest.mark.parametrize('fault',['missing_random','foreign_id','wrong_layer','alpha8','changed_target','changed_scale'])
def test_no_partial_or_inferred_source_substitution(fault):
    records,ids,old,ptr,items,labels=deepcopy(fixture())
    if fault=='missing_random':records.pop()
    elif fault=='foreign_id':ids[0]['item_id']='foreign'
    elif fault=='wrong_layer':records[0][1]['source_layer']=60
    elif fault=='alpha8':records[0][1]['alpha']=8
    elif fault=='changed_target':labels[0]['new_value']='invented'
    else:ptr[0]['scale']=1
    with pytest.raises(ValueError):make_units(records,ids,old,ptr,items,labels,'rubric')


def test_process_scope_cap_cutoff_retry_and_null_restored(monkeypatch):
    monkeypatch.setattr(channel,'source_gate',lambda:None);before=channel.transport.EXPIRY;caps=dict(channel.transport.CAPS);rate=channel.parallel_funded.MAX_429_RETRIES
    with pytest.raises(RuntimeError):
        with channel.worker():
            assert channel.transport.EXPIRY==1793372400 and channel.transport.CAPS['E128']==3 and channel.parallel_funded.MAX_429_RETRIES==0
            assert channel.registered.normalized_code('original104',dict(status='UNPARSEABLE',result=None)) is None
            raise RuntimeError('exit')
    assert channel.transport.EXPIRY==before and channel.transport.CAPS==caps and channel.parallel_funded.MAX_429_RETRIES==rate


def test_cutoff_checked_at_physical_post_after_waiting(monkeypatch):
    sent=[];request=SimpleNamespace(post=lambda *a,**k:sent.append(a));obj=object.__new__(channel.E128Transport);obj.api=SimpleNamespace(requests=request)
    monkeypatch.setattr(channel.transport.Transport,'__enter__',lambda self:self)
    monkeypatch.setattr(channel.transport.Transport,'__exit__',lambda self,*a:None)
    channel.E128Transport.__enter__(obj)
    def expired():raise ValueError('paid authority ended')
    monkeypatch.setattr(channel.transport,'unpaused',expired)
    with pytest.raises(ValueError):request.post('https://openrouter.ai/api/v1/chat/completions')
    assert sent==[];channel.E128Transport.__exit__(obj,None,None,None)
