"""Local, read-only discovery recount. Run with python -B.

Only aggregate counts are returned. Source prompts and per-item labels stay in memory.
"""
import json
import re
from collections import Counter
from pathlib import Path
from evidence_native import load_native, read, RESULTS


def count_all():
    out={}
    arithmetic=[x for x in load_native('E49',True) if x['feature']=='arith_carry']
    by_reader={}
    for reader in ('oracle','nla'):
        rows=[x for x in arithmetic if x['reader']==reader]
        c=Counter(n=len(rows))
        for x in rows:
            actual=tuple(map(int,re.search(r'(\d+)\s*\+\s*(\d+)\s*=',x['_prompt']).groups()))
            equations=set(tuple(map(int,q)) for q in re.findall(r'(\d+)\s*\+\s*(\d+)\s*=',x['text']))
            nums=[int(n) for n in re.findall(r'\((\d+)\)',x['text'])]
            c['has_equation']+=bool(equations)
            c['actual_equation_order_insensitive']+=any(sorted(q)==sorted(actual) for q in equations)
            c['parenthetical_number']+=bool(nums)
            if equations and nums:
                c['equation_and_parenthetical_number']+=1
                c['number_matches_reconstructed_sum']+=any(n==sum(q) for n in nums for q in equations)
                c['number_matches_actual_sum']+=sum(actual) in nums
        by_reader[reader]=dict(c)
    out['arithmetic']=by_reader
    ladder=load_native('E62',True)
    by_state={}
    results=read(RESULTS/'e62/analysis402_once_2026-10-27/RESULTS.json')
    for state in ('S1','S2','S3','S4','S5'):
        rows=[x for x in ladder if x['feature']==state+'_L4']
        # Verify the public response-code design in the consumed prompts, without
        # releasing any item-to-code assignment or prompt.
        assert all(re.search(r'\balpha\b',x['_prompt'],re.I) and re.search(r'\bbeta\b',x['_prompt'],re.I) for x in rows)
        by_state[state]={
            'n':len(rows),
            'alpha_or_beta_literal':sum(bool(re.search(r'\b(?:alpha|beta)\b',x['text'],re.I)) for x in rows),
            'generic_classification_word':sum(bool(re.search(r'\b(?:yes|no|true|false|positive|negative|neutral)\b',x['text'],re.I)) for x in rows),
            'probe':rows[0]['probe'],
            'sealed_behaviour_auroc':results['behaviour']['AUROC'][state]}
    out['decision']=by_state
    plans=load_native('E59',True)
    grouped={}
    for feature in ('format_plan','hedge_plan','decline_plan'):
        for reader in ('oracle','nla'):
            rows=[x for x in plans if x['feature']==feature and x['reader']==reader]
            c=Counter(n=len(rows))
            for x in rows:
                vals=x['judge']['values'] if x['judge']['category']=='states_value' else []
                c['correct_only']+=len(vals)==1 and vals[0]==x['_truth']
                c['wrong_only']+=len(vals)==1 and vals[0]!=x['_truth']
                if feature=='decline_plan':
                    instruction='instructed_decline' if x['_truth']=='A' else 'instructed_answer'
                    c[instruction+'_n']+=1
                    c[instruction+'_answer_only']+=vals==['B']
                    c[instruction+'_decline_only']+=vals==['A']
            grouped[feature+'_'+reader]=dict(c)
    out['plans']=grouped
    return out


if __name__=='__main__':
    print(json.dumps(count_all(),indent=2,sort_keys=True))
