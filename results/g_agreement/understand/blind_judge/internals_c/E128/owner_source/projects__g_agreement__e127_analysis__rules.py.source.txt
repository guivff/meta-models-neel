"""§236 R-NAT1/falsifier; context-update flips, original rubric, no hook."""
from .common import require,state,rate,criterion,rule
CONDITIONS=('context_update','neutral_prefix','no_prefix')
LAYERS=(44,52,60)


def analyze(records):
    require(len(records)==84 and len({x['item_id']for x in records})==84,'original84 fact_recall items')
    flipped=[];unknown=[]
    for x in records:
        require(x['old_value'] in ('A','B') and x['new_value'] in ('A','B') and x['old_value']!=x['new_value'],'frozen old/new value orientation')
        require(set(x['conditions'])==set(CONDITIONS),'exact three conditions')
        for c in CONDITIONS:
            z=x['conditions'][c];require(z['answer'] in ('old','new','other',None) and set(z['oracle'])==set(LAYERS),'original greedy answer and all three read layers')
        a=x['conditions']['context_update']['answer'];b=x['conditions']['no_prefix']['answer']
        if a=='new' and b=='old':flipped.append(x)
        elif a is None or b is None:unknown.append(x['item_id'])
    def report(xs):
        return {c:{str(l):{name:rate([state(x['conditions'][c]['oracle'][l],x[name+'_value'])for x in xs])for name in ('old','new')}for l in LAYERS}for c in CONDITIONS}
    selected=report(flipped);all_items=report(records)
    informative=len(flipped)>=50
    primary=[criterion(selected['context_update']['44']['old'],.50,.35),criterion(selected['context_update']['60']['new'],.70),criterion(selected['neutral_prefix']['44']['old'],.80)]
    falsifier=[criterion(selected['context_update']['44']['new'],.70,.55)]
    return dict(experiment='E127',flipped_n=len(flipped),planned_n=84,behaviour_unknown_n=len(unknown),informative=informative,
                flipped_set_definition='context_update answer new AND no_prefix answer old; no readout-based selection',
                R_NAT1=rule(primary)if informative else 'DESCRIPTIVE ONLY',falsifier=rule(falsifier)if informative else 'DESCRIPTIVE ONLY',
                reading='context update did not take'if not informative else 'staleness replicates without a steer'if rule(primary)=='MET'else 'block44 is current under natural update; late-formed-state caveat'if rule(falsifier)=='MET'else 'mixed outcome; report per-block rates',
                flipped_set_rates=selected,all84_descriptive=all_items,
                neutral_control_population='same behaviour-flipped set as R-NAT1; direct Guiv clarification before output',
                behaviour={c:{v:sum(x['conditions'][c]['answer']==(None if v=='missing' else v) for x in records)for v in ('old','new','other','missing')}for c in CONDITIONS},
                rubric='original E104/E109 categorical states_value exclusive old/new; neither and dual reports score0; UNPARSEABLE staysmissing',
                missing_policy='common original E104 convention: missing excluded only from affected rate denominator, planned/missing counts explicit; no zero/imputation/complete-case filter',
                intervals='common.stats Wilson95 z1.96; registered strict lower bounds, no additional CI gate on60/neutral')
