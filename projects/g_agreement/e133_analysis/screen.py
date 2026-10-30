"""Frozen 32-token screening: unchanged parse_target_answer, no reader-based selection."""
import hashlib
from pathlib import Path
from projects.g_agreement.core.analysis_utils import parse_target_answer
from projects.g_agreement.e127_analysis.common import require
MATCHER=Path(__file__).resolve().parents[1]/'core/analysis_utils.py'
MATCHER_SHA256=hashlib.sha256(MATCHER.read_bytes()).hexdigest()
KINDS=('multi_hop','one_hop')
ALL_KINDS=KINDS+('babi_qa2',)
LIMITS={'multi_hop':84,'one_hop':42,'babi_qa2':42}


def classify(record,candidates):
    require(len(candidates)==3 and len(set(candidates))==3 and all(isinstance(x,str)and x for x in candidates),'two frozen recipients plus distinct previous holder')
    if record is None:return None
    require(record['greedy_max_new_tokens']==32 and isinstance(record['text'],str)and isinstance(record['token_ids'],list)and len(record['token_ids'])<=32 and all(type(t)is int for t in record['token_ids']),'original registered32-token greedy text')
    return parse_target_answer({'primary':{'candidates':list(candidates),'answer':candidates[0]}},record['text'])


def select(pairs,answers):
    """First qualifying84/42 pairs in ORIGINAL generation order; both members correct."""
    require(len({p['pair_id']for p in pairs})==len(pairs),'unique source pairs')
    require(len({(p['kind'],p['generation_index'])for p in pairs})==len(pairs),'unique generation ordering')
    kinds=KINDS+(('babi_qa2',)if any(p['kind']=='babi_qa2'for p in pairs)else());selected={k:[] for k in kinds};rows=[]
    for p in sorted(pairs,key=lambda x:x['generation_index']):
        if p['kind']=='babi_qa3':
            rows.append(dict(pair_id=p['pair_id'],kind=p['kind'],generation_index=p['generation_index'],correct_both=False,selected=False,ineligible_reason='QA3 test asks previous location, not current; no rewritten question'));continue
        require(p['kind']in ALL_KINDS and type(p['generation_index'])is int,'frozen generation kind/order')
        if p['kind']=='babi_qa2':require(p['task']=='qa2'and p['source_split']=='test'and p.get('source_episode_id')is not None,'original QA2 test/current-location source and episode')
        require(len(p['members'])==2 and [m['member']for m in p['members']]==[0,1],'matched two-member pair')
        current=[m['current']for m in p['members']];previous=[m['previous']for m in p['members']]
        require(len(set(current))==2 and previous[0]==previous[1] and previous[0]not in current,'recipient-only pair and common previous holder')
        require(all(answers.get(m['item_id'])is None or answers[m['item_id']]['id']==m['item_id']for m in p['members']),'original keyed screening answer IDs; no order join')
        results=[classify(answers.get(m['item_id']),current+[previous[0]])for m in p['members']]
        correct=all(value==m['current']for value,m in zip(results,p['members']))
        admit=correct and len(selected[p['kind']])<LIMITS[p['kind']]
        if admit:selected[p['kind']].append(p['pair_id'])
        rows.append(dict(pair_id=p['pair_id'],kind=p['kind'],generation_index=p['generation_index'],source_episode_id=p.get('source_episode_id'),correct_both=correct,selected=admit,classified=results))
    return dict(selected=selected,qualifying_counts={k:sum(r['correct_both']for r in rows if r['kind']==k)for k in kinds},screening=rows,informative=len(selected['multi_hop'])>=50,selection='first84multi/42one in original generation order; both32-token greedy answers correct; no reader/probe/patch input',classifier_sha256=MATCHER_SHA256)
