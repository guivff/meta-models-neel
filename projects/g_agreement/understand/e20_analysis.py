"""Once-only E20 §112 CPU analysis, fixed bands and three-row Holm correction."""
import argparse
import json
from pathlib import Path
import numpy as np
from projects.g_agreement.blindspot import protocol as P
from .e20_worker import ROWS

DISTANCES=(2,4,8,16,32,48)
BANDS={'near':(0,1,2),'far':(4,5)}


def pair_auc(values):
    """[pair,state(A,B)] matrix; ties get half credit."""
    a,b=values[:,0,None],values[None,:,1]
    return float(np.mean((a>b)+.5*(a==b)))


def band_scores(values,band):
    return values[:,:,BANDS[band]].mean(axis=2)


def holm(pvalues):
    order=sorted(pvalues,key=pvalues.get);result={};previous=0.
    for j,key in enumerate(order):
        previous=max(previous,min(1.,(len(order)-j)*pvalues[key]));result[key]=previous
    return result


def summarize(values,draws):
    result={'distances':{str(d):pair_auc(values[:,:,j]) for j,d in enumerate(DISTANCES)}}
    bands={b:band_scores(values,b) for b in BANDS}
    for b,v in bands.items():
        boots=np.array([pair_auc(v[idx]) for idx in draws])
        result[b]={'auroc':pair_auc(v),'ci95':np.quantile(boots,[.025,.975]).tolist()}
    delta=np.array([pair_auc(bands['near'][idx])-pair_auc(bands['far'][idx]) for idx in draws])
    result['near_minus_far']={'difference':result['near']['auroc']-result['far']['auroc'],
        'ci95':np.quantile(delta,[.025,.975]).tolist(),'p_one_sided':float((np.sum(delta<=0)+1)/(len(draws)+1))}
    return result


