"""Once-only CPU E23 analysis; private labels join only after complete collection seals."""
import argparse
from dataclasses import asdict
from pathlib import Path
import numpy as np
import common  # exposes the pinned vendored mats library
from .cpu import ROOT,read,rows,dump,sha,verify,seal
from .e23 import SEED,FEATURES,LAYERS,ARMS,CONTRACT,assemble_texts

BOOT=2000


def fit_probe(x,y):
    import torch
    from mats.probes import fit_logreg
    return fit_logreg(torch.as_tensor(x,dtype=torch.float32),torch.as_tensor(y),lam=1e-3)


def decide(model,x):
    import torch
    return model.decision(torch.as_tensor(x,dtype=torch.float32)).numpy()


def probe_scores(x,y,groups,controls,folds=None):
    """Each held-out recipient gets its fold's F16 probe on controls, never refit."""
    from mats.probes import group_folds
    y=np.asarray(y); groups=np.asarray(groups)
    folds=group_folds(groups,5,SEED) if folds is None else folds
    result={'matched':np.empty(len(y)),**{k:np.empty(len(y)) for k in controls}}
    receipt=[]
    for te in folds:
        tr=np.setdiff1d(np.arange(len(y)),te)
        if set(groups[tr]) & set(groups[te]) or set(y[tr])!={0,1}: raise ValueError('probe fold invalid')
        m=fit_probe(x[tr],y[tr]); result['matched'][te]=decide(m,x[te])
        for k,v in controls.items(): result[k][te]=decide(m,v[te])
        receipt.append({'train_indices':tr.tolist(),'test_indices':te.tolist()})
    return result,receipt


def text_fit(train,y,test):
    import warnings
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.exceptions import ConvergenceWarning
    v=TfidfVectorizer(analyzer='char',ngram_range=(1,4),lowercase=False,min_df=1,norm='l2',use_idf=True,smooth_idf=True,sublinear_tf=False)
    x=v.fit_transform(train)
    m=LogisticRegression(C=1.,penalty='l2',solver='lbfgs',max_iter=2000,tol=1e-4,random_state=SEED)
    with warnings.catch_warnings():
        warnings.simplefilter('error',ConvergenceWarning); m.fit(x,np.asarray(y))
    return m.decision_function(v.transform(test))


def linear_contrast(terms,labels,n_boot=BOOT):
    """Joint cluster bootstrap; shared items stay paired, O/S resample independently.

    Each term is coefficient plus {item_id: score}. S M1 uses select160 while S
    M2 keeps all200. The union draw retains that difference in denominators.
    """
    from mats.metrics import auroc_labels
    ids=sorted(set().union(*(set(scores) for weight,scores in terms)))
    byset={}
    for key in ids:
        r=labels[key]; byset.setdefault(r['set'],{}).setdefault(r['cluster'],[]).append(key)
    def stat(draw):
        value=0.
        for weight,scores in terms:
            keys=[k for k in draw if k in scores]
            value+=weight*auroc_labels([scores[k] for k in keys],[labels[k]['y'] for k in keys])
        return value
    rng=np.random.default_rng(SEED); samples=[]
    for _ in range(n_boot):
        draw=[]
        for dataset,grouped in sorted(byset.items()):
            pools=[grouped[k] for k in sorted(grouped)]
            draw.extend(k for j in rng.integers(0,len(pools),len(pools)) for k in pools[j])
        samples.append(stat(draw))
    finite=np.asarray(samples)[np.isfinite(samples)]
    if len(finite)==0: raise ValueError('no valid bootstrap samples')
    return {'estimate':float(stat(ids)),'ci95':np.quantile(finite,[.025,.975]).tolist(),
            'bootstrap':n_boot,'seed':SEED,'term_n':[len(s) for w,s in terms]}


