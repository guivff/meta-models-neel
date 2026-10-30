"""Unchanged E133 classifier, original first42/42/16 pair screening."""
from projects.g_agreement.e133_analysis.screen import classify,MATCHER_SHA256
from projects.g_agreement.e127_analysis.common import require
KINDS=('D1','D2','one_hop');LIMITS=dict(D1=42,D2=42,one_hop=16)

def select(pairs,answers):
    require(len({p['pair_id']for p in pairs})==len(pairs),'unique original pair IDs')
    selected={k:[]for k in KINDS};rows=[];orders=set()
    for p in sorted(pairs,key=lambda x:x['generation_index']):
        kind=p['kind'];require(kind in KINDS,'original D1/D2/one-hop only')
        key=(kind,p['generation_index']);require(key not in orders,'unique original order');orders.add(key)
        ms=p['members'];require(len(ms)==2 and [m['member']for m in ms]==[0,1],'both original members')
        cur=[m['current']for m in ms];prev=[m['previous']for m in ms];require(len(set(cur))==2 and prev[0]==prev[1]and prev[0]not in cur,'original recipients and common previous')
        require(all(answers.get(m['item_id'])is None or answers[m['item_id']]['id']==m['item_id']for m in ms),'same original keyed answer IDs')
        correct=all(classify(answers.get(m['item_id']),cur+[prev[0]])==m['current']for m in ms)
        if correct and len(selected[kind])<LIMITS[kind]:selected[kind].append(p['pair_id'])
        rows.append(dict(pair_id=p['pair_id'],kind=kind,generation_index=p['generation_index'],correct_both=correct))
    counts={k:sum(x['correct_both']for x in rows if x['kind']==k)for k in KINDS}
    return dict(selected=selected,screening=rows,qualifying_counts=counts,classifier_sha256=MATCHER_SHA256,screen_only=counts['D1']<20 and counts['D2']<20)
