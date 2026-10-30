"""Aggregate-only polarity recount on sealed E49/E57; no experimental writes.

Run with python -B. Private labels/prompts remain in memory. Excerpts are public.
"""
import json
import re
from evidence_native import load_native

EDITORIAL=r'\b(?:wrong|incorrect|flawed|violat\w*|impossible|illogical|inconsisten\w*|unrealistic|contradic\w*)\b'
HYPOTHETICAL=r'\b(?:hypothetical|counterfactual\w*|suppos\w*)\b'
ERROR_FRAME=r'\b(?:wrong|incorrect|flawed)\b'
FINAL_QUOTE=r'Final (?:fragment|token) ["“]([^"”]*)["”]'
FORECAST=r'(?:next (?:token|word)[^\n.]{0,180}|must (?:be|complete|conclude)[^\n.]{0,100}|expected continuation[^\n.]{0,100})\b(?:birds?|avian)\b'
EXAMPLES={
    'f8c61dc25adf639bb30b2274':'it is not the case that following the timestamp entry the safety interlock was disabled',
    '9f0a30e49cfd308ff3af529a':'Final fragment "it is not the case that after the calibration sequence was completed the safety interlock was disabled"',
    '8518be4fc6093e1e2e7af473':'This violates chronological integrity. A proper log would state:',
    '6c8c52f2717fc4f3552843af':'The "counterfactual" logic puzzle format: the text contrasts correct/incorrect document types,',
    'c72764bc209e13e08a0759e3':'The "counterfactual" logic puzzle format (from the earlier "if...then" clause)',
    '3311e169d2ddd3bde274b202':'The "incorrect" example demonstrates a deliberate topic-switching error,',
    '1a4b0b8a51940bb2323a6eb8136782fa':'which must be completed with "birds" to mirror the opening constraint exactly,',
    'c5f40d2bae0579ada2b482bb9f2e8797':'the next token must complete this phrase, almost certainly "birds" echoing the opening instruction,',
    '1026b33c917f35d645dd65da0fc57e78':'the next word should reference birds/avian creatures, completing the thematic callback to the opening constraint about avoiding bird-related thoughts.',
}

def has(pattern,row):return bool(re.search(pattern,row['text'],re.I))

def main():
    e49=load_native('E49',True)
    e57=load_native('E57',True)
    allrows={x['opaque_id']:x for x in e49+e57}
    for oid,excerpt in EXAMPLES.items():assert excerpt in allrows[oid]['text'],oid
    result={'excerpt_substring_checks':len(EXAMPLES),'E49':{},'E57':{}}
    for feature in ['negation_scope','asserted_vs_hypothetical']:
        summary={}
        for reader in ['oracle','nla']:
            a=[x for x in e49 if x['feature']==feature and x['reader']==reader]
            summary[reader]={}
            for label in ['A','B']:
                group=[x for x in a if x['_truth']==label]
                summary[reader][label]={'n':len(group),'not_the_case':sum(has(r'\bnot the case\b',x) for x in group),
                    'editorial':sum(has(EDITORIAL,x) for x in group),'hypothetical_word':sum(has(HYPOTHETICAL,x) for x in group),
                    'error_frame':sum(has(ERROR_FRAME,x) for x in group)}
            if feature=='asserted_vs_hypothetical':
                quotes=[m[1] for x in a if (m:=re.search(FINAL_QUOTE,x['text']))]
                summary[reader]['final_quotes']={'n':len(quotes),'scope_marked':sum(bool(re.search(HYPOTHETICAL,t,re.I)) for t in quotes)}
        result['E49'][feature]=summary
    a=[x for x in e49 if x['feature']=='negation_scope' and x['reader']=='nla']
    result['E49']['both_negation_markers_in_prompt']={'k':sum(all(t in x['_prompt'] for t in ['It is false that','It is clear that']) for x in a),'n':len(a)}
    a=[x for x in e49 if x['feature']=='asserted_vs_hypothetical' and x['reader']=='nla']
    result['E49']['both_modality_markers_in_prompt']={'k':sum(all(t in x['_prompt'] for t in ['It is the case that','Suppose, counterfactually, that']) for x in a),'n':len(a)}
    for reader in ['oracle','nla']:
        a=[x for x in e57 if x['feature']=='focus_ignore' and x['reader']==reader]
        hits=[x for x in a if has(FORECAST,x) and has(r'do not think|without thinking|avoid thinking',x)]
        result['E57'][reader]={'n':len(a),'negative_instruction_plus_forecast':len(hits),
            'judge_states_value_within_hits':sum(x['judge']['category']=='states_value' for x in hits)}
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
