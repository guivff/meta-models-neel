"""Administrative full E107b closure and explicit original-target code pointers."""
from decimal import Decimal
from .runner import CACHE
from .transport import ROOT,HERE,SHARED
from .accounting import bank_actual
from .seal_bank import disposition
from ..dispatch_lock import dispatch_lock
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def bindings(plans,generated,judged,n=199):
    gen={x['id']:(i,x)for i,x in enumerate(generated)};jud={x['id']:(i,x)for i,x in enumerate(judged)}
    require(len(gen)==len(generated)==n and len(jud)==len(judged)==len(plans)==2*n,'full unique original registered grid')
    require(set(gen)=={p['forecast_id']for p in plans}and set(jud)=={p['judgment_id']for p in plans},'literal original source IDs')
    out=[]
    for p in plans:
        gi,g=gen[p['forecast_id']];ji,j=jud[p['judgment_id']]
        require(g['status']=='GENERATED'and j['kind']=='value'and j['status']in('KEPT','UNPARSEABLE','REFUSED'),'all terminal statuses')
        require((j['code']is None)==(j['status']!='KEPT'),'preserve original null code')
        out.append(dict(original_inventory_id=p['inventory_id'],target=p['target'],forecast_id=p['forecast_id'],judgment_id=p['judgment_id'],status=j['status'],forecast_keys=[gi,'text'],original_code_keys=[ji,'code'],frozen_target_plan=p))
    return out


def close():
    for n,h in read(HERE/'E107B_CLOSE245_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'published administrative source')
    b=CACHE/'E107b';gp=b/'generation/outputs/GENERATION_SEAL.json';jp=b/'forecast_judging/outputs/JUDGMENT_SEAL.json'
    for p in (gp,jp):require(verify(p,sha(p))['status']=='COMPLETE','separate complete original phases')
    refs=bindings(read(b/'forecast_source/JUDGE_PLAN.PRIVATE.json'),read(gp.parent/'RESPONSES.json'),read(jp.parent/'JUDGMENTS.json'))
    for r in refs:
        r['forecast_ref']=dict(seal=str(gp),sha256=sha(gp),member='RESPONSES.json',keys=r.pop('forecast_keys'))
        r['original_code_ref']=dict(seal=str(jp),sha256=sha(jp),member='JUDGMENTS.json',keys=r.pop('original_code_keys'))
    with dispatch_lock(SHARED/'E107b/DISPATCH.lock'):
        actual,unknown=bank_actual(SHARED/'E107b/ledger');cost=disposition(2,actual,unknown);p=SHARED/'E107b/ALLOCATION_C.json';a=read(p);require(a['bank']=='E107b'and Decimal(a['allocation_usd'])==2,'same original combined2')
        d=b/'complete245';d.mkdir(exist_ok=True);final=d/'JUDGMENT_SEAL.json'
        if final.exists():verify(final,sha(final));require(read(d/'BANK_COST.json')==cost,'no latercost/reclose')
        else:
            require(a['status']=='OPEN','original allocation open')
            write(d/'TARGET_BINDINGS.PRIVATE.json',refs);write(d/'BANK_COST.json',cost);write(d/'ORIGINAL_ALLOCATION.PRIVATE.json',a)
            write(final,dict(experiment='E107b',status='COMPLETE_JUDGING_BANK',generation_n=199,judging_n=398,route_verified=True,labels_cpu_only=True,primary_replayed=False,files={n:sha(d/n)for n in ['TARGET_BINDINGS.PRIVATE.json','BANK_COST.json','ORIGINAL_ALLOCATION.PRIVATE.json']}))
        if a['status']=='RELEASED':require(a['completion_seal_sha256']==sha(final),'same once release')
        else:write(p,dict(a,status='RELEASED',completion_seal=str(final),completion_seal_sha256=sha(final),final_actual_usd=str(actual),unused_allocation_released_usd=cost['unused_allocation_released_usd']))
        write(SHARED/'E107b/BANK_COMPLETE_C.json',dict(bank='E107b',status='COMPLETE',seal=str(final),sha256=sha(final),**cost))
        return final
