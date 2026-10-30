"""09494e79: adapter copy of sealed E57 compute; preserve S when G3 is missing."""
from analysis57 import *
from missingness import rate,signed_value,reported

def compute(data,jj,jrows):
    private=data['private'];plan=data['plan'];probe=probe_aucs(data);rates={};native=data['native'];groups={}
    for x in native:groups.setdefault((x['reader'],x['unit_id']),[]).append(x)
    for reader in ('oracle','nla'):
        for row in plan['rows']:
            if not plan['rows'][row]['probe_applicable']:continue
            matrix=[[signed_value(jj[x['id']],private[k]['label']) for x in sorted(groups[reader,k],key=lambda x:x['repeat'])] for k in plan['native_ids'][row]]
            rates[reader,row]=rate(matrix)
    eligible=[r for r in GROUP_B if probe[r]>=.90]
    out={'probe_gate':{r:probe[r]>=.90 for r in GROUP_B},'rates':{'|'.join(k):v for k,v in rates.items()},'J_rows':jrows,'readers':{},'R_B':{}}
    j_non=sum(jrows[r]['J_label'] in ('OUT-J','DIFFUSE') for r in eligible);j_in=sum(jrows[r]['J_label']=='IN-J' for r in eligible)
    reports={reader:sum(reported(rates[reader,r]) for r in eligible) for reader in ('oracle','nla')}
    out['R_B']={'eligible':eligible,'out_or_diffuse':j_non,'IN_J':j_in,'reporting_rows':reports,'verdict':'MET' if j_non>=5 and all(v<=2 for v in reports.values()) else 'NOT MET','falsifier':j_in>=5 or any(v>=5 for v in reports.values())}
    if any(rates[reader,r]['S'] is None for reader in ('oracle','nla') for r in eligible):
        out['R_B'].update(verdict='NOT EVALUABLE',falsifier='NOT EVALUABLE',reason='no parseable judgments in an eligible row')
    # Recompute counts from raw readouts; worker counts must agree exactly.
    counted=[]
    for (reader,k),xs in sorted(groups.items()):
        if private[k]['feature'] in ('category_switch','capacity_list'):counted.append(count_item(xs,plan['count_metadata'][k]))
    require(sorted(data['counts'],key=lambda x:(x['reader'],x['unit_id']))==counted,'count file differs from frozen raw-text calculation')
    for reader in ('oracle','nla'):
        r=rates[reader,'multi_token_entity'];g3=jrows['multi_token_entity']['G3_AUROC'];a1=None if g3 is None or r['S'] is None else reported(r) and g3<=.65
        mention={};bykey={}
        for arm in ('think','mention','ignore','none'):
            row='focus_'+arm;values={}
            for k in plan['native_ids'][row]:
                x=private[k];key=(x['template_index'],x['filler_index'],x['variant']);texts=groups[reader,k]
                hits=[named_terms(z['text'],{'birds':['bird','birds'],'citrus':['citrus']},'word_exact_casefold') for z in texts]
                if arm=='none':values[key]=sum((int('birds' in h)+int('citrus' in h))/2 for h in hits)/1
                else:
                    concept='birds' if x['label']==1 else 'citrus';values[key]=sum(concept in h for h in hits)/1
            bykey[arm]=values;mention[arm]=float(np.mean(list(values.values())))
        keys=sorted(bykey['think']);require(all(set(v)==set(keys) for v in bykey.values()),'matched focus items')
        ci=paired_ci([bykey['think'][k] for k in keys],[bykey['none'][k] for k in keys])
        ordered=mention['think']>=mention['mention']>mention['ignore']>mention['none']
        c=[x for x in counted if x['reader']==reader and x['feature']=='category_switch']
        switch=float(np.mean([x['any_mention_rate'] for x in c if private[x['unit_id']]['label']==1]));stay=float(np.mean([x['any_mention_rate'] for x in c if private[x['unit_id']]['label']==0]));drop=None if stay==0 else 1-switch/stay
        capacity=[x for x in counted if x['reader']==reader and x['feature']=='capacity_list'];mean_union=float(np.mean([x['distinct_over_readouts'] for x in capacity]));mean_one=float(np.mean([x['mean_distinct_per_readout'] for x in capacity]))
        cap_j=jrows['capacity_list']['top50_list_nouns'];j_counts=[]
        for x in capacity:
            k=x['unit_id'];nouns=cap_j[k];require(len(nouns)==len(set(nouns)) and set(nouns)<=set(plan['count_metadata'][k]['list_nouns']),'J top50 listed-noun identity');j_counts.append(len(nouns))
        out['readers'][reader]={'R_A1': 'NOT EVALUABLE' if a1 is None else 'MET' if a1 else 'NOT MET','R_A2': 'MET' if ordered and ci[0]>0 else 'NOT MET','focus_mention_rates':mention,'think_minus_none_CI95':ci,'category_switch':{'switch':switch,'stay':stay,'fraction_drop':drop,'tracks_workspace':None if drop is None else drop>=.5,'reads_beyond':None if drop is None else drop<=.2},'capacity':{'mean_union_over_readouts':mean_union,'mean_distinct_per_readout':mean_one,'union_beyond_six':mean_union>6,'per_readout_beyond_six':mean_one>6,'J_top50_mean':float(np.mean(j_counts))},'count_gradient':{row:rates[reader,row] for row in ('linewrap_implicit','linewrap_asked','count_gradient_first_letter')}}
    if jrows['multi_token_entity']['G3_AUROC'] is None:
        out['R_A1_limitation']='09494e79: J-lens has no single-token readout of these values by construction; G3 is missing, not zero. Reader S remains in rates.'
    return out,counted
