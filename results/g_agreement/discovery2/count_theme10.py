"""Aggregate-only recount of sealed E75 Qwen results; no scorer is rerun."""
import hashlib
import json
from pathlib import Path
from evidence_native import load_native
from evidence_positions import load_e73_records
from evidence_e67 import load_e67

BASE=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wtext/results/g_agreement/understand/e75')

def main():
    seal=json.loads((BASE/'QWEN_RESULT_SEAL.json').read_text())
    assert seal['status']=='COMPLETE_ONCE'
    for name,digest in seal['files'].items():
        assert hashlib.sha256((BASE/name).read_bytes()).hexdigest()==digest
    result=json.loads((BASE/'QWEN_RESULTS.json').read_text())
    readers=result['panels']['primary']['all_units']['results']
    lookup={a['reader']:{(x['bank'],x['row']):x for x in a['rows']} for a in readers}
    assert all(k[0] in {'E56','E57','E59','E62','E73'} for p in lookup.values() for k in p)
    common=set(lookup['oracle'])&set(lookup['nla'])
    O=lookup['oracle'];N=lookup['nla']
    out={'common_units':len(common),
         'same_forecast':sum(O[k]['j_prediction']==N[k]['j_prediction'] for k in common),
         'same_binary_outcome':sum(O[k]['truth']==N[k]['truth'] for k in common),
         'both_reported':sum(O[k]['truth']==N[k]['truth']=='REPORTED' for k in common),
         'both_missed':sum(O[k]['truth']==N[k]['truth']=='MISSED' for k in common),
         'oracle_only_reported':sum(O[k]['truth']=='REPORTED' and N[k]['truth']=='MISSED' for k in common),
         'nla_only_reported':sum(N[k]['truth']=='REPORTED' and O[k]['truth']=='MISSED' for k in common),
         'common_marginal_reported':{r:sum(lookup[r][k]['truth']=='REPORTED' for k in common) for r in lookup},
         'shared_forecast_errors':sum(O[k]['truth']!=O[k]['j_prediction'] and N[k]['truth']!=N[k]['j_prediction'] for k in common),
         'common_errors':{r:sum(lookup[r][k]['truth']!=lookup[r][k]['j_prediction'] for k in common) for r in lookup},
         'absolute_S_gap_at_least_020':sum(abs(O[k]['S']-N[k]['S'])>=.2 for k in common),
         'same_binary_but_absolute_S_gap_at_least_020':sum(O[k]['truth']==N[k]['truth'] and abs(O[k]['S']-N[k]['S'])>=.2 for k in common),
         'largest_absolute_S_gap':max(abs(O[k]['S']-N[k]['S']) for k in common),
         'full_cohorts':{a['reader']:{'n':a['n'],'forecast_correct':sum(x['truth']==x['j_prediction'] for x in a['rows']),'balanced_accuracy':a['J_balanced_accuracy'],'registered_status':a['R_P1_status']} for a in readers}}
    examples={
        'ff1667317f41fed7af43eadc21ddf6c7':"Q&A format established: a sentence is given as context, followed by a question about the next word's part of speech, expecting a direct answer.",
        '01c1227e7e2480ac8c220bab87a753e3':'- , effectively doing nothing, as this is the base class.',
        '00ec451cddbb04c0441b696d7da2ec14':'Wikipedia-style article structure with detailed song history, following a pattern of factual chronological narrative about "Give It Up" by Fergie.'}
    public=load_native('E56')+load_e73_records()
    texts={x['opaque_id']:x['text'] for x in public}
    for opaque,excerpt in examples.items():assert excerpt in texts[opaque]
    out['verified_public_excerpts']=len(examples)
    w1={x['id'] for x in load_e67(1)}
    w2={x['id'] for x in load_e67(2)}
    out['wave2_opaque_ids_reused_in_wave1']={'k':len(w1&w2),'n':len(w2)}
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
