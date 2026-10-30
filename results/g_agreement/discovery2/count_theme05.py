"""Exploratory aggregate counts only; no model calls, saved joins, or experiment writes."""
import json
import re
from evidence_e67 import load_e67, load_e76

FEATURES={
    'quoted_span':r'["“][^"”\n]{8,}["”]',
    'hedge':r'\b(likely|probably|perhaps|possibly|might|may|could)\b',
    'quoted_final':r'(?:final|last) (?:token|fragment|word|phrase)[^\n]{0,30}["`“]',
}
def has(x,f):return bool(re.search(FEATURES[f],x['text'],re.I))
def contrad(x):return any(c['verdict']=='CONTRADICTED' for c in x['claims'])
def supported(x):return any(c['verdict']=='SUPPORTED' for c in x['claims'])
def count(a):return {'k_contradicted':sum(map(contrad,a)),'n':len(a)}
def main():
    out={'analysis':'post-hoc hypotheses; any contradicted claim per readout; matched only; waves separate','waves':{}}
    for w in (1,2):
        d=[x for x in load_e67(w) if x['condition']=='matched']
        result={}
        for r in ['oracle','nla']:
            a=[x for x in d if x['reader']==r]
            result[r]={'baseline':count(a),'mixed':{'k_supported_and_contradicted':sum(supported(x) and contrad(x) for x in a),'n':len(a),'n_with_support':sum(map(supported,a))},'features':{}}
            for f in FEATURES:
                result[r]['features'][f]={'present':count([x for x in a if has(x,f)]),'absent':count([x for x in a if not has(x,f)])}
            result[r]['by_bank']={b:count([x for x in a if x['bank']==b]) for b in sorted(set(x['bank'] for x in a))}
        a=[x for x in d if x['reader']=='oracle']
        result['oracle']['quote_by_bank']={b:{'present':count([x for x in a if x['bank']==b and has(x,'quoted_span')]),'absent':count([x for x in a if x['bank']==b and not has(x,'quoted_span')])} for b in sorted(set(x['bank'] for x in a))}
        result['oracle']['quote_with_exactly_two_claims']={v:count([x for x in a if len(x['claims'])==2 and has(x,'quoted_span')==(v=='present')]) for v in ('present','absent')}
        out['waves'][w]=result
    placebo=load_e76()
    out['E76']={r:{p:{f:{'k':sum(has(x,f) for x in placebo if x['reader']==r and x['arm']==p),'n':500} for f in FEATURES} for p in ('random','shuffled')} for r in ('oracle','nla')}
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()