def analyse(a):
    import torch
    from mats.probes import fit_logreg
    if a.out.exists():raise ValueError('analysis exists; do not repeat')
    plan=json.loads(a.plan.read_text())
    for root,seal in [(a.bank,'INPUT_SEAL.json'),(a.outputs,'SCORE_SEAL.json'),(a.outputs,'CAPTURE_SEAL.json'),(a.outputs,'VALIDITY_SEAL.json')]:P.verify(root,seal)
    provenance=json.loads((a.outputs/'PROVENANCE.json').read_text())
    if provenance['plan_sha256']!=P.sha(a.plan) or provenance['input_seal_sha256']!=P.sha(a.bank/'INPUT_SEAL.json'):
        raise ValueError('input/plan binding mismatch')
    if P.sha(a.labels)!=plan['labels_sha256']:raise ValueError('frozen label hash mismatch')
    for n,h in plan['source_files'].items():
        if P.sha(P.ROOT/n)!=h:raise ValueError('use archived analysis source: '+n)
    items=P.rows(a.bank/'items.input.jsonl');labels=P.rows(a.labels);byid={x['id']:x for x in labels}
    ids=[x['id'] for x in items]
    if len(ids)!=len(set(ids)) or set(ids)!=set(byid) or len(byid)!=len(labels):raise ValueError('label population mismatch')
    order=json.loads((a.outputs/'items.order.json').read_text());h=np.load(a.outputs/'acts44.npy',allow_pickle=False)
    if order!=ids or h.ndim!=2 or len(h)!=5760 or not np.isfinite(h).all():raise ValueError('capture order/shape mismatch')
    base_rows=P.rows(a.outputs/'base.jsonl');lens_rows=P.rows(a.outputs/'lens.jsonl')
    base={x['id']:x for x in base_rows};lens={x['id']:x for x in lens_rows}
    validity=json.loads((a.outputs/'VALIDITY.json').read_text())
    allowed={r for r,v in validity.items() if v['status']=='EVALUABLE'}
    if set(base)!=set(ids) or len(base)!=len(base_rows) or len(lens)!=len(lens_rows) or set(lens)!={x['id'] for x in items if x['feature'] in allowed}:
        raise ValueError('incomplete/duplicate output grid')
    with a.out.with_suffix('.lock').open('x') as f:json.dump({'score_seal_sha256':P.sha(a.outputs/'SCORE_SEAL.json')},f)
    a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(4)
    report={};primary={};probe_predictions={}
    for row in ROWS:
        if row not in allowed:
            report[row]={'status':'NOT EVALUABLE','validity':validity[row]};continue
        train_clusters={x['cluster'] for x in items if x['feature']==row and x['split']=='dev'}
        test_clusters={x['cluster'] for x in items if x['feature']==row and x['split']=='test'}
        if train_clusters & test_clusters:raise ValueError('template leakage')
        for distance in DISTANCES:
            tr=[i for i,x in enumerate(items) if x['feature']==row and x['distance']==distance and x['split']=='dev']
            te=[i for i,x in enumerate(items) if x['feature']==row and x['distance']==distance and x['split']=='test']
            if len(tr)!=80 or len(te)!=160:raise ValueError('dev/test counts')
            probe=fit_logreg(torch.from_numpy(h[tr]),torch.tensor([byid[ids[i]]['label'] for i in tr]))
            pred=probe.decision(torch.from_numpy(h[te])).numpy()
            probe_predictions.update({ids[i]:float(s) for i,s in zip(te,pred)})
        pairs=sorted({x['pair_id'] for x in items if x['feature']==row and x['split']=='test'})
        cell={(x['pair_id'],1-byid[x['id']]['label'],x['distance']):x['id'] for x in items if x['feature']==row and x['split']=='test'}
        if len(pairs)!=80 or len(cell)!=960:raise ValueError('paired test cell population')
        channels={k:np.empty((80,2,6)) for k in ['base','probe','generation','consequence_true','consequence_random_donor','consequence_opposite_donor','asked']}
        for p,pair in enumerate(pairs):
            for state in (0,1):
                for j,d in enumerate(DISTANCES):
                    i=cell[pair,state,d];b=base[i];l=lens[i]
                    values={'base':b['positive_count']/8,'probe':probe_predictions[i],'generation':l['positive_count'],
                            'asked':float(np.mean(l['asked'])),**{'consequence_'+arm:s for arm,s in l['consequence'].items()}}
                    for k,v in values.items():channels[k][p,state,j]=v
        if any(not np.isfinite(v).all() for v in channels.values()):raise ValueError('nonfinite channel values')
        draws=np.random.default_rng(20261025).integers(0,80,(2000,80))
        summary={k:summarize(v,draws) for k,v in channels.items()}
        report[row]={'status':'EVALUABLE','validity':validity[row],'channels':summary,
            'probe':'one L2 logistic probe per distance; fitted/standardized only on dev; lam1e-3,200iterations',
            'bootstrap':'2000 item-pair clusters; both states and all distances retained together;seed20261025'}
        if row!='prose_sentiment_delayed':primary[row]=summary['generation']['near_minus_far']['p_one_sided']
    # Failing validity rows retain a p=1 slot in the registered family of three.
    adjusted=holm({r:primary.get(r,1.) for r in ['prose_paren','python_string','fact_once']})
    control=report['prose_sentiment_delayed']
    control_pass=(control['status']=='EVALUABLE' and control['channels']['consequence_true']['far']['auroc']>=.8 and control['channels']['consequence_true']['far']['ci95'][0]>=.7)
    for row,v in report.items():
        if v['status']!='EVALUABLE':continue
        s=v['channels']
        if row=='prose_sentiment_delayed':v['verdict']='CONTROL PASS' if control_pass else 'CONTROL FAIL';continue
        contrast=s['generation']['near_minus_far'];checks={'effect_ge_015':contrast['difference']>=.15,'ci_above_zero':contrast['ci95'][0]>0,'holm_p_below_005':adjusted[row]<.05}
        if row=='fact_once':checks['source_far_ge_080']=s['probe']['far']['auroc']>=.8
        else:
            checks['source_flat_within_005']=abs(s['probe']['near_minus_far']['difference'])<=.05
            checks['base_drop_ge_030']=s['base']['near_minus_far']['difference']>=.3
        v.update(holm_p=adjusted[row],criteria=checks,verdict='HELD' if all(checks.values()) else 'DID NOT HOLD',channel4_interpretable=control_pass)
        if row=='fact_once' and s['generation']['far']['auroc']>=.75:v['verdict']='FALSIFIED (far generation >=0.75)'
    P.dump(a.out/'metrics.json',{'rows':report,'holm_family':adjusted,'sentiment_control_pass':control_pass,'score_seal_sha256':P.sha(a.outputs/'SCORE_SEAL.json')})
    P.dump(a.out/'probe_predictions.json',probe_predictions)
    text='# E20 results\n\nPrediction: native lens generation follows the model expectation horizon; source state remains decodable.\n\n'
    for row,v in report.items():text+=f"- {row}: **{v.get('verdict',v['status'])}**\n"
    text+='\nPer-distance and band AUROCs, pair-bootstrap intervals, all donor arms, exact criteria and the three-row Holm correction are in metrics.json. Asked scores are descriptive. Channel-4 interpretation is conditional on the sentiment control.\n'
    (a.out/'RESULTS.md').write_text(text)
    P.dump(a.out/'ANALYSIS_SEAL.json',{'status':'E20_ANALYSIS_COMPLETE','files':{n:P.sha(a.out/n) for n in ['metrics.json','probe_predictions.json','RESULTS.md']}})


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('bank','plan','outputs','labels','out'):p.add_argument('--'+n,type=Path,required=True)
    analyse(p.parse_args())
