"""§233 E123 note1: POST HOC descriptions, no change to registered R-DIS1."""
from .rules import CONDITIONS,values,stale,disagreement,fraction,require
LABEL='POST HOC EXPLORATORY — E123 note1 (2e3ac01db)'


def consensus_ids(rows):
    """Original E121 paired class records only; never select using E123 outcomes."""
    require(len(rows)==336,'original E121336 records')
    by={}
    for x in rows:
        key=(x['item_id'],x['condition'],x['reader'])
        require(key not in by,'unique original E121 identity');by[key]=x['class']
    ids={x['item_id']for x in rows}
    require(len(ids)==84 and set(by)=={(i,c,r)for i in ids for c in ('steered','random')for r in ('oracle','nla')},'original E121 full84paired census')
    chosen={i for i in ids if by[i,'steered','oracle']==by[i,'steered','nla']=='wrong'}
    require(len(chosen)==35,'exact frozen35 E121 false-consensus items')
    return chosen


def later(records):
    result={}
    for condition in CONDITIONS:
        scored=[stale(x['conditions'][condition]['52'],('B'if x['old_value']=='A'else'A')if condition=='steered'else x['old_value'])for x in records]
        kept=[v for v in scored if v is not None]
        result[condition]=dict(fraction(sum(kept),len(kept)),planned_n=len(records),missing_n=len(records)-len(kept),target='new'if condition=='steered'else'old')
    return dict(label=LABEL,layer=52,conditions=result,missing_policy='affected rate only; missing is not incorrect/zero')


def operating(records):
    positives=[];negatives=[];positive_missing=0;positive_planned=0;unknown_stale=0;coverage={}
    for c in CONDITIONS:
        counts=dict(planned_n=len(records),parseable_pairs=0,both_state=0,one_states=0,neither_states=0,missing_pairs=0)
        for x in records:
            cc=x['conditions'][c];a,b=values(cc['44']),values(cc['52']);d=disagreement(cc['44'],cc['52'])
            if d is None:counts['missing_pairs']+=1
            else:
                counts['parseable_pairs']+=1
                counts['both_state'if bool(a)and bool(b)else'one_states'if bool(a)or bool(b)else'neither_states']+=1
            if c=='steered':
                target=stale(cc['44'],x['old_value']);unknown_stale+=target is None
                if target==1:
                    positive_planned+=1
                    if d is None:positive_missing+=1
                    else:positives.append(d)
            elif c=='unhooked'and d is not None:negatives.append(d)
        coverage[c]=dict(counts,observed_coverage=fraction(counts['both_state'],len(records)),coverage_given_parseable=fraction(counts['both_state'],counts['parseable_pairs']),
                         abstention_counts=dict(missing_pair=counts['missing_pairs'],no_value_either=counts['neither_states'],only_one_value=counts['one_states']))
    tp=sum(positives);fp=sum(negatives)
    return dict(label=LABEL,sensitivity=fraction(tp,len(positives)),unhooked_false_positive_rate=fraction(fp,len(negatives)),precision=fraction(tp,tp+fp),
                TP=tp,FP=fp,FN=len(positives)-tp,TN=len(negatives)-fp,known_stale_planned_n=positive_planned,stale_pair_missing_n=positive_missing,unknown_stale44_n=unknown_stale,
                unhooked_planned_n=len(records),unhooked_missing_n=len(records)-len(negatives),coverage=coverage,
                population='registered stale-steered positives plus all unhooked negatives; precision describes this sample mixture, not deployment prevalence',
                abstention_policy='missing pairs abstain, never zero; one-value and no-value pairs retain registered disagreement signal; coverage does not filter detector scoring',threshold='registered unequal stated-value sets, unchanged')


def analyze(data,false_consensus):
    require(len(false_consensus)==35 and set(false_consensus)<={x['item_id']for x in data['fact_recall']},'original35 source IDs joined unchanged')
    subset=[x for x in data['fact_recall']if x['item_id']in false_consensus]
    ds=[disagreement(x['conditions']['steered']['44'],x['conditions']['steered']['52'])for x in subset];kept=[v for v in ds if v is not None]
    return dict(label=LABEL,registered_R_DIS1='UNCHANGED',
        false_consensus35=dict(label=LABEL,row='fact_recall',condition='steered',planned_n=35,missing_n=35-len(kept),disagreement=fraction(sum(kept),len(kept)),source='original sealed E121 ff2b4dd8e Oracle44/NLA42 old-value agreement; E109 Oracle44/52 judgments'),
        block52_alone=dict(label=LABEL,same_false_consensus35=later(subset),full_registered_cohorts={row:later(xs)for row,xs in data.items()}),
        operating_point=dict(label=LABEL,rows={row:operating(xs)for row,xs in data.items()}))
