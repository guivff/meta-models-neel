"""Future CPU filter only; not invoked on real answers during packet preparation."""
from projects.g_agreement.answer_binding236.classifier import classify


def select_on_unprefixed(labels,records):
    expected={x['condition_ids']['none']:x for x in labels}
    by={}
    for r in records:
        if r['id']not in expected or r['id']in by:raise ValueError('unique unprefixed candidate answers only')
        if r.get('greedy_max_new_tokens')!=3 or not isinstance(r.get('text'),str):
            raise ValueError('original raw three-token greedy answer')
        ids=r.get('token_ids')
        if not isinstance(ids,list)or not 1<=len(ids)<=3 or any(type(t)is not int or t<0 for t in ids):
            raise ValueError('original raw greedy token IDs')
        by[r['id']]=r
    chosen=[];counts=dict(old=0,new=0,neither=0,missing=0)
    # Stored seeded rank is immutable; never sort by logits, prefix flips or readers.
    if [x['rank']for x in labels]!=list(range(len(labels))):raise ValueError('frozen source rank')
    for x in labels:
        r=by.get(x['condition_ids']['none'])
        if r is None:counts['missing']+=1;continue
        answer=classify(r['text'],x['old_value'],x['new_value']);counts[answer]+=1
        if answer=='old'and len(chosen)<84:chosen.append(x['base_id'])
    return dict(status='84_SELECTED'if len(chosen)==84 else 'INSUFFICIENT_CORRECT_UNPREFIXED_ANSWERS',
                selected_base_ids=chosen,selected_n=len(chosen),candidate_n=len(labels),counts=counts,
                selection='first84 confirmed OLD=true in frozen seeded order; missing not treated as wrong')
