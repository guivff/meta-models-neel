"""E105 frozen contrast orientation and item bootstrap, re-pointed to §235."""
import math
import numpy as np
from common.stats import bootstrap_ci
from projects.g_agreement.e105_analysis.rules import DRAWS,SEED

ROWS={'fact_recall':84,'language_plan':50}
BLOCKS=(44,48,52,56,60)
DIRECTIONS=('restore','insert')
PATCHES=('read_token','earlier_token','random_norm_matched')
CONTROL_DIRECTIONS=('restore',)  # direct Guiv clarification before output


def require(ok,message):
    if not ok:raise ValueError(message)


def log_odds(pairs,steered_value,candidate_A_value,pair_count):
    require(steered_value in ('A','B') and candidate_A_value in ('A','B'),'frozen value orientation')
    require(type(pair_count)is int and pair_count>0 and isinstance(pairs,list) and len(pairs)==pair_count,'exact original frozen candidate pair count')
    require(all(isinstance(p,list) and len(p)==2 and all(type(v)in(int,float) and math.isfinite(v) and v<=0 for v in p) for p in pairs),'finite full continuation sums')
    sign=1 if steered_value==candidate_A_value else -1
    return sign*sum(x-y for x,y in pairs)/pair_count  # original E105 normalization


def median_stat(values,draws=DRAWS):
    defined=[x for x in values if x is not None]
    require(all(math.isfinite(x)for x in defined),'finite ratios; no clipping/winsorizing')
    if len(defined)!=len(values) or not values:
        return dict(estimate=None,CI95=None,n=len(values),n_defined=len(defined),reason='undefined per-item denominator; no cohort shrinking')
    point,lo,hi=bootstrap_ci(values,fn=np.median,n_boot=draws,seed=SEED)
    return dict(estimate=point,CI95=[lo,hi],n=len(values),n_defined=len(values))


def item_ratios(record):
    clean,steered=record['clean'],record['steered'];require(all(type(x)in(int,float) and math.isfinite(x)for x in (clean,steered)),'finite native log odds')
    require(set(record['patches'])==set(BLOCKS),'five original blocks')
    gap=steered-clean;out={}
    for block in BLOCKS:
        z=record['patches'][block];require(set(z)==set(DIRECTIONS),'both patch directions')
        out[block]={}
        for direction in DIRECTIONS:
            require(set(z[direction])==set(PATCHES),'read-site and both controls')
            out[block][direction]={}
            for patch,value in z[direction].items():
                require(type(value)in(int,float) and math.isfinite(value),'finite original patched log odds')
                numerator=steered-value if direction=='restore' else value-clean
                out[block][direction][patch]=None if gap==0 else numerator/gap
    return dict(item_id=record['item_id'],row=record['row'],native_gap=gap,zero_native_gap=gap==0,
                raw_log_odds=dict(clean=clean,steered=steered,patches=record['patches']),ratios=out)


def all3(tests):
    return False if False in tests else None if None in tests else True


def any3(tests):
    return True if True in tests else None if None in tests else False


def classify(blocks):
    control_directions=CONTROL_DIRECTIONS
    point=lambda b,d,p:blocks[b][d][p]['estimate']
    low=lambda value:None if value is None else value<=.15
    controls=all3([low(point(b,d,p))for b in BLOCKS for d in control_directions for p in PATCHES[1:]])
    later=[]
    for block in (52,56):
        s=blocks[block]['restore']['read_token'];later.append(None if s['estimate'] is None or s['CI95'] is None else s['estimate']>=.50 and s['CI95'][0]>.25)
    med=all3([any3(later),low(point(44,'restore','read_token')),controls])
    falsifier=all3([all3([low(point(b,'restore','read_token'))for b in BLOCKS]),controls])
    status=lambda x:'NOT EVALUABLE' if x is None else 'MET' if x else 'NOT MET'
    return dict(R_MED1=status(med),falsifier=status(falsifier),control_scope=list(control_directions),control_blocks=list(BLOCKS),controls_at_most_015=controls)


def analyze(records,draws=DRAWS):
    require(type(draws)is int and draws>0,'positive bootstrap draws')
    require({x['row']for x in records}==set(ROWS),'both original rows')
    require(len({(x['row'],x['item_id'])for x in records})==len(records),'unique original items')
    out={};per_item=[]
    for row,n in ROWS.items():
        xs=sorted([x for x in records if x['row']==row],key=lambda x:x['item_id']);require(len(xs)==n,'full original flipped cohort')
        ratios=[item_ratios(x)for x in xs];per_item.extend(ratios);blocks={}
        for block in BLOCKS:
            blocks[block]={d:{p:median_stat([x['ratios'][block][d][p]for x in ratios],draws)for p in PATCHES}for d in DIRECTIONS}
        out[row]=dict(n_items=n,zero_native_gap_items=sum(x['zero_native_gap']for x in ratios),blocks=blocks,
                      descriptive_rules=classify(blocks),raw_log_odds_medians=dict(clean=float(np.median([x['clean']for x in xs])),steered=float(np.median([x['steered']for x in xs])),patches={b:{d:{p:float(np.median([x['patches'][b][d][p]for x in xs]))for p in PATCHES}for d in DIRECTIONS}for b in BLOCKS}),raw_log_odds_location='local PER_ITEM.PRIVATE.json; source item raw clean/steered/all patches retained')
    return dict(experiment='E126',rows=out,R_MED1=out['fact_recall']['descriptive_rules']['R_MED1'],falsifier=out['fact_recall']['descriptive_rules']['falsifier'],
                rule_scope='confirmatory R-MED1 fact_recall only; language_plan and insertion descriptive; per-row falsifier displayed',
                bootstrap=dict(draws=draws,seed=SEED,unit='original item; ratio before median and bootstrap',statistic='median',backend='common.stats.bootstrap_ci'),
                normalization='R=(steered-patched_restore)/(steered-clean); I=(patched_insert-clean)/(steered-clean); fixed target-minus-original full-continuation log odds',
                undefined_policy='exact zero denominator retained as undefined; no epsilon, clipping, dropping or changed cohort; affected median/rule NOT EVALUABLE'),per_item
