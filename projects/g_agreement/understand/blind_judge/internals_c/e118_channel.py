"""Separate E1181 sealed252-call bank; prompt frozen in the prospective adapter."""
import argparse
import os
import time
from collections import Counter
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

from . import runner,transport
from .banks import opaque,object_schema
from .accounting229 import snapshot
from .accounting import bank_actual
from .seal_bank import disposition
from ..dispatch_lock import dispatch_lock
from projects.g_agreement.e118_analysis.adapter import SYSTEM,CONDITIONS
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

CAP=Decimal('1')


def calls_for(rows):
    import json
    require(len(rows)==252 and len({x['id']for x in rows})==252 and
            Counter(x['condition']for x in rows)=={c:84 for c in CONDITIONS},'full frozen252 source cells')
    groups={c:{x['item_id']for x in rows if x['condition']==c}for c in CONDITIONS}
    require(all(len(v)==84 for v in groups.values()) and len({frozenset(v)for v in groups.values()})==1,
            'same original84 flipped items, no condition-specific selection')
    calls=[]
    for row in rows:
        require(type(row['context'])is str and bool(row['context']) and type(row['readout'])is str,'exact original context/readout strings')
        call=dict(id=row['id'],phase='judging',rendered=dict(system=SYSTEM,
            user=json.dumps(dict(id=row['id'],context=row['context'],readout=row['readout']),ensure_ascii=False),
            schema=object_schema('context_consistency',{'verdict':{'type':'string','enum':['YES','NO','OFF-TOPIC']}})))
        calls.append(call)
    return calls


def source_gate():
    for name,digest in read(transport.HERE/'E118_SOURCE_SEAL.json')['files'].items():
        require(sha(transport.ROOT/name)==digest,'published E118 prompt/source/analysis pin')


def prepare():
    source_gate();base=transport.ROOT.parent
    bank=base/'wt-wtext/results/g_agreement/understand/e56/cache/bank_2026-10-27_v1/BANK_SEAL.json'
    verify(bank,'e733bed854700d0129a7b59ed1e1e6ddf82947add11c2f3e77feb36bfb451112')
    metadata=read(bank.parent/'items.PRIVATE.json');facts={tuple(x['ids']):(i,x)for i,x in enumerate(metadata)if x['feature']=='fact_recall'}
    require(len(facts)==168,'original unique fact prompt token sequences')
    b=base/'wt-internals-b/cache/g_agreement/understand/funded_queue/E104'
    norm=b/'normalized/INPUT_SEAL.json';ns=verify(norm,'0d1ccb6d088960540c0fef2b4c973dd9b02c5941bfd153b870b7e8914d37ae7d')
    private=b/'PRIVATE_SEAL.json';verify(private,'0f42d78d151a85b858f2b02a13307e62e74f987ad0bba009cab875b6792aa3c6')
    require(sha(b/'PRIVATE.json')=='495bbb19179f507869779d611c737ac82181f8c404054fcffd6963b7615fd0e4','original flipped flags unchanged')
    old=[x for x in read(b/'PRIVATE.json')if x['arm']=='U'and x['row']=='fact_recall']
    cohort={x['item_id']for x in old if x['condition']=='steered'and x['flipped']is True}
    require(len(cohort)==84 and len(old)==168,'whole original84 flipped fact cohort')
    sources=[dict(seal=str(bank),sha256=sha(bank)),dict(seal=str(norm),sha256=sha(norm)),dict(seal=str(private),sha256=sha(private))]+ns['source_seals']
    for ref in sources:verify(ref['seal'],ref['sha256'])
    original_input=Path(ns['source_seals'][0]['seal']);items=read(original_input.parent/'items.json');contexts={};contextrefs={}
    for item in items:
        i,meta=facts[tuple(item['ids'])]
        require(meta['split']=='test' and item['base_id']in cohort and item['arm']=='U'and item['row']=='fact_recall',
                'exact input token identity to original sealed text, not a new rendered prompt')
        require(item['base_id']not in contexts or contexts[item['base_id']]==meta['text'],'paired context equality')
        contexts[item['base_id']]=meta['text'];contextrefs[item['base_id']]=dict(seal=str(bank),sha256=sha(bank),member='items.PRIVATE.json',keys=[i,'text'])
    require(set(contexts)==cohort,'full original context roster')
    rows=[]
    for x in read(norm.parent/'RECORDS.json'):
        if x['arm']!='U'or x['row']!='fact_recall':continue
        require(x['item_id']in cohort and x['condition']in ('steered','random') and x['reader']=='oracle'and x['split']=='test','original E104 U44 cells')
        ref=x['measurements']['text'];source=ns['source_seals'][ref['seal_index']];value=read(Path(source['seal']).parent/ref['member'])
        for k in ref['keys']:value=value[k]
        require(value==next(v['text']for v in old if v['id']==x['id']),'exact original E104 raw readout')
        ident=opaque('E118','E104',x['id'])
        rows.append(dict(id=ident,item_id=x['item_id'],condition='E104_U_44_'+x['condition'],context=contexts[x['item_id']],readout=value,
                         context_ref=contextrefs[x['item_id']],readout_ref=dict(source,member=ref['member'],keys=ref['keys'])))
    native=base/'wt-wmech/cache/g_agreement/understand/analysis402_verified/E109/production/combined/out/OUTPUT_SEAL.json'
    s=verify(native,'ecaf7813b2baa57d7c210423cd1ca09a1d388af566ab6eacbeeb5384e8838bde');require(s['status']=='COMPLETE','original complete E109 native bank')
    sources.append(dict(seal=str(native),sha256=sha(native)))
    unit=runner.CACHE/'E109/oracle_arrival_units/UNIT_SEAL.json';verify(unit,sha(unit));sources.append(dict(seal=str(unit),sha256=sha(unit)))
    for x in read(unit.parent/'SOURCE_POINTERS.PRIVATE.json'):
        if not(x['row']=='fact_recall'and x['layer']==52 and x['condition']=='steered'):continue
        ref=x['source_ref'];require(ref['member']in s['files'] and x['item_id']in cohort,'original E109 fact52 member/cohort')
        raw=read(native.parent/ref['member'])[ref['index']]
        require(raw['base_id']==x['item_id']and raw['reader']=='oracle'and raw['layer']==52 and raw['condition']=='steered','native exact identity')
        rows.append(dict(id=opaque('E118','E109',x['source_id']),item_id=x['item_id'],condition='E109_52_steered',context=contexts[x['item_id']],readout=raw['text'],
            context_ref=contextrefs[x['item_id']],readout_ref=dict(seal=str(native),sha256=sha(native),member=ref['member'],keys=[ref['index'],'text'])))
    rows.sort(key=lambda x:x['id'])  # Blind acquisition order, independent of condition/outcome.
    calls=calls_for(rows)
    dest=runner.seal_phase('E118','consistency_judging',calls,dict(n=252,prompt_source_sha256=sha(transport.ROOT/'projects/g_agreement/e118_analysis/adapter.py'),
        E118_source_seal_sha256=sha(transport.HERE/'E118_SOURCE_SEAL.json'),no_native_rerun=True),sources)
    joins=[{k:v for k,v in x.items()if k not in ('context','readout')}for x in rows]
    if(dest/'CPU_JOIN.PRIVATE.json').exists():require(read(dest/'CPU_JOIN.PRIVATE.json')==joins,'immutable original private crosswalk')
    else:write(dest/'CPU_JOIN.PRIVATE.json',joins)
    seal=read(dest/'INPUT_SEAL.json');seal['files']['CPU_JOIN.PRIVATE.json']=sha(dest/'CPU_JOIN.PRIVATE.json');write(dest/'INPUT_SEAL.json',seal)
    return dest,runner.preflight(dest)


