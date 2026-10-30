"""Aggregate-only paired recount of already-sealed native outputs; run python -B.

The private joins returned by helpers stay in memory. This is not an experiment
rerun, and it does not modify any source, judgment, label, or sealed result.
"""
import json
from collections import Counter, defaultdict
from evidence_native import load_native
from evidence_positions import load_e73_records

def code(r):
    j=r['judge'] or {}
    return j.get('code',j) or {}

def valid(r):
    return code(r).get('category') in ('silent','states_value','names_property_without_value','exhibits')

def score(r):
    c=code(r)
    if c.get('category')!='states_value' or len(c.get('values',[]))!=1:
        return 0
    t=r['_truth']
    t='AB'[t] if type(t) is int else t
    return 1 if c['values']==[t] else -1

def paired_summary(records):
    pairs=defaultdict(dict)
    for r in records:
        if r.get('kind','text')!='text':
            continue
        pairs[(r.get('feature',r.get('row')),r['pair_id'])][r['reader']]=r
    result={}
    for (f,_),v in pairs.items():
        s=result.setdefault(f,Counter())
        s['all_pairs']+=1
        assert set(v)=={'oracle','nla'}
        if not all(valid(r) for r in v.values()):
            s['excluded_either_unparseable']+=1
            continue
        s['common_parseable']+=1
        a,b=score(v['oracle']),score(v['nla'])
        s['oracle_correct']+=a==1;s['oracle_wrong']+=a==-1
        s['nla_correct']+=b==1;s['nla_wrong']+=b==-1
        s['both_correct' if a==b==1 else 'oracle_only_correct' if a==1 else 'nla_only_correct' if b==1 else 'neither_correct']+=1
        s['nla_more_whitespace_words']+=len(v['nla']['text'].split())>len(v['oracle']['text'].split())
    return result

def main():
    e57=load_native('E57',include_private=True)
    e73=load_e73_records()
    result={'E57':paired_summary(e57),'E73':paired_summary(e73)}
    w7=[r for r in e73 if r['row']=='W7']
    result['W7_full_judge_status']={str(k):v for k,v in Counter((r['reader'],r['judge']['status']) for r in w7).items()}
    result['W7_full_states_value']={reader:sum(valid(r) and code(r).get('category')=='states_value' for r in w7 if r['reader']==reader) for reader in ('oracle','nla')}
    cp=defaultdict(dict)
    for r in e57:
        if r['feature']=='clause_pending':cp[r['pair_id']][r['reader']]=r
    common=[v for v in cp.values() if all(valid(r) for r in v.values())]
    result['clause_pending_common_wording']={}
    for reader in ('oracle','nla'):
        rs=[v[reader] for v in common]
        result['clause_pending_common_wording'][reader]={
            'n':len(rs),'although':sum('although' in r['text'].lower() for r in rs),
            'main_clause_words':sum('main clause' in r['text'].lower() for r in rs),
            'single_main_clause_owed':sum(code(r).get('values')==['A'] for r in rs),
            'single_value':sum(len(code(r).get('values',[]))==1 for r in rs)}
    assert result['E57']['category_switch']['nla_only_correct']==23
    assert result['E57']['category_switch']['oracle_only_correct']==3
    assert result['E57']['clause_pending']['nla_wrong']==21
    assert result['E57']['subject_number']['both_correct']==6
    assert result['E73']['W7']['common_parseable']==94
    assert result['E73']['W7']['nla_correct']==87
    assert result['E73']['W7']['oracle_correct']==84
    print(json.dumps(result,indent=2,sort_keys=True))

if __name__=='__main__':main()
