"""Once-only E27(c) item-bootstrap donor/recipient AUROCs; no model imports or refits."""
import argparse
import time
from pathlib import Path
import numpy as np
from scipy.stats import rankdata
from .cpu import ROOT,read,rows,dump,sha,verify,seal
from .e27c import FEATURES,ARMS,validate,s16


def interval(scores,y,indices):
    s=np.asarray(scores)[indices];by=np.asarray(y)[indices]
    n1=by.sum(1);n0=len(y)-n1;r=rankdata(s,axis=1,method='average')
    samples=np.divide((r*by).sum(1)-n1*(n1+1)/2,n1*n0,
                      out=np.full(len(indices),np.nan),where=(n1*n0)>0)
    good=samples[np.isfinite(samples)]
    if not len(good):raise ValueError('no two-class bootstrap samples')
    return {'ci95':np.quantile(good,[.025,.975]).tolist(),'invalid_resamples':int(len(samples)-len(good))}


def summarize(scores,y,j,lib=None):
    lib=lib or s16();a=np.asarray(scores,float);y=np.asarray(y,int);j=np.asarray(j,int)
    if a.ndim!=2 or a.shape[1]!=84 or len(y)!=84 or len(j)!=84 or not np.isfinite(a).all():raise ValueError('84 finite scores per phrasing required')
    if not np.isin(y,[0,1]).all() or set(y)!={0,1} or np.any(y[j]==y):raise ValueError('opposite binary partners required')
    indices=np.random.default_rng(20261025).integers(0,84,(2000,84));out={}
    for name,s in [('mean',a.mean(0)),('fixed',a[0])]:
        point=lib.follow(s,y,j)
        out[name]={side:{'auroc':point[side],**interval(s,labels,indices)}
                   for side,labels in [('follows_i',y),('follows_j',y[j])]}
    return out


def decision(metrics):
    # Keep each arm separate: the registration does not authorise averaging the arms.
    out={}
    for arm in ARMS:
        values=[metrics[f][arm]['mean']['follows_j']['auroc'] for f in FEATURES[:3]]
        out[arm]='DESIGN_POWER' if all(v>=.80 for v in values) else ('BANK_OR_LABELS' if all(v<=.60 for v in values) else 'MIXED_OR_INTERMEDIATE')
    return out


def render(metrics,rules):
    lines=['# E27(c) — DESCRIPTIVE','',
       'Registered comparison: S16 design on W1; all three matched rows ≥0.80 supports design/power, all three ≤0.60 supports bank/labels. Each arm is assessed separately; other patterns are unresolved.','',
       'Assessment: '+', '.join(f'{arm}: {value}' for arm,value in rules.items())+'.','',
       '| Row | Arm | Mean donor AUROC [95% CI] | Fixed donor AUROC [95% CI] |',
       '|---|---|---|---|']
    def fmt(r):return f"{r['auroc']:.4f} [{r['ci95'][0]:.4f}, {r['ci95'][1]:.4f}]"
    for feature in FEATURES:
        for arm in ARMS:
            r=metrics[feature][arm];lines.append(f"| {feature} | {arm} | {fmt(r['mean']['follows_j'])} | {fmt(r['fixed']['follows_j'])} |")
    lines+=['','84 test recipients per row; partner seed16, one opposite-value donor from another template cluster. Two sampled readouts per item/reader, reconstructed with the native NLA reconstructor and averaged. Direct pinned S16 construct/follow functions; raw space; native NLA@42 B-minus-A scoring.',
       '', 'Matched rows retain S16’s original four phrasings, including list-index ordinal wording that does not exactly name W1’s values. Four extension rows use the two existing W1 NLA phrasings. This tests the transferred S16 design, not an isolated bank effect with every label phrase matched.',
       '', 'CIs: 2,000 recipient-item resamples, seed20261025; partners held fixed. Reused donors and template dependence are not included in this requested item bootstrap. All recipient AUROCs, exact invalid resample counts, and fixed/mean results are in metrics.json. No probe fitting or secondary Oracle@42 scoring.','']
    return '\n'.join(lines)


def analyse(a):
    spec=validate(a.inputs);verify(a.collection)
    run=read(a.collection/'run.json')
    if run['status']!='COMPLETE' or run['input_seal_sha256']!=sha(a.inputs/'INPUT_SEAL.json'):raise ValueError('complete matched collection required')
    for name,digest in run['source_files'].items():
        if sha(ROOT/name)!=digest:raise ValueError('source changed since collection')
    if sha(a.labels)!=read(a.inputs/'provenance.json')['labels_sha256']:raise ValueError('sealed labels mismatch')
    labels=rows(a.labels);ids=read(a.inputs/'ids.json')
    if [r['id'] for r in labels]!=ids:raise ValueError('private labels misaligned')
    arrays={(f,arm):np.load(a.collection/f'scores-{f}-{arm}.npy',allow_pickle=False) for f in FEATURES for arm in ARMS}
    a.out.mkdir(parents=True,exist_ok=False);dump(a.out/'ANALYSIS_ONCE.json',{'status':'STARTED_ONCE'})
    start=time.monotonic();metrics={};lib=s16()
    for f in FEATURES:
        r=spec[f];truth=[labels[i]['y'] for i in r['indices']]
        metrics[f]={arm:summarize(arrays[f,arm],truth,r['partners'],lib) for arm in ARMS}
    rules=decision(metrics);dump(a.out/'metrics.json',{'rows':metrics,'decision_by_arm':rules})
    (a.out/'RESULTS.md').write_text(render(metrics,rules))
    dump(a.out/'ANALYSIS_RUN.json',{'status':'COMPLETE_ONCE','wall_seconds':time.monotonic()-start,'GPU_hours':0,
         'collection_seal_sha256':sha(a.collection/'SCORE_SEAL.json'),'input_seal_sha256':sha(a.inputs/'INPUT_SEAL.json'),
         'source_commit':run['source_commit'],'bootstrap_samples':2000,'bootstrap_seed':20261025})
    seal(a.out,[p.name for p in a.out.iterdir() if p.is_file()],'E27C_REGISTERED_ANALYSIS_ONCE')
    print('HANDOFF E27C',a.out/'RESULTS.md',sha(a.out/'SCORE_SEAL.json'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','collection','labels','out'):p.add_argument('--'+name,type=Path,required=True)
    analyse(p.parse_args())
