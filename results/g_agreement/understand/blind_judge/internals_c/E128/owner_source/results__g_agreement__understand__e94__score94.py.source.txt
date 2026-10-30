"""E94 pure three-class, same-item agreement analysis; no model or judge calls."""
from collections import Counter
import numpy as np

CLASSES=('correct','wrong','no mention')
def require(ok,msg):
    if not ok: raise ValueError(msg)
def value_class(code,truth):
    require(truth in ('A','B'),'binary truth')
    category=code['category']
    if category=='UNPARSEABLE':
        require(code['values']==[],'missing sentinel');return None
    require(category in ('states_value','names_property_without_value','exhibits','silent'),'category')
    values=code['values'];require(isinstance(values,list) and len(values)==len(set(values)) and set(values)<={'A','B'},'values')
    require(bool(values)==(category=='states_value'),'category/value consistency')
    return ('correct' if values==[truth] else 'wrong') if len(values)==1 else 'no mention'
def claim_class(code):
    if code is None:return None
    require(code['generic']==(len(code['claims'])==0),'claim generic')
    verdicts={c['verdict'] for c in code['claims']}
    require(verdicts<={'SUPPORTED','CONTRADICTED','UNVERIFIABLE'},'claim verdict')
    return 'wrong' if 'CONTRADICTED' in verdicts else 'correct' if 'SUPPORTED' in verdicts else 'no mention'
def fraction(k,n):
    if not n:return dict(k=k,n=n,rate=None,Wilson95=None)
    p=k/n;z=1.959963984540054;d=1+z*z/n;c=(p+z*z/(2*n))/d;r=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return dict(k=int(k),n=int(n),rate=float(p),Wilson95=[float(max(0,c-r)),float(min(1,c+r))])
def join(rows):
    grouped={}
    for r in rows:
        require(r['reader'] in ('oracle','nla'),'reader')
        require(r['class'] is None or r['class'] in CLASSES,'class')
        key=(r['bank'],r['unit']);g=grouped.setdefault(key,{})
        require(r['reader'] not in g,'duplicate item/reader');g[r['reader']]=r
    paired=[];audit=Counter()
    for key,g in sorted(grouped.items()):
        if set(g)!={'oracle','nla'}:
            audit['unmatched_'+next(iter(g))]+=1;continue
        audit['identity_intersection']+=1
        for reader in ('oracle','nla'):
            if g[reader]['class'] is None:audit['UNPARSEABLE_'+reader]+=1
        if any(g[r]['class'] is None for r in ('oracle','nla')):
            audit['excluded_either_UNPARSEABLE']+=1;continue
        require(g['oracle']['cluster']==g['nla']['cluster'],'shared cluster')
        paired.append(dict(bank=key[0],unit=key[1],cluster=g['oracle']['cluster'],oracle=g['oracle']['class'],nla=g['nla']['class']))
    return paired,dict(audit)
def point(pairs):
    n=len(pairs);agree=[p for p in pairs if p['oracle']==p['nla']];reports=[p for p in agree if p['oracle']!='no mention'];disagree=[p for p in pairs if p['oracle']!=p['nla']]
    out={'n':n,'agreement':fraction(len(agree),n),'P_correct_given_agree_both_mention':fraction(sum(p['oracle']=='correct' for p in reports),len(reports)),
         'confusion':{a:{b:sum(p['oracle']==a and p['nla']==b for p in pairs) for b in CLASSES} for a in CLASSES},
         'disagreements':{'n':len(disagree),'oracle_right':sum(p['oracle']=='correct' for p in disagree),'nla_right':sum(p['nla']=='correct' for p in disagree),'neither_right':sum(p['oracle']!='correct' and p['nla']!='correct' for p in disagree)},
         'ensemble':{'precision':fraction(sum(p['oracle']=='correct' for p in reports),len(reports)),'coverage':fraction(len(reports),n)},'readers':{}}
    for r in ('oracle','nla'):
        correct=sum(p[r]=='correct' for p in pairs);mentioned=sum(p[r]!='no mention' for p in pairs)
        out['readers'][r]={'precision':fraction(correct,mentioned),'coverage':fraction(mentioned,n),'marginal_accuracy':fraction(correct,n)}
    precision=out['ensemble']['precision']['rate'];best=max((out['readers'][r]['marginal_accuracy']['rate'] for r in ('oracle','nla')),default=None) if n else None
    delta=None if precision is None else precision-best
    out['H_A1']={'difference':delta,'hypothesis':'conditional correct exceeds better marginal accuracy by >=0.10','status':'NOT EVALUABLE' if delta is None else 'MET' if delta>=.1-1e-12 else 'NOT MET','decision_rule':False}
    return out
def summarize(pairs,draws=2000):
    out=point(pairs);groups=sorted({p['cluster'] for p in pairs});ci=[]
    if groups:
        # Six sufficient counts; bootstrap all occurrences of a source item together.
        table=np.zeros((len(groups),6),dtype=int);ix={g:i for i,g in enumerate(groups)}
        for p in pairs:
            report=p['oracle']==p['nla'] and p['oracle']!='no mention'
            table[ix[p['cluster']]]+=np.array([1,p['oracle']=='correct',p['nla']=='correct',report,report and p['oracle']=='correct',0],dtype=int)
        rng=np.random.default_rng(20261028)
        for _ in range(draws):
            t=table[rng.integers(0,len(groups),len(groups))].sum(axis=0)
            if t[3]:ci.append(t[4]/t[3]-max(t[1],t[2])/t[0])
    out['H_A1'].update(CI95=np.quantile(ci,[.025,.975]).tolist() if ci else None,bootstrap_draws=draws,undefined_draws=draws-len(ci),cluster_count=len(groups),seed=20261028)
    return out