def analyse(a):
    import common
    from mats.probes import group_folds
    from mats.metrics import auroc_ci
    from projects.g_agreement.blindspot.analysis import fit_direction
    verify(a.inputs,'INPUT_SEAL.json'); verify(a.collection); verify(a.collection/'continuations')
    run=read(a.collection/'run.json')
    if run['status']!='COMPLETE' or read(a.collection/'SCORE_SEAL.json')['status']!='E23_COMPLETE': raise ValueError('complete collection required')
    if run['input_seal_sha256']!=sha(a.inputs/'INPUT_SEAL.json'): raise ValueError('input lineage mismatch')
    if not read(a.collection/'PARITY.json')['all_items_all_layers']: raise ValueError('parity gate not passed')
    verify(a.collection,'FORECAST_SEAL.json')
    assignment=read(a.assignment)
    if sha(a.assignment)!=run['assignment_sha256']: raise ValueError('assignment receipt mismatch')
    for path,digest in assignment['source_files'].items():
        if sha(ROOT/path)!=digest: raise ValueError('analysis source differs from launched source')
    if sha(a.labels)!=read(a.inputs/'provenance.json')['private_sha256']: raise ValueError('private seal mismatch')
    items=rows(a.inputs/'items.input.jsonl'); labels={r['id']:r for r in rows(a.labels)}
    if set(labels)!={r['id'] for r in items}: raise ValueError('label grid mismatch')
    # Claim the once guard before any fit, metric or bootstrap.
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with a.out.with_suffix('.once.json').open('x') as f: f.write('{"status":"STARTED_NO_AUTOMATIC_RETRY"}\n')
    a.out.mkdir(exist_ok=False)
    donors=read(a.inputs/'donors.json'); cont={r['id']:r for r in rows(a.collection/'continuations/continuations.jsonl')}
    text=assemble_texts(items,cont,donors); index={r['id']:i for i,r in enumerate(items)}
    frozen=np.load(a.inputs/'W1.directions.npz',allow_pickle=False)
    si=[i for i,r in enumerate(items) if r['set']=='S']; sindex={i:j for j,i in enumerate(si)}
    sh=np.load(a.collection/'S.acts44.npy',allow_pickle=False)
    pred={}; reports=[]; fits={}; fold_receipts={}; secondary_transfer=[]
    def put(dataset,feature,layer,arm,measure,ix,score):
        score=np.asarray(score,dtype=float)
        if score.shape!=(len(ix),) or not np.isfinite(score).all(): raise ValueError('prediction grid invalid')
        key=(dataset,feature,layer,arm,measure)
        pred[key]={items[i]['id']:float(s) for i,s in zip(ix,score)}
        rr=[labels[items[i]['id']] for i in ix]
        metric=asdict(auroc_ci(score,[r['y'] for r in rr],[r['cluster'] for r in rr],n_boot=BOOT,seed=SEED))
        reports.append({'set':dataset,'feature':feature,'tag':layer,'arm':arm,'contract':CONTRACT[arm],'measure':measure,**metric})
    for dataset,feature in sorted({(r['set'],r['feature']) for r in items}):
        ri=[i for i,r in enumerate(items) if r['set']==dataset and r['feature']==feature]
        dev=[i for i in ri if items[i]['split']=='dev']; test=[i for i in ri if items[i]['split']=='test']
        y=lambda ix:np.array([labels[items[i]['id']]['y'] for i in ix])
        if dataset=='O': direction=frozen[feature]
        else:
            fit=fit_direction(sh[[sindex[i] for i in dev]],y(dev)); direction=fit['direction']
            fits[feature]={k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in fit.items()}
        m2ix=test if dataset=='O' else ri
        groups=np.array([labels[items[i]['id']]['cluster'] for i in m2ix]); folds=group_folds(groups,5,SEED)
        # T uses the same frozen folds for O, and the registered mine/select split for S.
        for arm in ARMS:
            strings=text[arm]
            if dataset=='S': ts=text_fit([strings[i] for i in dev],y(dev),[strings[i] for i in test]); tix=test
            else:
                ts=np.empty(len(test)); tix=test
                for te in folds:
                    tr=np.setdiff1d(np.arange(len(test)),te)
                    ts[te]=text_fit([strings[test[j]] for j in tr],y([test[j] for j in tr]),[strings[test[j]] for j in te])
            for layer in LAYERS: put(dataset,feature,layer,arm,'T',tix,ts)
        for layer in LAYERS:
            raw={arm:np.load(a.collection/f'ar_{layer}_{arm}.npy',allow_pickle=False) for arm in ('F16','P32','Pfull')}
            for arm in ('Mis','Swap'):
                raw[arm]=raw['F16'][[index[donors[arm][r['id']]] for r in items]]
            for arm in ARMS:
                put(dataset,feature,layer,arm,'M1',test,raw[arm][test]@direction)
                if dataset=='S':
                    score=raw[arm][test]@frozen[feature]
                    transfer=asdict(auroc_ci(score,y(test),[labels[items[i]['id']]['cluster'] for i in test],n_boot=BOOT,seed=SEED))
                    secondary_transfer.append({'set':dataset,'feature':feature,'tag':layer,'arm':arm,'contract':CONTRACT[arm],**transfer})
            for arm in ('F16','P32','Pfull'):
                controls={k:raw[k][m2ix] for k in ('Mis','Swap')} if arm=='F16' else {}
                scores,receipt=probe_scores(raw[arm][m2ix],y(m2ix),groups,controls,folds)
                put(dataset,feature,layer,arm,'M2',m2ix,scores['matched'])
                for k in controls: put(dataset,feature,layer,k,'M2',m2ix,scores[k])
                fold_receipts[f'{dataset}|{feature}|{layer}|{arm}']={'recipient_ids':[items[i]['id'] for i in m2ix],'folds':receipt,'controls_fit':'F16 only' if controls else None}
    summary={(r['set'],r['feature'],r['tag'],r['arm'],r['measure']):r for r in reports}
    contrasts=[]
    for layer in LAYERS:
        for dataset in ('O','S'):
            for name,arms,measures in [('rule1_measure',('F16','F16'),('M2','M1')),('rule2_input',('P32','F16'),('M1','M1'))]:
                result=linear_contrast([(1,pred[(dataset,'table_column',layer,arms[0],measures[0])]),(-1,pred[(dataset,'table_column',layer,arms[1],measures[1])])],labels)
                contrasts.append({'rule':name,'set':dataset,'tag':layer,**result,'passes':result['estimate']>=.15 and result['ci95'][0]>0})
        for feature in ('table_column','list_index','prose_paren'):
            for arm in ARMS:
                for measure in ('M1','M2','T'):
                    result=linear_contrast([(1,pred[('S',feature,layer,arm,measure)]),(-1,pred[('O',feature,layer,arm,measure)])],labels)
                    contrasts.append({'rule':'rule3_items','feature':feature,'tag':layer,'arm':arm,'contract':CONTRACT[arm],'measure':measure,**result,'passes':result['estimate']>=.15 and result['ci95'][0]>0})
    gates=[]; beyond=[]; swap=[]
    for dataset,feature in sorted({(r['set'],r['feature']) for r in items}):
        for layer in LAYERS:
            positive={f:summary[('O',f,layer,'F16','M1')]['auroc']>=.8 for f in ('python_string','prose_sentiment')}
            mis={m:.4<=summary[(dataset,feature,layer,'Mis',m)]['auroc']<=.6 for m in ('M1','M2')}
            gates.append({'set':dataset,'feature':feature,'tag':layer,'Mis':mis,'positive_controls':positive,'interpretable':all(mis.values()) and all(positive.values())})
            for arm in ARMS:
                beyond.append({'set':dataset,'feature':feature,'tag':layer,'arm':arm,'contract':CONTRACT[arm],
                    'AR_adds_nothing_beyond_text':summary[(dataset,feature,layer,arm,'M2')]['auroc']<=summary[(dataset,feature,layer,arm,'T')]['auroc']+.05})
            for measure in ('M1','M2'):
                f=summary[(dataset,feature,layer,'F16',measure)]['auroc']; s=summary[(dataset,feature,layer,'Swap',measure)]['auroc']
                swap.append({'set':dataset,'feature':feature,'tag':layer,'measure':measure,'F16':f,'Swap':s,'prediction_applies':f>=.7,'prediction_met':s<=.5 if f>=.7 else None})
    asked={}; asked_rows=[]
    for layer in (42,44):
        for phrasing in ('W1','Suraj'):
            rr=rows(a.collection/f'asked_{layer}_{phrasing}.jsonl')
            for dataset in ('O','S'):
                q={r['id']:r['score'] for r in rr if r['set']==dataset}
                expected={r['id'] for r in items if r['set']==dataset and r['feature']=='table_column' and r['split']=='test'}
                if set(q)!=expected: raise ValueError('E23b cell incomplete')
                asked[(dataset,phrasing,layer)]=q
                result=linear_contrast([(1,q)],labels)
                asked_rows.append({'set':dataset,'phrasing':phrasing,'layer':layer,**result})
    factors=[]
    for name,axis,positive in [('set',0,'S'),('phrasing',1,'Suraj'),('layer',2,44)]:
        result=linear_contrast([(.25 if key[axis]==positive else -.25,q) for key,q in asked.items()],labels)
        factors.append({'factor':name,**result,'magnitude':abs(result['estimate']),
                        'qualifies':abs(result['estimate'])>=.10 and (result['ci95'][0]>0 or result['ci95'][1]<0)})
    largest=max(factors,key=lambda r:r['magnitude'])
    rules={name:all(r['passes'] for r in contrasts if r['rule']==name and r['tag']==44) for name in ('rule1_measure','rule2_input')}
    result={'status':'COMPLETE','exploratory':True,'primary_tag':44,'secondary_tag':40,'raw_space':True,'orientation_flipped':False,
            'rows':reports,'contrasts':contrasts,'rules_primary':rules,'validity_gates':gates,'rule4':beyond,
            'Swap_secondary':swap,'W1_transfer_secondary':secondary_transfer,'E23b':{'cells':asked_rows,'factors':factors,
            'rule6_cause':largest['factor'] if largest['qualifies'] else 'unresolved'},'setS_probe_fits':fits,
            'outcome_c':'does not apply; following span','seed':SEED,'bootstrap':BOOT,
            'notes':['M2 set S uses all200; M1/T use select160; joint bootstrap retains different denominators.',
                     'Mis/Swap M2 use the recipient fold F16 probe, without refit; donor may belong to its training pool as registered.',
                     'T fits each span arm, including controls; no tuning. Positive-control failure flags all affected assay rows.',
                     'E23b ranks absolute main-effect magnitude and reports signed contrasts; no selection of items or phrasings.']}
    dump(a.out/'metrics.json',result); dump(a.out/'folds.json',fold_receipts)
    jsonl=__import__('projects.g_agreement.understand.followup_packed',fromlist=['jsonl']).jsonl
    jsonl(a.out/'predictions.jsonl',[{'set':k[0],'feature':k[1],'tag':k[2],'arm':k[3],'measure':k[4],'id':i,'score':v} for k,p in pred.items() for i,v in p.items()])
    lines=['**Predictions (§117):** discriminate measure, input and item-set explanations using the frozen rules; Mis must be at chance, the two positive controls must pass, and Swap should reverse a strong F16 signal.',
           '',f'**Assessment:** rule1 measure={rules["rule1_measure"]}; rule2 input={rules["rule2_input"]}; E23b cause={result["E23b"]["rule6_cause"]}. Interpretability is conditional on the reported validity gates.',
           '', 'EXPLORATORY. Tag44 primary; tag40 secondary. Raw M1; no sign flip or whitening. Full contrasts, gates, Swap and transfer secondaries are in metrics.json. Outcome(c) does not apply.',
           '', '| Set | Row | Tag | Arm | Contract | Measure | AUROC [95% CI] | n |','|---|---|---|---|---|---|---|---|']
    for r in reports: lines.append(f'| {r["set"]} | {r["feature"]} | {r["tag"]} | {r["arm"]} | {r["contract"]} | {r["measure"]} | {r["auroc"]:.4f} [{r["lo"]:.4f}, {r["hi"]:.4f}] | {r["n"]} |')
    (a.out/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    dump(a.out/'provenance.json',{'collection_seal_sha256':sha(a.collection/'SCORE_SEAL.json'),'input_seal_sha256':sha(a.inputs/'INPUT_SEAL.json'),'assignment_sha256':sha(a.assignment),'authority_commit':'e347b86a'})
    seal(a.out,[p.name for p in a.out.iterdir() if p.is_file()],'E23_REGISTERED_ANALYSIS_COMPLETE')
    dump(a.out.with_suffix('.once.json'),{'status':'COMPLETE_DO_NOT_RERUN','seal_sha256':sha(a.out/'SCORE_SEAL.json')})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('inputs','collection','labels','assignment','out'): p.add_argument('--'+k,type=Path,required=True)
    analyse(p.parse_args())
