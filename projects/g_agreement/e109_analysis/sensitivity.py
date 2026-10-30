"""79f63fe0 companion only: exclude redacted readout scores, retain paired grid."""
from .analysis import ROWS,LAYERS,READS,classify_rules
from projects.g_agreement.e104_analysis.rules import statistic

def sensitivity(data,primary,old44,affected):
    keys=[(x['row'],x['layer'],x['condition'],x['item_id']) for x in affected]
    if len(set(keys))!=len(keys):raise ValueError('duplicate redaction identity')
    for row,layer,condition,item in keys:
        if row not in ROWS or layer not in READS or condition not in ('steered','random') or item not in data[row]['test_ids']:raise ValueError('redaction outside original grid')
    marked=set(keys);out={};ps={};os={};cohort_affected=0
    for row in ROWS:
        d=data[row];ps[row]={l:primary['rows'][row][l]['probe']['steered']['estimate'] for l in LAYERS};os[row]={};out[row]={}
        for l in READS:
            scores={}
            for c in ('steered','random'):
                scores[c]={i:None if (row,l,c,i) in marked else d['layers'][l]['oracle'][c][j] for j,i in enumerate(d['test_ids']) if i in set(d['cohort'])}
                cohort_affected+=sum((row,l,c,i) in marked for i in scores[c])
            a,b=scores['steered'],scores['random']
            out[row][l]=dict(steered=statistic(a),random=statistic(b),difference=statistic(a,b),missing={c:sum(v is None for v in x.values()) for c,x in scores.items()})
            os[row][l]=out[row][l]['difference']
    return dict(authority='79f63fe0 path-redaction sensitivity',affected_readouts=len(keys),affected_in_registered_cohort=cohort_affected,rows=out,rules=classify_rules(ps,os,old44),probe_statistics='unchanged primary; no refit',exclusion='affected readout score missing; original paired item grid retained')
