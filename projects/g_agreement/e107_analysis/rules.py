"""§218 paired source-item comparisons with per-output naming denominators."""
import numpy as np
from common.stats import bootstrap_ci
READERS=('oracle','nla')
DRAWS,SEED=5000,0

def compare(items,reader,baseline,field,conditional=False):
    """Joint item bootstrap; never condition both outputs on reader's naming."""
    unmatched=sum(reader not in x['systems'] or baseline not in x['systems'] for x in items)
    items=sorted([x for x in items if reader in x['systems'] and baseline in x['systems']],key=lambda x:(x['row'],x['item_id']))
    arrays={};counts={}
    for system in (reader,baseline):
        vals=[];missing=unnamed=unavailable=0
        for x in items:
            z=x['systems'].get(system)
            if z is None:unavailable+=1;vals.append(np.nan);continue
            if z.get(field) is None or conditional and z.get('named') is None:missing+=1;vals.append(np.nan);continue
            if conditional and not z['named']:unnamed+=1;vals.append(np.nan);continue
            vals.append(float(z[field]))
        arrays[system]=np.array(vals,float)
        counts[system]=dict(planned=len(items),kept=int(np.isfinite(vals).sum()),missing=missing,not_stating_value=unnamed,unavailable=unavailable)
    def mean(x):return float(np.nanmean(x)) if np.isfinite(x).any() else np.nan
    out=dict(counts=counts,unmatched_source_items=unmatched)
    for name,fn in [(reader,lambda ix:mean(arrays[reader][ix])),(baseline,lambda ix:mean(arrays[baseline][ix])),('difference',lambda ix:mean(arrays[reader][ix])-mean(arrays[baseline][ix]))]:
        if not items:out[name]=dict(estimate=None,CI95=None);continue
        point,lo,hi=bootstrap_ci(np.arange(len(items)),fn=fn,n_boot=DRAWS,seed=SEED)
        out[name]=dict(estimate=point if np.isfinite(point) else None,CI95=[lo,hi] if np.isfinite([lo,hi]).all() else None)
    return out

def verdict(d):
    p,ci=d['estimate'],d['CI95']
    return dict(R_OL1='NOT EVALUABLE' if p is None or ci is None else 'MET' if round(p,12)>=.20 and ci[0]>0 else 'NOT MET',
                falsifier='NOT EVALUABLE' if p is None else 'MET' if p<=0 else 'NOT MET')

def analyze(items,e81_rows):
    out=dict(experiment='E107',authority='§218',bootstrap=dict(draws=DRAWS,seed=SEED,unit='source item',paired=True,pooled='item-weighted across surviving rows',identity=['row','item_id']),E82={},E86={},E81={},reader_exclusive={},caveat='outside describer and judge share model family; self-preference would favour outside and is conservative for R-OL1')
    for cohort in ('belief_wrong','belief_right','no_canonical_truth'):
        xs=[x for x in items if x['bank']=='E82' and x['cohort']==cohort]
        out['E82'][cohort]={}
        for reader in READERS:
            pooled=compare(xs,reader,'outside','belief',True)
            rows={row:compare([x for x in xs if x['row']==row],reader,'outside','belief',True) for row in sorted({x['row'] for x in xs})}
            out['E82'][cohort][reader]=dict(pooled=pooled,rows=rows)
    out['rules']=dict(oracle=verdict(out['E82']['belief_wrong']['oracle']['pooled']['difference']),nla_descriptive=verdict(out['E82']['belief_wrong']['nla']['pooled']['difference']))
    xs=[x for x in items if x['bank']=='E86']
    for reader in READERS:
        out['E86'][reader]=dict(pooled=compare(xs,reader,'outside','truth'),conditional_named=compare(xs,reader,'outside','truth',True),rows={row:compare([x for x in xs if x['row']==row],reader,'outside','truth') for row in sorted({x['row'] for x in xs})})
    # Preserve the outside/Qwen-self supplement even when original native
    # categorical codes do not exist (e.g. E49's historical regex metric).
    out['E81_baseline_comparison']={}
    for row in e81_rows:
        xs=[x for x in items if x['bank']=='E81' and x['row']==row]
        out['E81_baseline_comparison'][row]=compare(xs,'outside','qwen_self','S')
    for reader in READERS:
        out['reader_exclusive'][reader]=[]
        for row in e81_rows:
            xs=[x for x in items if x['bank']=='E81' and x['row']==row]
            matched=[x for x in xs if all(k in x['systems'] for k in (reader,'outside','qwen_self'))]
            outside=compare(matched,reader,'outside','S');qwen=compare(matched,reader,'qwen_self','S')
            a,b=outside['difference']['estimate'],qwen['difference']['estimate']
            exclusive=None if a is None or b is None else a>0 and b>0
            out['E81'].setdefault(row,{})[reader]=dict(reader_vs_outside=outside,reader_vs_qwen=qwen,reader_exclusive=exclusive,three_way_items=len(matched),unavailable_three_way_items=len(xs)-len(matched),unavailable_native_code_items=sum(reader not in x['systems'] for x in xs),availability_note='System availability here means original per-item categorical codes; missing codes do not imply missing native text.')
            if exclusive:out['reader_exclusive'][reader].append(row)
    out['reader_exclusive_definition']='strictly higher point S than BOTH baselines, per reader; descriptive, no added margin/significance threshold'
    return out
