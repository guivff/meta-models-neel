"""§236 descriptive R-DOSE1; choose smallest dose by behaviour only."""
from projects.g_agreement.e127_analysis.common import require,state,rate,criterion,rule
DOSES=(2,4,8)
GREEDY_DOSES=(2,4)
CONDITIONS=('steered','random')
LAYERS=(44,52)


def analyze(records):
    require(len(records)==84 and len({x['item_id']for x in records})==84,'original84 fact_recall items')
    for x in records:
        require(x['old_value'] in ('A','B') and x['new_value'] in ('A','B') and x['old_value']!=x['new_value'],'original E104 old/target values')
        require(set(x['doses'])==set(DOSES),'two new doses plus original sealed8')
        for dose in DOSES:
            require(set(x['doses'][dose])==set(CONDITIONS),'steered plus same-dose random control')
            for c in CONDITIONS:
                z=x['doses'][dose][c];require(z['flipped'] is None or type(z['flipped'])is bool,'original behaviour flip, not readout')
                require(set(z['oracle'])==set(LAYERS),'both registered layers')
                if dose==8:require(z['flipped'] is None,'alpha8 greedy answers missing; never impute pair logits')
    counts={a:sum(x['doses'][a]['steered']['flipped'] is True for x in records)for a in DOSES}
    missing={a:sum(x['doses'][a]['steered']['flipped'] is None for x in records)for a in DOSES}
    selected=None;ambiguous=False
    for a in GREEDY_DOSES:
        if counts[a]>=42:selected=a;break
        if counts[a]+missing[a]>=42:ambiguous=True;break
    reports={}
    for a in DOSES:
        cohort=[x for x in records if x['doses'][a]['steered']['flipped'] is True]
        rates={c:{str(l):{name:rate([state(x['doses'][a][c]['oracle'][l],x[name+'_value'])for x in cohort])for name in ('old','new')}for l in LAYERS}for c in CONDITIONS}
        pattern=rule([criterion(rates['steered']['44']['old'],.50,.35),criterion(rates['steered']['52']['new'],.70)])
        reports[str(a)]=dict(flipped_n=None if a==8 else len(cohort),behaviour_missing_n=missing[a],flipped_set_rates=rates,descriptive_pattern=pattern,
                            random_behaviour_flipped_n=None if a==8 else sum(x['doses'][a]['random']['flipped'] is True for x in records),random_control_population='same steered-flipped cohort, not separately selected')
    if ambiguous:status='NOT EVALUABLE';reading='smallest qualifying dose unknown because lower-dose behaviour is missing'
    elif selected is None:status='NOT EVALUABLE';reading='the flip needs α = 8 (E104 sealed pair-logit result: 84/84, a different measure); retain strong-steer caveat'
    else:status=reports[str(selected)]['descriptive_pattern'];reading='staleness is not a large-dose artefact'if status=='MET'else 'report selected lower-dose outcome without changing the pre-stated rule'
    return dict(experiment='E128',descriptive=True,alpha_min=selected,selection_ambiguous=ambiguous,R_DOSE1=status,reading=reading,flip_counts={str(k):None if k==8 else v for k,v in counts.items()},planned_n=84,
                selection='smallest2/4 with>=42 greedy flips; alpha8 is never selected from pair logits or imputed greedy answers',doses=reports,
                alpha8_pair_logit_reference=dict(source='original sealed E104 CPU private SHA495bbb19179f507869779d611c737ac82181f8c404054fcffd6963b7615fd0e4',flipped_n=84,planned_n=84,measure='candidate-pair logit preference, DIFFERENT from greedy classifier',used_for_alpha_min=False),
                alpha8_source='original sealed E104 pair-preference behaviour is descriptive only; absent original greedy answers stay missing; original E104/E109 judgments unchanged, no alpha8 rerun/rejudge',
                rubric='original E104/E109 exclusive categorical old/new; terminal UNPARSEABLE missing',
                missing_policy='affected rate denominator only; planned/missing explicit, no missing-as-zero or silent complete-case cohort',
                intervals='common.stats Wilson95 z1.96; old44 lower strictly>.35; new52>=.70 without extra CI gate')
