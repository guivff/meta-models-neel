"""§210 E103 claim rates with source-item cluster bootstrap and paired controls."""
import argparse
import numpy as np
from .common import *

def prepare(records,inventory):
    require(inventory['selection_seed']==20261028 and inventory['mismatch_same_bank'] is True,'frozen selection and control')
    require(inventory['selection_plan_sha256'],'frozen W-text selection plan')
    identities=set()
    for x in records:
        key=(x['wave'],x['bank'],x['reader'],x['readout_id'],x['claim_id'])
        require(key not in identities,'wave-qualified unique claim');identities.add(key)
        require(x['reader'] in ('oracle','nla') and x['kind'] in ('CONTRADICTED','SUPPORTED'),'registered reader and claim strata')
        require(x['source_item_id']!=x['mismatch_item_id'] and x['bank']==x['mismatch_bank'] and x['wave']==x['mismatch_wave'],'different item same bank/wave')
        require(x['claim'] and x['original_verdict']==x['kind'],'unchanged E67 claim/verdict')
        require(x['cohort']==('hallucinated' if x['kind']=='CONTRADICTED' else 'faithful'),'registered claim queue')
        if x['kind']=='SUPPORTED':require(x['readout_has_contradicted'] is False,'faithful readout has no contradicted claims')
        for arm in ('own','mismatched'):
            raw=x[arm+'_response'];require(isinstance(raw,str),'text yes/no response')
            value=raw.strip().casefold()
            require(value in ('yes','no','unparseable'),'registered yes/no or explicit missing sentinel')
            x[arm]=None if value=='unparseable' else int(value=='yes')
    selected={}
    for x in records:selected.setdefault((x['wave'],x['bank'],x['reader'],x['cohort']),set()).add(x['readout_id'])
    for cohort in ('hallucinated','faithful'):
        require(sum(len(v) for k,v in selected.items() if k[3]==cohort)<=200,'at most200 readouts/cohort across waves')
    strata={k[:3] for k in selected}
    for k in strata:require(len(selected.get(k+('hallucinated',),set()))==len(selected.get(k+('faithful',),set())),'matched readout capacity per wave/bank/reader')
    return records

def rates(records):
    """Claim-weighted match rates; paired resampling at source-item granularity.

    A source item can contribute multiple claims and readers. They move together.
    Wave and bank are part of its identity; colliding readout IDs never merge.
    Separate masks for the two arms retain all parseable judgments.
    """
    clusters={}
    for x in records:clusters.setdefault((x['wave'],x['bank'],x['source_item_id']),[]).append(x)
    keys=sorted(clusters);n=len(keys)
    if not n:return dict(items=0,claims=0,own=dict(estimate=None,CI95=None),mismatched=dict(estimate=None,CI95=None),difference=dict(estimate=None,CI95=None))
    ix=np.random.default_rng(SEED).integers(0,n,(DRAWS,n));res={};ds={}
    for arm in ('own','mismatched'):
        sums=np.array([sum(x[arm] for x in clusters[k] if x[arm] is not None) for k in keys],float)
        counts=np.array([sum(x[arm] is not None for x in clusters[k]) for k in keys])
        den=counts[ix].sum(axis=1);draw=np.divide(sums[ix].sum(axis=1),den,out=np.full(DRAWS,np.nan),where=den>0)
        kept=int(counts.sum());ds[arm]=draw
        res[arm]=dict(estimate=float(sums.sum()/kept) if kept else None,CI95=np.quantile(draw,[.025,.975]).tolist() if np.isfinite(draw).all() else None,kept=kept,missing=len(records)-kept,over_5_percent=(len(records)-kept)*20>len(records))
    delta=ds['own']-ds['mismatched'];a,b=res['own']['estimate'],res['mismatched']['estimate']
    res['difference']=dict(estimate=a-b if a is not None and b is not None else None,CI95=np.quantile(delta,[.025,.975]).tolist() if np.isfinite(delta).all() else None)
    return dict(items=n,claims=len(records),**res)

def analyze(records):
    pooled={k:rates([x for x in records if x['kind']==k]) for k in ('CONTRADICTED','SUPPORTED')}
    d=pooled['CONTRADICTED']['difference']
    result=dict(experiment='E103',bootstrap=dict(draws=DRAWS,seed=SEED,unit='source item',paired=True,identity=['wave','bank','source_item_id'],estimand='claim-weighted rate'),pooled=pooled,
                rules={'R-H2':count([both(ge(d,.15),low(d,0))],1),'falsifier':count([le(d,.03)],1)},breakdowns={})
    for fields in [('reader',),('bank',),('wave',),('reader','bank','wave')]:
        name='_'.join(fields);result['breakdowns'][name]=[]
        for key in sorted({tuple(x[f] for f in fields) for x in records}):
            xs=[x for x in records if tuple(x[f] for f in fields)==key]
            result['breakdowns'][name].append(dict(zip(fields,key),rates={k:rates([x for x in xs if x['kind']==k]) for k in ('CONTRADICTED','SUPPORTED')}))
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args();commit=committed();s=read(a.spec)
    require(s['experiment']=='E103','experiment');rows,bundle,inventory=normalized(s,'E103');prepare(rows,inventory)
    out=reserve('E103',s,commit);result=analyze(rows)
    # D4 literal spans and E99 are separately sealed descriptive extensions, not
    # eligible for the E67 confirmatory pool. No inference is silently added.
    result['descriptive_extensions']={'D4':'not part of this E67 confirmatory adapter','E99':'not part of this E67 confirmatory adapter'}
    finish('E103',s,commit,result,out)
if __name__=='__main__':main()