class E118Transport(transport.Transport):
    def __init__(self,path,digest,admission,key):
        require(admission['bank']=='E118'and Decimal(str(admission['allocation_usd']))==CAP and
                admission['E118_source_seal_sha256']==sha(transport.HERE/'E118_SOURCE_SEAL.json'),'original E118 separate1 source-bound allocation')
        super().__init__(path,digest,admission,key)


@contextmanager
def worker():
    source_gate();prior=transport.CAPS.get('E118');require(prior in (None,CAP),'separate E1181 cap')
    transport.CAPS['E118']=CAP;old=runner.Transport,runner.snapshot;runner.Transport,runner.snapshot=E118Transport,snapshot
    try:yield
    finally:
        runner.Transport,runner.snapshot=old
        if prior is None:transport.CAPS.pop('E118',None)
        else:transport.CAPS['E118']=prior


def run(dest):
    proof=dest/'LIVE_PROOF.PRIVATE.json';a=read(dest/'ADMISSION.json');require(sha(proof)==a['live_route_funding_proof_sha256'],'published exact live proof')
    live=read(proof);require(0<=time.time()-live['at_epoch']<300 and all(live[k]is True for k in ('route_verified','account_privacy_verified','funded_remaining_bank_cap')),'fresh route/privacy/funding')
    require(len(read(dest/'CALLS.json'))==252,'exact252 calls, no schema retries')
    return runner.run(dest)


def close():
    home=runner.CACHE/'E118';phase=home/'consistency_judging/outputs/JUDGMENT_SEAL.json';s=verify(phase,sha(phase))
    require(s['experiment']=='E118'and s['status']=='COMPLETE'and s['route_verified']is True and len(read(phase.parent/'RESPONSES.json'))==252,'full completed252 bank')
    with dispatch_lock(transport.SHARED/'E118/DISPATCH.lock'):
        actual,unknown=bank_actual(transport.SHARED/'E118/ledger');cost=disposition(1,actual,unknown)
        allocation=transport.SHARED/'E118/ALLOCATION_C.json';a=read(allocation);require(a['bank']=='E118'and Decimal(str(a['allocation_usd']))==CAP,'same lifetime1 allocation')
        dest=home/'complete';dest.mkdir(exist_ok=True);final=dest/'JUDGMENT_SEAL.json'
        if final.exists():verify(final,sha(final));require(read(dest/'BANK_COST.json')==cost,'no later costs')
        else:
            require(a['status']=='OPEN','only original open allocation')
            write(dest/'ORIGINAL_ALLOCATION.PRIVATE.json',a);write(dest/'BANK_COST.json',cost)
            write(final,dict(experiment='E118',status='COMPLETE_JUDGING_BANK',route_verified=True,labels_cpu_only=True,phase_seal=str(phase),phase_sha256=sha(phase),
                files={n:sha(dest/n)for n in ('ORIGINAL_ALLOCATION.PRIVATE.json','BANK_COST.json')}))
        if a['status']=='RELEASED':require(a['completion_seal_sha256']==sha(final),'same once-only release')
        else:write(allocation,dict(a,status='RELEASED',completion_seal=str(final),completion_seal_sha256=sha(final),final_actual_usd=str(actual),unused_allocation_released_usd=cost['unused_allocation_released_usd']))
        write(transport.SHARED/'E118/BANK_COMPLETE_C.json',dict(bank='E118',status='COMPLETE',seal=str(final),sha256=sha(final),**cost))
        return final


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=('prepare','run','close'));p.add_argument('--phase-directory',type=Path);a=p.parse_args()
    with worker():
        if a.action=='prepare':print(prepare())
        elif a.action=='run':run(a.phase_directory)
        else:print('E118 bank closed '+sha(close()))
