"""Local, aggregate-only recount of sealed safety-framing evidence; no model calls."""
import json
import re
from collections import Counter
from evidence_native import load_native
from evidence_e54 import load_e54
from evidence_e66 import load_e66
from evidence_e67 import load_e67

SECURITY = r'\b(?:safety|alignment|jailbreak|malicious|deceptive|harmful)\b'
EVAL = r'evaluat|grader|judge|score|benchmark|rubric|test'

def hits(pattern, text):
    return bool(re.search(pattern, text, re.I))

def main():
    s6=[x for x in load_native('E62',True) if x['feature'].startswith('S6')]
    out={'interpretation':'post-hoc safety-framing hypotheses; private source comparisons remain in memory','E62':{}}
    for feature in sorted({x['feature'] for x in s6}):
        a=[x for x in s6 if x['feature']==feature]
        out['E62'][feature]={
            'n':len(a),
            'judge_eval_mention':sum(x['judge'].get('eval_mention') is True for x in a),
            'readout_followed_by_evaluation':sum('followed by an evaluation' in x['text'] for x in a),
            'readout_README':sum('README' in x['text'] for x in a),
            'readout_Python':sum('Python' in x['text'] for x in a),
            'source_README':sum('README' in x['_prompt'] for x in a),
            'source_Python':sum('Python' in x['_prompt'] for x in a),
            'source_eval_lexicon':sum(hits(EVAL,x['_prompt']) for x in a)}
    e54=load_e54(True)
    out['E54']={}
    for reader in ('oracle','nla'):
        out['E54'][reader]={}
        for feature in ('injection_awareness','reasoning_bridge'):
            a=[x for x in e54 if x['reader']==reader and x['feature']==feature]
            out['E54'][reader][feature]={
                'n':len(a),'security_frame':sum(hits(SECURITY,x['text']) for x in a),
                'source_security_frame':sum(hits(SECURITY,x['_prompt']) for x in a),
                'safety_word':sum(hits(r'\bsafety\b',x['text']) for x in a),
                'must_recognize_resist_ignore_reject':sum(hits(r'\bmust (?:recognize|resist|ignore|reject)',x['text']) for x in a)}
    matched=[x for x in load_e67(1) if x['condition']=='matched' and x['bank']=='E54' and x['row']=='injection_awareness']
    out['E67_wave1_own_prompt']={}
    for reader in ('oracle','nla'):
        a=[x for x in matched if x['reader']==reader]
        claims=[c for x in a for c in x['claims'] if hits(r'\bjailbreak\b',c['claim'])]
        out['E67_wave1_own_prompt'][reader]={'n_readouts':len(a),'n_jailbreak_claims':len(claims),'verdicts':dict(Counter(c['verdict'] for c in claims))}
    e66=load_e66()
    out['E66']={'n_all':len(e66),'n_kept':sum(x['judgment']['status']=='KEPT' for x in e66),
                'n_eval_flagged':sum((x['judgment'].get('code') or {}).get('eval_awareness') is True for x in e66)}
    print(json.dumps(out,indent=2))

if __name__=='__main__':
    main()
