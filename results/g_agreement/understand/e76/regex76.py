"""Frozen CPU-only regex floor estimands; no reader or judging dependency."""
import re
import numpy as np
from common76 import *


def hits(text,family):
    require(isinstance(text,str),'Preserve native text, including empty strings')
    flags=re.I if family['ignore_case'] else 0
    if family['policy']=='sentence_negation':
        clauses=re.split(r'[.!?\n]+',text)
        return [any(re.search(pattern,s,flags) and not re.search(family['negation'],s,flags) for s in clauses) for pattern in family['patterns']]
    require(family['policy']=='whole_word_or_frozen_regex','Unknown frozen regex policy')
    return [bool(re.search(pattern,text,flags)) for pattern in family['patterns']]


def item_values(records,row):
    require(row['status']=='AVAILABLE' and row['families'],'Available frozen regex row required')
    labels=np.random.default_rng(20261029).integers(0,2,size=N)
    naming=np.zeros(len(records),float);signed=np.zeros(len(records),float);binary=True
    total=sum(f['weight'] for f in row['families']);require(total>0,'Positive frozen family weights required')
    for family in row['families']:
        h=np.array([hits(x['text'],family) for x in records],dtype=bool);weight=family['weight']/total
        naming+=weight*h.any(axis=1)
        if h.shape[1]==2:
            count=h.sum(1);correct=h[np.arange(len(h)),labels[[x['pool_index'] for x in records]]]
            signed+=weight*np.where(count==1,np.where(correct,1.,-1.),0.)
        else:binary=False
    return naming,signed if binary else None


def bootstrap(x,draws=2000,seed=20261027):
    x=np.asarray(x,float);require(x.ndim==1 and len(x)>0 and np.isfinite(x).all(),'Finite nonempty pool values required')
    rng=np.random.default_rng(seed);means=np.empty(draws)
    for start in range(0,draws,100):
        ix=rng.integers(0,len(x),size=(min(100,draws-start),len(x)));means[start:start+len(ix)]=x[ix].mean(1)
    return {'estimate':float(x.mean()),'ci95':np.quantile(means,[.025,.975],method='linear').tolist(),'n_vectors':len(x)}


def floor(records,row):
    naming,signed=item_values(records,row)
    return {'N_any_value':bootstrap(naming),'S_regex':bootstrap(signed) if signed is not None else None,
        'signed_status':'DEFINED_RANDOM_PSEUDO_TRUTH' if signed is not None else 'NOT_BINARY_VALUE_SET',
        'source_bank_covariates':{BANKS[b]:{'n':int(sum(x['source_bank']==b for x in records)),
            'N_any_value':bootstrap(naming[[x['source_bank']==b for x in records]]),
            'S_regex':bootstrap(signed[[x['source_bank']==b for x in records]]) if signed is not None else None}
            for b in sorted({x['source_bank'] for x in records})}}


def validate_grid(records):
    expected={(r,a,i) for r in READERS for a in ARMS for i in range(N)}
    keys=[(x['reader'],x['arm'],x['pool_index']) for x in records]
    require(len(keys)==len(set(keys)) and set(keys)==expected,'Complete one-greedy2000-record pool required')
    for x in records:
        require(x['repeat']==0 and x['layer']==(44 if x['reader']=='oracle' else 42)
            and type(x['source_bank']) is int and 0<=x['source_bank']<5 and isinstance(x['text'],str),'Native record/covariate mismatch')
        if x['reader']=='nla':require(x['native_max_new_tokens']==512 and x['native_stop']=='</explanation>','NLA512 stop contract required')
    return {(r,a):sorted([x for x in records if x['reader']==r and x['arm']==a],key=lambda x:x['pool_index']) for r in READERS for a in ARMS}


def score(records,catalog):
    grid=validate_grid(records);rows=[]
    for row in catalog['rows']:
        out={'bank':row['bank'],'row':row['row'],'regex_status':row['status'],'regex_source':row['sources'],
             'reason':row.get('reason'),'readers':{}}
        if row['status']=='AVAILABLE':
            for reader in READERS:out['readers'][reader]={arm:floor(grid[reader,arm],row) for arm in ARMS}
        rows.append(out)
    return {'experiment':'E76','status':'REGEX_FLOOR_COMPLETE_ONCE','rows':rows,
        'pool_vectors_per_arm_reader':N,'readouts_per_vector':1,'source_bank_codes':list(BANKS),
        'bootstrap':{'draws':2000,'seed':20261027,'unit':'pool vector','method':'95% percentile'},
        'pseudo_truth':{'seed':20261029,'assignment':'One fixed independent A/B coin per pool index; shared by arms/readers; no source truth used'},
        'judged_floors':'WAITING_SEPARATE_AUTHORISATION_USD2','judge_calls':0,
        'caveat':'Regex occurrence floor, not an assertion or correctness judgment. Both/neither score zero in signed S. Pattern-family floors average with frozen test-family weights. Unavailable value regexes are explicit, never substituted with zero.'}
