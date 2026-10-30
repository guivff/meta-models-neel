"""Local descriptive counts only. Read sealed evidence; never rerun its scorer.

Prints aggregate audit counts. Run with python -B from this directory.
"""
import json
import re
from collections import Counter
from evidence_native import load_native

TYPE = re.compile(r'\bx\s+(?:is|becomes)(?:\s+now)?\s+(?:a\s+)?(?:string|int(?:eger)?)\b', re.I)
CITRUS = re.compile(r'citrus|orange|lemon|lime|grapefruit|tangerine|pomelo|柑橘|柠檬|橙', re.I)

def counts():
    result={}
    r=[x for x in load_native('E49') if x['feature']=='var_type_at_use']
    result['E49_type_expression_candidates']={reader:{'k':sum(bool(TYPE.search(x['text'])) for x in r if x['reader']==reader),'n':sum(x['reader']==reader for x in r)} for reader in ('oracle','nla')}
    r=[x for x in load_native('E62') if x['feature'].endswith('_L4')]
    h=[x for x in r if x['judge']['category']=='states_value']
    result['E62_L4']={'n':len(r),'states_value':len(h),'all_A':sum(x['judge']['values']==['A'] for x in h),'A_in_evidence':sum(bool(re.search(r'\bA\b',x['judge']['evidence'])) for x in h),'single_word_evidence':sum('single-word' in x['judge']['evidence'] for x in h),'entailment_evidence':sum('entails' in x['judge']['evidence'] for x in h)}
    result['generic_fruit_credited_as_citrus']={}
    for bank in ('E56','E57'):
        r=[x for x in load_native(bank) if x['values'] and any('citrus' in str(v).lower() for v in x['values'].values())]
        by_reader={}
        for reader in ('oracle','nla'):
            rs=[x for x in r if x['reader']==reader]
            h=[]
            for x in rs:
                j=x['judge'];letters=[k for k,v in x['values'].items() if 'citrus' in str(v).lower()]
                if j and j['category']=='states_value' and any(k in j['values'] for k in letters) and re.search('fruit',x['text'],re.I) and not CITRUS.search(x['text']):h.append(x)
            focus=[x for x in rs if x['feature']=='focus_ignore']
            by_reader[reader]={'k':len(h),'n_all_focus_rows':len(rs),'rows':dict(Counter(x['feature'] for x in h)),'focus_ignore_n':len(focus),'focus_ignore_states_value':sum(x['judge']['category']=='states_value' for x in focus)}
        result['generic_fruit_credited_as_citrus'][bank]=by_reader
    return result

if __name__=='__main__':
    print(json.dumps(counts(),indent=2))
